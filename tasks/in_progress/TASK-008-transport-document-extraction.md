# TASK-008 — Transport Document Extraction

Status: IN_PROGRESS  
Type: EPIC  
Priority: P1  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Owner / Final Approver: Project Leader (ChatGPT)  
Created: 2026-10-29  
Dependencies: TASK-007 DONE; documentation amendment independently reviewed, merged and closed before TASK-008A<br>
Children: TASK-008A..TASK-008E (ALL TODO)  
Reported Baseline: 1422 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1); not rerun by the docs-only amendment

---

## 1. PURPOSE & GLOBAL OBJECTIVE

Implement conservative, deterministic Bill of Lading (B/L) and Air Waybill (AWB) extraction using the existing `TransportDocument` canonical model and the proven local document-processing architecture from TASK-006 and TASK-007.

The target extraction pipeline supports:

```text
classified BILL_OF_LADING or AIR_WAYBILL
→ safe technical content (PDF, XLSX, XLS)
→ canonical TransportDocument
→ exact source provenance (page or sheet/cell; bounding boxes where available)
→ conservative review behavior (requires_review / flags)
→ discriminated envelope v3 persistence & history
→ production application orchestration
```

The current authorization is **documentation amendment only**; no TASK-008A implementation is authorized by this amendment. TASK-008A remains TODO until independent review → Project Leader assessment → Owner commit/push → Leader remote verification → Owner merge → closure, followed by separate development authorization. Each later child requires its predecessor to be approved and merged plus explicit authorization before implementation.

Extraction success is a technical result, not declaration correctness, document reconciliation or shipment PASS. The approved Owner operational source policy is recorded in [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md); its proposed downstream contracts and coverage are in the [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md) and [document inventory](../../docs/DOCUMENT_INVENTORY.md). This epic supplies B/L/AWB evidence without implementing that policy engine.

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
   - Input authorization is limited to established B/L and AWB kinds, not all documents mentioning a bill/AWB number. Arrival Notices containing AWB references, standalone manifests, Sea Waybills and other unsupported kinds must not route to transport extraction. Manifest-style tables inside an otherwise authorized B/L/AWB are layouts, not authorization for standalone manifests or multimodal documents.
   - **Current classifier gap**: existing enum results, keyword evidence and confidence alone do not prove these exact kind boundaries. TASK-008D/E require an independently verified kind gate; the necessary classifier/contract change must be separately scoped and approved by the Project Leader before implementation. This amendment does not change classification code or resolve the runtime gap.

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
   - TASK-008D retains the planned extraction envelope v3 (`(3, "transport_document")`) without altering SQLite DDL. Canonical `schema_version = "0.1"`, extraction envelope `format_version`, and database/DDL versioning are distinct; none implies another. No Arrival Notice envelope version is reserved here.

7. **Source Authority Boundary**:
   - B/L/AWB extraction records only the source's own values, raw text and provenance. It must not overwrite source values with Arrival Notice data or label a B/L/AWB value as the required declaration value merely because extraction succeeded.
   - AIR actual pieces/gross weight require applicable active Arrival Notice evidence under Owner policy; SEA loading-place sourcing and B/L totals eligibility also require Arrival Notice evidence. Missing, wrong-scope, inactive/unclear or insufficiently typed/unit-grounded AN cannot be replaced by Bill fallback. These checks remain future work; critical unimplemented coverage is NOT_CHECKED + BLOCK in a future checking result, never shipment PASS.
   - Separate AN contracts/evidence are planned under [TASK-016](../todo/TASK-016-arrival-notice-evidence.md), then structured/manual declaration intake under [TASK-017](../todo/TASK-017-declaration-intake.md). Do not add AN aliases, fields, policy evaluation, automatic declaration edits or fabricated weighing evidence to TASK-008.

---

## 3. CHILD TASK SEQUENCE

| Child | Status | Scope | Dependencies |
|---|---|---|---|
| **TASK-008A** | TODO | Transport foundation, multilingual aliases (EN/VI/ZH), typed contracts & tests | Completed TASK-007; documentation amendment review, merge and closure; separate authorization |
| **TASK-008B** | TODO | Deterministic B/L and AWB header extraction (PDF, XLSX, XLS) | TASK-008A approved & merged |
| **TASK-008C** | TODO | Container/seal references, multi-value extraction & context safety | TASK-008B approved & merged |
| **TASK-008D** | TODO | Transport extraction service & reviewed versioned persistence (envelope v3) | TASK-008C approved & merged |
| **TASK-008E** | TODO | Production-path integration, security boundaries & full regression | TASK-008D approved & merged |

Each child task requires its own independent review, Project Leader approval, and pull request merge before work on the subsequent child may commence.

After TASK-008A..E close sequentially, the planned order is TASK-016 AN/evidence foundation (contracts/compatibility → classification/extraction → service/persistence → integration/regression), TASK-017 declaration intake, TASK-009 normalization, TASK-010 document relationship and item matching, TASK-011 rule-engine foundation, TASK-012 lane A document ↔ document and lane B source ↔ declaration checks, then TASK-013 reporting, TASK-014 correction/recheck and TASK-015 golden regression. Existing TASK-009..015 IDs are retained. Road/rail/multimodal remain inventory/extension design, with no TASK-008 extractor authorization.

---

## 4. SAFETY INVARIANTS

1. **Non-fabrication**: Missing fields remain `None` or empty lists; no logistics facts are invented.
2. **Provenance Preservation**: All extracted values retain exact source document and page or sheet/cell evidence, plus bounding boxes where available; never invent geometry. Current parser geometry limitations need an explicit Leader-reviewed dependency if richer geometry is required, not silent parser/model expansion in TASK-008A.
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
  - Arrival Notice extraction/aliases, standalone manifest extraction, road/rail/multimodal extractor support, declaration intake and required-source decision execution.
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
8. Exact-kind negative scenarios reject AN with an AWB number, Sea Waybill, standalone manifest and unsupported kinds even when Bill/AWB keywords are present; no extraction persistence side effects occur on refusal. The TASK-008D classifier dependency must be resolved through a separately approved change before this can be claimed complete.
9. The foundation retains exactly 24 approved header paths and 2 reference-list paths, including `shipper.tax_id`, `consignee.tax_id` and `notify_party.tax_id`, with no AN aliases or relaxed path validator.

## 7. DOCS AMENDMENT STATE

Epic status remains IN_PROGRESS; all five children remain TODO. This amendment changes documentation only and does not satisfy implementation acceptance criteria. The 1422-test figure is a reported pre-task baseline, not a test run performed by this amendment. Design walkthroughs of ADR-004 are not runtime test PASS evidence.
