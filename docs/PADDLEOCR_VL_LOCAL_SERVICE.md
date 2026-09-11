# PaddleOCR-VL 1.6 Local Service — TASK-005A

The main Windows application never calls a hosted AI service.

TASK-005A expects the official PaddleOCR-VL full-pipeline serving API on loopback only:

```text
http://127.0.0.1:9090/layout-parsing
```

## Recommended prototype path

Use WSL2 Ubuntu with a dedicated virtual environment. The official PaddleOCR-VL documentation verifies Python 3.9–3.13 for the manual installation path.

Inside WSL2:

```bash
python3 -m venv ~/.venvs/paddleocr-vl
source ~/.venvs/paddleocr-vl/bin/activate
```

Install one supported PaddlePaddle inference engine for your CUDA version. For example, the upstream documentation currently shows CUDA 12.6 as:

```bash
python -m pip install paddlepaddle-gpu==3.2.1 \
  -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
python -m pip install -U "paddleocr[doc-parser]"
```

Do not install both CPU and GPU PaddlePaddle in the same environment.

## Explicit model preparation

The official pipeline can download its models on first use. Do that deliberately during setup, before enabling TASK-005A in the main application.

Use a synthetic/local test image and run:

```bash
paddleocr doc_parser \
  --input /path/to/synthetic_scan.png \
  --pipeline_version v1.6 \
  --save_path ./model-preparation-output
```

Wait for all required models to finish downloading and verify the command succeeds.

After model preparation, disconnecting Internet access must not prevent normal inference with already cached assets. For a stricter production/offline deployment, use PaddleOCR's official offline Docker images and pin the image version instead of `latest`.

## Install serving plugin

```bash
paddlex --install serving
```

## Start the full PaddleOCR-VL service

```bash
paddlex --serve \
  --pipeline PaddleOCR-VL \
  --host 127.0.0.1 \
  --port 9090
```

This is the full PaddleOCR-VL pipeline service, not only the 0.9B VLM component.

## Smoke request

From WSL2/Linux:

```bash
python - <<'PY'
import base64
import json
import urllib.request

image_path = "/path/to/synthetic_scan.png"
with open(image_path, "rb") as f:
    payload = {
        "file": base64.b64encode(f.read()).decode("ascii"),
        "fileType": 1,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useLayoutDetection": True,
        "returnMarkdownImages": False,
        "visualize": False,
        "prettifyMarkdown": False,
    }

req = urllib.request.Request(
    "http://127.0.0.1:9090/layout-parsing",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as resp:
    data = json.load(resp)

assert data["errorCode"] == 0
pages = data["result"]["layoutParsingResults"]
assert pages
print("PaddleOCR-VL local smoke: OK")
PY
```

## Enable the main application

Set in the main Windows `.env` only after the local service is ready:

```text
VISION__ENABLED=true
VISION__VLM_LOCAL_ENDPOINT=http://127.0.0.1:9090/layout-parsing
```

The application config rejects LAN/public/non-loopback VLM endpoints.

## RapidOCR smoke on Windows

Install the optional vision group:

```powershell
python -m pip install -e ".[vision]"
rapidocr check
```

RapidOCR 3.9+ uses PP-OCRv6 small detection/recognition by default and runs locally through ONNX Runtime in this project.
