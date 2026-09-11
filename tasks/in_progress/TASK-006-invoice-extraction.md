# TASK-006 — Invoice Extraction

Status: IN_PROGRESS  
Type: EPIC  
Priority: P1  
Owner: Project Leader  
Created: 2026-09-11  
Restructured: 2026-09-11  
Dependencies: TASK-001..TASK-005A DONE  
Children: TASK-006A..TASK-006F

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

That scope proved too large to review safely as one task. TASK-006 is therefore an epic and is implemented through TASK-006A..TASK-006F.

This is a scope decomposition, not a change to the product objective.

---

## 2. GLOBAL OBJECTIVE

The completed epic must support:

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

## 3. SUBTASKS

### TASK-006A — Extraction Foundation

Build only the reusable extraction primitives:

- extraction status / typed issue models;
- source candidate / provenance primitives if needed;
- invoice alias configuration + validation;
- strict lexical Decimal/date parsing;
- no document extraction;
- no DB;
- no service/orchestration;
- no semantic provider.

### TASK-006B — Deterministic Invoice Headers

Build deterministic header extraction only:

- PDF / Resolved PDF header fields;
- Excel header fields;
- Party fields;
- exact raw preservation;
- page/sheet/cell provenance;
- deterministic conflict handling;
- confidence policy.

No item-table extraction. No DB. No semantic provider.

### TASK-006C — Invoice Item Tables

Build conservative item-table extraction:

- Excel item-table candidate detection;
- item-field aliases;
- formula provenance;
- zero values;
- hidden rows/sheets policy;
- blank-row termination;
- TOTAL/SUBTOTAL safety;
- multi-table ambiguity.

No persistence. No semantic provider.

### TASK-006D — Extraction Persistence & State

Build persistence/state infrastructure only:

- `document_extractions`;
- active/history records;
- atomic save + SourceDocument status update;
- rollback;
- FAILED vs NEEDS_REVIEW persistence;
- explicit safe re-extraction policy.

No document parsing/extraction logic.

### TASK-006E — Invoice Extraction Service

Compose the approved pieces:

- primary input `document_id`;
- non-mutating downstream read/parse path;
- TASK-005A visual safety gate;
- deterministic header + item extraction;
- provider-neutral semantic fallback boundary;
- grounding/type validation;
- conservative merge;
- re-extraction orchestration;
- privacy-safe logging.

No hosted/vendor AI adapter.

### TASK-006F — Integration & Regression

Validate the complete Invoice flow:

- production composition;
- native PDF;
- Excel;
- safe ResolvedPdfDocument;
- unresolved visual review;
- persistence/history;
- source immutability;
- privacy;
- full regression;
- README/documentation.

---

## 4. GLOBAL INVARIANTS

Every child task must preserve:

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

## 5. WORKFLOW

Only one implementation child should be actively developed at a time.

Current:

```text
TASK-006A — IN_PROGRESS
TASK-006B — TODO
TASK-006C — TODO
TASK-006D — TODO
TASK-006E — TODO
TASK-006F — TODO
```

After each child is approved:

1. move that child to `tasks/done/`;
2. commit/push;
3. create a fresh project context bundle;
4. use the new exact pytest result as the next child baseline;
5. begin the next child.

Do not carry rejected code from the previous monolithic TASK-006 rounds into a child task unless it is independently re-read, re-implemented, and validated against that child's scope.

---

## 6. EPIC DEFINITION OF DONE

TASK-006 is DONE only when:

- [ ] TASK-006A DONE
- [ ] TASK-006B DONE
- [ ] TASK-006C DONE
- [ ] TASK-006D DONE
- [ ] TASK-006E DONE
- [ ] TASK-006F DONE
- [ ] final Invoice extraction flow passes full regression
- [ ] no unresolved CRITICAL/HIGH issue
- [ ] Project Leader closes the epic

---

## 7. PROJECT LEADER DECISION

2026-09-11 — Original monolithic TASK-006 implementation approach stopped before any rejected implementation was applied.

Reason: scope coupling was reducing implementation/review reliability. The epic was decomposed to improve code quality and make each acceptance boundary independently testable.
