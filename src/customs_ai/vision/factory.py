from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.providers.paddle_vl_client import LocalPaddleVlServiceClient
from customs_ai.vision.providers.rapidocr import RapidOcrProvider
from customs_ai.vision.service import VisualResolutionService


def vision_service_factory(
    repository: SourceDocumentRepository,
    config: VisionSettingsConfig | None = None,
) -> VisualResolutionService | None:
    cfg = config or settings.vision
    if not cfg.enabled:
        return None
    return VisualResolutionService(
        repository=repository,
        vlm_provider=LocalPaddleVlServiceClient(cfg),
        ocr_provider=RapidOcrProvider(),
        config=cfg,
    )
