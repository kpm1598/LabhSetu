"""Tests for automatic timestamps on the LabhSetu models.

Correction to Task 1: new Scheme / SchemeSource instances must get
created_at and updated_at automatically, new SyncLog instances must get
started_at, all from the shared UTC ISO 8601 helper (utc_now_iso).
Explicitly supplied timestamps - the values of records already stored
in the database - must be preserved, including through from_row.

Database tests use the temporary test database only (see conftest.py).
"""

from datetime import datetime, timezone

from app import database
from app.models import Scheme, SchemeSource, SyncLog

# Fixed, clearly-in-the-past timestamps: if any of these come back
# changed, something overwrote a supplied value with "now".
CREATED = "2020-01-02T03:04:05+00:00"
UPDATED = "2021-06-07T08:09:10+00:00"
STARTED = "2019-11-12T13:14:15+00:00"


def _assert_recent_utc_iso(value: str) -> None:
    """Assert value is a UTC ISO 8601 timestamp from the last minute."""
    assert value is not None
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    assert 0 <= age_seconds < 60


# Automatic initialization ---------------------------------------------------

def test_new_scheme_gets_created_and_updated_timestamps():
    scheme = Scheme(official_name="Test Fixture Scheme (not a real scheme)")
    _assert_recent_utc_iso(scheme.created_at)
    # On a new record, updated_at starts equal to created_at.
    assert scheme.updated_at == scheme.created_at


def test_new_scheme_source_gets_created_and_updated_timestamps():
    source = SchemeSource(source_name="Test Source", source_url="https://example.org")
    _assert_recent_utc_iso(source.created_at)
    assert source.updated_at == source.created_at


def test_new_sync_log_gets_started_at():
    log = SyncLog(status="started")
    _assert_recent_utc_iso(log.started_at)


# Preservation of supplied timestamps ----------------------------------------

def test_scheme_preserves_supplied_timestamps():
    scheme = Scheme(official_name="X", created_at=CREATED, updated_at=UPDATED)
    assert scheme.created_at == CREATED
    assert scheme.updated_at == UPDATED


def test_scheme_fills_only_the_missing_timestamp():
    scheme = Scheme(official_name="X", created_at=CREATED)
    assert scheme.created_at == CREATED
    # updated_at falls back to the supplied created_at, not to "now".
    assert scheme.updated_at == CREATED


def test_scheme_source_preserves_supplied_timestamps():
    source = SchemeSource(
        source_name="S",
        source_url="https://example.org",
        created_at=CREATED,
        updated_at=UPDATED,
    )
    assert source.created_at == CREATED
    assert source.updated_at == UPDATED


def test_sync_log_preserves_supplied_started_at():
    log = SyncLog(status="completed", started_at=STARTED)
    assert log.started_at == STARTED


def test_timestamps_survive_database_round_trip(temp_db_path):
    """Rows written with old timestamps read back with the same values."""
    database.initialize_database(temp_db_path)

    scheme = Scheme(
        official_name="Test Fixture Scheme (not a real scheme)",
        scheme_code="TEST-TS-001",
        created_at=CREATED,
        updated_at=UPDATED,
    )
    row = scheme.to_row()
    columns = ", ".join(row.keys())
    placeholders = ", ".join(f":{name}" for name in row.keys())

    source = SchemeSource(
        source_name="Test Source",
        source_url="https://example.org",
        created_at=CREATED,
        updated_at=UPDATED,
    )
    source_row = source.to_row()
    source_columns = ", ".join(source_row.keys())
    source_placeholders = ", ".join(f":{name}" for name in source_row.keys())

    with database.get_db(temp_db_path) as connection:
        connection.execute(
            f"INSERT INTO schemes ({columns}) VALUES ({placeholders})", row
        )
        connection.execute(
            f"INSERT INTO scheme_sources ({source_columns}) VALUES ({source_placeholders})",
            source_row,
        )
        connection.commit()
        stored_scheme = connection.execute("SELECT * FROM schemes").fetchone()
        stored_source = connection.execute("SELECT * FROM scheme_sources").fetchone()

    loaded_scheme = Scheme.from_row(stored_scheme)
    assert loaded_scheme.created_at == CREATED
    assert loaded_scheme.updated_at == UPDATED

    loaded_source = SchemeSource.from_row(stored_source)
    assert loaded_source.created_at == CREATED
    assert loaded_source.updated_at == UPDATED


# Update workflow --------------------------------------------------------------

def test_touch_refreshes_updated_at_but_not_created_at():
    scheme = Scheme(official_name="X", created_at=CREATED, updated_at=CREATED)
    scheme.touch()
    assert scheme.created_at == CREATED
    assert scheme.updated_at != CREATED
    _assert_recent_utc_iso(scheme.updated_at)

    source = SchemeSource(
        source_name="S",
        source_url="https://example.org",
        created_at=CREATED,
        updated_at=CREATED,
    )
    source.touch()
    assert source.created_at == CREATED
    assert source.updated_at != CREATED
    _assert_recent_utc_iso(source.updated_at)
