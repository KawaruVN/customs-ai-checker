# TASK-008B — Deterministic B/L and AWB Header Extraction

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008A approved & merged; separate implementation authorization<br>
Pre-task baseline: Established upon completion of TASK-008A

---

## 1. OBJECTIVE

Implement conservative, deterministic header extraction for Bill of Lading (ocean) and Air Waybill (air) documents from native PDF and Excel (XLSX, XLS) files, populating canonical `TransportDocument` headers with physical page or sheet/cell provenance and available geometry.

This child remains TODO and follows TASK-008A's documentation-amendment closure/start gate and sequential review/merge workflow. Input means an authorized B/L or AWB kind; references to Bill/AWB numbers inside AN, Sea Waybill, standalone manifest or another unsupported kind do not authorize extraction. The exact-kind service gate and separately approved current-classifier gap are tracked in [TASK-008D](TASK-008D-transport-service-persistence.md).

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
- **Cargo Totals**: `package_count`, `gross_weight`, `volume` use `Decimal`; `package_type` remains `str`.
- **Commercial Terms**: `freight_term` (e.g., "FREIGHT PREPAID", "FREIGHT COLLECT")

---

## 3. IN SCOPE

1. **PDF Deterministic Header Parsing**:
   - Native PDF text extraction preserving physical page and exact source spans; use layout blocks/coordinate geometry only where the approved parser supplies them. Current page-text parser does not guarantee field bounding boxes. Any required geometry/parser-contract expansion needs a separately Leader-approved dependency before implementation; never fabricate coordinates.
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
   - Every extracted field carries `ValueOrigin.EXTRACTED` with document ID, physical page (PDF) or sheet/cell (Excel), and exact raw string text. Preserve physical bounding boxes when available; absence is explicit, never invented.

---

## 4. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Strict Party Role Separation**:
   - `shipper`, `consignee`, and `notify_party` must not be confused with `seller`, `buyer`, `exporter`, or `importer`.
   - "Same as Consignee" or "Same as Above" in notify party must be handled conservatively (never fabricate a new identity; record raw token with appropriate review flag if unresolved).

2. **No Data Fabrication or Inference**:
   - Missing fields remain `None`.
   - Do NOT infer flight numbers from voyage numbers or vice-versa.
   - Do NOT infer freight terms if absent.
   - Keep source values, unit evidence and distinct label meanings. A source ETA is not actual arrival; port of loading, place of receipt, warehouse and declaration location codes are not interchangeable. No declaration-code mapping is implemented here.

3. **Date Precision**:
   - `etd` and `eta` must be resolved to valid `date` objects. Unparseable or ambiguous dates remain `None` with `INVALID_DATE` issue and `requires_review=True`.

4. **Reference Isolation**:
   - Container numbers and seal numbers must NOT be extracted in this task (reserved for TASK-008C). Headers must abstain from extracting container numbers as document numbers.

5. **Extraction Is Not Source Authority**:
   - Preserve B/L/AWB values independently; do not substitute AN values or execute required-source selection in this extractor. [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md) and the [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md) govern future declaration/reconciliation checks. Missing required AN and critical unchecked coverage cannot yield shipment PASS; those future checks are not implemented by successful header extraction.

---

## 5. OUT OF SCOPE

- Container and seal extraction (TASK-008C).
- Extraction service orchestration and database persistence (TASK-008D).
- Sea Waybill classification or automatic B/L mapping.
- AN extraction/aliases, standalone manifest and road/rail/multimodal extraction, declaration intake or required-source decision execution; see [TASK-016](TASK-016-arrival-notice-evidence.md) and [TASK-017](TASK-017-declaration-intake.md).
- Item matching, tariff classification, or cross-document rules.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: Deterministic header extraction succeeds across diverse B/L and AWB PDF and Excel samples.
- [ ] AC-02: All 24 header paths extract with exact document/page or sheet/cell provenance and raw text; preserve supplied bounding boxes without inventing missing geometry. Any geometry dependency is separately resolved through Leader approval.
- [ ] AC-03: Multiline party addresses truncate cleanly at field boundaries without bleeding into cargo or marks.
- [ ] AC-04: Ocean and air routing fields map correctly to canonical port/place fields without cross-mode pollution.
- [ ] AC-05: Dates and numeric totals parse into `date` and `Decimal` losslessly.
- [ ] AC-06: Pre-existing test suite passes with zero regressions.
- [ ] AC-07: Raw values and correct transport field meanings remain distinct from declaration source decisions; no ETA-to-actual-arrival fabrication or cross-document fill occurs.

---

## 7. REVIEW & APPROVAL GATES

- Separate authorization after TASK-008A approval/merge -> Developer Handoff -> Independent Technical Review (Antigravity) -> Project Leader Approval (ChatGPT) -> Owner merge -> separate authorization for TASK-008C.
