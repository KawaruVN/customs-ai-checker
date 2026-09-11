from pydantic import BaseModel, ConfigDict, Field

from customs_ai.classification.enums import ClassificationMethod, DocumentType


class ClassificationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_document_type: DocumentType
    clue: str
    weight: float = Field(ge=0.0, le=1.0)
    page: int | None = None
    sheet: str | None = None
    cell: str | None = None


class DocumentClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    method: ClassificationMethod
    evidence: list[ClassificationEvidence]
