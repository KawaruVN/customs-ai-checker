# Customs AI Checker — V1 Canonical Data Schema

Version: 0.1  
Status: Active

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
