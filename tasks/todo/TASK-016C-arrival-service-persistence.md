# TASK-016C — Arrival Notice Service & Persistence

Status: TODO
Priority: P1
Parent: TASK-016
Developer: Codex — Main Developer
Reviewer: Antigravity — Independent Technical Reviewer / QA
Final Approver: ChatGPT — Project Leader / Architect
Created: 2026-10-30
Updated: 2026-10-30
Target Version: V1
Dependencies: TASK-016B approved, merged and closed; explicit Leader codec/persistence design approval
Related ADR: [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md)

## 1. OBJECTIVE AND BACKGROUND

Compose approved AN extraction behind a safe application boundary and persist validated evidence/history without disturbing Invoice, Packing or Transport data. Follow [TASK-016](TASK-016-arrival-notice-evidence.md), [016A](TASK-016A-arrival-contracts-compatibility.md), [016B](TASK-016B-arrival-classification-extraction.md), existing ADR-001..003, [schema](../../docs/DATA_SCHEMA.md), [inventory](../../docs/DOCUMENT_INVENTORY.md) and [field matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md). Design is proposed, not current runtime support.

## 2. SCOPE

- Propose exact AN service outcome, discriminator/codec, historical family validation and any migration impact for Leader approval before implementation. No envelope number is reserved by this task plan.
- Compose secure source loading/hash verification, non-mutating parse-once, exact AN kind/mode authorization and approved extraction; unsafe/uncertain content remains reviewable/refused.
- Reuse the established repository transaction/history mechanism where compatible. Preserve explicit replacement, per-document attempts, one-active invariant, CAS and failure rollback semantics.
- Retain raw and typed evidence, location/extraction lineage, revisions/corrections and contract/policy metadata. Per-file active extraction must not select the active business revision across files.
- Expose safe typed outcomes distinguishing refusal, uncommitted persistence failure, committed failed attempt, reviewable active evidence and observed active record.

## 3. OUT OF SCOPE

Required-source winner/rule execution, document relationship/active revision resolution engine, declaration comparison or edits, exception UI, API/routes/jobs, report generation, normalization and new transport modes. Do not treat successful persistence as AN validity, reconciliation or shipment PASS.

## 4. INPUT / OUTPUT

Input: authoritative source ID, expected source snapshot/hash/status and explicit expected active extraction ID when replacing, approved AN contract/extractor and local repository. Output: typed service outcome and validated persisted AN attempt/history if allowed; all source bytes and previous records retained. A refusal must not create an attempt; a verified-source execution failure follows approved failure-history semantics, and a persistence failure must not trigger a second save.

## 5. FUNCTIONAL REQUIREMENTS

- FR-01: Secure source paths/size/hash and stored/current content authorization are independently checked; metadata or filename alone cannot route AN. No AN may persist as transport merely because it contains AWB/Bill references.
- FR-02: Revalidate detached result snapshots, exact source lineage and approved typed values before write and on read; unknown/malformed payloads fail closed without raw customer-data logging.
- FR-03: Define source/result family checks, CAS, attempt sequence, single-active and failed replacement behavior under the existing atomic transaction boundary; concurrency must not silently replace history.
- FR-04: Old extraction rows remain readable independent of later mutable source classification; reclassification cannot authorize cross-family active replacement.
- FR-05: Separate extraction active state from active document revision evidence. Unknown shipment/master-house scope, necessary unit/weight kind or active revision remains explicit for downstream OP-GATE-01; no Bill fallback or fabricated measurement evidence.
- FR-06: Preserve all original values/corrections and source-decision lineage references; derived values cannot be stored as EXTRACTED. Store only approved policy metadata and do not execute future policy engine here.
- FR-07: Source changes detected during processing or CAS mismatch refuse safely; persistence errors roll back and preserve prior active data. Hash bracketing is not an indefinite lock against arbitrary external file writes.

## 6. BUSINESS AND NON-FUNCTIONAL REQUIREMENTS

Owner INTERNAL_POLICY `OP-AN-DECL` v1 (ADR-004) is evidence context; AN priority does not imply deletion of AWB/B/L conflicts. AIR pieces/gross needs matching valid AN, no separate weigh-ticket prerequisite. SEA loading place is AN-based, sea totals conflict has no winner. Critical unsupported coverage cannot become shipment PASS. Reuse local deterministic mechanisms, private errors, lazy factories and bounded work; no hosted providers or new dependencies without approval.

## 7. MODEL / VERSION / MIGRATION IMPACT AND EXPECTED MODULES

Future approved extraction service, codec/repository integration and focused tests are expected. Canonical schema `0.1`, current Invoice v1/Packing v2, completed Transport v3 and DB schema/migration version are independent. Select AN discriminator/version only through explicit reviewed design, not the next integer by assumption. Any canonical/DDL changes require explicit ADR/migration approval; reusing existing payload storage must still be justified and tested. Never rewrite legacy rows to adopt AN or apply new coercion rules to old valid envelopes.

## 8. CONSTRAINTS AND EDGE CASES

Preserve completed TASK-006/007/008. Cover changed hash/path/classification with unchanged processing status, stale active ID, concurrent writes, unknown discriminator/version, corrupt/duplicate JSON keys, nonfinite Decimal, missing source, reclassification, failed replacement, commit failure, wrong-family output and mixed/cross-document provenance. No declaration auto-edit, no automatic revision precedence by upload order.

## 9. ACCEPTANCE CRITERIA

- [ ] AC-01: Leader approves AN envelope/service/repository/migration design before affected implementation; versions remain separate and existing wire formats remain readable.
- [ ] AC-02: Correct SEA/AIR AN persists/retrieves losslessly with source/extraction/field/location lineage, raw casing/identifiers, Decimal/date/unit/scope and issues intact.
- [ ] AC-03: Wrong kind/mode, source mismatch and invalid source state refuse with zero write; embedded AWB reference cannot authorize transport-family storage.
- [ ] AC-04: CAS, attempts, single-active, failed history/replacement, rollback and race behavior preserve prior data and do not reinterpret active extraction as active revision.
- [ ] AC-05: Existing Invoice v1/Packing v2/completed Transport v3 coexists unchanged; source files/hashes and original/correction history are retained.
- [ ] AC-06: Focused and full regression are independently reproducible, no unresolved critical/high blockers and no business PASS/exception/declaration editing implementation.

## 10. TEST REQUIREMENTS

Unit: orchestration, authorization, no import/factory side effects, malformed nested output and source lineage. Integration: real repository fresh-read round-trip, mixed-family history and concurrent CAS transactions. Failure: refused versus FAILED versus persistence failure, rollback at each transaction stage, corrupt envelopes, wrong family/classification and source mutations. Regression: all existing v1/v2/v3 codec/repository/service tests plus full suite. Report actual collected/pass/fail/skip/warnings/runtime. Synthetic SQLite databases only; never production DB.

## 11. OBSERVABILITY, COST AND SECURITY

Audit document/extraction IDs, attempt, method/contract/codec/policy versions, status and error codes; customer text, SQL parameters, paths and raw provider exceptions do not enter standard logs. AI allowed: no hosted AI; only explicitly authorized existing local visual boundary. Bound SQL parameters, validate untrusted JSON, no eval/pickle/dynamic imports, formulas/macros, source writes or silent retry. Local storage confidentiality/encryption limitations must be documented honestly.

## 12. DEPENDENCIES, DELIVERABLES AND DONE

Do not start until 016B closure and explicit technical approval. Deliver reviewed service/persistence changes, migration only if approved, focused/full evidence, source-diff/self-review, docs and limits. Done requires ACs, Antigravity APPROVE, Leader approval and Owner merge/closure before 016D.

## 13. DEVELOPER / REVIEW / LEADER NOTES

Planning only; TODO. No AN envelope number, schema migration or runtime availability approved here.
