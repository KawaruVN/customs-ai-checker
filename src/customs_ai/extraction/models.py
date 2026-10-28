from pydantic import BaseModel, ConfigDict, Field


class ExtractionIssue(BaseModel):
    """Typed extraction issue record.

    Safety contract: messages must be safe and must not contain raw customer values.
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    field_path: str | None = None
    is_review_required: bool = False


class ExtractionCandidate(BaseModel):
    """Generic provider-neutral source candidate primitive with provenance evidence."""

    model_config = ConfigDict(extra="forbid")

    field_path: str
    raw_value: str
    source_document_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    sheet: str | None = None
    cell: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    extraction_method: str | None = None
