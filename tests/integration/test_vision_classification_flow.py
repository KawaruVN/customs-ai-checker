from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.service import DocumentClassificationService
from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.parsers.models import ParsedPdfDocument, ParsedPdfPage
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.models import ProviderTextResult
from customs_ai.vision.service import VisualResolutionService


class Parsing:
    def __init__(self, parsed): self.parsed = parsed
    def parse_document(self, document_id): return self.parsed


class Provider:
    def __init__(self, text): self.text = text
    def process(self, image): return ProviderTextResult(provider="mock", text=self.text, confidence=0.99)


class Renderer:
    def render_page(self, path, index): return Image.new("RGB", (20, 20), "white")


def _seed(repo, path, doc_id):
    repo.create(SourceDocument(
        document_id=doc_id,
        shipment_id="SHP-V",
        original_filename="scan.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=doc_id,
        file_size=path.stat().st_size,
        stored_path=str(path),
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.PARSED,
    ))


def _service(tmp_path, monkeypatch, vlm_text, ocr_text):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    monkeypatch.setattr(settings, "upload_root", upload_root)
    path = upload_root / "scan.pdf"
    path.write_bytes(b"%PDF-mock")
    repo = SourceDocumentRepository()
    _seed(repo, path, "DOC-V")
    parsed = ParsedPdfDocument(
        document_id="DOC-V", page_count=1, has_text_layer=False, needs_ocr=True,
        pages=[ParsedPdfPage(page=1, text="")],
    )
    cfg = VisionSettingsConfig(
        enabled=True,
        min_meaningful_chars=3,
        min_meaningful_ratio=0.3,
        min_soft_text_overlap=0.2,
    )
    vision = VisualResolutionService(
        repo, Provider(vlm_text), Provider(ocr_text), config=cfg, renderer=Renderer()
    )
    classifier = DeterministicClassifier(load_classification_config())
    return repo, DocumentClassificationService(repo, Parsing(parsed), classifier, vision)


def test_safe_scanned_invoice_classifies_as_invoice(tmp_path, monkeypatch):
    text = "COMMERCIAL INVOICE INV-001 TOTAL AMOUNT 1200.50"
    repo, service = _service(tmp_path, monkeypatch, text, text)
    result = service.classify_document("DOC-V")
    assert result.document_type == DocumentType.COMMERCIAL_INVOICE
    assert repo.get_by_document_id("DOC-V").processing_status == ProcessingStatus.CLASSIFIED


def test_visual_conflict_forces_unknown_and_needs_review(tmp_path, monkeypatch):
    repo, service = _service(
        tmp_path,
        monkeypatch,
        "COMMERCIAL INVOICE INV-001 TOTAL 12500",
        "PACKING LIST INV-001 TOTAL 125000",
    )
    result = service.classify_document("DOC-V")
    assert result.document_type == DocumentType.UNKNOWN
    assert repo.get_by_document_id("DOC-V").processing_status == ProcessingStatus.NEEDS_REVIEW
