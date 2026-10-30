# Customs AI Checker — V1 Canonical Data Schema

Version: 0.1  
Status: Active

Sections 1–8 describe the implemented canonical contract in
`src/customs_ai/domain/schema.py`. Section 9 is a **proposed extension design** for
the 2026-10-30 docs amendment, pending review and separate implementation approval.
The implemented schema remains 0.1; this document does not add runtime fields.

## 1. Core Principles

The V1 Canonical Schema normalizes diverse customer document formats into standard semantic structures.

- **Provenance Preservation**: `raw_value` and `normalized_value` coexist when available.
- **Extraction vs. Inference**: Fields explicitly declare their `origin`.
- **Missing-Value Semantics**: Data absent from source documents evaluates to `None`. It is never fabricated.
- **Strict Extra-Field Policy**: Canonical domain models forbid undeclared extra fields (`extra="forbid"`) to prevent accidental schema drift from customer-specific layouts.

## 2. Precision and Types

- **Dates**: Normalized dates use `datetime.date` where appropriate.
- **Identifiers**: Identifier-like values (HS codes, tax IDs, invoice numbers, declaration identifiers, container/seal numbers, country/origin codes, item/model/part identifiers) are modeled as `str` where formatting or leading zeroes matter.
- **Numeric Values**: Business numeric values such as money, weight, quantity, rates, and volume use `Decimal`.
- **Confidence**: Confidence is a bounded score and may use `float`.

## 3. Provenance Contract (`CanonicalField[T]`)

All semantic business values are represented using `CanonicalField[T]`.

- `raw_value: str | None` — Exact source text when a raw source representation exists.
- `normalized_value: T | None` — Parsed/normalized typed value, for example `Decimal`, `date`, or `str`.
- `origin: ValueOrigin` — One of `EXTRACTED`, `INFERRED`, or `MANUAL`.
- `source_document_id: str | None` — Source document identifier when applicable.
- `page: int | None` — PDF/document page location when available.
- `sheet: str | None` — Spreadsheet sheet name when available.
- `cell: str | None` — Spreadsheet cell coordinate when available.
- `bounding_box: tuple[float, float, float, float] | None` — Optional geometric location.
- `extraction_method: str | None` — Method that produced the value when applicable, for example local parser, regex, OCR, or model extraction.
- `confidence: float | None` — Optional score in the inclusive range `[0.0, 1.0]`.

### Origin invariants

- `EXTRACTED`: requires both `raw_value` and `source_document_id`.
- `INFERRED`: represents a value inferred from context. It may legitimately have no raw source text.
- `MANUAL`: represents structured/manual user input. It may legitimately have no source document provenance.

Missing source data is represented by the parent model field being `None`; the schema layer does not fabricate a `CanonicalField`.

## 4. Top-Level Aggregate: `CanonicalShipment`

`CanonicalShipment` is the canonical aggregate representing one shipment/checking context.

It supports zero-to-many arrays for:

- `invoices`
- `packing_lists`
- `transport_documents`
- `customs_declarations`

The schema does not assume one Shipment equals one Invoice.

`schema_version` is fixed to `"0.1"` for the initial V1 canonical data contract.

## 5. Core Domain Models

### Party

Represents legal/business parties while preserving their distinct roles in documents.

Fields:

- `name: CanonicalField[str] | None`
- `tax_id: CanonicalField[str] | None`
- `address: CanonicalField[str] | None`
- `country_code: CanonicalField[str] | None`

### Invoice and InvoiceItem

`Invoice` supports:

- `invoice_number`
- `invoice_date`
- `seller`
- `buyer`
- `ship_to`
- `currency`
- `incoterm`
- `payment_term`
- `total_amount`
- `freight`
- `insurance`
- `discount`
- `items[]`

`InvoiceItem` supports:

- `item_number`
- `item_code`
- `part_number`
- `model`
- `description`
- `brand`
- `manufacturer`
- `quantity`
- `unit`
- `unit_price`
- `amount`
- `origin`
- `weight`
- `package_information`

Business numeric fields use `CanonicalField[Decimal]`.

### PackingList and PackingItem

`PackingList` supports:

- `packing_list_number`
- `date`
- `seller`
- `buyer`
- `shipment_reference`
- `invoice_references[]`
- `package_count`
- `package_type`
- `gross_weight`
- `net_weight`
- `dimensions`
- `volume`
- `items[]`

`PackingItem` supports:

- `item_code`
- `description`
- `quantity`
- `unit`
- `package_number`
- `gross_weight`
- `net_weight`

### TransportDocument

Represents Bill of Lading, Sea Waybill, and Air Waybill use cases using optional fields where a field does not apply.

Model representability does not authorize extraction of every kind. TASK-008 accepts
only B/L and AWB; Sea Waybill is not a supported classification and must not be
silently mapped to B/L. Arrival Notice will require a separate proposed contract.

Fields:

- `document_number`
- `shipper`
- `consignee`
- `notify_party`
- `vessel`
- `voyage`
- `flight`
- `port_of_loading`
- `port_of_discharge`
- `place_of_receipt`
- `place_of_delivery`
- `etd`
- `eta`
- `package_count`
- `package_type`
- `gross_weight`
- `volume`
- `container_numbers[]`
- `seal_numbers[]`
- `freight_term`

### CustomsDeclaration and CustomsDeclarationItem

`CustomsDeclaration` supports:

- `declaration_type`
- `customs_office`
- `importer`
- `exporter`
- `invoice_references[]`
- `transport_references[]`
- `currency`
- `exchange_rate`
- `delivery_term`
- `total_value`
- `freight`
- `insurance`
- `items[]`

`CustomsDeclarationItem` supports:

- `line_reference`
- `description`
- `hs_code`
- `origin`
- `quantity`
- `unit`
- `item_value`
- `tax_fields[]`
- `permit_references[]`

This schema only represents these values. It does not determine whether an HS code, tax treatment, permit, or legal requirement is correct.

## 6. Evidence Contract

`Evidence` is a downstream reporting/reference carrier. It points to the source values used by checks and reports.

Fields:

- `evidence_id: str`
- `document_id: str`
- `field_name: str`
- `raw_value: str`
- `normalized_value: Any | None`
- `page: int | None`
- `sheet: str | None`
- `cell: str | None`
- `bounding_box: tuple[float, float, float, float] | None`
- `extraction_id: str | None`

`normalized_value` is intentionally broad in `Evidence` because evidence can reference strings, dates, decimals, and other already-validated canonical values. `Evidence` is not the authoritative typed canonical value; strict business typing remains in `CanonicalField[T]` and the document models.

## 7. Strict Schema Policy

All canonical domain models inherit `extra="forbid"`.

Unknown customer/layout-specific fields must therefore be rejected instead of silently leaking into the canonical contract. Customer-specific handling belongs in adapters/rules outside the canonical schema.

## 8. Serialization

The canonical models support Pydantic validation, JSON serialization, JSON re-validation, and JSON Schema generation through `CanonicalShipment.model_json_schema()`.

Raw and normalized data must remain distinguishable after serialization, and the `origin` must remain explicit.

## 9. Proposed Arrival / Declaration Extensions — NOT IMPLEMENTED

Authority: Owner operational policy OP-AN-DECL v1 in
[MASTER_SPEC Section 61](../MASTER_SPEC.md), proposed technical decision
[ADR-004](decisions/ADR-004-arrival-declaration-source-policy.md),
[inventory](DOCUMENT_INVENTORY.md) and [field registry](DECLARATION_FIELD_SOURCE_MATRIX.md).
Business priorities are Owner-approved; field layouts, validators, version assignment,
migrations and public contracts below require separate Leader approval in
[TASK-016](../tasks/todo/TASK-016-arrival-notice-evidence.md) and
[TASK-017](../tasks/todo/TASK-017-declaration-intake.md). No schema.py change here.

### 9.1 Document identity dimensions and source lifecycle

Propose independent family (transport/arrival/commercial/declaration), exact kind
(B/L, AWB, AN, Sea Waybill, manifest, etc.), mode (SEA/AIR/ROAD/RAIL/MULTIMODAL),
hierarchy (master/house/unknown) and checking context (shipment/declaration type,
goods, direction and applicable operational policy). Unknown is explicit. A token
“AWB” inside an AN is a reference, not proof of AWB kind. Existing DocumentType and
ClassificationResult do not implement these dimensions; no enum expansion is implied.

Source-document revision and active-business-document selection need revision
identifier/date where present, supersession evidence, actor/time/reason and unresolved
state. Upload order is not revision order. A persistence active extraction is not
proof of business-document authority. Master/house/split/consolidation relationships
must be grounded before scopes can be compared or summed.

### 9.2 Separate proposed ArrivalNotice

The contract must preserve independently grounded AN reference; Bill/AWB references
with master/house scope; operational parties (including AN notify, separate from Bill
notify and importer/buyer); mode; arrival/loading/discharge/storage places with their
own field definitions/catalog references; flight or vessel/voyage; estimated and actual
arrival events as distinct facts; containers; actual pieces/package kind; gross/net/
chargeable weights with explicit units and shipment scope; and provenance/issues.
ArrivalNotice is not embedded into TransportDocument and is not a transport alias.
AN may lack any field; missing stays None/review, never copied from Bill to create AN.

Weight/unit/scope wrappers and aggregate linkage are proposals, not fields already
accepted by CanonicalField or CanonicalShipment. Gross/net/chargeable are never
interchangeable. No invented weigh ticket, weighing time or measurement ID; real
measurement evidence may be attached when it exists but is not an AIR AN prerequisite.
AN place names require exact declaration-field and catalog mapping; current
TransportDocument.port_of_loading is not a declaration location code carrier.

### 9.3 Declaration intake and registry

Current CustomsDeclaration is a skeleton representing only the fields in Section 5.
It has no intake service, operational loading-place/arrival fields or coverage gate.
Propose structured/manual intake first with field ID/definition, input version,
actor/time, supplied values and applicability context. Manual values retain MANUAL
origin and honest input evidence; do not fabricate document/page/cell for manual input.
Preserve identifiers/leading zeroes and exact supplied Decimal/date representations.
PDF/OCR declaration extraction is separately authorized later.

Proposed field registry contains ID/name/definition, mode/context applicability,
required source, forbidden overrides, comparison/aggregation/conversion/tolerance,
required evidence, severity/blocking/exception behavior and coverage/support status.
Internal registry IDs in the matrix are not official customs indicator codes. Map to
official field identifiers only after exact definitions/catalogs are approved.

### 9.4 Evidence, decisions, calculations, exceptions and snapshots

Existing CanonicalField provides document/page/sheet/cell/bbox and exact raw value;
existing Evidence can additionally reference extraction_id. Proposed decision evidence
joins document + extraction + canonical/registry field path + physical location where
applicable, source hash/revision/scope, normalization/catalog version and corrections.
All differing values stay inspectable. Source decision records need rule ID/version,
required source/value, eligibility/rejection reasons and evidence. SEA totals conflict
has unresolved decision + BLOCK, never an invented winning source.

Derived/calculated values must retain input evidence IDs, formula, unit/currency/
catalog conversion, rounding/tolerance and version. They must not have EXTRACTED
origin. A new derived origin or separate derivation model is a future approval choice;
the current enum remains EXTRACTED/INFERRED/MANUAL. Insurance insured value and premium
require different semantics; included freight/insurance costs cannot be counted twice.

Exception records must reference finding, fields/docs, all differing values, reason,
evidence, authorized acceptor, time and OP policy version. They may accept a permitted
discrepancy but cannot waive required AN, wrong required value or unidentified shipment.
Proposed check snapshot records exact declaration input, active document/extraction,
correction, context, catalog/rule/policy versions and coverage. Separate declaration
compliance, document reconciliation and readiness. BLOCK is proposed readiness,
NOT_CHECKED an unexecuted check; no runtime enum/schema change in this amendment.
Changed dependencies invalidate current checks/readiness; preserve historical results
and re-evaluate exceptions before recheck may support a current outcome.

### 9.5 Compatibility and independent version domains

| Domain | Implemented / planned state | Amendment boundary |
|---|---|---|
| Canonical schema | `CanonicalShipment.schema_version = "0.1"` implemented | AN/registry/decision additions need separate compatibility and version decision; none assigned here |
| Extraction envelope `format_version` + kind | Invoice `(1, invoice)`, `(1, invoice_items)` and Packing `(2, packing_list)` implemented; Transport `(3, transport_document)` planned in TASK-008D | Preserve exact pairs and legacy rows; no new AN envelope version reserved |
| Database schema/migration | Accepted SQLite repository DDL/history semantics (ADRs 001/003) | Independent migration/version control; 0.1 is not a SQLite database version; no DDL changes here |

No proposed contract is silently serialized into old envelopes or undeclared fields.
Future persistence must retain strict validation, Decimal/date/Unicode/provenance,
source/hash/CAS, single-active, failed-attempt history and rollback invariants. Schema,
classifier and persistence changes need separately reviewed task scopes before code.
