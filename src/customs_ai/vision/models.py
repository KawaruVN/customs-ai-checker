from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from customs_ai.vision.enums import TextResolutionSource, VerificationLevel


class ProviderTextResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    structured_content: dict[str, Any] | list[Any] | str | None = None


class ResolvedPdfPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    text: str
    source: TextResolutionSource
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_level: VerificationLevel
    agreement_score: float | None = Field(default=None, ge=0.0, le=1.0)
    requires_review: bool
    provider_results: list[ProviderTextResult] = Field(default_factory=list)


class ResolvedPdfDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    file_type: str = "pdf"
    parser_used: str = "pypdf+local_vision"
    page_count: int = Field(ge=0)
    pages: list[ResolvedPdfPage] = Field(default_factory=list)
    visual_pages: list[int] = Field(default_factory=list)
    unresolved_pages: list[int] = Field(default_factory=list)
    requires_review: bool
    vision_fallback_recommended: bool = False
