"""Real Packing factories and reconciliation; only local image/provider I/O faked."""

from contextlib import closing
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json

from PIL import Image
import pytest

import customs_ai.application.composition as composition
from customs_ai.classification.enums import DocumentType
from customs_ai.config import VisionSettingsConfig
from customs_ai.domain.schema import PackingList
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.packing_items import DeterministicPackingItemExtractor
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import DocumentExtractionRepository
from customs_ai.vision.enums import VerificationLevel
from customs_ai.vision.models import ProviderTextResult
from customs_ai.vision.service import VisualResolutionService


SAFE_TEXT = (
    "PACKING LIST\nPACKING LIST NO: 0000789\nPACKING LIST DATE: 2026-10-29\n"
    "SELLER: Synthetic Visual Seller\nBUYER: Synthetic Visual Buyer\n"
    "INVOICE NO: 0000045\nINVOICE NO: 0000046\nTOTAL PACKAGES: 0.00\n"
    "TOTAL GROSS WEIGHT: 125.50\nTOTAL NET WEIGHT: 120.50"
)
PRIVATE_ERROR = "SYNTHETIC_PRIVATE_PACKING_VISUAL_EXCEPTION"


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
            raise RuntimeError(PRIVATE_ERROR)
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
    """Production quality/reconciliation with controlled renderer/provider seams."""

    def __init__(self):
        self.renderer = LocalRenderer()
        self.vlm = LocalProvider("synthetic-packing-vlm")
        self.ocr = LocalProvider("synthetic-packing-ocr")
        self.mutate_resolution = None
        self.observed_resolutions = []

    def clear_calls(self):
        self.renderer.calls.clear()
        self.vlm.calls.clear()
        self.ocr.calls.clear()
        self.observed_resolutions.clear()

    def factory(self, repository):
        real = VisualResolutionService(
            repository, self.vlm, self.ocr, config=VisionSettingsConfig(enabled=True),
            renderer=self.renderer,
        )
        owner = self

        class Resolution:
            def resolve_document(self, document_id, parsed):
                resolved = real.resolve_document(document_id, parsed)
                owner.observed_resolutions.append(resolved.model_copy(deep=True))
                if owner.mutate_resolution is not None:
                    owner.mutate_resolution(resolved)
                return resolved

        return Resolution()


def classified_scan(pipeline, monkeypatch, *, pages=None):
    pages = [None] if pages is None else pages
    vision = LocalVision()
    monkeypatch.setattr(composition, "vision_service_factory", vision.factory)
    source = pipeline.register(pipeline.pdf(pages))
    before = sha256(pipeline.source_bytes(source.document_id)).hexdigest()
    assert before == source.file_hash
    classification = pipeline.classify(source.document_id)
    assert classification.document_id == source.document_id
    assert classification.document_type == DocumentType.PACKING_LIST
    assert pipeline.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.CLASSIFIED
    indexes = [index for index, text in enumerate(pages) if not text]
    assert vision.renderer.calls == indexes
    assert vision.vlm.calls == vision.ocr.calls == [index + 1 for index in indexes]
    vision.clear_calls()
    return source, before, vision


def assert_committed_roundtrip(pipeline, source, before, outcome):
    assert outcome.persisted and outcome.record is not None
    assert outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    assert outcome.result.packing_list.items == []
    assert any(issue.code == "PDF_PACKING_ITEMS_UNSUPPORTED" for issue in outcome.result.issues)
    fresh = DocumentExtractionRepository()
    active = fresh.get_active(source.document_id)
    assert active == outcome.record
    assert active.result == outcome.result
    assert fresh.get_by_extraction_id(active.extraction_id) == active
    assert fresh.list_history(source.document_id) == [active]
    assert active.schema_version == "0.1" and active.is_active
    assert pipeline.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.NEEDS_REVIEW
    with closing(get_connection()) as connection:
        wire = json.loads(connection.execute(
            "SELECT payload_json FROM document_extractions WHERE extraction_id=?",
            (active.extraction_id,),
        ).fetchone()[0])
    assert (wire["format_version"], wire["result_type"]) == (2, "packing_list")
    assert sha256(pipeline.source_bytes(source.document_id)).hexdigest() == before


def assert_unsafe_attempt(pipeline, source, before, outcome):
    assert_committed_roundtrip(pipeline, source, before, outcome)
    assert outcome.result.packing_list == PackingList()
    assert outcome.result.candidates == []
    assert any(issue.code == "UNSAFE_VISUAL_DOCUMENT" for issue in outcome.result.issues)


@pytest.mark.parametrize("pages", [1, 2])
def test_safe_native_packing_pages_bypass_all_visual_io_and_pdf_items(packing_pipeline, monkeypatch, pages):
    p = packing_pipeline
    vision = LocalVision()
    monkeypatch.setattr(composition, "vision_service_factory", vision.factory)
    item_calls = []
    original = DeterministicPackingItemExtractor.extract

    def observe(self, document):
        item_calls.append(document)
        return original(self, document)

    monkeypatch.setattr(DeterministicPackingItemExtractor, "extract", observe)
    source = p.register(p.pdf([SAFE_TEXT] * pages))
    before = source.file_hash
    assert p.classify(source.document_id).document_type == DocumentType.PACKING_LIST
    outcome = p.extract(source.document_id)
    assert_committed_roundtrip(p, source, before, outcome)
    packing = outcome.result.packing_list
    assert packing.packing_list_number.normalized_value == "0000789"
    assert packing.packing_list_number.raw_value == "0000789" and packing.packing_list_number.page == 1
    assert packing.date.normalized_value == date(2026, 10, 29)
    assert packing.seller.name.normalized_value == "Synthetic Visual Seller"
    assert packing.buyer.name.normalized_value == "Synthetic Visual Buyer"
    assert [field.normalized_value for field in packing.invoice_references] == ["0000045", "0000046"]
    assert packing.package_count.normalized_value.as_tuple() == Decimal("0.00").as_tuple()
    assert packing.gross_weight.normalized_value == Decimal("125.50")
    assert packing.net_weight.normalized_value == Decimal("120.50")
    assert vision.renderer.calls == vision.vlm.calls == vision.ocr.calls == []
    assert item_calls == []


def test_safe_scan_reconciles_once_per_page_per_production_stage(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source, before, vision = classified_scan(p, monkeypatch)
    outcome = p.extract(source.document_id)
    assert_committed_roundtrip(p, source, before, outcome)
    assert vision.renderer.calls == [0]
    assert vision.vlm.calls == vision.ocr.calls == [1]
    assert len(vision.observed_resolutions) == 1
    assert vision.observed_resolutions[0].pages[0].verification_level == VerificationLevel.CROSS_VERIFIED
    packing = outcome.result.packing_list
    assert packing.packing_list_number.normalized_value == "0000789" and packing.packing_list_number.page == 1
    assert packing.date.normalized_value == date(2026, 10, 29)
    assert packing.gross_weight.normalized_value.as_tuple() == Decimal("125.50").as_tuple()
    assert all(candidate.source_document_id == source.document_id and candidate.page == 1 for candidate in outcome.result.candidates)


@pytest.mark.parametrize("failed_provider", ["ocr", "vlm"])
def test_approved_single_provider_resolution_retains_grounded_packing_headers(packing_pipeline, monkeypatch, failed_provider):
    p = packing_pipeline
    source, before, vision = classified_scan(p, monkeypatch)
    getattr(vision, failed_provider).failed_pages = {1}
    outcome = p.extract(source.document_id)
    assert_committed_roundtrip(p, source, before, outcome)
    assert outcome.result.packing_list.packing_list_number.normalized_value == "0000789"
    assert vision.observed_resolutions[0].pages[0].verification_level == VerificationLevel.SINGLE_PROVIDER
    assert vision.renderer.calls == [0] and vision.vlm.calls == vision.ocr.calls == [1]


@pytest.mark.parametrize("unsafe", ["disabled", "providers_failed", "low_confidence", "identifier_conflict", "numeric_conflict", "mixed_page"])
def test_unsafe_visual_evidence_never_publishes_partial_packing_values(packing_pipeline, monkeypatch, caplog, unsafe):
    p = packing_pipeline
    pages = [SAFE_TEXT, None] if unsafe == "mixed_page" else [None]
    source, before, vision = classified_scan(p, monkeypatch, pages=pages)
    if unsafe == "disabled":
        monkeypatch.setattr(composition, "vision_service_factory", lambda repository: None)
    elif unsafe in {"providers_failed", "mixed_page"}:
        vision.vlm.failed_pages = vision.ocr.failed_pages = {2 if unsafe == "mixed_page" else 1}
    elif unsafe == "low_confidence":
        vision.vlm.confidence = vision.ocr.confidence = 0.01
    elif unsafe == "identifier_conflict":
        vision.ocr.text = SAFE_TEXT.replace("0000789", "0000799")
    else:
        vision.ocr.text = SAFE_TEXT.replace("125.50", "1250.50")
    outcome = p.extract(source.document_id)
    assert_unsafe_attempt(p, source, before, outcome)
    assert vision.renderer.calls == ([] if unsafe == "disabled" else [1 if unsafe == "mixed_page" else 0])
    assert PRIVATE_ERROR not in caplog.text
    assert source.stored_path not in caplog.text and "Synthetic Visual Seller" not in caplog.text
    assert PRIVATE_ERROR not in str(outcome.result.issues)


@pytest.mark.parametrize("malformed", [
    "document_id", "file_type", "page_count", "missing_page", "duplicate_page", "page_id",
    "unresolved", "document_review", "page_review", "visual_outside", "visual_duplicate",
    "visual_missing", "fallback_flag", "unverified", "agreement",
])
def test_malformed_resolved_metadata_is_rejected_after_real_reconciliation(packing_pipeline, monkeypatch, malformed):
    p = packing_pipeline
    source, before, vision = classified_scan(p, monkeypatch, pages=[None, None])

    def corrupt(result):
        if malformed == "document_id": result.document_id = "DOC-OTHER"
        elif malformed == "file_type": result.file_type = "xlsx"
        elif malformed == "page_count": result.page_count = 3
        elif malformed == "missing_page": result.pages.pop()
        elif malformed == "duplicate_page": result.pages[1].page = 1
        elif malformed == "page_id": result.pages[1].page = 99
        elif malformed == "unresolved": result.unresolved_pages = [999]
        elif malformed == "document_review": result.requires_review = True
        elif malformed == "page_review": result.pages[0].requires_review = True
        elif malformed == "visual_outside": result.visual_pages = [1, 999]
        elif malformed == "visual_duplicate": result.visual_pages = [1, 1, 2]
        elif malformed == "visual_missing": result.visual_pages = []
        elif malformed == "fallback_flag": result.vision_fallback_recommended = True
        elif malformed == "unverified": result.pages[0].verification_level = VerificationLevel.UNVERIFIED
        elif malformed == "agreement": result.pages[0].agreement_score = 0.0

    vision.mutate_resolution = corrupt
    outcome = p.extract(source.document_id)
    assert_unsafe_attempt(p, source, before, outcome)
    assert vision.renderer.calls == [0, 1] and vision.vlm.calls == vision.ocr.calls == [1, 2]


def test_replaced_native_page_text_is_not_accepted_from_visual_resolution(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source, before, vision = classified_scan(p, monkeypatch, pages=[SAFE_TEXT, None])
    vision.mutate_resolution = lambda result: setattr(result.pages[0], "text", SAFE_TEXT.replace("0000789", "FAKE-0001"))
    outcome = p.extract(source.document_id)
    assert_unsafe_attempt(p, source, before, outcome)
    assert vision.renderer.calls == [1] and vision.vlm.calls == vision.ocr.calls == [2]


def test_scan_without_visual_evidence_is_unknown_and_never_creates_attempt(packing_pipeline):
    p = packing_pipeline
    source = p.register(p.pdf([None]))
    before = source.file_hash
    classification = p.classify(source.document_id)
    assert classification.document_type == DocumentType.UNKNOWN
    stored = p.repo.get_by_document_id(source.document_id)
    assert stored.processing_status == ProcessingStatus.NEEDS_REVIEW
    outcome = p.extract(source.document_id)
    assert not outcome.persisted and outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    assert outcome.result.packing_list == PackingList()
    assert DocumentExtractionRepository().list_history(source.document_id) == []
    assert p.repo.get_by_document_id(source.document_id) == stored
    assert sha256(p.source_bytes(source.document_id)).hexdigest() == before
