# TASK-008B — Deterministic B/L and AWB Header Extraction

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008A approved & merged  
Pre-task baseline: Established upon completion of TASK-008A

---

## 1. OBJECTIVE

Implement conservative, deterministic header extraction for Bill of Lading (ocean) and Air Waybill (air) documents from native PDF and Excel (XLSX, XLS) files, populating the canonical `TransportDocument` header fields with physical coordinates and cell provenance.

---

## 2. CANONICAL CONTRACT & FIELDS IN SCOPE

Extract the approved 24 header paths from `TransportDocument`:
- **Document Identification**: `document_number` (B/L No, AWB No, Master/House B/L)
- **Parties**:
  - `shipper`: `name`, `tax_id`, `address`
  - `consignee`: `name`, `tax_id`, `address`
  - `notify_party`: `name`, `tax_id`, `address`
- **Transport Identification**:
  - Ocean: `vessel`, `voyage`
  - Air: `flight`
- **Routing & Places**:
  - `port_of_loading` (or airport of departure)
  - `port_of_discharge` (or airport of destination)
  - `place_of_receipt`
  - `place_of_delivery`
- **Dates**: `etd`, `eta` (parsed strictly into `datetime.date`)
- **Cargo Totals**: `package_count`, `package_type`, `gross_weight`, `volume` (parsed into `Decimal`)
- **Commercial Terms**: `freight_term` (e.g., "FREIGHT PREPAID", "FREIGHT COLLECT")

---

## 3. IN SCOPE

1. **PDF Deterministic Header Parsing**:
   - Native PDF text extraction using layout blocks and coordinate geometry.
   - Distinct handling of B/L and AWB layouts: ocean shipping forms (box-grid layout) vs standard IATA Air Waybill grids.
   - Non-header boundary labels (`_NON_HEADER_LABELS`) acting as fences to stop multiline party address extraction from overflowing into cargo description, marks, or container fields.

2. **Excel Deterministic Header Parsing**:
   - Cell-coordinate provenance (`sheet_name!A1`) for XLSX and XLS formats.
   - Formula text opacity: dynamic formulas are not trusted as header values.
   - Hidden row/column protection and merged cell normalization.

3. **Visual & Quality Safety**:
   - Native clean text bypasses OCR.
   - Scanned or degraded pages trigger visual quality evaluation; low confidence triggers sticky `requires_review=True` with `NEEDS_REVIEW` status.

4. **Provenance & Auditability**:
   - Every extracted field carries `ValueOrigin.EXTRACTED` with document ID, page number, physical bounding box (PDF) or sheet/cell (Excel), and raw string text.

---

## 4. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Strict Party Role Separation**:
   - `shipper`, `consignee`, and `notify_party` must not be confused with `seller`, `buyer`, `exporter`, or `importer`.
   - "Same as Consignee" or "Same as Above" in notify party must be handled conservatively (never fabricate a new identity; record raw token with appropriate review flag if unresolved).

2. **No Data Fabrication or Inference**:
   - Missing fields remain `None`.
   - Do NOT infer flight numbers from voyage numbers or vice-versa.
   - Do NOT infer freight terms if absent.

3. **Date Precision**:
   - `etd` and `eta` must be resolved to valid `date` objects. Unparseable or ambiguous dates remain `None` with `INVALID_DATE` issue and `requires_review=True`.

4. **Reference Isolation**:
   - Container numbers and seal numbers must NOT be extracted in this task (reserved for TASK-008C). Headers must abstain from extracting container numbers as document numbers.

---

## 5. OUT OF SCOPE

- Container and seal extraction (TASK-008C).
- Extraction service orchestration and database persistence (TASK-008D).
- Sea Waybill classification or automatic B/L mapping.
- Item matching, tariff classification, or cross-document rules.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: Deterministic header extraction succeeds across diverse B/L and AWB PDF and Excel samples.
- [ ] AC-02: All 24 header paths extract with complete physical/cell provenance and exact raw text.
- [ ] AC-03: Multiline party addresses truncate cleanly at field boundaries without bleeding into cargo or marks.
- [ ] AC-04: Ocean and air routing fields map correctly to canonical port/place fields without cross-mode pollution.
- [ ] AC-05: Dates and numeric totals parse into `date` and `Decimal` losslessly.
- [ ] AC-06: Pre-existing test suite passes with zero regressions.

---

## 7. REVIEW & APPROVAL GATES

- Developer Handoff -> Independent Technical Review (Antigravity) -> Project Leader Approval (ChatGPT).
