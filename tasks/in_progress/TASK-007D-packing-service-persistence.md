# TASK-007D — Packing List Service & Persistence

Status: IN_PROGRESS  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007B and TASK-007C approved and merged; TASK-006D/E contracts

Developer role: Codex — Main Developer  
Reviewer role: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Development date: 2026-10-29  
Pre-task baseline: 1178 passed / 0 failed / 0 skipped / 2 warnings

## Objective and inputs

Compose approved Packing extractors from authoritative SourceDocument IDs and
provide explicitly versioned Packing persistence support. The Project Leader
approved the bounded design in the TASK-007D development handoff: reuse the table
and repository, Invoice v1 unchanged, discriminated Packing v2, zero DDL migration.
Implementation still requires independent review and final approval.

## In scope and output

- Packing-only classification gate using safe current evidence and stored metadata.
- Existing secure source path resolution, non-mutating parsing and approved visual
  safety behavior; canonical PackingList assembly and issue propagation.
- Repository-layer save/read/history and explicit replacement for Packing results,
  preserving the approved Invoice records and SQLite transaction guarantees.
- Typed service outcome distinguishing refused/uncommitted attempts from committed
  EXTRACTED, NEEDS_REVIEW and FAILED attempts.

## Safety invariants

Preserve source bytes, raw/provenance, list-valued Invoice references and typed
business values. No parser status downgrade, filename classification shortcut,
unsafe visual bypass, silent overwrite, hidden SQL in application code or
customer values/paths in logs. Reuse 006D optimistic source snapshot/active guards,
rollback and single-active/history policy where the reviewed design permits.
Latest attempt metadata and active result remain distinct. Failed replacement
must preserve prior usable active data and complete history.

## Acceptance and tests

- Only safely classified Packing Lists enter extraction; wrong types, unsafe visual
  evidence, missing sources, path escapes and stale requests fail conservatively.
- Production composition preserves header/item issues and does not infer missing
  business facts or use Invoice-only storage as an unchecked Packing envelope.
- Reviewed versioned serialization preserves canonical Decimal/date, candidate
  typed-value types, raw evidence and source IDs across actual SQLite round-trips.
- Isolated DB tests cover migration compatibility, foreign keys, one active row,
  deterministic history, explicit replacement, writer races and rollback before/
  after metadata and at commit; Invoice persistence remains backward compatible.
- No raw payload/path leakage, source mutation or duplicate unnecessary visual work.

## Out of scope and review

No hosted SDK, semantic provider implementation, PDF item recognition,
cross-document matching, normalization, rules, endpoints, UI or background jobs.
Do not redesign the database or canonical models without explicit architectural
approval. Independent review and Project Leader approval precede merge/closure.

## Verified pre-flight and source review

Repository: P:\customs-ai-checker\customs-ai-checker.
Branch: task/007d-packing-service-persistence.
Initial HEAD/main ancestor: bd7c9b61b2298d86670bcc905a705b50228cb25c
(docs: close TASK-007C and prepare TASK-007D), beyond PR #9. Local main matched
HEAD, no newer main..HEAD commits or unexplained/untracked changes existed and
the index was empty. TASK-007A/B/C were DONE, Epic IN_PROGRESS and D TODO.
Earlier wrong-branch attempts stopped without edits; all gates passed on resume.
The developer measured the complete baseline: 1178 passed, 0 failed/skipped,
2 warnings in 40.88s before implementation.

Authoritative project documents, completed TASK-006D/E/F and TASK-007A/B/C,
canonical schema, parsing/path, classification/vision, source/extraction repository
and Packing extractor/contracts were inspected. The explicit handoff authorizes
this persistence extension. The architecture decision is recorded in
docs/decisions/ADR-003-packing-service-persistence.md; no separate migration was
necessary or performed.

## Implementation inventory

New:

- src/customs_ai/application/packing_extraction.py
- src/customs_ai/application/packing_models.py
- tests/unit/application/test_packing_extraction_service.py
- tests/unit/repositories/test_packing_persistence.py
- docs/decisions/ADR-003-packing-service-persistence.md

Modified shared modules, within approved scope:

- application/composition.py: add build_packing_extraction_service only.
- repositories/extraction_models.py: Packing result union, explicit wire pairs,
  type-preserving v2 codec and result-family helper; existing v1 path retained.
- repositories/document_extractions.py: type-safe writes/replacements, stored
  application-method family checks and fail-closed corrupt read guards, using the
  existing transaction engine.

This task moved tasks/todo -> tasks/in_progress and remains IN_PROGRESS. No other
approved source/test, database.py, canonical/config/visual contract, README,
Parent Epic or completed task documentation is modified. No DDL, parallel history
table, new dependency, SQL in the application service or semantic provider exists.

## Service flow and trust boundaries

PackingExtractionRequest validates exact identifiers and optional source hash,
processing status and expected active ID. PackingExtractionOutcome exposes the
Packing result, committed record, active_record when observed, and persisted.
Nested result/record snapshots are revalidated and incompatible records rejected.

1. Load authoritative SourceDocument by exact ID; support PDF/XLS/XLSX only.
   Require stored PACKING_LIST with finite configured-threshold confidence and an
   eligible processing state. Validate any caller hash/status guards.
2. Read and revalidate the observed active record; refuse missing/stale replacement
   authorization or incompatible record family. Resolve upload-root containment
   (including resolved symlink escape), actual size and SHA-256 before parsing.
3. Parse exactly once through DocumentParsingService.parse_document_readonly.
   Identity/type must match source; no PARSED downgrade or source metadata write.
4. For native PDF, verify all pages through the approved Packing safety policy.
   Safe native text never calls vision. Otherwise resolve at most once via existing
   local infrastructure, checking document/type/count/page identity, unique exact
   visual coverage, native-page equality and verification/quality/review metadata.
5. Recheck current deterministic classification on safe content. Hidden/formula/
   partly hidden merged cells do not provide Excel clues. Compare injected
   classifier output with independently computed approved output, including ID,
   type, confidence and actual clue locations; invalid assertions refuse without
   history. Filename and sheet names cannot authorize classification.
6. Compose approved Packing components, retaining all their issues and candidates.
   Revalidate detached outputs and verify exact source raw spans/locations, safe
   source cells and normalized Decimal/date/string values. Substrings inside IDs,
   foreign provenance, unsupported contracts and fabricated values are rejected.
7. Re-read the source snapshot and fingerprint, validate through the codec, then
   call save_attempt or replace_active with full expected_source_document.
   Repository CAS repeats hash/status/snapshot/active guards under BEGIN IMMEDIATE.

Unsafe PDF resolution cannot establish trusted business fields. With verified
source preflight it is persisted as empty NEEDS_REVIEW, including explicit PDF
items unsupported status. Technical parsing/extraction failures after verified
preflight may be committed FAILED, consistent with TASK-006D/E. Classification
mismatch is always an uncommitted refusal.

## Header/item composition and evidence policy

The composed object remains PackingListHeaderExtractionResult; its PackingList
contains the existing header fields, list-valued invoice_references and approved
PackingItems. No inferred value, calculation, unit conversion or document matching.

Excel item interpretation first establishes table scope. Only EXTRACTED supported
items may route actual accepted goods rows and explicit header-evidence rows out
of header interpretation. This avoids shared gross/net column labels becoming
document headers. It uses evidenced source positions, never fixed coordinates.
Ordinary footer candidates are retained as potential header context, not removed
as goods. If a document label exists outside the mapped item columns on a goods
row, retain full context conservatively. Non-clean item results never filter
header context. No component review issue is discarded or converted to success.

All returned header candidates receive header. prefix; item candidates receive
items. prefix while retaining TASK-007C table/physical-row/column identity. Raw,
source ID, page or sheet/cell, method and confidence stay exact. Candidate order is
header then item; prefix namespaces prevent collisions. Component issues keep
their existing typed details; service issues use fixed privacy-safe messages.

FAILED component status takes precedence; otherwise any NEEDS_REVIEW/review issue
keeps final NEEDS_REVIEW. EXTRACTED requires supported data with no unresolved
review conditions. Missing header/items add review indications. For every PDF,
items stay empty with PDF_PACKING_ITEMS_UNSUPPORTED; no PDF item extractor is
called. Safe optional missing values remain absent, not fabricated placeholders.

## Codec v1/v2 and migration assessment

Exact pairs: (1, invoice), (1, invoice_items), (2, packing_list). Canonical
schema_version remains 0.1. Only composed PackingListHeaderExtractionResult joins
the storage union; standalone PackingItemExtractionResult is rejected.

Use the existing explicit candidate tags for None/bool/int/float/str/Decimal/date/
datetime/time. Decimal text retains precision/scale; ISO values retain calendar
types and timezone offsets. Unicode, leading-zero IDs, raw text, list references,
items, issues and provenance survive actual SQLite reconstruction.

Decode duplicate-key-safe JSON, exact envelope shape/pairs and strict tags, then
revalidate the specific declared model. Packing v2 also compares against the
canonical writer shape, rejecting coercions, missing/default-elided fields and
malformed numbers/dates. Legacy v1 does not acquire this v2-only shape restriction;
existing v1 serialization and stored payload bytes are not rewritten.

The existing table supports both versions without DDL. Tests compare sqlite_master
before/after Packing operations, verify FK/sequence/active constraints and preserve
v1 payload bytes after v2 writes. No columns, indexes, CHECK/FK or migration changed.

## Transaction, history and outcomes

Reuse one BEGIN IMMEDIATE engine. Every attempted write checks source hash, state,
optional full snapshot, source/result family and expected active ID under lock.
Packing requires a Packing source; Invoice/Packing active families cannot replace
one another, even for FAILED. Legacy unclassified Invoice callers and the Invoice
header/item family remain supported.

Attempt numbers remain monotonic; successful/review attempts activate, failed
attempts stay inactive. Failed replacement preserves prior active data, while
SourceDocument records the latest committed FAILED status. Commit is atomic across
deactivation, insert and metadata; all exceptions roll back and close connections.
No retries or second writes disguise persistence errors.

Historical result family is determined by the stored envelope. Source classification
can change after a record was committed; such a change must not invalidate an old
Invoice/Packing history read. Known application extraction methods additionally
validate stored family consistency. Record status/provenance, missing source rows,
multiple active rows and duplicate sequence/history corruption fail closed.

Refusal: persisted=False, no committed record/history/metadata change. Committed
result: persisted=True with its validated record and explicit status. active_record
distinguishes retained prior active data from a failed latest attempt. Persistence
failure: uncommitted FAILED with safe reason, no successful-write claim or retry.

## Tests, development findings and remaining limits

New service and persistence suites use synthetic PDF/XLS/XLSX and real isolated
SQLite, not just repository mocks. Coverage includes production factory, read-only
source/hash snapshots, all visual identity/quality flags, classifier assertions,
composition prefixes, hidden/formula review, native dates, explicit/failed/stale
replacement, v1/v2 round-trips, complete candidate variants, malformed payloads,
CAS, two writers, five trigger abort positions, commit failure, FK/unique attempt
constraints, corrupt active index and source/record type confusion.

Development regression exposed a newly introduced history-read bug: interpreting
old Invoice records by mutable current classification broke two existing CAS race
tests. The extension was corrected to use stored discriminators for history and
apply current classification to new writes. Existing tests were not changed.
Additional red-before/green-after probes rejected truncated raw identifier evidence
and fabricated normalized values. These are fixes in this implementation, not
unapproved changes to previously completed extractors or schemas.

## Final measured validation

Windows / Python 3.13.14 / pytest 9.1.1. Use `python -B -m pytest`,
`-p no:cacheprovider` and unique external basetemp directories under the authorized
visualization workspace. Fixtures are synthetic; SQLite and runtime files are
isolated from the repository/production data. Full-suite execution uses the local
runtime for the existing Windows asyncio/TestClient tests.

| Scope | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-development full baseline `-q` | 1178 | 1178 | 0 | 0 | 2 | 40.88s |
| Final two new focused files `-q` | 149 | 149 | 0 | 0 | 0 | 7.49s |
| Final full `--collect-only -q` | 1327 | — | — | — | 2 | 1.17s |
| Final full execution `-v` | 1327 | 1327 | 0 | 0 | 2 | 43.80s |

New cases: 74 service tests and 75 codec/repository tests. All 1178 existing tests
remain present, unchanged and passing, including complete Invoice and TASK-007A/B/C
regressions. The two warnings remain the existing Starlette/httpx and AnyIO
BlockingPortal deprecations. The intermediate audit caught 2 failed/1314 passed
in 45.35s from the newly introduced mutable-classification historical-read check;
that defect is corrected without changing the old tests. Exact-identifier evidence
regressions also failed before the new service correction and pass in final tests.

No source code changed after the final full run; only this report was completed.
Tracked and new source/test whitespace checks pass, conflict markers are absent,
the index remains empty, and branch/HEAD still match the verified pre-flight.
All changed/untracked files are inventoried above; the unstaged task move appears
as an old TODO-path deletion plus a new IN_PROGRESS path until the owner stages it.

## Remaining limits and review probes

Limits: source hashes bracket processing rather than locking files indefinitely;
external writes after the final check remain outside the managed immutable-upload
contract. Header/item mixed rows, repeated or uninterrupted ambiguous footer
contexts may retain review under approved B/C policies. XLS may lack BIFF formula
provenance; the service cannot recover missing parser metadata. Visual trust follows
approved local resolution/quality contracts, not independent OCR certainty.
Codec validation is structural, not a cryptographic database integrity mechanism.
No new semantic AI, matching, business rules, PDF items, API/UI or background work.

Suggested Antigravity probes: source changes at repository lock boundary; cross-family
replacement after reclassification; legacy v1 reads and exact payload bytes;
duplicate-key/type-tag/v2 coercion attacks; mixed header/item rows and real footer
boundaries; source raw substrings and native date/numeric evidence; failed commit
after deactivation/metadata; concurrent replacements; no raw data in exceptions or
normal logs; source byte hashes and full Invoice/Packing regression.

Developer checks do not constitute independent approval. No commit, push, merge,
PR or DONE status is authorized/performed. Owner commit summary:
TASK-007D: implement packing extraction service and persistence.
