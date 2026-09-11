from typing import Any

import numpy as np
from PIL import Image

from customs_ai.vision.errors import OcrEngineUnavailableError, OcrFailedError
from customs_ai.vision.models import ProviderTextResult


class RapidOcrProvider:
    """Lazy RapidOCR 3.x adapter. The engine is created once and then reused."""

    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:  # pragma: no cover - installation guard
            raise OcrEngineUnavailableError() from exc
        try:
            self._engine = RapidOCR()
        except Exception as exc:  # pragma: no cover - provider guard
            raise OcrEngineUnavailableError() from exc
        return self._engine

    def process(self, image: Image.Image) -> ProviderTextResult:
        try:
            result = self._get_engine()(np.asarray(image.convert("RGB")))
            txts = getattr(result, "txts", None)
            scores = getattr(result, "scores", None)
            if not txts:
                return ProviderTextResult(provider="RapidOCR", text="", confidence=None)

            text = "\n".join(str(value) for value in txts if str(value).strip())
            confidence = None
            if scores:
                values = [float(score) for score in scores if score is not None]
                if values:
                    confidence = max(0.0, min(1.0, sum(values) / len(values)))
            return ProviderTextResult(
                provider="RapidOCR",
                text=text,
                confidence=confidence,
            )
        except (OcrEngineUnavailableError, OcrFailedError):
            raise
        except Exception as exc:
            raise OcrFailedError() from exc
