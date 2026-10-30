# TASK-016B — Arrival Notice Classification & Extraction

Status: TODO
Priority: P1
Parent: TASK-016
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: TASK-016A approved, merged and closed; separately approved classifier changes
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE AND BACKGROUND

Extract observed SEA/AIR AN data through strict approved 016A contracts, keeping uncertainty visible and preventing AN/Bill confusion. Follow the [parent](TASK-016-arrival-notice-evidence.md), [contracts child](TASK-016A-arrival-contracts-compatibility.md), [inventory](../../docs/DOCUMENT_INVENTORY.md), [schema](../../docs/DATA_SCHEMA.md) and [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md). This is a TODO plan; no classifier or extractor is implemented by the docs amendment.

## 2. SCOPE

- Implement only the exact approved SEA/AIR AN kind/mode classifier contract and conservative deterministic extraction of the 016A field set from approved local PDF/XLSX/XLS content.
- Distinguish AN identity from referenced B/L/MAWB/HAWB numbers; preserve both without assigning AN to the Bill family. Refuse unsupported kinds/modes and uncertain content authorization.
- Extract parties, referenced shipment identity, actual pieces, weight kinds/units, places, vessel/voyage or flight, containers, estimated/actual date kinds and explicit revision evidence where grounded in source.
- Preserve each raw candidate/location and conflict; do not resolve competing source values by majority vote or confidence. Hidden/formula or unverified visual evidence cannot become trusted data.
- Mark unsupported/missing/unclear values and scope explicitly for service and later checks; no business PASS outcome.

## 3. OUT OF SCOPE

Service orchestration/DB codec/writes (016C), declaration comparison, required-source decision engine, normalization/conversion engine, relationship/item matching, exception acceptance, correction UI, auto-editing declaration, hosted AI, new file formats, ROAD/RAIL/MULTIMODAL extraction, AN aliases in TASK-008 or implicit Sea Waybill authorization.

## 4. INPUT / OUTPUT

Input: approved classified content and source ID, 016A strict config/results, existing local parser outputs with page/cell geometry and quality metadata. Output: typed ArrivalNotice result with exact raw/typed field evidence, candidates/issues and conservative extraction status. A matching reference is evidence, not proof of same shipment or master/house equivalence. No repository side effects.

## 5. FUNCTIONAL REQUIREMENTS

- FR-01: Exact AN kind and SEA/AIR mode require observed evidence; filenames or a Bill/AWB substring cannot authorize another family. Unsupported or mixed documents require refusal/review rather than coercion.
- FR-02: Extract label meanings without customer layout coordinates; specific labels win over generic substrings. Preserve casing/leading zeros, zero values, Decimal scale, page/sheet/cell and available geometry.
- FR-03: Keep gross/net/chargeable weight and units separate. Do not infer gross from chargeable or net; missing necessary unit stays unresolved. Do not invent weighing evidence, measurement IDs or times.
- FR-04: ETA remains estimated and actual arrival requires explicit actual evidence. Preserve place definitions and raw names; no automatic Port of Loading/Place of Receipt/storage/customs-code equivalence or catalog lookup in this child.
- FR-05: Distinguish master/house numbers and stated shipment scope, party roles and revision evidence. Upload date does not determine active revision; this extractor does not choose an active business document.
- FR-06: Two-way/three-way conflicting candidates remain sticky. Never erase source values or correction links; no average/default Bill/confidence precedence.
- FR-07: Unsafe scans, degraded/missing pages, formulas, hidden rows/columns and ambiguous merged areas fail conservatively using the approved local safety boundary. Clean native files invoke no vision; any visual integration needs explicit child approval and retained verification metadata.

## 6. BUSINESS RULES AND NON-FUNCTIONAL REQUIREMENTS

Owner INTERNAL_POLICY `OP-AN-DECL` v1 (ADR-004) governs downstream use: OP-AIR-01, OP-SEA-01/02 and OP-GATE-01. AIR AN actual pieces/gross does not require a separate weigh ticket; AWB retains identity/routing/parties/freight role. SEA AN loading-place required; B/L totals disagreement has no automatic winner. Extraction retains evidence and does not execute these decisions. No uncertain/missing data may silently become eligibility or shipment PASS. Local deterministic processing, bounded resources, no import IO/new dependencies and private static error messages are required.

## 7. DATA MODEL IMPACT, EXPECTED MODULES AND CONSTRAINTS

Use only 016A-approved contracts; future classification/extraction modules and unit tests are expected, exact paths approved in the handoff. No unreviewed canonical field/enum, origin, DB or envelope changes. Canonical version, envelope and DB version are distinct; current v1/v2 and completed Transport v3 remain compatible, and no AN envelope number is assigned here. Preserve all completed TASK-006/007/008 algorithms unless a separately approved defect fix is necessary.

## 8. EDGE CASES

AN titled with AWB reference; AWB titled with arrival text; mixed content; master AN and house shipment; two revisions without active evidence; chargeable-only weight; zero values; unknown unit; ambiguous number/date; multiple ports; SEA loading place versus storage location; party address mistaken for party name; hidden grouped columns; formulas/cached values; conflicting three candidates; unsafe PDF page; no weigh ticket.

## 9. ACCEPTANCE CRITERIA

- [ ] AC-01: Authorized SEA/AIR AN extracts through the approved strict contract; AN containing AWB/Bill number never routes as AWB/B/L solely from that reference.
- [ ] AC-02: Missing/ambiguous unit, weight kind, date kind, scope or revision evidence remains explicit and cannot supply a trusted substituted value.
- [ ] AC-03: Every EXTRACTED field has exact source grounding, raw value and physical provenance; candidate conflicts and zero/leading-zero values survive.
- [ ] AC-04: Unsafe visual, formula and hidden Excel data cannot become trusted extraction; clean native files use no vision.
- [ ] AC-05: No source mutation, invented measurements, automatic source winner, declaration edit, DB write or later-task implementation.
- [ ] AC-06: Focused classifier/extractor and full regression pass with actual counts/runtime/warnings; Invoice/Packing/Transport behavior remains compatible.

## 10. TEST REQUIREMENTS

Unit: label boundaries, strict data/provenance validation, date/Decimal ambiguity, units/kinds/scope and sticky conflicts. Integration: real synthetic native PDF/XLSX/XLS through local parser + extractor, shifted layouts and source hashes; DB integration not required here. Failure: every edge case above plus unsupported kinds/modes, corrupted source and provider failures if approved visual boundary is used. Regression: full Invoice/Packing/Transport suite and full pytest. Report collected/passed/failed/skipped/warnings/runtime; documentation scenarios are not a substitute for runtime tests.

## 11. TEST DATA, OBSERVABILITY, COST AND SECURITY

Synthetic/anonymized data only. Logs: document/task/error/status and contract/policy versions, no party/cargo full text or raw exceptions. AI allowed: no hosted AI; existing local visual resolution only when explicitly authorized and quality-verified, otherwise abstain. No formula/macro execution, file mutation, external paths or new dependencies without approval.

## 12. DEPENDENCIES, DELIVERABLES AND DONE

Do not start until 016A closure and Leader classifier authorization. Deliver extractor/classifier changes limited to approved design, adversarial tests, actual focused/full results, docs and known limitations. Done requires all ACs, no unresolved critical/high issues, Antigravity APPROVE and Leader/Owner-controlled merge/closure before 016C.

## 13. DEVELOPER / REVIEW / LEADER NOTES

Planning only; TODO. Technical authorization, implementation and review pending.
