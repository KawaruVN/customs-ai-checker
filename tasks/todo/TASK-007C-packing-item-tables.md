# TASK-007C — Deterministic Packing Item Tables

Status: TODO  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007A and TASK-007B approved and merged

## Objective and inputs

Extract canonical PackingItem rows conservatively from generic parsed Excel
tables using the approved item aliases and result contract. This plan does not
authorize beginning implementation during TASK-007A.

## In scope and output

- Evidence-based header/table discovery at arbitrary worksheet/row/column positions.
- Seven approved item fields: item_code, description, quantity, unit,
  package_number, gross_weight and net_weight.
- Canonical item result with status, source candidates and typed review issues.

## Safety invariants

Do not treat generic numeric columns or isolated labels as proof of a product
table. Separate document totals from item quantities/weights and package numbers
from package count/type. Preserve raw values, leading-zero identifiers, numeric
zero, Decimal precision, document ID and actual sheet/cell provenance. Relevant
incomplete rows stay partial and reviewable. Formulas are opaque and unexecuted.
Hidden rows/sheets, merged/duplicate columns, summary boundaries, blank business
rows and competing tables require explicit conservative policies; never silently
append or arbitrarily choose competing tables.

## Acceptance and tests

- Synthetic XLSX/XLS and parsed-workbook tests exercise arbitrary layouts and
  EN/VI/ZH labels without fixed customer templates.
- Correct seven-field canonical mapping and exact source evidence; no fabricated
  quantity, package identifier or weights.
- Tests distinguish gross/net and document/item contexts, blank-row termination,
  genuine totals versus product names, formula uncertainty, hidden content,
  partial rows and multi-table ambiguity.
- Only structurally justified continuation is allowed; ambiguous cases need review.
- Foundation/header tests and all completed Invoice regression remain green.

## Out of scope and review

No PDF table recognition, item matching by position, orchestration, DB/codec,
semantic providers, normalization, rules, HTTP/UI or customer adapters. Independent
review and Project Leader approval are required before merge or task closure.
