# TASK-006D — Extraction Persistence & State

Status: IN_PROGRESS  
Priority: P1  
Parent: TASK-006  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Updated: 2026-10-29  
Dependencies: TASK-006C DONE

## Objective

Implement extraction persistence/history and processing-state transitions without business extraction logic.

## In scope

- document_extractions table;
- strict extraction record model;
- exactly one active extraction;
- history preservation;
- atomic extraction save + SourceDocument metadata update;
- rowcount validation;
- transaction rollback;
- FAILED vs NEEDS_REVIEW metadata;
- explicit re-extraction eligibility/policy;
- repository-only APIs;
- no raw document content in logs.

## Out of scope

- parsing;
- deterministic extraction;
- semantic fallback;
- document-type logic beyond safe identifiers/statuses.

## Key acceptance

- failed replacement leaves prior active extraction intact;
- missing SourceDocument rolls back insert;
- re-extraction preserves history and one active record;
- system failure and data review are distinct;
- application/domain layers do not execute raw SQL;
- full regression stays green.

Baseline is the exact approved TASK-006C full-suite result.

## Implementation policy and review handoff

- Baseline independently verified before implementation: 291 passed, 0 failed, 0 skipped, 2 warnings in 5.18s.
- Branch starts at TASK-006C merge `8bbb7f8`. Its approved closure was verified read-only from `main` commit `a08bbfb`; this branch does not yet contain that documentation-only commit. No merge or history change was performed.
- Decision record: `docs/decisions/ADR-001-extraction-persistence-state.md`.
- Repository API: `save_attempt`, `replace_active`, `get_by_extraction_id`, `get_active`, `list_history`. Inputs and records are strict Pydantic models; payloads reuse the approved invoice header/item result contracts and canonical models.
- First save requires no active extraction. Retry after FAILED with no active result uses first-save policy. Any existing active result, including NEEDS_REVIEW, requires `replace_active` with its exact expected extraction ID. Hash and expected processing status are checked inside the transaction. These are optimistic consistency guards, not user authentication or application orchestration.
- EXTRACTED and NEEDS_REVIEW activate. FAILED is retained as an inactive historical attempt and does not supersede or deactivate a prior active result. A later retry with a prior active result still requires explicit replacement.
- SourceDocument processing/extraction status describes the latest committed attempt. Consumers retrieve the usable active result through `get_active`; latest FAILED metadata may coexist with a prior EXTRACTED/NEEDS_REVIEW active result.
- BEGIN IMMEDIATE serializes writers. Deactivation, insertion and SourceDocument metadata update commit together; constraint, rowcount or commit errors roll back all changes. A rolled-back database operation is not recorded as a committed extraction attempt.
- Additive idempotent SQLite initialization preserves existing source rows. A unique partial index enforces at most one active row; every managed connection enables foreign keys. No history deletion API is provided.
- Persistence uses canonical schema version 0.1 and storage codec version 1. Canonical Decimal/date values retain their typed fields. Candidate union values have explicit type tags to prevent ambiguous JSON revalidation. Unsupported/nonfinite values or malformed stored content fail closed. Explicit non-null field/candidate source IDs must match the record's document ID; cross-document aggregation is outside this contract.
- Source files are neither opened nor modified by persistence. SQL is parameterized; repository errors are static and do not include payloads, paths or SQL parameters. No new network, ORM or extraction dependency.

## Developer validation evidence — 2026-10-29

Python 3.13.14, pytest 9.1.1. All tests use isolated temporary runtime/database
paths, `python -B`, `-p no:cacheprovider`, and an explicit external `--basetemp`
for execution. The full-suite TestClient run used the local execution environment.

| Command scope | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-implementation full baseline `pytest -v` | 291 | 291 | 0 | 0 | 2 | 5.18s |
| New persistence test files `--collect-only -q` | 144 | — | — | — | 0 | 0.62s |
| `pytest tests/unit/repositories -v` (144 new + 7 existing cases) | 151 | 151 | 0 | 0 | 0 | 2.99s |
| `pytest --collect-only -q` | 435 | — | — | — | 2 | 1.20s |
| Full `pytest -v` | 435 | 435 | 0 | 0 | 2 | 9.06s |

New test files: `test_document_extractions.py`, `test_extraction_database.py`,
`test_extraction_models.py` under `tests/unit/repositories/`. They cover real
SQLite constraints and concurrency, first activation and explicit replacement,
FAILED/history semantics, stale source/active guards, malformed input/stored JSON,
exact typed round-trip/provenance, injected failures before/after metadata and
at commit, connection closure, privacy and source immutability. The two full-suite
warnings are existing Starlette/httpx and AnyIO BlockingPortal deprecations.

Antigravity audit priorities: transaction/commit rollback, active-vs-latest status,
optimistic preconditions, type-tagged serialization and validation on read,
partial-index/FK enforcement, additive initialization and connection lifecycle.

## Review state

Implementation and measured test results require independent review by Antigravity. Developer does not approve or close this task.
