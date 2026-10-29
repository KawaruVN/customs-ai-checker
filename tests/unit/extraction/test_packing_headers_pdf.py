"""Synthetic PDF evidence and adversarial Packing header boundary tests."""

from datetime import date
from decimal import Decimal

import pytest

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import PackingList
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.packing_headers import DeterministicPackingHeaderExtractor
from customs_ai.extraction.packing_models import PackingListHeaderExtractionResult
from customs_ai.parsers.models import ParsedPdfDocument, ParsedPdfPage
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ResolvedPdfDocument, ResolvedPdfPage


_FILLER = "Synthetic packing document header evidence."


def _native(*texts, pad=True):
    return ParsedPdfDocument(
        document_id="PACK-PDF", page_count=len(texts), has_text_layer=True,
        needs_ocr=False,
        pages=[ParsedPdfPage(page=index + 1, text=text + ("\n" + _FILLER if pad else ""))
               for index, text in enumerate(texts)],
    )


def _resolved(text="PACKING LIST NO: 000045", *, source=TextResolutionSource.CROSS_VERIFIED_VISUAL,
              verification=VerificationLevel.CROSS_VERIFIED, confidence=0.93):
    return ResolvedPdfDocument(
        document_id="PACK-PDF", page_count=1, requires_review=False,
        visual_pages=[] if source == TextResolutionSource.TEXT_LAYER else [1],
        pages=[ResolvedPdfPage(
            page=1, text=text + "\n" + _FILLER, source=source,
            verification_level=verification, confidence=confidence,
            requires_review=False,
        )],
    )


def _extract(document):
    return DeterministicPackingHeaderExtractor().extract(document)


def _value(packing, path):
    for part in path.split("."):
        packing = getattr(packing, part)
    return packing


def _assert_abstains(result):
    assert isinstance(result, PackingListHeaderExtractionResult)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list == PackingList()
    assert result.candidates == []
    assert result.issues and any(issue.is_review_required for issue in result.issues)


@pytest.mark.parametrize("labels", [
    ["PACKING LIST NO", "PACKING LIST DATE", "SELLER", "SELLER TAX ID", "SELLER ADDRESS",
     "BUYER", "BUYER TAX ID", "BUYER ADDRESS", "SHIPMENT REFERENCE", "INVOICE NO",
     "TOTAL PACKAGES", "PACKAGE TYPE", "TOTAL GROSS WEIGHT", "TOTAL NET WEIGHT",
     "PACKAGE DIMENSIONS", "TOTAL VOLUME"],
    ["SỐ PHIẾU ĐÓNG GÓI", "NGÀY PHIẾU ĐÓNG GÓI", "NGƯỜI BÁN", "MÃ SỐ THUẾ NGƯỜI BÁN",
     "ĐỊA CHỈ NGƯỜI BÁN", "NGƯỜI MUA", "MÃ SỐ THUẾ NGƯỜI MUA", "ĐỊA CHỈ NGƯỜI MUA",
     "MÃ THAM CHIẾU LÔ HÀNG", "SỐ HÓA ĐƠN THAM CHIẾU", "TỔNG SỐ KIỆN", "LOẠI BAO BÌ",
     "TỔNG TRỌNG LƯỢNG CẢ BÌ", "TỔNG TRỌNG LƯỢNG TỊNH", "KÍCH THƯỚC KIỆN HÀNG", "TỔNG THỂ TÍCH"],
    ["装箱单号", "装箱单日期", "卖方", "卖方税号", "卖方地址", "买方", "买方税号", "买方地址",
     "装运参考号", "参考发票", "总件数", "包装类型", "总毛重", "总净重", "包装尺寸", "总体积"],
], ids=["english", "vietnamese", "chinese"])
def test_all_sixteen_header_paths_in_each_language(labels):
    values = ["000045", "2026-10-29", "MiXeD Seller", "000123", "Seller Lane 1",
              "MiXeD Buyer", "000234", "Buyer Lane 2", "SHIP/2026/0001", "000007",
              "0.00", "Carton", "12345678901234567890.1200", "9.50", "10 x 20 x 30 CM", "0.25"]
    paths = ["packing_list_number", "date", "seller.name", "seller.tax_id", "seller.address",
             "buyer.name", "buyer.tax_id", "buyer.address", "shipment_reference", "invoice_references",
             "package_count", "package_type", "gross_weight", "net_weight", "dimensions", "volume"]
    result = _extract(_native("\n".join(f"{label}: {value}" for label, value in zip(labels, values))))
    assert result.status == ExtractionStatus.EXTRACTED
    assert not any(issue.is_review_required for issue in result.issues)
    assert result.packing_list.items == []
    for path, raw in zip(paths, values):
        field = _value(result.packing_list, path)
        if path == "invoice_references":
            assert len(field) == 1
            field = field[0]
        assert field.raw_value == raw
        assert field.source_document_id == "PACK-PDF" and field.page == 1
        assert field.sheet is None and field.cell is None
        assert field.origin == ValueOrigin.EXTRACTED
        assert field.extraction_method
        assert field.confidence is not None and 0 < field.confidence <= 1
    assert result.packing_list.date.normalized_value == date(2026, 10, 29)
    assert type(result.packing_list.date.normalized_value) is date
    assert result.packing_list.package_count.normalized_value.as_tuple() == Decimal("0.00").as_tuple()
    assert result.packing_list.gross_weight.normalized_value.as_tuple() == Decimal("12345678901234567890.1200").as_tuple()
    assert result.packing_list.seller.name.normalized_value == "MiXeD Seller"
    assert result.packing_list.buyer.name.normalized_value == "MiXeD Buyer"
    assert result.packing_list.seller.tax_id.normalized_value == "000123"
    assert result.packing_list.dimensions.normalized_value == "10 x 20 x 30 CM"


def test_number_and_invoice_references_keep_independent_page_provenance():
    result = _extract(_native("PACKING LIST NO: 000045\nINVOICE NO: 000007", "INVOICE NO: 000008"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.packing_list_number.normalized_value == "000045"
    assert result.packing_list.packing_list_number.page == 1
    assert [(field.normalized_value, field.raw_value, field.page) for field in result.packing_list.invoice_references] == [
        ("000007", "000007", 1), ("000008", "000008", 2),
    ]
    assert result.packing_list.items == []


def test_duplicate_references_are_one_business_value_with_all_source_candidates():
    result = _extract(_native("INVOICE NO: 000007", "INVOICE REF.: 000007\nINVOICE NO: 000008"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert [field.normalized_value for field in result.packing_list.invoice_references] == ["000007", "000008"]
    refs = [candidate for candidate in result.candidates if candidate.field_path == "invoice_references"]
    assert len(refs) == 3
    assert {candidate.page for candidate in refs} == {1, 2}


@pytest.mark.parametrize("combined", ["INV-001, INV-002", "INV-001; INV-002", "INV-001 / INV-002", "INV-001 to INV-003"])
def test_ambiguous_combined_reference_is_not_guessed_or_split(combined):
    result = _extract(_native(f"PACKING LIST NO: PL-001\nINVOICE REFERENCES: {combined}"))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.invoice_references == []
    assert any(candidate.field_path == "invoice_references" and candidate.raw_value == combined for candidate in result.candidates)
    assert any(issue.field_path == "invoice_references" and issue.is_review_required for issue in result.issues)
    assert all(combined not in issue.message for issue in result.issues)


def test_slashes_inside_one_invoice_identifier_are_not_reference_separators():
    result = _extract(_native("INVOICE NO: INV/2026/0001"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert [field.normalized_value for field in result.packing_list.invoice_references] == ["INV/2026/0001"]


@pytest.mark.parametrize("text", [
    "XPACKING LIST NO: FAKE", "PACKING LIST NOTHING: FAKE", "PACKING LIST NUMBERED: FAKE",
    "MY SELLER: FAKE", "SELLER ADDRESSABLE: FAKE", "BUYER ADDRESSES: FAKE",
    "The product carries PACKING LIST NO: FAKE", "DESCRIPTION: SELLER: FAKE",
    "DESCRIPTION: TOTAL GROSS WEIGHT: 999", "Description of GROSS WEIGHT: 999",
    "SHIPMENT DATE: 2026-10-29", "DELIVERY DATE: 2026-10-29",
    "DATE: 2026-10-29\nNO: 0009\nTOTAL: 99\nQTY: 99\nWEIGHT: 99",
    "ITEM GROSS WEIGHT: 99\nITEM NET WEIGHT: 88",
])
def test_false_prefixes_unknown_labels_and_product_prose_do_not_fill_headers(text):
    result = _extract(_native("PACKING LIST NO: 000045\n" + text))
    assert result.packing_list.packing_list_number.normalized_value == "000045"
    assert result.packing_list.date is None
    assert result.packing_list.seller is None and result.packing_list.buyer is None
    assert result.packing_list.gross_weight is None and result.packing_list.net_weight is None
    assert result.packing_list.package_count is None
    assert result.packing_list.items == []
    assert all(candidate.raw_value != "FAKE" for candidate in result.candidates)


@pytest.mark.parametrize("role", ["SHIPPER", "CONSIGNEE", "EXPORTER", "IMPORTER", "NGƯỜI GỬI HÀNG", "NGƯỜI NHẬN HÀNG", "发货人", "收货人"])
def test_shipping_roles_do_not_establish_seller_or_buyer(role):
    result = _extract(_native(f"PACKING LIST NO: 000045\n{role}: Role Company"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.seller is None and result.packing_list.buyer is None


def test_address_and_tax_specific_labels_do_not_also_set_party_names():
    result = _extract(_native("SELLER ADDRESS: Seller Street\nSELLER TAX ID: 00001\nBUYER ADDRESS: Buyer Street\nBUYER TAX ID: 00002"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.seller.name is None
    assert result.packing_list.buyer.name is None
    assert result.packing_list.seller.address.normalized_value == "Seller Street"
    assert result.packing_list.buyer.tax_id.normalized_value == "00002"


def test_multiple_explicit_fields_on_one_line_stay_separate():
    result = _extract(_native("PACKING LIST NO: 000045 | INVOICE NO: 000007 | TOTAL GROSS WEIGHT: 12.50 | TOTAL NET WEIGHT: 11.50"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.packing_list_number.normalized_value == "000045"
    assert [field.normalized_value for field in result.packing_list.invoice_references] == ["000007"]
    assert result.packing_list.gross_weight.normalized_value == Decimal("12.50")
    assert result.packing_list.net_weight.normalized_value == Decimal("11.50")


def test_label_only_line_uses_exact_immediately_following_value_on_same_page():
    result = _extract(_native("PACKING LIST NO:\n000045\nTOTAL GROSS WEIGHT:\n0.00"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.packing_list_number.normalized_value == "000045"
    assert result.packing_list.gross_weight.normalized_value.as_tuple() == Decimal("0.00").as_tuple()
    assert result.packing_list.gross_weight.page == 1


def test_missing_label_value_does_not_consume_another_label_or_next_page():
    result = _extract(_native("SELLER:\nBUYER: Buyer Company\nPACKING LIST NO:", "000045\n" + _FILLER, pad=False))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.seller is None
    assert result.packing_list.buyer.name.normalized_value == "Buyer Company"
    assert result.packing_list.packing_list_number is None


def test_pdf_item_column_labels_do_not_produce_document_weight_or_item_rows():
    result = _extract(_native("PACKING LIST NO: 000045\nDESCRIPTION | QUANTITY | GROSS WEIGHT | NET WEIGHT\nSynthetic pump | 2 | 12.50 | 11.50"))
    assert result.packing_list.gross_weight is None and result.packing_list.net_weight is None
    assert result.packing_list.package_count is None and result.packing_list.items == []


@pytest.mark.parametrize("raw", ["1,200", "1.200", "USD 1200", "12 KG", "NaN", "Infinity", "=2+2", "True"])
def test_invalid_numeric_evidence_retains_raw_candidate_and_abstains(raw):
    result = _extract(_native(f"TOTAL GROSS WEIGHT: {raw}"))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.gross_weight is None
    assert any(candidate.raw_value == raw and candidate.field_path == "gross_weight" for candidate in result.candidates)
    assert any(issue.field_path == "gross_weight" and issue.is_review_required for issue in result.issues)


@pytest.mark.parametrize("raw", ["01/02/2026", "2026-02-30", "12:30:00", "True", "=TODAY()"])
def test_invalid_dates_do_not_silently_become_calendar_values(raw):
    result = _extract(_native(f"PACKING LIST DATE: {raw}"))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.date is None
    assert any(candidate.raw_value == raw and candidate.field_path == "date" for candidate in result.candidates)


@pytest.mark.parametrize("values", [("0.00", "1.00"), ("0.00", "1.00", "0.00"), ("0.00", "1.00", "2.00")])
def test_scalar_conflicts_stay_sticky_without_majority_voting(values):
    result = _extract(_native(*[f"TOTAL GROSS WEIGHT: {value}" for value in values]))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list.gross_weight is None
    assert len([candidate for candidate in result.candidates if candidate.field_path == "gross_weight"]) == len(values)
    assert any(issue.field_path == "gross_weight" and issue.is_review_required for issue in result.issues)


def test_equivalent_numeric_candidates_are_deduplicated_without_losing_source_scale():
    result = _extract(_native("TOTAL GROSS WEIGHT: 2.50", "TOTAL GROSS WEIGHT: 2,50"))
    assert result.status == ExtractionStatus.EXTRACTED
    field = result.packing_list.gross_weight
    assert field.normalized_value.as_tuple() == Decimal("2.50").as_tuple()
    assert field.raw_value == "2.50" and field.page == 1
    assert len([candidate for candidate in result.candidates if candidate.field_path == "gross_weight"]) == 2


@pytest.mark.parametrize("label,path", [("PACKING LIST NO", "packing_list_number"), ("SELLER", "seller.name"), ("BUYER TAX ID", "buyer.tax_id")])
def test_three_way_string_conflicts_remain_unresolved_and_retain_all_candidates(label, path):
    result = _extract(_native(*[f"{label}: {value}" for value in ["000001", "000002", "000001"]]))
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    if "." in path:
        parent, field = path.split(".")
        party = getattr(result.packing_list, parent)
        assert party is None or getattr(party, field) is None
    else:
        assert getattr(result.packing_list, path) is None
    assert len([candidate for candidate in result.candidates if candidate.field_path == path]) == 3
    assert any(issue.field_path == path and issue.is_review_required for issue in result.issues)


def test_partial_result_preserves_missing_fields_and_does_not_invent_completeness():
    result = _extract(_native("PACKING LIST NO: 000045"))
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.packing_list.date is None and result.packing_list.seller is None
    assert result.packing_list.invoice_references == [] and result.packing_list.items == []
    assert result.packing_list.package_count is None and result.packing_list.volume is None


@pytest.mark.parametrize("document", [_native("", pad=False), _native("No supported header evidence."), _native()])
def test_empty_or_unrecognized_pdf_does_not_claim_extracted(document):
    result = _extract(document)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.packing_list == PackingList()
    assert result.issues and any(issue.is_review_required for issue in result.issues)


@pytest.mark.parametrize("source,verification", [
    (TextResolutionSource.TEXT_LAYER, VerificationLevel.UNVERIFIED),
    (TextResolutionSource.OCR_LOCAL, VerificationLevel.SINGLE_PROVIDER),
    (TextResolutionSource.DOCUMENT_VISION_LOCAL, VerificationLevel.SINGLE_PROVIDER),
    (TextResolutionSource.CROSS_VERIFIED_VISUAL, VerificationLevel.CROSS_VERIFIED),
])
def test_safe_resolved_pdf_accepts_approved_source_verification_pairs(source, verification):
    result = _extract(_resolved(source=source, verification=verification))
    assert result.status == ExtractionStatus.EXTRACTED
    field = result.packing_list.packing_list_number
    assert field.normalized_value == "000045" and field.raw_value == "000045"
    assert field.source_document_id == "PACK-PDF" and field.page == 1
    assert field.origin == ValueOrigin.EXTRACTED
    assert field.confidence is not None and field.confidence <= 0.93


@pytest.mark.parametrize("patch", [
    {"requires_review": True}, {"unresolved_pages": [1]}, {"unresolved_pages": [99]},
    {"vision_fallback_recommended": True}, {"file_type": "xlsx"},
    {"document_id": ""}, {"document_id": "   "}, {"page_count": 0}, {"page_count": 2},
    {"visual_pages": []}, {"visual_pages": [1, 1]}, {"visual_pages": [99]},
])
def test_resolved_document_metadata_inconsistency_abstains_whole_document(patch):
    _assert_abstains(_extract(_resolved().model_copy(update=patch)))


@pytest.mark.parametrize("patch", [
    {"requires_review": True}, {"source": TextResolutionSource.UNRESOLVED},
    {"verification_level": VerificationLevel.UNVERIFIED},
    {"verification_level": VerificationLevel.CONFLICT}, {"confidence": 0.1},
    {"page": 2}, {"text": ""}, {"text": "??? !!! @@@"},
    {"text": "PACKING LIST NO: 000045" + "\x00" * 100},
    {"text": "PACKING LIST NO: 000045" + "\ufffd" * 100},
    {"text": "装箱单号: 1"},
])
def test_unsafe_resolved_page_rejects_even_easily_extractable_label(patch):
    document = _resolved()
    document.pages[0] = document.pages[0].model_copy(update=patch)
    _assert_abstains(_extract(document))


@pytest.mark.parametrize("source,verification", [
    (TextResolutionSource.CROSS_VERIFIED_VISUAL, VerificationLevel.SINGLE_PROVIDER),
    (TextResolutionSource.OCR_LOCAL, VerificationLevel.CROSS_VERIFIED),
    (TextResolutionSource.DOCUMENT_VISION_LOCAL, VerificationLevel.CROSS_VERIFIED),
])
def test_inconsistent_visual_source_and_verification_metadata_is_not_trusted(source, verification):
    _assert_abstains(_extract(_resolved(source=source, verification=verification)))


@pytest.mark.parametrize("patch", [
    {"has_text_layer": False}, {"needs_ocr": True}, {"document_id": ""},
    {"document_id": "   "}, {"page_count": 0}, {"page_count": 2},
])
def test_unsafe_native_document_flags_and_page_count_abstain(patch):
    _assert_abstains(_extract(_native("PACKING LIST NO: 000045").model_copy(update=patch)))


@pytest.mark.parametrize("text", [
    "", "??? !!! @@@", "装箱单号: 1", "PACKING LIST NO: 000045" + "\x00" * 100,
    "PACKING LIST NO: 000045" + "\ufffd" * 100,
])
def test_native_text_quality_gate_cannot_be_bypassed_by_header_label(text):
    _assert_abstains(_extract(_native(text, pad=False)))


@pytest.mark.parametrize("pages", [
    [ParsedPdfPage(page=0, text=_FILLER)],
    [ParsedPdfPage(page=2, text="PACKING LIST NO: 000045\n" + _FILLER)],
    [ParsedPdfPage(page=1, text="PACKING LIST NO: 000045\n" + _FILLER), ParsedPdfPage(page=1, text=_FILLER)],
    [ParsedPdfPage(page=1, text="PACKING LIST NO: 000045\n" + _FILLER), ParsedPdfPage(page=3, text=_FILLER)],
])
def test_native_page_identity_must_be_unique_contiguous_and_one_based(pages):
    document = _native("PACKING LIST NO: 000045").model_copy(update={"pages": pages, "page_count": len(pages)})
    _assert_abstains(_extract(document))


def test_native_good_page_cannot_hide_an_unsafe_partial_page():
    _assert_abstains(_extract(_native("PACKING LIST NO: 000045\n" + _FILLER, "", pad=False)))


def test_resolved_good_page_cannot_hide_an_unsafe_partial_page():
    document = _resolved()
    document.page_count = 2
    document.visual_pages = [1, 2]
    document.pages.append(ResolvedPdfPage(
        page=2, text="INVOICE NO: 000007\n" + _FILLER,
        source=TextResolutionSource.OCR_LOCAL, verification_level=VerificationLevel.UNVERIFIED,
        confidence=0.99, requires_review=False,
    ))
    _assert_abstains(_extract(document))


def test_duplicate_resolved_page_ids_are_rejected_even_if_count_matches():
    document = _resolved()
    document.page_count = 2
    document.pages.append(document.pages[0].model_copy())
    _assert_abstains(_extract(document))


def test_native_marked_resolved_page_cannot_have_visual_page_metadata():
    document = _resolved(source=TextResolutionSource.TEXT_LAYER, verification=VerificationLevel.UNVERIFIED)
    document.visual_pages = [1]
    _assert_abstains(_extract(document))


def test_extractor_does_not_mutate_native_or_resolved_inputs():
    for document in [_native("PACKING LIST NO: 000045"), _resolved()]:
        before = document.model_dump(mode="python")
        result = _extract(document)
        assert result.status == ExtractionStatus.EXTRACTED
        assert document.model_dump(mode="python") == before


def test_unknown_input_is_a_typed_technical_failure_without_raw_error_echo():
    result = _extract(object())
    assert result.status == ExtractionStatus.FAILED
    assert result.packing_list == PackingList() and result.candidates == []
    assert result.issues and any(issue.is_review_required for issue in result.issues)
