# TASK-008 — Transport Document Extraction

Status: IN_PROGRESS  
Type: EPIC  
Priority: P1  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Owner / Final Approver: Project Leader (ChatGPT)  
Created: 2026-10-29  
Dependencies: TASK-007 DONE  
Children: TASK-008A..TASK-008E (ALL TODO)  
Authoritative Baseline: 1422 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. PURPOSE & GLOBAL OBJECTIVE

Implement conservative, deterministic Bill of Lading (B/L) and Air Waybill (AWB) extraction using the existing `TransportDocument` canonical model and the proven local document-processing architecture from TASK-006 and TASK-007.

The target extraction pipeline supports:

```text
classified BILL_OF_LADING or AIR_WAYBILL
→ safe technical content (PDF, XLSX, XLS)
→ canonical TransportDocument
→ exact source provenance (page & cell coordinates, bounding boxes)
→ conservative review behavior (requires_review / flags)
→ discriminated envelope v3 persistence & history
→ production application orchestration
```

The current implementation authorization covers **TASK-008A only**. Future children must not be implemented until explicitly authorized, reviewed, and merged in sequence.

---

## 2. CANONICAL CONTRACT & ARCHITECTURAL BOUNDARIES

1. **Authoritative Canonical Model**:
   - `TransportDocument` in `src/customs_ai/domain/schema.py` is the sole authoritative target model:
     - `document_number: CanonicalField[str] | None`
     - `shipper: Party | None`
     - `consignee: Party | None`
     - `notify_party: Party | None`
     - `vessel: CanonicalField[str] | None`
     - `voyage: CanonicalField[str] | None`
     - `flight: CanonicalField[str] | None`
     - `port_of_loading: CanonicalField[str] | None`
     - `port_of_discharge: CanonicalField[str] | None`
     - `place_of_receipt: CanonicalField[str] | None`
     - `place_of_delivery: CanonicalField[str] | None`
     - `etd: CanonicalField[date] | None` (strictly `datetime.date`, not datetime or arbitrary strings)
     - `eta: CanonicalField[date] | None` (strictly `datetime.date`, not datetime or arbitrary strings)
     - `package_count: CanonicalField[Decimal] | None`
     - `package_type: CanonicalField[str] | None`
     - `gross_weight: CanonicalField[Decimal] | None`
     - `volume: CanonicalField[Decimal] | None`
     - `container_numbers: list[CanonicalField[str]]` (list-valued, default empty list)
     - `seal_numbers: list[CanonicalField[str]]` (list-valued, default empty list)
     - `freight_term: CanonicalField[str] | None`
   - No canonical schema changes or database migrations are authorized.

2. **Classification & Document Types**:
   - `DocumentType` enum in `src/customs_ai/classification/enums.py` defines `BILL_OF_LADING` and `AIR_WAYBILL`.
   - **Sea Waybill Architectural Gap**: `SEA_WAYBILL` has no distinct entry in `DocumentType`. It is **STRICTLY FORBIDDEN** to silently add `SEA_WAYBILL` or map Sea Waybills to `BILL_OF_LADING`. The handling of Sea Waybill classification is documented as a pending architectural decision reserved for future Project Leader review.

3. **Logistics Party Role Segregation**:
   - `shipper`, `consignee`, and `notify_party` represent distinct maritime/air logistics parties.
   - Do NOT equate `shipper` with `seller`/`exporter`, or `consignee` with `buyer`/`importer`.
   - Parties must remain strictly separated; missing party identities or tax IDs must never be inferred from commercial invoices or packing lists.

4. **Independent Reference Lists & Positional Safety**:
   - `container_numbers` and `seal_numbers` are independent list-valued fields.
   - Positional index (e.g. `container_numbers[i]` and `seal_numbers[i]`) MUST NEVER be assumed to establish container-to-seal pairing unless structured tabular grounding explicitly links them.
   - Container numbers and seal numbers must never leak into document numbers or other header fields.

5. **Type Safety & Non-Inference**:
   - `etd` and `eta` must be parsed strictly into `datetime.date` using existing date parsers; ambiguous dates require human review.
   - Do NOT infer freight terms (e.g., Prepaid vs. Collect), port/airport equivalence, voyage/flight schedules, or missing entities.

6. **Persistence Compatibility**:
   - The persistence layer must preserve existing Commercial Invoice v1 (`(1, "invoice")`) and Packing List v2 (`(2, "packing_list")`) envelopes intact.
   - TASK-008D will define envelope v3 (`(3, "transport_document")`) without altering the SQLite schema (`schema_version = "0.1"`).

---

## 3. CHILD TASK SEQUENCE

| Child | Status | Scope | Dependencies |
|---|---|---|---|
| **TASK-008A** | TODO | Transport foundation, multilingual aliases (EN/VI/ZH), typed contracts & tests | Completed TASK-007 |
| **TASK-008B** | TODO | Deterministic B/L and AWB header extraction (PDF, XLSX, XLS) | TASK-008A approved & merged |
| **TASK-008C** | TODO | Container/seal references, multi-value extraction & context safety | TASK-008B approved & merged |
| **TASK-008D** | TODO | Transport extraction service & reviewed versioned persistence (envelope v3) | TASK-008C approved & merged |
| **TASK-008E** | TODO | Production-path integration, security boundaries & full regression | TASK-008D approved & merged |

Each child task requires its own independent review, Project Leader approval, and pull request merge before work on the subsequent child may commence.

---

## 4. SAFETY INVARIANTS

1. **Non-fabrication**: Missing fields remain `None` or empty lists; no logistics facts are invented.
2. **Provenance Preservation**: All extracted values retain exact source document, page, or cell coordinates and bounding box evidence.
3. **Party Distinction**: `shipper`, `consignee`, and `notify_party` remain strictly isolated from commercial `seller`/`buyer`.
4. **Transport Mode Separation**: Ocean fields (`vessel`, `voyage`, `port_of_loading`, `port_of_discharge`) and air fields (`flight`) must not be cross-contaminated.
5. **No Pairing Assumption**: `container_numbers` and `seal_numbers` are independent lists; positional correspondence is forbidden.
6. **Date & Decimal Rigor**: `etd` and `eta` are typed `date`; weights, counts, and volumes are typed `Decimal` with lossless scale.
7. **Visual Safety**: Unsafe visual evidence (scanned/degraded pages) triggers sticky review (`requires_review=True`) and never enters unverified text output.
8. **Source Immutability**: Source document bytes and hashes remain unaltered throughout processing.
9. **Backward Compatibility**: Commercial Invoice v1 and Packing List v2 pipelines must remain 100% green without behavioral regression.
10. **Privacy in Logs**: Customer logistics details, party addresses, and cargo descriptions must not leak into standard logs.

---

## 5. SCOPE BOUNDARIES

- **In Scope for TASK-008**:
  - Multilingual transport aliases (EN, VI, ZH) for B/L and AWB.
  - Deterministic header extraction from PDF and Excel files.
  - Robust multi-container and multi-seal extraction with ISO 6346 validation where applicable.
  - Transport extraction service with classification gating (`BILL_OF_LADING`, `AIR_WAYBILL`).
  - Discriminated persistence envelope v3 for transport documents in SQLite.
  - Full end-to-end integration and regression test coverage.

- **Explicitly Out of Scope for TASK-008**:
  - `SEA_WAYBILL` classification or automatic mapping to B/L (pending architectural decision).
  - Cross-document reconciliation (e.g. matching B/L weights to Packing List or Invoice totals).
  - Normalization engine (TASK-009) and Item Matching engine (TASK-010).
  - Customs legal rules, tariff classification, HS codes, or tax calculation.
  - Hosted LLM APIs, cloud services, external OCR endpoints.
  - Web UI, client dashboard, or public REST endpoints.

---

## 6. EPIC ACCEPTANCE CRITERIA

1. All 5 child tasks (TASK-008A through TASK-008E) completed, reviewed, and merged into `main`.
2. Both `BILL_OF_LADING` and `AIR_WAYBILL` documents extract cleanly through the production pipeline.
3. TransportDocument fields round-trip losslessly through the SQLite repository via envelope v3.
4. Pre-existing Invoice v1 and Packing List v2 tests remain 100% green (zero regressions).
5. Full regression test suite passes with zero failures and zero skipped tests.
6. Independent adversarial QA verifies security boundaries, error resilience, and edge case handling.
7. Project Leader formally approves epic closure.
