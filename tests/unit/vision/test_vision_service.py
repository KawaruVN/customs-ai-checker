from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.parsers.models import ParsedPdfDocument, ParsedPdfPage, ParsedWorkbook
from customs_ai.vision.enums import TextResolutionSource
from customs_ai.vision.models import ProviderTextResult
from customs_ai.vision.service import VisualResolutionService


class Repo:
    def __init__(self, path: Path):
        self.doc = SourceDocument(
            document_id="DOC-1",
            shipment_id="SHP-1",
            original_filename="scan.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_hash="x",
            file_size=path.stat().st_size,
            stored_path=str(path),
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
        )
    def get_by_document_id(self, document_id):
        return self.doc


class Provider:
    def __init__(self, text, confidence=0.99):
        self.text = text
        self.confidence = confidence
        self.images = []
    def process(self, image):
        self.images.append(image)
        return ProviderTextResult(provider="mock", text=self.text, confidence=self.confidence)


class Renderer:
    def __init__(self):
        self.calls = []
        self.image = Image.new("RGB", (10, 10), "white")
    def render_page(self, path, index):
        self.calls.append((path, index))
        return self.image


def _setup(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    monkeypatch.setattr(settings, "upload_root", upload_root)
    pdf = upload_root / "scan.pdf"
    pdf.write_bytes(b"%PDF-mock")
    return pdf


def _service(tmp_path, monkeypatch, vlm_text="COMMERCIAL INVOICE INV-001", ocr_text=None):
    pdf = _setup(tmp_path, monkeypatch)
    cfg = VisionSettingsConfig(
        enabled=True,
        min_meaningful_chars=3,
        min_meaningful_ratio=0.3,
        min_soft_text_overlap=0.2,
    )
    vlm = Provider(vlm_text)
    ocr = Provider(ocr_text if ocr_text is not None else vlm_text)
    renderer = Renderer()
    service = VisualResolutionService(Repo(pdf), vlm, ocr, config=cfg, renderer=renderer)
    return service, renderer, vlm, ocr


def test_clean_native_page_bypasses_renderer_and_providers(tmp_path, monkeypatch):
    service, renderer, vlm, ocr = _service(tmp_path, monkeypatch)
    parsed = ParsedPdfDocument(
        document_id="DOC-1", page_count=1, has_text_layer=True, needs_ocr=False,
        pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE INV-001")],
    )
    result = service.resolve_document("DOC-1", parsed)
    assert result.pages[0].source == TextResolutionSource.TEXT_LAYER
    assert renderer.calls == []
    assert vlm.images == []
    assert ocr.images == []


def test_visual_page_renders_once_and_reuses_same_image_for_both(tmp_path, monkeypatch):
    service, renderer, vlm, ocr = _service(tmp_path, monkeypatch)
    parsed = ParsedPdfDocument(
        document_id="DOC-1", page_count=1, has_text_layer=False, needs_ocr=True,
        pages=[ParsedPdfPage(page=1, text="")],
    )
    result = service.resolve_document("DOC-1", parsed)
    assert len(renderer.calls) == 1
    assert vlm.images[0] is renderer.image
    assert ocr.images[0] is renderer.image
    assert result.pages[0].source == TextResolutionSource.CROSS_VERIFIED_VISUAL


def test_mixed_pdf_only_bad_page_uses_visual_path(tmp_path, monkeypatch):
    service, renderer, vlm, ocr = _service(tmp_path, monkeypatch)
    parsed = ParsedPdfDocument(
        document_id="DOC-1", page_count=2, has_text_layer=True, needs_ocr=False,
        pages=[
            ParsedPdfPage(page=1, text="COMMERCIAL INVOICE INV-001"),
            ParsedPdfPage(page=2, text=""),
        ],
    )
    result = service.resolve_document("DOC-1", parsed)
    assert result.visual_pages == [2]
    assert [p.page for p in result.pages] == [1, 2]
    assert len(renderer.calls) == 1


def test_provider_conflict_marks_document_for_review(tmp_path, monkeypatch):
    service, _, _, _ = _service(
        tmp_path, monkeypatch,
        vlm_text="COMMERCIAL INVOICE INV-001 total 12500",
        ocr_text="PACKING LIST INV-001 total 125000",
    )
    parsed = ParsedPdfDocument(
        document_id="DOC-1", page_count=1, has_text_layer=False, needs_ocr=True,
        pages=[ParsedPdfPage(page=1, text="")],
    )
    result = service.resolve_document("DOC-1", parsed)
    assert result.requires_review
    assert result.unresolved_pages == [1]
    assert result.pages[0].source == TextResolutionSource.UNRESOLVED


def test_excel_bypasses_visual_path(tmp_path, monkeypatch):
    service, renderer, vlm, ocr = _service(tmp_path, monkeypatch)
    workbook = ParsedWorkbook(
        document_id="DOC-X", file_type="xlsx", parser_used="openpyxl",
        workbook_name="x.xlsx", sheet_count=0, sheets=[],
    )
    assert service.resolve_document("DOC-1", workbook) is workbook
    assert renderer.calls == [] and vlm.images == [] and ocr.images == []
