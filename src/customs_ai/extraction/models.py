from datetime import date, datetime, time
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from customs_ai.domain.schema import Invoice, InvoiceItem
from customs_ai.extraction.enums import ExtractionStatus

CandidateTypedValue = Union[bool, date, datetime, time, Decimal, int, float, str, None]


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
    typed_value: CandidateTypedValue = None


class InvoiceHeaderExtractionResult(BaseModel):
    """Result of deterministic invoice header extraction."""

    model_config = ConfigDict(extra="forbid")

    invoice: Invoice
    status: ExtractionStatus
    issues: list[ExtractionIssue] = Field(default_factory=list)
    candidates: list[ExtractionCandidate] = Field(default_factory=list)


class InvoiceItemExtractionResult(BaseModel):
    """Canonical item rows with explicit review status and source evidence."""

    model_config = ConfigDict(extra="forbid")

    items: list[InvoiceItem] = Field(default_factory=list)
    status: ExtractionStatus
    issues: list[ExtractionIssue] = Field(default_factory=list)
    candidates: list[ExtractionCandidate] = Field(default_factory=list)
