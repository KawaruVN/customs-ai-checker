# TASK-006D — Extraction Persistence & State

Status: TODO  
Priority: P1  
Parent: TASK-006  
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
