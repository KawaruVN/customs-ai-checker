# TASK-007B — Deterministic Packing List Headers

Status: TODO  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007A approved and merged

## Objective and inputs

Extract canonical Packing List header fields from approved parsed workbooks and
safe native/resolved PDF content, using TASK-007A configuration and contracts.
This is a future scope plan, not implementation authorization.

## In scope and output

- Generic EN/VI/ZH whole-label candidate discovery with longest/specific matching.
- Canonical PackingList header result, typed issues and source candidates.
- Separate Packing List number from list-valued Invoice references; retain all
  supported references without scalar conversion or invented associations.
- Explicit party labels and document-level package/weight/volume distinctions.

## Safety invariants

Use existing conservative Decimal/date parsing. Preserve exact raw text, source
document and page or sheet/cell evidence. Missing fields remain None/empty lists.
Do not use substrings, fixed customer coordinates, hidden data or formula text as
trusted labels/values. Seller/buyer must not be inferred from shipping roles.
Conflicting values stay unresolved with review, including three-way conflicts.
Unsafe visual content cannot become trusted extraction evidence.

## Acceptance and tests

- Synthetic PDF/Excel tests at arbitrary positions cover EN/VI/ZH labels and
  longest/specific boundaries, without false role or weight/count matches.
- PDF page and Excel sheet/cell raw evidence survives canonical assembly.
- Multiple invoice references remain canonical lists; missing values are not made up.
- Zero, ambiguous numeric/date, formulas, hidden data and sticky conflicts behave
  conservatively with typed review issues.
- TASK-007A and completed Invoice regression remain green.

## Out of scope and review

No item tables, service, DB/codec changes, semantic providers, matching, rules,
normalization, endpoints or UI. Independent review and Project Leader approval
are required before merge; no DONE state is authorized by this plan.
