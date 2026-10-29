from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.service import DocumentClassificationService
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.factory import vision_service_factory


def build_classification_service(
    repository: SourceDocumentRepository | None = None,
) -> DocumentClassificationService:
    repo = repository or SourceDocumentRepository()
    parsing = DocumentParsingService(repo)
    classifier = DeterministicClassifier(load_classification_config())
    vision = vision_service_factory(repo)
    return DocumentClassificationService(
        repository=repo,
        parsing_service=parsing,
        classifier=classifier,
        vision_service=vision,
    )


def build_invoice_extraction_service(
    repository: SourceDocumentRepository | None = None,
    *, semantic_provider=None,
):
    """Build local extraction dependencies; semantic fallback is opt-in only."""
    from customs_ai.application.invoice_extraction import InvoiceExtractionService
    from customs_ai.repositories.document_extractions import DocumentExtractionRepository

    repo = repository if repository is not None else SourceDocumentRepository()
    return InvoiceExtractionService(
        repository=repo,
        parsing_service=DocumentParsingService(repo),
        classifier=DeterministicClassifier(load_classification_config()),
        extraction_repository=DocumentExtractionRepository(),
        vision_service=vision_service_factory(repo),
        semantic_provider=semantic_provider,
    )
