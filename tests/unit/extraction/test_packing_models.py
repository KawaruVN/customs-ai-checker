from datetime import date
from decimal import Decimal
from typing import get_args

import pytest
from pydantic import ValidationError

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, PackingItem, PackingList, Party
from customs_ai.domain.schema import Invoice
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_date, parse_decimal
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue
from customs_ai.extraction.packing_models import PackingItemExtractionResult, PackingListHeaderExtractionResult


def field(value, raw="synthetic", **provenance):
    return CanonicalField(normalized_value=value, raw_value=raw, origin=ValueOrigin.EXTRACTED,
                          source_document_id="DOC-PACKING", **provenance)


def packing():
    return PackingList(
        packing_list_number=field("000045", " 000045 ", page=2),
        date=field(date(2026, 10, 29), "2026/10/29", page=2),
        seller=Party(name=field("Synthetic Seller", "Synthetic Seller", page=1)),
        buyer=Party(name=field("Synthetic Buyer", "Synthetic Buyer", page=1)),
        invoice_references=[field("000001", "000001", page=2), field("000002", "000002", page=2)],
        package_count=field(Decimal("0.00"), "0.00", sheet="Packing", cell="C3"),
        gross_weight=field(Decimal("12345678901234567890.1200"), "12345678901234567890.1200", page=3),
        net_weight=field(Decimal("-2.50"), "-2.50", page=3),
        dimensions=field("10 x 20 x 30 CM", "10 x 20 x 30 CM", page=3),
        volume=field(Decimal("0.20"), "0.20", page=3),
    )


def item():
    return PackingItem(
        item_code=field("000009", "000009", sheet="Packing", cell="B8"),
        description=field("Synthetic pump", "Synthetic pump", sheet="Packing", cell="C8"),
        quantity=field(Decimal("0.00"), "0.00", sheet="Packing", cell="D8"),
        package_number=field("000007", "000007", sheet="Packing", cell="F8"),
        gross_weight=field(Decimal("3.5000"), "3.5000", sheet="Packing", cell="G8"),
        net_weight=field(Decimal("-0.5000"), "-0.5000", sheet="Packing", cell="H8"),
    )


def test_canonical_types_precision_raw_and_provenance_survive_result_roundtrip():
    original = PackingListHeaderExtractionResult(packing_list=packing(), status=ExtractionStatus.EXTRACTED)
    restored = PackingListHeaderExtractionResult.model_validate_json(original.model_dump_json())
    assert restored == original
    assert type(restored.packing_list) is PackingList
    assert type(restored.packing_list.date.normalized_value) is date
    assert restored.packing_list.gross_weight.normalized_value.as_tuple() == Decimal("12345678901234567890.1200").as_tuple()
    assert restored.packing_list.packing_list_number.raw_value == " 000045 "
    assert restored.packing_list.packing_list_number.normalized_value == "000045"
    assert restored.packing_list.packing_list_number.page == 2
    assert restored.packing_list.package_count.sheet == "Packing"
    assert restored.packing_list.package_count.cell == "C3"
    assert restored.packing_list.package_count.normalized_value == Decimal("0")
    assert restored.packing_list.net_weight.normalized_value == Decimal("-2.50")


def test_packing_date_annotation_is_the_actual_calendar_date_type():
    packing_field_type = next(kind for kind in get_args(PackingList.model_fields["date"].annotation) if kind is not type(None))
    assert date in get_args(packing_field_type.model_fields["normalized_value"].annotation)
    assert packing_field_type is CanonicalField[date]
    invoice_field_type = next(kind for kind in get_args(Invoice.model_fields["invoice_date"].annotation) if kind is not type(None))
    assert invoice_field_type is CanonicalField[date]


def test_direct_canonical_date_validation_roundtrip_and_provenance():
    source = CanonicalField[date](
        normalized_value=date(2026, 10, 29), raw_value="2026/10/29",
        origin=ValueOrigin.EXTRACTED, source_document_id="DOC-PACKING",
        page=2, sheet="Packing", cell="C4", bounding_box=(1, 2, 3, 4),
        extraction_method="synthetic", confidence=0.9,
    )
    packing_list = PackingList(date=source)
    restored = PackingList.model_validate_json(packing_list.model_dump_json())
    assert restored.date == source
    assert type(restored.date.normalized_value) is date
    assert restored.date.raw_value == "2026/10/29"
    assert restored.date.source_document_id == "DOC-PACKING"
    assert restored.date.page == 2 and restored.date.sheet == "Packing" and restored.date.cell == "C4"
    invoice = Invoice(invoice_date=source)
    assert Invoice.model_validate_json(invoice.model_dump_json()).invoice_date == source
    for missing in ["raw_value", "source_document_id"]:
        data = source.model_dump(mode="python")
        data[missing] = None
        with pytest.raises(ValidationError):
            PackingList(date=data)


@pytest.mark.parametrize("invalid", ["not-a-date", "2026-02-30", "01/02/2026", {}, [], True])
def test_direct_packing_date_rejects_invalid_values(invalid):
    data = dict(normalized_value=invalid, raw_value="synthetic", origin=ValueOrigin.EXTRACTED, source_document_id="DOC-PACKING")
    with pytest.raises(ValidationError):
        PackingList(date=data)


def test_item_contract_uses_existing_model_and_keeps_document_and_item_weights_distinct():
    result = PackingItemExtractionResult(items=[item()], status=ExtractionStatus.EXTRACTED)
    restored = PackingItemExtractionResult.model_validate_json(result.model_dump_json())
    assert restored == result and type(restored.items[0]) is PackingItem
    assert restored.items[0].package_number.normalized_value == "000007"
    assert restored.items[0].quantity.normalized_value.as_tuple() == Decimal("0.00").as_tuple()
    assert restored.items[0].gross_weight.normalized_value.as_tuple() == Decimal("3.5000").as_tuple()
    assert restored.items[0].net_weight.cell == "H8"
    assert restored.items[0].unit is None
    assert packing().gross_weight.normalized_value != restored.items[0].gross_weight.normalized_value


def test_invoice_references_stay_a_list_and_do_not_replace_packing_number():
    result = PackingListHeaderExtractionResult(packing_list=packing(), status=ExtractionStatus.EXTRACTED)
    assert [value.normalized_value for value in result.packing_list.invoice_references] == ["000001", "000002"]
    data = packing().model_dump(mode="python")
    data["invoice_references"] = field("000001").model_dump(mode="python")
    with pytest.raises(ValidationError):
        PackingListHeaderExtractionResult(packing_list=data, status=ExtractionStatus.NEEDS_REVIEW)


def test_empty_uncertain_and_failed_results_never_fabricate_values():
    for status in [ExtractionStatus.NEEDS_REVIEW, ExtractionStatus.FAILED]:
        header = PackingListHeaderExtractionResult(packing_list=PackingList(), status=status)
        rows = PackingItemExtractionResult(status=status)
        assert header.packing_list.packing_list_number is None
        assert header.packing_list.package_count is None
        assert header.packing_list.invoice_references == [] and header.packing_list.items == []
        assert rows.items == []
    with pytest.raises(ValidationError):
        PackingListHeaderExtractionResult(packing_list=PackingList())
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(items=[])


@pytest.mark.parametrize("factory", [
    lambda: PackingListHeaderExtractionResult(packing_list=PackingList(), status=ExtractionStatus.EXTRACTED),
    lambda: PackingItemExtractionResult(items=[], status=ExtractionStatus.EXTRACTED),
    lambda: PackingItemExtractionResult(items=[item(), PackingItem()], status=ExtractionStatus.EXTRACTED),
    lambda: PackingListHeaderExtractionResult(packing_list=PackingList(items=[item()]), status=ExtractionStatus.EXTRACTED),
    lambda: PackingItemExtractionResult(items=[PackingItem(quantity=field(None, "uncertain"))], status=ExtractionStatus.EXTRACTED),
    lambda: PackingListHeaderExtractionResult(packing_list=packing(), status=ExtractionStatus.EXTRACTED,
              issues=[ExtractionIssue(code="UNCERTAIN", message="Synthetic issue", is_review_required=True)]),
])
def test_extracted_rejects_empty_unresolved_and_contradictory_success(factory):
    with pytest.raises(ValidationError):
        factory()


@pytest.mark.parametrize("bad", ["bad", "=2*5", float("inf"), float("nan")])
def test_bad_decimal_business_values_are_rejected(bad):
    data = item().model_dump(mode="python")
    data["quantity"]["normalized_value"] = bad
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(items=[data], status=ExtractionStatus.NEEDS_REVIEW)


def test_unapproved_fields_dates_provenance_and_extra_result_fields_fail_closed():
    for change in [
        {"date": field("2026-02-30").model_dump(mode="python")},
        {"unapproved": "layout-specific"},
        {"packing_list_number": {"normalized_value": "000045", "origin": "EXTRACTED"}},
    ]:
        data = packing().model_dump(mode="python") | change
        with pytest.raises(ValidationError):
            PackingListHeaderExtractionResult(packing_list=data, status=ExtractionStatus.NEEDS_REVIEW)
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(items=[{"price": field(Decimal("1"))}], status=ExtractionStatus.NEEDS_REVIEW)
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW, extra="unknown")
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(status="PASS")


def test_nested_models_and_revalidated_results_cannot_hide_invalid_mutations():
    original = packing()
    original.gross_weight.normalized_value = "not-a-decimal"
    with pytest.raises(ValidationError):
        PackingListHeaderExtractionResult(packing_list=original, status=ExtractionStatus.NEEDS_REVIEW)
    result = PackingItemExtractionResult(items=[item()], status=ExtractionStatus.EXTRACTED)
    result.items[0].item_code.source_document_id = None
    with pytest.raises(ValidationError):
        PackingItemExtractionResult.model_validate(result)
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(items=[PackingItem.model_construct(quantity="invalid")], status=ExtractionStatus.NEEDS_REVIEW)


def test_issue_and_candidate_reuse_detached_defaults_and_nested_validation():
    first = PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW)
    second = PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW)
    first.issues.append(ExtractionIssue(code="A", message="Synthetic"))
    first.candidates.append(ExtractionCandidate(field_path="quantity", raw_value="=1+1", sheet="Packing", cell="D8"))
    first.items.append(item())
    assert second.issues == second.candidates == second.items == []
    candidate = ExtractionCandidate(field_path="quantity", raw_value="1", source_document_id="DOC-PACKING", typed_value=Decimal("1.00"))
    result = PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW, candidates=[candidate])
    restored = PackingItemExtractionResult.model_validate(result.model_dump(mode="python"))
    assert type(restored.candidates[0]) is ExtractionCandidate
    assert restored.candidates[0].typed_value.as_tuple() == Decimal("1.00").as_tuple()
    candidate.page = -1
    with pytest.raises(ValidationError):
        PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW, candidates=[candidate])


def test_approved_lexical_parsers_remain_the_only_numeric_date_interpretation():
    assert parse_decimal("12,50") == Decimal("12.50")
    for raw in ["1,200", "1.200", "=2*5", "USD 12.50"]:
        assert parse_decimal(raw) is None
    assert parse_date("2026/10/29") == date(2026, 10, 29)
    assert parse_date("01/02/2026") is None
    assert parse_date("2026-02-30") is None
