from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
import warnings

import pytest
from pydantic import ValidationError

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice, InvoiceItem
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import (
    ExtractionCandidate,
    ExtractionIssue,
    InvoiceHeaderExtractionResult,
    InvoiceItemExtractionResult,
)
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.extraction_models import (
    ExtractionAttempt,
    ExtractionRecord,
    ExtractionReplacement,
    deserialize_result,
    serialize_result,
)


def result(status=ExtractionStatus.EXTRACTED):
    return InvoiceHeaderExtractionResult(
        invoice=Invoice(
            invoice_number=CanonicalField[str](
                raw_value=" 0000123 ", normalized_value="0000123", origin=ValueOrigin.EXTRACTED,
                source_document_id="DOC-1", sheet="中文", cell="B12", page=2,
                bounding_box=(1.0, 2.0, 3.0, 4.0), confidence=0.95, extraction_method="synthetic",
            ),
            invoice_date=CanonicalField[date](
                raw_value="2026-10-28", normalized_value=date(2026, 10, 28),
                origin=ValueOrigin.EXTRACTED, source_document_id="DOC-1",
            ),
            total_amount=CanonicalField[Decimal](
                raw_value="12.500", normalized_value=Decimal("12.500"),
                origin=ValueOrigin.EXTRACTED, source_document_id="DOC-1",
            ),
            items=[InvoiceItem(quantity=CanonicalField[Decimal](
                raw_value="0", normalized_value=Decimal("0.000"),
                origin=ValueOrigin.EXTRACTED, source_document_id="DOC-1", cell="C14",
            ))],
        ),
        status=status,
        issues=[ExtractionIssue(code="SYNTHETIC_REVIEW", message="Synthetic safe issue.")],
    )


def attempt_data(**overrides):
    return {
        "document_id": "DOC-1", "source_file_hash": "a" * 64,
        "expected_processing_status": ProcessingStatus.CLASSIFIED,
        "result": result(), **overrides,
    }


def record_data(**overrides):
    return {
        "extraction_id": "EXT-1", "document_id": "DOC-1", "attempt_number": 1,
        "result": result(), "status": ExtractionStatus.EXTRACTED, "is_active": True,
        "created_at": datetime(2026, 10, 28, tzinfo=timezone.utc), "source_file_hash": "a" * 64,
        **overrides,
    }


def test_canonical_values_raw_and_complete_provenance_round_trip():
    original = result()
    restored = deserialize_result(serialize_result(original))
    assert restored == original
    assert restored.invoice.total_amount.normalized_value.as_tuple() == Decimal("12.500").as_tuple()
    assert restored.invoice.items[0].quantity.normalized_value.as_tuple() == Decimal("0.000").as_tuple()
    assert type(restored.invoice.invoice_date.normalized_value) is date
    assert restored.invoice.invoice_number.raw_value == " 0000123 "


def test_persistence_ids_cannot_create_records_unreadable_by_lookup_api():
    for identifier in [" DOC-1", "DOC-1 ", "DOC-1\n"]:
        with pytest.raises(ValidationError):
            ExtractionAttempt(**attempt_data(document_id=identifier))
        with pytest.raises(ValidationError):
            ExtractionRecord(**record_data(extraction_id=identifier))
        with pytest.raises(ValidationError):
            ExtractionRecord(**record_data(supersedes_extraction_id=identifier))
        with pytest.raises(ValidationError):
            ExtractionReplacement(**attempt_data(), expected_active_extraction_id=identifier)


def test_derived_result_cannot_extend_approved_persisted_business_schema():
    class ExtendedResult(InvoiceHeaderExtractionResult):
        customer_layout_value: str

    extended = ExtendedResult(
        **result().model_dump(mode="python"), customer_layout_value="synthetic"
    )
    with pytest.raises(ValueError, match="Invalid extraction result"):
        serialize_result(extended)
    with pytest.raises(ValidationError):
        ExtractionAttempt(**attempt_data(result=extended))


@pytest.mark.parametrize("value", [
    Decimal("12.500"), Decimal("-0.000"), date(2026, 10, 28),
    datetime(2026, 10, 28, 9, 15, 22, 1234, tzinfo=timezone(timedelta(hours=7))),
    datetime(2026, 10, 28, 9, 15), time(9, 15, 22, 1234), time(9, tzinfo=timezone.utc),
    "12.500", "2026-10-28", "2026-10-28T09:15:00+07:00", "0000123", "", True, False,
    0, 12, 0.0, -0.0, 12.5, None,
])
def test_candidate_typed_values_preserve_exact_types(value):
    original = result()
    original.candidates = [ExtractionCandidate(
        field_path="test", raw_value="synthetic", source_document_id="DOC-1", typed_value=value,
    )]
    restored = deserialize_result(serialize_result(original)).candidates[0].typed_value
    assert type(restored) is type(value)
    assert restored == value
    if isinstance(value, Decimal):
        assert restored.as_tuple() == value.as_tuple()
    if isinstance(value, float):
        assert restored.hex() == value.hex()


def test_item_result_uses_existing_canonical_model_and_preserves_status():
    original = InvoiceItemExtractionResult(
        items=result().invoice.items, status=ExtractionStatus.NEEDS_REVIEW,
        candidates=[ExtractionCandidate(field_path="items[0].quantity", raw_value="0", typed_value=Decimal("0.00"))],
    )
    restored = deserialize_result(serialize_result(original))
    assert type(restored) is InvoiceItemExtractionResult
    assert isinstance(restored.items[0], InvoiceItem)
    assert restored == original
    assert restored.status == ExtractionStatus.NEEDS_REVIEW


@pytest.mark.parametrize("changes", [
    {"document_id": " "}, {"document_id": 12}, {"source_file_hash": "A" * 64},
    {"source_file_hash": "a" * 63}, {"source_file_hash": "a" * 64 + "\n"},
    {"source_file_hash": 123}, {"expected_processing_status": "UNKNOWN"},
    {"schema_version": "1.0"}, {"extraction_method": " "}, {"extraction_method": 123},
    {"unexpected": "extra"},
])
def test_attempt_rejects_invalid_and_extra_metadata(changes):
    with pytest.raises(ValidationError):
        ExtractionAttempt(**attempt_data(**changes))


def test_explicit_replacement_requires_nonblank_observed_active_identifier():
    assert ExtractionReplacement(**attempt_data(), expected_active_extraction_id="EXT-1").expected_active_extraction_id == "EXT-1"
    for identifier in [None, " ", 12]:
        with pytest.raises(ValidationError):
            ExtractionReplacement(**attempt_data(), expected_active_extraction_id=identifier)
    with pytest.raises(ValidationError):
        ExtractionReplacement(**attempt_data())


@pytest.mark.parametrize("changes", [
    {"attempt_number": True}, {"attempt_number": "1"}, {"attempt_number": 0},
    {"is_active": 1}, {"extraction_id": " "}, {"document_id": ""},
    {"created_at": datetime(2026, 10, 28)}, {"status": "UNKNOWN"},
    {"status": ExtractionStatus.NEEDS_REVIEW}, {"extra": "field"},
    {"supersedes_extraction_id": " "},
])
def test_record_rejects_invalid_strict_metadata_or_status_conflict(changes):
    with pytest.raises(ValidationError):
        ExtractionRecord(**record_data(**changes))


def test_failed_history_cannot_be_active_and_timestamp_is_utc():
    data = record_data(result=result(ExtractionStatus.FAILED), status=ExtractionStatus.FAILED)
    with pytest.raises(ValidationError):
        ExtractionRecord(**data)
    data["is_active"] = False
    data["created_at"] = datetime(2026, 10, 28, 7, tzinfo=timezone(timedelta(hours=7)))
    record = ExtractionRecord(**data)
    assert record.status == ExtractionStatus.FAILED
    assert record.created_at == datetime(2026, 10, 28, tzinfo=timezone.utc)
    assert record.created_at.tzinfo is timezone.utc


@pytest.mark.parametrize("location", ["canonical", "candidate"])
def test_document_provenance_must_match_attempt_and_record(location):
    original = result()
    if location == "canonical":
        original.invoice.items[0].quantity.source_document_id = "DOC-OTHER"
    else:
        original.candidates = [ExtractionCandidate(field_path="test", raw_value="synthetic", source_document_id="DOC-OTHER")]
    with pytest.raises(ValidationError):
        ExtractionAttempt(**attempt_data(result=original))
    with pytest.raises(ValidationError):
        ExtractionRecord(**record_data(result=original))


def test_mutated_or_constructed_nested_results_are_revalidated_before_persistence():
    original = result()
    original.invoice.invoice_number.raw_value = None
    with pytest.raises(ValueError, match="Invalid extraction result"):
        serialize_result(original)
    with pytest.raises(ValidationError):
        ExtractionAttempt(**attempt_data(result=original))
    constructed = InvoiceItemExtractionResult.model_construct(items=[{"unknown": "field"}], status=ExtractionStatus.EXTRACTED)
    with pytest.raises(ValueError, match="Invalid extraction result"):
        serialize_result(constructed)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_nonfinite_candidate_numeric_values_are_rejected_before_write(value):
    original = result()
    candidate = ExtractionCandidate(field_path="test", raw_value="synthetic")
    candidate.typed_value = value
    original.candidates = [candidate]
    with pytest.raises(ValueError):
        serialize_result(original)


@pytest.mark.parametrize("tag", [
    None, "12.500", {"type": "decimal", "value": "NaN"},
    {"type": "decimal", "value": "Infinity"}, {"type": "decimal", "value": "not-decimal"},
    {"type": "decimal", "value": "1_2"}, {"type": "float", "value": 1},
    {"type": "int", "value": True}, {"type": "str", "value": 12},
    {"type": "date", "value": "2026-13-28"}, {"type": "datetime", "value": "2026-10-28"},
    {"type": "unknown", "value": "synthetic"}, {"type": "none", "value": 1},
    {"type": "str", "value": "synthetic", "extra": True}, {"value": "synthetic"},
])
def test_read_rejects_malformed_missing_or_unknown_candidate_type_tags(tag):
    original = result()
    original.candidates = [ExtractionCandidate(field_path="test", raw_value="synthetic")]
    envelope = json.loads(serialize_result(original))
    envelope["result"]["candidates"][0]["typed_value"] = tag
    with pytest.raises(ValueError, match="Invalid serialized extraction result"):
        deserialize_result(json.dumps(envelope))


@pytest.mark.parametrize("change", ["extra", "version", "boolean_version", "kind", "missing_candidates", "bad_status", "bad_field", "missing_tag"])
def test_read_rejects_malformed_envelope_and_payload(change):
    original = result()
    original.candidates = [ExtractionCandidate(field_path="test", raw_value="synthetic")]
    envelope = json.loads(serialize_result(original))
    if change == "extra":
        envelope["extra"] = True
    elif change == "version":
        envelope["format_version"] = 2
    elif change == "boolean_version":
        envelope["format_version"] = True
    elif change == "kind":
        envelope["result_type"] = "unknown"
    elif change == "missing_candidates":
        del envelope["result"]["candidates"]
    elif change == "bad_status":
        envelope["result"]["status"] = "UNKNOWN"
    elif change == "bad_field":
        envelope["result"]["invoice"]["extra"] = "bad"
    else:
        del envelope["result"]["candidates"][0]["typed_value"]
    with pytest.raises(ValueError):
        deserialize_result(json.dumps(envelope))


@pytest.mark.parametrize("serialized", ["not JSON", "[]", "null", '{"format_version":1,"format_version":1}', '{"format_version":NaN}', 12])
def test_read_rejects_invalid_json_duplicate_keys_nonfinite_tokens_and_nonstring_input(serialized):
    with pytest.raises(ValueError, match="Invalid serialized extraction result"):
        deserialize_result(serialized)


def test_nonfinite_geometry_is_rejected_on_write_and_overflow_json_read():
    original = result()
    original.invoice.invoice_number.bounding_box = (1.0, 2.0, float("inf"), 4.0)
    with pytest.raises(ValueError):
        serialize_result(original)
    serialized = serialize_result(result())
    envelope = json.loads(serialized)
    envelope["result"]["invoice"]["invoice_number"]["bounding_box"][2] = "overflow_placeholder"
    serialized = json.dumps(envelope).replace('"overflow_placeholder"', "1e999")
    with pytest.raises(ValueError):
        deserialize_result(serialized)


def test_rejected_constructed_payload_does_not_emit_raw_values_in_warnings_or_logs(caplog):
    sensitive_marker = "synthetic-sensitive-marker-123"
    original = InvoiceItemExtractionResult.model_construct(
        items=[{"unexpected": sensitive_marker}], status=ExtractionStatus.EXTRACTED,
    )
    with warnings.catch_warnings(record=True) as emitted:
        with pytest.raises(ValueError) as failure:
            serialize_result(original)
    assert emitted == []
    assert sensitive_marker not in str(failure.value)
    assert sensitive_marker not in caplog.text
