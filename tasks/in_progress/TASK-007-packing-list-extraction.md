# TASK-007 — Packing List Extraction

Status: IN_PROGRESS  
Type: EPIC  
Priority: P1  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Owner / Final Approver: Project Leader  
Created: 2026-10-29  
Dependencies: TASK-006 DONE  
Children: TASK-007A..TASK-007E

## Objective

Build conservative Packing List extraction using the existing canonical models
and the proven local parsing, provenance, safety and transactional patterns from
TASK-006. The current implementation authorization covers TASK-007A only.

## Canonical contract

`PackingList`, `PackingItem`, `CanonicalField`, `Party` and `ValueOrigin` in
`src/customs_ai/domain/schema.py` remain authoritative. TASK-007A includes only
the explicitly Project Leader-approved PackingList.date annotation bug fix from
the erroneous runtime CanonicalField[NoneType] to CanonicalField[datetime.date].
All other canonical fields/structures and the database schema remain unchanged.

The foundation header alias paths are `packing_list_number`, `date`,
`seller.name`, `seller.tax_id`, `seller.address`, `buyer.name`, `buyer.tax_id`,
`buyer.address`, `shipment_reference`, `invoice_references`, `package_count`,
`package_type`, `gross_weight`, `net_weight`, `dimensions` and `volume`.
`invoice_references` denotes the existing list, not a new scalar field.

Item paths are `item_code`, `description`, `quantity`, `unit`, `package_number`,
`gross_weight` and `net_weight`. `items` remains `list[PackingItem]`.
Canonical Party fields outside the approved alias subset, such as country_code,
are not removed or newly authorized for extraction by this epic plan.

## Child sequence

| Child | Status | Scope | Dependencies |
|---|---|---|---|
| TASK-007A | DONE | Packing aliases, validation, typed result contracts and tests (PR #7, commit `57957a4`) | TASK-006 DONE |
| TASK-007B | TODO | Deterministic Packing List headers | TASK-007A approved and merged |
| TASK-007C | TODO | Conservative deterministic Excel packing item tables | TASK-007A and TASK-007B approved and merged |
| TASK-007D | TODO | Packing service composition and reviewed persistence support | TASK-007B and TASK-007C approved and merged |
| TASK-007E | TODO | Production-path integration and full regression | TASK-007D approved and merged |

Each child requires its own implementation handoff, independent review, Project
Leader approval and merge before the next implementation begins. This proposed
decomposition does not authorize implementing future children during TASK-007A.

## Safety invariants

1. Missing fields remain None or empty lists; no business values are fabricated.
2. Preserve raw values separately from typed values, with source document and
   page or sheet/cell evidence. EXTRACTED provenance rules remain intact.
3. Keep seller/buyer distinct from shipper/consignee/exporter/importer. Aliases
   alone cannot prove a party role or document context.
4. Keep document package counts separate from item quantity and package numbers;
   keep gross/net weights and document/item weight contexts distinct.
5. Keep dimensions as dimensional text and volume as a Decimal quantity.
6. Use conservative existing Decimal/date parsers; uncertainty requires review.
7. No customer coordinates, inferred missing facts, formula execution or silent
   majority-vote resolution of competing evidence.
8. Unsafe visual evidence cannot become trusted text or enter semantic fallback.
9. Preserve source bytes, history and privacy. SQL remains in repositories.
10. Preserve approved Invoice behavior and the completed TASK-006 contracts.

## Scope boundaries

TASK-007A contains no document extraction, orchestration, persistence or AI.
Later children may reuse approved components within their explicit scope.
PDF item-table recognition is not authorized by this decomposition; unsupported
PDF item data must be represented explicitly and conservatively in later tasks.
Matching, normalization, customs rules, hosted SDKs, endpoints and UI are excluded.

TASK-007D must review a versioned Packing-specific persistence extension rather
than sending Packing data through the current Invoice-only storage envelope.
No SQLite schema or codec change is made in TASK-007A.

## Epic acceptance and closure

- Every child meets its own canonical, evidence, safety and regression criteria.
- Packing values, list-valued references, Decimal/date types and provenance
  survive approved processing and future persistence round-trips.
- Conflicting or insufficient evidence remains reviewable; source files remain
  byte-identical and normal logs exclude sensitive data.
- All pre-existing Invoice tests remain green and integration uses production
  components rather than a duplicate extraction implementation.
- No unresolved CRITICAL/HIGH issue remains and the Project Leader closes the
  epic after independent review and approved child merges.

Authoritative baseline after TASK-007A: 697 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1).
This epic remains IN_PROGRESS.
