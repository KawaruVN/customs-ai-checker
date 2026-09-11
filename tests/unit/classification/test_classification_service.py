import hashlib
from datetime import datetime, timezone

import pytest

from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.errors import ClassificationFailedError
from customs_ai.classification.service import DocumentClassificationService
from customs_ai.config import settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.parsers.models import ParsedPdfDocument, ParsedPdfPage
from customs_ai.repositories.source_documents import SourceDocumentRepository


class MockParsingService(DocumentParsingService):
    def __init__(self, mock_doc):
        self.mock_doc = mock_doc

    def parse_document(self, document_id: str):
        if not self.mock_doc:
            raise Exception("Parsing failed")
        return self.mock_doc


@pytest.fixture
def service():
    repo = SourceDocumentRepository()
    classifier = DeterministicClassifier(load_classification_config())
    return repo, classifier


def _seed_db(repo, doc_id="DOC-1"):
    doc = SourceDocument(
        document_id=doc_id,
        shipment_id="SHP-1",
        original_filename="test.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash="hash",
        file_size=100,
        stored_path="/dev/null",
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.PARSED,
        parser_used="pypdf",
        page_count=5
    )
    repo.create(doc)


def test_missing_source_document(service):
    repo, classifier = service
    classification_svc = DocumentClassificationService(repo, MockParsingService(None), classifier)
    with pytest.raises(ClassificationFailedError) as exc:
        classification_svc.classify_document("DOC-MISSING")
    assert "not found" in str(exc.value)


def test_parser_failure_prevents_classification(service):
    repo, classifier = service
    _seed_db(repo, "DOC-FAIL")
    classification_svc = DocumentClassificationService(repo, MockParsingService(None), classifier)
    
    with pytest.raises(ClassificationFailedError):
        classification_svc.classify_document("DOC-FAIL")
        
    doc = repo.get_by_document_id("DOC-FAIL")
    assert doc.processing_status == ProcessingStatus.PARSED # Remains unchanged


def test_repository_update_failure(service, monkeypatch):
    repo, classifier = service
    _seed_db(repo, "DOC-DB-FAIL")
    parsed = ParsedPdfDocument(document_id="DOC-DB-FAIL", page_count=1, has_text_layer=True, needs_ocr=False, pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE")])
    classification_svc = DocumentClassificationService(repo, MockParsingService(parsed), classifier)

    monkeypatch.setattr(repo, "update_classification_metadata", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("DB Offline")))

    with pytest.raises(ClassificationFailedError):
        classification_svc.classify_document("DOC-DB-FAIL")

    # DB not updated
    doc = repo.get_by_document_id("DOC-DB-FAIL")
    assert doc.processing_status == ProcessingStatus.PARSED


def test_repeated_classification_idempotent(service):
    repo, classifier = service
    _seed_db(repo, "DOC-IDEM")
    parsed = ParsedPdfDocument(document_id="DOC-IDEM", page_count=1, has_text_layer=True, needs_ocr=False, pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE")])
    classification_svc = DocumentClassificationService(repo, MockParsingService(parsed), classifier)

    res1 = classification_svc.classify_document("DOC-IDEM")
    res2 = classification_svc.classify_document("DOC-IDEM")
    
    assert res1.document_type == res2.document_type
    assert res1.confidence == res2.confidence


def test_source_file_hash_unchanged(service, tmp_path):
    # Integration style check to ensure nothing touched the disk
    path = tmp_path / "test.pdf"
    path.write_bytes(b"immutable")
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    repo, classifier = service
    doc = SourceDocument(
        document_id="DOC-HASH", shipment_id="SHP-1", original_filename="test.pdf",
        file_type="pdf", mime_type="application/pdf", file_hash=original_hash,
        file_size=9, stored_path=str(path), upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.PARSED
    )
    repo.create(doc)

    parsed = ParsedPdfDocument(document_id="DOC-HASH", page_count=1, has_text_layer=True, needs_ocr=False, pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE")])
    classification_svc = DocumentClassificationService(repo, MockParsingService(parsed), classifier)
    
    classification_svc.classify_document("DOC-HASH")
    
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash


def test_parser_metadata_preserved(service):
    repo, classifier = service
    _seed_db(repo, "DOC-META")
    parsed = ParsedPdfDocument(document_id="DOC-META", page_count=5, has_text_layer=True, needs_ocr=False, pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE")])
    classification_svc = DocumentClassificationService(repo, MockParsingService(parsed), classifier)

    classification_svc.classify_document("DOC-META")
    
    doc = repo.get_by_document_id("DOC-META")
    assert doc.parser_used == "pypdf"
    assert doc.page_count == 5


def test_unknown_persists_as_needs_review(service):
    repo, classifier = service
    _seed_db(repo, "DOC-UNK")
    parsed = ParsedPdfDocument(document_id="DOC-UNK", page_count=1, has_text_layer=True, needs_ocr=False, pages=[ParsedPdfPage(page=1, text="random unknown text")])
    classification_svc = DocumentClassificationService(repo, MockParsingService(parsed), classifier)

    res = classification_svc.classify_document("DOC-UNK")
    
    assert res.document_type == DocumentType.UNKNOWN
    doc = repo.get_by_document_id("DOC-UNK")
    assert doc.processing_status == ProcessingStatus.NEEDS_REVIEW
    assert doc.detected_document_type == "UNKNOWN"
