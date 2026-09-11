import pytest
from pydantic import ValidationError

from customs_ai.application.composition import build_classification_service
from customs_ai.config import settings
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.models import ProviderTextResult, ResolvedPdfDocument


def test_provider_result_is_raw_and_forbids_usable_field():
    ProviderTextResult(provider="x", text="abc", confidence=0.5)
    with pytest.raises(ValidationError):
        ProviderTextResult(provider="x", text="abc", usable=True)


def test_resolved_document_contract_accepts_service_fields():
    doc = ResolvedPdfDocument(
        document_id="D",
        page_count=0,
        requires_review=False,
        vision_fallback_recommended=False,
    )
    assert doc.vision_fallback_recommended is False


def test_production_composition_vision_disabled_does_not_build_visual_service(monkeypatch):
    monkeypatch.setattr(settings.vision, "enabled", False)
    service = build_classification_service(SourceDocumentRepository())
    assert service.vision_service is None


def test_production_composition_vision_enabled_uses_factory(monkeypatch):
    marker = object()
    monkeypatch.setattr(settings.vision, "enabled", True)
    import customs_ai.application.composition as composition
    monkeypatch.setattr(composition, "vision_service_factory", lambda repo: marker)
    service = composition.build_classification_service(SourceDocumentRepository())
    assert service.vision_service is marker
