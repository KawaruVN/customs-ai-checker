# TASK-006F — Invoice Integration & Regression

Status: DONE  
Priority: P1  
Parent: TASK-006  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Created: 2026-09-11  
Completed: 2026-10-29  
Merged PR: #6 (commit `be6c7d9`)  
Dependencies: TASK-006A..TASK-006E DONE  
Authoritative pre-task baseline: 566 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 616 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

## Objective

Validate and document the complete TASK-006 Invoice Extraction epic.

## In scope

End-to-end production-path tests for:

- native-text PDF;
- Excel;
- safe ResolvedPdfDocument;
- unresolved visual review;
- canonical provenance;
- persistence/history;
- intentional re-extraction;
- semantic fake-provider boundary;
- privacy-safe failures;
- source-file immutability;
- production composition from document_id;
- full regression;
- implementation/test evidence in this TASK file (README and parent epic are reserved for formal closure).

## Out of scope

No new business features.

If integration exposes a defect in an approved child, fix the defect in the owning boundary without expanding TASK-006F into a second implementation task.

## Closure

TASK-006F may close only when the complete full-suite result is green and Project Leader confirms the parent TASK-006 epic is ready to close.

Baseline is the exact approved TASK-006E full-suite result.

## Pre-flight evidence

- Repository and required branch verified; HEAD `c2d3573fecb41c7b4aa5b081257bccf8aa5cbe41` equals local `main` and `origin/main` at start.
- TASK-006E merge PR #5 (`b6932c6`) and closure commit `c2d3573` are ancestors; `tasks/done/TASK-006E-invoice-extraction-service.md` exists with DONE status.
- Working tree initially clean; no staged, unstaged or untracked changes.
- Baseline independently run before editing: 566 collected, 566 passed, 0 failed, 0 skipped, 2 warnings in 15.36s (Python 3.13.14, pytest 9.1.1).
- README and parent TASK-006 epic will remain untouched. No task closure or Git publication is authorized.

## Executed production path

Synthetic fixture bytes are uploaded through the real IngestionService into
isolated storage, producing a real SourceDocument. Tests then call
`build_classification_service().classify_document(document_id)` followed by
`build_invoice_extraction_service().extract_document(document_id)` and retrieve
the committed extraction using fresh DocumentExtractionRepository instances.
The real parsers, classification, 006B/C extractors, 006D codecs/transactions and
006E orchestration remain in use.

Visual tests replace only provider/renderer I/O and exercise real 005A text-quality
and reconciliation logic. They verify one rendering and one invocation of each
visual provider per visual page in each stage, and zero calls for native pages.
Classification and extraction are separate stages with no cross-stage OCR cache,
as already documented in ADR-002.

## Integration matrix and test ownership

| Handoff group | Evidence |
|---|---|
| A — Native PDF | Two-page real PDF: ingestion/classification/extraction, exact raw/date/Decimal and page 1/page 2 provenance, zero render/OCR calls, persisted PDF_ITEMS_UNSUPPORTED with empty items. |
| B — XLSX/XLS | Real parsers, shifted rows/columns/later sheet, canonical party separation, zero/leading-zero identifiers and exact decimals; formulas, hidden data, competing tables, ambiguous numbers and incomplete rows remain unresolved/reviewable. |
| C — Safe visual PDF | Real 005A reconciliation with controlled local provider/renderer outputs; safe verified text reaches deterministic extraction once per stage and survives SQLite round-trip. |
| D — Unsafe visual PDF | Disabled/failed providers, low confidence, numeric disagreement, mixed pages and malformed metadata return review; no trusted headers or fabricated items, semantic call count exactly zero. |
| E — Semantic boundary | Fake provider only: strict document/path/provenance/type/raw evidence checks, immutable deterministic values, sticky conflicts, exception/malformed output sanitization and explicit grounded missing-field fill. |
| F — Persistence/history | First activation, explicit replacement, stale active/hash/status refusals, writer-lock source races, FAILED retaining prior active, latest-vs-active semantics and BEFORE/AFTER metadata rollback verified through committed repository reads. |
| G — Immutability/privacy | Uploaded bytes/hash checked across processing; path escape refusal; routine logs exclude synthetic invoice values, paths and private provider/DB exception markers. |
| H — Production composition | Actual factories throughout; isolated fresh-process import/default construction performs no network calls, loads no remote SDK or OCR engine and creates no runtime database/upload directory. AST inspection finds no application-layer SQL execution calls. |

New files:

- `tests/integration/conftest.py`: synthetic PDF/XLSX/XLS generation and real ingestion/factory helpers; no duplicate business extraction implementation.
- `tests/integration/test_invoice_native_excel.py`: 11 cases.
- `tests/integration/test_invoice_visual_safety.py`: 17 cases, including metadata regression tests.
- `tests/integration/test_invoice_semantic_history.py`: 22 cases.

The valid semantic-fill test deliberately simulates one optional deterministic
header miss at the extractor seam, while retaining the real parsing,
classification, local grounding, canonical validation and persistence chain.
Approved deterministic extraction ordinarily already fills these explicit labels;
the test does not claim new free-form semantic coverage.

## Demonstrated defect and minimal fix

Owner: TASK-006E, InvoiceExtractionService._safe_pdf. Severity: MEDIUM metadata
integrity/safety gap; no source corruption or false EXTRACTED PDF was established
(PDF items already require review).

Before the fix, a real 005A result mutated to an inconsistent `file_type`,
out-of-range/duplicate/missing `visual_pages`, or contradictory
`vision_fallback_recommended=True` still reached trusted header extraction and
semantic fallback instead of abstaining. The gate checked document/page IDs and
review flags but did not validate this related bookkeeping.

Failing integration evidence before editing production: the parameterized
`test_inconsistent_resolved_metadata_fails_closed_after_real_reconciliation`
run had 9 selected cases, 5 failed, 4 passed, 8 deselected, 0 skipped/warnings in
1.00s. Assertions expected no trusted headers and zero semantic calls; all five
malformed variants instead published invoice number 0000789.

The only production change adds five lines to `_safe_pdf`: require matching PDF
file type, no unresolved fallback recommendation, and a unique visual-page list
equal to the actual non-native page set. No canonical schema, database migration,
new extraction feature or approved status/history policy changed. After the fix,
all 17 visual integration cases pass (1.31s), including the five regressions and
valid native/safe-visual cases.

## Final measured validation

Environment: Windows, Python 3.13.14, pytest 9.1.1. All execution uses
`python -B -m pytest`, `-p no:cacheprovider` and a unique explicit `--basetemp`
outside the repository. Windows asyncio ingestion and TestClient tests run in the
local execution environment; sandbox attempts that stalled at asyncio startup
were interrupted and are not counted as passing runs. No production database or
customer documents were used.

| Scope | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-implementation full baseline | 566 | 566 | 0 | 0 | 2 | 15.36s |
| All three new integration files, including metadata regressions | 50 | 50 | 0 | 0 | 0 | 8.15s |
| Relevant existing unit suites: application, extraction, repositories, vision | 435 | 435 | 0 | 0 | 0 | 14.75s |
| Full collection `--collect-only -q` | 616 | — | — | — | 2 | 1.26s |
| Full regression `-v` | 616 | 616 | 0 | 0 | 2 | 24.34s |

New integration command scope:

```text
python -B -m pytest tests/integration/test_invoice_native_excel.py tests/integration/test_invoice_visual_safety.py tests/integration/test_invoice_semantic_history.py -v
```

Relevant unit command scope:

```text
python -B -m pytest tests/unit/application tests/unit/extraction tests/unit/repositories tests/unit/vision -q
```

Both were executed with the cache/temporary-directory options above. The full
suite retains only the existing Starlette/httpx and AnyIO BlockingPortal
deprecation warnings. No pre-existing test assertions were weakened or removed.

## Known limitations and review focus

- Controlled local visual outputs verify integration and safety contracts; no
  installed-model OCR accuracy or actual customer documents are evaluated.
- PDF item recognition remains unsupported with an explicit review issue.
- No cross-stage OCR cache, endpoint, UI, normalization, matching or business rule
  was added. The new missing-header fill test uses the one explicit seam above.
- Existing ADR-001/002 limitations remain, including hash checks not locking source
  files against arbitrary external writes after the last check.
- Antigravity should mutate resolved metadata after real reconciliation, verify
  no semantic calls for mixed/unsafe pages, challenge valid-vs-fabricated fills,
  inject writer-lock metadata races and transaction failures, and independently
  confirm source hashes and log privacy.

## Independent QA verification — 2026-10-29

Antigravity independent technical review: **APPROVE**.

### 1. Test Inventory Classification (50 New Tests)
- **Category A (True End-to-End Application Integration):** 21 tests (42%)
- **Category B (Cross-Module Integration):** 29 tests (58%)
- **Category C (Unit / Mock-based):** 0 tests (0%)
- **Category D (Duplicated / Low-value):** 0 tests (0%)

All tests exercise the real `IngestionService`, real `SourceDocumentRepository`, real technical parsers (`pypdf`, `openpyxl`, `xlrd`), real deterministic extractors, and real `DocumentExtractionRepository` SQLite transactions under `BEGIN IMMEDIATE`.

### 2. Independent Adversarial Probes
14/14 independent probes PASSED across 14 failure modes:
- Probe 1: Production factory wiring & complete isolated flow — PASS
- Probe 2: Native PDF completeness invariant & PDF_ITEMS_UNSUPPORTED review flag — PASS
- Probe 3: Excel Decimal precision, zero, negative & DB roundtrip preservation — PASS
- Probe 4: Excel competing item-table ambiguity abstention — PASS
- Probe 5: Visual safety gate on mixed PDF with zero semantic calls — PASS
- Probe 6: Visual safety gate on vision_fallback_recommended metadata flag — PASS
- Probe 7: Semantic cannot unblock sticky deterministic conflicts — PASS
- Probe 8: Semantic ungrounded fabrication attempt strictly rejected — PASS
- Probe 9: Non-mutating parsing preserves CLASSIFIED status — PASS
- Probe 10: Uploaded source bytes strictly immutable across pipeline — PASS
- Probe 11: Normal logs strictly sanitize customer data and exceptions — PASS
- Probe 12: Atomic transaction rollback on repository write failure — PASS
- Probe 13: CAS re-extraction guards reject stale ID and mismatched hash — PASS
- Probe 14: Cross-document provenance contamination strictly rejected — PASS

### 3. Full Regression Suite
- **616 passed, 0 failed, 0 skipped, 2 warnings** in 26.63s (Python 3.13.14, pytest 9.1.1).

---

## Definition of Done

- [x] End-to-end native-text PDF integration verified
- [x] Excel XLSX and XLS integration verified
- [x] Safe ResolvedPdfDocument visual integration verified
- [x] Unresolved visual review & zero semantic calls verified
- [x] Visual metadata integrity regression fixed in `_resolve_pdf`
- [x] Canonical provenance and persistence round-trip verified
- [x] Persistence history & atomic rollback verified
- [x] Intentional CAS re-extraction guards verified
- [x] Semantic fake-provider boundary & sticky conflicts verified
- [x] Source-file immutability and privacy in logs verified
- [x] Production composition from document_id verified
- [x] 50 new integration tests added (21 True E2E, 29 Cross-Module)
- [x] Full regression suite green (616 passed, 2 warnings)
- [x] 14/14 independent adversarial probes passed
- [x] Antigravity independent review: APPROVE
- [x] Project Leader approval: APPROVE
- [x] GitHub Pull Request #6 merged into main (commit `be6c7d9`)

---

## Closure summary

- **Status**: CLOSED / DONE
- **Date**: 2026-10-29
- **Merged PR**: Pull Request #6 (commit `be6c7d9`)
- **Developer**: Codex — Main Developer
- **Review Decision**: Antigravity — Independent Technical Reviewer / QA — APPROVE
- **Architectural Approval**: Project Leader — APPROVE
- **Authoritative Baseline after TASK-006F**: 616 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1)

