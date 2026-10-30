# TASK-016 — Arrival Notice & Operational Evidence Foundation

Status: TODO
Type: EPIC
Priority: P1
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: Docs amendment reviewed, approved, merged and closed; TASK-008 DONE
Children: TASK-016A..TASK-016D (ALL TODO)
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE

Establish a separate, evidence-grounded Arrival Notice (AN) extraction foundation for SEA/AIR and operational evidence needed by later declaration checking. Extraction success must not imply document reconciliation or shipment PASS.

## 2. BACKGROUND AND AUTHORITATIVE INPUTS

Follow the Constitution, Master Specification, Architecture, [schema boundaries](../../docs/DATA_SCHEMA.md), [document inventory](../../docs/DOCUMENT_INVENTORY.md), [field/source/coverage matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md), and ADR-004. Owner operational policy is approved business input; the technical contracts described here remain proposals requiring Project Leader approval before code changes. This epic is a plan, not implementation authorization.

## 3. SCOPE AND CHILD SEQUENCE

| Child | Status | Deliverable | Start dependency |
|---|---|---|---|
| [TASK-016A](TASK-016A-arrival-contracts-compatibility.md) | TODO | Separate AN contracts, classification dimensions, compatibility and version plan | TASK-008 DONE; amendment closure; Leader approves contract scope |
| [TASK-016B](TASK-016B-arrival-classification-extraction.md) | TODO | SEA/AIR AN classification and conservative extraction | 016A independently approved, merged and closed; approved classifier changes |
| [TASK-016C](TASK-016C-arrival-service-persistence.md) | TODO | Service, validated history and persistence | 016B independently approved, merged and closed; approved codec/persistence design |
| [TASK-016D](TASK-016D-arrival-integration-regression.md) | TODO | Production integration, adversarial coverage and regression | 016C independently approved, merged and closed |

Each child receives its own explicit handoff, review and approval. Do not implement all children together. The execution order is docs amendment closure → TASK-008A..E → TASK-016A..D → [TASK-017](TASK-017-declaration-intake.md) → TASK-009 Normalization → TASK-010 Document Relationship + Item Matching → TASK-011 Rule Engine Foundation → TASK-012 two-direction checks → TASK-013 Report → TASK-014 Correction/Recheck → TASK-015 Golden Dataset Regression. Existing TASK-009..015 IDs are retained.

## 4. OUT OF SCOPE

- Implementing declaration comparison, source winner selection, relationship matching, rule execution, exceptions workflow, report UI, normalization engine or automatic declaration changes.
- Implementing ROAD/RAIL/MULTIMODAL extractors, Sea Waybill support, external legal rules, hosted AI, or fabricated weighing operations.
- Reserving an AN envelope version, changing canonical/DB schema without an approved design, or expanding TASK-008 aliases/path coverage.

## 5. INPUT AND OUTPUT

Inputs: synthetic/anonymized SEA/AIR AN files, existing source IDs/hashes, approved technical classifications, source references, and observed revision evidence. Operational evidence is input only if it actually exists.

Outputs: independently reviewed AN contracts, extractors, service/history integration, tests and documentation. Every field must retain document/extraction/field/page or sheet/cell lineage where available. Missing values remain missing; unresolved shipment identity, scope, units, weight kind or active revision stays explicit.

## 6. FUNCTIONAL REQUIREMENTS

- FR-01: Model AN separately from `TransportDocument`; distinguish document family, exact kind, mode, master/house hierarchy and checking context. An AN containing an AWB number is still an AN, never an AWB solely because of that reference.
- FR-02: Preserve raw text, typed values, identifiers with leading zeros, physical provenance and every candidate/conflict. Keep gross/net/chargeable weights, units, actual/estimated dates and shipment scope distinct.
- FR-03: Represent source revision/replacement evidence and unresolved active-document selection; upload time alone is not revision precedence. Do not conflate active extraction of one file with the active business revision among several files.
- FR-04: Retain original extraction and correction history. Source-decision evidence must later trace rule ID/version, required source/value and reason; this epic supplies evidence, not a rule-engine verdict.
- FR-05: Missing mandatory AN, wrong shipment, uncertain master/house mapping, uncertain active revision, wrong weight kind or missing necessary unit must remain visible to downstream consumers so they cannot silently fall back to Bill data.

## 7. OWNER BUSINESS POLICY AND SAFETY

Policy type: INTERNAL_POLICY / Owner operational policy `OP-AN-DECL` v1 (2026-10-30). Rule IDs OP-AIR-01, OP-SEA-01/02, OP-GATE-01, OP-READY-01, OP-EXC-01 and OP-RECHECK-01 are governed by ADR-004 and the field matrix, not legal assertions.

- AIR actual pieces and gross weight must use the valid, matching active AN. A separate weigh ticket is not a prerequisite. AWB remains evidence for shipment identity, actual Bill number, transport parties, routing and freight terms. AWB disagreement remains an open finding even when declaration follows AN.
- SEA AN is mandatory for the workflow's “địa điểm xếp hàng”. Name-to-code mapping must use the correct catalog and exact field definition; Port of Loading, Place of Receipt, storage and customs-location codes are distinct. Reconcile vessel/voyage, arrival/ETA and containers against AN; ETA never supplies actual arrival. B/L packages/weight are eligible only when matching AN; disagreement is conflict + BLOCK without an automatic winner.
- No averaging, default Bill winner or confidence override. No invention of weighing evidence, time or measurement ID. Role distinctions remain intact: seller ≠ shipper and importer/buyer/consignee/notify are not default synonyms.
- Separate declaration compliance, document reconciliation and dossier readiness. Critical NOT_CHECKED means BLOCK. Exceptions cannot excuse a wrong required AN value, missing mandatory AN or unresolved shipment identity. Rule execution remains TASK-012 scope.

## 8. MODEL, VERSION AND PERSISTENCE IMPACT

Current runtime canonical schema is `0.1`; no ArrivalNotice model is implemented. Proposed AN contracts/aggregate additions and compatibility are reviewed in 016A. Current extraction envelope pairs `(1, "invoice")`, `(1, "invoice_items")`, `(2, "packing_list")` and planned TASK-008 `(3, "transport_document")` remain distinct from canonical schema version and database schema/migration version. Do not reserve a future AN envelope number here. Any new classifier, codec or persistence change requires a separate approved technical design and child authorization; existing rows must remain readable.

## 9. EXPECTED MODULES AND CONSTRAINTS

Future approved work may affect domain/extraction/classification/repositories and unit/integration tests; exact files and migration need approval in each child. Preserve TASK-006/007 and completed TASK-008 behavior. Reuse local parsing, safety and transactional mechanisms. No new dependency, legal conclusion, source mutation, automatic declaration edit, public API or UI without explicit authorization.

## 10. ACCEPTANCE CRITERIA

- [ ] AC-01: All four children are independently approved, merged and closed in sequence.
- [ ] AC-02: SEA/AIR AN has a separate reviewed contract with provenance, units, scope, role and revision distinctions; unsupported dimensions stay unresolved.
- [ ] AC-03: AN cannot route as B/L/AWB by embedded reference; unsupported kinds/modes are refused conservatively.
- [ ] AC-04: AIR/SEA policy evidence is preserved without fabrication, silent fallback, hidden conflicts or extraction-to-PASS escalation.
- [ ] AC-05: Current Invoice/Packing and completed Transport persistence compatibility, source immutability and history guarantees are independently verified.
- [ ] AC-06: Full regression and adversarial integration meet child-specific criteria; actual counts/warnings/runtime are reported without reusing reported baseline as fresh evidence.
- [ ] AC-07: Leader approves epic closure before Declaration Intake implementation begins.

## 11. TEST REQUIREMENTS AND EDGE CASES

Unit: strict contracts/configuration, Decimal/date ambiguity, exact kinds, units/weight kinds, master/house scope, revisions and provenance. Integration: real local files through extraction, repository, fresh read and correction-history boundary. Failure: AN with AWB keyword; missing AN; wrong shipment; master AN versus house scope; chargeable-only AN; ambiguous revision; unsafe visual pages; hidden/formula Excel; unknown units; malformed/corrupt payloads. Regression: Invoice v1/Packing v2/completed Transport v3 and full suite. Include the 12 design walkthroughs in [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md) as future runtime cases at their authorized layers; current documentation walkthroughs are not runtime PASS.

## 12. TEST DATA, OBSERVABILITY, COST AND PRIVACY

Use synthetic/anonymized documents only. Log IDs, status/error codes and policy/contract versions; avoid party details, cargo content and provider exceptions. Audit references retain authorized evidence without duplicating confidential full text in logs. Deterministic local processing first; no hosted AI. Any use of existing local visual infrastructure requires a child-specific approved safety boundary. Never execute macros/formulas or mutate uploaded files.

## 13. DELIVERABLES AND DEFINITION OF DONE

- [ ] Reviewed child implementation and tests, compatibility evidence, docs and limitations.
- [ ] Reproducible focused/full test commands and exact results; no unresolved critical/high blockers.
- [ ] Antigravity independent approval and Project Leader closure; Owner controls Git publication.

## 14. DEVELOPER / REVIEW / LEADER NOTES

Planning only. All children TODO; no runtime capability or approval claimed. Antigravity review pending. Project Leader technical design and implementation authorization pending.
