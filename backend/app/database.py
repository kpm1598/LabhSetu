"""SQLite database configuration and initialization for LabhSetu.

The database is a single SQLite file at ``backend/labhsetu.db``.
Initialization only creates tables and indexes when they are missing
(``CREATE TABLE IF NOT EXISTS``) - it never deletes or overwrites
existing records, so it is safe to run on every application startup.

Tables:
    - scheme_sources: where scheme information came from.
    - schemes: government scheme records.
    - sync_logs: records of synchronization attempts.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Database file lives in the backend folder, whatever machine / OS this runs on.
# (Preserved from the starter project - do not change this location.)
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "labhsetu.db"

# The three tables this foundation is responsible for, in creation order.
# scheme_sources is created first because the other two tables reference it.
REQUIRED_TABLES: tuple[str, ...] = ("scheme_sources", "schemes", "sync_logs")


class DatabaseError(Exception):
    """Raised when database initialization or a database check fails."""


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Example: ``2026-11-02T10:30:00+00:00``. Every timestamp stored in the
    database uses this one format, so timestamps are always comparable.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection(database_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection.

    - Rows are accessible by column name (``sqlite3.Row``).
    - Foreign key enforcement is switched ON. SQLite disables it by
      default, and it must be requested on every single connection.

    The caller is responsible for closing the connection. Prefer the
    ``get_db`` context manager below, which closes it automatically.
    """
    path = Path(database_path) if database_path is not None else DATABASE_PATH
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


@contextmanager
def get_db(database_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection and guarantee it is closed afterwards.

    Usage:
        with get_db() as connection:
            rows = connection.execute("SELECT ...").fetchall()
    """
    connection = get_connection(database_path)
    try:
        yield connection
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Schema
#
# JSON data (beneficiary categories, eligibility criteria, required
# documents, benefit details) is stored as JSON text in TEXT columns.
# Validation and (de)serialization of those fields lives in app.models.
# ---------------------------------------------------------------------------

_CREATE_SCHEME_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS scheme_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT,
    authorization_status TEXT DEFAULT 'unverified',
    last_verified_at TEXT,
    last_successful_sync_at TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""

_CREATE_SCHEMES_TABLE = """
CREATE TABLE IF NOT EXISTS schemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_code TEXT UNIQUE,
    official_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    state TEXT,
    beneficiary_categories TEXT,
    eligibility_criteria TEXT,
    required_documents TEXT,
    benefit_details TEXT,
    application_start_date TEXT,
    application_end_date TEXT,
    official_application_url TEXT,
    source_id INTEGER,
    verification_status TEXT,
    last_verified_at TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (source_id) REFERENCES scheme_sources (id)
);
"""

_CREATE_SYNC_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    started_at TEXT,
    completed_at TEXT,
    status TEXT,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES scheme_sources (id)
);
"""

# Indexes for the most common scheme searches, plus the foreign keys.
_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes (category);",
    "CREATE INDEX IF NOT EXISTS idx_schemes_state ON schemes (state);",
    "CREATE INDEX IF NOT EXISTS idx_schemes_status ON schemes (status);",
    "CREATE INDEX IF NOT EXISTS idx_schemes_category_state ON schemes (category, state);",
    "CREATE INDEX IF NOT EXISTS idx_schemes_source_id ON schemes (source_id);",
    "CREATE INDEX IF NOT EXISTS idx_sync_logs_source_id ON sync_logs (source_id);",
)

_SCHEMA_STATEMENTS = (
    _CREATE_SCHEME_SOURCES_TABLE,
    _CREATE_SCHEMES_TABLE,
    _CREATE_SYNC_LOGS_TABLE,
    *_CREATE_INDEXES,
)


def initialize_database(database_path: Path | str | None = None) -> None:
    """Create the required tables and indexes if they do not exist yet.

    Safe to run multiple times: existing tables and records are left
    untouched. Raises DatabaseError (with the original SQLite error as
    context) if initialization fails.
    """
    try:
        with get_db(database_path) as connection:
            for statement in _SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to initialize database: {exc}") from exc


def get_database_status(database_path: Path | str | None = None) -> dict:
    """Report whether the database exists and has all required tables.

    Never creates the database file: a missing file simply reports
    ``initialized: False``. Used by GET /api/database/status.
    """
    path = Path(database_path) if database_path is not None else DATABASE_PATH
    tables = {table: False for table in REQUIRED_TABLES}

    if not path.exists():
        return {
            "initialized": False,
            "database_path": str(path),
            "tables": tables,
            "all_tables_exist": False,
        }

    try:
        with get_db(path) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = ? AND name IN (?, ?, ?)",
                ("table", *REQUIRED_TABLES),
            ).fetchall()
    except sqlite3.Error as exc:
        return {
            "initialized": False,
            "database_path": str(path),
            "tables": tables,
            "all_tables_exist": False,
            "error": str(exc),
        }

    found = {row["name"] for row in rows}
    for table in tables:
        tables[table] = table in found
    all_exist = all(tables.values())

    return {
        "initialized": all_exist,
        "database_path": str(path),
        "tables": tables,
        "all_tables_exist": all_exist,
    }
