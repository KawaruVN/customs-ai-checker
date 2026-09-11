from datetime import datetime, timezone
import hashlib
import sqlite3

import pytest

from customs_ai.config import settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories.database import init_db
from customs_ai.repositories.source_documents import SourceDocumentRepository


def dummy_document(document_id="DOC-1", shipment_id="SHP-1", seed=b"one"):
    return SourceDocument(
        document_id=document_id,
        shipment_id=shipment_id,
        original_filename="synthetic.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=hashlib.sha256(seed).hexdigest(),
        file_size=len(seed),
        stored_path="synthetic/original.pdf",
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.UPLOADED,
    )


def test_create_and_get_by_document_id():
    repository = SourceDocumentRepository()
    document = dummy_document()
    repository.create(document)

    fetched = repository.get_by_document_id(document.document_id)

    assert fetched is not None
    assert fetched.document_id == document.document_id
    assert fetched.shipment_id == document.shipment_id
    assert fetched.file_hash == document.file_hash
    assert fetched.upload_time.tzinfo is not None
    assert fetched.upload_time.utcoffset().total_seconds() == 0
    assert fetched.detected_document_type is None
    assert fetched.classification_confidence is None
    assert fetched.page_count is None
    assert fetched.sheet_count is None
    assert fetched.parser_used is None
    assert fetched.extraction_status is None


def test_find_by_shipment_and_hash():
    repository = SourceDocumentRepository()
    document = dummy_document()
    repository.create(document)
    fetched = repository.find_by_shipment_and_hash(document.shipment_id, document.file_hash)
    assert fetched is not None
    assert fetched.document_id == document.document_id


def test_unique_shipment_hash_constraint():
    repository = SourceDocumentRepository()
    first = dummy_document("DOC-1", "SHP-1", b"same")
    second = dummy_document("DOC-2", "SHP-1", b"same")
    repository.create(first)

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(second)


def test_same_hash_different_shipment_allowed():
    repository = SourceDocumentRepository()
    repository.create(dummy_document("DOC-1", "SHP-1", b"same"))
    repository.create(dummy_document("DOC-2", "SHP-2", b"same"))
    assert repository.get_by_document_id("DOC-1") is not None
    assert repository.get_by_document_id("DOC-2") is not None


def test_persistence_survives_repository_recreation():
    first_repository = SourceDocumentRepository()
    document = dummy_document()
    first_repository.create(document)

    second_repository = SourceDocumentRepository()
    fetched = second_repository.get_by_document_id(document.document_id)
    assert fetched is not None
    assert fetched.file_hash == document.file_hash


def test_init_db_failure_propagates(monkeypatch, tmp_path):
    db_path_that_is_directory = tmp_path / "app.db"
    db_path_that_is_directory.mkdir()
    monkeypatch.setattr(settings, "db_path", db_path_that_is_directory)

    with pytest.raises(sqlite3.OperationalError):
        init_db()
