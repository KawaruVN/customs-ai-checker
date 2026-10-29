# TASK-007E — Packing List Integration & Regression

Status: TODO  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007D approved and merged

## Objective and inputs

Verify the complete approved Packing pipeline through real production composition
and isolated synthetic fixtures. Use the exact latest approved baseline, not an
assumed test count. This is a future integration task, not a feature expansion.

## In scope and output

- SourceDocument/classification, readonly parse, approved visual safety,
  deterministic Packing header/Excel items, canonical assembly and persistence.
- Real native PDF, XLSX/XLS, controlled local safe/unsafe visual cases and fresh
  repository active/history reads.
- Exact measured regression evidence and clearly disclosed minimal defect fixes.

## Safety invariants

No source mutation, fabricated item rows, scalar reduction of invoice references,
package/quantity/weight/role conflation or unverified visual evidence. Preserve raw
text and source page/sheet/cell, Decimal/date types and leading-zero identifiers.
PDF item recognition remains unsupported unless a separate approved task adds it.
No actual customer files, production DB, hosted calls or sensitive routine logs.

## Acceptance and tests

- Production-path tests cover legitimate Packing Lists and wrong/unknown types,
  missing/ambiguous fields, formulas, hidden/competing tables and visual conflicts.
- Document totals and item weights/quantities remain distinct, and all Invoice
  references survive canonical/persistence round-trip as a list.
- Explicit replacement preserves history; stale source/active guards and injected
  persistence failures leave committed state atomic and prior active data intact.
- Source SHA-256 and log privacy checks pass; no import-time remote/model activity
  or application SQL is introduced.
- All earlier Packing and Invoice tests pass; collected/passed/failed/skipped/
  warnings/runtime and environment are independently measured and reported.

## Defects, exclusions and closure

Prove defects with failing tests and apply only minimal backward-compatible fixes
at their owning boundary. Escalate architecture/security changes rather than
weakening assertions. No new extraction features, matching, normalization, rules,
provider SDKs, UI or endpoints. Passing tests alone does not close TASK-007:
Antigravity review, Project Leader approval and approved merges are required.
