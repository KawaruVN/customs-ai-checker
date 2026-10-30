# TASK-008D — Transport Service & Persistence

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008C approved & merged; separately approved exact-kind classifier dependency resolved; separate implementation authorization<br>
Pre-task baseline: Established upon completion of TASK-008C

---

## 1. OBJECTIVE

Build the application orchestration layer (`TransportExtractionService`, `build_transport_extraction_service`) uniting deterministic header extraction and container/seal extraction under strict classification gates, and integrate versioned SQLite persistence using discriminated envelope v3.

This child remains TODO. It inherits the documentation-amendment closure gate and sequential child review/merge workflow. The requirements below describe future implementation, not current runtime capability.

---

## 2. CANONICAL CONTRACT & PERSISTENCE ARCHITECTURE

1. **Application Service**:
   - `TransportExtractionService` coordinates reading source files, verifying document classification, invoking deterministic header and container extractors, and persisting canonical `TransportDocument` results.
   - Dual-classification support: handles both `DocumentType.BILL_OF_LADING` and `DocumentType.AIR_WAYBILL`.

2. **Classification Gate**:
   - Re-verifies content classification using `build_classification_service`.
   - Requires document type in `{BILL_OF_LADING, AIR_WAYBILL}` and classification confidence >= 0.50; this is necessary but is not sufficient proof of exact document kind.
   - Establishes supported B/L/AWB kind from document purpose/context rather than Bill/AWB keyword or number occurrence alone. Refuse AN containing an AWB reference, Sea Waybill, standalone shipping/air-cargo/transport manifest and other unsupported kinds even if a keyword classifier labels them B/L/AWB with high confidence. A manifest-style table inside an otherwise established B/L/AWB is an allowed layout only.
   - Refuses unclassified documents, non-transport documents (e.g. Invoice, Packing List), or conflicting classifications immediately with zero persistence side-effects.
   - **Unresolved runtime gap / approval dependency**: the current enum/keyword-based classifier does not establish these exact kind distinctions. Re-running the same classifier or trusting its confidence cannot close the gap. The Project Leader must separately approve the classifier/contract change scope and acceptance evidence before it is implemented or this gate can be claimed complete. No enum, classifier or schema change is authorized by this docs amendment; do not silently add that work to TASK-008A or add AN aliases to transport configuration.
   - **GAP-CLASSIFIER-008 — no concrete task assigned yet**: propose a separately scoped classifier-boundary safety dependency after TASK-008C closure and before TASK-008D development. Leader must assign/approve its task ID, exact scope and regression/negative-case acceptance, followed by independent review and merge/closure. It must not depend on TASK-016B, TASK-016, TASK-017 or any task starting after TASK-008E. TASK-008D stays blocked until that dependency is closed; TASK-008E inherits the same gate. This is a planning proposal, not an implementation authorization or a claim the gap is fixed.

3. **Discriminated Persistence Envelope v3**:
   - Extends `DocumentExtractionRepository` to support envelope version 3 `(3, "transport_document")`.
   - Serialization encodes canonical `TransportDocument`, candidates, and issues without data loss.
   - Preserves lossless `Decimal` precision/scale tuples, `date` objects, and list-valued fields (`container_numbers`, `seal_numbers`).
   - Zero modifications to SQLite DDL. Preserve canonical schema version `"0.1"`; this is separate from extraction envelope `format_version = 3` and database/DDL versioning. No AN envelope version is reserved.

4. **Transactional & Concurrency Guarantees**:
   - Unique partial index `one_active_extraction_per_document` (`document_id` WHERE `is_active = 1`) guarantees at most one active extraction per document; a document with no usable committed attempt may have zero active rows.
   - Monotonic attempt numbering (`attempt_number = prior_max + 1`).
   - CAS (Compare-And-Swap) re-extraction guards under `BEGIN IMMEDIATE`.
   - Failed extractions persist as inactive history (`is_active = 0`), preserving prior active data.

---

## 3. IN SCOPE

1. **Service Implementation (`src/customs_ai/extraction/transport_service.py`)**:
   - Factory function `build_transport_extraction_service`.
   - Method `extract_transport_document(document_id: str, ...) -> TransportExtractionResult`.
   - Handling of both ocean B/L and air AWB parsing pipelines based on classified document type.

2. **Repository Envelope v3 (`src/customs_ai/repositories/document_extractions.py`)**:
   - Codec support for `(3, "transport_document")`.
   - Deserialization back into canonical `TransportDocument`.
   - Strict validation of stored payloads against schema tampering.

3. **Multi-Document Database Coexistence**:
   - Seamless coexistence of Invoice v1, Packing List v2, and Transport v3 envelopes in the same SQLite database without collision.

4. **Comprehensive Unit & Persistence Tests**:
   - `tests/unit/test_transport_service.py`: classification gating, orchestration, error handling.
   - `tests/unit/test_transport_persistence.py`: envelope v3 round-trips, active invariant, attempt history, CAS protection.

---

## 4. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Zero SQLite DDL Changes**:
   - No schema migrations. Envelope v3 operates within the established `payload_json` architecture.

2. **Invoice & Packing Preservation**:
   - Existing Invoice v1 (`(1, "invoice")`) and Packing List v2 (`(2, "packing_list")`) records must not be modified, mutated, or invalidated.

3. **Unsupported Kind and Classification Gap**:
   - The service must NOT map Sea Waybills, AN or standalone manifests to B/L/AWB. `UNKNOWN` and `OTHER` are refused, but rejection must also cover misleading supported-enum predictions for unsupported kinds. Keyword/confidence assertions alone cannot authorize persistence; separately approved gap resolution is a prerequisite.

4. **Source Byte Immutability**:
   - Source document bytes and hashes must remain untouched during extraction and persistence.

5. **Extraction State Is Not Business Approval**:
   - Persist source B/L/AWB values and provenance without rewriting them from AN, resolving active document revisions by newest upload, evaluating required-source policy or creating shipment PASS. Canonical/extraction state does not prove correct shipment scope or reconciliation. Future policy and coverage boundaries are in [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md), the [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md), [TASK-016](TASK-016-arrival-notice-evidence.md) and [TASK-017](TASK-017-declaration-intake.md).

---

## 5. OUT OF SCOPE

- Production pipeline integration across the full upload endpoint (TASK-008E).
- Cross-document matching between Transport documents and Invoices or Packing Lists.
- Normalization or legal rule validation.
- User interface or external API controllers.
- AN extraction/persistence contracts or envelope reservation, standalone manifest and road/rail/multimodal extraction, declaration intake, required-source evaluation or automatic declaration edits.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: `TransportExtractionService` extracts and persists `BILL_OF_LADING` and `AIR_WAYBILL` documents correctly.
- [ ] AC-02: Unsupported kinds are rejected with zero database mutations, including AN with AWB number, Sea Waybill and standalone manifest even when Bill/AWB keywords or misleading supported-enum classification are present; UNKNOWN/OTHER and genuine conflicting classifications are also refused.
- [ ] AC-03: Envelope v3 serializes and deserializes `TransportDocument` losslessly (preserving dates, decimals, and list-valued fields).
- [ ] AC-04: Single-active record invariant, monotonic attempts, and CAS guards function reliably.
- [ ] AC-05: Coexistence tests verify Invoice v1 and Packing v2 records remain 100% unaffected.
- [ ] AC-06: Full test suite passes with zero regressions.
- [ ] AC-07: Exact-kind approval dependency is resolved with explicit Project Leader-approved scope and independent negative-case evidence; the existing classifier is not asserted to meet this contract without that change. Invoice v1/Packing v2 compatibility and planned transport v3 remain distinct from canonical and DB versions.

---

## 7. REVIEW & APPROVAL GATES

- TASK-008C approved/merged plus separately approved classifier-gap resolution -> separate implementation authorization -> Developer Handoff -> Independent Technical Review (Antigravity) -> Project Leader Approval (ChatGPT) -> Owner merge -> separate authorization for TASK-008E.
