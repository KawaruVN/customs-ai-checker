# TASK-016D — Arrival Notice Integration & Regression

Status: TODO
Priority: P1
Parent: TASK-016
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: TASK-016C approved, merged and closed
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE AND BACKGROUND

Independently verify production-path SEA/AIR AN intake, classification, extraction, persistence and retrieval, preserving all completed document families. Follow [TASK-016](TASK-016-arrival-notice-evidence.md), [016A](TASK-016A-arrival-contracts-compatibility.md), [016B](TASK-016B-arrival-classification-extraction.md), [016C](TASK-016C-arrival-service-persistence.md), [inventory](../../docs/DOCUMENT_INVENTORY.md), [schema](../../docs/DATA_SCHEMA.md), [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md) and ADR-004. Verification is not implementation of later declaration/rule/report tasks.

## 2. SCOPE

- Exercise real authorized local files through ingestion, exact AN classification, service, approved codec/repository and fresh retrieval, using synthetic SEA/AIR layouts and languages.
- Verify negative AN/Bill/AWB kind boundaries, master/house context, unit/weight/date-kind distinctions, unresolved revisions, raw/provenance and sticky uncertainty.
- Verify source safety, private logs, refusal/attempt/history/CAS/rollback semantics and coexistence with Invoice v1, Packing v2 and completed Transport v3.
- Inventory remaining unsupported coverage and required downstream readiness blockers. Produce exact focused/full regression evidence and epic closure recommendation for Leader.

## 3. OUT OF SCOPE

Source↔declaration or document↔document business-rule execution, source winner selection, exception acceptance, declaration auto-edit, normalization engine, document relationship resolution, new extractors/modes or unapproved schema/codec refactor. Future rule scenarios remain design expectations until their authorized layer exists.

## 4. INPUT / OUTPUT

Input: approved 016A/B/C production components and synthetic AN/transport/commercial document bytes plus expected extraction/refusal/evidence outcomes. Output: adversarial integration tests, actual test result report, compatibility and immutability evidence, coverage/limits and independent review handoff. No runtime shipment PASS is inferred from extraction success.

## 5. FUNCTIONAL AND NON-FUNCTIONAL REQUIREMENTS

- FR-01: Real production-path tests must verify AN containing AWB number, standalone manifest, Sea Waybill, wrong mode/kind, wrong source ID and misleading filename cannot cross-authorize families.
- FR-02: Assert exact raw casing/leading zeros, zero values, Decimal/date and physical document/extraction/field/page or sheet/cell lineage after fresh read; preserve scope/unit/kind and unresolved revision evidence.
- FR-03: Prove chargeable-only AN does not supply gross, ETA does not supply actual arrival, absent data remains absent, and no weigh ticket/time/measurement is fabricated. Absence of a separate weigh ticket does not disqualify observed AIR AN pieces/gross under Owner policy.
- FR-04: Simulate unsafe PDF pages, grouped hidden/formula/merged Excel, source/hash changes, classifier mismatch, stale/concurrent CAS, failed replacement and commit failure; preserve prior active history and source bytes.
- FR-05: Preserve existing v1/v2/completed v3 records and full regression. Do not rely solely on mocked outcomes or developer-reported baseline.
- NFR-01: Tests are deterministic, local, isolated, bounded and use temporary databases; no hosted AI, external credentials, production data or network dependency.

## 6. BUSINESS RULES / DESIGN SCENARIO BOUNDARY

Owner INTERNAL_POLICY `OP-AN-DECL` v1 and rules in ADR-004 remain future checking requirements. Trace the 12 design walkthroughs in [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md) to evidence preserved by this epic: AIR 108/113 with both declaration values; no weigh ticket; chargeable-only AN; SEA loading-place disagreement; missing AN; master/house scope; ambiguous active revision; SEA totals disagreement; distinct parties/named exception; critical NOT_CHECKED; stale result after data changes. At this extraction layer, test evidence retention and conservative status only. Declaration comparison, exception/readiness decision and old-result invalidation runtime assertions belong to TASK-012/014 and must not be simulated as already implemented PASS tests here.

## 7. MODEL / VERSION IMPACT AND EXPECTED FILES

Expected changes are future unit/integration/regression tests and truthful docs; production fixes require separate Leader-approved defect scope and regression evidence. Use only approved AN design and do not assign a new envelope number. Canonical, extraction envelope and DB versions stay distinct; no legacy row rewrite, classifier scope expansion or DDL migration hidden in this test child.

## 8. EDGE CASES AND CONSTRAINTS

Test full native file bytes in shifted/multilingual layouts, ambiguous dates/numbers, many candidate conflicts, missing units, chargeable/net/gross labels, master AN versus HAWB, multiple document revisions, explicit actual versus estimated dates, missing pages, wrong-family historical payloads, source path escapes and confidential content logging. No new dependency or future-task implementation; unsupported critical coverage is reported for later NOT_CHECKED + BLOCK, never quietly omitted.

## 9. ACCEPTANCE CRITERIA

- [ ] AC-01: Real SEA/AIR AN production paths round-trip approved values/evidence and source bytes remain identical.
- [ ] AC-02: Exact kind/mode authorization and adversarial AN/AWB/Bill confusion tests refuse safely without inappropriate persistence side effects.
- [ ] AC-03: Units, gross/net/chargeable, actual/estimated dates, scope and revision uncertainty survive; hidden/formula/unverified evidence cannot become trusted values.
- [ ] AC-04: Refusal, history, failed replacement, concurrency, rollback, family coexistence and fresh-read tests pass without changing existing contracts.
- [ ] AC-05: Focused and full regression report collected/passed/failed/skipped/warnings/runtime; every failure/skip/warning is explained and there are no unresolved critical/high blockers.
- [ ] AC-06: Coverage/limitations and all design-scenario handoffs identify unimplemented later layers; no runtime shipment PASS or AN epic closure is claimed before Antigravity/Leader approval.

## 10. TEST REQUIREMENTS

Unit: supplement uncovered safety contract branches with meaningful assertions. Integration: real native PDF/XLSX/XLS and source repository round-trips, cross-family coexistence, lazy factory behavior and privacy. Failure: all adversarial cases above, persistence corruptions and provider failure where an approved local visual adapter is used. Regression: focused AN, Invoice, Packing, Transport and full pytest. Use synthetic/anonymized files only, no real private carrier/customer documents. Record actual commands and runtimes; reported historical baseline is not fresh verification.

## 11. OBSERVABILITY, COST AND SECURITY

Audit IDs, statuses, versions and static errors without party/cargo content or raw exceptions. AI allowed: NO external/hosted calls; deterministic native cases must prove no vision/provider use. Existing approved local visual safety may be tested using controlled failure adapters without claiming independent OCR certainty. No source writes, formula execution, public uploads or production databases.

## 12. DEPENDENCIES, DELIVERABLES AND DONE

Start only after 016C closure. Deliver adversarial tests, exact results, coverage matrix mapping, compatibility/source-hash evidence, truthful limitations and independent-review handoff. Done requires all ACs, Antigravity APPROVE, Leader approval and Owner merge/epic closure before TASK-017 begins. Do not mark the epic DONE solely because tests passed.

## 13. DEVELOPER / REVIEW / LEADER NOTES

Planning only; TODO. No runtime tests were run or implementation authorized by creation of this specification.
