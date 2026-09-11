# TASK-006 — Invoice Extraction

Status: IN_PROGRESS  
Priority: P1  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Created: 2026-09-11  
Updated: 2026-09-11  
Target Version: V1  
Dependencies: TASK-001..TASK-005A DONE  
Related ADR: None

---

## 1. OBJECTIVE

Implement the first canonical business-document extraction stage for `COMMERCIAL_INVOICE`.

TASK-006 must convert already-classified Invoice content into the existing canonical:

```text
Invoice
Party
InvoiceItem
CanonicalField[T]
```

while preserving raw source values, field-level provenance, extraction method, and confidence.

The task must remain layout-agnostic and deterministic-first.

TASK-006 establishes a reusable extraction architecture for later TASK-007 Packing List Extraction and TASK-008 Transport Document Extraction.

---

## 2. BACKGROUND

The repository already provides:

```text
TASK-003 → safely persisted SourceDocument
TASK-004 → local PDF / XLS / XLSX technical parsing
TASK-005 → deterministic document classification
TASK-005A → per-page scanned-PDF visual resolution
TASK-002 → strict canonical Invoice / InvoiceItem / Party schema
```

Current canonical Invoice fields are:

```text
invoice_number
invoice_date
seller
buyer
ship_to
currency
incoterm
payment_term
total_amount
freight
insurance
discount
items[]
```

Current InvoiceItem fields are:

```text
item_number
item_code
part_number
model
description
brand
manufacturer
quantity
unit
unit_price
amount
origin
weight
package_information
```

`CanonicalField[T]` already carries:

```text
raw_value
normalized_value
origin
source_document_id
page
sheet
cell
bounding_box
extraction_method
confidence
```

For `origin=EXTRACTED`, both `raw_value` and `source_document_id` are mandatory.

TASK-006 must reuse these models. Do not create a parallel Invoice schema.

---

## 3. SCOPE

TASK-006 MUST:

1. Implement a coherent `InvoiceExtractionService` under the application/extraction boundary.
2. Accept `document_id` as the main application input.
3. Load `SourceDocument` through the repository layer.
4. Require the document to have been classified as `COMMERCIAL_INVOICE`.
5. Reject `UNKNOWN`, non-Invoice, or otherwise unsafe classification state rather than extracting anyway.
6. Reuse TASK-004 parsing and TASK-005A visual resolution; do not duplicate PDF/Excel parsers or OCR.
7. Support extraction from:
   - `ParsedPdfDocument`;
   - `ResolvedPdfDocument`;
   - `ParsedWorkbook` for XLS/XLSX.
8. Preserve PDF page provenance.
9. Preserve Excel sheet + cell provenance.
10. Produce the existing canonical `Invoice`.
11. Produce zero-to-many existing canonical `InvoiceItem` records.
12. Preserve source text exactly in `raw_value` wherever a field is extracted.
13. Set `origin=EXTRACTED` for source-backed extraction.
14. Set `source_document_id` on every extracted CanonicalField.
15. Set `page` OR `sheet/cell` when the source representation allows it.
16. Populate `extraction_method` with a stable method identifier.
17. Keep confidence bounded to `[0.0, 1.0]`.
18. Never fabricate a missing value. Missing source data remains `None`.
19. Add configurable, layout-agnostic field/header aliases outside orchestration code.
20. Provide deterministic extraction for clearly labeled header fields.
21. Provide deterministic Excel item-table extraction when a table header can be identified safely from generic configured aliases.
22. PDF item extraction may support clearly detectable text tables/rows, but MUST NOT guess row structure when unsafe.
23. Add a provider-neutral semantic extraction protocol/boundary for future AI fallback.
24. The provider-neutral boundary MUST be mockable in tests.
25. Default TASK-006 runtime MUST NOT require a hosted AI/API provider.
26. If deterministic extraction is incomplete or ambiguous and no approved semantic provider is available, return/persist `NEEDS_REVIEW` rather than inventing data.
27. Add strict typed extraction result/status/error models.
28. Persist extraction records through a repository boundary.
29. Preserve extraction history rather than destructively overwriting the only prior extraction record.
30. Persist the active extraction payload in SQLite as validated canonical JSON or an equivalent strict representation.
31. Update `SourceDocument.extraction_status`.
32. Update `SourceDocument.processing_status`:
    - safe successful extraction → `EXTRACTED`;
    - material ambiguity/insufficient usable content → `NEEDS_REVIEW`;
    - deterministic system failure → `FAILED` only when the processing operation actually failed.
33. Keep parser/classification metadata unchanged.
34. Keep source files immutable.
35. Add unit, integration, failure, and full regression tests.
36. Keep all existing 178 tests passing.

---

## 4. OUT OF SCOPE

TASK-006 MUST NOT implement:

- Packing List extraction;
- Bill of Lading / AWB extraction;
- Customs Declaration extraction;
- TASK-009 full normalization;
- unit normalization/mapping;
- party-name normalization;
- country normalization;
- item matching;
- cross-document checks;
- arithmetic validation such as `qty × unit_price == amount`;
- HS classification/recommendation;
- tariff/tax logic;
- permit/legal decisions;
- customer-specific template code;
- rule engine;
- reporting UI;
- human correction workflow;
- a hosted OpenAI/Gemini/Claude production adapter;
- API-key management;
- paid model routing;
- autonomous agents;
- source-file mutation.

Do not add a vendor SDK merely to satisfy the semantic-extractor interface.

---

## 5. INPUT

Primary application input:

```text
document_id
```

Required repository state:

```text
SourceDocument exists
detected_document_type == COMMERCIAL_INVOICE
classification already completed safely
```

Content source:

```text
SourceDocument
→ TASK-004 parser
→ optional TASK-005A visual resolver for PDF pages
→ invoice extraction pipeline
```

Supported technical content:

```text
ParsedPdfDocument
ResolvedPdfDocument
ParsedWorkbook
```

---

## 6. OUTPUT

Application-level result must clearly distinguish canonical data from extraction state.

Conceptually:

```text
InvoiceExtractionResult
- extraction_id
- document_id
- status
- invoice: Invoice | None
- requires_review: bool
- issues[]
- extraction_methods[]
- extractor_version
```

Use strict Pydantic models.

Do not change the existing canonical Invoice/InvoiceItem schema merely to carry task-specific orchestration metadata.

---

## 7. FUNCTIONAL REQUIREMENTS

### FR-01 — Classification gate

Extraction is allowed only when the source document is safely classified:

```text
COMMERCIAL_INVOICE
```

Non-Invoice/UNKNOWN/unreviewed content must fail safely before business extraction.

### FR-02 — Canonical schema reuse

Use the existing models from:

```text
customs_ai.domain.schema
```

No duplicate `InvoiceV2`, `ExtractedInvoice`, or customer-specific business schema may become a second canonical source of truth.

Internal extraction-candidate models are allowed when needed, but they must map into the existing canonical model.

### FR-03 — Header fields

The deterministic layer must be able to extract clearly labeled values using configurable aliases.

At minimum design aliases for:

```text
invoice_number
invoice_date
seller.name
seller.tax_id
seller.address
buyer.name
buyer.tax_id
buyer.address
ship_to.name
ship_to.address
currency
incoterm
payment_term
total_amount
freight
insurance
discount
```

Aliases may include English / Vietnamese / Chinese examples but must remain configuration-driven and customer-neutral.

### FR-04 — Item fields

The extraction architecture must support all current InvoiceItem fields:

```text
item_number
item_code
part_number
model
description
brand
manufacturer
quantity
unit
unit_price
amount
origin
weight
package_information
```

Do not require every invoice to contain every field.

### FR-05 — PDF provenance

A value extracted from PDF content must retain the 1-based source page.

Bounding boxes are optional because the current parser/resolution contract does not guarantee field-level boxes.

### FR-06 — Excel provenance

A value extracted from Excel must preserve:

```text
sheet
cell
```

For an item row, each field should retain the actual source cell whenever deterministically known.

### FR-07 — Raw value preservation

`raw_value` must be the exact source representation used for extraction.

Do not silently replace it with normalized/canonical spelling.

### FR-08 — Safe typed parsing vs TASK-009 normalization

TASK-006 may perform only the minimum unambiguous syntactic conversion required to populate the existing typed canonical field:

```text
clearly parsed numeric literal → Decimal
clearly unambiguous date → date
source-backed string → str
```

If formatting is ambiguous, keep `raw_value` and leave `normalized_value=None` rather than guessing.

Full semantic normalization belongs to TASK-009.

Examples:

```text
"1200.50"       → Decimal("1200.50") is safe
"1,200.50"      → safe if parser logic proves the punctuation pattern
"1,200"         → do not guess decimal-vs-thousands semantics when ambiguous
"2026-09-11"    → safe ISO date
"01/02/2026"    → raw only unless date semantics are explicit from source context/config
```

### FR-09 — Missing values

Absent values:

```text
None
```

Never use:

```text
"UNKNOWN"
"N/A"
0
""
```

as fabricated business values.

### FR-10 — Confidence

Confidence must be bounded and method-aware.

Do not invent high precision such as `0.973421` without a documented scoring basis.

Deterministic exact-label extraction may use a documented stable confidence policy.

### FR-11 — Item table detection

For Excel:

- detect candidate header row using generic configured aliases;
- require enough recognized headers to avoid treating arbitrary cells as item tables;
- map columns deterministically;
- retain actual sheet/cell provenance;
- stop/skip rows using documented generic empty-row/terminator logic;
- never assume a fixed row number or customer layout.

For PDF:

- only parse rows when boundaries/columns are sufficiently clear;
- ambiguous text tables must become review-required rather than guessed.

### FR-12 — Semantic provider boundary

Provide a provider-neutral protocol/interface conceptually similar to:

```text
InvoiceSemanticExtractor
extract(...)
```

Requirements:

- business/application code depends on the protocol, not a vendor SDK;
- input must use already parsed/resolved text/structure rather than re-uploading the binary by default;
- output must be strict and source-grounded;
- tests use fake/mock providers;
- no network is required by the default composition in TASK-006.

A concrete hosted provider is deferred until separately approved.

### FR-13 — Grounding of semantic candidates

Any semantic-provider candidate accepted into canonical output must include enough source reference to validate:

```text
raw_value
source_document_id
page OR sheet/cell where applicable
confidence
method/provider id
```

Provider output without valid grounding must not become a trusted extracted CanonicalField.

### FR-14 — Review conditions

At minimum, `requires_review=True` when:

- content is unavailable/unresolved;
- classification is unsafe;
- a material field has conflicting candidates;
- a detected item table cannot be safely structured;
- semantic provider output is malformed/ungrounded;
- extraction yields no useful business content.

Missing optional fields alone must not automatically cause review.

### FR-15 — Minimum useful extraction

For a classified Commercial Invoice, extraction should be considered insufficient if it produces neither a usable invoice identity/value signal nor any safely extracted item content.

Do not manufacture fields merely to avoid `NEEDS_REVIEW`.

### FR-16 — Extraction persistence

Add a repository-backed extraction record.

Recommended minimum data:

```text
extraction_id
document_id
document_type
schema_version
extractor_version
status
payload_json
requires_review
created_at
is_active
```

Preserve prior extraction records by deactivating old active records rather than deleting them when a new extraction is stored.

Use a transaction for active-record replacement.

### FR-17 — SourceDocument metadata

On success/review:

```text
extraction_status
processing_status
```

must be updated consistently through the repository boundary.

Do not change:

```text
file_hash
stored_path
parser_used
page_count
sheet_count
detected_document_type
classification_confidence
```

### FR-18 — Failure atomicity

If extraction persistence fails:

- do not falsely report success;
- do not partially mark SourceDocument as extracted;
- do not modify the source file.

### FR-19 — Idempotency / repeat extraction

Repeated extraction of the same source must remain safe.

It may create a new history record, but there must be exactly one active extraction for the document after a successful transaction.

### FR-20 — Production composition

Provide a real factory/composition path for Invoice extraction.

Vision-disabled mode must still work for native-text PDF and Excel.

Importing the application must not initialize/download heavy models or make network calls.

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- Python >= 3.12 compatible.
- Python 3.13.14 on the user's Windows machine remains authoritative.
- Pydantic models use strict/forbid-extra policy where appropriate.
- CWD-independent configuration.
- Deterministic behavior for deterministic inputs.
- No source mutation.
- No customer-specific layout hard-coding.
- No hidden external network access.
- No content-heavy logs.
- SQLite through repository boundaries.
- Existing modular-monolith architecture preserved.
- No new framework/orchestration dependency without explicit need.

---

## 9. BUSINESS RULES

TASK-006 performs extraction only.

It MUST NOT decide whether:

- invoice math is correct;
- currency is legally valid;
- Incoterm is appropriate;
- item quantity agrees with Packing List;
- origin is correct;
- HS code is correct;
- tax treatment is correct.

Those are later normalization/matching/rule tasks.

---

## 10. DATA MODEL IMPACT

### Existing canonical models

Reuse unchanged unless an actual source-of-truth defect is discovered:

```text
CanonicalField
Party
Invoice
InvoiceItem
ValueOrigin
```

A canonical-schema change requires explicit Project Leader approval before implementation.

### New task-specific models

Allowed examples:

```text
ExtractionStatus
ExtractionIssue
InvoiceExtractionResult
DocumentExtractionRecord
internal candidate models
semantic provider request/response models
```

### Database

TASK-006 may add a `document_extractions` table and the minimal repository methods needed to persist extraction history.

Do not introduce PostgreSQL/migrations framework merely for this task.

---

## 11. FILES / MODULES EXPECTED

Likely modules:

```text
config/invoice_extraction.yaml

src/customs_ai/extraction/
    __init__.py
    enums.py
    errors.py
    models.py
    config.py
    deterministic.py
    mapper.py
    service.py
    semantic.py

src/customs_ai/repositories/
    extractions.py

src/customs_ai/application/
    composition.py              # extend factory wiring carefully

src/customs_ai/repositories/database.py
src/customs_ai/repositories/source_documents.py

tests/unit/extraction/
tests/integration/test_invoice_extraction_flow.py
```

Exact file split may differ if the Developer can keep cohesion higher without breaking architecture.

---

## 12. CONSTRAINTS

- Source of truth priority remains Constitution → Master Spec → Architecture → Data Schema → Task → Implementation.
- Do not modify the canonical schema casually.
- Do not duplicate parser/OCR logic.
- Do not call the classifier to "re-decide" business fields.
- Do not infer from filename.
- Do not parse source binaries again inside a semantic provider if resolved technical content is already available.
- Do not log full invoice content.
- Do not add OpenAI/Gemini/Claude SDK in TASK-006.
- Do not add customer-specific invoice code.
- Do not introduce TASK-009 normalization logic.
- Do not introduce TASK-010 matching logic.
- Do not introduce TASK-011/012 checks.

---

## 13. EDGE CASES

Must account for:

- SourceDocument not found;
- document not classified yet;
- document classified as non-Invoice;
- classification `UNKNOWN`;
- native PDF Invoice;
- scanned Invoice resolved by TASK-005A;
- unresolved scanned page;
- mixed PDF where one page remains unresolved;
- multi-page Invoice;
- repeated labels on different pages;
- multiple numbers near `Invoice No`;
- seller/buyer both containing addresses/tax IDs;
- multilingual English/Vietnamese/Chinese labels;
- blank fields;
- optional freight/insurance/discount absent;
- decimal commas/thousands punctuation ambiguity;
- ambiguous date;
- negative discount values;
- Excel formulas;
- merged Excel headers;
- hidden rows/sheets;
- two possible item tables;
- subtotal/total rows that resemble items;
- multiline item description;
- item without item code but with description/model;
- table with quantity but no unit price;
- zero quantity/price as actual source values;
- semantic provider unavailable;
- malformed semantic provider output;
- provider candidate with no provenance;
- persistence failure;
- repeated extraction;
- original file hash unchanged.

---

## 14. ACCEPTANCE CRITERIA

### AC-01 — Classification gate

Non-`COMMERCIAL_INVOICE` documents are not extracted as Invoice.

### AC-02 — Existing canonical schema

Successful output validates as the existing `Invoice` model without undeclared fields.

### AC-03 — PDF header extraction

A synthetic PDF Invoice with clear labels produces correctly grounded canonical header fields with page provenance.

### AC-04 — Excel header extraction

A synthetic Excel Invoice with clear cells produces grounded canonical header fields with sheet/cell provenance.

### AC-05 — Excel items

A generic synthetic Excel item table is detected and mapped without fixed row/customer assumptions.

### AC-06 — Raw preservation

Extracted `raw_value` exactly matches the source representation.

### AC-07 — Missing-value safety

Missing fields remain `None`; no placeholders are fabricated.

### AC-08 — Typed safety

Safe numeric/date literals are typed correctly; ambiguous numeric/date forms are not guessed.

### AC-09 — Scanned handoff

A safely resolved scanned Invoice can be extracted from `ResolvedPdfDocument` without re-running a hosted service or bypassing TASK-005A boundaries.

### AC-10 — Unresolved visual content

Material unresolved content routes to `NEEDS_REVIEW`, not fabricated extraction.

### AC-11 — No table guessing

Ambiguous item-table structure does not create invented InvoiceItem rows.

### AC-12 — Provenance

Every `EXTRACTED` CanonicalField has `raw_value`, `source_document_id`, and location provenance when available.

### AC-13 — Extraction history

Successful re-extraction preserves historical records and leaves exactly one active record.

### AC-14 — Source metadata

Successful extraction updates only allowed extraction/processing metadata and does not alter parser/classification metadata.

### AC-15 — Source immutability

Source file hash is unchanged before/after extraction.

### AC-16 — Provider independence

Semantic fallback is represented by a mockable provider-neutral contract; core code contains no vendor SDK dependency.

### AC-17 — No network by default

Full TASK-006 tests pass with no Internet, no hosted AI API, no model download, and no real socket required.

### AC-18 — Regression

All pre-TASK-006 tests remain green.

Authoritative pre-TASK-006 baseline:

```text
178 passed
0 failed
0 skipped
2 warnings
```

Final test count must be greater than 178.

### AC-19 — No scope creep

No normalization engine, item matching, rule engine, HS/legal logic, Packing/Bill extraction, UI, or hosted AI adapter is introduced.

---

## 15. TEST REQUIREMENTS

### Unit — extraction models/config

Cover:

- strict models;
- status enum;
- confidence bounds;
- malformed alias config;
- CWD-independent config;
- multilingual aliases;
- duplicate/ambiguous alias handling.

### Unit — deterministic header extraction

Cover at minimum:

- invoice number;
- invoice date;
- seller/buyer;
- currency;
- incoterm;
- payment term;
- total amount;
- freight/insurance/discount;
- repeated labels;
- ambiguous date;
- safe/ambiguous numeric punctuation.

### Unit — item extraction

Cover:

- header detection;
- minimum safe header evidence;
- generic Excel row extraction;
- actual cell provenance;
- blank row termination;
- subtotal/total suppression;
- multiline descriptions where representable;
- optional item fields;
- zero numeric values;
- no fixed customer row index.

### Unit — canonical mapping

Cover:

- `origin=EXTRACTED`;
- raw preserved;
- source_document_id required;
- PDF page;
- Excel sheet/cell;
- extraction_method;
- confidence;
- missing values stay `None`.

### Unit — semantic boundary

Use fake providers only:

- valid grounded candidate;
- malformed result;
- missing provenance;
- provider unavailable;
- provider disagreement / ambiguous candidate.

No external socket.

### Repository

Cover:

- create extraction;
- get active extraction;
- preserve history;
- one active record after repeat;
- transaction rollback on failure;
- SourceDocument extraction metadata update;
- parser/classification metadata unchanged.

### Integration

At minimum:

```text
native PDF
→ existing parse
→ Invoice extraction
→ canonical Invoice
→ persisted extraction
```

```text
Excel
→ existing parse
→ deterministic table extraction
→ canonical Invoice/items
→ persisted extraction
```

```text
ResolvedPdfDocument
→ extraction
```

```text
non-Invoice
→ rejected
```

```text
ambiguous/unusable
→ NEEDS_REVIEW
```

### Failure/security

Cover:

- missing document;
- unsafe document type;
- parser/resolver failure;
- persistence failure;
- source immutable;
- no path leakage;
- no invoice-content logging.

### Regression

Run:

```text
python -m pytest -v
```

No dependency-based skips may be introduced to make the suite green.

---

## 16. TEST DATA

Use only synthetic/anonymized data.

Include representative multilingual examples:

```text
COMMERCIAL INVOICE
Invoice No: INV-TEST-006
Số hóa đơn: INV-VN-006
发票号码: CN-006
```

Use generic synthetic companies/items only.

Do not commit real customer invoices or identifying customer information.

---

## 17. OBSERVABILITY REQUIREMENTS

Safe logs may include:

```text
document_id
extraction_id
status
method id
item count
safe error code
duration
```

Do NOT log:

```text
full invoice text
full item descriptions
seller/buyer raw values
tax IDs
addresses
Excel cell contents
OCR/VLM page text
absolute source path
provider raw response
credentials
raw exception text from external/provider boundaries
```

---

## 18. COST REQUIREMENTS

```text
Hosted AI allowed: NO in TASK-006 default implementation
External network calls: NO
Paid services: NO
New vendor SDK: NO
```

Provider-neutral semantic extraction boundary: YES.

The purpose is to make future AI fallback pluggable without coupling TASK-006 to a vendor before provider/cost/privacy policy is approved.

---

## 19. SECURITY / PRIVACY REQUIREMENTS

- source file immutable;
- upload-root path containment preserved;
- no secrets;
- no production customer fixtures;
- no invoice content in normal logs;
- no hosted upload;
- semantic provider interface must accept already-resolved content by default;
- strict Pydantic validation before persistence;
- SQL parameterization through repository layer;
- no code/macro execution from documents;
- no customer-specific confidential template logic in source.

---

## 20. DEPENDENCIES

Required complete:

```text
TASK-001 DONE
TASK-002 DONE
TASK-003 DONE
TASK-004 DONE
TASK-005 DONE
TASK-005A DONE
```

Current repository baseline:

```text
178 passed
0 failed
0 skipped
2 warnings
```

---

## 21. DELIVERABLES

Developer must provide:

- TASK-006 source implementation;
- invoice extraction alias/config;
- extraction persistence/repository support;
- tests;
- README documentation;
- exact created/modified file list;
- local validation commands/results;
- known limitations;
- Developer Completion Report.

Developer must not move TASK-006 to `tasks/done`.

---

## 22. DEFINITION OF DONE

- [ ] TASK-001..005A remain DONE
- [ ] Classification gate implemented
- [ ] Existing Invoice/InvoiceItem/Party schema reused
- [ ] Deterministic header extraction implemented
- [ ] Safe Excel item-table extraction implemented
- [ ] PDF provenance preserved
- [ ] Excel sheet/cell provenance preserved
- [ ] Missing values not fabricated
- [ ] Safe typed parsing separated from TASK-009 normalization
- [ ] Provider-neutral semantic boundary implemented
- [ ] No hosted AI/network dependency introduced
- [ ] Extraction history persisted
- [ ] SourceDocument extraction status persisted safely
- [ ] Source immutable
- [ ] Full suite >178 tests and green
- [ ] No dependency-based skips
- [ ] No unresolved CRITICAL/HIGH
- [ ] Gemini #2 APPROVE
- [ ] Project Leader APPROVE
- [ ] No secrets/customer data
- [ ] Ready to move to `tasks/done/`

---

## 23. DEVELOPER NOTES

Gemini #1 updates when necessary.

If a requirement conflicts with the actual current schema/code, do not silently reinterpret it. Report the conflict to Project Leader.

Do not add a hosted AI provider just because arbitrary PDF layout extraction is difficult. Return `NEEDS_REVIEW` for unsupported ambiguity and keep the provider boundary clean.

---

## 24. REVIEW NOTES

Gemini #2 updates during review.

---

## 25. PROJECT LEADER DECISION

Pending.
