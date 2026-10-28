import pytest
from pydantic import ValidationError

from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue


def test_extraction_status_enum_values():
    assert ExtractionStatus.EXTRACTED.value == "EXTRACTED"
    assert ExtractionStatus.NEEDS_REVIEW.value == "NEEDS_REVIEW"
    assert ExtractionStatus.FAILED.value == "FAILED"
    assert len(ExtractionStatus) == 3


def test_extraction_issue_valid_and_defaults():
    issue = ExtractionIssue(
        code="HEADER_PARSE_FAILED",
        message="Failed to parse header date field",
    )
    assert issue.code == "HEADER_PARSE_FAILED"
    assert issue.message == "Failed to parse header date field"
    assert issue.field_path is None
    assert issue.is_review_required is False

    issue_with_field = ExtractionIssue(
        code="SUSPICIOUS_AMOUNT",
        message="Amount appears anomalous",
        field_path="total_amount",
        is_review_required=True,
    )
    assert issue_with_field.field_path == "total_amount"
    assert issue_with_field.is_review_required is True


def test_extraction_issue_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ExtractionIssue(
            code="TEST",
            message="Test message",
            extra_field="disallowed",  # type: ignore[call-arg]
        )


def test_extraction_candidate_valid_and_confidence_bounds():
    candidate = ExtractionCandidate(
        field_path="invoice_number",
        raw_value="INV-2026-001",
        source_document_id="doc_123",
        page=1,
        sheet=None,
        cell=None,
        bounding_box=(0.1, 0.2, 0.3, 0.4),
        confidence=0.95,
        extraction_method="deterministic_header",
    )
    assert candidate.field_path == "invoice_number"
    assert candidate.raw_value == "INV-2026-001"
    assert candidate.confidence == 0.95

    # Confidence below 0.0 rejected
    with pytest.raises(ValidationError):
        ExtractionCandidate(
            field_path="invoice_number",
            raw_value="INV-001",
            confidence=-0.1,
        )

    # Confidence above 1.0 rejected
    with pytest.raises(ValidationError):
        ExtractionCandidate(
            field_path="invoice_number",
            raw_value="INV-001",
            confidence=1.05,
        )


def test_extraction_candidate_page_bounds_and_empty_field_path():
    # Page <= 0 rejected
    with pytest.raises(ValidationError):
        ExtractionCandidate(
            field_path="invoice_number",
            raw_value="INV-001",
            page=0,
        )
    with pytest.raises(ValidationError):
        ExtractionCandidate(
            field_path="invoice_number",
            raw_value="INV-001",
            page=-1,
        )


def test_extraction_candidate_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ExtractionCandidate(
            field_path="invoice_number",
            raw_value="INV-001",
            undeclared_property="invalid",  # type: ignore[call-arg]
        )
