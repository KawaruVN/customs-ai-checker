# TASK-016A — Arrival Notice Contracts & Compatibility

Status: TODO
Priority: P1
Parent: TASK-016
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: Docs amendment review/merge/closure; TASK-008 DONE; explicit Leader contract approval
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE AND BACKGROUND

Define and, only after explicit technical approval, implement strict provider-neutral AN extraction contracts and compatibility tests. Current canonical schema `0.1` has no ArrivalNotice; the proposal must not masquerade as an implemented field set. Follow the [parent epic](TASK-016-arrival-notice-evidence.md), [schema](../../docs/DATA_SCHEMA.md), [inventory](../../docs/DOCUMENT_INVENTORY.md) and [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md).

## 2. SCOPE

- Propose a separate `ArrivalNotice` canonical contract and exact approved field/path coverage for SEA/AIR. Submit aggregate impact and serialization compatibility to Leader before edits.
- Define strict configuration/alias and result contracts without interpreting files. Separate family, exact kind, mode, hierarchy and checking context; classification assertions need evidence rather than filenames or one embedded Bill/AWB keyword.
- Define field lineage to document/extraction/field/page or sheet/cell, raw/typed value, unit, weight kind, shipment scope and date kind. Keep actual arrival separate from ETA; no invented actual date.
- Define explicit unresolved revision/active-document evidence and correction links. Distinguish source revision selection from per-file active extraction.
- Specify how later source decisions reference rule ID/version, inputs, required source/value and reason. Derived values must trace inputs/formula and must never be marked EXTRACTED.
- Review version/migration strategy and strict backward-compatible tests before implementing approved contracts.

## 3. OUT OF SCOPE

File parsing/extraction, classifier algorithm changes, service/DB writes, normalization, rule execution, source winner selection, exceptions engine, relationship matching, UI and declaration auto-edit. No AN aliases in TASK-008 or loosened 24+2 path validator. No ROAD/RAIL/MULTIMODAL extractor.

## 4. INPUT / OUTPUT

Input: approved Owner policy and proposed field registry, current `schema.py`, canonical JSON schema, existing v1/v2 and completed Transport v3 examples, synthetic AN evidence. Output: Leader-approved contract/version proposal, exact path specification, strict typed/configuration contracts, schema/serialization compatibility tests and limitations. Output must identify proposed versus implemented support.

## 5. FUNCTIONAL AND NON-FUNCTIONAL REQUIREMENTS

- FR-01: Reject unknown fields, invalid enum/type/units/scope and ambiguous configuration; missing source values remain None, never generated zeros/identifiers.
- FR-02: Preserve distinct gross/net/chargeable values, actual pieces, units and source scope. Missing necessary unit/type/scope stays explicit and ineligible for required-source use.
- FR-03: Preserve party roles and transport references separately; do not infer importer=buyer=consignee=notify or seller=shipper.
- FR-04: A provenance claim identifies actual observed evidence; EXTRACTED requires source grounding, and no weighing record/time/measurement ID is generated.
- FR-05: Unclear shipment, master/house relationship, revision or active selection cannot become trusted eligibility by confidence or upload order.
- NFR-01: CWD-independent configuration, deterministic validation, immutable configuration and no shared mutable defaults; no IO at import.
- NFR-02: No network/model/parser/DB operation in contract tests; no sensitive logs or new dependency without approval.

## 6. BUSINESS RULES

INTERNAL_POLICY `OP-AN-DECL` v1 (2026-10-30), rule IDs from ADR-004: OP-AIR-01 requires AIR AN actual pieces/gross without a weigh-ticket prerequisite; OP-SEA-01 requires AN loading-place indicator with exact place definition/catalog; OP-SEA-02 makes SEA B/L totals eligible only when matching AN, with no automatic winner on conflict. OP-GATE-01 preserves eligibility uncertainty. Contracts retain evidence for later rule enforcement; they do not implement readiness/PASS. Missing required AN or critical unsupported data later yields NOT_CHECKED + BLOCK rather than Bill fallback under OP-READY-01.

## 7. DATA MODEL / VERSION IMPACT AND EXPECTED FILES

Future approved modules may include domain AN contracts, extraction AN config/results and focused tests. Exact files are a reviewed design output. Current canonical `0.1`, existing envelope v1 Invoice/v2 Packing, planned v3 Transport and DB schema/migration version are independent axes. Do not assign an AN envelope version. Canonical aggregate/enum/origin or migration changes require explicit Leader approval and an ADR update; technical approval of this document is not permission to invent fields during coding. Old rows and source/correction history must remain readable and unmodified.

## 8. CONSTRAINTS AND EDGE CASES

Preserve completed TASK-006/007/008. Test leading zeros/casing, zero values, exact Decimal scale, valid/ambiguous dates, master AN versus HAWB scope, chargeable-only AN, missing unit, different unit with no conversion evidence, conflicting revisions, computed values and manual correction provenance. No default Bill precedence, averaging, fabricated measurement evidence or automatic declaration edit.

## 9. ACCEPTANCE CRITERIA

- [ ] AC-01: Leader approves exact AN contract/path set and canonical compatibility strategy before affected code changes.
- [ ] AC-02: Contracts separate kind/mode/hierarchy/context, unit/weight kind/scope and estimated/actual dates; strict unknown/type/configuration failures are tested.
- [ ] AC-03: Document/extraction/field/location lineage, raw identifiers, correction/revision uncertainty and derived-value lineage survive serialization.
- [ ] AC-04: AN is separate from TransportDocument; no TASK-008 alias/validator expansion or implicit AN envelope version.
- [ ] AC-05: Invoice v1/Packing v2/completed Transport v3 and canonical compatibility tests pass; full regression independently reported.
- [ ] AC-06: No parser, classifier algorithm, service, persistence or business-rule implementation enters this child.

## 10. TEST REQUIREMENTS

Unit: strict fields/configuration, enum/type/Decimal/date and unknown-key failures, origin/provenance/derived lineage, mutable-default isolation. Integration: in-memory serialization/schema compatibility only; file parsing and database integration not required for this contracts child. Failure: ambiguous units/scope/revisions, invalid source claims, chargeable substituted for gross, extra/duplicate aliases. Regression: existing canonical/Invoice/Packing/Transport contract and codec tests plus full suite. Use synthetic/anonymized fixtures; report actual counts, failures/skips/warnings/runtime.

## 11. OBSERVABILITY, COST AND SECURITY

Validation errors identify field/error codes without raw confidential contents. AI allowed: NO. Do not open uploaded files, execute formulas/macros, call network/providers or expose customer documents. Test artifacts must be synthetic; no production DB changes.

## 12. DEPENDENCIES, DELIVERABLES AND DONE

Blocked from implementation until header dependencies and explicit design approval are satisfied. Deliver approved proposal/ADR, contracts/configuration, focused and full regression evidence, docs, source-diff/self-review and limitations. Done requires all ACs, no unresolved critical/high issues, Antigravity APPROVE, Leader approval and Owner-controlled merge/closure before 016B. No present approval or runtime success is claimed.

## 13. DEVELOPER / REVIEW / LEADER NOTES

Planning only; TODO. Technical design approval and independent review pending.
