# TASK-002 â€” Canonical Data Schema

Status: DONE  
Priority: P1  
Owner: Gemini #1 â€” Main Developer  
Reviewer: Gemini #2 â€” Reviewer / QA  
Created: 2026-09-11  
Updated: 2026-09-11  
Target Version: V1  
Dependencies: TASK-001 â€” Project Foundation (DONE)  
Related ADR: None

---

## 1. OBJECTIVE

Define and implement the V1 canonical data contract used by downstream Customs AI Checker modules so that data from different customer layouts can be represented consistently without losing raw values, provenance, or the distinction between extracted and inferred information.

The task must produce both:

1. an authoritative human-readable schema document at `docs/DATA_SCHEMA.md`; and
2. validated Pydantic domain models representing that schema.

The schema must be sufficiently stable for TASK-003 onward, while remaining intentionally limited to V1 needs.

---

## 2. BACKGROUND

`TASK-001` established the Python/FastAPI project foundation.

The architecture requires downstream logic to work with a canonical model instead of customer-specific layouts. The Rule Engine must reason about semantic fields such as `invoice.total_amount` and `invoice.items[].quantity`, not about fixed coordinates or customer templates.

The project also requires field-level provenance. Normalization must not destroy raw source data. Information that actually appears in a document must be distinguishable from information inferred by the system.

This task establishes those contracts before ingestion, parsing, extraction, normalization, matching, and checking modules are implemented.

---

## 3. SCOPE

TASK-002 MUST:

1. Create `docs/DATA_SCHEMA.md` as the V1 canonical schema specification.
2. Implement Pydantic v2 domain models under `src/customs_ai/domain/`.
3. Define a reusable field/provenance representation that preserves at minimum:
   - raw value;
   - normalized value;
   - origin (`EXTRACTED`, `INFERRED`, and manual input support);
   - source document reference when applicable;
   - page or sheet/cell location when available;
   - extraction method when available;
   - confidence when applicable.
4. Explicitly distinguish missing data from inferred data.
5. Support optional source locations without inventing evidence.
6. Define a V1 schema version identifier.
7. Define reusable domain primitives/enums needed by the canonical schema.
8. Define canonical models for at least:
   - Party;
   - Invoice;
   - InvoiceItem;
   - PackingList;
   - PackingItem;
   - TransportDocument (Bill of Lading / Sea Waybill / Air Waybill representation);
   - CustomsDeclaration;
   - CustomsDeclarationItem;
   - Evidence;
   - CanonicalShipment aggregate.
9. Support multiple invoices, packing lists, transport documents, and declarations in one Shipment.
10. Represent dates, decimals, money/value, quantity, units, weight/volume/dimensions, identifiers, and references without using binary floating point for business-critical numeric values.
11. Preserve identifiers such as HS codes, tax IDs, declaration types, container numbers, invoice numbers, and country/origin codes as strings where leading zeroes or formatting may matter.
12. Forbid silent customer-specific/layout-specific fields in the canonical layer.
13. Add unit tests that validate schema behavior, failure cases, and JSON round-trip/schema generation.
14. Keep existing TASK-001 health/config tests passing.

---

## 4. OUT OF SCOPE

TASK-002 MUST NOT implement:

- file upload or file storage;
- SHA-256 ingestion behavior;
- database persistence or SQLAlchemy tables;
- database migrations;
- PDF/Excel/DOCX/image parsing;
- OCR;
- document classification logic;
- AI provider integration;
- LLM extraction;
- normalization algorithms;
- unit conversion logic;
- item matching;
- rule engine behavior;
- cross-document checks;
- HS classification or HS recommendation;
- legal checking;
- customer-specific adapters;
- FastAPI endpoints for domain entities;
- human correction workflow;
- production authentication;
- UI.

This task defines data contracts only. It must not pull implementation from later roadmap tasks forward.

---

## 5. INPUT

Primary source of truth:

```text
PROJECT_CONSTITUTION.md
MASTER_SPEC.md
ARCHITECTURE.md
TASK_TEMPLATE.md
TASK-002-canonical-data-schema.md
```

No production customer documents are required.

Synthetic examples may be used to validate the schema.

---

## 6. OUTPUT

Required outputs:

```text
docs/DATA_SCHEMA.md
src/customs_ai/domain/... canonical schema implementation
tests/unit/domain/... schema tests
```

The exact Python file split may be chosen by the Developer if it remains simple and coherent. A small number of focused files is preferred over unnecessary fragmentation.

The schema document and Python implementation MUST agree.

---

## 7. FUNCTIONAL REQUIREMENTS

### FR-01 â€” Canonical field provenance

Every canonical business field that originates from extraction/inference must be able to preserve:

```text
raw_value
normalized_value
origin
source_document_id (when applicable)
page (optional)
sheet (optional)
cell (optional)
bounding_box (optional)
extraction_method (optional)
confidence (optional)
```

Equivalent decomposition into nested provenance/location models is allowed if the information is not lost.

### FR-02 â€” Raw value preservation

Normalization-ready fields MUST NOT replace or destroy `raw_value`.

Example concept:

```json
{
  "raw_value": "USD 12,500.00",
  "normalized_value": "12500.00",
  "origin": "EXTRACTED",
  "source_document_id": "DOC-001",
  "page": 1
}
```

Exact JSON serialization may differ as long as semantics are documented and deterministic.

### FR-03 â€” Extraction vs inference

At minimum, the schema MUST support the following origins:

```text
EXTRACTED
INFERRED
MANUAL
```

`EXTRACTED` and `INFERRED` MUST remain distinguishable after serialization.

The Developer MUST NOT silently label an inferred value as extracted.

### FR-04 â€” Missing values

A field that does not exist in the source MUST be representable as missing/`None` without fabricating a `CanonicalField` value.

Missing data MUST NOT be auto-converted into inferred data by the schema layer.

### FR-05 â€” Extracted provenance invariant

For an `EXTRACTED` canonical field, the model SHOULD require enough provenance to establish that the value came from a real source document.

Minimum required invariant for an extracted field:

```text
source_document_id is present
raw_value is present
```

If the Developer chooses a different invariant, it must be explicitly justified in `docs/DATA_SCHEMA.md` and in the Completion Report.

### FR-06 â€” Confidence

If confidence is present, it MUST validate to the inclusive range:

```text
0.0 <= confidence <= 1.0
```

Confidence may remain optional because deterministic/manual values may not need it.

### FR-07 â€” Source location

The schema MUST support:

```text
PDF/page source: page
Spreadsheet source: sheet + optional cell
Optional bounding box when available
```

The schema MUST NOT require a bounding box for V1.

### FR-08 â€” Canonical Shipment

A `CanonicalShipment` aggregate MUST support zero-to-many:

```text
Invoice
PackingList
TransportDocument
CustomsDeclaration
```

It MUST NOT assume `1 Shipment = 1 Invoice`.

### FR-09 â€” Invoice

Invoice schema MUST support at least these optional business fields when present:

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

InvoiceItem MUST support at least:

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

Not every field is required.

### FR-10 â€” Packing List

PackingList MUST support at least:

```text
packing_list_number
date
seller
buyer
shipment_reference
invoice_reference(s)
package_count
package_type
gross_weight
net_weight
dimensions
volume
items[]
```

PackingItem MUST support at least:

```text
item_code
description
quantity
unit
package_number
gross_weight
net_weight
```

### FR-11 â€” Transport document

TransportDocument MUST support Bill of Lading / Sea Waybill / Air Waybill use cases and at least:

```text
document_number
shipper
consignee
notify_party
vessel
voyage
flight
port_of_loading
port_of_discharge
place_of_receipt
place_of_delivery
ETD
ETA
package_count
package_type
gross_weight
volume
container_number(s)
seal_number(s)
freight_term
```

Fields irrelevant to a specific transport mode remain optional.

### FR-12 â€” Customs declaration

CustomsDeclaration MUST support at least:

```text
declaration_type
customs_office
importer
exporter
invoice_reference(s)
transport_reference(s)
currency
exchange_rate
delivery_term
total/value field(s)
freight
insurance
items[]
```

CustomsDeclarationItem MUST support at least:

```text
line/item reference
description
HS code
origin
quantity
unit
value-related field(s)
tax-related references/fields if represented
permit/policy reference(s) if represented
```

This is a data representation only. TASK-002 MUST NOT decide whether an HS code, tax rate, permit, or legal requirement is correct.

### FR-13 â€” Party

Party MUST support at least:

```text
name
tax/business identifier
address
country/origin identifier when present
```

No assumption may be made that all documents contain all party fields.

### FR-14 â€” Evidence

Define an `Evidence` representation usable later by CheckResult/reporting modules. At minimum it must be able to carry:

```text
evidence_id
document_id
field_name
raw_value
normalized_value
page
sheet
cell
bounding_box (optional)
extraction_id (optional)
```

TASK-002 does not implement rule execution or evidence generation logic.

### FR-15 â€” Numeric precision

Business-critical decimal numbers MUST use `Decimal` (or an equally precise decimal representation), not Python `float`, for normalized monetary/value/quantity/weight values.

Float may be used for confidence because it is a bounded score, not a financial quantity.

### FR-16 â€” Dates

Normalized dates SHOULD use Python `date` (and `datetime` only where time is materially present), while raw source text remains preserved by canonical field provenance.

### FR-17 â€” String identifiers

These values MUST NOT be modeled as integers merely because they contain digits:

```text
HS code
tax ID
invoice number
declaration number/type
container number
seal number
country/origin code
item/part/model identifiers
```

### FR-18 â€” Extra fields

Canonical domain models SHOULD reject unknown top-level/model fields (`extra="forbid"` or equivalent) so customer-layout leakage and accidental schema drift are detected early.

If the Developer chooses not to use strict extra-field validation for a specific model, that exception must be documented and justified.

### FR-19 â€” Schema version

The canonical aggregate MUST expose a schema version identifier, initially:

```text
0.1
```

The version is a data-contract version, not the application package version.

### FR-20 â€” JSON / Pydantic schema generation

The canonical models MUST support deterministic Pydantic validation and JSON serialization. `CanonicalShipment.model_json_schema()` or an equivalent top-level schema generation path MUST work without error.

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- NFR-01: Python version must remain compatible with the project baseline (`>=3.12`; Python 3.13 is acceptable).
- NFR-02: Use Pydantic v2 already present in the project; do not add another validation framework.
- NFR-03: AI allowed: NO.
- NFR-04: No network calls.
- NFR-05: No database dependency.
- NFR-06: No customer-specific field names or layout coordinates embedded in document models.
- NFR-07: Models and documentation must be readable by future extraction, normalization, matching, and rule modules.
- NFR-08: Avoid excessive class fragmentation and premature abstractions.
- NFR-09: Public model names and field names use English `snake_case`.
- NFR-10: Existing TASK-001 behavior and tests must remain green.

---

## 9. BUSINESS RULES

None.

TASK-002 defines data contracts. It does not implement customs/legal/business validation rules.

---

## 10. DATA MODEL IMPACT

Creates the V1 canonical data contract.

Expected domain concepts include:

```text
CanonicalField / provenance representation
ValueOrigin
SourceLocation / equivalent
Evidence
Party
Invoice
InvoiceItem
PackingList
PackingItem
TransportDocument
CustomsDeclaration
CustomsDeclarationItem
CanonicalShipment
```

Additional small value objects are allowed when justified, for example decimal measurement/dimensions structures.

This task intentionally does NOT create database tables.

Because this is the initial canonical schema definition rather than a breaking change to an established schema, no ADR is required unless the Developer proposes a broader architecture change.

---

## 11. FILES / MODULES EXPECTED

Expected affected areas:

```text
docs/DATA_SCHEMA.md
src/customs_ai/domain/
tests/unit/domain/
tasks/in_progress/TASK-002-canonical-data-schema.md
```

Possible simple implementation layout (illustrative, not mandatory):

```text
src/customs_ai/domain/
  __init__.py
  enums.py
  schema.py
```

Do not split into many files without a concrete maintainability reason.

---

## 12. CONSTRAINTS

1. Follow source-of-truth priority:
   `PROJECT_CONSTITUTION.md` > `MASTER_SPEC.md` > `ARCHITECTURE.md` > `DATA_SCHEMA.md` > Task > Implementation.
2. Do not erase raw source values during normalization-ready representation.
3. Do not represent inferred values as extracted values.
4. Do not create customer-specific canonical schemas.
5. Do not assume one invoice per shipment.
6. Do not make every field mandatory when source documents may omit it.
7. Do not add legal conclusions or HS classification logic.
8. Do not add SQLAlchemy/database persistence in this task.
9. Do not add AI SDKs or make API calls.
10. Do not modify `PROJECT_CONSTITUTION.md`, `MASTER_SPEC.md`, `ARCHITECTURE.md`, or `TASK_TEMPLATE.md` unless a real conflict is found and escalated to Project Leader.
11. Do not silently change the schema away from the task. Report conflicts/questions instead.
12. No real customer/production data in tests.

---

## 13. EDGE CASES

Developer and Reviewer MUST consider at least:

- a Shipment with zero documents;
- a Shipment with multiple invoices;
- a source field missing completely;
- an extracted raw value with no normalized value yet;
- an inferred value with explicit `INFERRED` origin;
- manual structured input;
- extracted field missing source document provenance (should fail if FR-05 invariant is implemented);
- confidence exactly `0.0` and `1.0`;
- confidence less than 0 or greater than 1;
- Unicode Vietnamese/Chinese party names/descriptions;
- Decimal values with many digits;
- HS code containing leading zeroes;
- multiple container/seal numbers;
- transport fields irrelevant to AWB vs B/L left missing;
- fields sourced from PDF page;
- fields sourced from Excel sheet/cell;
- optional bounding box absent;
- unknown extra canonical field supplied;
- JSON serialization + validation round-trip.

---

## 14. ACCEPTANCE CRITERIA

### AC-01 â€” Documentation

Given the completed implementation  
When `docs/DATA_SCHEMA.md` is read  
Then it documents the canonical field/provenance contract, document models, missing-value semantics, extraction-vs-inference distinction, numeric precision approach, and schema version.

### AC-02 â€” Provenance preservation

Given an extracted field with raw text and normalized value  
When it is validated and serialized  
Then both raw and normalized values remain available together with the extracted origin and source document reference.

### AC-03 â€” Inference distinction

Given an inferred field  
When it is serialized  
Then its origin remains explicitly `INFERRED` and cannot be confused with `EXTRACTED`.

### AC-04 â€” Missing data

Given an Invoice without `insurance` or `payment_term`  
When the Invoice is validated  
Then validation succeeds without fabricating values.

### AC-05 â€” Multiple documents

Given a CanonicalShipment with at least two Invoices and two PackingLists  
When the aggregate is validated  
Then validation succeeds and all document objects remain distinct.

### AC-06 â€” Core document models

Given minimal valid examples of Invoice, PackingList, TransportDocument, and CustomsDeclaration  
When each is validated  
Then each passes using the documented canonical schema.

### AC-07 â€” Invalid confidence

Given confidence `< 0` or `> 1`  
When a canonical field is validated  
Then validation fails.

### AC-08 â€” Decimal precision

Given a business numeric value requiring decimal precision  
When stored in the normalized canonical form  
Then the implementation does not rely on binary float for that value.

### AC-09 â€” String identifiers

Given an HS code such as `01012100`  
When validated/serialized  
Then the leading zero is preserved.

### AC-10 â€” Extra field protection

Given an undeclared customer/layout-specific field is injected into a strict canonical model  
When validated  
Then validation fails rather than silently accepting schema drift.

### AC-11 â€” JSON schema

Given the top-level canonical model  
When Pydantic JSON Schema generation is requested  
Then generation succeeds without error.

### AC-12 â€” Regression

Given the repository after TASK-002 implementation  
When the complete pytest suite is run  
Then all TASK-001 and TASK-002 tests pass.

### AC-13 â€” Scope

Given the final diff  
When reviewed  
Then there is no parser, OCR, AI, DB, rule engine, HS/legal decision logic, or customer-specific implementation introduced by TASK-002.

---

## 15. TEST REQUIREMENTS

### Unit Tests

Must include tests for at least:

- canonical extracted field with raw + normalized + source provenance;
- inferred field origin preservation;
- manual field representation;
- optional/missing field behavior;
- confidence bounds;
- extracted-field provenance failure case if FR-05 is enforced;
- Decimal business values;
- leading-zero HS code/string identifier preservation;
- Party with Unicode text;
- Invoice + InvoiceItem validation;
- PackingList + PackingItem validation;
- TransportDocument validation;
- CustomsDeclaration + item validation;
- multiple documents in one CanonicalShipment;
- rejection of unexpected extra fields;
- top-level JSON serialization round-trip;
- Pydantic JSON schema generation.

### Integration Tests

No new API integration endpoint is required for TASK-002.

Existing TASK-001 integration test for `/health` MUST continue to pass.

### Failure Tests

Must cover:

- confidence out of range;
- invalid extra field;
- broken required provenance for extracted field if FR-05 is enforced;
- invalid normalized numeric type where strict validation is expected.

### Regression Tests

Full existing test suite must pass.

---

## 16. TEST DATA

Use only:

- synthetic values;
- anonymized examples;
- public/non-sensitive examples.

Include multilingual examples where useful, e.g. Vietnamese and Chinese company/product text.

Do not use real customer documents or identifying customer data.

---

## 17. OBSERVABILITY REQUIREMENTS

No runtime logging/audit workflow is required because TASK-002 defines passive domain models only.

Model validation errors should remain standard, inspectable Pydantic validation errors. Do not suppress validation detail with generic exceptions.

---

## 18. COST REQUIREMENTS

AI allowed: NO

Network/API calls: NO

New paid services: NO

---

## 19. SECURITY / PRIVACY REQUIREMENTS

- No API keys, tokens, passwords, or secrets.
- No production/customer data in fixtures.
- Do not log field values merely to test models.
- Documentation examples must be synthetic/anonymized.
- Schema must not embed real customer names/templates as special cases.

---

## 20. DEPENDENCIES

Depends on:

```text
TASK-001 â€” Project Foundation (DONE)
```

Downstream tasks expected to depend on TASK-002 include ingestion/parsers/extraction/normalization/matching/checking modules.

---

## 21. DELIVERABLES

Developer must provide:

- `docs/DATA_SCHEMA.md`;
- Pydantic canonical domain models;
- unit/failure/regression tests;
- updated domain exports if appropriate;
- Developer Completion Report;
- known limitations and unresolved schema questions;
- exact pytest result.

No database migration is expected.

---

## 22. DEFINITION OF DONE

- [ ] Scope implemented
- [ ] `docs/DATA_SCHEMA.md` matches implementation
- [ ] Provenance/raw-value contract implemented
- [ ] EXTRACTED vs INFERRED distinction implemented
- [ ] Missing values do not become fabricated values
- [ ] Core document models implemented
- [ ] CanonicalShipment supports multiple documents
- [ ] Decimal precision preserved
- [ ] Tests cover success and failure paths
- [ ] Full pytest suite passes
- [ ] No unresolved CRITICAL/HIGH issues
- [ ] Reviewer approved
- [ ] No secrets/customer data committed
- [ ] No scope creep into later tasks
- [ ] Ready to move to `tasks/done/`

---

## 23. DEVELOPER NOTES

Gemini #1 updates when necessary.

If a schema decision is ambiguous and could materially constrain later tasks, stop and raise it to the Project Leader instead of silently choosing a customer-specific or overly rigid interpretation.

---

## 24. REVIEW NOTES

Gemini #2 updates during review.

---

## 25. PROJECT LEADER DECISION

Pending.
