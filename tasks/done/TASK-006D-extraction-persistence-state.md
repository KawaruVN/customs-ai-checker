# TASK-006D — Extraction Persistence & State

Status: DONE  
Priority: P1  
Parent: TASK-006  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Created: 2026-09-11  
Completed: 2026-10-29  
Merged PR: #4 (commit `cd875b9`)  
Dependencies: TASK-006C DONE  
Authoritative pre-task baseline: 291 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 435 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. OBJECTIVE

Implement extraction persistence, audit history, and processing-state transitions in the SQLite repository layer without business extraction logic, external ORMs, or application-level extraction orchestration.

---

## 2. IN SCOPE

- `document_extractions` table and constraints in SQLite schema.
- Strict Pydantic extraction record models (`ExtractionAttempt`, `ExtractionReplacement`, `ExtractionRecord`).
- Database-enforced single-active-record constraint via unique partial index.
- Full audit history preservation with monotonic attempt numbering per document.
- Transactional atomicity: `BEGIN IMMEDIATE` serialization; atomic deactivation of prior active record, insertion of new attempt, and `SourceDocument` metadata update.
- Explicit rowcount assertions (`cursor.rowcount == 1`) on every write.
- Explicit transaction rollback on any database, trigger, rowcount, or commit failure.
- Strict separation of `FAILED` vs `NEEDS_REVIEW` vs `EXTRACTED`: `FAILED` extractions are stored as inactive history (`is_active = 0`) and never deactivate or overwrite an existing valid active result.
- Explicit re-extraction authorization policy: `save_attempt` allowed only without an active extraction; `replace_active` requires exact `expected_active_extraction_id`.
- Optimistic concurrency guards verifying `source_file_hash` and `expected_processing_status` under the writer lock.
- Storage codec envelope version 1 with explicit type tags for candidate union values, preserving Decimal scale, dates, and multilingual text.
- Privacy and security: parameterized SQL queries only; static sanitized repository error messages without leaking payload, customer data, file paths, or SQL parameters.

---

## 3. OUT OF SCOPE

- Parsing documents (handled in local parser layer / TASK-004).
- Deterministic extraction algorithms (handled in TASK-006B / TASK-006C).
- Application extraction service orchestration (`InvoiceExtractionService` — TASK-006E).
- Semantic / hosted AI fallback.
- Customs document rules and matching logic.
- External database migration (PostgreSQL, MySQL).

---

## 4. KEY ACCEPTANCE CRITERIA (6/6 PASS)

1. [x] **Failed replacement leaves prior active extraction intact**: Injected failure during replacement rolls back completely; a replacement with `status = FAILED` records the failure in history as inactive (`is_active = 0`) while leaving the prior active extraction untouched.
2. [x] **Missing SourceDocument rolls back insert**: Foreign key constraints with `ON DELETE RESTRICT` and repository validation reject orphan extractions; transactions roll back cleanly.
3. [x] **Re-extraction preserves history and exactly one active record**: Monotonic attempt numbers (`attempt_number > 0`, `UNIQUE(document_id, attempt_number)`) and partial index (`WHERE is_active = 1`) guarantee that history is appended and at most one active record exists.
4. [x] **System failure and data review are distinct**: `FAILED` extractions are stored as inactive historical attempts and cannot be active; `NEEDS_REVIEW` activates normally and provides usable data requiring human review.
5. [x] **Application/domain layers do not execute raw SQL**: All SQL statements are encapsulated inside the repository layer (`DocumentExtractionRepository` and `database.py`) using bound parameters.
6. [x] **Full regression stays green**: 435 passed, 0 failed, 2 warnings across the repository test suite.

---

## 5. VALIDATION EVIDENCE

Authoritative pytest commands and counts:

```text
python -m pytest tests/unit/repositories/ -v                # 151 passed in 2.99s
python -m pytest -v                                       # 435 passed, 2 warnings in 8.66s
```

Detailed test metrics:
- Focused repository persistence tests (`test_document_extractions.py`, `test_extraction_database.py`, `test_extraction_models.py`): 144 passed, 0 failed, 0 skipped
- Pre-existing repository tests (`test_source_documents.py`): 7 passed
- Pre-existing regression suite: 291 passed (100% green)
- Total suite: 435 passed, 0 failed, 0 skipped, 2 warnings (Starlette/httpx testclient and AnyIO BlockingPortal deprecations)
- Independent adversarial probes: 23 distinct probes passed (100% green)
  - 7 direct SQL schema and constraint probes (partial index, FK restrict, duplicate attempts, FAILED active check, idempotent `init_db`).
  - 5 mandatory transaction fault-injection probes (fault before write, fault after deactivation, fault after insert, fault during metadata update, fault at `commit()`).
  - 4 history and re-extraction lifecycle probes (initial failed, retry activation, failed replacement, successful re-extraction).
  - 4 canonical serialization and codec probes (Decimal scale/precision, multilingual CJK/Vietnamese, cross-document provenance guard, duplicate JSON keys).
  - 1 privacy and exception message sanitization probe (no leak of sensitive database trigger messages).
  - 2 multi-threaded concurrent writer probes (concurrent `save_attempt` and concurrent `replace_active` serialized safely).
- Environment: Windows, Python 3.13.14, pytest 9.1.1

---

## 6. DELIVERABLES

- `src/customs_ai/repositories/database.py` — Schema definition for `document_extractions` table and `one_active_extraction_per_document` partial unique index, with enforced foreign keys and connection closing wrappers.
- `src/customs_ai/repositories/document_extractions.py` — `DocumentExtractionRepository` with `BEGIN IMMEDIATE` transactions, atomic deactivation/insert/update, and rowcount assertions.
- `src/customs_ai/repositories/extraction_models.py` — Pydantic models (`ExtractionAttempt`, `ExtractionReplacement`, `ExtractionRecord`) and storage envelope v1 codec (`serialize_result`, `deserialize_result`).
- `src/customs_ai/repositories/source_documents.py` — Updated repository with connection closing wrappers.
- `docs/decisions/ADR-001-extraction-persistence-state.md` — Formal Architectural Decision Record for extraction persistence.
- `tests/unit/repositories/test_document_extractions.py` — 34 unit tests for repository lifecycle and transactions.
- `tests/unit/repositories/test_extraction_database.py` — 33 unit tests for DDL, foreign keys, and constraints.
- `tests/unit/repositories/test_extraction_models.py` — 77 unit tests for model validation and JSON serialization.

---

## 7. DEFINITION OF DONE

- [x] `document_extractions` table and constraints implemented
- [x] Strict extraction record models defined
- [x] Exactly one active extraction enforced at DB level
- [x] History preservation and monotonic attempt ordering implemented
- [x] Atomic write transaction with rowcount checks and rollback implemented
- [x] `FAILED` vs `NEEDS_REVIEW` semantics strictly separated
- [x] Explicit re-extraction eligibility and optimistic preconditions enforced
- [x] Repository-only SQL encapsulation maintained
- [x] No raw document content or secrets logged
- [x] 6/6 key acceptance criteria PASS
- [x] 144 focused tests added
- [x] Pre-existing regression green (291/291 tests)
- [x] Antigravity independent review: APPROVE
- [x] Project Leader architectural approval: APPROVE

---

## 8. CLOSURE SUMMARY

- **Status**: CLOSED / DONE
- **Date**: 2026-10-29
- **Merged PR**: Pull Request #4 (commit `cd875b9`)
- **Key Acceptance**: 6/6 PASS
- **Developer**: Codex — Main Developer
- **Review Decision**: Antigravity — Independent Technical Reviewer / QA — APPROVE
- **Architectural Approval**: Project Leader — APPROVE
- **Baseline for TASK-006E**: 435 passed, 0 failed, 0 skipped, 2 warnings
