# TASK-006F — Invoice Integration & Regression

Status: TODO  
Priority: P1  
Parent: TASK-006  
Dependencies: TASK-006A..TASK-006E DONE

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
- README/docs update.

## Out of scope

No new business features.

If integration exposes a defect in an approved child, fix the defect in the owning boundary without expanding TASK-006F into a second implementation task.

## Closure

TASK-006F may close only when the complete full-suite result is green and Project Leader confirms the parent TASK-006 epic is ready to close.

Baseline is the exact approved TASK-006E full-suite result.
