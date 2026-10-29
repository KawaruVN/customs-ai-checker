from contextlib import closing
from datetime import datetime, timezone
import sqlite3

import pytest

from customs_ai.config import settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories import database
from customs_ai.repositories.database import get_connection, init_db
from customs_ai.repositories.source_documents import SourceDocumentRepository


def _document(document_id="DOC-SCHEMA"):
    return SourceDocument(
        document_id=document_id,
        shipment_id="SHP-SCHEMA",
        original_filename="synthetic.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash="a" * 64,
        file_size=9,
        stored_path="synthetic/source.pdf",
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.CLASSIFIED,
    )


def _insert(connection, extraction_id="EXT-1", document_id="DOC-SCHEMA", **changes):
    row = {
        "attempt_number": 1,
        "status": "EXTRACTED",
        "is_active": 1,
        "schema_version": "0.1",
        "supersedes_extraction_id": None,
    } | changes
    connection.execute(
        """INSERT INTO document_extractions (
            extraction_id, document_id, attempt_number, payload_json,
            status, is_active, created_at, schema_version, extraction_method,
            source_file_hash, supersedes_extraction_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            extraction_id, document_id, row["attempt_number"], "{}",
            row["status"], row["is_active"], "2026-10-28T00:00:00+00:00",
            row["schema_version"], "synthetic", "a" * 64,
            row["supersedes_extraction_id"],
        ),
    )


def test_fresh_database_has_extraction_table_and_foreign_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", tmp_path / "fresh" / "app.db")
    init_db()
    with closing(get_connection()) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        columns = {row[1] for row in connection.execute("PRAGMA table_info(document_extractions)")}
        assert columns == {
            "extraction_id", "document_id", "attempt_number", "payload_json", "status",
            "is_active", "created_at", "schema_version", "extraction_method",
            "source_file_hash", "supersedes_extraction_id",
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_existing_database_rows_and_columns_survive_idempotent_initialization(monkeypatch, tmp_path):
    path = tmp_path / "legacy.db"
    monkeypatch.setattr(settings, "db_path", path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE source_documents (document_id TEXT PRIMARY KEY, legacy_note TEXT)")
        connection.execute("INSERT INTO source_documents VALUES (?, ?)", ("DOC-LEGACY", "synthetic legacy evidence"))
    init_db()
    init_db()
    with closing(get_connection()) as connection:
        row = connection.execute("SELECT * FROM source_documents").fetchone()
        assert dict(row) == {"document_id": "DOC-LEGACY", "legacy_note": "synthetic legacy evidence"}
        assert connection.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0] == 0
        _insert(connection, document_id="DOC-LEGACY")
        connection.commit()
    init_db()
    with closing(get_connection()) as connection:
        assert connection.execute("SELECT extraction_id FROM document_extractions").fetchone()[0] == "EXT-1"


def test_orphan_extraction_is_rejected_by_database():
    with closing(get_connection()) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError):
            _insert(connection, document_id="MISSING")
        assert connection.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0] == 0


def test_active_partial_unique_index_allows_history_and_separate_documents():
    repository = SourceDocumentRepository()
    repository.create(_document())
    other = _document("DOC-OTHER").model_copy(update={"file_hash": "b" * 64})
    repository.create(other)
    with closing(get_connection()) as connection, connection:
        _insert(connection)
        with pytest.raises(sqlite3.IntegrityError):
            _insert(connection, "EXT-DUPLICATE", attempt_number=2)
        _insert(connection, "EXT-HISTORY", attempt_number=2, is_active=0)
        _insert(connection, "EXT-OTHER", document_id="DOC-OTHER")
        active = connection.execute("SELECT document_id FROM document_extractions WHERE is_active = 1 ORDER BY document_id").fetchall()
        assert [row[0] for row in active] == ["DOC-OTHER", "DOC-SCHEMA"]


@pytest.mark.parametrize("changes", [
    {"status": "PASS"},
    {"status": "FAILED", "is_active": 1},
    {"is_active": 2},
    {"attempt_number": 0},
    {"schema_version": "9.9"},
    {"supersedes_extraction_id": "MISSING"},
])
def test_invalid_extraction_metadata_is_rejected_by_database(changes):
    SourceDocumentRepository().create(_document())
    with closing(get_connection()) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError):
            _insert(connection, **changes)
        assert connection.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0] == 0


def test_database_preserves_referenced_source_document_and_history():
    SourceDocumentRepository().create(_document())
    with closing(get_connection()) as connection, connection:
        _insert(connection, is_active=0)
        _insert(connection, "EXT-2", attempt_number=2, supersedes_extraction_id="EXT-1")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM source_documents WHERE document_id = ?", ("DOC-SCHEMA",))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM document_extractions WHERE extraction_id = ?", ("EXT-1",))
        assert connection.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0] == 2


class _TrackingConnection(sqlite3.Connection):
    closed = False
    fail_on = None

    def execute(self, sql, parameters=()):
        if self.fail_on and self.fail_on in sql:
            raise sqlite3.OperationalError("Synthetic SQLite failure")
        return super().execute(sql, parameters)

    def close(self):
        self.closed = True
        return super().close()


def _track_connections(monkeypatch, fail_on=None):
    original_connect = sqlite3.connect
    connections = []

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs, factory=_TrackingConnection)
        connection.fail_on = fail_on
        connections.append(connection)
        return connection

    monkeypatch.setattr(database.sqlite3, "connect", connect)
    return connections


def test_schema_initialization_rolls_back_all_ddl_and_closes_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", tmp_path / "broken_init.db")
    connections = _track_connections(monkeypatch, "CREATE UNIQUE INDEX")
    with pytest.raises(sqlite3.OperationalError, match="Synthetic SQLite failure"):
        init_db()
    assert len(connections) == 1 and connections[0].closed
    with closing(get_connection()) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == []


def test_connection_configuration_failure_closes_the_connection(monkeypatch):
    connections = _track_connections(monkeypatch, "PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.OperationalError, match="Synthetic SQLite failure"):
        get_connection()
    assert len(connections) == 1 and connections[0].closed


def test_init_and_source_repository_close_every_connection_on_success_and_failure(monkeypatch):
    connections = _track_connections(monkeypatch)
    init_db()
    repository = SourceDocumentRepository()
    document = _document()
    repository.create(document)
    with pytest.raises(sqlite3.IntegrityError):
        repository.create(document)
    assert repository.get_by_document_id(document.document_id) is not None
    assert repository.find_by_shipment_and_hash(document.shipment_id, document.file_hash) is not None
    repository.update_parsing_metadata(document.document_id, ProcessingStatus.PARSED, "synthetic", 1, None)
    repository.update_classification_metadata(document.document_id, "COMMERCIAL_INVOICE", 1.0, ProcessingStatus.CLASSIFIED)
    with pytest.raises(LookupError):
        repository.update_parsing_metadata("MISSING", ProcessingStatus.PARSED, "synthetic", 1, None)
    with pytest.raises(LookupError):
        repository.update_classification_metadata("MISSING", "COMMERCIAL_INVOICE", 1.0, ProcessingStatus.CLASSIFIED)
    assert len(connections) == 9
    assert all(connection.closed for connection in connections)
