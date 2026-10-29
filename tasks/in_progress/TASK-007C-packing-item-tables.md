# TASK-007C — Deterministic Packing Item Tables

Status: IN_PROGRESS  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007A and TASK-007B approved and merged

Developer role: Codex — Main Developer  
Reviewer role: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Development date: 2026-10-29  
Pre-task baseline: 962 passed / 0 failed / 0 skipped / 2 warnings

## Objective and inputs

Extract canonical PackingItem rows conservatively from generic parsed Excel
tables using the approved item aliases and result contract. Implementation is
authorized by the Project Leader's TASK-007C development handoff.

## In scope and output

- Evidence-based header/table discovery at arbitrary worksheet/row/column positions.
- Seven approved item fields: item_code, description, quantity, unit,
  package_number, gross_weight and net_weight.
- Canonical item result with status, source candidates and typed review issues.

## Safety invariants

Do not treat generic numeric columns or isolated labels as proof of a product
table. Separate document totals from item quantities/weights and package numbers
from package count/type. Preserve raw values, leading-zero identifiers, numeric
zero, Decimal precision, document ID and actual sheet/cell provenance. Relevant
incomplete rows stay partial and reviewable. Formulas are opaque and unexecuted.
Hidden rows/sheets, merged/duplicate columns, summary boundaries, blank business
rows and competing tables require explicit conservative policies; never silently
append or arbitrarily choose competing tables.

## Acceptance and tests

- Synthetic XLSX/XLS and parsed-workbook tests exercise arbitrary layouts and
  EN/VI/ZH labels without fixed customer templates.
- Correct seven-field canonical mapping and exact source evidence; no fabricated
  quantity, package identifier or weights.
- Tests distinguish gross/net and document/item contexts, blank-row termination,
  genuine totals versus product names, formula uncertainty, hidden content,
  partial rows and multi-table ambiguity.
- Only structurally justified continuation is allowed; ambiguous cases need review.
- Foundation/header tests and all completed Invoice regression remain green.

## Out of scope and review

No PDF table recognition, item matching by position, orchestration, DB/codec,
semantic providers, normalization, rules, HTTP/UI or customer adapters. Independent
review and Project Leader approval are required before merge or task closure.

## Pre-flight evidence

Repository root: `P:\customs-ai-checker\customs-ai-checker`.
Branch: `task/007c-packing-item-tables`.
Initial HEAD: `c177e615501e392186b0ef5aedc826beb7986c34`, the required ancestor.
The developer verified the ancestor, a clean working tree including untracked
files, empty index, TASK-007A/B DONE under tasks/done, parent Epic IN_PROGRESS and
this task present under tasks/todo before editing. The complete pre-development
baseline independently passed 962 tests, 0 failed, 0 skipped, 2 warnings in 32.58s.

Authoritative sources read: PROJECT_CONSTITUTION.md, MASTER_SPEC.md,
ARCHITECTURE.md, docs/DATA_SCHEMA.md, parent TASK-007, completed TASK-007A/B and
TASK-006C, this task and the explicit TASK-007C handoff. No specification conflict
was found. The handoff authorizes C despite the older plan's A-only wording;
shared README, parent Epic and completed task documents remain unchanged.

## Production component and boundaries

`src/customs_ai/extraction/packing_items.py` implements
`DeterministicPackingItemExtractor(config=None).extract(workbook)` and
`extract_packing_items(workbook, config=None)`. The input is ParsedWorkbook
(XLSX/openpyxl or XLS/xlrd); output is the approved PackingItemExtractionResult.
Use TASK-007A config/result contracts, canonical PackingItem/CanonicalField,
ExtractionStatus/Issue/Candidate, normalize_alias and parse_decimal unchanged.

The seven fields are item_code, description, quantity, unit, package_number,
gross_weight and net_weight. No new canonical fields or PackingList/header values
are introduced. Invoice's structural patterns were reviewed; its specific field,
formatter and footer-prefix policies were not copied. No generic framework or
shared approved-module refactor is added.

There is no file parsing, PDF item extraction, service, persistence/codec, SQLite,
matching, normalization, unit conversion, quantity/weight reconciliation, semantic
provider, HTTP endpoint, UI or customer layout. No previously approved production
source or tests are changed, including the TASK-007B hidden-column parser fix.

## Table recognition and eligibility

1. Match whole configured item labels using approved case/whitespace normalization
   and one optional terminal ASCII/fullwidth colon. No substring or fixed-position
   matching. A post-colon-normalization collision across paths fails construction
   with a generic ValueError rather than silently overwriting an alias.
2. A structural header must contain item_code or description AND at least one
   of quantity, gross_weight or net_weight. Package_number/unit do not establish
   product identity. Document aggregate labels are not item numeric headers.
3. A credible region must contain at least one physical body row with BOTH a safe
   visible string identity and safely parsed numeric evidence under that header.
   Item code requires an alphanumeric character; description requires a letter.
   Punctuation-only, numeric-only descriptions, hidden/formula identities and
   identity/numeric evidence split across different rows do not certify goods.
4. Eligible selection additionally requires an unambiguous, visible, unmerged
   header mapping. Duplicate paths, compound multi-field cells and separately
   credible column groups make the affected header ineligible. All evidence is
   retained with review. A hidden/ineligible/header-only/noncredible region cannot
   outvote or replace one independently supported eligible region.
5. Exactly one eligible credible region may supply canonical items. Two or more
   eligible credible regions, even with repeated identical values or a 2:1 split,
   produce items=[] and NEEDS_REVIEW. No position, majority or automatic table
   concatenation chooses a result. Ineligible regions alongside a supported one
   still force NEEDS_REVIEW; retained canonical rows are partial supported output,
   not a claim that the full workbook has been resolved.

Header/body notes safeguards reject explicit colon-labelled note context and bare
standalone note headings until a visible blank separator. An unrelated NOTES
column is permitted. Hidden empty rows cannot manufacture a visible separator.
This bounded policy intentionally abstains on illustrative tables in contiguous
notes; it is not semantic classification of arbitrary prose.

## Geometry, row boundaries and partial items

Discover all worksheets/rows/columns; order and offsets are not fixed. Extra
unrelated columns do not map to canonical fields. Validate document ID, sheet
counts/names/indices, visibility values, coordinate/row/column identity, duplicate
positions, range bounds, overlapping merges and populated merged interiors before
constructing a grid. Malformed metadata returns empty NEEDS_REVIEW, not a crash
or arbitrarily overwritten evidence.

Body scanning requires contiguous physical rows with mapped business content.
Implicit gaps, a blank mapped row (even if unrelated columns contain notes), a
different header, totals or footer terminate the region. An implicit gap involving
hidden rows also forces review and retains the next actual mapped evidence.
No source values are shifted across a gap or borrowed from an adjacent row.

Contiguous repeated identical header mappings continue the same region, including
equivalent EN/VI/ZH labels. Identical headers after a blank/summary boundary start
independent regions; credible separated regions compete. Subtotals always flag
review and stop; later unheadered sections are never appended automatically.

Exact normalized TOTAL, GRAND TOTAL, SUBTOTAL, SUB TOTAL, TỔNG/TỔNG CỘNG/CỘNG,
小计/合计/总计/SUMMARY and NOTE/NOTES/REMARK(S)/GHI CHÚ/备注 are boundaries.
Configured package_count labels and explicit TOTAL/TỔNG/总 gross/net/volume
aggregate labels are also boundaries. Explicit marker+colon text, including a
space before the colon, is supported. Descriptions merely containing these words
(TOTAL CONTROL, NOTES HOLDER, SUMMARY BOOK, etc.) remain product descriptions.
A boundary marker with independent product identity is ambiguous: retain evidence,
stop and review rather than decide that it is a product or commercial total.

Within one supported eligible region, incomplete physical rows retain their safe
fields and trigger INCOMPLETE_PACKING_ROW. Missing optional package/weight fields
alone do not cause review when identity plus quantity/weight is grounded. A
description plus gross/net weight without quantity is supported. Continuation or
quantity-only rows are never joined to neighbouring items; their partial fields
remain reviewable observations. Rows with no safely parsed fields create no empty
canonical placeholder. Repeated package IDs on two independently supported goods
rows are allowed; no item deduplication or package allocation is inferred.

## Hidden, formula and merged evidence

Only visible source cells can produce accepted values. Nonempty excluded hidden
rows/columns/sheets cause review. Hidden-only workbooks never fall back to hidden
data. Hidden headers/mapped columns make that table ineligible; hidden business
rows are omitted with source candidates, without claiming clean completeness.
The approved parser's grouped B:D metadata is consumed unchanged and tested using
a real XLSX. No parser exception or new visibility policy is introduced.

Formula detection uses all three signals: is_formula, data_type=f, and raw text
beginning '=' after whitespace. Formula labels cannot establish headers. Formula
values and supplied caches cannot become canonical fields, even if the raw value
looks numeric/string-like. Keep opaque source candidates and review. Displayed
values never replace original raw evidence; formulas are never evaluated.

Merged mapped headers are ineligible. A horizontal body merge is accepted only
when it spans one physical row, intersects one mapped field and that field is the
actual merge anchor. It never produces ghost cells. Vertical/cross-field merges
stop canonical interpretation with review; actual mapped evidence on all affected
physical rows is retained. No merged quantity or description is distributed across
several items. Hidden overlap in a merged region is not trusted.

## Numeric, identifier and source contracts

Numeric fields use the existing strict parse_decimal. Preserve zero, negative
values, long lexical Decimals and trailing scale. Finite native floats convert
through Decimal(str(raw)); precision already lost before extraction is not
recoverable. Ambiguous separators, arbitrary text/unit suffixes, bool/date/time,
nonfinite numbers and formulas remain unresolved. No calculations or unit guesses.

String fields require actual nonblank source strings; native numeric IDs, even
with a zero display format, do not silently invent or lose intended leading zeros.
String item/package IDs retain original casing and leading zeros. Unsupported
control characters are rejected; description line breaks may be retained without
inventing continuation associations.

Package_number is one opaque scalar identifier. Combined values containing spaces,
list delimiters (including CJK punctuation), ampersands or pure numeric ranges
remain unresolved with review. Do not split or duplicate items. An atomic slash
identifier such as BOX/2026/001 is preserved. This conservative policy can require
review for otherwise legitimate identifiers containing whitespace.

Every accepted field has original raw_value, typed normalized_value,
origin=EXTRACTED, source_document_id, actual sheet/cell, extraction method
`deterministic_packing_item_table`, confidence=0.95 and page=None. The score follows
the approved deterministic specific-label policy and is not commercial validation.
Canonical item indices are zero-based output-list positions only.

Candidate convention:
`tables[sheet_index:header_excel_row].rows[physical_excel_row].columns[column_index].field`.
All Excel row/column coordinates in this path are one-based physical source
positions; sheet_index is the supplied parser sheet index. They are never canonical
item indices. Header candidates use a `headers.` prefix. Unmapped formula candidates
use `unresolved.sheets[sheet_index].rows[row].columns[column]`. Duplicate/compound
columns retain distinct coordinates/paths. Safe typed values are preserved in
Python-mode candidates; unresolved/hidden evidence has no certified typed value.

## Status, privacy and source immutability

EXTRACTED requires supported nonempty items with no review-required issues and no
empty rows, consistent with TASK-007A. NEEDS_REVIEW covers absent/unsupported tables,
unsafe/partial evidence, structure ambiguity and malformed metadata. Unsupported
runtime types (including ParsedPdfDocument) return typed FAILED with no PDF work.
No placeholder, quantity, weight, leading zero or cross-row association is invented.

Inputs are detached and revalidated, never mutated. Real XLS/XLSX source hashes
and parsed snapshots are checked by tests. Issues use fixed generic messages and
structural field paths only; no raw IDs/descriptions/values, filenames, absolute
paths or exception messages are exposed. The extractor performs no normal logging
or network/provider calls.

## Test inventory and development defects

- `tests/unit/extraction/test_packing_items_tables.py`: 69 cases for all seven
  fields/three languages, geometry, table evidence, partial rows, boundaries,
  competing tables, repeated headers, provenance and immutability.
- `tests/unit/extraction/test_packing_items_safety.py`: 109 cases for numeric/type
  refusal, all formula signals/caches, hidden sources, merged/invalid metadata,
  alias collisions, real grouped-hidden XLSX and source/privacy contracts.
- `tests/unit/extraction/test_packing_items_adversarial.py`: 25 cases for package
  ambiguity, false tables/identity, notes contexts, hidden separators and paths.
- `tests/unit/extraction/test_packing_items_integration.py`: 13 cases for real
  all-field XLS extraction, PDF refusal, note/footer and merged-row evidence.

Development probes found new-module defects before handoff: explicit document
totals became products, optional-colon aliases could silently collide, meaningless
codes certified goods, and notes/hidden separators could establish false tables.
Failing regressions were added before fixes (e.g. safety 103 passed/6 failed in
2.72s, adversarial 19 passed/5 failed in 1.29s, then hidden-gap 24 passed/1 failed).
All are corrected in the new module and pass final focused tests. No inherited
defect requiring an approved-source exception was found or changed in TASK-007C.
These are developer checks, not Antigravity's independent approval.

## Final measured validation

Environment: Windows / Python 3.13.14 / pytest 9.1.1. Tests use synthetic parsed
structures and real temporary XLS/XLSX files. Commands use `python -B -m pytest`,
`-p no:cacheprovider` and a unique external `--basetemp` under the authorized
visualization workspace. Local full-suite execution supports the project's
Windows asyncio/TestClient tests; temporary runtime/SQLite data stays isolated
from repository and production data.

| Scope | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-development complete baseline `-q` | 962 | 962 | 0 | 0 | 2 | 32.58s |
| Final four new focused files `-v` | 216 | 216 | 0 | 0 | 0 | 3.78s |
| Final global `--collect-only -q` | 1178 | — | — | — | 2 | 1.47s |
| Final complete suite `-v` | 1178 | 1178 | 0 | 0 | 2 | 26.76s |

Focused arguments are the four new test files listed above. Global collection
and full execution use the repository's existing pytest discovery unchanged.
The final total adds 216 new cases to the unchanged 962-test approved baseline.
All Invoice extraction/service/persistence, Packing foundation/header and grouped
hidden-column regressions pass. Warnings remain the existing Starlette/httpx and
AnyIO BlockingPortal deprecations; no new warning is introduced.

Changed/untracked inventory at handoff:

- New `src/customs_ai/extraction/packing_items.py`.
- New `tests/unit/extraction/test_packing_items_tables.py`.
- New `tests/unit/extraction/test_packing_items_safety.py`.
- New `tests/unit/extraction/test_packing_items_adversarial.py`.
- New `tests/unit/extraction/test_packing_items_integration.py`.
- Move/update `tasks/todo/TASK-007C-packing-item-tables.md` to this IN_PROGRESS
  path. Before staging, Git represents this as the deleted old path plus an
  untracked new path. No index change is made.

Branch and HEAD remain the verified pre-flight values. The working tree now has
only the listed intended development changes. All existing application code,
parsers, canonical models, configuration, approved tests, README, parent Epic and
completed task documents are unchanged. No source mutation, task closure or Git
publication action was performed.

## Acceptance evidence

| Acceptance condition | Developer evidence |
|---|---|
| Seven approved fields and canonical contracts | All-field EN/VI/ZH + real XLS tests; unchanged domain/config/models |
| Grounded table discovery; false tables excluded | Identity+numeric header and same-row body tests, punctuation/note/footer refusal |
| Competing tables remain reviewable | Two/three regions, multiple sheets, separate groups and noncredible-vs-supported tests |
| Conservative summary/footer boundaries | Exact multilingual markers, aggregates, subtotals, repeated headers and product-word tests |
| Hidden/formula data cannot be trusted | Per-field hidden/formula/cache tests and actual grouped-hidden XLSX |
| Safe merged/ambiguous geometry | Header, horizontal anchor, vertical/cross-field, overlap/interior metadata tests |
| Partial values, no invented row associations | Identity-only/quantity-only/continuation, no empty placeholders or shifting |
| Numeric/identifier and exact provenance | Zero/scale/large/negative/ambiguous values, ID refusal, actual sheet/cell/source hashes |
| Backward compatibility and scope | Final full regression; no approved production/tests, header/parser/DB/API changes |
| Review readiness | Developer validation only; independent review still required, task remains IN_PROGRESS |

## Known limitations and Antigravity probes

- Only configured whole single-row headers and conservative contiguous regions
  are supported. Multi-row header semantics, inferred continuations and cross-row
  package allocation abstain. No PDF item-table support is claimed.
- A safe header and one same-row identity/numeric pair are structural evidence,
  not semantic certification of every product description. Explicit notes are
  shielded; arbitrary unlabelled explanatory matrices cannot be linguistically
  authenticated without a later authorized capability.
- Ineligible regions retain candidates/review and do not outvote a unique eligible
  region. Antigravity should challenge this evidence-quality policy, hidden/merged
  regions beside genuine tables, and two/three independently eligible tables.
- Numeric identifiers/display reconstruction, compound packages, uninterrupted
  note contexts and ambiguous merged ownership intentionally require review.
- Approved ParsedWorkbook metadata is the source boundary. The inherited XLS
  parser may omit BIFF formula provenance and expose cached values; this extractor
  cannot recover absent metadata. No stronger guarantee about unidentified cached
  XLS values is claimed and no parser change is authorized here.
- ExtractionCandidate's inherited bare-JSON union type ambiguity remains TASK-007D
  scope; no persistence/codec change is made. Python-mode typed evidence and typed
  canonical values are preserved.
- Suggested independent probes: alias colon collisions, multilingual document
  totals among goods, numeric/punctuation-only identities, compound/duplicate
  column groups, hidden empty gaps after notes, vertical merge evidence, and
  competing regions with identical versus conflicting data. Recheck source bytes
  and privacy-safe issues, then all Invoice/Packing header regressions.

## Review and Git handoff

Status remains IN_PROGRESS. No commit, push, merge, PR or task closure is performed.
Shared README, parent Epic and completed task documents are unchanged. Suggested
owner commit summary: `TASK-007C: implement deterministic packing item tables`.
Independent Antigravity approval and Project Leader review are still required.
