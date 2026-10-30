# TASK-017 — Declaration Intake: Structured / Manual Foundation

Status: TODO
Priority: P1
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: Docs amendment review/merge/closure; TASK-008 DONE; TASK-016 DONE; explicit Leader intake/schema/persistence design approval
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE AND BACKGROUND

Receive a versioned draft declaration as structured/manual data with field identity, evidence, correction history and explicit support coverage before normalization and checking. Prioritize reducing mistakes that lead to declaration amendment/cancellation. Extraction/intake success is never shipment PASS. Current `CustomsDeclaration` is a canonical representation only; it does not implement intake, a full declaration registry, source policy or readiness gates.

Follow the Constitution, Master Specification, Architecture, [schema](../../docs/DATA_SCHEMA.md), [document inventory](../../docs/DOCUMENT_INVENTORY.md), [declaration field/source/coverage matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md), [TASK-016](TASK-016-arrival-notice-evidence.md) and ADR-004. Owner business policy is approved input; all new technical contracts in this TODO spec require independent technical review and Leader approval before affected changes.

## 2. SCOPE

- Propose and obtain approval for a strict structured/manual intake contract and exact supported declaration field set, using the current canonical model where semantically adequate and explicitly identifying gaps.
- Implement the approved provider-neutral intake application boundary for supplied structured data and manual corrections; no format-specific PDF/OCR or UI required. Treat imported data as untrusted and retain its true input method, source version/hash where available and MANUAL versus EXTRACTED origin.
- Define the versioned declaration field registry and intake coverage snapshot with field ID/name/definition, mode/context applicability, required sources and forbidden overrides, comparison/aggregation/conversion/tolerance specification, evidence requirements, severity/blocking/exception behavior and support/coverage state.
- Preserve a draft's identity/revision, exact raw input, typed value, field/source lineage, original values and correction history. Make a changed draft/sources/policy identifiable so later checks cannot reuse a stale result as current.
- Produce a proposed check-input snapshot/coverage contract for downstream tasks; execute no source comparisons or readiness business engine in this intake task.

## 3. OUT OF SCOPE

- PDF/scan/image/OCR declaration extraction, arbitrary Excel layout interpretation and hosted AI. Any future PDF/OCR intake needs a separate explicit task/handoff after structured/manual foundation is stable.
- Automatic declaration preparation, edits, transmission or external customs-system integration; legal/tax/HS decision; historical HS auto-copy.
- Normalization engine (TASK-009), document relationship + item matching (TASK-010), rule engine (TASK-011), document↔document or source↔declaration execution (TASK-012), report UI (TASK-013), correction/recheck workflow (TASK-014) and golden dataset execution (TASK-015). Preserve their IDs and intended responsibilities.
- Unapproved canonical/DB/origin-enum changes, new document extractors, forced party equality, default Bill winner or exception approval engine.

## 4. INPUT / OUTPUT

Input: authoritative shipment/checking context and SEA/AIR applicability, draft declaration identity/revision, supplied structured fields/manual values with input provenance, existing extracted document references and approved registry. No undocumented export format or external legal catalog is assumed; specific import adapters/catalog mappings require reviewed specifications.

Output: strictly validated, versioned draft snapshot plus immutable original/correction lineage and explicit per-field intake/support coverage. Output identifies missing/unsupported/ambiguous fields and unresolved evidence/source dependencies; it does not say that declared values are compliant. Proposed persisted format and snapshot signatures need Leader approval before implementation.

## 5. FUNCTIONAL REQUIREMENTS

- FR-01: Validate exact approved fields and types; reject unknown or malformed structured input without losing an already accepted draft. Keep leading zeros/casing, Decimal precision, valid date semantics and zero values. No fabricated default values.
- FR-02: Register fields by semantic definition and mode/context; do not equate Port of Loading, Place of Receipt, storage or customs location codes. Record mapping catalog/version and evidence when approved conversion is performed; unresolved mapping stays explicit.
- FR-03: Retain declared values independently of each source document's values. Required-source metadata must not overwrite the declaration or extraction. Separate declared, required, document and calculated values in downstream contracts.
- FR-04: Preserve importer/exporter, commercial seller/buyer and transport shipper/consignee/notify as separate roles. Legitimate differences require traceable named exception evidence at the authorized checking layer, not forced equality at intake.
- FR-05: Registry coverage distinguishes supported/checked from unsupported/missing/not checked and conditional not-applicable evidence. An accepted draft is not a PASS; critical unsupported/unchecked fields must be exposed as NOT_CHECKED with required BLOCK readiness semantics for later aggregation.
- FR-06: Calculated values trace input field versions, formula, conversion/rate/catalog and rounding/tolerance policy. Never label a calculation EXTRACTED; origin/provenance representation must be approved before any enum/schema change.
- FR-07: Keep insured value distinct from insurance premium/charge. Freight/insurance adjustments record amounts already included in price and prevent duplicate addition; intake must not treat insured value as insurance charge or silently compute customs value.
- FR-08: Preserve declarant-supplied HS as their decision; do not copy historical HS automatically. Capture classification description for later cross-document reconciliation and explicitly mark legal/classification correctness unchecked.
- FR-09: C/O, permits and specialized certificates are conditional on approved shipment/goods applicability; absence is not a universal missing-document error. Unknown applicability remains explicit, not silently NOT_APPLICABLE.
- FR-10: Snapshot dependencies include draft/source/extraction/correction/registry/policy versions; changed inputs make earlier results stale. Intake supplies immutable identity/version evidence; later TASK-014 owns recheck orchestration.

## 6. OWNER BUSINESS POLICY

INTERNAL_POLICY `OP-AN-DECL` v1 (2026-10-30), IDs and meaning in ADR-004 and the field matrix; these are Owner operational requirements, not universal law.

- OP-AIR-01: Actual pieces/gross must follow valid matching active AN; no separate weigh ticket prerequisite. AWB preserves shipment identity/Bill number/parties/routing/freight evidence. With AWB108/AN113, declaration108 must later BLOCK; declaration113 may pass source comparison while AWB discrepancy stays OPEN and dossier readiness is still separately decided.
- OP-SEA-01/02: AN required for workflow loading-place indicator; exact field/catalog mapping. Vessel/voyage, arrival/ETA and containers reconcile against AN; ETA is not actual arrival. B/L packages/weight eligible only if matching AN, and disagreement has no automatic winner.
- OP-GATE-01: Missing AN, wrong shipment, uncertain active revision/master-house scope, wrong weight kind or missing necessary unit means no Bill fallback. Confidence and averaging cannot override policy.
- OP-READY-01: Declaration compliance, document reconciliation and dossier readiness are separate. High-risk unresolved conflicts on SEA loading place, AIR totals, actual Bill identity, importer/consignee relationships, invoice number/date/currency/Incoterms/value and arrival/flight/vessel/voyage block. Critical NOT_CHECKED blocks shipment PASS.
- OP-EXC-01: Future accepted exception records finding/fields/documents, differing values, reason/evidence, authorized acceptor, time and policy version. It cannot permit a wrong required AN value, omit mandatory AN or bypass shipment identity. Intake may carry existing evidence, but cannot accept an exception or erase a discrepancy.
- OP-RECHECK-01: Input/policy changes invalidate old-result applicability; preserve old audit history rather than overwrite it.

No source winner/check/readiness/exception engine is implemented in this task; these requirements define the downstream interface and later acceptance cases.

## 7. NON-FUNCTIONAL, MODEL / VERSION AND EXPECTED FILES

Deterministic strict validation and local processing; no import/factory side effects, new dependency or network service without approval. Future domain/intake/registry/repository modules and unit/integration tests depend on the approved design. Current canonical `0.1`, Invoice envelope v1, Packing v2, completed Transport v3, future reviewed AN encoding and DB schema/migration version are distinct. Do not reserve a declaration or AN envelope version here. Any registry/correction/snapshot storage schema, canonical aggregate, field/origin enum or migration requires explicit Leader approval and ADR; preserve legacy rows and completed functionality.

## 8. CONSTRAINTS AND EDGE CASES

Use exact approved field IDs, maintain distinction between operational policy and legal checks, and no automatic external action. Cover incomplete/duplicate drafts, ambiguous version/active state, changed source after check, missing required AN, wrong shipment/master-house mapping, chargeable-only weight, missing unit, zero values, unknown/mismatched currency, leading-zero identifiers, ambiguous date/Decimal, place-name/code mismatch, missing applicability data, legitimate party differences and already-included freight/insurance. No fabricated weighing evidence/time/measurement ID.

## 9. ACCEPTANCE CRITERIA

- [ ] AC-01: Leader approves exact structured/manual intake contract, registry field set, canonical gaps and persistence/version/migration proposal before affected implementation.
- [ ] AC-02: Valid supplied drafts round-trip losslessly with true input origin, field/version/source evidence and original/correction history; wrong/unknown values fail without overwriting prior data.
- [ ] AC-03: Registry includes every required metadata dimension from Scope, explicit critical coverage and conditional applicability. No unsupported critical field can disappear into a shipment PASS claim.
- [ ] AC-04: Declared values stay separate from required/document/calculated values; no automatic declaration edit or source-policy override. Proposed report input can later show declaration + each source + required value/source/reason + discrepancy/block/exception/action.
- [ ] AC-05: Units, weight kinds, arrival date kinds, semantic place mapping, roles, premium/insured value, included costs and declarant HS responsibility remain distinct and tested.
- [ ] AC-06: Draft/source/correction/registry/policy changes produce a new immutable snapshot identity; stale check applicability is detectable without implementing recheck orchestration.
- [ ] AC-07: PDF/OCR, normalization, matching, rule execution, exceptions acceptance and external transmission remain unimplemented; all existing document/persistence compatibility and focused/full regression pass.
- [ ] AC-08: Antigravity independently verifies source/coverage false-PASS risks and exact test evidence before Leader approval and Owner-controlled closure; TASK-009 cannot start before this dependency is satisfied.

## 10. TEST REQUIREMENTS

Unit: strict input/registry schemas, exact field coverage and applicability, type/date/Decimal/identifier/origin validation, calculated lineage, snapshot dependency identity. Integration: structured/manual input → approved storage → fresh read → correction/new revision; old snapshot retained, cross-family compatibility and concurrent correction guard. Failure: unknown fields, malformed drafts, unauthorized origin claims, missing units/source references, ambiguous active draft, wrong scope, incomplete critical coverage, corrupt stored data, failed transaction, stale input, insured value passed as premium and double-included costs. Regression: completed Invoice/Packing/Transport/AN and full suite. No PDF/OCR tests required for this phase; explicitly deferred, not counted as supported coverage.

Use the 12 design walkthroughs in [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md) as traceability and later TASK-012/014 runtime scenarios. In this task test input/evidence/coverage/snapshot behavior only, without inventing a fake passing rule engine. Report actual collected/passed/failed/skipped/warnings/runtime and command; historical baseline is not a just-run result.

## 11. TEST DATA, OBSERVABILITY, COST AND PRIVACY

Synthetic/anonymized drafts/documents and isolated local DB only. AI allowed: NO. Log IDs, draft/snapshot/field IDs, contract/registry/policy versions, correction actor/time and static failure codes as approved; do not log full declaration, party identities or confidential cargo data. Treat formulas/macros and structured uploads as untrusted, never execute them. Any authorization/acceptor identity contract must be explicit; a client-supplied label alone is not proof of authority.

## 12. DEPENDENCIES AND DELIVERABLES

No implementation before amendment closure, TASK-008/TASK-016 DONE and explicit contract approval. Deliver approved technical design/ADR, strict structured/manual intake and registry, storage/correction snapshot handling only if approved, adversarial tests, actual focused/full regression, coverage gaps and independent-review report. Execution then continues to TASK-009..015 with IDs unchanged; source↔declaration checks are TASK-012 lane B alongside document↔document lane A.

## 13. DEFINITION OF DONE / NOTES

- [ ] Approved scope implemented and all ACs/test requirements verified.
- [ ] No unresolved critical/high issues or hidden coverage gaps; compatibility and source history retained.
- [ ] Antigravity APPROVE, Leader technical approval, Owner-controlled merge/closure; docs truthful.

Planning only; TODO. Developer implementation, independent review and Project Leader technical approval pending. No runtime intake or readiness capability claimed by this specification.
