from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.errors import ClassificationFailedError
from customs_ai.classification.models import DocumentClassificationResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.logger import logger
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.models import ResolvedPdfDocument
from customs_ai.vision.service import VisualResolutionService


class DocumentClassificationService:
    def __init__(
        self,
        repository: SourceDocumentRepository,
        parsing_service: DocumentParsingService,
        classifier: DeterministicClassifier,
        vision_service: VisualResolutionService | None = None,
    ) -> None:
        self.repository = repository
        self.parsing_service = parsing_service
        self.classifier = classifier
        self.vision_service = vision_service

    def classify_document(self, document_id: str) -> DocumentClassificationResult:
        source_document = self.repository.get_by_document_id(document_id)
        if not source_document:
            raise ClassificationFailedError(f"SourceDocument '{document_id}' not found.")

        try:
            parsed_doc = self.parsing_service.parse_document(document_id)
            resolved_doc = (
                self.vision_service.resolve_document(document_id, parsed_doc)
                if self.vision_service is not None
                else parsed_doc
            )
            result = self.classifier.classify(
                resolved_doc, filename=source_document.original_filename
            )

            vision_requires_review = (
                isinstance(resolved_doc, ResolvedPdfDocument)
                and resolved_doc.requires_review
            )
            if vision_requires_review and result.document_type != DocumentType.UNKNOWN:
                result = result.model_copy(update={"document_type": DocumentType.UNKNOWN})

            new_status = (
                ProcessingStatus.NEEDS_REVIEW
                if vision_requires_review or result.document_type == DocumentType.UNKNOWN
                else ProcessingStatus.CLASSIFIED
            )

            self.repository.update_classification_metadata(
                document_id=document_id,
                detected_document_type=result.document_type.value,
                classification_confidence=result.confidence,
                processing_status=new_status,
            )
            return result

        except Exception as exc:
            error_code = getattr(exc, "code", "CLASSIFICATION_FAILED")
            logger.error(
                "Document classification failed: document_id=%s error_code=%s",
                document_id,
                error_code,
            )
            raise ClassificationFailedError() from exc
