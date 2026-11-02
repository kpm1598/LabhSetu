"""Data models for LabhSetu, built on plain Python dataclasses.

No ORM is used. Each dataclass mirrors one database table and knows how
to convert itself to a database row (``to_row``) and back (``from_row``).

JSON fields (beneficiary categories, eligibility criteria, required
documents, benefit details) are kept as parsed Python objects (dict /
list) on the dataclass, stored as JSON text in the database, and parsed
again when a row is read. Malformed JSON raises :class:`ValidationError`
with a clear message - it is never silently accepted.

This module defines shapes and validation only. It contains no scheme
data and invents no eligibility conditions or benefit values.
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

try:  # Normal package import (app.models).
    from app.database import utc_now_iso
except ImportError:  # Direct module import (database next to this file).
    from database import utc_now_iso  # type: ignore[no-redef]

# A JSON field can hold an object, a list, or nothing.
JsonValue = dict[str, Any] | list[Any] | None

# Scheme fields that are stored as JSON text in the database.
SCHEME_JSON_FIELDS: tuple[str, ...] = (
    "beneficiary_categories",
    "eligibility_criteria",
    "required_documents",
    "benefit_details",
)


class ValidationError(ValueError):
    """Raised when data does not pass validation (for example bad JSON)."""


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def validate_json_text(value: str, field_name: str) -> Any:
    """Parse ``value`` as JSON text and return the parsed object.

    Raises ValidationError with the field name if the text is malformed.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValidationError(f"Field '{field_name}' contains invalid JSON: {exc}") from exc


def dumps_json_field(value: JsonValue | str, field_name: str) -> str | None:
    """Serialize a JSON field to the text stored in the database.

    Accepts a Python object (dict / list) or, for convenience, a string
    that must already be valid JSON - a malformed string is rejected
    with ValidationError instead of being stored.
    """
    if value is None:
        return None
    if isinstance(value, str):
        parsed = validate_json_text(value, field_name)
        return json.dumps(parsed, ensure_ascii=False)
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Field '{field_name}' is not JSON serializable: {exc}") from exc


def loads_json_field(raw: str | None, field_name: str) -> JsonValue:
    """Parse JSON text read from the database into a Python object.

    Returns None for an empty column. Raises ValidationError if the
    stored text is malformed, so corrupt data surfaces loudly.
    """
    if raw is None:
        return None
    parsed = validate_json_text(raw, field_name)
    if not isinstance(parsed, (dict, list)):
        raise ValidationError(
            f"Field '{field_name}' must contain a JSON object or array, got {type(parsed).__name__}"
        )
    return parsed


def _normalize_json_field(value: JsonValue | str, field_name: str) -> JsonValue:
    """Normalize a constructor value to a parsed Python object (or None)."""
    if value is None:
        return None
    if isinstance(value, str):
        parsed = validate_json_text(value, field_name)
    else:
        # Round-trip through dumps/loads: proves the value is JSON
        # serializable and detaches it from the caller's object.
        parsed = json.loads(dumps_json_field(value, field_name) or "null")
    if not isinstance(parsed, (dict, list)):
        raise ValidationError(f"Field '{field_name}' must be a JSON object or array")
    return parsed


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not str(value).strip():
        raise ValidationError(f"Field '{field_name}' is required and must not be empty")


def _fill_new_record_timestamps(record: Any) -> None:
    """Populate created_at / updated_at on a NEW record, in place.

    Only missing (None) values are filled, using the shared UTC ISO 8601
    helper from app.database. Explicitly supplied timestamps - for
    example the ones read back from an existing database row by
    ``from_row`` - are always preserved unchanged. A new record's
    updated_at starts equal to its created_at.
    """
    if getattr(record, "created_at", None) is None:
        record.created_at = utc_now_iso()
    if getattr(record, "updated_at", None) is None:
        record.updated_at = record.created_at


# ---------------------------------------------------------------------------
# Models - one dataclass per table
# ---------------------------------------------------------------------------


@dataclass
class SchemeSource:
    """A row of ``scheme_sources``: where scheme information came from.

    A publicly accessible source is NOT automatically an authorized one,
    which is why ``authorization_status`` defaults to 'unverified'.
    """

    source_name: str
    source_url: str
    id: int | None = None
    source_type: str | None = None
    authorization_status: str = "unverified"
    last_verified_at: str | None = None
    last_successful_sync_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.source_name, "source_name")
        _require_non_empty(self.source_url, "source_url")
        _fill_new_record_timestamps(self)

    def touch(self) -> None:
        """Refresh updated_at to now - call before saving an update.

        created_at is never changed by an update.
        """
        self.updated_at = utc_now_iso()

    def to_row(self) -> dict[str, Any]:
        """Return a dict ready for a parameterized INSERT / UPDATE."""
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "authorization_status": self.authorization_status,
            "last_verified_at": self.last_verified_at,
            "last_successful_sync_at": self.last_successful_sync_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SchemeSource":
        """Build a SchemeSource from a database row."""
        data = dict(row)
        return cls(
            id=data.get("id"),
            source_name=data.get("source_name"),
            source_url=data.get("source_url"),
            source_type=data.get("source_type"),
            authorization_status=data.get("authorization_status") or "unverified",
            last_verified_at=data.get("last_verified_at"),
            last_successful_sync_at=data.get("last_successful_sync_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class Scheme:
    """A row of ``schemes``: one government scheme record.

    Only ``official_name`` is required at this layer. Source-verified
    facts are added by later tasks - nothing is invented here.
    """

    official_name: str
    id: int | None = None
    scheme_code: str | None = None
    description: str | None = None
    category: str | None = None
    state: str | None = None
    beneficiary_categories: JsonValue = None
    eligibility_criteria: JsonValue = None
    required_documents: JsonValue = None
    benefit_details: JsonValue = None
    application_start_date: str | None = None
    application_end_date: str | None = None
    official_application_url: str | None = None
    source_id: int | None = None
    verification_status: str | None = None
    last_verified_at: str | None = None
    status: str = "pending"
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.official_name, "official_name")
        for name in SCHEME_JSON_FIELDS:
            setattr(self, name, _normalize_json_field(getattr(self, name), name))
        _fill_new_record_timestamps(self)

    def touch(self) -> None:
        """Refresh updated_at to now - call before saving an update.

        created_at is never changed by an update.
        """
        self.updated_at = utc_now_iso()

    def to_row(self) -> dict[str, Any]:
        """Return a dict ready for a parameterized INSERT / UPDATE.

        JSON fields are serialized to JSON text; malformed values raise
        ValidationError before anything reaches the database.
        """
        row: dict[str, Any] = {
            "scheme_code": self.scheme_code,
            "official_name": self.official_name,
            "description": self.description,
            "category": self.category,
            "state": self.state,
            "application_start_date": self.application_start_date,
            "application_end_date": self.application_end_date,
            "official_application_url": self.official_application_url,
            "source_id": self.source_id,
            "verification_status": self.verification_status,
            "last_verified_at": self.last_verified_at,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        for name in SCHEME_JSON_FIELDS:
            row[name] = dumps_json_field(getattr(self, name), name)
        return row

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Scheme":
        """Build a Scheme from a database row, parsing the JSON fields."""
        data = dict(row)
        json_values = {
            name: loads_json_field(data.get(name), name) for name in SCHEME_JSON_FIELDS
        }
        return cls(
            id=data.get("id"),
            scheme_code=data.get("scheme_code"),
            official_name=data.get("official_name"),
            description=data.get("description"),
            category=data.get("category"),
            state=data.get("state"),
            application_start_date=data.get("application_start_date"),
            application_end_date=data.get("application_end_date"),
            official_application_url=data.get("official_application_url"),
            source_id=data.get("source_id"),
            verification_status=data.get("verification_status"),
            last_verified_at=data.get("last_verified_at"),
            status=data.get("status") or "pending",
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            **json_values,
        )


@dataclass
class SyncLog:
    """A row of ``sync_logs``: one synchronization attempt."""

    id: int | None = None
    source_id: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    status: str | None = None
    new_records: int = 0
    updated_records: int = 0
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.new_records < 0 or self.updated_records < 0:
            raise ValidationError("Record counts in a sync log must not be negative")
        # A new sync log starts now, unless an existing record's
        # started_at was supplied (for example by from_row).
        if self.started_at is None:
            self.started_at = utc_now_iso()

    def to_row(self) -> dict[str, Any]:
        """Return a dict ready for a parameterized INSERT / UPDATE."""
        return {
            "source_id": self.source_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "new_records": self.new_records,
            "updated_records": self.updated_records,
            "error_message": self.error_message,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SyncLog":
        """Build a SyncLog from a database row."""
        data = dict(row)
        return cls(
            id=data.get("id"),
            source_id=data.get("source_id"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            status=data.get("status"),
            new_records=data.get("new_records") or 0,
            updated_records=data.get("updated_records") or 0,
            error_message=data.get("error_message"),
        )
