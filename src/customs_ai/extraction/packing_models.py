"""Provider-neutral Packing contracts; no document interpretation or storage.

Canonical models and 006A issue/candidate types remain authoritative. Status is
explicit. EXTRACTED rejects empty/unresolved values and review-required issues;
it does not certify completeness or independently verify a source document.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from customs_ai.domain.schema import CanonicalField, PackingItem, PackingList
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue


def _fresh(model, value):
    """Validate nested instances too, including unsafe copies or mutations."""
    try:
        data = value.model_dump(mode="python", warnings="error") if isinstance(value, BaseModel) else value
        return model.model_validate(data)
    except (ValueError, TypeError):
        raise ValueError("Invalid nested Packing extraction value.") from None


def _fields(value):
    if isinstance(value, CanonicalField):
        yield value
    elif isinstance(value, BaseModel):
        for _, child in value:
            yield from _fields(child)
    elif isinstance(value, list):
        for child in value:
            yield from _fields(child)


def _check_success(status, issues, fields):
    if status != ExtractionStatus.EXTRACTED:
        return
    if any(issue.is_review_required for issue in issues):
        raise ValueError("EXTRACTED cannot contain review-required issues.")
    values = list(fields)
    if not values or any(value.normalized_value is None for value in values):
        raise ValueError("EXTRACTED requires resolved canonical values.")


class _PackingResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, revalidate_instances="always",
        hide_input_in_errors=True,
    )

    status: ExtractionStatus
    issues: list[ExtractionIssue] = Field(default_factory=list)
    candidates: list[ExtractionCandidate] = Field(default_factory=list)

    @field_validator("issues", mode="before")
    @classmethod
    def validate_issues(cls, value):
        if type(value) is not list:
            raise ValueError("Issues must be a list.")
        return [_fresh(ExtractionIssue, item) for item in value]

    @field_validator("candidates", mode="before")
    @classmethod
    def validate_candidates(cls, value):
        if type(value) is not list:
            raise ValueError("Candidates must be a list.")
        return [_fresh(ExtractionCandidate, item) for item in value]


class PackingListHeaderExtractionResult(_PackingResult):
    """Header result using the existing list-valued canonical PackingList."""

    packing_list: PackingList

    @field_validator("packing_list", mode="before")
    @classmethod
    def validate_packing_list(cls, value):
        return _fresh(PackingList, value)

    @model_validator(mode="after")
    def check_success(self):
        # Header completion cannot be inferred merely from item data.
        header_fields = (
            field for name, value in self.packing_list if name != "items"
            for field in _fields(value)
        )
        _check_success(self.status, self.issues, header_fields)
        return self


class PackingItemExtractionResult(_PackingResult):
    """Item-table result; optional canonical fields remain absent by default."""

    items: list[PackingItem] = Field(default_factory=list)

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, value):
        if type(value) is not list:
            raise ValueError("Items must be a list.")
        return [_fresh(PackingItem, item) for item in value]

    @model_validator(mode="after")
    def check_success(self):
        _check_success(self.status, self.issues, _fields(self.items))
        if self.status == ExtractionStatus.EXTRACTED and any(not list(_fields(item)) for item in self.items):
            raise ValueError("EXTRACTED cannot contain empty item rows.")
        return self
