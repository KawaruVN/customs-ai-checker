import json
import threading
import time

import httpx
import pytest
from PIL import Image

from customs_ai.config import VisionSettingsConfig
from customs_ai.vision.errors import DocumentVisionFailedError, DocumentVisionUnavailableError
from customs_ai.vision.providers.paddle_vl_client import LocalPaddleVlServiceClient
from customs_ai.vision.providers.rapidocr import RapidOcrProvider


def _image():
    return Image.new("RGB", (20, 20), "white")


def _client(handler, max_concurrency=1):
    cfg = VisionSettingsConfig(
        vlm_local_endpoint="http://127.0.0.1:9090/layout-parsing",
        vlm_max_response_bytes=100_000,
        vlm_max_concurrency=max_concurrency,
    )
    return LocalPaddleVlServiceClient(cfg, httpx.Client(transport=httpx.MockTransport(handler)))


def test_loopback_config_accepts_local_hosts_and_rejects_remote():
    for host in ("127.0.0.1", "localhost", "::1"):
        endpoint = f"http://[{host}]:9090/layout-parsing" if host == "::1" else f"http://{host}:9090/layout-parsing"
        VisionSettingsConfig(vlm_local_endpoint=endpoint)
    for endpoint in (
        "http://192.168.1.10:9090/layout-parsing",
        "https://8.8.8.8/layout-parsing",
        "https://example.com/layout-parsing",
    ):
        with pytest.raises(ValueError):
            VisionSettingsConfig(vlm_local_endpoint=endpoint)


def test_paddle_client_parses_official_service_contract_without_real_network():
    def handler(request):
        body = json.loads(request.content)
        assert body["fileType"] == 1
        return httpx.Response(
            200,
            json={
                "logId": "x",
                "errorCode": 0,
                "errorMsg": "Success",
                "result": {
                    "layoutParsingResults": [
                        {"markdown": {"text": "COMMERCIAL INVOICE INV-001"}, "prunedResult": {"ok": True}}
                    ],
                    "dataInfo": {},
                },
            },
        )

    res = _client(handler).process(_image())
    assert res.provider == "PaddleOCR-VL-1.6"
    assert "COMMERCIAL INVOICE" in res.text
    assert res.structured_content == [{"ok": True}]


def test_paddle_client_maps_503_and_malformed_payload_to_safe_errors():
    with pytest.raises(DocumentVisionUnavailableError):
        _client(lambda request: httpx.Response(503, json={"error": "down"})).process(_image())
    with pytest.raises(DocumentVisionFailedError):
        _client(lambda request: httpx.Response(200, content=b"not-json")).process(_image())


def test_paddle_client_rejects_out_of_range_confidence_if_service_adds_it():
    # The official full-pipeline response currently does not expose a single confidence score.
    # This regression test keeps the project contract independent from invented confidence values.
    res = _client(lambda request: httpx.Response(200, json={
        "errorCode": 0,
        "errorMsg": "Success",
        "result": {"layoutParsingResults": [{"markdown": {"text": "Invoice text"}}]},
    })).process(_image())
    assert res.confidence is None


class _RapidResult:
    txts = ("COMMERCIAL INVOICE", "INV-001")
    scores = (0.9, 1.0)


class _RapidEngine:
    def __init__(self):
        self.calls = 0
    def __call__(self, image):
        self.calls += 1
        return _RapidResult()


def test_rapidocr_3_adapter_uses_result_attributes_and_reuses_engine():
    engine = _RapidEngine()
    provider = RapidOcrProvider(engine=engine)
    first = provider.process(_image())
    second = provider.process(_image())
    assert first.text == "COMMERCIAL INVOICE\nINV-001"
    assert first.confidence == pytest.approx(0.95)
    assert second.text == first.text
    assert engine.calls == 2



def test_paddle_client_enforces_local_concurrency_bound():
    active = 0
    max_active = 0
    lock = threading.Lock()

    def handler(request):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.03)
            return httpx.Response(
                200,
                json={
                    "errorCode": 0,
                    "errorMsg": "Success",
                    "result": {
                        "layoutParsingResults": [
                            {"markdown": {"text": "COMMERCIAL INVOICE INV-001"}}
                        ]
                    },
                },
            )
        finally:
            with lock:
                active -= 1

    client = _client(handler, max_concurrency=1)
    errors = []

    def worker():
        try:
            client.process(_image())
        except Exception as exc:  # pragma: no cover - assertion aid
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert max_active == 1
