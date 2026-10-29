"""Real XLSX regressions for grouped hidden-column metadata and consumers."""

from hashlib import sha256

from openpyxl import Workbook
import pytest

from customs_ai.application.invoice_extraction import InvoiceExtractionService
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.headers import DeterministicInvoiceHeaderExtractor
from customs_ai.extraction.packing_headers import DeterministicPackingHeaderExtractor
from customs_ai.parsers.excel import XlsxParser


def parse_synthetic(tmp_path, *, groups=(), hidden_single=None, cells=None):
    path = tmp_path / "synthetic-grouped-columns.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Synthetic Visible Sheet"
    for start, end, hidden in groups:
        worksheet.column_dimensions.group(start, end, hidden=hidden)
    if hidden_single is not None:
        worksheet.column_dimensions[hidden_single].hidden = True
    for coordinate, value in (cells or {"A1": "Synthetic"}).items():
        worksheet[coordinate] = value
    workbook.save(path)
    workbook.close()
    source_hash = sha256(path.read_bytes()).hexdigest()
    parsed = XlsxParser().parse("DOC-GROUPED-COLUMNS", path)
    assert sha256(path.read_bytes()).hexdigest() == source_hash
    return parsed, path, source_hash


def test_single_hidden_column_is_preserved(tmp_path):
    parsed, _, _ = parse_synthetic(tmp_path, hidden_single="C")
    assert parsed.sheets[0].hidden_columns == ["C"]


def test_group_b_through_d_reports_every_hidden_column(tmp_path):
    parsed, _, _ = parse_synthetic(tmp_path, groups=[("B", "D", True)])
    assert parsed.sheets[0].hidden_columns == ["B", "C", "D"]


def test_nonhidden_group_does_not_hide_columns(tmp_path):
    parsed, _, _ = parse_synthetic(tmp_path, groups=[("B", "D", False)])
    assert parsed.sheets[0].hidden_columns == []


def test_disjoint_groups_preserve_all_hidden_members_and_outside_visibility(tmp_path):
    parsed, _, _ = parse_synthetic(
        tmp_path, groups=[("B", "D", True), ("G", "H", True), ("J", "L", False)],
    )
    hidden = parsed.sheets[0].hidden_columns
    assert hidden == ["B", "C", "D", "G", "H"]
    assert not {"A", "E", "F", "I", "J", "K", "L", "M"}.intersection(hidden)


@pytest.mark.parametrize("hidden_member", ["C", "D"])
def test_group_hidden_business_values_cannot_be_trusted_by_packing_headers(tmp_path, hidden_member):
    parsed, path, source_hash = parse_synthetic(
        tmp_path, groups=[("B", "D", True)],
        cells={
            f"{hidden_member}7": "TOTAL PACKAGES: 900",
            "G17": "PACKING LIST NO", "H17": "000017",
        },
    )

    result = DeterministicPackingHeaderExtractor().extract(parsed)

    assert result.packing_list.package_count is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.is_review_required for issue in result.issues)
    assert result.packing_list.packing_list_number.normalized_value == "000017"
    assert result.packing_list.packing_list_number.raw_value == "000017"
    assert result.packing_list.packing_list_number.source_document_id == "DOC-GROUPED-COLUMNS"
    assert result.packing_list.packing_list_number.sheet == "Synthetic Visible Sheet"
    assert result.packing_list.packing_list_number.cell == "H17"
    assert not any(candidate.field_path == "package_count" for candidate in result.candidates)
    assert sha256(path.read_bytes()).hexdigest() == source_hash


@pytest.mark.parametrize("hidden_member", ["C", "D"])
def test_invoice_production_visibility_policy_excludes_every_hidden_group_member(tmp_path, hidden_member):
    parsed, path, source_hash = parse_synthetic(
        tmp_path, groups=[("B", "D", True)],
        cells={
            f"{hidden_member}7": "SELLER: Synthetic Hidden Company",
            "G17": "INVOICE NO", "H17": "000019",
        },
    )

    visible, omitted = InvoiceExtractionService._visible_workbook(parsed)
    result = DeterministicInvoiceHeaderExtractor().extract(visible)

    assert result.invoice.seller is None
    assert omitted is True
    assert {cell.coordinate for cell in visible.sheets[0].cells} == {"G17", "H17"}
    assert result.invoice.invoice_number.normalized_value == "000019"
    assert result.invoice.invoice_number.raw_value == "000019"
    assert result.invoice.invoice_number.source_document_id == "DOC-GROUPED-COLUMNS"
    assert result.invoice.invoice_number.sheet == "Synthetic Visible Sheet"
    assert result.invoice.invoice_number.cell == "H17"
    assert sha256(path.read_bytes()).hexdigest() == source_hash
