# TASK-004 — Local PDF / Excel Parsers

Status: IN_PROGRESS  
Priority: P1  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Created: 2026-09-11  
Updated: 2026-09-11  
Target Version: V1  
Dependencies: TASK-001 — Project Foundation (DONE); TASK-002 — Canonical Data Schema (DONE); TASK-003 — File Ingestion + Hashing (DONE)  
Related ADR: None

---

## 1. OBJECTIVE

Implement the deterministic local parser layer for safely ingested PDF and Excel documents.

TASK-004 must convert a persisted `SourceDocument` plus its stored file into a technical parsed representation that downstream classification/extraction tasks can consume without depending on customer-specific layouts.

The parser layer must:

- route PDF to a local PDF parser;
- route XLSX/XLS to local Excel parsers;
- preserve PDF page boundaries;
- preserve Excel workbook/sheet/cell provenance;
- preserve technical metadata required by later extraction;
- update safe parser metadata on the `SourceDocument`;
- avoid OCR/vision/LLM calls;
- remain deterministic, testable, CWD-independent, and layout-agnostic.

TASK-004 is technical parsing only. It MUST NOT decide whether a document is an Invoice, Packing List, Bill, declaration, C/O, etc.

---

## 2. BACKGROUND

The architecture defines `src/customs_ai/parsers/` as the parser layer. The Parser Router chooses the technical parser based on validated file type.

Architecture requirements:

- PDF: local text extraction first; preserve page boundaries; scanned/no-text files must be recognizable as requiring later OCR/vision fallback.
- Excel: parse locally; prefer `openpyxl` for XLSX and a compatible local parser for XLS; preserve workbook name, sheet name, cell location, raw value, displayed/cached value where practical, merged cells, and hidden sheet/row metadata when practical.
- Parser output is technical content only and does not perform document classification or customs business logic.

TASK-003 now provides safely persisted `SourceDocument` records and local files. TASK-004 builds the next deterministic stage.

---

## 3. SCOPE

TASK-004 MUST:

1. Add a parser abstraction/protocol or coherent common interface.
2. Add a Parser Router for:
   - `pdf` → PDF parser
   - `xlsx` → XLSX parser
   - `xls` → XLS parser
3. Resolve a `SourceDocument` by `document_id` through the repository boundary.
4. Locate the persisted source file safely.
5. Reject a stored path that resolves outside configured `upload_root`.
6. Return deterministic parser errors if the SourceDocument/file is missing or unsupported.
7. Parse PDF locally:
   - page count;
   - one output record per page;
   - 1-based page number;
   - extracted text per page;
   - empty string when no local text is extractable;
   - document-level `has_text_layer`;
   - document-level `needs_ocr` flag when no usable text layer exists;
   - encrypted PDF handling;
   - corrupted/unreadable PDF handling.
8. Parse XLSX locally with `openpyxl`:
   - workbook/source name;
   - sheet names and order;
   - sheet visibility/state;
   - cells with stable A1 coordinates;
   - row/column indexes;
   - raw cell value;
   - cached/displayed value when practically available without calculating formulas;
   - formula indicator / formula text preservation when present;
   - number format;
   - merged-cell ranges;
   - hidden-row metadata;
   - hidden-column metadata when practical.
9. Parse legacy XLS locally with a lightweight compatible parser such as `xlrd`:
   - workbook/source name;
   - sheet names and order;
   - cell coordinates;
   - raw cell values;
   - basic cell type metadata;
   - merged ranges when available;
   - hidden row/column metadata when the library exposes it safely.
10. Never execute spreadsheet formulas or macros.
11. Never use `data_only` or formula evaluation in a way that fabricates recalculated values.
12. Preserve formulas as source content where available.
13. Produce Pydantic/typed parser output models with strict extra-field behavior.
14. Keep parser output JSON-serializable.
15. Update SourceDocument parser metadata after successful parse:
   - `processing_status = PARSED`
   - `parser_used`
   - PDF `page_count`
   - Excel `sheet_count`
   - do not fabricate classification metadata;
   - do not mark canonical extraction complete.
16. Add repository update operation(s) behind the existing repository boundary as needed.
17. Keep TASK-001/TASK-002/TASK-003 behavior green.
18. Add unit, integration/service, failure, and regression tests.

---

## 4. OUT OF SCOPE

TASK-004 MUST NOT implement:

- OCR;
- image/vision parsing;
- PDF visual layout/bounding-box extraction;
- table reconstruction from PDF;
- semantic document classification;
- filename-based document classification;
- Invoice/Packing/Bill/Declaration structured extraction;
- canonical business field creation;
- normalization algorithms;
- item matching;
- rule/check engine behavior;
- HS classification/recommendation;
- legal decisions;
- customer-specific template adapters;
- AI/LLM/API calls;
- external network calls;
- CSV parsing;
- DOCX parsing;
- JPG/JPEG/PNG OCR;
- UI;
- report generation;
- human correction;
- formula execution;
- macro execution;
- writing/modifying uploaded workbooks;
- automatic password cracking/decryption.

Scanned/no-text PDFs are detected and flagged for a later OCR-capable stage; TASK-004 does not OCR them.

---

## 5. INPUT

Primary service input:

```text
document_id
```

Repository input:

```text
SourceDocument
- document_id
- shipment_id
- file_type
- stored_path
- processing_status
- ...
```

Supported parser file types for this task:

```text
pdf
xlsx
xls
```

---

## 6. OUTPUT

### PDF output concept

```json
{
  "document_id": "DOC-...",
  "file_type": "pdf",
  "parser_used": "pypdf",
  "page_count": 2,
  "has_text_layer": true,
  "needs_ocr": false,
  "pages": [
    {
      "page": 1,
      "text": "..."
    },
    {
      "page": 2,
      "text": "..."
    }
  ]
}
```

### Excel output concept

```json
{
  "document_id": "DOC-...",
  "file_type": "xlsx",
  "parser_used": "openpyxl",
  "workbook_name": "original.xlsx",
  "sheet_count": 2,
  "sheets": [
    {
      "name": "Invoice",
      "index": 0,
      "state": "visible",
      "merged_ranges": ["A1:D1"],
      "hidden_rows": [5],
      "hidden_columns": ["C"],
      "cells": [
        {
          "coordinate": "A1",
          "row": 1,
          "column": 1,
          "raw_value": "Invoice No.",
          "displayed_value": "Invoice No.",
          "data_type": "s",
          "is_formula": false,
          "number_format": "General"
        }
      ]
    }
  ]
}
```

Exact naming may vary if coherent and documented, but page/sheet/cell provenance must remain explicit.

---

## 7. FUNCTIONAL REQUIREMENTS

### FR-01 — Parser interface

Provide a small parser contract that accepts a trusted local file path plus required document identity and returns a typed parsed result.

Parser implementations must not query FastAPI/request objects.

### FR-02 — Parser Router

The router MUST use validated `SourceDocument.file_type` or equivalent trusted metadata.

It MUST NOT use user filename semantics to decide whether a file is an invoice/packing list/etc.

### FR-03 — SourceDocument lookup

A parser/application service must retrieve the SourceDocument through `SourceDocumentRepository.get_by_document_id(...)`.

Unknown ID:

```text
SOURCE_DOCUMENT_NOT_FOUND
```

### FR-04 — Stored-file existence

Missing file:

```text
SOURCE_FILE_NOT_FOUND
```

### FR-05 — Stored path containment

Before parsing, resolve the stored path and verify it remains inside `settings.upload_root`.

Escape/symlink path outside root:

```text
SOURCE_FILE_PATH_INVALID
```

### FR-06 — Unsupported parser type

A SourceDocument with a file type not handled by TASK-004 must fail deterministically:

```text
PARSER_UNSUPPORTED
```

Do not silently route CSV/DOCX/images into unrelated parsers.

### FR-07 — PDF local extraction

Use a local PDF library.

Preserve page order and 1-based page number.

`page.extract_text()` returning `None` is represented as `""`, not fabricated content.

### FR-08 — PDF text-layer signal

`has_text_layer=true` only when locally extracted usable text exists.

If every page is empty/whitespace:

```text
has_text_layer=false
needs_ocr=true
```

This is a technical signal, not a document-classification decision.

### FR-09 — Encrypted PDF

If a PDF can be opened only with a password not provided to the system, fail:

```text
PDF_ENCRYPTED
```

If the library can safely open an encryption wrapper with an empty password, parsing may proceed.

No password guessing.

### FR-10 — Corrupted PDF

Malformed/unreadable PDF:

```text
FILE_CORRUPTED
```

or another single documented deterministic parser-corruption code.

Do not expose raw library tracebacks through the application contract.

### FR-11 — XLSX local parsing

Use `openpyxl` locally.

Workbook must be opened read-only with respect to user data; never save the uploaded workbook.

Do not execute macros.

### FR-12 — Formula handling

Formula source text should be preserved when available, e.g.:

```text
=SUM(B2:B10)
```

Do not recalculate formulas.

If a cached/displayed value is available from the file without calculation, it may be exposed separately.

If unavailable, `displayed_value` may be null.

### FR-13 — Sheet metadata

Preserve:

- sheet name;
- sheet index/order;
- sheet state/visibility;
- merged ranges;
- hidden rows;
- hidden columns where practical.

### FR-14 — Cell metadata

For meaningful/populated cells, preserve at minimum:

- coordinate;
- row index;
- column index;
- raw value;
- data type;
- formula indicator;
- number format.

Avoid emitting millions of structurally empty cells created only by worksheet dimensions.

### FR-15 — XLS parser

Use a lightweight local XLS-compatible parser, preferably `xlrd>=2`.

No conversion via external Office/LibreOffice process.

### FR-16 — XLS provenance

Generate stable A1-style coordinates for returned XLS cells.

Preserve sheet order and merged ranges where available.

### FR-17 — Parser metadata persistence

After a successful parse, update SourceDocument through the repository boundary:

PDF:
```text
processing_status = PARSED
parser_used = pypdf
page_count = actual page count
sheet_count = null
```

Excel:
```text
processing_status = PARSED
parser_used = openpyxl or xlrd
sheet_count = actual sheet count
page_count = null
```

Do not set:
```text
detected_document_type
classification_confidence
```

Do not falsely mark semantic/canonical extraction complete.

### FR-18 — Failed parse metadata

A parse failure must not leave falsely successful metadata such as `processing_status=PARSED`.

Whether failure status is persisted as `FAILED` is implementation-defined for V1 if done coherently through the repository boundary.

### FR-19 — Original files immutable

Parser must not alter, rename, rewrite, or delete the stored source document.

### FR-20 — Deterministic errors

At minimum define/document:

```text
SOURCE_DOCUMENT_NOT_FOUND
SOURCE_FILE_NOT_FOUND
SOURCE_FILE_PATH_INVALID
PARSER_UNSUPPORTED
PDF_ENCRYPTED
FILE_CORRUPTED
PARSER_FAILED
```

Exact class layout is flexible.

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- NFR-01: AI allowed: NO.
- NFR-02: No external network/API calls.
- NFR-03: Do not log full document text or workbook cell contents.
- NFR-04: Do not log secrets.
- NFR-05: Do not execute formulas/macros.
- NFR-06: Do not modify uploaded files.
- NFR-07: Parser layer remains independent of FastAPI route handlers.
- NFR-08: Database access remains behind repository boundary.
- NFR-09: Do not add pandas, LangChain, OCR frameworks, Office automation, or other heavy frameworks.
- NFR-10: Compatible with Python >=3.12 and user's Python 3.13 environment.
- NFR-11: Parsed results must be deterministic for the same local file/library version.
- NFR-12: Existing 73-test TASK-001..003 suite must not regress.
- NFR-13: Tests use only synthetic/anonymized fixtures.
- NFR-14: No production/customer documents committed.

---

## 9. BUSINESS RULES

None.

This task performs technical parsing, not customs/business validation.

---

## 10. DATA MODEL IMPACT

Creates technical parser-output models only.

Possible conceptual models:

```text
ParsedPdfDocument
ParsedPdfPage

ParsedWorkbook
ParsedSheet
ParsedCell
```

These models MUST remain separate from the TASK-002 canonical business models.

Do not mutate Invoice/PackingList/TransportDocument/CustomsDeclaration schema semantics.

---

## 11. FILES / MODULES EXPECTED

Expected affected areas:

```text
pyproject.toml
README.md

src/customs_ai/parsers/
    __init__.py
    errors.py
    models.py
    base.py           # optional
    pdf.py
    excel.py
    router.py

src/customs_ai/application/
    parsing.py        # optional/coherent service location

src/customs_ai/repositories/
    source_documents.py

tests/unit/parsers/
tests/unit/repositories/
tests/integration/ or tests/unit/application/
tests/fixtures/
```

This is guidance, not a mandate. Prefer a small coherent implementation.

No parser API endpoint is required in TASK-004.

---

## 12. DEPENDENCIES

Allowed/expected lightweight runtime dependencies:

```text
pypdf
openpyxl
xlrd
```

Preferred:

```text
pypdf>=5
openpyxl>=3.1
xlrd>=2.0.1
```

Do NOT add pandas merely for parsing.

If a dependency choice materially differs, explain it in the Developer Completion Report.

---

## 13. CONSTRAINTS

1. TASK-003 must be DONE before implementation.
2. Parser input file must come from a persisted SourceDocument, not an arbitrary public filesystem path.
3. Never trust filename to infer document semantic type.
4. Never execute workbook macros or formulas.
5. No OCR in TASK-004.
6. No AI in TASK-004.
7. No customer-specific hard-coded layouts.
8. Preserve provenance boundaries.
9. Original source file remains unchanged.
10. No expensive/repeated whole-document copies when not needed.
11. No subprocess Office/LibreOffice automation.
12. Do not add an API endpoint just to expose parser internals unless Project Leader approves.

---

## 14. EDGE CASES

Must consider:

### PDF

- one-page text PDF;
- multi-page PDF;
- blank page;
- all pages blank/no local text;
- page with `extract_text()` returning `None`;
- encrypted PDF;
- malformed/corrupted PDF;
- valid PDF whose local extraction yields whitespace;
- missing stored file;
- path outside upload root.

### XLSX

- one sheet;
- multiple sheets;
- Unicode Vietnamese/Chinese strings;
- numeric values;
- dates/datetimes;
- booleans;
- formulas;
- empty cells;
- merged cells;
- hidden sheet;
- hidden row;
- hidden column;
- duplicate sheet-like names are handled by workbook rules, not parser assumptions;
- corrupted ZIP/workbook;
- file with `.xlsx` metadata but unreadable OOXML.

### XLS

- one/multiple sheets;
- strings/numbers/booleans;
- Unicode where supported;
- merged ranges;
- blank cells;
- malformed file.

### General

- unknown document ID;
- unsupported SourceDocument file type;
- original file immutable;
- parser exception does not fabricate `PARSED`;
- repository metadata update failure must not corrupt/delete source file.

---

## 15. ACCEPTANCE CRITERIA

### AC-01 — PDF text extraction

Given a synthetic PDF containing local text  
When parsed  
Then text is returned page-by-page with correct 1-based page provenance.

### AC-02 — PDF no-text detection

Given a valid PDF with no extractable text  
When parsed  
Then:

```text
has_text_layer = false
needs_ocr = true
```

and no OCR/AI call occurs.

### AC-03 — PDF page count

Parsed PDF page count equals actual PDF page count and is persisted to SourceDocument after success.

### AC-04 — PDF encrypted

Password-protected PDF that cannot be opened without a password fails deterministically with `PDF_ENCRYPTED`.

### AC-05 — PDF corrupt

Malformed PDF fails deterministically and does not mark SourceDocument as PARSED.

### AC-06 — XLSX cells

Given a synthetic XLSX with populated cells  
When parsed  
Then output includes correct sheet + A1 cell coordinates + raw typed values.

### AC-07 — Formula preservation

Given an XLSX formula cell  
When parsed  
Then the formula source is preserved and the parser does not recalculate it.

### AC-08 — XLSX metadata

Merged ranges and hidden sheet/row/column metadata are preserved where supplied.

### AC-09 — XLS support

Given a valid synthetic legacy XLS  
When parsed  
Then sheet/cell content and coordinates are returned using the XLS parser.

### AC-10 — Router

PDF/XLSX/XLS dispatch to the correct parser based on trusted `SourceDocument.file_type`.

### AC-11 — Unsupported type

CSV/DOCX/image SourceDocument passed to TASK-004 router fails `PARSER_UNSUPPORTED`.

### AC-12 — Path safety

Stored path outside `upload_root` is rejected before parsing.

### AC-13 — Source metadata

Successful PDF/Excel parse updates parser metadata/status without fabricating classification or canonical extraction data.

### AC-14 — Original immutable

Hash of source file before and after parsing is unchanged.

### AC-15 — Regression

Complete test suite passes, including all 73 TASK-001..003 tests.

### AC-16 — Scope

No OCR, LLM, classification, canonical business extraction, normalization, matching, rule engine, HS/legal logic, customer-specific adapter, or UI is introduced.

---

## 16. TEST REQUIREMENTS

### Unit Tests — Models / Router / Errors

Must cover:

- strict parser-output model validation;
- router PDF selection;
- router XLSX selection;
- router XLS selection;
- unsupported type rejection;
- missing document ID;
- missing source file;
- stored path escape rejection.

### Unit Tests — PDF

Must cover:

- synthetic text PDF;
- multi-page page boundaries;
- no-text/blank PDF;
- encrypted PDF;
- corrupted PDF;
- page count;
- text-layer flags;
- original source hash unchanged.

### Unit Tests — XLSX

Must cover:

- string/numeric/boolean cells;
- Unicode;
- multiple sheets/order;
- formula source preservation;
- merged cells;
- hidden sheet;
- hidden row;
- hidden column;
- cell coordinates;
- number format where available;
- corrupt workbook;
- original source hash unchanged.

### Unit Tests — XLS

Must cover:

- basic strings/numbers;
- sheet order;
- cell coordinates;
- merged ranges where fixture supports them;
- corrupt file;
- source unchanged.

### Repository / Application Tests

Must cover:

- parse success updates `processing_status=PARSED`;
- parser_used update;
- PDF page_count update;
- Excel sheet_count update;
- classification fields remain null;
- failed parser is not marked PARSED;
- repository update failure does not mutate/delete source file.

### Regression Tests

Run the entire suite.

Expected baseline before TASK-004:

```text
73 passed
```

Final count will be greater than 73.

Do not hard-code final expected count in implementation.

---

## 17. TEST DATA

Use only synthetic/anonymized files.

PDF and workbook fixtures may be generated programmatically or stored as tiny synthetic fixtures.

Fixtures must contain no real customer/company/document information.

Multilingual test examples may use generic strings such as:

```text
Hóa đơn thử nghiệm
测试发票
Synthetic Item
```

Do not add a heavy runtime dependency solely to generate test files.

---

## 18. OBSERVABILITY REQUIREMENTS

Safe logs may contain:

```text
document_id
file_type
parser_used
page_count/sheet_count
error code
elapsed time if already supported simply
```

Do NOT log:

```text
full PDF text
cell values
customer content
credentials
absolute source path
```

No new observability framework is required.

---

## 19. COST REQUIREMENTS

```text
AI allowed: NO
External network calls: NO
Paid services: NO
```

Local deterministic parsing only.

---

## 20. SECURITY / PRIVACY REQUIREMENTS

- Validate resolved stored path is inside configured upload root.
- Do not execute spreadsheet formulas/macros.
- Do not invoke shell/Office/LibreOffice.
- Do not modify user source files.
- Do not log parsed document contents.
- No customer data in fixtures.
- No secrets.
- Runtime data remains gitignored.
- Parser errors exposed to higher layers must not leak absolute filesystem paths.
- Handle corrupted/encrypted files without uncontrolled traceback leakage in service contracts.

---

## 21. DELIVERABLES

Developer must provide:

- parser output models;
- PDF parser;
- XLSX parser;
- XLS parser;
- parser router;
- parsing application/service orchestration;
- SourceDocument repository metadata update if required;
- dependency updates;
- unit/failure/regression tests;
- synthetic fixtures if required;
- README parser-layer documentation;
- Developer Completion Report;
- exact created/modified file list;
- local-validation commands.

---

## 22. DEFINITION OF DONE

- [ ] TASK-003 is already DONE/pushed before implementation begins
- [ ] PDF local parser implemented
- [ ] XLSX local parser implemented
- [ ] XLS local parser implemented
- [ ] parser router implemented
- [ ] page provenance preserved
- [ ] workbook/sheet/cell provenance preserved
- [ ] no-text PDF is flagged for OCR rather than OCR'd
- [ ] encrypted/corrupt PDF handled deterministically
- [ ] formula source preserved without execution
- [ ] merged/hidden Excel metadata handled
- [ ] stored-path containment enforced
- [ ] SourceDocument parser metadata updated after success
- [ ] no false PARSED status on failure
- [ ] uploaded source files remain unchanged
- [ ] all TASK-004 tests pass
- [ ] all previous 73 regression tests pass
- [ ] no unresolved CRITICAL/HIGH issues
- [ ] Gemini #2 Reviewer approved
- [ ] Project Leader approved
- [ ] no secrets/customer data committed
- [ ] ready to move to `tasks/done/`

---

## 23. DEVELOPER NOTES

Gemini #1 updates when necessary.

If a parser-library limitation prevents preserving a requested XLS field safely (for example cached formula source in old BIFF XLS), document the limitation rather than inventing data.

---

## 24. REVIEW NOTES

Gemini #2 updates during review.

---

## 25. PROJECT LEADER DECISION

Pending.
