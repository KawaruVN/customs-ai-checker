from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.errors import ClassificationFailedError
from customs_ai.classification.models import DocumentClassificationResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.logger import logger
from customs_ai.repositories.source_documents import SourceDocumentRepository


class DocumentClassificationService:
    def __init__(
        self,
        repository: SourceDocumentRepository,
        parsing_service: DocumentParsingService,
        classifier: DeterministicClassifier,
    ) -> None:
        self.repository = repository
        self.parsing_service = parsing_service
        self.classifier = classifier

    def classify_document(self, document_id: str) -> DocumentClassificationResult:
        source_document = self.repository.get_by_document_id(document_id)
        if not source_document:
            raise ClassificationFailedError(f"SourceDocument '{document_id}' not found.")

        try:
            parsed_doc = self.parsing_service.parse_document(document_id)
            
            result = self.classifier.classify(
                parsed_doc, filename=source_document.original_filename
            )

            new_status = (
                ProcessingStatus.NEEDS_REVIEW
                if result.document_type == DocumentType.UNKNOWN
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
