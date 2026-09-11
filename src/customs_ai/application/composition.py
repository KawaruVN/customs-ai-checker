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
