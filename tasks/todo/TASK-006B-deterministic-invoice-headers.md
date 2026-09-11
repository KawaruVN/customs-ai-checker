# TASK-006B — Deterministic Invoice Headers

Status: TODO  
Priority: P1  
Parent: TASK-006  
Dependencies: TASK-006A DONE

## Objective

Extract Commercial Invoice header/party fields deterministically from existing parsed/resolved content.

## In scope

- ParsedPdfDocument / ResolvedPdfDocument header fields.
- ParsedWorkbook header fields.
- Party: seller/buyer/ship_to.
- Exact source `raw_value`.
- PDF page provenance.
- Excel sheet/cell provenance.
- Config-driven EN/VI/ZH aliases from TASK-006A.
- Longest/specific exact-key matching.
- Repeated-identical candidate dedupe.
- Sticky conflicting-field detection.
- Stable documented confidence policy.
- Canonical Invoice mapping.

## Out of scope

- InvoiceItem tables.
- DB/persistence.
- application service.
- semantic/AI fallback.
- hosted network.
- TASK-009 normalization.

## Key acceptance

- DELIVERY DATE does not become invoice_date.
- SELLER ADDRESS does not become seller.name.
- BUYER ADDRESS does not become buyer.name.
- PDF casing/raw source is preserved.
- Excel formula evidence is preserved conservatively.
- zero values are not dropped.
- 3-way conflict remains unresolved.
- missing fields remain None.
- no customer-specific coordinates/row numbers.
- full regression stays green.

Baseline is the exact approved TASK-006A full-suite result.
