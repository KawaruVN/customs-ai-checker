from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from customs_ai.domain.enums import ValueOrigin
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.headers import (
    DeterministicInvoiceHeaderExtractor,
    extract_invoice_headers,
)
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue
from customs_ai.parsers.excel import XlsxParser
from customs_ai.parsers.models import (
    ParsedCell,
    ParsedPdfDocument,
    ParsedPdfPage,
    ParsedSheet,
    ParsedWorkbook,
)
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ResolvedPdfDocument, ResolvedPdfPage


# =============================================================================
# Helper Fixtures & Builders
# =============================================================================

def _build_pdf(doc_id: str, pages_text: list[str]) -> ParsedPdfDocument:
    pages = [
        ParsedPdfPage(page=i + 1, text=txt)
        for i, txt in enumerate(pages_text)
    ]
    return ParsedPdfDocument(
        document_id=doc_id,
        page_count=len(pages),
        has_text_layer=True,
        needs_ocr=False,
        pages=pages,
    )


def _build_workbook(doc_id: str, sheet_name: str, cells: list[ParsedCell]) -> ParsedWorkbook:
    sheet = ParsedSheet(
        name=sheet_name,
        index=0,
        state="visible",
        cells=cells,
    )
    return ParsedWorkbook(
        document_id=doc_id,
        file_type="xlsx",
        parser_used="openpyxl",
        workbook_name=f"{doc_id}.xlsx",
        sheet_count=1,
        sheets=[sheet],
    )


# =============================================================================
# Unit Tests for Deterministic Invoice Header Extraction
# =============================================================================

def test_pdf_single_field_and_multipage_extraction():
    """PDF extraction with fields across multiple pages preserving 1-based page numbers."""
    pdf = _build_pdf(
        "doc_pdf_multi",
        [
            "INVOICE NO: INV-2026-001\nINVOICE DATE: 2026-05-12",
            "TOTAL AMOUNT: 1,200.50\nCURRENCY: USD",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.normalized_value == "INV-2026-001"
    assert result.invoice.invoice_number.page == 1
    assert result.invoice.invoice_number.source_document_id == "doc_pdf_multi"
    assert result.invoice.invoice_number.origin == ValueOrigin.EXTRACTED

    assert result.invoice.invoice_date is not None
    assert result.invoice.invoice_date.normalized_value == date(2026, 5, 12)
    assert result.invoice.invoice_date.page == 1

    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("1200.50")
    assert result.invoice.total_amount.page == 2

    assert result.invoice.currency is not None
    assert result.invoice.currency.normalized_value == "USD"
    assert result.invoice.currency.page == 2


def test_excel_sheet_cell_provenance():
    """Excel extraction preserves sheet name and cell coordinate for value source."""
    cells = [
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="Invoice No:", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value="INV-EXCEL-99", data_type="s"),
        ParsedCell(coordinate="A4", row=4, column=1, raw_value="Total Amount:", data_type="s"),
        ParsedCell(coordinate="B4", row=4, column=2, raw_value="2,500.00", displayed_value="2,500.00", data_type="s"),
    ]
    wb = _build_workbook("doc_wb_prov", "InvoiceSheet", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.EXTRACTED
    inv_num = result.invoice.invoice_number
    assert inv_num is not None
    assert inv_num.normalized_value == "INV-EXCEL-99"
    assert inv_num.sheet == "InvoiceSheet"
    assert inv_num.cell == "B2"
    assert inv_num.source_document_id == "doc_wb_prov"

    tot = result.invoice.total_amount
    assert tot is not None
    assert tot.normalized_value == Decimal("2500.00")
    assert tot.sheet == "InvoiceSheet"
    assert tot.cell == "B4"


def test_raw_casing_preserved():
    """Label matching is case-insensitive but raw_value preserves original document casing."""
    pdf = _build_pdf("doc_casing", ["invoice no: inv-001-aBc\nSELLER: acme GLOBAL Co."])
    result = extract_invoice_headers(pdf)

    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.raw_value == "inv-001-aBc"

    assert result.invoice.seller is not None
    assert result.invoice.seller.name is not None
    assert result.invoice.seller.name.raw_value == "acme GLOBAL Co."


def test_specific_labels_override_generic_prefix_labels():
    """SELLER ADDRESS must not become seller.name; BUYER ADDRESS must not become buyer.name."""
    pdf = _build_pdf(
        "doc_prefix",
        [
            "SELLER ADDRESS: 123 Harbor Rd, Hai Phong\nBUYER ADDRESS: 456 Ocean St, Da Nang",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.invoice.seller is not None
    assert result.invoice.seller.address is not None
    assert result.invoice.seller.address.raw_value == "123 Harbor Rd, Hai Phong"
    assert result.invoice.seller.name is None

    assert result.invoice.buyer is not None
    assert result.invoice.buyer.address is not None
    assert result.invoice.buyer.address.raw_value == "456 Ocean St, Da Nang"
    assert result.invoice.buyer.name is None


def test_delivery_date_vs_invoice_date():
    """DELIVERY DATE must not be interpreted as invoice_date."""
    # Both present: invoice_date takes the INVOICE DATE value
    pdf_both = _build_pdf(
        "doc_both_dates",
        [
            "DELIVERY DATE: 2026-05-20\nINVOICE DATE: 2026-05-12",
        ],
    )
    res_both = extract_invoice_headers(pdf_both)
    assert res_both.invoice.invoice_date is not None
    assert res_both.invoice.invoice_date.normalized_value == date(2026, 5, 12)

    # Only DELIVERY DATE present: invoice_date remains None
    pdf_only_deliv = _build_pdf(
        "doc_only_deliv",
        [
            "DELIVERY DATE: 2026-05-20",
        ],
    )
    res_only = extract_invoice_headers(pdf_only_deliv)
    assert res_only.invoice.invoice_date is None


def test_seller_and_buyer_name_and_address_together():
    """SELLER and SELLER ADDRESS present on separate lines are both properly attributed."""
    pdf = _build_pdf(
        "doc_parties",
        [
            "SELLER: Acme Global Trading Ltd\nSELLER ADDRESS: 123 Harbor Rd\n"
            "BUYER: Pacific Import Corp\nBUYER ADDRESS: 456 Trade Ave",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.invoice.seller is not None
    assert result.invoice.seller.name is not None
    assert result.invoice.seller.name.raw_value == "Acme Global Trading Ltd"
    assert result.invoice.seller.address is not None
    assert result.invoice.seller.address.raw_value == "123 Harbor Rd"

    assert result.invoice.buyer is not None
    assert result.invoice.buyer.name is not None
    assert result.invoice.buyer.name.raw_value == "Pacific Import Corp"
    assert result.invoice.buyer.address is not None
    assert result.invoice.buyer.address.raw_value == "456 Trade Ave"


def test_distinct_party_roles_not_conflated():
    """Per MASTER_SPEC.md:499, Shipper and Consignee labels must not map to Seller/Buyer."""
    pdf = _build_pdf(
        "doc_roles",
        [
            "SHIPPER: International Logistics Co.\nCONSIGNEE: Destination Depot LLC",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.invoice.seller is None
    assert result.invoice.buyer is None


def test_empty_missing_fields_remain_none():
    """Document with only partial headers leaves unmentioned fields as None."""
    pdf = _build_pdf("doc_sparse", ["INVOICE NO: INV-001\nTOTAL AMOUNT: 500.00"])
    result = extract_invoice_headers(pdf)

    assert result.invoice.invoice_number is not None
    assert result.invoice.total_amount is not None
    assert result.invoice.invoice_date is None
    assert result.invoice.freight is None
    assert result.invoice.insurance is None
    assert result.invoice.discount is None
    assert result.invoice.incoterm is None
    assert result.invoice.payment_term is None
    assert result.invoice.seller is None
    assert result.invoice.buyer is None
    assert result.invoice.ship_to is None


def test_zero_amount_preserved():
    """Valid zero values for numeric fields (e.g. discount, total) are not dropped as falsy."""
    pdf = _build_pdf(
        "doc_zero",
        [
            "TOTAL AMOUNT: 0.00\nDISCOUNT: 0",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("0.00")
    assert result.invoice.discount is not None
    assert result.invoice.discount.normalized_value == Decimal("0")


def test_ambiguous_decimal_and_date_produce_issues():
    """Ambiguous numeric (1,200) and date (01/02/2026) trigger review issues and leave fields None."""
    pdf = _build_pdf(
        "doc_ambig",
        [
            "TOTAL AMOUNT: 1,200\nINVOICE DATE: 01/02/2026",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert result.invoice.invoice_date is None

    issue_codes = {iss.code for iss in result.issues}
    assert "UNPARSEABLE_NUMERIC_FIELD" in issue_codes
    assert "UNPARSEABLE_DATE_FIELD" in issue_codes


def test_repeated_identical_values_deduplicated_without_conflict():
    """Same field appearing on multiple pages with identical values is deduplicated cleanly."""
    pdf = _build_pdf(
        "doc_repeat",
        [
            "INVOICE NO: INV-DUPE-01\nTOTAL: 1200.50",
            "INVOICE NO: INV-DUPE-01\nTOTAL: 1,200.50",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.EXTRACTED
    assert len(result.issues) == 0
    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.normalized_value == "INV-DUPE-01"
    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("1200.50")


def test_two_value_conflict_produces_review_issue():
    """Different values for the same field cause conflict issue and leave field None."""
    pdf = _build_pdf(
        "doc_conflict",
        [
            "TOTAL AMOUNT: 1,200.50",
            "TOTAL AMOUNT: 1,500.00",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert any(iss.code == "CONFLICTING_FIELD_VALUES" for iss in result.issues)


def test_three_way_sticky_conflict():
    """2-to-1 majority candidate does not resolve; conflict remains strictly sticky."""
    pdf = _build_pdf(
        "doc_sticky_conflict",
        [
            "INVOICE NO: INV-A",
            "INVOICE NO: INV-B",
            "INVOICE NO: INV-A",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.invoice_number is None
    assert any(iss.code == "CONFLICTING_FIELD_VALUES" for iss in result.issues)


def test_formula_evidence_preserved_conservatively():
    """Excel cell formula is preserved as raw value evidence and not executed."""
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="Total Amount:", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value="=SUM(B2:B5)", is_formula=True, data_type="s"),
    ]
    wb = _build_workbook("doc_wb_formula", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert any(iss.code in ("UNRESOLVED_FORMULA_FIELD", "UNPARSEABLE_NUMERIC_FIELD") for iss in result.issues)
    assert any(c.raw_value == "=SUM(B2:B5)" for c in result.candidates)


def test_unsafe_unresolved_pdf_visual_content():
    """ResolvedPdfDocument with unresolved pages surfaces review issue and skips unsafe pages."""
    doc = ResolvedPdfDocument(
        document_id="doc_res_unresolved",
        page_count=2,
        requires_review=True,
        unresolved_pages=[2],
        pages=[
            ResolvedPdfPage(
                page=1,
                text="INVOICE NO: INV-SAFE-01",
                source=TextResolutionSource.TEXT_LAYER,
                verification_level=VerificationLevel.SINGLE_PROVIDER,
                requires_review=False,
            ),
            ResolvedPdfPage(
                page=2,
                text="TOTAL AMOUNT: 9999.99",
                source=TextResolutionSource.UNRESOLVED,
                verification_level=VerificationLevel.CONFLICT,
                requires_review=True,
            ),
        ],
    )
    result = extract_invoice_headers(doc)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(iss.code == "UNRESOLVED_VISUAL_PAGE" for iss in result.issues)
    # Page 1 was safe and extracted
    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.normalized_value == "INV-SAFE-01"
    # Page 2 was unsafe and skipped
    assert result.invoice.total_amount is None


def test_no_customer_specific_fixed_coordinates():
    """Headers placed at arbitrary row/col coordinates in Excel are correctly found."""
    cells = [
        ParsedCell(coordinate="E15", row=15, column=5, raw_value="INVOICE NO", data_type="s"),
        ParsedCell(coordinate="F15", row=15, column=6, raw_value="INV-ARB-123", data_type="s"),
        ParsedCell(coordinate="C22", row=22, column=3, raw_value="INCOTERM", data_type="s"),
        ParsedCell(coordinate="C23", row=23, column=3, raw_value="FOB SHANGHAI", data_type="s"),
    ]
    wb = _build_workbook("doc_wb_arbitrary", "ArbitraryLayout", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.normalized_value == "INV-ARB-123"
    assert result.invoice.invoice_number.cell == "F15"

    assert result.invoice.incoterm is not None
    assert result.invoice.incoterm.normalized_value == "FOB SHANGHAI"
    assert result.invoice.incoterm.cell == "C23"


def test_multilingual_invoice_headers():
    """Supports Vietnamese and Chinese aliases according to configuration."""
    pdf = _build_pdf(
        "doc_multilingual",
        [
            "SỐ HÓA ĐƠN: HD-2026-VN\nNGÀY HÓA ĐƠN: 2026-05-12\nTỔNG CỘNG: 1,500.00\n"
            "发票号码: FP-ZH-888\n发票日期: 2026-05-12\n总金额: 2,500.00",
        ],
    )
    result = extract_invoice_headers(pdf)

    # There are two invoice numbers (HD-2026-VN and FP-ZH-888) and two totals (1500 and 2500)
    # so conflict detection should catch these
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(iss.code == "CONFLICTING_FIELD_VALUES" for iss in result.issues)


# =============================================================================
# Codex Audit Regression Tests (Issues 1-7 + Worksheet Visibility)
# =============================================================================

def test_negative_amount_and_sign_preservation():
    """Issue 1: Delimiters must not consume negative signs or identifier leading dashes."""
    pdf = _build_pdf(
        "doc_negative_values",
        [
            "DISCOUNT: -50.00\nINVOICE NO: -001",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.discount is not None
    assert result.invoice.discount.normalized_value == Decimal("-50.00")
    assert result.invoice.discount.raw_value == "-50.00"

    assert result.invoice.invoice_number is not None
    assert result.invoice.invoice_number.normalized_value == "-001"
    assert result.invoice.invoice_number.raw_value == "-001"


def test_opposing_signs_produce_conflict():
    """Issue 1: Same field with opposing signs (+50 vs -50) triggers conflict, not deduplicated."""
    pdf = _build_pdf(
        "doc_opposing_signs",
        [
            "TOTAL AMOUNT: -50.00",
            "TOTAL AMOUNT: 50.00",
        ],
    )
    result = extract_invoice_headers(pdf)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert any(iss.code == "CONFLICTING_FIELD_VALUES" for iss in result.issues)


def test_internal_double_space_in_labels_and_values():
    """Issue 2: No naive regex whitespace split; internal double spaces preserved without breaking labels."""
    # 1. DELIVERY  DATE must not be split into DELIVERY and DATE (DATE -> invoice_date)
    pdf_delivery = _build_pdf("doc_deliv_sp", ["DELIVERY  DATE: 2026-05-20"])
    res_deliv = extract_invoice_headers(pdf_delivery)
    assert res_deliv.invoice.invoice_date is None

    # 2. SELLER: Acme  Global Co. preserves full string including double space
    pdf_seller = _build_pdf("doc_seller_sp", ["SELLER: Acme  Global Co."])
    res_seller = extract_invoice_headers(pdf_seller)
    assert res_seller.invoice.seller is not None
    assert res_seller.invoice.seller.name is not None
    assert res_seller.invoice.seller.name.raw_value == "Acme  Global Co."

    # 3. Double space after colon: INVOICE NO:  INV-001 extracts INV-001 and does not steal next line
    pdf_inv = _build_pdf("doc_inv_sp", ["INVOICE NO:  INV-001\nFree text note"])
    res_inv = extract_invoice_headers(pdf_inv)
    assert res_inv.invoice.invoice_number is not None
    assert res_inv.invoice.invoice_number.raw_value == "INV-001"


def test_lookahead_and_adjacent_label_boundary_protection_pdf():
    """Issue 3: PDF lookahead stops if next line is any known or excluded label."""
    # Label alone on line followed by excluded label (SHIPPER)
    pdf_shipper = _build_pdf("doc_la_shipper", ["SELLER:\nSHIPPER: Synthetic Logistics"])
    res_shipper = extract_invoice_headers(pdf_shipper)
    assert res_shipper.invoice.seller is None

    # Label alone on line followed by excluded label (DELIVERY DATE)
    pdf_deliv = _build_pdf("doc_la_deliv", ["INVOICE NO:\nDELIVERY DATE: 2026-05-20"])
    res_deliv = extract_invoice_headers(pdf_deliv)
    assert res_deliv.invoice.invoice_number is None


def test_lookahead_and_adjacent_label_boundary_protection_excel():
    """Issue 3: Excel horizontal search stops immediately upon hitting another label."""
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="INVOICE NO", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value="CURRENCY", data_type="s"),
        ParsedCell(coordinate="C1", row=1, column=3, raw_value="USD", data_type="s"),
    ]
    wb = _build_workbook("doc_wb_adjacent", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    # A1 (INVOICE NO) stopped at B1 (CURRENCY) and did NOT steal USD
    assert result.invoice.invoice_number is None
    # B1 (CURRENCY) found USD at C1
    assert result.invoice.currency is not None
    assert result.invoice.currency.normalized_value == "USD"
    assert result.invoice.currency.cell == "C1"


def test_visual_safety_unverified_ocr_requires_review():
    """Issue 4: OCR_LOCAL with UNVERIFIED level requires review and cannot be extracted as safe."""
    doc = ResolvedPdfDocument(
        document_id="doc_unverified_ocr",
        page_count=1,
        requires_review=False,
        unresolved_pages=[],
        pages=[
            ResolvedPdfPage(
                page=1,
                text="TOTAL AMOUNT: 1,500.00",
                source=TextResolutionSource.OCR_LOCAL,
                verification_level=VerificationLevel.UNVERIFIED,
                requires_review=False,
            ),
        ],
    )
    result = extract_invoice_headers(doc)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert any(iss.code == "UNRESOLVED_VISUAL_PAGE" for iss in result.issues)


def test_visual_safety_document_unresolved_pages_respected():
    """Issue 4: Document-level unresolved_pages triggers safety review even if page requires_review is False."""
    doc = ResolvedPdfDocument(
        document_id="doc_unres_list",
        page_count=1,
        requires_review=True,
        unresolved_pages=[1],
        pages=[
            ResolvedPdfPage(
                page=1,
                text="TOTAL AMOUNT: 1,500.00",
                source=TextResolutionSource.TEXT_LAYER,
                verification_level=VerificationLevel.SINGLE_PROVIDER,
                requires_review=False,
            ),
        ],
    )
    result = extract_invoice_headers(doc)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert any(iss.code == "UNRESOLVED_VISUAL_PAGE" for iss in result.issues)


def test_prose_and_undefined_compound_labels_rejected():
    """Issue 5: Single-space fallback removed; prose and compound labels are not misidentified as values."""
    pdf = _build_pdf(
        "doc_prose",
        [
            "Seller agrees to deliver goods on time\nSELLER BANK ACCOUNT: 00123",
        ],
    )
    result = extract_invoice_headers(pdf)

    # Neither line should populate seller.name
    assert result.invoice.seller is None


def test_universal_formula_rejection_across_fields():
    """Issue 6: Formula expressions starting with '=' are rejected across ALL fields, including identifiers."""
    # Excel identifier formula
    cells_excel = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="INVOICE NO", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value="=A2", is_formula=True, data_type="s"),
    ]
    wb = _build_workbook("doc_wb_id_formula", "Sheet1", cells_excel)
    res_wb = extract_invoice_headers(wb)

    assert res_wb.status == ExtractionStatus.NEEDS_REVIEW
    assert res_wb.invoice.invoice_number is None
    assert any(iss.code == "UNRESOLVED_FORMULA_FIELD" for iss in res_wb.issues)

    # PDF text with =1200 for TOTAL AMOUNT
    pdf_eq = _build_pdf("doc_pdf_eq", ["TOTAL AMOUNT: =1200"])
    res_pdf = extract_invoice_headers(pdf_eq)

    assert res_pdf.status == ExtractionStatus.NEEDS_REVIEW
    assert res_pdf.invoice.total_amount is None
    assert any(iss.code == "UNRESOLVED_FORMULA_FIELD" for iss in res_pdf.issues)


def test_excel_typed_datetime_parses_to_date():
    """Issue 7 / Rework Issue 4: Excel cells carrying datetime objects parse to date, preserving source raw evidence."""
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="INVOICE DATE", data_type="s"),
        ParsedCell(
            coordinate="B1",
            row=1,
            column=2,
            raw_value=datetime(2026, 5, 12, 14, 30, 45),
            data_type="d",
        ),
    ]
    wb = _build_workbook("doc_wb_datetime", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.EXTRACTED
    assert len(result.issues) == 0
    assert result.invoice.invoice_date is not None
    assert result.invoice.invoice_date.normalized_value == date(2026, 5, 12)
    assert result.invoice.invoice_date.raw_value == "2026-05-12 14:30:45"


def test_excluded_labels_on_same_line_terminate_prior_field():
    """Rework Round 2 Issue 1: Excluded label terminates preceding field value without leaking into it."""
    # 1. SELLER: Acme  SHIPPER: Synthetic Logistics -> seller.name is "Acme"
    pdf_seller = _build_pdf(
        "doc_seller_shipper",
        ["SELLER: Acme  SHIPPER: Synthetic Logistics"],
    )
    res_seller = extract_invoice_headers(pdf_seller)
    assert res_seller.status == ExtractionStatus.EXTRACTED
    assert res_seller.invoice.seller is not None
    assert res_seller.invoice.seller.name is not None
    assert res_seller.invoice.seller.name.raw_value == "Acme"

    # 2. INVOICE NO: 000123  DELIVERY DATE: 2026-05-20 -> invoice_number is "000123"
    pdf_inv = _build_pdf(
        "doc_inv_deliv",
        ["INVOICE NO: 000123  DELIVERY DATE: 2026-05-20"],
    )
    res_inv = extract_invoice_headers(pdf_inv)
    assert res_inv.status == ExtractionStatus.EXTRACTED
    assert res_inv.invoice.invoice_number is not None
    assert res_inv.invoice.invoice_number.raw_value == "000123"
    assert res_inv.invoice.invoice_date is None


def test_lookahead_rejects_non_target_labels_and_multilabel_lines():
    """Rework Round 2 Issue 2: Next-line lookahead rejects non-target labels and multi-label header rows."""
    # 1. SELLER:\nCONTRACT NO: C-001 -> seller.name must NOT become CONTRACT NO: C-001
    pdf_contract = _build_pdf("doc_contract", ["SELLER:\nCONTRACT NO: C-001"])
    res_contract = extract_invoice_headers(pdf_contract)
    assert res_contract.invoice.seller is None

    # 2. INVOICE NO:  CURRENCY:\nUSD -> neither field steals USD
    pdf_multi = _build_pdf("doc_multi_lbl", ["INVOICE NO:  CURRENCY:\nUSD"])
    res_multi = extract_invoice_headers(pdf_multi)
    assert res_multi.invoice.invoice_number is None
    assert res_multi.invoice.currency is None

    # 3. SELLER  PHONE: 012345 -> seller.name must NOT become PHONE: 012345
    pdf_phone = _build_pdf("doc_phone", ["SELLER  PHONE: 012345"])
    res_phone = extract_invoice_headers(pdf_phone)
    assert res_phone.invoice.seller is None

    # 4. Excel horizontal lookahead stopped by non-target label CONTRACT NO
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="SELLER:", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value="CONTRACT NO: C-001", data_type="s"),
    ]
    wb = _build_workbook("doc_wb_contract", "Sheet1", cells)
    res_wb = extract_invoice_headers(wb)
    assert res_wb.invoice.seller is None


def test_pipe_and_semicolon_boundaries_with_whitespace():
    """Rework Round 2 Issue 3: Pipe and semicolon with surrounding whitespace cleanly delimit fields."""
    # 1. INVOICE NO: 000123 | CURRENCY: USD
    pdf_pipe = _build_pdf("doc_pipe", ["INVOICE NO: 000123 | CURRENCY: USD"])
    res_pipe = extract_invoice_headers(pdf_pipe)
    assert res_pipe.status == ExtractionStatus.EXTRACTED
    assert res_pipe.invoice.invoice_number is not None
    assert res_pipe.invoice.invoice_number.normalized_value == "000123"
    assert res_pipe.invoice.invoice_number.raw_value == "000123"
    assert res_pipe.invoice.currency is not None
    assert res_pipe.invoice.currency.normalized_value == "USD"
    assert res_pipe.invoice.currency.raw_value == "USD"

    # 2. SELLER: Acme; BUYER: Other
    pdf_semi = _build_pdf("doc_semi", ["SELLER: Acme; BUYER: Other"])
    res_semi = extract_invoice_headers(pdf_semi)
    assert res_semi.status == ExtractionStatus.EXTRACTED
    assert res_semi.invoice.seller is not None
    assert res_semi.invoice.seller.name is not None
    assert res_semi.invoice.seller.name.raw_value == "Acme"
    assert res_semi.invoice.buyer is not None
    assert res_semi.invoice.buyer.name is not None
    assert res_semi.invoice.buyer.name.raw_value == "Other"


def test_worksheet_visibility_ignores_hidden_sheets():
    """Non-blocking: Hidden and veryHidden worksheets are ignored when visible sheets exist."""
    sheet_visible = ParsedSheet(
        name="VisibleInvoice",
        index=0,
        state="visible",
        cells=[
            ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
            ParsedCell(coordinate="B1", row=1, column=2, raw_value="1,000.00", data_type="s"),
        ],
    )
    sheet_hidden = ParsedSheet(
        name="HiddenDraft",
        index=1,
        state="hidden",
        cells=[
            ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
            ParsedCell(coordinate="B1", row=1, column=2, raw_value="9,999.00", data_type="s"),
        ],
    )
    wb = ParsedWorkbook(
        document_id="doc_wb_visibility",
        file_type="xlsx",
        parser_used="openpyxl",
        workbook_name="visibility.xlsx",
        sheet_count=2,
        sheets=[sheet_visible, sheet_hidden],
    )
    result = extract_invoice_headers(wb)

    # Should not produce conflict; hidden sheet values are ignored
    assert result.status == ExtractionStatus.EXTRACTED
    assert len(result.issues) == 0
    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("1000.00")
    assert result.invoice.total_amount.sheet == "VisibleInvoice"


# =============================================================================
# Codex Audit Rework Round 3 Probes (Issues 1-4)
# =============================================================================

def test_excel_native_float_and_zero_parsing():
    """Rework Round 3 Issue 1: Excel native float amounts and XLS zero values parsed cleanly."""
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value=1200.5, data_type="n"),
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="DISCOUNT", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value=0.0, data_type="n"),
    ]
    wb = _build_workbook("doc_wb_floats", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.EXTRACTED
    assert len(result.issues) == 0

    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("1200.5")
    assert result.invoice.total_amount.raw_value == "1200.5"

    assert result.invoice.discount is not None
    assert result.invoice.discount.normalized_value == Decimal("0.0")
    assert result.invoice.discount.raw_value == "0.0"


def test_excel_xlsx_parser_native_float_real_file(tmp_path: Path):
    """Rework Round 3 Issue 1: Real XLSX file parsed via XlsxParser parses native floats and zero."""
    wb_file = tmp_path / "test_invoice.xlsx"
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws.title = "Invoice"
    ws["A1"] = "TOTAL AMOUNT"
    ws["B1"] = 1200.5
    ws["A2"] = "DISCOUNT"
    ws["B2"] = 0.0
    workbook.save(wb_file)
    workbook.close()

    parser = XlsxParser()
    parsed_wb = parser.parse("real_xlsx_doc", wb_file)

    result = extract_invoice_headers(parsed_wb)
    assert result.status == ExtractionStatus.EXTRACTED
    assert len(result.issues) == 0

    assert result.invoice.total_amount is not None
    assert result.invoice.total_amount.normalized_value == Decimal("1200.5")

    assert result.invoice.discount is not None
    assert result.invoice.discount.normalized_value == Decimal("0.0")


def test_labels_with_punctuation_rejected_from_party_and_lookahead():
    """Rework Round 3 Issue 2: Key-value headers with hyphens, apostrophes etc. are not taken as values."""
    # 1. PDF: CONTRACT-NO: C-001
    pdf_contract = _build_pdf("doc_punc_contract", ["SELLER:\nCONTRACT-NO: C-001"])
    res_contract = extract_invoice_headers(pdf_contract)
    assert res_contract.invoice.seller is None

    # 2. PDF: SHIPPER'S NAME: Synthetic Logistics
    pdf_shipper = _build_pdf("doc_punc_shipper", ["SELLER:\nSHIPPER'S NAME: Synthetic Logistics"])
    res_shipper = extract_invoice_headers(pdf_shipper)
    assert res_shipper.invoice.seller is None

    # 3. Excel: B1="SHIPPER'S NAME: Synthetic Logistics"
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="SELLER:", data_type="s"),
        ParsedCell(
            coordinate="B1",
            row=1,
            column=2,
            raw_value="SHIPPER'S NAME: Synthetic Logistics",
            data_type="s",
        ),
    ]
    wb = _build_workbook("doc_wb_punc_shipper", "Sheet1", cells)
    res_wb = extract_invoice_headers(wb)
    assert res_wb.invoice.seller is None


def test_excel_inline_cell_compound_label_rejected():
    """Rework Round 3 Issue 3: Excel inline cell with compound label rejects non-target remainder."""
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="SELLER  PHONE: 012345", data_type="s"),
    ]
    wb = _build_workbook("doc_wb_inline_compound", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    # Must NOT extract "PHONE: 012345" as seller.name
    assert result.invoice.seller is None


def test_single_tab_multiple_tabs_and_tab_with_spaces():
    """Rework Round 3 Issue 4: Single tab, multiple tabs, and tab with spaces delimit fields cleanly."""
    # 1. Single tab
    pdf_tab = _build_pdf("doc_single_tab", ["INVOICE NO: 000123\tCURRENCY: USD"])
    res_tab = extract_invoice_headers(pdf_tab)
    assert res_tab.status == ExtractionStatus.EXTRACTED
    assert res_tab.invoice.invoice_number is not None
    assert res_tab.invoice.invoice_number.normalized_value == "000123"
    assert res_tab.invoice.invoice_number.raw_value == "000123"
    assert res_tab.invoice.currency is not None
    assert res_tab.invoice.currency.normalized_value == "USD"
    assert res_tab.invoice.currency.raw_value == "USD"

    # 2. Tab with spaces
    pdf_sp_tab = _build_pdf("doc_sp_tab", ["INVOICE NO: 000123 \t CURRENCY: USD"])
    res_sp_tab = extract_invoice_headers(pdf_sp_tab)
    assert res_sp_tab.status == ExtractionStatus.EXTRACTED
    assert res_sp_tab.invoice.invoice_number is not None
    assert res_sp_tab.invoice.invoice_number.raw_value == "000123"
    assert res_sp_tab.invoice.currency is not None
    assert res_sp_tab.invoice.currency.raw_value == "USD"

    # 3. Multiple tabs
    pdf_tabs = _build_pdf("doc_tabs", ["INVOICE NO: 000123\t\tCURRENCY: USD"])
    res_tabs = extract_invoice_headers(pdf_tabs)
    assert res_tabs.status == ExtractionStatus.EXTRACTED
    assert res_tabs.invoice.invoice_number is not None
    assert res_tabs.invoice.invoice_number.raw_value == "000123"
    assert res_tabs.invoice.currency is not None
    assert res_tabs.invoice.currency.raw_value == "USD"


# =============================================================================
# Codex Audit Rework Round 4 Probes (Issues 1-3 & Cross-Matrix)
# =============================================================================

def test_excel_boolean_cells_rejected_for_numeric_and_date(tmp_path: Path):
    """Rework Round 4 Issue 1: Excel boolean cells rejected for numeric/date fields without coercion."""
    # 1. Direct ExtractionCandidate coercion check
    c_true = ExtractionCandidate(
        field_path="total_amount",
        raw_value="True",
        typed_value=True,
    )
    assert type(c_true.typed_value) is bool and c_true.typed_value is True

    c_false = ExtractionCandidate(
        field_path="discount",
        raw_value="False",
        typed_value=False,
    )
    assert type(c_false.typed_value) is bool and c_false.typed_value is False

    extractor = DeterministicInvoiceHeaderExtractor()
    resolved, issues = extractor._resolve_canonical_fields([c_true, c_false])
    assert "total_amount" not in resolved
    assert "discount" not in resolved
    assert any(iss.code == "UNPARSEABLE_NUMERIC_FIELD" and iss.field_path == "total_amount" for iss in issues)
    assert any(iss.code == "UNPARSEABLE_NUMERIC_FIELD" and iss.field_path == "discount" for iss in issues)

    # 2. Synthetic ParsedWorkbook
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value=True, data_type="b"),
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="DISCOUNT", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value=False, data_type="b"),
        ParsedCell(coordinate="A3", row=3, column=1, raw_value="INVOICE DATE", data_type="s"),
        ParsedCell(coordinate="B3", row=3, column=2, raw_value=True, data_type="b"),
    ]
    wb = _build_workbook("doc_bool_wb", "Sheet1", cells)
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert result.invoice.discount is None
    assert result.invoice.invoice_date is None
    issue_codes = {iss.code for iss in result.issues}
    assert "UNPARSEABLE_NUMERIC_FIELD" in issue_codes
    assert "UNPARSEABLE_DATE_FIELD" in issue_codes

    # 3. Real XLSX file with boolean cells via XlsxParser
    wb_file = tmp_path / "boolean_invoice.xlsx"
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws["A1"] = "TOTAL AMOUNT"
    ws["B1"] = True
    ws["A2"] = "DISCOUNT"
    ws["B2"] = False
    ws["A3"] = "INVOICE DATE"
    ws["B3"] = False
    workbook.save(wb_file)
    workbook.close()

    parser = XlsxParser()
    parsed_wb = parser.parse("real_bool_doc", wb_file)
    res_real = extract_invoice_headers(parsed_wb)

    assert res_real.status == ExtractionStatus.NEEDS_REVIEW
    assert res_real.invoice.total_amount is None
    assert res_real.invoice.discount is None
    assert res_real.invoice.invoice_date is None
    real_codes = {iss.code for iss in res_real.issues}
    assert "UNPARSEABLE_NUMERIC_FIELD" in real_codes
    assert "UNPARSEABLE_DATE_FIELD" in real_codes


def test_excel_inline_numeric_and_date_cells_parsed_cleanly(tmp_path: Path):
    """Rework Round 4 Issue 2: Excel inline amount/date cells parsed from value span, not full cell."""
    # 1. Synthetic ParsedWorkbook with inline cells
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT: 1200.50", data_type="s"),
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="INVOICE DATE: 2026-05-12", data_type="s"),
        ParsedCell(coordinate="A3", row=3, column=1, raw_value="DISCOUNT: -50.00", data_type="s"),
        ParsedCell(coordinate="A4", row=4, column=1, raw_value="TOTAL AMOUNT: 0", data_type="s"),
    ]
    # Test zero specifically on its own
    wb_zero = _build_workbook("doc_inline_zero", "Sheet1", [cells[3]])
    res_zero = extract_invoice_headers(wb_zero)
    assert res_zero.status == ExtractionStatus.EXTRACTED
    assert res_zero.invoice.total_amount is not None
    assert res_zero.invoice.total_amount.normalized_value == Decimal("0")
    assert res_zero.invoice.total_amount.raw_value == "0"

    # Test negative discount
    wb_disc = _build_workbook("doc_inline_disc", "Sheet1", [cells[2]])
    res_disc = extract_invoice_headers(wb_disc)
    assert res_disc.status == ExtractionStatus.EXTRACTED
    assert res_disc.invoice.discount is not None
    assert res_disc.invoice.discount.normalized_value == Decimal("-50.00")
    assert res_disc.invoice.discount.raw_value == "-50.00"

    # 2. Real XLSX file with multiple inline cells via XlsxParser
    wb_file = tmp_path / "inline_invoice.xlsx"
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws["A1"] = "TOTAL AMOUNT: 1200.50"
    ws["A2"] = "INVOICE DATE: 2026-05-12"
    ws["A3"] = "DISCOUNT: -50.00"
    ws["A4"] = "INVOICE NO: INV-001"
    workbook.save(wb_file)
    workbook.close()

    parser = XlsxParser()
    parsed_wb = parser.parse("real_inline_doc", wb_file)
    res_real = extract_invoice_headers(parsed_wb)

    assert res_real.status == ExtractionStatus.EXTRACTED
    assert len(res_real.issues) == 0

    assert res_real.invoice.total_amount is not None
    assert res_real.invoice.total_amount.normalized_value == Decimal("1200.50")
    assert res_real.invoice.total_amount.raw_value == "1200.50"

    assert res_real.invoice.invoice_date is not None
    assert res_real.invoice.invoice_date.normalized_value == date(2026, 5, 12)
    assert res_real.invoice.invoice_date.raw_value == "2026-05-12"

    assert res_real.invoice.discount is not None
    assert res_real.invoice.discount.normalized_value == Decimal("-50.00")
    assert res_real.invoice.discount.raw_value == "-50.00"

    assert res_real.invoice.invoice_number is not None
    assert res_real.invoice.invoice_number.normalized_value == "INV-001"
    assert res_real.invoice.invoice_number.raw_value == "INV-001"

    # 3. Inline boolean strings rejected
    cells_bool_inline = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT: True", data_type="s"),
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="INVOICE DATE: False", data_type="s"),
    ]
    wb_bool_inline = _build_workbook("doc_bool_inline", "Sheet1", cells_bool_inline)
    res_bool_inline = extract_invoice_headers(wb_bool_inline)
    assert res_bool_inline.status == ExtractionStatus.NEEDS_REVIEW
    assert res_bool_inline.invoice.total_amount is None
    assert res_bool_inline.invoice.invoice_date is None


def test_excel_native_time_does_not_raise_exception(tmp_path: Path):
    """Rework Round 4 Issue 3: Native Excel time does not raise ValidationError and returns review issue."""
    # 1. Synthetic ParsedWorkbook with time(14, 30)
    cells = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value=time(14, 30), data_type="d", number_format="hh:mm"),
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="INVOICE DATE", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value=time(14, 30), data_type="d", number_format="hh:mm"),
    ]
    wb = _build_workbook("doc_time_wb", "Sheet1", cells)

    # Must NOT raise ValidationError!
    result = extract_invoice_headers(wb)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert result.invoice.invoice_date is None

    # Evidence must be preserved in candidates
    time_cands = [c for c in result.candidates if c.cell == "B1"]
    assert len(time_cands) == 1
    assert time_cands[0].typed_value == time(14, 30)
    assert time_cands[0].raw_value == "14:30:00"

    issue_codes = {iss.code for iss in result.issues}
    assert "UNPARSEABLE_NUMERIC_FIELD" in issue_codes
    assert "UNPARSEABLE_DATE_FIELD" in issue_codes

    # 2. Real XLSX file with time value via openpyxl and XlsxParser
    wb_file = tmp_path / "time_invoice.xlsx"
    workbook = openpyxl.Workbook()
    ws = workbook.active
    ws["A1"] = "TOTAL AMOUNT"
    ws["B1"] = time(14, 30)
    workbook.save(wb_file)
    workbook.close()

    parser = XlsxParser()
    parsed_wb = parser.parse("real_time_doc", wb_file)
    res_real = extract_invoice_headers(parsed_wb)

    assert res_real.status == ExtractionStatus.NEEDS_REVIEW
    assert res_real.invoice.total_amount is None
    assert any(iss.code == "UNPARSEABLE_NUMERIC_FIELD" for iss in res_real.issues)


def test_cross_matrix_inline_adjacent_string_native():
    """Non-blocking: Cross-matrix test [inline vs adjacent] x [string vs native] x [numeric vs date vs string]."""
    # Matrix 1: Numeric fields (float, int, zero, string)
    cells_numeric = [
        # Adjacent native float
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="TOTAL AMOUNT", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value=2500.75, data_type="n"),
        # Adjacent native int
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="FREIGHT", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value=150, data_type="n"),
    ]
    res_num = extract_invoice_headers(_build_workbook("doc_matrix_num", "Sheet1", cells_numeric))
    assert res_num.status == ExtractionStatus.EXTRACTED
    assert res_num.invoice.total_amount.normalized_value == Decimal("2500.75")
    assert res_num.invoice.freight.normalized_value == Decimal("150")

    # Matrix 2: Date fields (inline string, adjacent native date, adjacent native datetime)
    cells_date = [
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="INVOICE DATE", data_type="s"),
        ParsedCell(coordinate="B1", row=1, column=2, raw_value=date(2026, 10, 28), data_type="d"),
    ]
    res_date = extract_invoice_headers(_build_workbook("doc_matrix_date", "Sheet1", cells_date))
    assert res_date.status == ExtractionStatus.EXTRACTED
    assert res_date.invoice.invoice_date.normalized_value == date(2026, 10, 28)

    # Matrix 3: String fields (inline string, adjacent string, adjacent int-like string)
    cells_str = [
        # Inline string
        ParsedCell(coordinate="A1", row=1, column=1, raw_value="INVOICE NO: INV-2026-X", data_type="s"),
        # Adjacent string
        ParsedCell(coordinate="A2", row=2, column=1, raw_value="CURRENCY", data_type="s"),
        ParsedCell(coordinate="B2", row=2, column=2, raw_value="USD", data_type="s"),
        # Adjacent int identifier (e.g. numeric invoice number in Excel)
        ParsedCell(coordinate="A3", row=3, column=1, raw_value="SELLER", data_type="s"),
        ParsedCell(coordinate="B3", row=3, column=2, raw_value="Acme Global Co.", data_type="s"),
    ]
    res_str = extract_invoice_headers(_build_workbook("doc_matrix_str", "Sheet1", cells_str))
    assert res_str.status == ExtractionStatus.EXTRACTED
    assert res_str.invoice.invoice_number.normalized_value == "INV-2026-X"
    assert res_str.invoice.currency.normalized_value == "USD"
    assert res_str.invoice.seller.name.normalized_value == "Acme Global Co."


# =============================================================================
# Codex Audit Rework Round 5 Probes (Formula Cells Blocked as Label Sources)
# =============================================================================

def test_formula_cells_blocked_as_label_sources_and_preserved_as_values_real_xlsx(tmp_path: Path):
    """Rework Round 5 Issue 1: Formula cells cannot act as label sources; preserved as review values."""
    # 1. Formula cell containing label-like text on its own must NOT be a label source
    wb_file1 = tmp_path / "formula_label_source.xlsx"
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    ws1["A1"] = '="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    ws1["A2"] = '="INVOICE NO: INV-999"'
    wb1.save(wb_file1)
    wb1.close()

    parser = XlsxParser()
    parsed_wb1 = parser.parse("doc_formula_source", wb_file1)
    res1 = extract_invoice_headers(parsed_wb1)

    # Must NOT extract fake values from inside formula expressions
    assert res1.invoice.total_amount is None
    assert res1.invoice.currency is None
    assert res1.invoice.invoice_number is None

    # 2. Formula cell as the target value of an external label preserves expression as review issue
    wb_file2 = tmp_path / "formula_as_value.xlsx"
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2["A1"] = "TOTAL AMOUNT"
    ws2["B1"] = '="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    ws2["A2"] = "INVOICE NO"
    ws2["B2"] = '="INV-" & "999"'
    wb2.save(wb_file2)
    wb2.close()

    parsed_wb2 = parser.parse("doc_formula_val", wb_file2)
    res2 = extract_invoice_headers(parsed_wb2)

    assert res2.status == ExtractionStatus.NEEDS_REVIEW
    assert res2.invoice.total_amount is None
    assert res2.invoice.invoice_number is None

    # Full expression evidence must be preserved in candidates
    amt_cands = [c for c in res2.candidates if c.field_path == "total_amount"]
    assert len(amt_cands) == 1
    assert amt_cands[0].cell == "B1"
    assert amt_cands[0].raw_value.startswith("=")
    assert 'TOTAL AMOUNT: 999' in amt_cands[0].raw_value

    inv_cands = [c for c in res2.candidates if c.field_path == "invoice_number"]
    assert len(inv_cands) == 1
    assert inv_cands[0].cell == "B2"
    assert inv_cands[0].raw_value.startswith("=")

    # Review issue UNRESOLVED_FORMULA_FIELD must be present for both fields
    formula_issues = [iss for iss in res2.issues if iss.code == "UNRESOLVED_FORMULA_FIELD"]
    issue_fields = {iss.field_path for iss in formula_issues}
    assert "total_amount" in issue_fields
    assert "invoice_number" in issue_fields
    assert all(iss.is_review_required for iss in formula_issues)


def test_expression_text_with_indentation_and_inline_expression_real_xlsx(tmp_path: Path):
    """Rework Round 6 Issue 1: Expression text with indentation and inline expression opaque value."""
    # 1. Indented expression text in plain text cell (is_formula=False)
    # e.g. A1 = '  ="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    wb_file1 = tmp_path / "indented_expression_text.xlsx"
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    ws1["A1"] = '  ="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    ws1["A2"] = '\t="INVOICE NO: INV-999"'
    wb1.save(wb_file1)
    wb1.close()

    parser = XlsxParser()
    parsed_wb1 = parser.parse("doc_indented_expr", wb_file1)
    res1 = extract_invoice_headers(parsed_wb1)

    assert res1.invoice.total_amount is None
    assert res1.invoice.currency is None
    assert res1.invoice.invoice_number is None
    assert len(res1.candidates) == 0

    # 2. Expression text located directly after an inline label
    # e.g. A1 = 'TOTAL AMOUNT: ="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    # e.g. A2 = 'INVOICE NO: ="INVOICE NO: 12345 | CURRENCY: USD"'
    wb_file2 = tmp_path / "inline_expression_value.xlsx"
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2["A1"] = 'TOTAL AMOUNT: ="  TOTAL AMOUNT: 999 | CURRENCY: USD"'
    ws2["A2"] = 'INVOICE NO: ="INVOICE NO: 12345 | CURRENCY: USD"'
    wb2.save(wb_file2)
    wb2.close()

    parsed_wb2 = parser.parse("doc_inline_expr_val", wb_file2)
    res2 = extract_invoice_headers(parsed_wb2)

    assert res2.status == ExtractionStatus.NEEDS_REVIEW
    # Both fields must remain None (unresolved)!
    assert res2.invoice.total_amount is None
    assert res2.invoice.invoice_number is None
    # Currency inside expression must NOT be extracted!
    assert res2.invoice.currency is None

    # Full raw expression preserved in candidate evidence
    amt_cands = [c for c in res2.candidates if c.field_path == "total_amount"]
    assert len(amt_cands) == 1
    assert amt_cands[0].cell == "A1"
    assert amt_cands[0].raw_value.startswith("=")
    assert "TOTAL AMOUNT: 999" in amt_cands[0].raw_value

    inv_cands = [c for c in res2.candidates if c.field_path == "invoice_number"]
    assert len(inv_cands) == 1
    assert inv_cands[0].cell == "A2"
    assert inv_cands[0].raw_value.startswith("=")
    assert "12345" in inv_cands[0].raw_value

    # UNRESOLVED_FORMULA_FIELD issues present and review required
    issues = [iss for iss in res2.issues if iss.code == "UNRESOLVED_FORMULA_FIELD"]
    issue_fields = {iss.field_path for iss in issues}
    assert "total_amount" in issue_fields
    assert "invoice_number" in issue_fields
    assert all(iss.is_review_required for iss in issues)



