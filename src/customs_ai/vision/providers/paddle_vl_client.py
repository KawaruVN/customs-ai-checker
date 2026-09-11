import base64
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.vision.errors import DocumentVisionFailedError, DocumentVisionUnavailableError
from customs_ai.vision.models import ProviderTextResult


class _MarkdownResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str


class _LayoutParsingResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    markdown: _MarkdownResult
    prunedResult: dict[str, Any] | None = None


class _InferenceResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    layoutParsingResults: list[_LayoutParsingResult]


class _ServiceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    errorCode: int
    errorMsg: str
    result: _InferenceResult | None = None


class LocalPaddleVlServiceClient:
    """Client for the official local PaddleOCR-VL full-pipeline serving API."""

    def __init__(
        self,
        config: VisionSettingsConfig | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or settings.vision
        self._validate_loopback(self.config.vlm_local_endpoint)
        self.endpoint = self.config.vlm_local_endpoint
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(
                connect=self.config.vlm_connect_timeout_seconds,
                read=self.config.vlm_read_timeout_seconds,
                write=10.0,
                pool=self.config.vlm_connect_timeout_seconds,
            )
        )

    @staticmethod
    def _validate_loopback(endpoint: str) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("VLM endpoint must use HTTP or HTTPS.")
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("VLM endpoint must use a loopback host.")

    def process(self, image: Image.Image) -> ProviderTextResult:
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=95)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        payload = {
            "file": encoded,
            "fileType": 1,
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useLayoutDetection": True,
            "returnMarkdownImages": False,
            "visualize": False,
            "prettifyMarkdown": False,
        }
        try:
            response = self.client.post(self.endpoint, json=payload)
        except httpx.ConnectError as exc:
            raise DocumentVisionUnavailableError() from exc
        except httpx.TimeoutException as exc:
            raise DocumentVisionUnavailableError() from exc
        except httpx.HTTPError as exc:
            raise DocumentVisionFailedError() from exc

        if len(response.content) > self.config.vlm_max_response_bytes:
            raise DocumentVisionFailedError()
        if response.status_code == 503:
            raise DocumentVisionUnavailableError()
        if response.status_code >= 400:
            raise DocumentVisionFailedError()

        try:
            parsed = _ServiceResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise DocumentVisionFailedError() from exc

        if parsed.errorCode != 0 or parsed.result is None:
            raise DocumentVisionFailedError()
        if not parsed.result.layoutParsingResults:
            return ProviderTextResult(provider="PaddleOCR-VL-1.6", text="")

        texts = [
            item.markdown.text.strip()
            for item in parsed.result.layoutParsingResults
            if item.markdown.text and item.markdown.text.strip()
        ]
        structured = [
            item.prunedResult
            for item in parsed.result.layoutParsingResults
            if item.prunedResult is not None
        ]
        return ProviderTextResult(
            provider="PaddleOCR-VL-1.6",
            text="\n\n".join(texts),
            confidence=None,
            structured_content=structured or None,
        )
