# TASK-005A — Scanned PDF Local Document Vision + OCR Verification

Status: DONE
Priority: P1
Owner: Gemini #1 — Main Developer
Reviewer: Gemini #2 — Reviewer / QA
Updated: 2026-09-11
Target Version: V1
Dependencies: TASK-001..TASK-005 DONE

## Objective

Implement an accuracy-first, local-only page-resolution layer between TASK-004 parsing and downstream classification.

Production path:

```text
Usable native PDF text
→ preserve pypdf text
→ no OCR/VLM

Unusable/scanned PDF page
→ render once in memory
→ PaddleOCR-VL 1.6 (primary document vision)
→ RapidOCR 3.x (independent literal OCR verifier)
→ central quality gate
→ typed high-signal reconciliation
→ resolved text OR NEEDS_REVIEW
```

No hosted AI/API call is allowed in TASK-005A.

## Mandatory architectural decisions

### Native text

Per-page decision only.

TASK-004 document-level `needs_ocr` is insufficient for mixed PDFs.

Usable native text:
- preserved unchanged;
- source = TEXT_LAYER;
- no rendering;
- no VLM;
- no OCR.

### PaddleOCR-VL

Use actual PaddleOCR-VL 1.6 document parsing.

Do not substitute standard `PaddleOCR(...)`.

Current implementation direction:
- main Customs AI application remains Windows / Python 3.13;
- PaddleOCR-VL runs in an isolated local WSL2/Linux or Docker service;
- main application communicates only over loopback.

Local service must use the current official `PaddleOCRVL` API and `pipeline_version="v1.6"` or verified equivalent.

### RapidOCR

Use the current `rapidocr` 3.x package.

Do not use:
- `rapidocr-onnxruntime`;
- `from rapidocr_onnxruntime import RapidOCR`.

Adapter must follow the actual current RapidOCR 3.x result API.

### Local-only security

The VLM endpoint must allow only:
- `127.0.0.1`
- `localhost`
- `::1`

Reject:
- LAN IPs;
- public IPs;
- arbitrary DNS hosts.

A configuration change must not be able to send customer page images outside the local machine.

### Model assets

Normal document processing must never trigger uncontrolled model downloads.

For V1, model preparation is an explicit setup operation performed before the main application enables vision. The approved local serving path may use PaddleOCR/PaddleX's prepared local cache, or a custom local pipeline configuration with explicit `model_dir` values for stricter offline deployment.

Before `VISION__ENABLED=true`:
- prepare all required PaddleOCR-VL 1.6 assets deliberately;
- start the local full-pipeline service;
- complete a synthetic local smoke request successfully;
- verify normal inference still works with external network access unavailable.

Missing/unprepared assets must leave the local visual provider unavailable; they must not be fetched as a side effect of a customs-document request.

## Raw provider contract

Provider outputs are raw observations.

Conceptually:

```text
ProviderTextResult
- provider
- text
- confidence: float | None
- optional provider-neutral structured content
```

Do not let provider objects self-certify trust with `usable=True`.

Trust is computed centrally:

```text
vlm_usable = evaluator.evaluate_provider_result(...)
ocr_usable = evaluator.evaluate_provider_result(...)
```

## Text quality gate

Shared text statistics must support:
- Vietnamese;
- Chinese;
- English.

Configurable checks:
- minimum meaningful-character count;
- maximum control/NUL ratio;
- maximum replacement-character ratio;
- minimum meaningful-character ratio;
- confidence threshold where confidence exists.

Symbol-only garbage must not pass.

## Reconciliation

Use separate token classes.

### Dates

Extract recognized date-like tokens first.

Normalize only safely recognized formats.

Do not infer ambiguous date semantics.

### Numbers

Support at minimum:
- `12500`
- `12500.50`
- `12,500.50`

Handle punctuation conservatively.

Equivalent, safely-normalizable forms must not conflict only because formatting differs.

### Identifiers

Identifier-like tokens require signals such as:
- at least one digit; or
- meaningful alphanumeric separator structure.

Examples:
- `INV-001`
- `ABC123`
- `CONT/2026/01`

Ordinary words such as:
- `Invoice`
- `Amount`
- `Container`

must not automatically become identifiers.

Case-normalize identifiers for comparison.

### Conflict policy

If both accepted providers materially disagree on high-signal tokens:
- source = UNRESOLVED;
- verification = CONFLICT;
- requires_review = true;
- do not merge text;
- do not force classification.

Soft text overlap may be a secondary signal only.

## PDF rendering

Preferred renderer:
`pypdfium2`

Requirements:
- render only pages that need visual processing;
- one render reused by both VLM and OCR;
- in-memory by default;
- bounded DPI;
- bounded max pixels;
- bounded visual pages/document;
- guaranteed resource cleanup;
- source file immutable.

Dedicated error:
`PDF_RENDER_LIMIT_EXCEEDED`

## Local PaddleOCR-VL service

The approved V1 serving implementation is the official PaddleX/PaddleOCR full-pipeline serving path, not a project-maintained imitation server.

Reference startup:

```text
paddlex --serve --pipeline PaddleOCR-VL --host 127.0.0.1 --port 9090
```

Main inference endpoint:

```text
POST /layout-parsing
```

This service must execute the complete PaddleOCR-VL pipeline (layout analysis + VLM recognition), corresponding to PaddleOCR-VL 1.6/current verified v1.6 default or an explicitly pinned v1.6 pipeline configuration.

Requirements:
- local only;
- loopback binding;
- model preparation completed before enabling main-app vision;
- official request/response contract validated by the main-app client;
- bounded response size in the main client;
- deterministic unavailable vs failed behavior;
- safe logging;
- project-side local inference concurrency bounded conservatively (default `1`) for workstation hardware.

A custom `/health` or `/v1/vision` wrapper is not required for V1 because the project consumes the official `/layout-parsing` contract directly. Readiness is established operationally by successful service startup plus a synthetic local smoke request before vision is enabled.

## Main-app VLM client

Requirements:
- loopback-only validated `/layout-parsing` endpoint;
- short bounded timeouts;
- bounded local inference concurrency;
- strict response validation;
- malformed JSON handling;
- confidence range validation;
- deterministic unavailable vs inference-failed errors;
- no raw remote/local exception text in logs.

Pytest must mock HTTP transport and must not open a real socket.

## Classification handoff

TASK-005 clue/scoring semantics remain unchanged.

Required behavior:

```text
safe resolved scanned Invoice
→ deterministic TASK-005 classifier
→ COMMERCIAL_INVOICE
```

```text
provider conflict
→ no fabricated text
→ UNKNOWN / NEEDS_REVIEW
```

Excel bypasses visual processing.

## Production composition

Provide a real application composition/factory path that wires:
- repository;
- parsing service;
- PaddleOCR-VL client;
- RapidOCR provider;
- visual resolution service;
- deterministic classifier;
- classification service.

Vision-disabled mode must not initialize visual providers.

Importing the app must not download/load models.

## Privacy and logging

Never log:
- OCR/VLM full text;
- page image bytes;
- absolute source paths;
- local model paths;
- credentials;
- raw provider exception strings;
- tracebacks from document/provider processing.

Safe logs only:
- document id;
- page;
- provider id;
- safe error code;
- timing/metrics without content.

## Required tests

Authoritative baseline before TASK-005A:

```text
Windows
Python 3.13.14
pytest 9.1.1
139 passed
0 failed
0 skipped
2 known warnings
```

Final suite must exceed 139 and pass.

Pytest:
- no Internet;
- no localhost socket;
- no GPU;
- no model download;
- no dependency-based skip.

Must cover:
- strict model/service contract;
- clean PDF bypass;
- mixed PDF;
- render once/reuse same image;
- Vietnamese/Chinese quality;
- NUL/control/replacement/symbol garbage rejection;
- low confidence rejection;
- `12500`;
- `1200.50`;
- safe thousands/decimal equivalence;
- date mismatch;
- identifier mismatch;
- case-only identifier equivalence;
- ordinary words not treated as identifiers;
- one numeric mismatch among otherwise identical text;
- VLM unavailable + OCR good;
- OCR unavailable + VLM good;
- both unavailable;
- loopback allowed;
- LAN/public/arbitrary DNS rejected;
- mocked HTTP client contract;
- malformed service response;
- 503 unavailable;
- render pixel limit;
- renderer cleanup;
- source hash unchanged;
- path traversal rejected;
- safe resolved scan → COMMERCIAL_INVOICE;
- conflict → UNKNOWN/NEEDS_REVIEW;
- production composition;
- vision-disabled composition does not initialize providers.

## Manual smoke evidence

Separate from pytest.

Provide exact commands for:
1. main Windows app install;
2. RapidOCR smoke on synthetic local image;
3. WSL2/Docker PaddleOCR-VL v1.6 environment;
4. explicit local model preparation;
5. service startup;
6. health check;
7. synthetic image inference;
8. main-client call against loopback service.

Do not claim smoke success unless actually executed.

## Acceptance criteria

- Actual full-pipeline PaddleOCR-VL 1.6 through the verified official PaddleX/PaddleOCR serving path, not standard `PaddleOCR(...)`.
- Actual RapidOCR 3.x, not rapidocr-onnxruntime.
- Native good text bypasses all visual processing.
- Mixed PDF works per page.
- Visual page rendered once and reused.
- Central provider-quality gate.
- High-signal conflicts force review.
- No unsafe merge.
- Loopback-only VLM transport.
- No model download is triggered by normal customs-document processing after the vision service is enabled.
- Source immutable.
- No customer content leakage in logs.
- Deterministic TASK-005 semantics unchanged.
- Full regression suite passes.
- Gemini #2 APPROVE.
- Project Leader APPROVE.

## Project Leader status

APPROVED — 2026-09-11.

- Authoritative local validation: 178 passed, 0 failed, 0 skipped, 2 warnings.
- Gemini #2 Review Round: PASS / APPROVE.
- Project Leader final decision: APPROVE / CLOSE TASK-005A.
- Manual RapidOCR and PaddleOCR-VL smoke remain a pre-production operational gate before enabling `VISION__ENABLED=true`; they do not block code-task closure.