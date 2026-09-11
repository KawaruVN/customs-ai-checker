from customs_ai.vision.providers.base import LocalDocumentVisionProvider, LocalOcrProvider
from customs_ai.vision.providers.paddle_vl_client import LocalPaddleVlServiceClient
from customs_ai.vision.providers.rapidocr import RapidOcrProvider

__all__ = [
    "LocalDocumentVisionProvider",
    "LocalOcrProvider",
    "LocalPaddleVlServiceClient",
    "RapidOcrProvider",
]
