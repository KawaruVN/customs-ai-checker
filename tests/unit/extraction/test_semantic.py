from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue, InvoiceHeaderExtractionResult
from customs_ai.extraction.semantic import SemanticInvoiceRequest, SemanticInvoiceResponse, merge_semantic
from customs_ai.parsers.models import ParsedCell, ParsedPdfDocument, ParsedPdfPage, ParsedSheet, ParsedWorkbook
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ResolvedPdfDocument, ResolvedPdfPage


def workbook(rows=None, **sheet_changes):
    rows = rows or [["INVOICE NO", "00012"], ["TOTAL AMOUNT", "12.50"], ["INVOICE DATE", "2026-10-29"]]
    cells = []
    for row, values in enumerate(rows, 1):
        for col, value in enumerate(values, 1):
            cells.append(ParsedCell(row=row, column=col, coordinate=f"{chr(64 + col)}{row}", raw_value=value, data_type="s"))
    return ParsedWorkbook(
        document_id="DOC-1", file_type="xlsx", parser_used="openpyxl", workbook_name="must_not_send.xlsx",
        sheet_count=1, sheets=[ParsedSheet(name="Invoice", index=0, state="visible", cells=cells, **sheet_changes)],
    )


def baseline(**changes):
    return InvoiceHeaderExtractionResult(invoice=Invoice(), status=ExtractionStatus.EXTRACTED, **changes)


def candidate(path="invoice_number", raw="00012", typed="00012", **changes):
    data = dict(field_path=path, raw_value=raw, typed_value=typed, source_document_id="DOC-1", sheet="Invoice", cell="B1")
    data.update(changes)
    return ExtractionCandidate(**data)


class Provider:
    def __init__(self, candidates=None, **changes):
        self.candidates = candidates if candidates is not None else [candidate()]
        self.changes = changes
        self.calls = []

    def extract(self, request):
        self.calls.append(request)
        return SemanticInvoiceResponse(document_id=self.changes.get("document_id", "DOC-1"), candidates=self.candidates)


def test_grounded_missing_fields_fill_with_exact_raw_typed_value_and_provenance():
    provider = Provider([
        candidate(), candidate("total_amount", "12.50", Decimal("12.50"), cell="B2"),
        candidate("invoice_date", "2026-10-29", date(2026, 10, 29), cell="B3"),
    ])
    source = workbook()
    original = baseline()
    result = merge_semantic(source, original, provider)
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.invoice_number.normalized_value == "00012"
    assert result.invoice.total_amount.normalized_value == Decimal("12.50")
    assert type(result.invoice.invoice_date.normalized_value) is date
    assert result.invoice.total_amount.origin == ValueOrigin.EXTRACTED
    assert result.invoice.total_amount.source_document_id == "DOC-1"
    assert result.invoice.total_amount.cell == "B2"
    assert result.invoice.total_amount.sheet == "Invoice"
    assert original.invoice.invoice_number is None
    request = provider.calls[0].model_dump()
    assert set(request) == {"document_id", "sources"}
    assert "must_not_send" not in str(request)


@pytest.mark.parametrize("changes", [
    {"source_document_id": "OTHER"}, {"sheet": "Missing"}, {"cell": "Z99"},
    {"page": 1}, {"raw_value": "FABRICATED"}, {"field_path": "seller.country_code"},
    {"field_path": "items[0].quantity"}, {"typed_value": 12}, {"typed_value": None},
    {"typed_value": "OTHER"}, {"bounding_box": (0.0, 0.0, 1.0, 1.0)},
])
def test_malicious_or_incorrect_candidate_cannot_fill(changes):
    result = merge_semantic(workbook(), baseline(), Provider([candidate(**changes)]))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.invoice_number is None
    assert result.issues


def test_wrong_response_document_id_is_rejected():
    result = merge_semantic(workbook(), baseline(), Provider(document_id="OTHER"))
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


@pytest.mark.parametrize("typed", ["12.50", 12.5, 12, True, Decimal("999"), Decimal("NaN")])
def test_numeric_source_cannot_be_fabricated_or_coerced_from_wrong_provider_type(typed):
    result = merge_semantic(workbook(), baseline(), Provider([candidate("total_amount", "12.50", typed, cell="B2")]))
    assert result.invoice.total_amount is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_wrong_party_role_rejected_even_when_raw_exists_at_claimed_location():
    doc = workbook([["SELLER", "Synthetic Seller"]])
    result = merge_semantic(doc, baseline(), Provider([candidate("buyer.name", "Synthetic Seller", "Synthetic Seller")]))
    assert result.invoice.buyer is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    valid = merge_semantic(doc, baseline(), Provider([candidate("seller.name", "Synthetic Seller", "Synthetic Seller")]))
    assert valid.invoice.seller.name.normalized_value == "Synthetic Seller"


def test_unlabelled_value_is_not_evidence_for_arbitrary_canonical_field():
    doc = workbook([["INVOICE NO", "00012"], ["UNRELATED NOTE", "Synthetic Seller"]])
    provider = Provider([candidate("seller.name", "Synthetic Seller", "Synthetic Seller", cell="B2")])
    result = merge_semantic(doc, baseline(), provider)
    assert result.invoice.seller is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_adjacent_value_containing_another_party_label_cannot_change_its_role():
    doc = workbook([["BUYER", "SELLER: Synthetic Seller"]])
    provider = Provider([candidate("buyer.name", "SELLER: Synthetic Seller", "SELLER: Synthetic Seller")])
    result = merge_semantic(doc, baseline(), provider)
    assert result.invoice.buyer is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert not any(source.field_path == "buyer.name" for source in provider.calls[0].sources)


def test_accepted_deterministic_values_are_never_overwritten():
    original = baseline()
    original.invoice.invoice_number = CanonicalField[str](
        raw_value="ORIGINAL", normalized_value="ORIGINAL", origin=ValueOrigin.EXTRACTED,
        source_document_id="DOC-1", sheet="Invoice", cell="B5",
    )
    result = merge_semantic(workbook(), original, Provider())
    assert result.invoice.invoice_number == original.invoice.invoice_number
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.code == "SEMANTIC_OVERWRITE_REJECTED" for issue in result.issues)


@pytest.mark.parametrize("code", ["CONFLICTING_FIELD_VALUES", "UNRESOLVED_FORMULA_FIELD", "UNPARSEABLE_DATE_FIELD"])
def test_deterministic_review_issue_and_missing_field_remain_sticky(code):
    issue = ExtractionIssue(code=code, message="Synthetic review.", field_path="invoice_number", is_review_required=True)
    original = baseline(issues=[issue])
    result = merge_semantic(workbook(), original, Provider())
    assert result.invoice.invoice_number is None
    assert issue in result.issues
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_existing_unresolved_deterministic_candidates_block_fill_even_without_issue():
    original = baseline(candidates=[candidate(raw="=A1", typed=None)])
    result = merge_semantic(workbook(), original, Provider())
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_three_way_semantic_conflict_is_sticky_not_majority_vote():
    doc = workbook([["INVOICE NO", "00012"], ["INVOICE NO", "00013"], ["INVOICE NO", "00012"]])
    provider = Provider([candidate(), candidate(raw="00013", typed="00013", cell="B2"), candidate(cell="B3")])
    result = merge_semantic(doc, baseline(), provider)
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.code == "SEMANTIC_CONFLICTING_VALUES" for issue in result.issues)


def test_provider_cannot_hide_conflicting_grounded_sources_by_proposing_one_value():
    doc = workbook([["INVOICE NO", "00012"], ["INVOICE NO", "00013"]])
    result = merge_semantic(doc, baseline(), Provider([candidate()]))
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.code == "SEMANTIC_CONFLICTING_VALUES" for issue in result.issues)


@pytest.mark.parametrize("change", ["hidden_sheet", "hidden_row", "hidden_column", "formula_label", "formula_value", "expression_label", "expression_value", "merged"])
def test_unsafe_excel_content_never_reaches_provider(change):
    doc = workbook([["INVOICE NO", "00012"]])
    sheet = doc.sheets[0]
    if change == "hidden_sheet":
        sheet.state = "hidden"
    elif change == "hidden_row":
        sheet.hidden_rows = [1]
    elif change == "hidden_column":
        sheet.hidden_columns = ["B"]
    elif change == "formula_label":
        sheet.cells[0].is_formula = True
    elif change == "formula_value":
        sheet.cells[1].is_formula = True
    elif change == "expression_label":
        sheet.cells[0].raw_value = '="INVOICE NO"'
    elif change == "expression_value":
        sheet.cells[1].raw_value = '="00012"'
    else:
        sheet.merged_ranges = ["A1:B1"]
    provider = Provider()
    result = merge_semantic(doc, baseline(), provider)
    assert provider.calls == []
    assert result.invoice.invoice_number is None


@pytest.mark.parametrize("response", [
    {"document_id": "DOC-1", "candidates": [], "extra": "private"},
    {"document_id": "DOC-1", "candidates": [{"field_path": "invoice_number", "raw_value": "00012", "extra": "private"}]},
    None, "not a result",
])
def test_malformed_provider_result_fails_closed(response):
    class Malformed:
        def extract(self, request):
            return response
    result = merge_semantic(workbook(), baseline(), Malformed())
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.invoice_number is None


def test_provider_exception_is_safe_and_does_not_silently_succeed(caplog):
    class Failing:
        def extract(self, request):
            raise RuntimeError("SYNTHETIC_PRIVATE_PROVIDER_PAYLOAD")
    result = merge_semantic(workbook(), baseline(), Failing())
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "SYNTHETIC_PRIVATE" not in str(result.issues) + caplog.text


def test_mutating_provider_request_cannot_forge_grounding():
    class Mutating:
        def extract(self, request):
            request.sources.clear()
            return SemanticInvoiceResponse(document_id="DOC-1", candidates=[candidate(raw="FORGED", typed="FORGED")])
    result = merge_semantic(workbook(), baseline(), Mutating())
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_provider_output_mutated_after_validation_is_revalidated():
    class Mutated:
        def extract(self, request):
            value = SemanticInvoiceResponse(document_id="DOC-1", candidates=[candidate()])
            value.candidates[0].source_document_id = 23
            return value
    result = merge_semantic(workbook(), baseline(), Mutated())
    assert result.invoice.invoice_number is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_safe_native_pdf_explicit_label_and_actual_page_grounding():
    doc = ParsedPdfDocument(
        document_id="DOC-1", page_count=1, has_text_layer=True, needs_ocr=False,
        pages=[ParsedPdfPage(page=1, text="COMMERCIAL INVOICE\nINVOICE NO: 00012\nTOTAL AMOUNT: 12.50")],
    )
    provider = Provider([candidate(raw=" 00012", sheet=None, cell=None, page=1)])
    result = merge_semantic(doc, baseline(), provider)
    assert result.invoice.invoice_number.normalized_value == "00012"
    assert result.invoice.invoice_number.raw_value == " 00012"
    assert result.invoice.invoice_number.page == 1


@pytest.mark.parametrize("unsafe", ["review", "unresolved", "unverified", "conflict", "low_confidence", "one_unsafe_page"])
def test_unsafe_resolved_visual_document_never_calls_semantic_provider(unsafe):
    page = ResolvedPdfPage(
        page=1, text="COMMERCIAL INVOICE\nINVOICE NO: 00012", source=TextResolutionSource.CROSS_VERIFIED_VISUAL,
        verification_level=VerificationLevel.CROSS_VERIFIED, requires_review=False, confidence=0.99,
    )
    doc = ResolvedPdfDocument(document_id="DOC-1", page_count=1, pages=[page], requires_review=False)
    if unsafe == "review":
        doc.requires_review = True
    elif unsafe == "unresolved":
        doc.unresolved_pages = [1]
    elif unsafe == "unverified":
        page.verification_level = VerificationLevel.UNVERIFIED
    elif unsafe == "conflict":
        page.verification_level = VerificationLevel.CONFLICT
    elif unsafe == "low_confidence":
        page.confidence = 0.01
    else:
        doc.pages.append(page.model_copy(update={"page": 2, "requires_review": True}))
        doc.page_count = 2
    provider = Provider()
    result = merge_semantic(doc, baseline(), provider)
    assert provider.calls == []
    assert result.status == ExtractionStatus.NEEDS_REVIEW


def test_strict_request_and_response_reject_unexpected_fields():
    with pytest.raises(ValidationError):
        SemanticInvoiceRequest(document_id="DOC-1", sources=[], source_path="private")
    with pytest.raises(ValidationError):
        SemanticInvoiceResponse(document_id="DOC-1", candidates=[], invoice=Invoice())
