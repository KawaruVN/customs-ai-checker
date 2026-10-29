"""Real Packing upload/classification/extraction/SQLite flows from native files."""

from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest

from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.enums import DocumentType
from customs_ai.domain.enums import ValueOrigin
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.ingestion.enums import ProcessingStatus


PATHS = ["packing_list_number", "date", "seller.name", "seller.tax_id", "seller.address",
         "buyer.name", "buyer.tax_id", "buyer.address", "shipment_reference",
         "invoice_references", "invoice_references", "package_count", "package_type",
         "gross_weight", "net_weight", "dimensions", "volume"]
LABELS = {
    "en": ["PACKING LIST NO", "PACKING LIST DATE", "SELLER", "SELLER TAX ID", "SELLER ADDRESS",
           "BUYER", "BUYER TAX ID", "BUYER ADDRESS", "SHIPMENT REFERENCE", "INVOICE NO", "INVOICE NO",
           "TOTAL PACKAGES", "PACKAGE TYPE", "TOTAL GROSS WEIGHT", "TOTAL NET WEIGHT", "DIMENSIONS", "TOTAL VOLUME"],
    "vi": ["SỐ PHIẾU ĐÓNG GÓI", "NGÀY PHIẾU ĐÓNG GÓI", "NGƯỜI BÁN", "MÃ SỐ THUẾ NGƯỜI BÁN",
           "ĐỊA CHỈ NGƯỜI BÁN", "NGƯỜI MUA", "MÃ SỐ THUẾ NGƯỜI MUA", "ĐỊA CHỈ NGƯỜI MUA",
           "MÃ THAM CHIẾU LÔ HÀNG", "SỐ HÓA ĐƠN THAM CHIẾU", "SỐ HÓA ĐƠN THAM CHIẾU",
           "TỔNG SỐ KIỆN", "LOẠI BAO BÌ", "TỔNG TRỌNG LƯỢNG CẢ BÌ", "TỔNG TRỌNG LƯỢNG TỊNH",
           "KÍCH THƯỚC KIỆN HÀNG", "TỔNG THỂ TÍCH"],
    "zh": ["装箱单号", "装箱单日期", "卖方", "卖方税号", "卖方地址", "买方", "买方税号", "买方地址",
           "装运参考号", "参考发票", "参考发票", "总件数", "包装类型", "总毛重", "总净重", "包装尺寸", "总体积"],
}
RAW = ["0000456", "2026-10-29", "MiXeD Seller 合成", "00000123", "Seller Lane 1",
       "MiXeD Buyer Tổng hợp", "00000456", "Buyer Road 2", "SHIP/2026/001", "0000789", "INV/2026/0002",
       "0.00", "Carton", "123456789012345.1200", "-5.2500", "10 x 20 x 30 CM", "0.25"]
ITEM_LABELS = {
    "en": ["ITEM CODE", "DESCRIPTION", "QTY", "UNIT", "PACKAGE NO.", "GROSS WEIGHT", "NET WEIGHT"],
    "vi": ["MÃ HÀNG", "MÔ TẢ HÀNG HÓA", "SỐ LƯỢNG", "ĐƠN VỊ TÍNH", "SỐ HIỆU KIỆN", "TRỌNG LƯỢNG CẢ BÌ", "TRỌNG LƯỢNG TỊNH"],
    "zh": ["货号", "品名", "数量", "单位", "箱号", "毛重", "净重"],
}
ITEM_RAW = [
    ["000009", "Động cơ 电机", "0.00", "PCS", "000045", "12.50", "10.50"],
    ["000010", "TOTAL CONTROL", "2.50", "PCS", "BOX/2026/0002", "7.25", "-1.25"],
]


def _rows(language="en"):
    title = {"en": "PACKING LIST", "vi": "PHIẾU ĐÓNG GÓI", "zh": "装箱单"}[language]
    return ([[title]] + [[label, raw] for label, raw in zip(LABELS[language], RAW)] + [[]]
            + [[None, None] + ITEM_LABELS[language]] + [[None, None] + values for values in ITEM_RAW])


def _run(pipeline, path):
    original = path.read_bytes()
    source = pipeline.register(path)
    assert source.processing_status == ProcessingStatus.UPLOADED
    assert source.file_hash == sha256(original).hexdigest()
    assert pipeline.source_bytes(source.document_id) == original
    classification = pipeline.classify(source.document_id)
    assert classification.document_id == source.document_id
    assert classification.document_type == DocumentType.PACKING_LIST
    assert classification.evidence and classification.confidence >= 0.5
    before = pipeline.repo.get_by_document_id(source.document_id)
    assert before.processing_status == ProcessingStatus.CLASSIFIED
    parsed = DocumentParsingService(pipeline.repo).parse_document_readonly(source.document_id)
    assert parsed.document_id == source.document_id and parsed.file_type == source.file_type
    assert parsed.parser_used == {"pdf": "pypdf", "xlsx": "openpyxl", "xls": "xlrd"}[source.file_type]
    assert pipeline.repo.get_by_document_id(source.document_id) == before
    outcome = pipeline.extract(source.document_id)
    assert outcome.persisted
    pipeline.assert_roundtrip(source, outcome)
    after = pipeline.repo.get_by_document_id(source.document_id)
    for name in ("stored_path", "file_hash", "original_filename", "detected_document_type",
                 "classification_confidence", "parser_used", "page_count", "sheet_count"):
        assert getattr(after, name) == getattr(before, name)
    assert path.read_bytes() == original and pipeline.source_bytes(source.document_id) == original
    return source, outcome.result, parsed


def _field(packing, path):
    for part in path.split("."):
        packing = getattr(packing, part)
    return packing


def _assert_all_headers(packing, source, raws=RAW, *, pages=None, row_offset=0, column="B"):
    reference = 0
    for index, (path, raw) in enumerate(zip(PATHS, raws), start=2):
        field = _field(packing, path)
        if path == "invoice_references":
            field = field[reference]
            reference += 1
        expected = date(2026, 10, 29) if path == "date" else Decimal(raw) if path in {
            "package_count", "gross_weight", "net_weight", "volume"} else raw
        assert field.normalized_value == expected and field.raw_value == raw
        assert field.source_document_id == source.document_id and field.origin == ValueOrigin.EXTRACTED
        assert field.extraction_method and field.confidence is not None
        if isinstance(expected, Decimal):
            assert field.normalized_value.as_tuple() == expected.as_tuple()
        if pages is None:
            assert field.cell == f"{column}{index + row_offset}" and field.sheet == "Packing Data"
            assert field.page is None
        else:
            assert field.page == pages[path] and field.sheet is None and field.cell is None
    assert type(packing.date.normalized_value) is date
    assert len(packing.invoice_references) == 2


def _assert_items(packing, source, *, row=21, columns=("C", "D", "E", "F", "G", "H", "I")):
    assert len(packing.items) == 2
    fields = ["item_code", "description", "quantity", "unit", "package_number", "gross_weight", "net_weight"]
    for offset, (item, values) in enumerate(zip(packing.items, ITEM_RAW)):
        for name, raw, column in zip(fields, values, columns):
            field = getattr(item, name)
            expected = Decimal(raw) if name in {"quantity", "gross_weight", "net_weight"} else raw
            assert field.raw_value == raw and field.normalized_value == expected
            assert field.sheet == "Packing Data" and field.cell == f"{column}{row + offset}"
            assert field.source_document_id == source.document_id and field.page is None
            assert field.origin == ValueOrigin.EXTRACTED and field.extraction_method and field.confidence is not None
            if isinstance(expected, Decimal):
                assert field.normalized_value.as_tuple() == expected.as_tuple()


@pytest.mark.parametrize("language", ["en", "vi", "zh"])
@pytest.mark.parametrize("format", ["xlsx", "xls"])
def test_actual_multilingual_excel_preserves_all_headers_items_and_v2_sqlite(packing_pipeline, language, format):
    path = getattr(packing_pipeline, format)(_rows(language))
    if format == "xls":
        assert path.read_bytes().startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    source, result, parsed = _run(packing_pipeline, path)
    assert result.status == ExtractionStatus.EXTRACTED
    _assert_all_headers(result.packing_list, source)
    _assert_items(result.packing_list, source)
    cells = {cell.coordinate: cell for cell in parsed.sheets[0].cells}
    assert cells["C21"].raw_value == "000009" and cells["G21"].raw_value == "000045"
    assert result.packing_list.package_count.normalized_value != result.packing_list.items[1].quantity.normalized_value
    assert result.packing_list.gross_weight.normalized_value != result.packing_list.items[0].gross_weight.normalized_value


def test_actual_xls_formula_limit_is_visible_without_inventing_formula_provenance(packing_pipeline):
    import xlwt
    rows = _rows()
    rows[20][4] = xlwt.Formula("1+1")  # BIFF cache emitted by xlwt is empty, not evaluated.
    _, result, parsed = _run(packing_pipeline, packing_pipeline.xls(rows))
    quantity = next(cell for cell in parsed.sheets[0].cells if cell.coordinate == "E21")
    assert quantity.raw_value == "" and quantity.displayed_value == ""
    assert quantity.is_formula is False  # The approved XLS contract has no expression metadata.
    assert result.packing_list.items[0].quantity is None
    assert result.packing_list.items[0].gross_weight.normalized_value == Decimal("12.50")
    assert result.packing_list.items[1].quantity.normalized_value == Decimal("2.50")
    assert not any(candidate.raw_value in {"=1+1", "1+1"} for candidate in result.candidates)


@pytest.mark.parametrize("page_count", [1, 2])
def test_real_native_pdf_commits_all_headers_exact_pages_and_explicit_missing_items(packing_pipeline, page_count):
    # Real standard-font native text PDF: Unicode coverage is exercised by real XLS/XLSX above.
    raws = [value.replace(" 合成", "").replace(" Tổng hợp", "") for value in RAW]
    lines = ["PACKING LIST"] + [f"{label}: {value}" for label, value in zip(LABELS["en"], raws)]
    pages = ["\n".join(lines)] if page_count == 1 else ["\n".join(lines[:10]), "PACKING LIST continuation\n" + "\n".join(lines[10:])]
    source, result, parsed = _run(packing_pipeline, packing_pipeline.pdf(pages))
    assert parsed.has_text_layer and not parsed.needs_ocr
    assert result.status == ExtractionStatus.NEEDS_REVIEW and result.packing_list.items == []
    # Both references occur on page two for the two-page split.
    locations = {path: 1 if page_count == 1 or index < 9 else 2 for index, path in enumerate(PATHS)}
    _assert_all_headers(result.packing_list, source, raws, pages=locations)
    assert any(issue.code == "PDF_PACKING_ITEMS_UNSUPPORTED" and issue.is_review_required for issue in result.issues)


def test_shifted_table_and_headers_on_later_visible_sheet_have_actual_coordinates(packing_pipeline):
    rows = [[], [], [], []] + [[None, None] + values for values in _rows()]
    def cover(book):
        book.create_sheet("Cover", 0)["A1"] = "Synthetic document cover"
    source, result, parsed = _run(packing_pipeline, packing_pipeline.xlsx(rows, mutate=cover))
    assert result.status == ExtractionStatus.EXTRACTED and parsed.sheet_count == 2
    _assert_all_headers(result.packing_list, source, row_offset=4, column="D")
    _assert_items(result.packing_list, source, row=25, columns=("E", "F", "G", "H", "I", "J", "K"))


def test_actual_excel_native_datetime_zero_and_float_preserve_known_source_precision(packing_pipeline):
    def native(book):
        book.active["B3"] = datetime(2026, 10, 29, 13, 37, 42)
        book.active["E21"] = 0
        book.active["H21"] = 12.5
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=native))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.date.raw_value == "2026-10-29 13:37:42"
    assert result.packing_list.date.normalized_value == date(2026, 10, 29)
    assert result.packing_list.items[0].quantity.raw_value == "0"
    assert result.packing_list.items[0].quantity.normalized_value == Decimal("0")
    assert result.packing_list.items[0].gross_weight.raw_value == "12.5"
    assert result.packing_list.items[0].gross_weight.normalized_value == Decimal("12.5")


@pytest.mark.parametrize("kind", ["group_columns", "row", "sheet"])
def test_hidden_material_never_becomes_trusted_canonical_data(packing_pipeline, kind):
    def hide(book):
        if kind == "group_columns": book.active.column_dimensions.group("B", "D", hidden=True)
        elif kind == "row": book.active.row_dimensions[21].hidden = True
        else:
            tab = book.create_sheet("Hidden Goods")
            tab.append(["ITEM CODE", "QTY"]); tab.append(["SYNTHETIC-HIDDEN", "7.00"])
            tab.sheet_state = "hidden"
    _, result, parsed = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=hide))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.is_review_required for issue in result.issues)
    codes = [item.item_code.normalized_value for item in result.packing_list.items if item.item_code]
    if kind == "group_columns":
        assert parsed.sheets[0].hidden_columns == ["B", "C", "D"]
        assert result.packing_list.items == [] and result.packing_list.packing_list_number is None
    elif kind == "row":
        assert codes == ["000010"]
        assert any(c.raw_value == "000009" and c.cell == "C21" for c in result.candidates)
    else:
        assert codes == ["000009", "000010"] and "SYNTHETIC-HIDDEN" not in codes


@pytest.mark.parametrize("coordinate,path,expression", [("E21", "quantity", "=1+1"), ("H21", "gross_weight", "=H22+1")])
def test_real_formula_values_preserve_expression_and_do_not_trust_cache(packing_pipeline, coordinate, path, expression):
    def formula(book): book.active[coordinate] = expression
    _, result, parsed = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=formula))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert getattr(result.packing_list.items[0], path) is None
    assert result.packing_list.items[0].item_code.normalized_value == "000009"
    assert any(c.raw_value == expression and c.cell == coordinate for c in result.candidates)
    actual = next(cell for cell in parsed.sheets[0].cells if cell.coordinate == coordinate)
    assert actual.is_formula and actual.raw_value == expression and actual.displayed_value is None


@pytest.mark.parametrize("merge", ["D21:D22", "E21:F21"])
def test_ambiguous_real_merged_items_never_create_ghost_rows(packing_pipeline, merge):
    def merged(book): book.active.merge_cells(merge)
    _, result, parsed = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=merged))
    assert result.status == ExtractionStatus.NEEDS_REVIEW and result.packing_list.items == []
    assert any(issue.code == "AMBIGUOUS_PACKING_MERGE" for issue in result.issues)
    actual_coordinates = {cell.coordinate for cell in parsed.sheets[0].cells}
    assert all(c.cell in actual_coordinates for c in result.candidates if c.sheet == "Packing Data")


def test_duplicate_item_header_abstains_and_keeps_actual_conflicting_cells(packing_pipeline):
    def duplicate(book):
        book.active["J20"] = "QUANTITY"; book.active["J21"] = "9.00"
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=duplicate))
    assert result.status == ExtractionStatus.NEEDS_REVIEW and result.packing_list.items == []
    assert any(issue.code == "AMBIGUOUS_PACKING_COLUMNS" for issue in result.issues)
    assert any(c.raw_value == "9.00" and c.cell == "J21" for c in result.candidates)


def test_two_real_credible_tables_never_arbitrarily_select_or_concatenate(packing_pipeline):
    def second(book):
        book.active["C27"], book.active["D27"] = "ITEM CODE", "QTY"
        book.active["C28"], book.active["D28"] = "000077", "7.00"
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=second))
    assert result.status == ExtractionStatus.NEEDS_REVIEW and result.packing_list.items == []
    assert any(issue.code == "MULTIPLE_PACKING_TABLES" for issue in result.issues)
    assert {"000009", "000010", "000077"} <= {c.raw_value for c in result.candidates}


@pytest.mark.parametrize("raw", ["1,200", "1.200", "12 KG"])
def test_ambiguous_item_quantity_remains_missing_and_source_candidate_survives(packing_pipeline, raw):
    def invalid(book): book.active["E21"] = raw
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=invalid))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.items[0].quantity is None
    assert result.packing_list.items[0].gross_weight.normalized_value == Decimal("12.50")
    assert any(c.raw_value == raw and c.cell == "E21" for c in result.candidates)


def test_summary_row_does_not_become_goods_while_total_word_product_remains(packing_pipeline):
    def total(book):
        book.active["D23"] = "TOTAL"; book.active["H23"] = "19.75"
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=total))
    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.description.normalized_value for item in result.packing_list.items] == ["Động cơ 电机", "TOTAL CONTROL"]
    assert all(item.description.normalized_value != "TOTAL" for item in result.packing_list.items)


def test_shipping_roles_do_not_fill_missing_commercial_parties(packing_pipeline):
    values = _rows()
    for index, label in {3: "SHIPPER", 4: "SHIPPER TAX ID", 5: "SHIPPER ADDRESS", 6: "CONSIGNEE", 7: "CONSIGNEE TAX ID", 8: "CONSIGNEE ADDRESS"}.items():
        values[index][0] = label
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(values))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.seller is None and result.packing_list.buyer is None
    assert result.packing_list.packing_list_number.normalized_value == "0000456"


def test_missing_date_and_optional_item_unit_are_not_fabricated(packing_pipeline):
    def missing(book): book.active["B3"] = None; book.active["F21"] = None
    _, result, _ = _run(packing_pipeline, packing_pipeline.xlsx(_rows(), mutate=missing))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.date is None and result.packing_list.items[0].unit is None
    assert result.packing_list.items[0].package_number.normalized_value == "000045"
