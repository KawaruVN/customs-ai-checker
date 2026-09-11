from typing import Protocol

from PIL import Image

from customs_ai.vision.models import ProviderTextResult


class LocalDocumentVisionProvider(Protocol):
    def process(self, image: Image.Image) -> ProviderTextResult:
        ...


class LocalOcrProvider(Protocol):
    def process(self, image: Image.Image) -> ProviderTextResult:
        ...
