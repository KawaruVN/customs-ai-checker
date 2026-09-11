import pytest
from pydantic import ValidationError

from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.models import DocumentClassificationResult, ClassificationEvidence
from customs_ai.parsers.models import ParsedCell, ParsedPdfDocument, ParsedPdfPage, ParsedSheet, ParsedWorkbook


@pytest.fixture
def classifier():
    return DeterministicClassifier(load_classification_config())


def create_pdf(text: str) -> ParsedPdfDocument:
    return ParsedPdfDocument(
        document_id="D1",
        page_count=1,
        has_text_layer=True,
        needs_ocr=False,
        pages=[ParsedPdfPage(page=1, text=text)],
    )


def create_excel(cells_data: list[tuple[str, str, str]]) -> ParsedWorkbook:
    # cells_data is list of (sheet_name, coordinate, text)
    sheets_dict = {}
    for sheet_name, coord, text in cells_data:
        if sheet_name not in sheets_dict:
            sheets_dict[sheet_name] = []
        sheets_dict[sheet_name].append(
            ParsedCell(coordinate=coord, row=1, column=1, raw_value=text, data_type="s")
        )
    
    sheets = []
    for i, (name, cells) in enumerate(sheets_dict.items()):
        sheets.append(ParsedSheet(name=name, index=i, state="visible", cells=cells))

    return ParsedWorkbook(
        document_id="D2",
        file_type="xlsx",
        parser_used="openpyxl",
        workbook_name="f.xlsx",
        sheet_count=len(sheets),
        sheets=sheets,
    )


def test_all_v1_enum_values_exist():
    expected = [
        "COMMERCIAL_INVOICE", "PACKING_LIST", "BILL_OF_LADING", "AIR_WAYBILL",
        "CUSTOMS_DECLARATION", "CONTRACT", "PURCHASE_ORDER", "CERTIFICATE_OF_ORIGIN",
        "CATALOGUE", "SPECIFICATION", "OTHER", "UNKNOWN"
    ]
    for e in expected:
        assert getattr(DocumentType, e).value == e


def test_commercial_invoice_classification(classifier):
    pdf = create_pdf("COMMERCIAL INVOICE")
    res = classifier.classify(pdf)
    assert res.document_type == DocumentType.COMMERCIAL_INVOICE


def test_packing_list_classification(classifier):
    pdf = create_pdf("PACKING LIST with GROSS WEIGHT")
    res = classifier.classify(pdf)
    assert res.document_type == DocumentType.PACKING_LIST


def test_bl_awb_differentiation(classifier):
    bl = create_pdf("This is a BILL OF LADING")
    awb = create_pdf("This is an AIR WAYBILL")
    assert classifier.classify(bl).document_type == DocumentType.BILL_OF_LADING
    assert classifier.classify(awb).document_type == DocumentType.AIR_WAYBILL


def test_customs_declaration(classifier):
    doc = create_pdf("TỜ KHAI HẢI QUAN")
    assert classifier.classify(doc).document_type == DocumentType.CUSTOMS_DECLARATION


def test_contract_po_co_catalog_spec(classifier):
    assert classifier.classify(create_pdf("SALES CONTRACT")).document_type == DocumentType.CONTRACT
    assert classifier.classify(create_pdf("PURCHASE ORDER")).document_type == DocumentType.PURCHASE_ORDER
    assert classifier.classify(create_pdf("CERTIFICATE OF ORIGIN")).document_type == DocumentType.CERTIFICATE_OF_ORIGIN
    assert classifier.classify(create_pdf("PRODUCT CATALOG")).document_type == DocumentType.CATALOGUE
    assert classifier.classify(create_pdf("TECHNICAL SPECIFICATION")).document_type == DocumentType.SPECIFICATION


def test_empty_content_returns_unknown(classifier):
    assert classifier.classify(create_pdf("")).document_type == DocumentType.UNKNOWN


def test_generic_content_returns_unknown(classifier):
    res = classifier.classify(create_pdf("DATE: 2026-01-01. QUANTITY: 50. DESCRIPTION: Widgets."))
    assert res.document_type == DocumentType.UNKNOWN


def test_bl_vs_awb_conflict_returns_unknown(classifier):
    # Both strong clues present -> difference is 0 -> UNKNOWN
    res = classifier.classify(create_pdf("BILL OF LADING and AIR WAYBILL combined"))
    assert res.document_type == DocumentType.UNKNOWN


def test_filename_contradiction_commercial_empty(classifier):
    # Filename ignored. Empty content -> UNKNOWN
    res = classifier.classify(create_pdf(""), filename="COMMERCIAL INVOICE.pdf")
    assert res.document_type == DocumentType.UNKNOWN
    assert res.confidence == 0.0


def test_filename_contradiction_invoice_vs_packing(classifier):
    # Filename suggests Invoice, content is Packing List
    res = classifier.classify(create_pdf("PACKING LIST"), filename="invoice.pdf")
    assert res.document_type == DocumentType.PACKING_LIST


def test_filename_contradiction_packing_vs_invoice(classifier):
    res = classifier.classify(create_pdf("COMMERCIAL INVOICE"), filename="packing_list.pdf")
    assert res.document_type == DocumentType.COMMERCIAL_INVOICE


def test_form_e_alone_returns_unknown(classifier):
    # FORM E is supporting only (0.2). Threshold is 0.5.
    res = classifier.classify(create_pdf("FORM E"))
    assert res.document_type == DocumentType.UNKNOWN
    assert res.confidence == 0.2




def test_po_number_alone_is_supporting_not_decisive(classifier):
    res = classifier.classify(create_pdf("PO NO: PO-12345"))
    assert res.document_type == DocumentType.UNKNOWN
    assert res.confidence == 0.2


def test_po_reference_does_not_override_clear_invoice_content(classifier):
    res = classifier.classify(
        create_pdf("COMMERCIAL INVOICE\nPO NO: PO-12345")
    )
    assert res.document_type == DocumentType.COMMERCIAL_INVOICE


def test_co_abbreviation_alone_returns_unknown(classifier):
    res = classifier.classify(create_pdf("C/O"))
    assert res.document_type == DocumentType.UNKNOWN
    assert res.confidence == 0.2


def test_multilingual_positive_clues(classifier):
    assert classifier.classify(create_pdf("商业发票")).document_type == DocumentType.COMMERCIAL_INVOICE
    assert classifier.classify(create_pdf("HÓA ĐƠN THƯƠNG MẠI")).document_type == DocumentType.COMMERCIAL_INVOICE


def test_evidence_page_provenance(classifier):
    pdf = create_pdf("COMMERCIAL INVOICE")
    res = classifier.classify(pdf)
    assert res.evidence[0].page == 1
    assert res.evidence[0].sheet is None


def test_evidence_sheet_cell_provenance(classifier):
    excel = create_excel([("Sheet1", "A1", "PACKING LIST")])
    res = classifier.classify(excel)
    assert res.evidence[0].sheet == "Sheet1"
    assert res.evidence[0].cell == "A1"


def test_clues_spread_across_excel_cells(classifier):
    # No single cell has strong clue, but multiple supporting clues aggregate
    # INVOICE NO (0.2) + UNIT PRICE (0.2) + TOTAL AMOUNT (0.2) = 0.6 (>0.5)
    excel = create_excel([
        ("Sheet1", "A1", "INVOICE NO"),
        ("Sheet1", "B1", "UNIT PRICE"),
        ("Sheet2", "C1", "TOTAL AMOUNT")
    ])
    res = classifier.classify(excel)
    assert res.document_type == DocumentType.COMMERCIAL_INVOICE
    assert res.confidence == 0.6
    assert len(res.evidence) == 3


def test_short_abbreviation_false_positives(classifier):
    # AWB standalone works
    assert classifier.classify(create_pdf("Send the AWB now")).document_type == DocumentType.AIR_WAYBILL
    # DRAWBACK should NOT trigger AWB
    assert classifier.classify(create_pdf("Claim your DRAWBACK")).document_type == DocumentType.UNKNOWN


def test_punctuation_abbreviation(classifier):
    assert classifier.classify(create_pdf("B/L")).document_type == DocumentType.BILL_OF_LADING
    assert classifier.classify(create_pdf("B.L.")).document_type == DocumentType.BILL_OF_LADING


def test_unknown_vs_other_documentation(classifier):
    # Deterministic classifier should never return OTHER on its own.
    # OTHER is reserved for future manual override.
    res = classifier.classify(create_pdf("Random unrecognized text"))
    assert res.document_type == DocumentType.UNKNOWN
    assert res.document_type != DocumentType.OTHER


def test_classification_evidence_model_strictness():
    # Confidence bounds
    with pytest.raises(ValidationError):
        DocumentClassificationResult(document_id="1", document_type=DocumentType.COMMERCIAL_INVOICE, confidence=1.1, method="DETERMINISTIC", evidence=[])
    
    # Extra fields
    with pytest.raises(ValidationError):
        ClassificationEvidence(target_document_type=DocumentType.UNKNOWN, clue="x", weight=0.1, extra="bad")
        
    # JSON Serialization works
    ev = ClassificationEvidence(target_document_type=DocumentType.COMMERCIAL_INVOICE, clue="TEST", weight=0.6)
    assert '"target_document_type":"COMMERCIAL_INVOICE"' in ev.model_dump_json()
