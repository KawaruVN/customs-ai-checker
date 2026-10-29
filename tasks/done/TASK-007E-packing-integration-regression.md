# TASK-007E — Packing List Integration & Regression

Status: DONE  
Priority: P1  
Parent: TASK-007  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA (APPROVE)  
Final Approver: ChatGPT — Project Leader / Architect (APPROVE FOR MERGE)  
Completed date: 2026-10-29  
Pull Request: PR #11 (Merged into main)  
Implementation Commit: `8cf5b3fbc491303856f195e5f17d75cdc3cf32b9`  
Merge Commit: `6d603511243c02d4a913a1a9979f1bf9fe41085d`  
Pre-task baseline: 1327 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 1422 passed / 0 failed / 0 skipped / 2 warnings  
Dependencies: TASK-007D approved and merged

## Objective and inputs

Verify the complete approved Packing pipeline through real production composition
and isolated synthetic fixtures. Use the exact latest approved baseline, not an
assumed test count. Implementation is authorized by the TASK-007E handoff and
remains an integration/regression task, not a feature expansion.

## In scope and output

- SourceDocument/classification, readonly parse, approved visual safety,
  deterministic Packing header/Excel items, canonical assembly and persistence.
- Real native PDF, XLSX/XLS, controlled local safe/unsafe visual cases and fresh
  repository active/history reads.
- Exact measured regression evidence and clearly disclosed minimal defect fixes.

## Safety invariants

No source mutation, fabricated item rows, scalar reduction of invoice references,
package/quantity/weight/role conflation or unverified visual evidence. Preserve raw
text and source page/sheet/cell, Decimal/date types and leading-zero identifiers.
PDF item recognition remains unsupported unless a separate approved task adds it.
No actual customer files, production DB, hosted calls or sensitive routine logs.

## Acceptance and tests

- Production-path tests cover legitimate Packing Lists and wrong/unknown types,
  missing/ambiguous fields, formulas, hidden/competing tables and visual conflicts.
- Document totals and item weights/quantities remain distinct, and all Invoice
  references survive canonical/persistence round-trip as a list.
- Explicit replacement preserves history; stale source/active guards and injected
  persistence failures leave committed state atomic and prior active data intact.
- Source SHA-256 and log privacy checks pass; no import-time remote/model activity
  or application SQL is introduced.
- All earlier Packing and Invoice tests pass; collected/passed/failed/skipped/
  warnings/runtime and environment are independently measured and reported.

## Defects, exclusions and closure

Prove defects with failing tests and apply only minimal backward-compatible fixes
at their owning boundary. Escalate architecture/security changes rather than
weakening assertions. No new extraction features, matching, normalization, rules,
provider SDKs, UI or endpoints. Passing tests alone does not close TASK-007:
Antigravity review, Project Leader approval and approved merges are required.

## Verified pre-flight

Repository: P:\customs-ai-checker\customs-ai-checker.
Branch: task/007e-packing-integration-regression.
Initial HEAD/main ancestor: d5039cc9a003e35cc51ae3ce82df8946a807ea67
(docs: close TASK-007D and prepare TASK-007E), verified by merge-base ancestry.
Local main matched HEAD and main..HEAD was empty. Working tree/index were clean,
including untracked files. TASK-007A/B/C/D existed under tasks/done with DONE;
the parent Epic remained IN_PROGRESS and E was TODO.

Before edits, the entire approved baseline independently measured 1327 passed,
0 failed/skipped, 2 warnings in 29.99s. No prerequisite was bypassed.
PROJECT_CONSTITUTION, MASTER_SPEC, ARCHITECTURE, DATA_SCHEMA, parent/child specs,
completed TASK-006F and ADR-003 were reviewed with actual source/interfaces.
No specification conflict required an architecture decision.

## Exact changed-file inventory

- tests/integration/conftest.py: add PackingPipeline fixture/byte generation and
  assertion helpers, reusing the existing generic native-file/upload helpers.
  Existing Invoice fixture behavior is unchanged; Packing uses a separate temp
  subdirectory so both pipelines can share one isolated SQLite test database.
- New tests/integration/test_packing_native_excel.py: 26 cases.
- New tests/integration/test_packing_visual_safety.py: 28 cases.
- New tests/integration/test_packing_cross_module_regression.py: 15 cases.
- New tests/integration/test_packing_persistence_history.py: 17 cases.
- New tests/integration/test_packing_source_security.py: 9 cases.
- src/customs_ai/classification/service.py: six-line result contract/identity
  validation fix proved red/green below; no classification scoring change.
- Move/update this task from tasks/todo to tasks/in_progress; keep IN_PROGRESS.

No existing test assertion is weakened or deleted. No canonical, parser, Packing
extractor/service, codec, repository, database, config, API, dependency, README,
parent Epic, completed task or ADR file is changed. No task/epic closure occurred.

## Real execution path and fixture inventory

Tests upload generated byte streams as FastAPI UploadFile objects through the
actual IngestionService.ingest, validate real SourceDocument/hash/status and call
build_classification_service().classify_document. They then call
build_packing_extraction_service().extract_document, using approved read-only
parsing, native/visual PDF gates and deterministic extractors. Results cross the
actual codec and document_extractions transaction path before fresh repository
get_active, get_by_extraction_id and list_history checks. No endpoint is claimed
to have been tested or added.

Fixture helpers generate inputs and assert outputs; they do not duplicate business
extraction. Data includes real standard-font one/two-page native PDFs, blank/mixed
PDF pages for controlled local visual I/O, openpyxl XLSX and xlwt XLS with true OLE
signature. All inputs are synthetic. Actual bytes enter the upload directory; SHA
is compared before/after ingestion, classification/extraction and persistence.

Packing workbook samples contain all 16 header paths, two separately labelled
Invoice references, all seven item columns and two business rows. EN/VI/ZH labels
and Unicode values, leading zeros, zero, negatives, high-precision/scaled Decimals,
explicit dates and native datetime/float values are exercised. Tables are also
shifted across rows/columns and placed after a visible cover worksheet.

Every committed integration workflow checks status/issues, actual canonical values,
source ID and page or sheet/cell, active/history/by-ID retrieval and source hashes.
Native/Excel helpers additionally inspect actual parser selection (pypdf/openpyxl/
xlrd), read-only source metadata and exact value-cell coordinates. Round-trip
helpers compare Decimal tuples/types, date types, candidate typed-value types,
Unicode, raw source and the persisted (2, packing_list) envelope/schema_version0.1.

## Integration matrix and evidence

| Group | Executed production evidence |
|---|---|
| A — Native PDF | Real 1/2-page PDF, all 16 headers, exact pages/raw/date/Decimal/reference list, zero visual I/O and zero PDF-item calls |
| B — XLSX | All headers/items, two rows, offsets/later worksheet, native types, extra columns, hidden B:D/row/sheet, formulas, merged/duplicate/competing tables, ambiguous quantities and summary words |
| C — XLS | True OLE signature, xlrd selection, EN/VI/ZH raw identifiers and canonical values through actual SQLite |
| D — Classification | Real content versus misleading filename, Invoice/wrong/unknown/weak types, inconsistent stored metadata, unclassified source, unsupported CSV and wrong-ID/nonfinite classifier fault |
| E — Visual | Real VisualResolutionService quality/reconciler with renderer/provider I/O doubles only; native zero calls, one render/provider pass per visual page per stage, safe single/cross-provider and unsafe/malformed/mixed results |
| F — Canonical | Exact all-field values/locations, explicit party roles, count/package/quantity and document/item gross/net separation, missing date/unit preserved, no fabricated/moved rows |
| G — Codec/SQLite | Fresh repository reconstruction, list references/items, types/scale/Unicode/raw, actual wire pair (2, packing_list), schema0.1, v1 Invoice bytes unchanged in same database |
| H — Lifecycle | Explicit review/success replacement, failed inactive attempt preserving active, retry, missing/stale guards, source snapshot races, concurrent writers, five trigger abort positions and commit rollback |
| I — Security/privacy | Source bytes, relative traversal, real resolved directory-link escape, missing/changed file, identity substitution and sanitized parser/extractor/classifier/SQL/commit faults; no application SQL |
| J — Invoice | All existing real Invoice native PDF/XLSX/XLS, semantic/history/visual integration tests and complete old regression run unchanged |
| K — Composition | Actual factories with native enabled vision do not load engines or connect; fresh subprocess creates no DB/upload directory, worker thread or hosted SDK/network activity |

PDF output always has items=[] and explicit PDF_PACKING_ITEMS_UNSUPPORTED. Safe
headers commit NEEDS_REVIEW; unsafe visual content commits empty review only after
verified-source preflight or refuses earlier when classification is unknown.
No unsupported PDF item extraction is invoked.

Classification and extraction are separate production stages. Controlled scan
tests count one render and one call to each local provider per visual page in
each stage. They deliberately do not assert an unimplemented cross-stage cache.
Only renderer/provider I/O is doubled; quality/reconciliation remains real.

For Excel, supported clean tables can yield EXTRACTED; any component review issue
remains sticky. Quantity/weight formulas retain expression candidates and no
trusted field. Hidden source data, merged ownership, duplicate or competing table
ambiguity never becomes invented trusted rows. Raw document totals and item values
are deliberately different and checked individually, not merely non-null.

## Proven defects and minimal correction

### E-01 — HIGH: classification result identity not bound before metadata update

Owning module: classification/service.py, DocumentClassificationService.
A controlled fault wrapped the real classifier after real ingestion/parsing and
changed only the returned document_id. The service previously accepted the result
and could authorize classification metadata on the requested source despite the
returned identity belonging elsewhere.

### E-02 — MEDIUM: mutated NaN classification confidence not revalidated

The same real production boundary accepted a model whose confidence had been
mutated to NaN after initial Pydantic construction. It could write classification
metadata without satisfying its declared typed/finite confidence contract. The
probe demonstrates unsafe metadata authorization, not fabricated business fields.

Before source edits, the two focused regressions failed (2 failed, 13 deselected,
0 skipped/warnings, 0.34s). The minimal six-line correction revalidates a detached
DocumentClassificationResult snapshot and requires result.document_id to equal
the requested ID before metadata is written. Existing configured scoring, labels,
confidence thresholds, visual policy and schema remain unchanged. This enforces
existing contracts within the handoff's bounded defect policy; it does not add
new classification semantics or a new security/visual trust policy.

After correction, all 15 cross-module cases passed (2.48s developer run; 2.46s
development check). Related classification/ingestion/parser/repository tests pass,
and full regression is recorded below. No existing test or fixture was excluded
to conceal either defect. Classification-stage parsing may reach PARSED on failure
as already designed; it cannot mark the invalid result CLASSIFIED. Extraction's
separate read-only parsing remains non-downgrading.

## Test-environment findings and limits

- The initial new dual-pipeline fixture had one setup error from sharing the same
  temp directory. Only the new Packing helper was corrected to use its own
  subdirectory; the old Invoice fixture and assertions remain unchanged.
- This Windows account lacks symbolic-link creation privilege (WinError1314).
  The directory-link escape test first attempts a real symlink and, on that exact
  permission error only, creates/asserts a real NTFS junction with the same outside
  target. Containment, matching-hash refusal and immutable-source assertions stay
  unchanged; no test is skipped. A true IO_REPARSE_TAG_SYMLINK creation path was
  not validated on this account; rerun under an account with that privilege for
  that exact link variant. Junction/link resources are explicitly removed.
- A sandboxed related-unit run stalled at Windows asyncio initialization and was
  cancelled. The complete required group was rerun in the approved local runtime
  and measured; the uncompleted run is not reported as passing.
- XLS cached BIFF formula provenance is an inherited parser limit. A real xlwt
  formula fixture proves the approved parser exposes its empty cache without an
  is_formula flag/expression; output quantity stays None and is never evaluated
  or filled with 2. Tests do not invent unavailable flags or weaken policy to
  compensate. Unicode uses
  genuine XLS/XLSX; standard-font native PDF fixtures use supported Latin text.
- No cross-stage OCR cache, PDF item tables, semantic Packing extraction,
  matching, unit conversion, business reconciliation, customs rules, endpoint,
  UI or background work is introduced. Conservative B/C coverage remains as
  documented; source hashes bracket processing rather than locking external files
  indefinitely. Codec validation remains structural, not cryptographic integrity.

## Final measured execution

Environment: Windows / Python3.13.14 / pytest9.1.1. All commands use
`python -B -m pytest`, `-p no:cacheprovider` and a unique external basetemp under
the authorized visualization workspace. Full/new E2E/async ingestion groups run
in the approved local Windows runtime, with temporary SQLite/uploads only.

| Required execution | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-change full baseline `-q` | 1327 | 1327 | 0 | 0 | 2 | 29.99s |
| Final five new Packing E2E files `-q` | 95 | 95 | 0 | 0 | 0 | 13.18s |
| Existing Packing A/B/C/D unit files `-q` | 703 | 703 | 0 | 0 | 0 | 13.70s |
| Existing Invoice integration files `-q` | 50 | 50 | 0 | 0 | 0 | 6.42s |
| Classification/ingestion/parser/repository unit groups `-q` | 318 | 318 | 0 | 0 | 0 | 5.51s |
| Final global `--collect-only -q` | 1422 | — | — | — | 2 | 1.28s |
| Final full `-v` | 1422 | 1422 | 0 | 0 | 2 | 44.60s |

New counts by actual file: native_excel26 + visual_safety28 + cross_module15 +
persistence_history17 + source_security9 =95. Existing 1327 tests remain present
and unchanged; only new fixture helpers are added alongside the old Invoice
fixture. The two warnings remain the existing Starlette/httpx and AnyIO
BlockingPortal deprecations. Intermediate narrower runs are development evidence,
not a substitute for the final full execution.

Scopes: new E2E files are the five paths in the inventory above. Existing Packing
unit scope is every tests/unit/**/test_packing_*.py file. Existing Invoice scope is
test_invoice_native_excel.py, test_invoice_semantic_history.py and
test_invoice_visual_safety.py under tests/integration. Related unit scope is
tests/unit/classification, ingestion, parsers and repositories. These overlapping
groups are not added together to claim a unique suite count; only global pytest
collection determines the final total.

No production/test source changed after final execution. Diff whitespace and
conflict-marker checks pass; the index stays empty and branch/HEAD remain the
verified pre-flight values. Connection, image, thread, subprocess and directory-link
resources close through their test contexts. Only isolated synthetic test runtime
directories created for this task are eligible for final cleanup, never source
documents in the project, approved data or unrelated artifacts.
After all runs completed, 19 task-owned external pytest runtime directories were
verified inside the authorized scratch root, checked for remaining reparse points
and removed. Test code and measured evidence remain in this task; no synthetic
runtime database/upload directory was left by these runs.

## Epic acceptance evidence — developer checklist, not closure

- [x] 007A configuration/canonical contracts: unchanged and existing Packing regressions green.
- [x] 007B headers: all 16 fields and source locations through real PDF/XLSX/XLS.
- [x] 007C Excel items: seven fields, real layouts and conservative negative cases.
- [x] 007D service/persistence: actual factories, v2 storage, fresh reads and lifecycle.
- [x] 007E genuine production integration: byte upload to active/history retrieval.
- [x] No fabricated business values: actual raw/normalized/missing/type/role assertions.
- [x] EN/VI/ZH source evidence retained: real XLS/XLSX round-trips.
- [x] Dates and Decimals survive persistence: typed values and tuple/scale checks.
- [x] Invoice references remain list-valued: independent labels/provenance retained.
- [x] PDF items unsupported behavior explicit: empty items, review and no item calls.
- [x] Unsafe visual evidence cannot become trusted: whole-document abstention/fault matrix.
- [x] Source bytes unchanged: before/after SHA; intentional fault mutations are detected, not overwritten.
- [x] Active/history invariants: explicit replacements, inactive FAILED, CAS, races and rollback.
- [x] Invoice regression green: required old integration and complete baseline tests unchanged.
- [x] No unauthorized new features: tests plus bounded classification contract fix only.
- [x] No unresolved CRITICAL/HIGH defect identified in developer verification; E-01 corrected.

This is evidence for later independent review and Project Leader closure. It does
not approve or close TASK-007E or the parent Epic; both remain IN_PROGRESS.

## Independent-review probes and Git boundary

Antigravity should independently repeat wrong-ID/NaN metadata faults, actual source
raw/typed/coordinate comparisons, hidden B:D and formula/merged cases, safe/native
versus malformed/mixed visual resolution and call counts, cross-stage metadata
changes, two-writer replacement, trigger/commit rollback and mixed v1/v2 histories.
Repeat directory-link containment with native symlink privilege where available.
Inspect the fresh-process side-effect assertions and privacy sentinels.

No commit, push, PR, merge or task/epic closure is performed. Parent Epic and README
are unchanged. Suggested owner commit summary:
TASK-007E: integrate packing extraction and complete regression.

## Task closure and sign-off

- Status: DONE
- Completed: 2026-10-29
- Developer: Codex — Main Developer
- Independent Technical Reviewer: Antigravity — QA & Reviewer (APPROVE)
- Final Approval Authority: ChatGPT — Project Leader / Architect (APPROVE FOR MERGE)
- Pull Request: #11 merged into main
- Implementation commit: `8cf5b3fbc491303856f195e5f17d75cdc3cf32b9`
- Merge commit: `6d603511243c02d4a913a1a9979f1bf9fe41085d`
- Merge timestamp: `2026-10-29T22:25:49+07:00`
- Full test evidence: 1422 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1 in 63.49s).
- 95 new integration tests added across 5 files:
  - `tests/integration/test_packing_native_excel.py`: 26 passed
  - `tests/integration/test_packing_visual_safety.py`: 28 passed
  - `tests/integration/test_packing_cross_module_regression.py`: 15 passed
  - `tests/integration/test_packing_persistence_history.py`: 17 passed
  - `tests/integration/test_packing_source_security.py`: 9 passed
- Independent adversarial probes: 49/50 scenarios PASS, 1 NOT RUN (A34 native symlink variant due to Windows unprivileged account `WinError 1314` constraint; real NTFS directory junction alternative verified PASS).
- Production bug fixes:
  - E-01: Classification result identity check in `src/customs_ai/classification/service.py`.
  - E-02: Mutated NaN classification confidence revalidation.
- Preserved developer implementation evidence, integration test matrix, and known limitations.
- No unresolved CRITICAL/HIGH findings.
