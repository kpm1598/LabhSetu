"""Tests for the LabhSetu database foundation (Task 1).

Every test uses a temporary database file (see conftest.py) - the real
backend/labhsetu.db is never opened, modified, or deleted by tests.
The scheme inserted below is a clearly fake *test fixture* used only to
exercise JSON storage; it is test data, not a real government scheme,
and it never leaves the temporary test database.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.models import (
    Scheme,
    ValidationError,
    dumps_json_field,
    loads_json_field,
    validate_json_text,
)


def _table_names(db_path) -> set[str]:
    with database.get_db(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
        ).fetchall()
    return {row["name"] for row in rows}


# 1. Database initializes successfully --------------------------------------

def test_database_initializes_successfully(temp_db_path):
    database.initialize_database(temp_db_path)
    assert temp_db_path.exists()
    status = database.get_database_status(temp_db_path)
    assert status["initialized"] is True


# 2. Initialization can run multiple times ----------------------------------

def test_initialization_is_idempotent_and_preserves_records(temp_db_path):
    database.initialize_database(temp_db_path)
    with database.get_db(temp_db_path) as connection:
        connection.execute(
            "INSERT INTO scheme_sources (source_name, source_url) VALUES (?, ?)",
            ("Test Source", "https://example.org/source"),
        )
        connection.commit()

    # Running initialization again must not fail or delete anything.
    database.initialize_database(temp_db_path)
    database.initialize_database(temp_db_path)

    with database.get_db(temp_db_path) as connection:
        count = connection.execute("SELECT COUNT(*) AS c FROM scheme_sources").fetchone()["c"]
    assert count == 1


# 3. All three tables exist --------------------------------------------------

def test_all_three_tables_exist(temp_db_path):
    database.initialize_database(temp_db_path)
    names = _table_names(temp_db_path)
    assert {"schemes", "scheme_sources", "sync_logs"} <= names

    status = database.get_database_status(temp_db_path)
    assert status["tables"] == {
        "scheme_sources": True,
        "schemes": True,
        "sync_logs": True,
    }
    assert status["all_tables_exist"] is True


def test_scheme_indexes_exist(temp_db_path):
    database.initialize_database(temp_db_path)
    with database.get_db(temp_db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", ("index",)
        ).fetchall()
    index_names = {row["name"] for row in rows}
    assert "idx_schemes_category" in index_names
    assert "idx_schemes_state" in index_names
    assert "idx_schemes_status" in index_names


# 4. Foreign keys are enabled ------------------------------------------------

def test_foreign_keys_are_enabled(temp_db_path):
    database.initialize_database(temp_db_path)
    with database.get_db(temp_db_path) as connection:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert enabled == 1


def test_foreign_key_is_enforced(temp_db_path):
    database.initialize_database(temp_db_path)
    with database.get_db(temp_db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO sync_logs (source_id, status) VALUES (?, ?)",
                (9999, "started"),  # no scheme_sources row with id 9999
            )


# 5. JSON serialization and deserialization ----------------------------------

def test_json_round_trip_through_database(temp_db_path):
    database.initialize_database(temp_db_path)
    scheme = Scheme(
        official_name="Test Fixture Scheme (not a real scheme)",
        scheme_code="TEST-FIXTURE-001",
        beneficiary_categories=["category-a", "category-b"],
        eligibility_criteria={"min_age": 18},
        required_documents=["Document A"],
        benefit_details={"amount_note": "test fixture value"},
    )
    row = scheme.to_row()
    columns = ", ".join(row.keys())
    placeholders = ", ".join(f":{name}" for name in row.keys())
    with database.get_db(temp_db_path) as connection:
        connection.execute(
            f"INSERT INTO schemes ({columns}) VALUES ({placeholders})", row
        )
        connection.commit()
        stored = connection.execute("SELECT * FROM schemes").fetchone()

    loaded = Scheme.from_row(stored)
    assert loaded.beneficiary_categories == ["category-a", "category-b"]
    assert loaded.eligibility_criteria == {"min_age": 18}
    assert loaded.required_documents == ["Document A"]
    assert loaded.benefit_details == {"amount_note": "test fixture value"}


def test_json_helpers_round_trip():
    value = {"key": ["a", "b"]}
    assert loads_json_field(dumps_json_field(value, "benefit_details"), "benefit_details") == value
    assert loads_json_field(None, "benefit_details") is None


# 6. Invalid JSON is rejected -------------------------------------------------

@pytest.mark.parametrize(
    "bad_json",
    ["{not json", "[unclosed", "{'single': 'quotes'}"],
)
def test_invalid_json_text_is_rejected(bad_json):
    with pytest.raises(ValidationError):
        validate_json_text(bad_json, "eligibility_criteria")
    with pytest.raises(ValidationError):
        dumps_json_field(bad_json, "eligibility_criteria")
    with pytest.raises(ValidationError):
        loads_json_field(bad_json, "eligibility_criteria")


def test_invalid_json_in_scheme_model_is_rejected():
    with pytest.raises(ValidationError):
        Scheme(official_name="X", eligibility_criteria="{broken json")


# 7-9. API endpoints -----------------------------------------------------------

@pytest.fixture()
def client(temp_db_path):
    # Entering the TestClient context runs the FastAPI lifespan, which
    # initializes the (patched, temporary) database.
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint_still_works(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to LabhSetu", "status": "running"}


def test_health_endpoint_still_works(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_status_endpoint_works(client, temp_db_path):
    response = client.get("/api/database/status")
    assert response.status_code == 200
    body = response.json()
    assert body["initialized"] is True
    assert body["all_tables_exist"] is True
    assert body["tables"]["schemes"] is True
    assert body["tables"]["scheme_sources"] is True
    assert body["tables"]["sync_logs"] is True
    # The endpoint must be reporting on the temporary test database,
    # proving the real labhsetu.db was not used.
    assert body["database_path"] == str(temp_db_path)
