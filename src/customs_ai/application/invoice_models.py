"""Application contracts; stored payloads remain the approved extraction models."""

import re

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from customs_ai.extraction.models import InvoiceHeaderExtractionResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.extraction_models import ExtractionRecord


class InvoiceExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: StrictStr
    expected_active_extraction_id: StrictStr | None = None
    expected_source_file_hash: StrictStr | None = None
    expected_processing_status: ProcessingStatus | None = None

    @field_validator("document_id", "expected_active_extraction_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("Invalid extraction identifier.")
        return value

    @field_validator("expected_source_file_hash")
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("Invalid source fingerprint.")
        return value


class InvoiceExtractionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: StrictStr | None
    result: InvoiceHeaderExtractionResult
    record: ExtractionRecord | None = None

    @property
    def persisted(self) -> bool:
        return self.record is not None
