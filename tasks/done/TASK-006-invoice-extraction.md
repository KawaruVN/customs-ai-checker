# TASK-006 — Invoice Extraction

Status: DONE  
Type: EPIC  
Priority: P1  
Owner: Project Leader  
Created: 2026-09-11  
Restructured: 2026-09-11  
Completed: 2026-10-29  
Dependencies: TASK-001..TASK-005A DONE  
Children: TASK-006A..TASK-006F (ALL DONE)  
Project Leader: APPROVE (Epic Closed: 2026-10-29)  
Final Merged PR: PR #6 (commit `be6c7d955a5c1ec947927f1e2616ca1489ea4c94`)  
Authoritative Baseline: 616 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)  
Adversarial Verification: 14/14 PASS (TASK-006F probes)

---

## 1. PURPOSE

Implement reliable Commercial Invoice extraction without coupling too many independent concerns into one development round.

The original TASK-006 scope combined:

- extraction primitives;
- numeric/date parsing;
- alias configuration;
- PDF/Excel header extraction;
- Excel item-table extraction;
- provenance/conflict handling;
- persistence/history;
- processing state transitions;
- re-extraction;
- semantic-provider boundaries;
- visual safety gates;
- composition;
- privacy logging;
- end-to-end regression.

That scope proved too large to review safely as one task. TASK-006 was therefore restructured as an epic and implemented through independent child tasks TASK-006A..TASK-006F.

This is a scope decomposition, not a change to the product objective.

---

## 2. GLOBAL OBJECTIVE

The completed epic supports:

```text
classified COMMERCIAL_INVOICE
→ safe technical content
→ canonical Invoice / InvoiceItem
→ exact source provenance
→ conservative review behavior
→ persisted extraction history
→ production application flow
```

Existing canonical models remain the source of truth:

```text
CanonicalField[T]
Party
Invoice
InvoiceItem
ValueOrigin
```

---

## 3. SUBTASKS SUMMARY & EXECUTION

### TASK-006A — Extraction Foundation (DONE — Merged via PR #1, commit `02a748e`)
- Built reusable extraction primitives: `ExtractionStatus`, typed `ExtractionIssue`, `ExtractionCandidate`.
- Established alias configuration `config/invoice_extraction.yaml` covering 17 approved header paths and 14 item paths (EN/VI/ZH) with strict party role separation.
- Strict lexical `Decimal` and `date` parsing with zero coercion of ambiguous formats.
- Pre-task baseline: 165 passed -> Post-task: 207 passed, 2 warnings.

### TASK-006B — Deterministic Invoice Headers (DONE — Merged via PR #2, commit `29c4da2`)
- Built deterministic header extraction for native PDF, safe Resolved PDF, and Excel.
- Implemented strict party role separation (seller, buyer, ship-to) per MASTER_SPEC.md:499.
- Opaque formula handling; formulas as values trigger `UNRESOLVED_FORMULA_FIELD` with `NEEDS_REVIEW`.
- Rejection of boolean/time cells for numeric/date fields; exact raw preservation and cell coordinates.
- Pre-task baseline: 207 passed -> Post-task: 249 passed, 2 warnings.

### TASK-006C — Invoice Item Tables (DONE — Merged via PR #3, commit `8bbb7f8`)
- Built conservative item-table extraction for generic Excel workbooks (`ParsedWorkbook`).
- Dual-constraint header validation (identity + numeric fields); grounded body product identity requirement.
- Exact summary boundary detection (`TOTAL`, `GRAND TOTAL`, `TỔNG CỘNG`, `合计`) and subtotal flags (`ITEM_SUBTOTAL_BOUNDARY`).
- Strict abstention on competing tables, compound columns, or ambiguous layouts (`MULTIPLE_ITEM_TABLES`).
- Pre-task baseline: 249 passed -> Post-task: 291 passed, 2 warnings; 42 independent probes verified.

### TASK-006D — Extraction Persistence & State (DONE — Merged via PR #4, commit `cd875b9`)
- Built SQLite persistence and state transitions in `document_extractions` table.
- Enforced single-active-record invariant at DB engine level via unique partial index (`WHERE is_active = 1`).
- Append-only monotonic attempt history (`attempt_number`); atomic transactions under `BEGIN IMMEDIATE`.
- Strict failure isolation: `FAILED` attempts remain inactive history and do not overwrite prior active records.
- Explicit re-extraction policy guarded by CAS (`expected_active_extraction_id`), hash match, and source status.
- Pre-task baseline: 291 passed -> Post-task: 435 passed, 2 warnings; 23 independent adversarial probes verified.

### TASK-006E — Invoice Extraction Service (DONE — Merged via PR #5, commit `b6932c6`)
- Composed the application extraction service orchestration (`InvoiceExtractionService`, `build_invoice_extraction_service`).
- Non-mutating downstream read/parse pipeline (`parse_document_readonly`), preventing status downgrade.
- Visual safety gate: unusable or conflicting visual pages terminate immediately with `NEEDS_REVIEW` and 0 semantic calls.
- Canonical invoice composition: deterministic headers and Excel item tables with typed candidates and full provenance.
- Fill-only semantic boundary rejecting overwrites, ungrounded proposals, or sticky deterministic conflicts.
- Pre-task baseline: 435 passed -> Post-task: 566 passed, 2 warnings; 14 independent adversarial probes verified.

### TASK-006F — Integration & Regression (DONE — Merged via PR #6, commit `be6c7d9`)
- Validated end-to-end integration connecting ingestion, classification, parsing, extraction, visual safety, semantic boundary, and persistence.
- Added 50 integration tests (21 True E2E, 29 Cross-Module) across native PDF, Excel (XLSX/XLS), visual safety, and semantic boundary.
- Verified CAS re-extraction guards, failure rollback, trigger rollbacks, and log privacy.
- Pre-task baseline: 566 passed -> Post-task: 616 passed, 2 warnings; 14 independent adversarial probes verified.

---

## 4. GLOBAL INVARIANTS

Every child task preserved:

1. No fabricated missing business values.
2. `raw_value` preserves the actual source representation used as evidence.
3. `origin=EXTRACTED` requires source grounding.
4. PDF page provenance and Excel sheet/cell provenance are preserved when available.
5. TASK-009 semantic normalization is not pulled into TASK-006.
6. No customer-specific hard-coded layouts.
7. No hosted AI/network dependency in the default implementation.
8. Unsafe visual/OCR conflict cannot be silently overridden by semantic extraction.
9. AI/provider outputs never bypass strict validation.
10. Source files remain immutable.
11. No customer content, absolute source paths, tax IDs, addresses, or provider raw payloads in normal logs.
12. Existing tests remain green after every approved child task.
13. Each child task is reviewed/approved independently before the next implementation task begins.

---

## 5. APPROVED LIMITATIONS & ARCHITECTURAL DECISIONS

The following known limitations and architectural constraints are explicitly approved for the V1 release of TASK-006:

1. **PDF Item Table Extraction Unsupported (V1 Scope Boundary)**:
   - Extraction of line-item tables from PDF documents (both native vector text and scanned/OCR pages) is intentionally unsupported in TASK-006.
   - For all PDF Commercial Invoices, header fields and parties are extracted, the item list is returned empty (`items=[]`), and `review_issues` includes `IssueCode.PDF_ITEMS_UNSUPPORTED`.
   - The document status is persisted as `NEEDS_REVIEW` (never false `EXTRACTED`), signaling the need for human operator review or manual entry for PDF line items.
   - Formal automated PDF table structure recognition is deferred to a future dedicated epic.

2. **Excel Line-Item Scope**:
   - Generic table detection applies to Excel files (`.xlsx`, `.xls`). It requires clear header labels (EN/VI/ZH aliases), numeric + identity columns, and valid body rows.
   - Workbooks with multiple competing item tables, compound header columns, or merged structures fail closed with `MULTIPLE_ITEM_TABLES` and `NEEDS_REVIEW`.

3. **Formula Cells**:
   - Formula text and expression strings are strictly opaque and never serve as extraction label headers.
   - Numeric cells containing uncalculated or dynamic formulas raise `UNRESOLVED_ITEM_FORMULA` with `NEEDS_REVIEW`, preserving the raw formula string in candidate provenance.

4. **Visual OCR & Semantic Boundary**:
   - Local OCR / visual fallback (TASK-005A) is restricted to page text reconciliation and header detection.
   - Discrepancies between OCR engines result in immediate `NEEDS_REVIEW` with zero semantic LLM calls.
   - The semantic provider operates strictly in fill-only mode for missing optional headers; it cannot override deterministic values or resolve deterministic conflicts.

5. **Storage & Re-extraction**:
   - Re-extraction requires an explicit CAS guard (`expected_active_extraction_id`), active document status, and matching SHA-256 source hash under `BEGIN IMMEDIATE`.
   - `FAILED` extractions are stored as inactive history (`is_active = 0`) to preserve audit trails without corrupting prior valid extractions.

---

## 6. EPIC DEFINITION OF DONE

TASK-006 is DONE:

- [x] TASK-006A DONE (Extraction Foundation)
- [x] TASK-006B DONE (Deterministic Invoice Headers)
- [x] TASK-006C DONE (Invoice Item Tables)
- [x] TASK-006D DONE (Extraction Persistence & State)
- [x] TASK-006E DONE (Invoice Extraction Service)
- [x] TASK-006F DONE (Integration & Regression)
- [x] final Invoice extraction flow passes full regression (616 passed, 0 failed, 0 skipped, 2 warnings)
- [x] no unresolved CRITICAL/HIGH issue
- [x] Project Leader closes the epic

---

## 7. PROJECT LEADER DECISIONS & CLOSURE

### 2026-09-11 — Scope Decomposition
- Original monolithic TASK-006 implementation stopped before any rejected implementation was applied.
- Reason: scope coupling reduced review reliability. Decomposed into TASK-006A..TASK-006F.

### 2026-10-29 — Epic Acceptance & Closure
- **Epic Status**: DONE
- **Date**: 2026-10-29
- **Project Leader / Architect**: ChatGPT — APPROVE
- **Technical Reviewer / QA**: Antigravity — APPROVE
- **Main Developer**: Codex
- **Final Merged Pull Request**: PR #6 (commit `be6c7d955a5c1ec947927f1e2616ca1489ea4c94`)
- **Full Test Suite Evidence**: 616 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1)
- **Independent Adversarial Probes**: 14/14 passed
- **Next Epic**: TASK-007 — Packing List Extraction (TASK-007A: Packing List Foundation, TODO)
