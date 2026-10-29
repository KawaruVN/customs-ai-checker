# TASK-007A — Packing List Extraction Foundation & Contracts

Status: DONE  
Priority: P1  
Parent: TASK-007  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Created: 2026-10-29  
Completed: 2026-10-29  
Merged PR: #7 (commit `57957a43bee76bb3e89c8afd30b06311650780c1`)  
Dependencies: TASK-006 DONE  
Pre-task baseline: 616 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 697 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)  
Independent adversarial probes: 27/27 PASS

## Objective

Establish Packing List configuration and provider-neutral result contracts for
future deterministic extraction, without implementing document interpretation.

## Authoritative inputs

Follow PROJECT_CONSTITUTION.md, MASTER_SPEC.md, ARCHITECTURE.md and
docs/DATA_SCHEMA.md. Existing `PackingList`, `PackingItem`, `CanonicalField`,
`Party` and `ValueOrigin` models are the canonical source of truth. Preserve the
completed TASK-006 implementation and use its normalization, lexical parsing,
issue and candidate primitives where appropriate.

## In scope and outputs

- `config/packing_extraction.yaml`: customer-neutral EN/VI/ZH aliases.
- `src/customs_ai/extraction/packing_config.py`: isolated strict configuration
  contract and CWD-independent loader, with approved header/item path sets.
- `src/customs_ai/extraction/packing_models.py`: strict header and item result
  contracts reusing the canonical Packing types and approved extraction primitives.
- Focused synthetic unit tests and TASK-007 epic/child planning documents.

The 16 header paths are `packing_list_number`, `date`, `seller.name`,
`seller.tax_id`, `seller.address`, `buyer.name`, `buyer.tax_id`, `buyer.address`,
`shipment_reference`, `invoice_references`, `package_count`, `package_type`,
`gross_weight`, `net_weight`, `dimensions` and `volume`.

The seven item paths are `item_code`, `description`, `quantity`, `unit`,
`package_number`, `gross_weight` and `net_weight`. Header and item aliases are
separate contexts. `invoice_references` continues to be a list of canonical
string fields; no scalar replacement or alternate Packing schema is introduced.

## Configuration and role policy

Require exact approved path coverage in both contexts. Reject unknown/missing
keys, malformed shapes, empty/blank/non-string aliases, repeated normalized
aliases and cross-field alias collisions within a context. Reuse approved alias
normalization: case-insensitive comparison after trimming/collapsing whitespace;
punctuation and Unicode distinctions are not silently collapsed by a new policy.

Keep seller/buyer roles separate from shipper, consignee, exporter and importer.
Do not conflate package counts with item quantities or package identifiers,
gross with net weight, or dimensions with volume. Aliases shared across distinct
contexts do not authorize assigning document weights to item fields.

Prefix/specific-label matching, source grounding and document-context resolution
belong to TASK-007B/007C. This loader validates configuration, not documents.

## Result contracts and reuse

`PackingListHeaderExtractionResult` carries canonical `packing_list`, an explicit
ExtractionStatus, issues and candidates. `PackingItemExtractionResult` carries
canonical item rows, an explicit status, issues and candidates. Extra fields are
forbidden and missing values are not invented. Reuse ExtractionIssue and
ExtractionCandidate, preserving their meaning and canonical EXTRACTED provenance.

Use existing `normalize_alias`, `parse_decimal` and `parse_date` rather than new
lexical parsers. Do not refactor Invoice modules merely to add Packing support.
Canonical Decimal/date and raw/provenance fields retain their existing types.

The shared candidate `typed_value` union has inherited JSON type ambiguity.
TASK-007A does not claim lossless candidate-union JSON serialization or change
SQLite codecs. Canonical typed fields and Python-mode candidate values must be
preserved; TASK-007D must define/review Packing persistence and typed serialization
before use. No candidate claim is verified against a real source in this task.

## Acceptance criteria

- [x] AC-01: Canonical Packing and Invoice fields/structures remain unchanged, except
  the Project Leader-approved correction of PackingList.date's erroneous runtime
  annotation to CanonicalField[datetime.date]. No other canonical field or database
  schema change is authorized.
- [x] AC-02: All 16 approved header and seven item paths are supported in separate
  maps, without unauthorized business fields.
- [x] AC-03: EN/VI/ZH aliases preserve seller/buyer, package/quantity, gross/net,
  dimensions/volume and Packing-number/Invoice-reference distinctions.
- [x] AC-04: Unknown/missing paths, bad shapes, duplicate/conflicting normalized
  aliases and empty/blank/non-string aliases fail validation.
- [x] AC-05: Invalid YAML fails safely and default loading is CWD-independent.
- [x] AC-06: Strict result models reuse canonical types/status/issues/candidates;
  status is explicit and uncertain/missing evidence cannot imply default success.
- [x] AC-07: Invoice references and items retain list-valued canonical contracts;
  independent instances do not share mutable defaults.
- [x] AC-08: Decimal/date, identifiers, raw data and provenance are preserved; malformed
  nested values and missing EXTRACTED provenance are rejected by the contracts.
- [x] AC-09: Focused negative tests cover the requirements and full regression keeps
  all completed TASK-006 behavior green.
- [x] AC-10: TASK-007 epic and bounded TODO plans for B–E exist; no later child is
  implemented or approved by this work.

## Tests and pre-flight evidence

Required branch: `task/007a-packing-extraction-foundation`. Initial HEAD
`6749d83054b0d7e7db39a5596d1819612f5a262d` contains the official TASK-006 closure,
TASK-006F DONE and merged PR #6. Working tree was clean before implementation.
The main developer independently verified 616 collected/passed, 0 failed,
0 skipped, 2 warnings in 18.07s (Python 3.13.14, pytest 9.1.1).

Focused tests must challenge path coverage, normalization/collisions, malformed
YAML/shapes, CWD independence, role/context separation, strict nested contracts,
list-valued references, raw/provenance and typed values. Full pytest collection
and execution provide the actual post-task count; counts must not be estimated.

Final implementation/test evidence is recorded below. These are developer
measurements, not independent approval.

## Approved annotation defect correction

The new valid-date test exposed a pre-existing canonical defect, independently
reproduced through direct PackingList construction before any canonical edit.
`PackingList.model_fields["date"].annotation` was
`CanonicalField[NoneType] | None`, so a real `datetime.date(2026, 10, 29)` failed
with `date.normalized_value: none_required`. The field's class-body name `date`
shadowed the imported date type when its annotation was evaluated. This was not
an extraction algorithm or parser failure.

The first model-focused run had 18 collected, 13 passed and 5 failed in 1.26s;
all five failed because the shared valid-date fixture hit the canonical defect.
A two-line source-copy proposal was verified in memory without altering the
repository. The developer requested approval because the original handoff
explicitly prohibited canonical changes.

Project Leader explicitly approved the strict exception: add `import datetime`
and change only PackingList.date to `CanonicalField[datetime.date] | None` in
`src/customs_ai/domain/schema.py`. No other canonical fields, names, model
structure, Invoice contracts or database schema are changed. This is an
annotation bug fix restoring the declared date contract, not schema refactoring.

Regression tests inspect the actual runtime generic annotation, directly construct
PackingList/Invoice dates, reject invalid dates/types and missing EXTRACTED
provenance, and preserve raw/source/page/sheet/cell/bounding box/method/confidence
through canonical JSON round-trip. After the approved correction all 26 model
cases pass in 1.02s; full final measurements follow below.

## Final measured validation

Environment: Windows, Python 3.13.14, pytest 9.1.1. Tests use synthetic values,
temporary YAML and isolated runtime/database directories outside the repository.
Commands use `python -B -m pytest` and `-p no:cacheprovider`; execution also uses a
unique explicit external `--basetemp`. Full-suite execution uses the local runtime
for the project's Windows asyncio/TestClient tests.

| Scope / pytest arguments | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-development baseline `-v` | 616 | 616 | 0 | 0 | 2 | 18.07s |
| Approved date/model regressions `tests/unit/extraction/test_packing_models.py -v` | 26 | 26 | 0 | 0 | 0 | 1.02s |
| Both new focused files `tests/unit/extraction/test_packing_config.py tests/unit/extraction/test_packing_models.py -v` | 81 | 81 | 0 | 0 | 0 | 1.78s |
| Global `--collect-only -q` | 697 | — | — | — | 2 | 1.46s |
| Full regression `-v` | 697 | 697 | 0 | 0 | 2 | 25.93s |

The 81 new cases comprise 55 config cases and 26 contract/date regression cases.
All 616 pre-existing tests remain present, unchanged and passing in the full run,
including the complete TASK-006 Invoice pipeline and persistence regression.
Warnings remain the existing Starlette/httpx and AnyIO BlockingPortal deprecations.

No shared Invoice config, extractors, lexical parsers, result primitives,
persistence schema/codec, README or completed TASK-006 documents were changed.
Only the explicitly approved PackingList.date annotation correction touches an
existing production file. No Packing extraction, service, matching, normalization
or hosted provider was implemented.

## Known limitations and independent audit suggestions

- Alias validation is structural and checks normalized collisions; arbitrary
  custom alias meanings are not linguistically certified. Default vocabulary
  separates the approved roles/concepts. Future B/C must establish document/table
  context and handle longest/specific labels conservatively.
- Shared normalization is case/whitespace only. ASCII/fullwidth colons and other
  punctuation/Unicode distinctions remain literal. Future matching must not
  silently introduce ambiguity by using a different normalization policy.
- Typed result models validate canonical types/provenance shape and conservative
  success conditions, not the existence or correctness of actual source text.
- Candidate typed-value JSON ambiguity is inherited and explicitly not solved by
  this task; future Packing persistence needs separately reviewed type-safe
  serialization. Canonical typed values and Python-mode candidates are tested.
- Antigravity should independently challenge malformed/duplicate YAML keys and
  aliases, CWD changes, role/count/weight/dimension collisions, list-valued Invoice
  references, nested model mutations, empty/review-required EXTRACTED results and
  the runtime date annotation plus Invoice compatibility.

## Result-validation policy

Result containers are strict, forbid extras and require explicit ExtractionStatus.
In Python-mode construction the enum is required; JSON validation accepts its
declared enum representation. Nested canonical/issue/candidate instances are
revalidated from detached snapshots, including mutated/unchecked model copies.
No new domain model or local numeric/date parser is introduced.

An explicit EXTRACTED result is rejected if no canonical values are present, a
present field remains unresolved, an empty item row exists, or review-required
issues remain. Header success cannot be established solely by item data.
NEEDS_REVIEW/FAILED may retain empty or partial results. Optional fields and lists
retain their canonical None/empty defaults. These checks do not certify document
completeness or verify claimed source material; actual extraction and grounding
remain future-task work.

## Out of scope

No actual header/item extraction, service orchestration, SQLite persistence or
codec extension, PDF table recognition, semantic provider, matching,
normalization, customs rules, HTTP/UI, migrations or customer-specific layouts.
Do not modify shared README or completed TASK-006 documentation.

## Review state

DONE — Approved by Antigravity (Independent Technical Reviewer / QA) and ChatGPT (Project Leader / Architect). Merged via Pull Request #7 (commit `57957a43bee76bb3e89c8afd30b06311650780c1`).

---

## Closure summary

- **Status**: CLOSED / DONE
- **Date**: 2026-10-29
- **Merged PR**: Pull Request #7 (commit `57957a43bee76bb3e89c8afd30b06311650780c1`)
- **Developer**: Codex — Main Developer
- **Review Decision**: Antigravity — Independent Technical Reviewer / QA — APPROVE
- **Architectural Approval**: ChatGPT — Project Leader / Architect — APPROVE
- **Authoritative Baseline after TASK-007A**: 697 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1)
- **Independent Adversarial Probes**: 27/27 PASSED
- **Next Task**: TASK-007B — Deterministic Packing List Headers (TODO)
