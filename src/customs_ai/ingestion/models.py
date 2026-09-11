from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator

from customs_ai.ingestion.enums import ProcessingStatus


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    shipment_id: str
    original_filename: str
    file_type: str
    mime_type: str
    file_hash: str
    file_size: int
    stored_path: str
    upload_time: datetime
    processing_status: ProcessingStatus

    detected_document_type: str | None = None
    classification_confidence: float | None = None
    page_count: int | None = None
    sheet_count: int | None = None
    parser_used: str | None = None
    extraction_status: str | None = None

    @field_validator("upload_time")
    @classmethod
    def require_timezone_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("upload_time must be timezone-aware")
        return value.astimezone(timezone.utc)


class UploadResponse(BaseModel):
    document_id: str
    shipment_id: str
    status: ProcessingStatus
    sha256: str
    mime_type: str
    file_size: int
    is_duplicate: bool
