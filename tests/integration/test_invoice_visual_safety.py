"""Production invoice factories with real 005A reconciliation and local doubles."""

from datetime import date
from decimal import Decimal
from hashlib import sha256

from PIL import Image
import pytest

import customs_ai.application.composition as composition
from customs_ai.classification.enums import DocumentType
from customs_ai.config import VisionSettingsConfig
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.semantic import SemanticInvoiceResponse
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.document_extractions import DocumentExtractionRepository
from customs_ai.vision.models import ProviderTextResult
from customs_ai.vision.service import VisualResolutionService


SAFE_TEXT = (
    "COMMERCIAL INVOICE\nINVOICE NO: 0000789\nINVOICE DATE: 2026-10-29\n"
    "TOTAL AMOUNT: 125.50\nSELLER: Synthetic Visual Exporter"
)


class SemanticSpy:
    def __init__(self):
        self.calls = 0

    def extract(self, request):
        self.calls += 1
        return SemanticInvoiceResponse(document_id=request.document_id, candidates=[])


class LocalProvider:
    def __init__(self, name):
        self.name = name
        self.calls = []
        self.text = SAFE_TEXT
        self.confidence = 0.99
        self.failed_pages = set()

    def process(self, image):
        page = image.info["synthetic_page"]
        self.calls.append(page)
        if page in self.failed_pages:
            raise RuntimeError("SYNTHETIC_PRIVATE_VISUAL_EXCEPTION")
        return ProviderTextResult(provider=self.name, text=self.text, confidence=self.confidence)


class LocalRenderer:
    def __init__(self):
        self.calls = []

    def render_page(self, path, index):
        self.calls.append(index)
        image = Image.new("RGB", (12, 12), "white")
        image.info["synthetic_page"] = index + 1
        return image


class LocalVision:
    """Only renderer/provider I/O is doubled; quality and reconciler stay real."""

    def __init__(self):
        self.renderer = LocalRenderer()
        self.vlm = LocalProvider("synthetic-vlm")
        self.ocr = LocalProvider("synthetic-ocr")
        self.mutate_resolution = None

    def clear_calls(self):
        self.renderer.calls.clear()
        self.vlm.calls.clear()
        self.ocr.calls.clear()

    def factory(self, repository):
        real = VisualResolutionService(
            repository, self.vlm, self.ocr, config=VisionSettingsConfig(enabled=True),
            renderer=self.renderer,
        )
        owner = self

        class Resolution:
            def resolve_document(self, document_id, parsed):
                result = real.resolve_document(document_id, parsed)
                if owner.mutate_resolution is not None:
                    owner.mutate_resolution(result)
                return result

        return Resolution()


def classified_scan(pipeline, monkeypatch, *, pages=None):
    vision = LocalVision()
    monkeypatch.setattr(composition, "vision_service_factory", vision.factory)
    source = pipeline.register(pipeline.pdf([None] if pages is None else pages))
    before = sha256(pipeline.source_bytes(source.document_id)).hexdigest()
    classification = pipeline.classify(source.document_id)
    assert classification.document_type == DocumentType.COMMERCIAL_INVOICE
    assert pipeline.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.CLASSIFIED
    visual_indexes = [index for index, text in enumerate([None] if pages is None else pages) if not text]
    assert vision.renderer.calls == visual_indexes
    assert vision.vlm.calls == vision.ocr.calls == [index + 1 for index in visual_indexes]
    vision.clear_calls()
    return source, before, vision


def assert_unsafe_attempt(pipeline, source, before, semantic, outcome):
    assert outcome.persisted
    assert outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    assert outcome.result.invoice.invoice_number is None
    assert outcome.result.invoice.items == []
    assert any(issue.code == "UNSAFE_VISUAL_DOCUMENT" for issue in outcome.result.issues)
    assert semantic.calls == 0
    fresh = DocumentExtractionRepository()
    active = fresh.get_active(source.document_id)
    assert active.result == outcome.result
    assert active.status == ExtractionStatus.NEEDS_REVIEW
    assert len(fresh.list_history(source.document_id)) == 1
    assert pipeline.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.NEEDS_REVIEW
    assert sha256(pipeline.source_bytes(source.document_id)).hexdigest() == before


def test_production_scan_pipeline_reconciles_once_per_stage_and_persists_exact_evidence(invoice_pipeline, monkeypatch):
    p = invoice_pipeline
    source, before, vision = classified_scan(p, monkeypatch)
    # Classification's provider calls are cleared; approved architecture has no
    # cross-stage OCR cache. Extraction itself renders each visual page once.
    semantic = SemanticSpy()
    outcome = p.extract(source.document_id, semantic_provider=semantic)
    assert outcome.persisted
    assert vision.renderer.calls == [0]
    assert vision.vlm.calls == [1]
    assert vision.ocr.calls == [1]
    assert outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    invoice = DocumentExtractionRepository().get_active(source.document_id).result.invoice
    assert invoice.invoice_number.normalized_value == "0000789"
    assert invoice.invoice_number.raw_value == "0000789"
    assert invoice.invoice_number.source_document_id == source.document_id
    assert invoice.invoice_number.page == 1
    assert invoice.invoice_date.normalized_value == date(2026, 10, 29)
    assert invoice.total_amount.normalized_value == Decimal("125.50")
    assert invoice.items == []
    assert any(issue.code == "PDF_ITEMS_UNSUPPORTED" for issue in outcome.result.issues)
    assert sha256(p.source_bytes(source.document_id)).hexdigest() == before


def test_native_pages_bypass_rendering_and_both_visual_providers_across_production_flow(invoice_pipeline, monkeypatch):
    p = invoice_pipeline
    vision = LocalVision()
    monkeypatch.setattr(composition, "vision_service_factory", vision.factory)
    source = p.register(p.pdf())
    assert p.classify(source.document_id).document_type == DocumentType.COMMERCIAL_INVOICE
    outcome = p.extract(source.document_id)
    assert outcome.persisted
    assert outcome.result.invoice.invoice_number.page == 1
    assert outcome.result.invoice.total_amount.page == 2
    assert vision.renderer.calls == vision.vlm.calls == vision.ocr.calls == []


@pytest.mark.parametrize("unsafe", ["disabled", "providers_failed", "low_confidence", "numeric_disagreement", "mixed_page"])
def test_unsafe_visual_pipeline_never_calls_semantic_or_publishes_partial_headers(invoice_pipeline, monkeypatch, caplog, unsafe):
    p = invoice_pipeline
    pages = [SAFE_TEXT, None] if unsafe == "mixed_page" else [None]
    source, before, vision = classified_scan(p, monkeypatch, pages=pages)
    if unsafe == "disabled":
        monkeypatch.setattr(composition, "vision_service_factory", lambda repository: None)
    elif unsafe in {"providers_failed", "mixed_page"}:
        vision.vlm.failed_pages = {2 if unsafe == "mixed_page" else 1}
        vision.ocr.failed_pages = set(vision.vlm.failed_pages)
    elif unsafe == "low_confidence":
        vision.vlm.confidence = vision.ocr.confidence = 0.01
    else:
        vision.ocr.text = SAFE_TEXT.replace("125.50", "1250.50")
    semantic = SemanticSpy()
    outcome = p.extract(source.document_id, semantic_provider=semantic)
    assert_unsafe_attempt(p, source, before, semantic, outcome)
    expected = [] if unsafe == "disabled" else [1 if unsafe == "mixed_page" else 0]
    assert vision.renderer.calls == expected
    assert "SYNTHETIC_PRIVATE_VISUAL_EXCEPTION" not in caplog.text
    assert source.stored_path not in caplog.text
    assert "Synthetic Visual Exporter" not in caplog.text


@pytest.mark.parametrize("malformed", [
    "document_id", "file_type", "page_count", "duplicate_page", "unresolved",
    "visual_outside", "visual_duplicate", "visual_missing", "fallback_flag",
])
def test_inconsistent_resolved_metadata_fails_closed_after_real_reconciliation(invoice_pipeline, monkeypatch, malformed):
    p = invoice_pipeline
    source, before, vision = classified_scan(p, monkeypatch, pages=[None, None])

    def corrupt(result):
        if malformed == "document_id":
            result.document_id = "DOC-OTHER"
        elif malformed == "file_type":
            result.file_type = "xlsx"
        elif malformed == "page_count":
            result.page_count = 3
        elif malformed == "duplicate_page":
            result.pages[1].page = 1
        elif malformed == "unresolved":
            result.unresolved_pages = [999]
        elif malformed == "visual_outside":
            result.visual_pages = [1, 999]
        elif malformed == "visual_duplicate":
            result.visual_pages = [1, 1, 2]
        elif malformed == "visual_missing":
            result.visual_pages = []
        else:
            result.vision_fallback_recommended = True

    vision.mutate_resolution = corrupt
    semantic = SemanticSpy()
    outcome = p.extract(source.document_id, semantic_provider=semantic)
    assert_unsafe_attempt(p, source, before, semantic, outcome)
    assert vision.renderer.calls == [0, 1]


def test_unclassified_scan_without_vision_is_unknown_and_refused_without_attempt(invoice_pipeline):
    p = invoice_pipeline
    source = p.register(p.pdf([None]))
    before = p.source_bytes(source.document_id)
    classification = p.classify(source.document_id)
    assert classification.document_type == DocumentType.UNKNOWN
    assert p.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.NEEDS_REVIEW
    semantic = SemanticSpy()
    outcome = p.extract(source.document_id, semantic_provider=semantic)
    assert not outcome.persisted
    assert outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    assert outcome.result.invoice.invoice_number is None
    assert semantic.calls == 0
    assert DocumentExtractionRepository().list_history(source.document_id) == []
    assert p.source_bytes(source.document_id) == before
