# TASK-005A — Scanned PDF Local Document Vision + OCR Verification

Status: IN_PROGRESS
Priority: P1
Owner: Gemini #1 — Main Developer
Reviewer: Gemini #2 — Reviewer / QA
Created: 2026-09-11
Updated: 2026-09-11
Target Version: V1
Dependencies: TASK-001..TASK-005 DONE
Related ADR: None

---

## 1. OBJECTIVE

Add an accuracy-first, local-only visual document resolution layer between TASK-004 parsing and downstream classification/extraction.

The project deliberately prioritizes correctness over raw speed for scanned pages.

Production strategy:

```text
TIER 0 — Native PDF text
pypdf
↓
usable?
├─ YES → preserve native text; no visual model needed
└─ NO  → visual page path

VISUAL PAGE PATH — ACCURACY FIRST
PaddleOCR-VL 1.6
↓
document text + layout/structure
↓
RapidOCR verification / literal OCR
↓
reconcile evidence
├─ sufficiently consistent → resolved page
└─ materially conflicting / still unusable → NEEDS_REVIEW
```

No external AI/API call is allowed in TASK-005A.

---

## 2. DESIGN PRINCIPLE

For clean digital PDFs, native text is the most faithful and cheapest source and remains Tier 0.

For scanned / image-only / unusable-text pages:

- **PaddleOCR-VL 1.6 is the primary visual document parser** because the project values layout/table/document understanding.
- **RapidOCR is the independent literal-text verifier and resilience fallback**, not the primary semantic parser.

This is intentionally different from an OCR-first pipeline.

The project must never treat a generative/document-VLM output as unquestionable ground truth for critical literal values.

---

## 3. WHY BOTH PROVIDERS ARE KEPT

PaddleOCR-VL is useful for:
- reading-order understanding;
- complex page layout;
- tables;
- visually structured documents;
- difficult scans.

RapidOCR is useful for:
- literal character recognition;
- independent cross-checking;
- fast fallback if the local VLM is unavailable;
- later verification of high-risk numeric/string fields.

Therefore the architecture uses:

```text
PaddleOCR-VL = primary visual understanding
RapidOCR     = independent verification / fallback
```

Do not remove either boundary.

---

## 4. SCANNED PAGE POLICY

For every PDF page:

### A. Native text is usable
Return:

```text
source = TEXT_LAYER
```

Do not call PaddleOCR-VL.
Do not call RapidOCR.

### B. Native text is unusable

Default project mode:

```text
accuracy_mode = true
```

Then:

1. render the page locally in memory;
2. run PaddleOCR-VL 1.6;
3. run RapidOCR on the same rendered page;
4. normalize both outputs only for comparison;
5. reconcile them conservatively;
6. retain provider-specific evidence/provenance.

If one provider is unavailable:
- use the other if its result passes quality gates;
- record reduced verification strength;
- do not fabricate agreement.

If both fail or materially conflict:
- page is unresolved or requires review.

---

## 5. RECONCILIATION CONTRACT

Do not simply concatenate provider outputs.

Introduce a provider-neutral reconciliation result.

Conceptually:

```text
VisualAgreement:
- vlm_usable: bool
- ocr_usable: bool
- agreement_score: float | None
- material_conflict: bool
- verification_level:
    - UNVERIFIED
    - SINGLE_PROVIDER
    - CROSS_VERIFIED
    - CONFLICT
```

Comparison should be deterministic and lightweight.

Possible signals:
- normalized text overlap;
- presence/absence of strong document clues;
- exact numeric token agreement;
- exact identifier-like token agreement;
- disagreement on short critical-looking tokens.

Do NOT attempt TASK-006 business extraction inside TASK-005A.

---

## 6. CRITICAL TOKEN SAFETY

Even before structured Invoice extraction exists, TASK-005A may compare literal token classes generically:

- numbers;
- decimal values;
- percentages;
- dates;
- identifier-like alphanumeric strings;
- currency-like tokens.

It MUST NOT label them as invoice number, amount, HS code, etc. yet.

If PaddleOCR-VL and RapidOCR materially disagree on many literal numeric/identifier tokens:

```text
requires_review = true
```

This is especially important because document VLMs can normalize, omit or infer content.

---

## 7. PROVIDER-NEUTRAL MODELS

Conceptually:

```text
TextResolutionSource:
- TEXT_LAYER
- DOCUMENT_VISION_LOCAL
- OCR_LOCAL
- CROSS_VERIFIED_VISUAL
- UNRESOLVED
```

```text
ProviderTextResult:
- provider
- text
- confidence: float | None
- usable: bool
- structured_content: object | string | None
```

```text
ResolvedPdfPage:
- page
- text
- source
- confidence: float | None
- verification_level
- agreement_score: float | None
- requires_review
- provider_results[]
```

```text
ResolvedPdfDocument:
- document_id
- page_count
- pages[]
- visual_pages[]
- unresolved_pages[]
- requires_review
- vision_fallback_recommended
```

Exact names may vary if coherent and strict.

Never erase the fact that text came from a visual model versus literal OCR.

---

## 8. TEXT SOURCE PRIORITY

When choosing the resolved text presented to TASK-005 classification:

1. usable native text layer;
2. cross-verified visual result;
3. PaddleOCR-VL result if usable and no material contradiction exists;
4. RapidOCR result if PaddleOCR-VL unavailable/unusable and RapidOCR passes quality gates;
5. unresolved.

For a material provider conflict:

```text
classification must not receive a fabricated merged text
```

Prefer unresolved/review behavior.

---

## 9. PADDLEOCR-VL 1.6 PROVIDER

Add a project-owned `LocalDocumentVisionProvider` interface.

PaddleOCR-VL implementation requirements:
- local only;
- provider isolated;
- lazy/reused initialization;
- explicit local model assets;
- no silent first-document download;
- no content logging;
- no absolute model-path leakage;
- bounded page/resource limits;
- CPU/GPU backend details isolated from orchestration;
- no downstream classifier imports Paddle-specific objects.

Do not make vLLM/FastDeploy mandatory unless independently justified.

---

## 10. RAPIDOCR PROVIDER

Add a project-owned `LocalOcrProvider` interface.

RapidOCR implementation requirements:
- local only;
- ONNX/runtime isolated;
- reused initialization;
- line/text conversion provider-neutral;
- confidence bounded `[0,1]`;
- no content logging;
- no source mutation.

In default accuracy mode, RapidOCR verifies scanned pages even when PaddleOCR-VL produces a usable result.

A future performance mode may make verification conditional, but that is not the default V1 behavior.

---

## 11. PDF RENDERING

Preferred local renderer:
`pypdfium2`.

Requirements:
- render only visual pages;
- one render can be reused by both PaddleOCR-VL and RapidOCR;
- no duplicate page rendering for the two providers;
- image remains in memory by default;
- bounded DPI/pixel size;
- source PDF unchanged;
- deterministic errors;
- external page numbering remains 1-based.

---

## 12. PAGE TEXT QUALITY

Implement a deterministic multilingual-safe quality evaluator.

Consider:
- non-whitespace character count;
- meaningful Unicode letter/digit/CJK count;
- printable ratio;
- control/replacement-character ratio.

Must work with:
- English;
- Vietnamese;
- Chinese.

Must not:
- strip Vietnamese diacritics;
- require ASCII;
- require English words;
- infer customs semantics.

---

## 13. CLASSIFICATION HANDOFF

TASK-005 classifier remains deterministic and unchanged in clue semantics.

Required flows:

```text
scanned Commercial Invoice
→ PaddleOCR-VL sees COMMERCIAL INVOICE
→ RapidOCR confirms literal clue
→ resolved text
→ TASK-005
→ COMMERCIAL_INVOICE
```

```text
PaddleOCR-VL says COMMERCIAL INVOICE
RapidOCR says PACKING LIST
→ material conflict
→ no forced classification
→ UNKNOWN / NEEDS_REVIEW
```

```text
PaddleOCR-VL unavailable
RapidOCR confidently reads COMMERCIAL INVOICE
→ classifier may proceed
→ provenance shows single-provider verification
```

---

## 14. EXCEL

XLS/XLSX:
- no PaddleOCR-VL;
- no RapidOCR;
- existing TASK-004 parse path unchanged.

---

## 15. EXTERNAL NETWORK POLICY

Normal document processing:

```text
External network calls = 0
Paid API calls = 0
```

Do not implement hosted:
- OpenAI;
- Gemini;
- SiliconFlow;
- Novita;
- remote Paddle API;
- other vendor API.

A future external vision provider may be added in a separate approved task.

---

## 16. MODEL ASSET POLICY

Model preparation is an explicit setup step.

A document request must never trigger uncontrolled model downloads.

If assets are missing:

```text
DOCUMENT_VISION_UNAVAILABLE
```

RapidOCR may still be used if available.

Do not hide compatibility failures.

---

## 17. ERRORS

At minimum:

```text
OCR_ENGINE_UNAVAILABLE
OCR_FAILED

DOCUMENT_VISION_UNAVAILABLE
DOCUMENT_VISION_FAILED

PDF_RENDER_FAILED
VISUAL_RESULT_CONFLICT
VISUAL_PAGE_LIMIT_EXCEEDED
TEXT_RESOLUTION_FAILED
```

Exposed errors/logs must not contain:
- document text;
- page image bytes;
- absolute source path;
- local model path;
- credentials.

A content disagreement is normally a review condition, not necessarily a process crash.

---

## 18. RESOURCE LIMITS

Config must include validated limits conceptually covering:
- render DPI;
- max render pixels;
- max visual pages/document;
- VLM max concurrency;
- OCR/VLM enabled flags;
- text-quality thresholds;
- provider acceptance thresholds;
- reconciliation/material-conflict threshold.

For the user's workstation-oriented V1:
- conservative VLM concurrency is preferred;
- accuracy is prioritized over throughput.

---

## 19. DEPENDENCY POLICY

Preferred direction:
- pypdfium2;
- RapidOCR;
- ONNX Runtime;
- PaddleOCR 3.x / PaddleOCR-VL 1.6.

Gemini #1 must verify actual current Windows/Python 3.13 compatibility before exact version pins.

Prefer optional dependency groups where coherent.

Do not introduce merely for this task:
- PyTorch;
- TensorFlow;
- EasyOCR;
- LangChain;
- LlamaIndex;
- OCRmyPDF;
- system Tesseract.

If local PaddleOCR-VL dependencies cannot be made compatible without destabilizing the main Python 3.13 application:
- preserve the provider interface;
- isolate local inference cleanly;
- report the real blocker;
- do not fake support.

---

## 20. TEST REQUIREMENTS

Authoritative pre-task local baseline:

```text
Windows
Python 3.13.14
pytest 9.1.1
139 passed
0 failed
0 skipped
2 pre-existing warnings
```

Final suite must exceed 139 and pass.

Tests must use fakes/mocks for provider engines.
Pytest must not download real models or use network.

### Native text
- clean PDF calls neither provider;
- native text preserved unchanged.

### Visual page
- scan renders once;
- PaddleOCR-VL called;
- RapidOCR called in default accuracy mode;
- same rendered page reused.

### Agreement
- both providers agree → CROSS_VERIFIED;
- agreement score bounded;
- strong document clue agreement works;
- numeric/identifier agreement works.

### Conflict
- conflicting document clue → requires_review;
- material numeric/identifier conflict → requires_review;
- no concatenated/fabricated text;
- classification does not force type.

### Provider resilience
- VLM unavailable + OCR good → usable single-provider result;
- OCR unavailable + VLM good → usable single-provider result;
- both unavailable → unresolved;
- provider exception deterministic;
- provider initialized/reused.

### Mixed PDF
- visual processing only on bad page;
- page order preserved;
- provenance preserved.

### Excel
- no visual provider calls.

### Security/resource
- source hash unchanged;
- page/DPI/pixel limits;
- errors do not leak paths/content/model paths.

### Integration
- scan + provider agreement → COMMERCIAL_INVOICE;
- VLM difficult-layout result + OCR verification → known type;
- provider disagreement → UNKNOWN/NEEDS_REVIEW;
- text-PDF regression;
- path protections preserved.

---

## 21. SMOKE / BENCHMARK

Developer must provide explicit local setup/smoke instructions for:
- RapidOCR;
- PaddleOCR-VL.

Model preparation/download must be separate from document processing.

Provide a mini benchmark that reports only safe metrics:

```text
page
native/visual
vlm elapsed ms
ocr elapsed ms
agreement score
verification level
requires review
```

Never print document text.

---

## 22. ACCEPTANCE CRITERIA

AC-01 Clean native PDF invokes neither visual provider.  
AC-02 Visual page uses PaddleOCR-VL as primary visual parser.  
AC-03 Default accuracy mode also uses RapidOCR as independent verifier.  
AC-04 One page render is reused for both providers.  
AC-05 Provider agreement produces cross-verified result.  
AC-06 Material conflict produces review state, not forced merge.  
AC-07 Numeric/identifier conflict can trigger review without business-field semantics.  
AC-08 VLM unavailable can fall back to RapidOCR.  
AC-09 OCR unavailable can retain good VLM result with single-provider provenance.  
AC-10 both fail → unresolved.  
AC-11 mixed PDF operates per page.  
AC-12 classification consumes resolved text only when safe.  
AC-13 clue/scoring semantics from TASK-005 unchanged.  
AC-14 Excel bypasses both providers.  
AC-15 source immutable.  
AC-16 no automatic network/API call.  
AC-17 no silent model download during document processing.  
AC-18 resource limits exist.  
AC-19 provider-specific details remain behind boundaries.  
AC-20 full local suite passes beyond 139 baseline.

---

## 23. OUT OF SCOPE

- Invoice/Packing/Bill structured business extraction;
- normalization;
- matching;
- rules;
- HS/legal;
- customer templates;
- JPG/PNG upload OCR;
- hosted AI;
- UI;
- training/fine-tuning.

---

## 24. DEFINITION OF DONE

- [ ] TASK-005 DONE
- [ ] per-page quality evaluator
- [ ] reusable in-memory renderer
- [ ] PaddleOCR-VL provider boundary + implementation
- [ ] RapidOCR provider boundary + implementation
- [ ] accuracy-mode dual-provider visual path
- [ ] deterministic reconciliation
- [ ] conflict/review behavior
- [ ] mixed PDF
- [ ] provenance
- [ ] resource limits
- [ ] no silent model download
- [ ] classification handoff
- [ ] Excel bypass
- [ ] source immutable
- [ ] README/smoke/benchmark docs
- [ ] all new tests pass
- [ ] all prior 139 tests pass
- [ ] Gemini #2 APPROVE
- [ ] Project Leader APPROVE
- [ ] ready for tasks/done/

---

## 25. PROJECT LEADER DECISION

Pending.
