"""Packing application requests/outcomes; canonical and stored types are reused."""

import re
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator

from customs_ai.extraction.packing_models import PackingListHeaderExtractionResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.extraction_models import ExtractionRecord


class PackingExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    document_id: StrictStr
    expected_active_extraction_id: StrictStr | None = None
    expected_source_file_hash: StrictStr | None = None
    expected_processing_status: ProcessingStatus | None = None

    @field_validator("document_id", "expected_active_extraction_id")
    @classmethod
    def identifiers(cls, value):
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("Invalid extraction identifier.")
        return value

    @field_validator("expected_source_file_hash")
    @classmethod
    def fingerprint(cls, value):
        if value is not None and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("Invalid source fingerprint.")
        return value


class PackingExtractionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    document_id: StrictStr | None
    result: PackingListHeaderExtractionResult
    record: ExtractionRecord | None = None
    active_record: ExtractionRecord | None = None

    @field_validator("result", mode="before")
    @classmethod
    def result_snapshot(cls, value):
        data = value.model_dump(mode="python", warnings="error") if isinstance(value, BaseModel) else value
        return PackingListHeaderExtractionResult.model_validate(data)

    @field_validator("record", "active_record", mode="before")
    @classmethod
    def record_snapshot(cls, value):
        if value is None:
            return None
        data = value.model_dump(mode="python", warnings="error") if isinstance(value, BaseModel) else value
        return ExtractionRecord.model_validate(data)

    @model_validator(mode="after")
    def consistent(self):
        for record in (self.record, self.active_record):
            if record is not None and (record.document_id != self.document_id or
                                      not isinstance(record.result, PackingListHeaderExtractionResult)):
                raise ValueError("Incompatible Packing outcome record.")
        if self.record is not None and self.record.result != self.result:
            raise ValueError("Committed result differs from outcome.")
        if self.active_record is not None and not self.active_record.is_active:
            raise ValueError("Active outcome record must be active.")
        return self

    @property
    def persisted(self) -> bool:
        return self.record is not None
