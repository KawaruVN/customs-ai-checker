# TASK-008D — Transport Service & Persistence

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008C approved & merged  
Pre-task baseline: Established upon completion of TASK-008C

---

## 1. OBJECTIVE

Build the application orchestration layer (`TransportExtractionService`, `build_transport_extraction_service`) uniting deterministic header extraction and container/seal extraction under strict classification gates, and integrate versioned SQLite persistence using discriminated envelope v3.

---

## 2. CANONICAL CONTRACT & PERSISTENCE ARCHITECTURE

1. **Application Service**:
   - `TransportExtractionService` coordinates reading source files, verifying document classification, invoking deterministic header and container extractors, and persisting canonical `TransportDocument` results.
   - Dual-classification support: handles both `DocumentType.BILL_OF_LADING` and `DocumentType.AIR_WAYBILL`.

2. **Classification Gate**:
   - Re-verifies content classification using `build_classification_service`.
   - Requires document type in `{BILL_OF_LADING, AIR_WAYBILL}` and classification confidence >= 0.50.
   - Refuses unclassified documents, non-transport documents (e.g. Invoice, Packing List), or conflicting classifications immediately with zero persistence side-effects.

3. **Discriminated Persistence Envelope v3**:
   - Extends `DocumentExtractionRepository` to support envelope version 3 `(3, "transport_document")`.
   - Serialization encodes canonical `TransportDocument`, candidates, and issues without data loss.
   - Preserves lossless `Decimal` precision/scale tuples, `date` objects, and list-valued fields (`container_numbers`, `seal_numbers`).
   - Zero modifications to SQLite DDL schema (`schema_version = "0.1"` preserved).

4. **Transactional & Concurrency Guarantees**:
   - Unique partial index `one_active_extraction_per_document` (`document_id` WHERE `is_active = 1`) guarantees exactly one active extraction per document.
   - Monotonic attempt numbering (`attempt_number = prior_max + 1`).
   - CAS (Compare-And-Swap) re-extraction guards under `BEGIN IMMEDIATE`.
   - Failed extractions persist as inactive history (`is_active = 0`), preserving prior active data.

---

## 3. IN SCOPE

1. **Service Implementation (`src/customs_ai/extraction/transport_service.py`)**:
   - Factory function `build_transport_extraction_service`.
   - Method `extract_transport_document(document_id: str, ...) -> TransportExtractionResult`.
   - Handling of both ocean B/L and air AWB parsing pipelines based on classified document type.

2. **Repository Envelope v3 (`src/customs_ai/repositories/document_extraction.py`)**:
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

3. **Sea Waybill Classification Gap**:
   - The service must NOT map Sea Waybills to B/L. If a document is classified as `UNKNOWN` or `OTHER`, it must be refused by the classification gate.

4. **Source Byte Immutability**:
   - Source document bytes and hashes must remain untouched during extraction and persistence.

---

## 5. OUT OF SCOPE

- Production pipeline integration across the full upload endpoint (TASK-008E).
- Cross-document matching between Transport documents and Invoices or Packing Lists.
- Normalization or legal rule validation.
- User interface or external API controllers.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: `TransportExtractionService` extracts and persists `BILL_OF_LADING` and `AIR_WAYBILL` documents correctly.
- [ ] AC-02: Non-transport documents are rejected by the classification gate with zero database mutations.
- [ ] AC-03: Envelope v3 serializes and deserializes `TransportDocument` losslessly (preserving dates, decimals, and list-valued fields).
- [ ] AC-04: Single-active record invariant, monotonic attempts, and CAS guards function reliably.
- [ ] AC-05: Coexistence tests verify Invoice v1 and Packing v2 records remain 100% unaffected.
- [ ] AC-06: Full test suite passes with zero regressions.

---

## 7. REVIEW & APPROVAL GATES

- Developer Handoff -> Independent Technical Review (Antigravity) -> Project Leader Approval (ChatGPT).
