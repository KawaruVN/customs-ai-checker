"""Strict extraction records and a versioned, local JSON persistence codec.

Canonical models remain authoritative. Candidate typed values need explicit type
tags: their approved union cannot preserve all Python types through bare JSON.
Dates/times use ISO representations (timezone offsets, not timezone class names);
Decimal text preserves precision and scale. No arbitrary object serialization is
supported. A record describes one source document, not a cross-document aggregate.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
import json
import math
import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    TypeAdapter,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticSerializationError

from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import (
    InvoiceHeaderExtractionResult,
    InvoiceItemExtractionResult,
)
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument

ExtractionResult = InvoiceHeaderExtractionResult | InvoiceItemExtractionResult
_RESULT_ADAPTER = TypeAdapter(ExtractionResult)
_RESULT_TYPES = {
    "invoice": InvoiceHeaderExtractionResult,
    "invoice_items": InvoiceItemExtractionResult,
}
_INVALID_RESULT = "Invalid extraction result."
_INVALID_SERIALIZED = "Invalid serialized extraction result."


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Identifier or method must not be blank.")
    return value


def _identifier(value: str) -> str:
    if not value.strip() or value != value.strip():
        raise ValueError("Identifier must be nonblank without surrounding whitespace.")
    return value


def _source_hash(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Source fingerprint must be lowercase SHA-256 hexadecimal.")
    return value


def _fresh_result(value: Any) -> ExtractionResult:
    """Revalidate a Python snapshot, including pre-existing nested instances."""
    try:
        result = _RESULT_ADAPTER.validate_python(value)
        model = (
            InvoiceHeaderExtractionResult
            if isinstance(result, InvoiceHeaderExtractionResult)
            else InvoiceItemExtractionResult
        )
        result = model.model_validate(result.model_dump(mode="python", warnings="error"))
        _check_finite(result.model_dump(mode="python"))
        for candidate in result.candidates:
            _encode_value(candidate.typed_value)
        return result
    except (ValueError, TypeError, OverflowError, PydanticSerializationError):
        raise ValueError(_INVALID_RESULT) from None


def _check_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(_INVALID_RESULT)
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError(_INVALID_RESULT)
    if isinstance(value, dict):
        for child in value.values():
            _check_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _check_finite(child)


def _check_provenance(value: Any, document_id: str) -> None:
    if isinstance(value, dict):
        source = value.get("source_document_id")
        if source is not None and source != document_id:
            raise ValueError("Extraction provenance belongs to another document.")
        for child in value.values():
            _check_provenance(child, document_id)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _check_provenance(child, document_id)


class ExtractionAttempt(BaseModel):
    """Validated attempt input with optimistic source-state guards."""

    model_config = ConfigDict(extra="forbid")

    document_id: StrictStr
    source_file_hash: StrictStr
    expected_processing_status: ProcessingStatus
    # Optional stronger CAS for application callers. Not stored in the payload.
    expected_source_document: SourceDocument | None = None
    result: ExtractionResult
    schema_version: Literal["0.1"] = "0.1"
    extraction_method: StrictStr | None = None

    _validate_document_id = field_validator("document_id")(_identifier)
    _validate_hash = field_validator("source_file_hash")(_source_hash)

    @field_validator("extraction_method")
    @classmethod
    def validate_method(cls, value: str | None) -> str | None:
        return _nonblank(value) if value is not None else None

    @field_validator("result", mode="before")
    @classmethod
    def validate_result(cls, value: Any) -> ExtractionResult:
        return _fresh_result(value)

    @model_validator(mode="after")
    def check_source_provenance(self) -> "ExtractionAttempt":
        if self.expected_source_document is not None and (
            self.expected_source_document.document_id != self.document_id
            or self.expected_source_document.file_hash != self.source_file_hash
            or self.expected_source_document.processing_status != self.expected_processing_status
        ):
            raise ValueError("Source snapshot preconditions are inconsistent.")
        _check_provenance(self.result.model_dump(mode="python"), self.document_id)
        return self


class ExtractionReplacement(ExtractionAttempt):
    """Explicit replacement identifying the active record the caller observed."""

    expected_active_extraction_id: StrictStr

    _validate_expected_id = field_validator("expected_active_extraction_id")(_identifier)


class ExtractionRecord(BaseModel):
    """Validated stored attempt; FAILED records are historical, never active."""

    model_config = ConfigDict(extra="forbid")

    extraction_id: StrictStr
    document_id: StrictStr
    attempt_number: Annotated[int, Field(strict=True, gt=0)]
    result: ExtractionResult
    status: ExtractionStatus
    is_active: StrictBool
    created_at: datetime
    schema_version: Literal["0.1"] = "0.1"
    extraction_method: StrictStr | None = None
    source_file_hash: StrictStr
    supersedes_extraction_id: StrictStr | None = None

    _validate_ids = field_validator("extraction_id", "document_id")(_identifier)
    _validate_hash = field_validator("source_file_hash")(_source_hash)

    @field_validator("supersedes_extraction_id")
    @classmethod
    def validate_superseded_id(cls, value: str | None) -> str | None:
        return _identifier(value) if value is not None else None

    @field_validator("extraction_method")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _nonblank(value) if value is not None else None

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Extraction timestamp must be timezone-aware.")
        return value.astimezone(timezone.utc)

    @field_validator("result", mode="before")
    @classmethod
    def validate_result(cls, value: Any) -> ExtractionResult:
        return _fresh_result(value)

    @model_validator(mode="after")
    def check_status_and_source(self) -> "ExtractionRecord":
        if self.status != self.result.status:
            raise ValueError("Record status differs from the extraction result.")
        if self.status == ExtractionStatus.FAILED and self.is_active:
            raise ValueError("Failed extraction records cannot be active.")
        _check_provenance(self.result.model_dump(mode="python"), self.document_id)
        return self


def _encode_value(value: Any) -> dict[str, Any]:
    if value is None:
        kind, encoded = "none", None
    elif type(value) is bool:
        kind, encoded = "bool", value
    elif type(value) is int:
        kind, encoded = "int", value
    elif type(value) is float and math.isfinite(value):
        kind, encoded = "float", value
    elif type(value) is str:
        kind, encoded = "str", value
    elif isinstance(value, Decimal) and value.is_finite():
        kind, encoded = "decimal", str(value)
    elif isinstance(value, datetime):
        kind, encoded = "datetime", value.isoformat()
    elif isinstance(value, date):
        kind, encoded = "date", value.isoformat()
    elif isinstance(value, time):
        kind, encoded = "time", value.isoformat()
    else:
        raise ValueError(_INVALID_RESULT)
    return {"type": kind, "value": encoded}


def _decode_value(tag: Any) -> Any:
    if type(tag) is not dict or set(tag) != {"type", "value"}:
        raise ValueError(_INVALID_SERIALIZED)
    kind, value = tag["type"], tag["value"]
    primitive_types = {"none": type(None), "bool": bool, "int": int, "float": float, "str": str}
    if not isinstance(kind, str):
        raise ValueError(_INVALID_SERIALIZED)
    if kind in primitive_types:
        if type(value) is not primitive_types[kind]:
            raise ValueError(_INVALID_SERIALIZED)
        if kind == "float" and not math.isfinite(value):
            raise ValueError(_INVALID_SERIALIZED)
        return value
    if type(value) is not str:
        raise ValueError(_INVALID_SERIALIZED)
    if kind == "decimal":
        decoded = Decimal(value)
        if not decoded.is_finite() or str(decoded) != value:
            raise ValueError(_INVALID_SERIALIZED)
        return decoded
    parsers = {"date": date.fromisoformat, "datetime": datetime.fromisoformat, "time": time.fromisoformat}
    if kind not in parsers:
        raise ValueError(_INVALID_SERIALIZED)
    decoded = parsers[kind](value)
    if decoded.isoformat() != value:
        raise ValueError(_INVALID_SERIALIZED)
    return decoded


def _reject_constant(value: str) -> None:
    raise ValueError(_INVALID_SERIALIZED)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_INVALID_SERIALIZED)
        result[key] = value
    return result


def serialize_result(result: ExtractionResult) -> str:
    """Serialize only approved results, preserving candidate typed-value types."""
    try:
        validated = _fresh_result(result)
        data = validated.model_dump(mode="json")
        for candidate, source in zip(data["candidates"], validated.candidates, strict=True):
            candidate["typed_value"] = _encode_value(source.typed_value)
        envelope = {
            "format_version": 1,
            "result_type": "invoice" if isinstance(validated, InvoiceHeaderExtractionResult) else "invoice_items",
            "result": data,
        }
        return json.dumps(envelope, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (ValueError, TypeError, OverflowError):
        raise ValueError(_INVALID_RESULT) from None


def deserialize_result(serialized: str) -> ExtractionResult:
    """Validate the wire envelope, decode known tags, then validate canonical data."""
    try:
        if type(serialized) is not str:
            raise ValueError(_INVALID_SERIALIZED)
        envelope = json.loads(serialized, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if type(envelope) is not dict or set(envelope) != {"format_version", "result_type", "result"}:
            raise ValueError(_INVALID_SERIALIZED)
        if type(envelope["format_version"]) is not int or envelope["format_version"] != 1:
            raise ValueError(_INVALID_SERIALIZED)
        kind = envelope["result_type"]
        if not isinstance(kind, str) or kind not in _RESULT_TYPES:
            raise ValueError(_INVALID_SERIALIZED)
        data = envelope["result"]
        if type(data) is not dict or type(data.get("candidates")) is not list:
            raise ValueError(_INVALID_SERIALIZED)
        for candidate in data["candidates"]:
            if type(candidate) is not dict or "typed_value" not in candidate:
                raise ValueError(_INVALID_SERIALIZED)
            candidate["typed_value"] = _decode_value(candidate["typed_value"])
        return _fresh_result(_RESULT_TYPES[kind].model_validate(data))
    except (ValueError, TypeError, InvalidOperation, OverflowError, RecursionError):
        raise ValueError(_INVALID_SERIALIZED) from None
