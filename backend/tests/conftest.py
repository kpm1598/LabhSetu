"""Shared test setup for the LabhSetu backend tests.

Makes the ``app`` package importable no matter which folder pytest is
started from, and provides a fixture that points the application at a
temporary database file. Tests must never touch the developer's real
``backend/labhsetu.db``.
"""

import sys
from pathlib import Path

import pytest

# backend/ folder (the parent of this tests/ folder) goes on sys.path
# so `import app...` works from any working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import database  # noqa: E402


@pytest.fixture()
def temp_db_path(tmp_path, monkeypatch) -> Path:
    """Use a fresh temporary database file for one test.

    ``database.DATABASE_PATH`` is patched, and every helper in
    ``app.database`` resolves that global at call time, so both direct
    database calls and the FastAPI startup in ``app.main`` (which calls
    ``database.initialize_database()``) use the temporary file only.
    """
    path = tmp_path / "test_labhsetu.db"
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    return path
