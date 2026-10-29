# TASK-006E — Invoice Extraction Service



Status: DONE  

Priority: P1  

Parent: TASK-006  

Developer: Codex — Main Developer  

Reviewer: Antigravity — Independent Technical Reviewer / QA  

Created: 2026-09-11  

Completed: 2026-10-29  

Merged PR: #5 (commit b6932c6)  

Dependencies: TASK-006B DONE, TASK-006C DONE, TASK-006D DONE  

Authoritative pre-task baseline: 435 passed / 0 failed / 0 skipped / 2 warnings  

Post-task baseline: 566 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)



---



## 1. OBJECTIVE



Compose the approved Invoice extraction components into the production application service without coupling external vendor AI dependencies, HTTP endpoints, or modifying SQLite schemas.



---



## 2. IN SCOPE



- Primary input document_id.

- Safely classified COMMERCIAL_INVOICE gate: dual-check with stored document metadata and live content re-classification.

- Non-mutating downstream parse/read path (parse_document_readonly), preventing status downgrade from CLASSIFIED / NEEDS_REVIEW to PARSED.

- TASK-005A visual safety gate: unusable or conflicting visual pages abort extraction with NEEDS_REVIEW and UNSAFE_VISUAL_DOCUMENT.

- Unsafe visual conflict strictly bypasses semantic fallback (call count to semantic provider is exactly 0).

- Assembly of deterministic headers (TASK-006B) and Excel item tables (TASK-006C) into canonical Invoice model.

- PDF item extraction unsupported policy: items list remains empty [], no guessed items fabricated, and explicit PDF_ITEMS_UNSUPPORTED review issue attached.

- Provider-neutral semantic fallback interface (SemanticInvoiceProvider, SemanticInvoiceRequest, SemanticInvoiceResponse).

- Strict role-labeled semantic grounding validation: candidates must match verified SemanticSource spans in raw value, coordinate/page, and exact typed representation.

- Conservative fill-only merge: semantic proposals cannot overwrite deterministically extracted values or bypass sticky review issues.

- Explicit safe re-extraction through TASK-006D policy with optimistic CAS (expected_active_extraction_id, expected_source_file_hash, expected_processing_status).

- Atomic source snapshot verification (expected_source_document) under writer lock preventing concurrent mutation races.

- Privacy-safe logging: zero customer data, file paths, or raw payload dumps in logs.

- Production composition factory: build_invoice_extraction_service.



---



## 3. OUT OF SCOPE



- Hosted / vendor AI provider SDK integration.

- TASK-009 semantic normalization.

- Cross-document matching or rules engine.

- Packing List or Bill of Lading extraction.

- HTTP API / FastAPI endpoints (deferred to TASK-006F / downstream).



---



## 4. KEY ACCEPTANCE



- [x] Unsafe visual document is never sent to semantic fallback (call count = 0).

- [x] Wrong semantic document / provenance / type triggers typed issue and review.

- [x] Semantic cannot overwrite deterministic accepted values or resolve conflicts.

- [x] Source file remains immutable.

- [x] No parser status downgrade during extraction (parse_document_readonly).

- [x] No SQL in application service.

- [x] Full regression stays green (566 passed, 2 warnings).



---



## 5. TEST EVIDENCE



### Full Test Suite (pytest)

- Pre-task baseline: 435 passed / 0 failed / 0 skipped / 2 warnings

- Implementation additions: 131 new tests

- Post-task regression: **566 passed, 0 failed, 0 skipped, 2 warnings** in 17.84s (Python 3.13.14, pytest 9.1.1)



### Independent Adversarial Probes (Antigravity QA)

14/14 independent probes PASSED across 6 test groups:

- **Group 1 (Non-mutating parsing & immutability):**

  - Probe 1.1: parse_document_readonly() leaves CLASSIFIED status untouched — PASS

  - Probe 1.2: extract_document() advances CLASSIFIED -> EXTRACTED atomically without PARSED downgrade — PASS

  - Probe 1.3: Uploaded source bytes remain strictly immutable — PASS

- **Group 2 (Classification gate & content verification):**

  - Probe 2.1: PACKING_LIST refused by classification gate despite filename containing \'invoice\' — PASS

  - Probe 2.2: Content re-check catches content mismatch and refuses without persistence — PASS

- **Group 3 (Visual / OCR safety gates & fallback bypass):**

  - Probe 3.1: Unresolved visual document bypasses semantic fallback (call count = 0) — PASS

  - Probe 3.2: Conflicting OCR/VLM resolution bypasses semantic fallback (call count = 0) — PASS

- **Group 4 (Semantic grounding, validation & fill-only merge):**

  - Probe 4.1: Adversarial semantic overwrite of deterministic value is strictly rejected — PASS

  - Probe 4.2: Fabricated ungrounded semantic field is strictly rejected — PASS

  - Probe 4.3: Valid independently grounded semantic fill succeeds for None field — PASS

- **Group 5 (Deterministic invoice assembly & PDF items policy):**

  - Probe 5.1: PDF item extraction unsupported policy enforced (no guessed items) — PASS

- **Group 6 (Persistence CAS, re-extraction & race protection):**

  - Probe 6.1: Re-extraction without expected_active_extraction_id refused without write — PASS

  - Probe 6.2: Stale expected_active_extraction_id refused without write — PASS

  - Probe 6.3: Source mutation detected and refused; prior active extraction intact — PASS



---



## 6. DELIVERABLES



- src/customs_ai/application/invoice_extraction.py — InvoiceExtractionService and build_invoice_extraction_service.

- src/customs_ai/application/invoice_models.py — Pydantic models for extraction outcomes and preflights.

- src/customs_ai/application/composition.py — Production service factory composition.

- src/customs_ai/application/parsing.py — parse_document_readonly() implementation.

- src/customs_ai/extraction/semantic.py — Role-labeled source extractor (_sources), semantic protocol, and merge_semantic.

- src/customs_ai/repositories/document_extractions.py — Atomic expected_source_document snapshot verification under writer lock.

- src/customs_ai/repositories/extraction_models.py — CAS models with expected_source_document.

- docs/decisions/ADR-002-invoice-extraction-service.md — Formal Architectural Decision Record.

- 	ests/unit/application/test_invoice_extraction_service.py — 58 application service tests.

- 	ests/unit/application/test_readonly_parsing.py — 21 non-mutating parsing tests.

- 	ests/unit/extraction/test_semantic.py — 52 semantic boundary and grounding tests.



---



## 7. DEFINITION OF DONE



- [x] Application extraction service implemented and orchestrated

- [x] Non-mutating parsing pipeline (parse_document_readonly) operational

- [x] Dual classification gate active and verified against misleading filenames

- [x] Visual safety gates enforce zero semantic fallback calls on unresolved/conflicted pages

- [x] Canonical invoice assembly merges deterministic headers and Excel items

- [x] PDF items unsupported policy enforced without heuristics

- [x] Semantic fallback strictly validated, role-grounded, and fill-only

- [x] Deterministic issues and conflicts remain sticky

- [x] SQLite CAS persistence verifies source document snapshot under writer lock

- [x] Full regression suite green (566 passed, 2 warnings)

- [x] 14/14 independent adversarial probes passed

- [x] Antigravity independent review: APPROVE

- [x] Project Leader approval: APPROVE

- [x] GitHub Pull Request #5 merged into main (commit b6932c6)



---



## 8. CLOSURE SUMMARY



- **Status**: CLOSED / DONE

- **Date**: 2026-10-29

- **Merged PR**: Pull Request #5 (commit b6932c6)

- **Developer**: Codex — Main Developer

- **Review Decision**: Antigravity — Independent Technical Reviewer / QA — APPROVE

- **Architectural Approval**: Project Leader — APPROVE

- **Baseline for TASK-006F**: 566 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1)

