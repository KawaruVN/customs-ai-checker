# TASK-003 — File Ingestion + Hashing

Status: IN_PROGRESS  
Priority: P1  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Created: 2026-09-11  
Updated: 2026-09-11  
Target Version: V1  
Dependencies: TASK-001 — Project Foundation (DONE); TASK-002 — Canonical Data Schema (DONE)  
Related ADR: None

---

## 1. OBJECTIVE

Build the V1 file-ingestion path that receives a document for a Shipment, validates the upload, determines/validates its file type, enforces a configurable size limit, computes SHA-256, detects same-file duplicates inside the same Shipment, stores the file safely on local disk, persists `SourceDocument` metadata in SQLite through a repository boundary, and exposes the upload through the FastAPI API.

TASK-003 ends at safe ingestion and metadata persistence. It does not parse document business content.

---

## 2. BACKGROUND

TASK-001 established the Python/FastAPI/config/test foundation.

TASK-002 established the canonical document data contract.

The architecture requires the ingestion module to receive a file, validate it, determine MIME/type, enforce size limits, compute SHA-256, detect duplicates, store the file, create `SourceDocument`, and then make the document available for the later parser pipeline.

The Master Specification requires each uploaded file to create a `SourceDocument`, and requires file hashes for duplicate detection and caching.

This task implements that deterministic boundary before TASK-004 local PDF/Excel parsers.

---

## 3. SCOPE

TASK-003 MUST:

1. Add a `SourceDocument` domain/data model for ingestion metadata.
2. Add document processing/status enums needed for the SourceDocument metadata contract.
3. Accept a file through:
   `POST /shipments/{shipment_id}/documents`
4. Support the V1 input extensions:
   - `.pdf`
   - `.xls`
   - `.xlsx`
   - `.csv`
   - `.docx`
   - `.jpg`
   - `.jpeg`
   - `.png`
5. Validate:
   - Shipment ID as a safe storage/path identifier;
   - filename presence;
   - supported extension;
   - upload not empty;
   - configurable maximum upload size;
   - declared MIME when supplied;
   - basic content signature/container consistency where deterministic local checks are practical.
6. Compute SHA-256 from the actual uploaded bytes.
7. Detect duplicate content by `(shipment_id, file_hash)`.
8. Avoid creating a second SourceDocument or second stored file for the same hash in the same Shipment.
9. Allow the same hash in a different Shipment to create a distinct SourceDocument.
10. Store accepted files under a generated document identifier rather than the user filename.
11. Use a storage structure conceptually equivalent to:
    `data/uploads/{shipment_id}/{document_id}/original.<validated_extension>`
12. Preserve sanitized original filename in metadata.
13. Persist SourceDocument metadata to SQLite behind a repository interface/boundary.
14. Enforce a database uniqueness constraint equivalent to `(shipment_id, file_hash)`.
15. Return an upload response containing at minimum:
    - document_id
    - shipment_id
    - status
    - sha256/file_hash
    - mime_type
    - file_size
    - is_duplicate
16. On duplicate upload inside the same Shipment, return the existing `document_id` and clearly mark the response as duplicate.
17. Add configurable paths/limits without reintroducing CWD-dependent path bugs.
18. Add deterministic error codes.
19. Add unit, integration, failure, and regression tests.
20. Keep all existing TASK-001/TASK-002 tests passing.

---

## 4. OUT OF SCOPE

TASK-003 MUST NOT implement:

- PDF text extraction;
- Excel workbook parsing;
- CSV semantic parsing;
- DOCX content parsing;
- OCR;
- image OCR/vision;
- document classification;
- AI/LLM calls;
- canonical Invoice/Packing/Transport/Declaration extraction;
- normalization algorithms;
- item matching;
- rule/check engine behavior;
- HS classification/recommendation;
- legal decisions;
- customer-specific adapters;
- UI;
- human correction;
- report generation;
- cache reuse/extraction reuse logic beyond recording file hash;
- revised-document semantic detection;
- parser routing behavior beyond a clean handoff-ready SourceDocument.

Deep corruption/encryption parsing belongs to TASK-004 or the relevant parser task. TASK-003 performs only safe ingestion-level validation.

---

## 5. INPUT

API path input:

```text
shipment_id
```

Multipart upload input:

```text
file binary
original filename
declared content type / MIME if supplied by client
```

Supported extensions:

```text
.pdf
.xls
.xlsx
.csv
.docx
.jpg
.jpeg
.png
```

---

## 6. OUTPUT

Successful new upload should return an object conceptually equivalent to:

```json
{
  "document_id": "DOC-<generated-id>",
  "shipment_id": "SHP-2026-000001",
  "status": "UPLOADED",
  "sha256": "<64-char lowercase hex>",
  "mime_type": "application/pdf",
  "file_size": 12345,
  "is_duplicate": false
}
```

Same-file duplicate in the same Shipment should return the existing document identity, for example:

```json
{
  "document_id": "DOC-<existing-id>",
  "shipment_id": "SHP-2026-000001",
  "status": "UPLOADED",
  "sha256": "<same hash>",
  "mime_type": "application/pdf",
  "file_size": 12345,
  "is_duplicate": true
}
```

The exact response model may include additional safe metadata, but must not expose absolute local filesystem paths.

---

## 7. FUNCTIONAL REQUIREMENTS

### FR-01 — SourceDocument model

Create a SourceDocument representation containing at minimum:

```text
document_id
shipment_id
original_filename
file_type
mime_type
file_hash
file_size
stored_path
upload_time
processing_status
detected_document_type
classification_confidence
page_count
sheet_count
parser_used
extraction_status
```

Fields that belong to later processing phases should be nullable initially.

`original_filename` is metadata only and MUST NOT be the primary identifier or storage filename.

### FR-02 — Generated document ID

Every non-duplicate accepted upload MUST receive a generated unique document ID.

Recommended format:

```text
DOC-<UUID-derived-value>
```

Sequential IDs are not required.

### FR-03 — Shipment ID safety

Because the storage layout contains `shipment_id`, it MUST be validated as a safe path segment.

The implementation must reject path traversal or unsafe values such as:

```text
../x
..\x
/x
C:\x
```

A conservative identifier pattern such as letters, digits, `_`, and `-` is acceptable.

### FR-04 — Supported types

The ingestion layer MUST allow only the V1 extensions listed in this task.

Unsupported extension MUST produce:

```text
FILE_UNSUPPORTED
```

### FR-05 — MIME/content validation

The system MUST not rely only on the filename extension.

The implementation must perform deterministic local validation appropriate for the format, without calling an external service.

Expected minimum behavior:

- PDF: `%PDF-` signature.
- PNG: PNG signature.
- JPEG: JPEG signature.
- XLS: OLE Compound File signature plus supported extension/MIME consistency.
- XLSX/DOCX: ZIP container inspection sufficient to distinguish spreadsheet (`xl/`) from Word (`word/`) OOXML content.
- CSV: conservative text/CSV validation; reject clearly binary content.

The implementation may use standard library logic or a small dependency only if justified. Prefer no additional MIME-sniffing dependency.

Client-declared MIME must not override contradictory local evidence.

MIME/content mismatch MUST produce a clear code such as:

```text
FILE_MIME_MISMATCH
```

or

```text
FILE_INVALID_CONTENT
```

The chosen distinction must be documented and tested.

### FR-06 — Empty file

Zero-byte upload MUST be rejected:

```text
FILE_EMPTY
```

### FR-07 — Configurable size limit

Maximum upload size MUST be configurable through project settings.

Default V1 limit:

```text
50 MiB
```

Suggested setting:

```text
MAX_UPLOAD_SIZE_MB=50
```

or an equivalent clearly named setting.

The default path/limit configuration MUST be CWD-independent.

Oversized upload MUST be rejected:

```text
FILE_TOO_LARGE
```

The system must enforce the limit while streaming/reading, not only after the entire file has already been persisted.

### FR-08 — SHA-256

Every accepted upload MUST be hashed from its actual bytes using SHA-256.

The stored hash MUST be lowercase 64-character hexadecimal.

Hashing should occur in chunks rather than requiring the full file to be loaded into memory.

### FR-09 — Duplicate inside same Shipment

If `(shipment_id, file_hash)` already exists:

- no second SourceDocument row is created;
- no second final stored file is created;
- the API returns the existing document identity;
- response clearly indicates `is_duplicate = true`.

### FR-10 — Same file in another Shipment

If the same file hash exists under a different Shipment, it is NOT considered a duplicate for this task.

A new SourceDocument MUST be created for that other Shipment.

### FR-11 — Safe local storage

Accepted files MUST be stored under the configured upload root.

Storage path MUST be based on validated/generate identifiers, not the raw user filename.

Conceptual layout:

```text
{upload_root}/{shipment_id}/{document_id}/original.<validated_extension>
```

The implementation MUST ensure the resolved final path remains under the configured upload root.

### FR-12 — Filename sanitization

Preserve a sanitized basename as `original_filename`.

Path components from a submitted filename must not be preserved.

Examples:

```text
../../invoice.pdf -> invoice.pdf
C:\temp\invoice.pdf -> invoice.pdf
```

Reject filenames containing invalid/null content if they cannot be sanitized safely.

Unicode filenames are allowed if otherwise safe.

### FR-13 — SQLite repository boundary

Database access MUST go through a repository abstraction.

At minimum provide operations equivalent to:

```text
create_source_document(...)
get_by_document_id(...)
find_by_shipment_and_hash(...)
```

SQLite implementation may use Python standard-library `sqlite3`; SQLAlchemy is not required.

The SourceDocument table MUST enforce uniqueness for:

```text
(shipment_id, file_hash)
```

### FR-14 — Persistence consistency

The implementation MUST avoid leaving a successful-looking database record when file persistence failed.

It SHOULD also clean temporary/final files if metadata persistence fails.

Tests must cover at least one storage/repository failure path or equivalent cleanup invariant.

### FR-15 — Upload time

Upload time MUST use timezone-aware UTC datetime.

### FR-16 — Initial processing metadata

For a newly ingested document:

```text
processing_status = UPLOADED
```

Later-phase fields such as:

```text
detected_document_type
classification_confidence
page_count
sheet_count
parser_used
extraction_status
```

remain `None` unless known without parsing.

TASK-003 MUST NOT fabricate them.

### FR-17 — API behavior

Add:

```text
POST /shipments/{shipment_id}/documents
```

Recommended status behavior:

- new accepted document: HTTP 201;
- same-shipment duplicate: HTTP 200;
- invalid upload: appropriate 4xx response with deterministic application error code.

Do not expose stack traces or filesystem paths.

### FR-18 — Error contract

At minimum support deterministic errors:

```text
INVALID_SHIPMENT_ID
FILE_EMPTY
FILE_TOO_LARGE
FILE_UNSUPPORTED
FILE_MIME_MISMATCH and/or FILE_INVALID_CONTENT
INGESTION_FAILED
```

Exact HTTP mapping must be documented and covered by integration tests.

### FR-19 — No parser execution

Successful ingestion ends after metadata/file persistence.

TASK-003 must not extract business text or classify the document.

### FR-20 — Handoff readiness

The persisted SourceDocument must contain enough metadata for TASK-004 to locate the stored file and process it later.

No parser invocation is required in TASK-003.

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- NFR-01: AI allowed: NO.
- NFR-02: No external network calls.
- NFR-03: Do not log document contents.
- NFR-04: Do not log credentials/secrets.
- NFR-05: Use chunked I/O for hashing/size enforcement.
- NFR-06: Do not execute uploaded content or macros.
- NFR-07: Upload directories and database/runtime data remain outside Git-tracked production data.
- NFR-08: Keep ingestion deterministic and testable.
- NFR-09: Business logic must not live directly in FastAPI route handlers.
- NFR-10: Database-specific access remains behind repository boundary.
- NFR-11: No large framework dependency.
- NFR-12: Existing canonical schema behavior must not regress.
- NFR-13: Python remains compatible with project baseline `>=3.12`, including the user's Python 3.13 environment.

---

## 9. BUSINESS RULES

None.

File validation/duplicate behavior in this task is technical system behavior, not a customs/legal rule.

---

## 10. DATA MODEL IMPACT

Creates:

```text
SourceDocument
DocumentProcessingStatus (or equivalent)
Upload/Ingestion response model as appropriate
SourceDocument repository persistence schema
```

TASK-003 MUST NOT alter the existing Invoice/PackingList/TransportDocument/CustomsDeclaration canonical field semantics from TASK-002.

This is not a breaking change to the canonical business schema and does not require an ADR.

---

## 11. FILES / MODULES EXPECTED

Expected affected areas:

```text
config/app.yaml
.env.example
pyproject.toml
src/customs_ai/config.py
src/customs_ai/main.py
src/customs_ai/api/routes/
src/customs_ai/domain/
src/customs_ai/ingestion/
src/customs_ai/repositories/
tests/unit/
tests/integration/
```

Possible implementation structure:

```text
src/customs_ai/domain/
  documents.py

src/customs_ai/ingestion/
  errors.py
  file_types.py
  service.py

src/customs_ai/repositories/
  source_documents.py

src/customs_ai/api/routes/
  documents.py
```

This layout is guidance, not a mandate. Prefer a small coherent implementation over excessive file fragmentation.

A small required dependency such as `python-multipart` is acceptable for FastAPI multipart uploads.

---

## 12. CONSTRAINTS

1. Follow source-of-truth priority:
   `PROJECT_CONSTITUTION.md` > `MASTER_SPEC.md` > `ARCHITECTURE.md` > `DATA_SCHEMA.md` > Task > Implementation.
2. Do not use filename as primary identifier.
3. Do not trust extension alone.
4. Do not trust client MIME alone.
5. Do not use raw shipment ID or raw filename to escape configured storage root.
6. Do not load arbitrary-size files fully into memory.
7. Do not parse business content.
8. Do not classify document type.
9. Do not call AI.
10. Do not create customer-specific ingestion paths.
11. Do not commit runtime uploads or SQLite database files.
12. Do not expose absolute storage path in public API response.
13. Do not modify TASK-002 canonical semantics to make ingestion easier.
14. Do not silently swallow repository/storage errors.

---

## 13. EDGE CASES

Developer and Reviewer MUST consider at least:

- zero-byte file;
- unsupported extension;
- uppercase extension (`.PDF`);
- filename with multiple dots;
- filename with Unicode;
- filename containing path traversal;
- invalid shipment ID/path traversal;
- MIME contradicting extension;
- PDF extension with non-PDF bytes;
- XLSX renamed DOCX and vice versa;
- clearly binary file renamed CSV;
- exactly-at-limit file;
- one byte over size limit;
- same bytes uploaded twice to same Shipment;
- same bytes uploaded to different Shipments;
- duplicate filenames with different content;
- duplicate content with different filenames;
- database uniqueness race/constraint;
- database failure after temporary file write;
- storage failure;
- interrupted/partial temporary file;
- encrypted PDF: ingestion may store it if the basic PDF signature is valid; deep encryption detection belongs to parser task;
- syntactically valid signature but deeply corrupted document: parser task owns deep structural validation.

---

## 14. ACCEPTANCE CRITERIA

### AC-01 — Valid upload

Given a valid supported file  
When uploaded to a valid Shipment ID  
Then the system stores it safely, persists one SourceDocument, and returns a generated `document_id`.

### AC-02 — SHA-256

Given known file bytes  
When ingested  
Then the stored SHA-256 exactly matches the standard SHA-256 of those bytes.

### AC-03 — Duplicate same Shipment

Given a file already exists in Shipment A  
When the same bytes are uploaded again to Shipment A  
Then no new SourceDocument/final file is created and the existing document ID is returned with `is_duplicate=true`.

### AC-04 — Same hash different Shipment

Given a file exists in Shipment A  
When the same bytes are uploaded to Shipment B  
Then a distinct SourceDocument is created for Shipment B.

### AC-05 — Oversize

Given an upload larger than configured maximum  
When ingested  
Then it is rejected with `FILE_TOO_LARGE` and no final file/database record remains.

### AC-06 — Empty

Given a zero-byte upload  
When ingested  
Then it is rejected with `FILE_EMPTY`.

### AC-07 — Unsupported file

Given an unsupported extension  
When ingested  
Then it is rejected with `FILE_UNSUPPORTED`.

### AC-08 — Content mismatch

Given a supported extension whose bytes clearly belong to a conflicting/invalid format  
When ingested  
Then it is rejected with deterministic MIME/content error.

### AC-09 — Path safety

Given malicious filename or Shipment path input  
When ingested  
Then no path can escape configured upload root.

### AC-10 — Metadata

Given a successful new upload  
When SourceDocument is read back from the repository  
Then required metadata, hash, file size, safe stored path, MIME/type, and upload time are available while later parser/classification fields remain null.

### AC-11 — Persistence

Given the application/repository is recreated using the same SQLite database  
When a persisted SourceDocument is queried  
Then it remains available.

### AC-12 — API

Given a multipart upload through FastAPI  
When valid  
Then endpoint returns the documented response/status code.

### AC-13 — API duplicate

Given the same file is uploaded twice through the API to the same Shipment  
Then the second response is non-error, explicitly duplicate, and references the existing document ID.

### AC-14 — Failure cleanup

Given repository or storage persistence fails  
When ingestion aborts  
Then it does not leave a misleading successful SourceDocument and temporary artifacts are cleaned as reasonably possible.

### AC-15 — Regression

Given the completed TASK-003 implementation  
When `python -m pytest -v` is executed in the real repository  
Then all TASK-001, TASK-002, and TASK-003 tests pass.

### AC-16 — Scope

Given the final diff  
When reviewed  
Then TASK-003 contains no OCR, parser extraction, document classification, AI calls, canonical business extraction, matching, rule engine, HS/legal decision logic, or UI.

---

## 15. TEST REQUIREMENTS

### Unit Tests

Must include meaningful assertions for at least:

- SourceDocument model validation;
- generated document ID not based on filename;
- known SHA-256;
- filename sanitization;
- Unicode filename;
- safe Shipment ID;
- invalid Shipment ID;
- supported extension normalization/case handling;
- PDF signature;
- PNG signature;
- JPEG signature;
- XLS/compound signature;
- XLSX vs DOCX ZIP distinction;
- CSV text validation;
- binary-as-CSV rejection;
- empty upload;
- size exactly at limit;
- size one byte over limit;
- duplicate same Shipment;
- same hash different Shipment;
- same filename different bytes;
- different filename same bytes;
- repository persistence;
- unique `(shipment_id, file_hash)`;
- failure cleanup/rollback;
- upload/storage/config paths remain CWD-independent.

### Integration Tests

Must include at least:

- `POST /shipments/{shipment_id}/documents` valid upload;
- API duplicate upload;
- invalid Shipment ID;
- unsupported extension;
- empty file;
- oversized file using test-configured small limit;
- MIME/content mismatch;
- API response does not leak absolute `stored_path`;
- existing `/health` still passes.

### Failure Tests

Must cover:

- storage failure;
- repository failure or uniqueness conflict;
- invalid/contradictory file content;
- oversized stream;
- unsafe path input.

### Regression Tests

Run the complete repository suite.

---

## 16. TEST DATA

Use only synthetic in-memory/small fixture data.

Recommended fixtures:

```text
minimal PDF-signature bytes
small PNG/JPEG signature fixtures
synthetic OOXML ZIP containers with xl/ or word/ entries
small CSV text
small OLE-signature fixture for XLS ingestion validation
```

Do not commit real customer documents.

No test fixture needs to contain actual customs/customer data.

---

## 17. OBSERVABILITY REQUIREMENTS

Log only technical metadata necessary for operations, for example:

```text
document_id
shipment_id
file_size
mime_type
processing outcome
error_code
```

Do NOT log:

```text
file contents
full extracted text
API keys
credentials
sensitive document payload
```

Do not emit absolute local storage paths at normal INFO level or in public API errors.

---

## 18. COST REQUIREMENTS

AI allowed: NO

External network/API calls: NO

Preferred implementation:

```text
standard library + existing project dependencies
```

Allowed new dependency:

```text
python-multipart
```

only as needed for FastAPI multipart upload support.

---

## 19. SECURITY / PRIVACY REQUIREMENTS

- Reject path traversal in Shipment ID.
- Sanitize submitted filename to basename.
- Store by generated document ID, not user filename.
- Ensure resolved storage destination remains inside upload root.
- Never execute uploaded content/macros.
- Do not trust extension alone.
- Do not trust client MIME alone.
- Do not expose absolute filesystem paths in API.
- Do not commit uploads or `app.db`.
- Use synthetic test files.
- Enforce max size while reading.
- Clean temporary files after rejection/failure.
- Keep upload/storage directories non-public.

---

## 20. DEPENDENCIES

Depends on:

```text
TASK-001 — Project Foundation (DONE)
TASK-002 — Canonical Data Schema (DONE)
```

TASK-004 Local PDF/Excel Parsers depends on TASK-003 because it needs safely persisted SourceDocuments and stored files.

---

## 21. DELIVERABLES

Developer must provide:

- SourceDocument domain/data model;
- ingestion service;
- local file type/content validation;
- chunked SHA-256/size enforcement;
- safe local storage;
- SQLite SourceDocument repository;
- upload API endpoint;
- deterministic error model;
- config updates;
- required dependency update if any;
- unit/integration/failure tests;
- documentation/README update for upload endpoint and runtime paths;
- Developer Completion Report;
- exact list of files changed;
- local-validation handoff command.

Gemini #1 must NOT fabricate pytest output if it cannot execute tests.

---

## 22. DEFINITION OF DONE

- [ ] TASK-002 is already DONE/pushed before TASK-003 implementation begins
- [ ] SourceDocument contract implemented
- [ ] upload API implemented
- [ ] supported type validation implemented
- [ ] size limit configurable
- [ ] SHA-256 chunked hashing implemented
- [ ] same-Shipment duplicate detection implemented
- [ ] same-hash different-Shipment behavior correct
- [ ] safe local storage implemented
- [ ] SQLite repository boundary implemented
- [ ] persistence/failure cleanup tested
- [ ] security/path tests pass
- [ ] no parser/OCR/AI scope creep
- [ ] complete local pytest suite passes
- [ ] no unresolved CRITICAL/HIGH issues
- [ ] Gemini #2 Reviewer approved
- [ ] Project Leader approved
- [ ] no secrets/customer data committed
- [ ] ready to move to `tasks/done/`

---

## 23. DEVELOPER NOTES

Gemini #1 updates when necessary.

If a requirement would require parsing document business content to validate it deeply, stop at safe ingestion-level validation and leave deep parsing to TASK-004.

---

## 24. REVIEW NOTES

Gemini #2 updates during review.

---

## 25. PROJECT LEADER DECISION

Pending.
