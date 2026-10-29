"""Native PDF/Excel production flows, including real ingestion and SQLite reads."""

from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest

from customs_ai.classification.enums import DocumentType
from customs_ai.config import VisionSettingsConfig
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.document_extractions import DocumentExtractionRepository
from customs_ai.vision.service import VisualResolutionService


def _run(pipeline, path, **kwargs):
    source = pipeline.register(path)
    assert source.processing_status == ProcessingStatus.UPLOADED
    original = pipeline.source_bytes(source.document_id)
    classified = pipeline.classify(source.document_id)
    assert classified.document_type == DocumentType.COMMERCIAL_INVOICE
    before = pipeline.repo.get_by_document_id(source.document_id)
    assert before.processing_status == ProcessingStatus.CLASSIFIED
    outcome = pipeline.extract(source.document_id, **kwargs)
    assert outcome.persisted
    fetched = DocumentExtractionRepository().get_active(source.document_id)
    assert fetched is not None and fetched == outcome.record
    assert fetched.result == outcome.result
    assert pipeline.source_bytes(source.document_id) == original
    assert sha256(original).hexdigest() == source.file_hash
    after = pipeline.repo.get_by_document_id(source.document_id)
    for name in ("file_hash", "stored_path", "original_filename", "detected_document_type",
                 "classification_confidence", "parser_used", "page_count", "sheet_count"):
        assert getattr(after, name) == getattr(before, name)
    return source, fetched.result


def test_native_two_page_pdf_production_flow_bypasses_renderers_and_persists_pages(invoice_pipeline, monkeypatch):
    import customs_ai.application.composition as composition

    class NoVisualProvider:
        calls = 0

        def process(self, image):
            self.calls += 1
            raise AssertionError("Native text must not invoke OCR/VLM")

    class NoRenderer:
        calls = 0

        def render_page(self, path, index):
            self.calls += 1
            raise AssertionError("Native text must not be rendered")

    vlm, ocr, renderer = NoVisualProvider(), NoVisualProvider(), NoRenderer()
    monkeypatch.setattr(composition, "vision_service_factory", lambda repository: VisualResolutionService(
        repository, vlm, ocr, config=VisionSettingsConfig(enabled=True), renderer=renderer,
    ))
    source, result = _run(invoice_pipeline, invoice_pipeline.pdf())
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.invoice_number.raw_value == "0000456"
    assert result.invoice.invoice_number.normalized_value == "0000456"
    assert result.invoice.invoice_number.page == 1
    assert result.invoice.invoice_date.normalized_value == date(2026, 10, 29)
    assert type(result.invoice.invoice_date.normalized_value) is date
    total = result.invoice.total_amount
    assert total.raw_value == "123456789012345.1200"
    assert total.normalized_value.as_tuple() == Decimal("123456789012345.1200").as_tuple()
    assert total.source_document_id == source.document_id and total.page == 2
    assert total.sheet is None and total.cell is None
    assert result.invoice.items == []
    assert any(issue.code == "PDF_ITEMS_UNSUPPORTED" and issue.is_review_required for issue in result.issues)
    assert (vlm.calls, ocr.calls, renderer.calls) == (0, 0, 0)


@pytest.mark.parametrize("format", ["xlsx", "xls"])
def test_excel_ingestion_classification_extraction_roundtrip_preserves_exact_values(invoice_pipeline, format):
    path = getattr(invoice_pipeline, format)()
    source, result = _run(invoice_pipeline, path)
    assert result.status == ExtractionStatus.EXTRACTED
    invoice = result.invoice
    assert invoice.invoice_number.raw_value == "0000456"
    assert invoice.invoice_number.normalized_value == "0000456"
    assert invoice.invoice_number.cell == "B2"
    assert invoice.invoice_number.sheet == "Invoice Data"
    assert invoice.invoice_date.normalized_value == date(2026, 10, 29)
    assert type(invoice.invoice_date.normalized_value) is date
    assert invoice.seller.name.normalized_value == "Synthetic Exporter"
    assert invoice.buyer.name.normalized_value == "Synthetic Importer"
    assert invoice.ship_to.name.normalized_value == "Synthetic Receiver"
    assert invoice.total_amount.normalized_value.as_tuple() == Decimal("123456789012345.1200").as_tuple()
    assert [item.item_code.normalized_value for item in invoice.items] == ["000009", "000010"]
    first = invoice.items[0]
    assert first.item_code.raw_value == "000009" and first.item_code.cell == "C12"
    assert first.description.raw_value == "Synthetic control motor" and first.description.cell == "D12"
    assert first.quantity.raw_value == "0.00" and first.quantity.normalized_value == Decimal("0.00")
    assert first.quantity.cell == "E12"
    assert first.unit_price.raw_value == "12.50" and first.unit_price.normalized_value == Decimal("12.50")
    assert first.unit_price.cell == "G12"
    assert first.amount.raw_value == "0.00" and first.amount.normalized_value == Decimal("0.00")
    assert first.amount.cell == "H12"
    assert invoice.items[1].description.normalized_value == "TOTAL CONTROL"
    assert invoice.items[1].quantity.normalized_value == Decimal("2.50")
    assert first.origin is None and first.weight is None and first.brand is None
    for item in invoice.items:
        for _, field in item:
            if field is not None:
                assert field.source_document_id == source.document_id
                assert field.sheet == "Invoice Data"
                assert field.page is None


def test_real_xlsx_table_on_later_sheet_shifted_rows_and_columns_keeps_actual_locations(invoice_pipeline):
    rows = [[], [], []] + [[None, None] + row for row in invoice_pipeline.rows()]

    def add_cover(book):
        book.create_sheet("Cover", 0)["A1"] = "Synthetic document cover"

    path = invoice_pipeline.xlsx(rows, mutate=add_cover)
    _, result = _run(invoice_pipeline, path)
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.invoice_number.cell == "D5"
    assert result.invoice.invoice_number.sheet == "Invoice Data"
    assert result.invoice.items[0].item_code.cell == "E15"
    assert result.invoice.items[0].quantity.cell == "G15"
    assert result.invoice.items[0].amount.cell == "J15"
    assert len(result.invoice.items) == 2


def test_real_xlsx_native_datetime_and_numeric_zero_survive_all_boundaries(invoice_pipeline):
    def native_values(book):
        sheet = book.active
        sheet["B3"] = datetime(2026, 10, 29, 13, 37, 42)
        sheet["E12"] = 0
        sheet["G12"] = 12.5
        sheet["H12"] = 0

    _, result = _run(invoice_pipeline, invoice_pipeline.xlsx(mutate=native_values))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.invoice.invoice_date.normalized_value == date(2026, 10, 29)
    assert type(result.invoice.invoice_date.normalized_value) is date
    item = result.invoice.items[0]
    assert item.quantity.raw_value == "0" and item.quantity.normalized_value == Decimal("0")
    assert item.unit_price.raw_value == "12.5" and item.unit_price.normalized_value == Decimal("12.5")
    assert item.amount.raw_value == "0" and item.amount.normalized_value == Decimal("0")


def test_formula_header_and_item_values_remain_unresolved_after_real_pipeline(invoice_pipeline):
    def formulas(book):
        book.active["B8"] = "=SUM(H12:H13)"
        book.active["G12"] = "=12.5*1"

    _, result = _run(invoice_pipeline, invoice_pipeline.xlsx(mutate=formulas))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.total_amount is None
    assert len(result.invoice.items) == 2
    assert result.invoice.items[0].unit_price is None
    assert result.invoice.items[0].quantity.normalized_value == Decimal("0.00")
    assert result.invoice.items[0].amount.normalized_value == Decimal("0.00")
    assert any(issue.code == "UNRESOLVED_FORMULA_FIELD" for issue in result.issues)
    assert any(issue.code == "UNRESOLVED_ITEM_FORMULA" for issue in result.issues)
    assert {"=SUM(H12:H13)", "=12.5*1"} <= {candidate.raw_value for candidate in result.candidates}


def test_competing_real_tables_abstain_while_preserving_header_and_candidate_history(invoice_pipeline):
    def second_table(book):
        sheet = book.active
        sheet["C20"], sheet["D20"] = "ITEM CODE", "QTY"
        sheet["C21"], sheet["D21"] = "000099", "7.00"

    _, result = _run(invoice_pipeline, invoice_pipeline.xlsx(mutate=second_table))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.invoice.invoice_number.normalized_value == "0000456"
    assert result.invoice.items == []
    assert any(issue.code == "MULTIPLE_ITEM_TABLES" for issue in result.issues)
    candidates = {candidate.raw_value for candidate in result.candidates}
    assert {"000009", "000010", "000099"} <= candidates


@pytest.mark.parametrize("hidden", ["row", "column", "sheet"])
def test_hidden_workbook_material_does_not_silently_become_persisted_items(invoice_pipeline, hidden):
    def hide(book):
        if hidden == "row":
            book.active.row_dimensions[12].hidden = True
        elif hidden == "column":
            book.active.column_dimensions["G"].hidden = True
        else:
            sheet = book.create_sheet("Hidden Items")
            sheet.append(["ITEM CODE", "QTY"])
            sheet.append(["HIDDEN-SECRET", "7.00"])
            sheet.sheet_state = "hidden"

    _, result = _run(invoice_pipeline, invoice_pipeline.xlsx(mutate=hide))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    codes = [item.item_code.normalized_value for item in result.invoice.items]
    if hidden == "row":
        assert codes == ["000010"]
        assert any(issue.code == "HIDDEN_ITEM_ROW" for issue in result.issues)
    elif hidden == "column":
        assert codes == []
        assert any(issue.code == "HIDDEN_ITEM_COLUMN" for issue in result.issues)
    else:
        assert codes == ["000009", "000010"]
        assert "HIDDEN-SECRET" not in codes
        assert any(issue.code == "HIDDEN_ITEM_TABLE" for issue in result.issues)


def test_ambiguous_numeric_and_incomplete_real_rows_remain_partial_without_fabrication(invoice_pipeline):
    def unresolved(book):
        book.active["E12"] = "0.000"
        book.active["D14"] = "Synthetic partial pump"

    _, result = _run(invoice_pipeline, invoice_pipeline.xlsx(mutate=unresolved))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert len(result.invoice.items) == 3
    assert result.invoice.items[0].quantity is None
    assert result.invoice.items[0].amount.normalized_value == Decimal("0.00")
    assert result.invoice.items[1].quantity.normalized_value == Decimal("2.50")
    partial = result.invoice.items[2]
    assert partial.description.normalized_value == "Synthetic partial pump"
    assert partial.item_code is None and partial.quantity is None
    assert partial.amount is None and partial.unit_price is None
    assert any(candidate.raw_value == "0.000" and candidate.cell == "E12" for candidate in result.candidates)
    assert any(issue.code == "INCOMPLETE_ITEM_ROW" for issue in result.issues)
