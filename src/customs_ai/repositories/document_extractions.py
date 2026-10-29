"""Transactional extraction attempts; no extraction or application orchestration.

SourceDocument status describes the latest committed attempt. The active result
is retrieved explicitly and survives a FAILED replacement. Every write checks
the caller's source hash and processing state under the same SQLite writer lock.
"""

from contextlib import closing
from datetime import datetime, timezone
import sqlite3
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.extraction_models import (
    ExtractionAttempt,
    ExtractionRecord,
    ExtractionReplacement,
    deserialize_result,
    serialize_result,
)


class ExtractionPersistenceError(RuntimeError):
    """Safe repository failure; never contains source values or SQL parameters."""


class ExtractionValidationError(ExtractionPersistenceError):
    """An extraction input or identifier is invalid."""


class ExtractionConflictError(ExtractionPersistenceError):
    """An explicit replacement or source-state precondition was not met."""


class ExtractionNotFoundError(ExtractionPersistenceError):
    """The referenced SourceDocument no longer exists."""


class ExtractionCorruptionError(ExtractionPersistenceError):
    """Stored extraction content does not satisfy the persistence contract."""


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ExtractionValidationError("Invalid persistence identifier.")
    return value


def _snapshot(request, model):
    try:
        # Do not trust model_construct(), model_copy(update=...), or mutations
        # of nested approved models. Validate a detached Python-mode snapshot.
        data = request.model_dump(mode="python", warnings="error") if isinstance(request, BaseModel) else request
        return model.model_validate(data)
    except (ValidationError, ValueError, TypeError):
        raise ExtractionValidationError("Invalid extraction attempt.") from None


def _record(row: sqlite3.Row) -> ExtractionRecord:
    try:
        values = dict(row)
        if type(values["is_active"]) is not int or values["is_active"] not in (0, 1):
            raise ValueError("Invalid active flag")
        values["is_active"] = bool(values["is_active"])
        values["result"] = deserialize_result(values.pop("payload_json"))
        return ExtractionRecord.model_validate(values)
    except (ValidationError, ValueError, TypeError, KeyError):
        raise ExtractionCorruptionError("Stored extraction is invalid.") from None


class DocumentExtractionRepository:
    """Append-only history with explicit, optimistic active replacement.

    save_attempt is eligible only when no active row exists (including retry
    after an initial FAILED attempt). replace_active requires the exact current
    active ID, even after NEEDS_REVIEW. No implicit overwrite or history deletion.
    """

    def save_attempt(self, attempt: ExtractionAttempt) -> ExtractionRecord:
        return self._save(_snapshot(attempt, ExtractionAttempt), None)

    def replace_active(self, replacement: ExtractionReplacement) -> ExtractionRecord:
        validated = _snapshot(replacement, ExtractionReplacement)
        return self._save(validated, validated.expected_active_extraction_id)

    def _save(
        self, attempt: ExtractionAttempt, expected_active_id: str | None,
    ) -> ExtractionRecord:
        try:
            payload_json = serialize_result(attempt.result)
        except (ValidationError, ValueError, TypeError):
            raise ExtractionValidationError("Invalid extraction payload.") from None

        try:
            with closing(get_connection()) as connection:
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    row = connection.execute(
                        "SELECT * FROM source_documents WHERE document_id = ?",
                        (attempt.document_id,),
                    ).fetchone()
                    if row is None:
                        raise ExtractionNotFoundError("SourceDocument not found.")
                    try:
                        source = SourceDocument.model_validate(dict(row))
                    except ValidationError:
                        raise ExtractionConflictError("SourceDocument metadata is invalid.") from None
                    if (
                        source.file_hash != attempt.source_file_hash
                        or source.processing_status != attempt.expected_processing_status
                    ):
                        raise ExtractionConflictError("SourceDocument changed before extraction save.")

                    active_row = connection.execute(
                        "SELECT * FROM document_extractions WHERE document_id = ? AND is_active = 1",
                        (attempt.document_id,),
                    ).fetchone()
                    active = _record(active_row) if active_row else None
                    if expected_active_id is None and active is not None:
                        raise ExtractionConflictError("An active extraction requires explicit replacement.")
                    if expected_active_id is not None and (
                        active is None or active.extraction_id != expected_active_id
                    ):
                        raise ExtractionConflictError("The expected active extraction is stale or missing.")

                    sequence = connection.execute(
                        "SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM document_extractions WHERE document_id = ?",
                        (attempt.document_id,),
                    ).fetchone()[0]
                    activates = attempt.result.status != ExtractionStatus.FAILED
                    saved = ExtractionRecord(
                        extraction_id=str(uuid4()),
                        document_id=attempt.document_id,
                        attempt_number=sequence,
                        result=attempt.result,
                        status=attempt.result.status,
                        is_active=activates,
                        created_at=datetime.now(timezone.utc),
                        schema_version=attempt.schema_version,
                        extraction_method=attempt.extraction_method,
                        source_file_hash=attempt.source_file_hash,
                        supersedes_extraction_id=active.extraction_id if active and activates else None,
                    )
                    if active is not None and activates:
                        cursor = connection.execute(
                            "UPDATE document_extractions SET is_active = 0 WHERE extraction_id = ? AND document_id = ? AND is_active = 1",
                            (active.extraction_id, attempt.document_id),
                        )
                        if cursor.rowcount != 1:
                            raise ExtractionConflictError("Active extraction changed during replacement.")
                    cursor = connection.execute(
                        """INSERT INTO document_extractions (
                            extraction_id, document_id, attempt_number, payload_json,
                            status, is_active, created_at, schema_version,
                            extraction_method, source_file_hash, supersedes_extraction_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            saved.extraction_id, saved.document_id, saved.attempt_number,
                            payload_json, saved.status.value, int(saved.is_active),
                            saved.created_at.isoformat(), saved.schema_version,
                            saved.extraction_method, saved.source_file_hash,
                            saved.supersedes_extraction_id,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise ExtractionPersistenceError("Extraction attempt was not inserted.")
                    cursor = connection.execute(
                        """UPDATE source_documents
                        SET processing_status = ?, extraction_status = ?
                        WHERE document_id = ? AND file_hash = ? AND processing_status = ?""",
                        (
                            saved.status.value, saved.status.value, saved.document_id,
                            attempt.source_file_hash, attempt.expected_processing_status.value,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise ExtractionConflictError("SourceDocument changed during metadata update.")
                    connection.commit()
                    return saved
                except BaseException:
                    connection.rollback()
                    raise
        except sqlite3.IntegrityError:
            raise ExtractionConflictError("Extraction persistence constraint conflict.") from None
        except (sqlite3.Error, OSError):
            raise ExtractionPersistenceError("Extraction persistence operation failed.") from None
        except (ValidationError, ValueError, TypeError):
            raise ExtractionValidationError("Invalid extraction record.") from None

    def get_by_extraction_id(self, extraction_id: str) -> ExtractionRecord | None:
        extraction_id = _identifier(extraction_id)
        try:
            with closing(get_connection()) as connection:
                row = connection.execute(
                    "SELECT * FROM document_extractions WHERE extraction_id = ?",
                    (extraction_id,),
                ).fetchone()
                return _record(row) if row else None
        except (sqlite3.Error, OSError):
            raise ExtractionPersistenceError("Extraction read failed.") from None

    def get_active(self, document_id: str) -> ExtractionRecord | None:
        document_id = _identifier(document_id)
        try:
            with closing(get_connection()) as connection:
                row = connection.execute(
                    "SELECT * FROM document_extractions WHERE document_id = ? AND is_active = 1",
                    (document_id,),
                ).fetchone()
                return _record(row) if row else None
        except (sqlite3.Error, OSError):
            raise ExtractionPersistenceError("Active extraction read failed.") from None

    def list_history(self, document_id: str) -> list[ExtractionRecord]:
        document_id = _identifier(document_id)
        try:
            with closing(get_connection()) as connection:
                rows = connection.execute(
                    "SELECT * FROM document_extractions WHERE document_id = ? ORDER BY attempt_number ASC",
                    (document_id,),
                ).fetchall()
                return [_record(row) for row in rows]
        except (sqlite3.Error, OSError):
            raise ExtractionPersistenceError("Extraction history read failed.") from None
