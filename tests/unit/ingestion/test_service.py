import asyncio
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import sqlite3

from fastapi import UploadFile
import pytest

from customs_ai.config import settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.errors import (
    FileEmptyError,
    FileInvalidContentError,
    FileTooLargeError,
    IngestionError,
    InvalidShipmentIdError,
)
from customs_ai.ingestion.models import SourceDocument
from customs_ai.ingestion.service import IngestionService
from customs_ai.repositories.source_documents import SourceDocumentRepository


def run(coro):
    return asyncio.run(coro)


def upload(filename: str, content: bytes, content_type: str | None = None) -> UploadFile:
    headers = None
    if content_type is not None:
        from starlette.datastructures import Headers
        headers = Headers({"content-type": content_type})
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=headers)


@pytest.fixture
def service():
    return IngestionService(SourceDocumentRepository())


def valid_pdf(payload: bytes = b"synthetic") -> bytes:
    return b"%PDF-1.7\n" + payload


def test_sanitize_filename_cross_platform_and_unicode(service):
    assert service._sanitize_filename("../../invoice.pdf") == "invoice.pdf"
    assert service._sanitize_filename(r"C:\temp\invoice.pdf") == "invoice.pdf"
    assert service._sanitize_filename("hóa_đơn_北京.pdf") == "hóa_đơn_北京.pdf"


def test_validate_shipment_id(service):
    service._validate_shipment_id("SHP-2026_001")
    for invalid in ("../SHP", r"..\SHP", "/SHP", r"C:\SHP", "SHP!001", ""):
        with pytest.raises(InvalidShipmentIdError):
            service._validate_shipment_id(invalid)


def test_empty_file_rejected_and_temp_cleaned(service):
    with pytest.raises(FileEmptyError):
        run(service.ingest("SHP1", upload("empty.pdf", b"")))
    assert not list(settings.upload_root.glob("ingest_*"))


def test_exact_size_limit_accepted(service, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    prefix = b"%PDF-1.7\n"
    content = prefix + b"A" * (1024 * 1024 - len(prefix))

    response, status = run(service.ingest("SHP-LIMIT", upload("exact.pdf", content)))

    assert status == 201
    assert response.file_size == 1024 * 1024
    assert (settings.upload_root / "SHP-LIMIT" / response.document_id / "original.pdf").exists()


def test_one_byte_over_limit_rejected_without_artifacts_or_db_row(service, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    prefix = b"%PDF-1.7\n"
    content = prefix + b"A" * (1024 * 1024 + 1 - len(prefix))

    with pytest.raises(FileTooLargeError):
        run(service.ingest("SHP-OVER", upload("over.pdf", content)))

    assert not list(settings.upload_root.glob("ingest_*"))
    assert not (settings.upload_root / "SHP-OVER").exists()
    assert service.repo.find_by_shipment_and_hash(
        "SHP-OVER", hashlib.sha256(content).hexdigest()
    ) is None


def test_hash_correctness_and_generated_document_id(service):
    content = valid_pdf(b"hash-test")
    expected = hashlib.sha256(content).hexdigest()

    response, status = run(service.ingest("SHP-HASH", upload("customer_invoice.pdf", content)))

    assert status == 201
    assert response.sha256 == expected
    assert response.document_id.startswith("DOC-")
    assert "customer_invoice" not in response.document_id


def test_invalid_content_rejection_cleans_temp(service):
    with pytest.raises(FileInvalidContentError):
        run(service.ingest("SHP-BAD", upload("bad.pdf", b"plain text")))
    assert not list(settings.upload_root.glob("ingest_*"))
    assert not (settings.upload_root / "SHP-BAD").exists()


def test_current_request_content_is_validated_before_duplicate(service):
    content = valid_pdf(b"same-bytes")
    first, _ = run(service.ingest("SHP-DUP", upload("first.pdf", content)))

    with pytest.raises(FileInvalidContentError):
        run(service.ingest("SHP-DUP", upload("renamed.csv", content, "text/csv")))

    stored = service.repo.get_by_document_id(first.document_id)
    assert stored is not None


def test_same_filename_different_content_creates_new_document(service):
    first, _ = run(service.ingest("SHP-SAME-NAME", upload("invoice.pdf", valid_pdf(b"one"))))
    second, _ = run(service.ingest("SHP-SAME-NAME", upload("invoice.pdf", valid_pdf(b"two"))))
    assert second.document_id != first.document_id
    assert second.is_duplicate is False


def test_different_filename_same_content_is_duplicate(service):
    content = valid_pdf(b"same")
    first, _ = run(service.ingest("SHP-SAME", upload("a.pdf", content)))
    second, status = run(service.ingest("SHP-SAME", upload("b.pdf", content)))
    assert status == 200
    assert second.is_duplicate is True
    assert second.document_id == first.document_id


def test_same_hash_different_shipment_creates_new_document(service):
    content = valid_pdf(b"cross-shipment")
    first, _ = run(service.ingest("SHP-A", upload("a.pdf", content)))
    second, status = run(service.ingest("SHP-B", upload("b.pdf", content)))
    assert status == 201
    assert second.document_id != first.document_id


def test_generic_repository_failure_cleans_final_file_and_doc_dir(service, monkeypatch):
    monkeypatch.setattr(service.repo, "create", lambda document: (_ for _ in ()).throw(RuntimeError("db down")))

    with pytest.raises(IngestionError) as exc:
        run(service.ingest("SHP-DBFAIL", upload("fail.pdf", valid_pdf(b"db-fail"))))

    assert exc.value.code == "INGESTION_FAILED"
    assert exc.value.http_status == 500
    assert not list(settings.upload_root.rglob("original.*"))
    shipment_dir = settings.upload_root / "SHP-DBFAIL"
    assert not shipment_dir.exists() or not list(shipment_dir.glob("DOC-*"))


def test_storage_finalization_failure_creates_no_db_row(service, monkeypatch):
    import customs_ai.ingestion.service as service_module

    content = valid_pdf(b"move-fail")
    file_hash = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(service_module.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("move failed")))

    with pytest.raises(IngestionError) as exc:
        run(service.ingest("SHP-MOVEFAIL", upload("fail.pdf", content)))

    assert exc.value.http_status == 500
    assert service.repo.find_by_shipment_and_hash("SHP-MOVEFAIL", file_hash) is None
    assert not list(settings.upload_root.glob("ingest_*"))
    shipment_dir = settings.upload_root / "SHP-MOVEFAIL"
    assert not shipment_dir.exists() or not list(shipment_dir.glob("DOC-*"))


def test_unique_race_returns_winner_and_removes_loser_artifact(service, monkeypatch):
    content = valid_pdf(b"race")
    expected_hash = hashlib.sha256(content).hexdigest()
    calls = {"find": 0}

    winner = SourceDocument(
        document_id="DOC-WINNER",
        shipment_id="SHP-RACE",
        original_filename="winner.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=expected_hash,
        file_size=len(content),
        stored_path="winner/original.pdf",
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.UPLOADED,
    )

    def fake_find(shipment_id, file_hash):
        calls["find"] += 1
        return None if calls["find"] == 1 else winner

    monkeypatch.setattr(service.repo, "find_by_shipment_and_hash", fake_find)
    monkeypatch.setattr(service.repo, "create", lambda document: (_ for _ in ()).throw(sqlite3.IntegrityError("race")))

    response, status = run(service.ingest("SHP-RACE", upload("race.pdf", content)))

    assert status == 200
    assert response.is_duplicate is True
    assert response.document_id == "DOC-WINNER"
    assert not list(settings.upload_root.rglob("original.*"))


def test_new_source_document_metadata_is_complete_and_downstream_fields_none(service):
    content = valid_pdf(b"metadata")
    response, _ = run(service.ingest("SHP-META", upload("meta.pdf", content)))
    document = service.repo.get_by_document_id(response.document_id)

    assert document is not None
    assert document.shipment_id == "SHP-META"
    assert document.original_filename == "meta.pdf"
    assert document.file_type == "pdf"
    assert document.mime_type == "application/pdf"
    assert document.file_hash == hashlib.sha256(content).hexdigest()
    assert document.file_size == len(content)
    assert document.upload_time.tzinfo is not None
    assert document.upload_time.utcoffset().total_seconds() == 0
    assert document.processing_status == ProcessingStatus.UPLOADED
    assert document.detected_document_type is None
    assert document.classification_confidence is None
    assert document.page_count is None
    assert document.sheet_count is None
    assert document.parser_used is None
    assert document.extraction_status is None
