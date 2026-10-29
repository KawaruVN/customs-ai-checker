# TASK-007B — Deterministic Packing List Headers

Status: IN_PROGRESS  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007A approved and merged

Developer role: Codex — Main Developer  
Reviewer role: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Development date: 2026-10-29  
Pre-task baseline: 697 passed / 0 failed / 0 skipped / 2 warnings

## Objective and inputs

Extract canonical Packing List header fields from approved parsed workbooks and
safe native/resolved PDF content, using TASK-007A configuration and contracts.
Implementation is authorized by the Project Leader's TASK-007B development handoff.

## In scope and output

- Generic EN/VI/ZH whole-label candidate discovery with longest/specific matching.
- Canonical PackingList header result, typed issues and source candidates.
- Separate Packing List number from list-valued Invoice references; retain all
  supported references without scalar conversion or invented associations.
- Explicit party labels and document-level package/weight/volume distinctions.

## Safety invariants

Use existing conservative Decimal/date parsing. Preserve exact raw text, source
document and page or sheet/cell evidence. Missing fields remain None/empty lists.
Do not use substrings, fixed customer coordinates, hidden data or formula text as
trusted labels/values. Seller/buyer must not be inferred from shipping roles.
Conflicting values stay unresolved with review, including three-way conflicts.
Unsafe visual content cannot become trusted extraction evidence.

## Acceptance and tests

- Synthetic PDF/Excel tests at arbitrary positions cover EN/VI/ZH labels and
  longest/specific boundaries, without false role or weight/count matches.
- PDF page and Excel sheet/cell raw evidence survives canonical assembly.
- Multiple invoice references remain canonical lists; missing values are not made up.
- Zero, ambiguous numeric/date, formulas, hidden data and sticky conflicts behave
  conservatively with typed review issues.
- TASK-007A and completed Invoice regression remain green.

## Out of scope and review

No item tables, service, DB/codec changes, semantic providers, matching, rules,
normalization, endpoints or UI. Independent review and Project Leader approval
are required before merge; no DONE state is authorized by this plan.

## Verified pre-flight

Repository root: `P:\customs-ai-checker\customs-ai-checker`.
Branch: `task/007b-packing-list-headers`.
Initial HEAD: `e8f421ea2c254f3ec0988f915775aa9315e1b3de`, the required TASK-007A
closure ancestor. The working tree was clean, including untracked files; the
index was empty. TASK-007A exists in `tasks/done/` with Status DONE, and the parent
TASK-007 remains IN_PROGRESS. Baseline independently measured 697 passed,
0 failed, 0 skipped, 2 warnings in 31.71s before any file was changed.

## Production implementation

`src/customs_ai/extraction/packing_headers.py` provides
`DeterministicPackingHeaderExtractor(config=None).extract(document)` and
`extract_packing_headers(document, config=None)`. It accepts the three approved
parsed document types and returns `PackingListHeaderExtractionResult` using
TASK-007A configuration/result contracts and the existing canonical models.
It does not call providers, parse files, classify documents or write storage.

All 16 configured paths are supported. Party components are assembled only from
explicit seller/buyer labels; country_code remains outside scope. Packing items
are always empty. No Invoice extractor, service, schema, codec or existing test
is modified. The only existing production-file change is the separately approved
parser safety correction below.

### Label and layout policy

- Compile configured whole labels longest first with case-insensitive and flexible
  horizontal-whitespace comparison. Punctuation stays literal. Accepted separators
  include ASCII/fullwidth colon, spaced dash, tabs and two or more spaces.
- Begin at an explicit label; never search ordinary prose for embedded labels.
  Additional fields require an explicit column separator and another whole label.
  A non-target/item boundary makes the rest of its value opaque, including target
  labels quoted inside DESCRIPTION, NOTES or other unknown labelled values.
- Generic NO/DATE/TOTAL/QTY/WEIGHT do not establish approved fields, even when
  supplied as custom aliases. Shipping-role labels are non-target boundaries,
  never seller/buyer values or defaults. Explicit ITEM GROSS/NET labels shield
  their values from shared document-weight aliases.
- PDF label-only lookahead is limited to the immediately following nonempty,
  non-labelled line on the same page. It never crosses a page boundary. Strings
  preserve casing and value-span whitespace; syntactic label/separator characters
  are outside the value span.
- Excel uses an inline labelled span or the actual immediately adjacent right
  cell. A merged-label anchor may use the actual cell just right of the merge.
  No arbitrary coordinate, skipped-cell scan, first-sheet fallback or below-cell
  lookup is used. Multiple grounded label/value pairs on one row are supported.
  Multiline cells containing another labelled business value are ambiguous and
  stay unresolved; unlabelled multiline address text retains its exact source.
- Adjacent standalone column labels are ambiguous column evidence, not permission
  to use the first item row. Item-labelled/ambiguous column context is shielded
  until an actual blank separator, including continuation across PDF pages.
  An omitted hidden row cannot manufacture a separator. This is abstention only,
  not table recognition/extraction; headers without a clear boundary may be missed.

### Typed values, references and conflicts

Reuse `parse_decimal` and `parse_date` unchanged. Preserve zero, negative values
and Decimal precision/scale; do not perform business validation or infer units.
Native finite Excel floats are represented through Decimal(str(raw)); precision
already absent from a binary float cannot be recovered. Native typed date/datetime
uses the approved date parser. Bool/time/invalid/ambiguous evidence abstains.
All string-valued fields require string source evidence; numeric identifier cells
remain reviewable rather than guessing display-format leading zeroes. Dimensions
remain text and never calculate volume.

Invoice reference policy: one atomic string token per explicit reference label.
Independently labelled distinct references coexist with separate provenance.
Exact equivalent strings are deduplicated as business values, with every source
candidate retained. Embedded slash identifiers such as INV/2026/0001 are preserved.
Whitespace, comma/semicolon/pipe/ampersand separators, CJK list punctuation or pure
numeric ranges such as 001-003/001/003 are ambiguous and are never split or invented.
Opaque hyphenated/alphanumeric identifiers are not interpreted as ranges.
An ambiguous reference does not erase a separately evidenced valid reference,
but it keeps the result NEEDS_REVIEW. No cross-document association is inferred.

Scalar resolution groups all candidates before deciding. One exact typed value
may be deduplicated; material disagreement leaves the field None with conflict
and all candidates retained. Three-way conflicts remain sticky with no majority
vote. Invalid evidence alongside valid evidence also leaves the scalar unresolved.
For equivalent values the first in deterministic source traversal supplies the
canonical provenance; this never chooses between different business values.

Candidates retain the original raw/native evidence, location, method and typed
value when safely parsed. An unresolved candidate's typed_value may still contain
its native source type; it does not certify successful parsing. Canonical accepted
fields use origin EXTRACTED with raw/source ID and exact page or sheet/cell.
The deterministic specific-label score is 0.95, capped by supplied PDF confidence.
It indicates method confidence, not commercial correctness or completeness.
Issue messages contain no source values, filenames, sheet names or exception text;
the extractor produces no normal log output.

### PDF/visual safety and status

Revalidate detached Python-mode snapshots, including nested mutated models.
Require a nonblank source ID and a complete, unique page set 1..page_count.
Native PDFs require has_text_layer, no needs_ocr and acceptable text on every
page under the existing TASK-005A TextQualityEvaluator/settings.

Resolved PDFs require file_type pdf, no document/page review, unresolved or
fallback flags, and unique visual_pages exactly matching non-native page IDs.
Accept production source/verification combinations: TEXT_LAYER/UNVERIFIED,
OCR_LOCAL or DOCUMENT_VISION_LOCAL/SINGLE_PROVIDER, and
CROSS_VERIFIED_VISUAL/CROSS_VERIFIED. Check native/provider quality centrally,
including the configured provider-confidence threshold. A supplied cross-verified
agreement_score below the configured overlap threshold is contradictory and unsafe.
One unsafe page rejects the whole PDF with empty canonical data/candidates;
no partial trusted extraction, provider call or semantic bypass occurs.

EXTRACTED requires at least one resolved canonical header and no review-required
condition, consistent with TASK-007A. Optional absent fields stay None/empty lists;
EXTRACTED does not mean all fields exist or the business document is correct.
Ambiguity, missing labelled values, conflicts, hidden/formula or unsafe evidence
return NEEDS_REVIEW. Unsupported runtime document types return typed FAILED.
Malformed source metadata returns empty NEEDS_REVIEW without exposing its contents.

### Excel evidence safety

Use all visible worksheets; hidden/veryHidden sheets, rows and columns are never
trusted, including a hidden-only workbook. Nonempty omitted content produces a
review indication. Hidden cells may be retained only as unresolved candidates
when an explicit visible label points at them.

Formula detection uses is_formula, data_type=f and raw expression text beginning
with '='. Formula labels are opaque; formula values retain raw candidate evidence
with review. Displayed/cached values never override supplied raw evidence.
Validate workbook sheet metadata, cell coordinate/row/column identity, duplicate
positions and merged ranges before constructing a grid. Overlaps, populated merged
interiors and malformed ranges abstain. Only real merge anchors/cells contribute
evidence; partially hidden merged regions are not trusted and coordinates are
never synthesized.

## Project Leader-approved parser safety defect fix

Independent real-XLSX probes demonstrated that an openpyxl hidden column group
B:D was parsed as hidden_columns=['B']; C/D business data could therefore be
trusted by both Packing and Invoice's production visibility policy. This is a
pre-existing metadata loss in `src/customs_ai/parsers/excel.py`, not a new schema
or extraction-policy requirement. The developer escalated it before changing
the completed implementation. The Project Leader explicitly approved this
minimal exception and mandatory before/after regressions.

The fix expands each hidden=True ColumnDimension.min..max to column letters,
falling back to its key for individual dimensions. The existing unique sorted
list shape remains unchanged; hidden=False outline groups stay visible.
No XLS parser, model, API, SQLite or Invoice/Packing policy was changed for this
fix. New real-XLSX tests verify individual/nonhidden/disjoint groups, every B:D
member, outside-column visibility, source byte hashes, visible coordinates and
both consumers. Invoice probes call its production _visible_workbook policy
before the approved Invoice header extractor; the standalone legacy Invoice
extractor is not given a new visibility policy.

Before the fix the new eight-case regression produced 2 passed / 6 failed in
1.45s. After the fix the same eight cases passed in 0.87s. All 27 parser tests
passed in 1.21s. Full final verification is recorded below.

## Final measured validation

Windows / Python 3.13.14 / pytest 9.1.1. All commands use `python -B -m pytest`
and `-p no:cacheprovider`; execution uses a unique external `--basetemp` under the
authorized visualization workspace. Full/legacy execution uses the local Windows
runtime for asyncio/TestClient compatibility. Fixtures are synthetic and runtime/
SQLite data is isolated from the repository and production data.

| Scope | Collected | Passed | Failed | Skipped | Warnings | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pre-development full baseline | 697 | 697 | 0 | 0 | 2 | 31.71s |
| New grouped-column tests before approved fix | 8 | 2 | 6 | 0 | 0 | 1.45s |
| Same grouped-column tests after fix | 8 | 8 | 0 | 0 | 0 | 0.87s |
| All parser tests after fix | 27 | 27 | 0 | 0 | 0 | 1.21s |
| Final Packing A/B plus all parsers | 365 | 365 | 0 | 0 | 0 | 8.05s |
| Legacy / TASK-006 regression plus parser safety tests | 624 | 624 | 0 | 0 | 2 | 23.55s |
| Final full collection | 962 | — | — | — | 2 | 1.34s |
| Final full execution | 962 | 962 | 0 | 0 | 2 | 31.68s |

Focused scope: all five `tests/unit/extraction/test_packing_*.py` files and
`tests/unit/parsers/`, with `-q`. Legacy scope: full pytest with
`--ignore-glob=tests/unit/extraction/test_packing_*.py -q`; this includes all 616
pre-Packing tests plus the eight approved parser safety regressions. Global
collection uses `--collect-only -q` and full execution uses `-q`.

265 new tests were added: 112 PDF + 91 workbook + 54 adversarial + eight parser.
All 697 baseline tests remain unchanged and pass. The two warnings are the
pre-existing Starlette/httpx and AnyIO BlockingPortal deprecations. Development
probes found and corrected opaque-tail, foreign-role, item-context, visual-score
and multiline-cell false positives with new regressions; these developer checks
do not replace Antigravity's independent review.

Final changed-file inventory: new Packing extractor, the approved XLSX parser
metadata correction, four new test files and this task moved TODO -> IN_PROGRESS.
Git represents the unstaged task move as a deleted old path plus an untracked
new path; no index change is made. Branch and HEAD remain the verified pre-flight
values. No existing tests, canonical schema, Invoice functionality, YAML config,
README or parent Epic are changed. Git diff whitespace checks pass for tracked
changes; all source/test files are exercised by final pytest.

## New test inventory and acceptance evidence

- `tests/unit/extraction/test_packing_headers_pdf.py`: 112 cases covering all
  16 paths in EN/VI/ZH, exact page/raw evidence, references, conflicts, native
  quality, safe resolved PDF, unsafe partial documents and malformed metadata.
- `tests/unit/extraction/test_packing_headers_workbook.py`: 91 cases covering
  all paths, role/boundary safety, arbitrary layouts, adjacent/inline cells,
  hidden/formula/merged data, conflicts, native value types and real XLSX/XLS
  parser/source-byte smoke tests.
- `tests/unit/extraction/test_packing_headers_adversarial.py`: 54 additional
  development probes covering opaque descriptions/notes before and after valid
  fields, bare role labels, item context, cross-page continuation, contradictory
  agreement scores, hidden-row barriers, same-row key/value pairs, numeric IDs
  and multiline-cell field contamination.
- `tests/unit/parsers/test_hidden_column_groups.py`: the eight real-XLSX approved
  defect regressions, proved failing before and passing after the parser fix.

| Acceptance condition | Developer evidence |
|---|---|
| All 16 approved paths and EN/VI/ZH | PDF and workbook all-path tests; unchanged A config |
| Canonical PackingList, items always empty | All result tests; no PackingItem implementation |
| List-valued references, zeros and exact evidence | Multi-page/sheet references, dedup, ambiguous combined input and provenance tests |
| Explicit roles/counts/gross/net/dimensions/volume | Positive all-path and negative prefix/item/foreign-role probes |
| Decimal/date and leading-zero safety | High precision/scale, native zero/date, invalid/ambiguous input and numeric-ID abstention |
| Conflicts conservative, no majority | Equivalent, two-way, three-way and mixed-invalid candidate probes |
| Hidden/formula/merged safety | Workbook suite plus red-before/green-after grouped-XLSX regression |
| PDF safety with whole-document abstention | Native/resolved quality, identity, flags and inconsistent verification tests |
| No source mutation or private issue/log values | Input snapshot/hash tests and safe issue messages |
| TASK-006/007A compatible and scope bounded | Final regressions; unchanged approved modules except authorized parser delta |

## Known limitations and independent-review probes

- Excel supports explicit inline/right-adjacent evidence only; below-cell, distant,
  ambiguous columns or uninterrupted item-context headers abstain. PDF layout that
  loses useful line boundaries may need later separately authorized extraction.
- Reference strings containing spaces/list separators or numeric ranges abstain;
  opaque single-token alphanumeric identifiers are not linguistically interpreted.
- No unit stripping/conversion, volume calculation, date-locale guess, normalization,
  item extraction, service/persistence, matching or AI is implemented.
- Source identity/text/visibility is supplied by the approved parser/resolution
  boundary. This component cannot authenticate fabricated caller source content or
  reread original PDF pages. Missing optional provider_results/agreement metadata
  follows the approved ResolvedPdfDocument contract; explicit contradictions reject.
- The inherited XLS parser exposes BIFF cached values without formula expressions/
  flags. This extractor refuses formula evidence when supplied; it cannot recover
  formula provenance already absent from ParsedCell. No stronger guarantee about
  unidentified XLS cached values or Excel display-format reconstruction is claimed.
- The inherited ExtractionCandidate union has bare-JSON type ambiguity documented
  in TASK-007A. Python-mode candidate and typed canonical values are preserved;
  Packing persistence/serialization remains a separate TASK-007D scope.
- Antigravity should repeat opaque-tail and item-description probes, multi-sheet
  conflicts, ambiguous reference boundaries, malformed/partially hidden merges,
  grouped XLSX metadata and entire-document unsafe visual abstention. Independently
  assess the stated source/parser boundaries and conservative layout limitations.

## Review state and handoff

IN_PROGRESS. Developer validation is not independent approval. No commit, push,
merge or PR is performed; no task is marked DONE. Shared README and parent Epic
are unchanged as instructed. Suggested owner commit summary:
`TASK-007B: implement deterministic packing list headers`.
