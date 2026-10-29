# TASK-008E — Transport Integration & Regression

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008D approved & merged  
Pre-task baseline: Established upon completion of TASK-008D

---

## 1. OBJECTIVE

Execute complete production-path integration testing and comprehensive regression verification for the Transport Document extraction pipeline (both Bill of Lading and Air Waybill), verifying that real document bytes flow seamlessly through ingestion, classification, visual inspection, deterministic extraction, SQLite persistence, and subsequent retrieval without corrupting prior Invoice or Packing List records.

---

## 2. INTEGRATION MATRIX & SCOPE

1. **Ocean Bill of Lading (B/L) Integration**:
   - Single-page and multi-page native PDF files.
   - Excel shipping manifests and B/L tables (XLSX, XLS).
   - Extraction of all 24 canonical header paths, multi-container lists, and multi-seal lists.
   - Carrier variations (Maersk, MSC, CMA CGM, Evergreen style layouts).

2. **Air Waybill (AWB) Integration**:
   - Standard IATA-style Air Waybill PDFs (Master AWB, House AWB).
   - Excel air cargo manifests.
   - Extraction of flight details, airport departure/destination routing, and gross weight/volume totals.

3. **Security Boundaries & Immutability**:
   - **Source Immutability**: SHA-256 hash of uploaded document bytes verified before and after extraction.
   - **Path Traversal & Link Escapes**: Refusal of relative paths (`../`), symlinks, and directory junctions pointing outside upload root via `resolve_source_path`.
   - **Privacy Guard**: Verification that sensitive party identities, addresses, and cargo descriptions are excluded from standard production logs.

4. **Visual & Quality Safety**:
   - Degraded, noisy, or scanned documents trigger sticky `requires_review=True` and `NEEDS_REVIEW` status.
   - Clean native text documents bypass OCR entirely.

5. **Tri-Document Database Coexistence**:
   - Simultaneous storage and retrieval of Commercial Invoice (envelope v1), Packing List (envelope v2), and Transport Document (envelope v3) within a single SQLite database file.
   - Verification of CAS re-extraction guards, single-active constraint, and monotonic attempt tracking.

---

## 3. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Production Component Usage**:
   - Tests must invoke real production entry points (`IngestionService`, `ClassificationService`, `TransportExtractionService`, `DocumentExtractionRepository`) rather than test mocks.

2. **Zero Regressions**:
   - All pre-existing Invoice (TASK-006) and Packing List (TASK-007) test suites must remain 100% green.

3. **Sea Waybill Policy**:
   - Verify that documents classified as `UNKNOWN` or `OTHER` (including unclassified Sea Waybills) are rejected cleanly without error or corrupting state.

4. **Party and Identifier Isolation**:
   - Verify that `shipper` never populates `seller`, `consignee` never populates `buyer`, and container numbers never populate `document_number`.

---

## 4. OUT OF SCOPE

- Cross-document matching between B/L/AWB and Invoices or Packing Lists (TASK-010).
- Normalization of port codes or carrier names to UN/LOCODE (TASK-009).
- Tariff or customs legal checks.
- User interface or external REST endpoints.

---

## 5. ACCEPTANCE CRITERIA

- [ ] AC-01: End-to-end integration succeeds for diverse synthetic B/L and AWB files (PDF, XLSX, XLS).
- [ ] AC-02: Lossless persistence round-trip through envelope v3 verified in SQLite.
- [ ] AC-03: Security boundaries verified (source byte immutability, path traversal refusal, privacy in logs).
- [ ] AC-04: Tri-document coexistence verified with zero data corruption across Invoice, Packing, and Transport documents.
- [ ] AC-05: Full regression suite passes 100% with zero failures and zero skipped tests.
- [ ] AC-06: Independent adversarial QA passes all probes without unresolved critical/high blockers.

---

## 6. REVIEW & APPROVAL GATES

- Developer Handoff -> Independent Technical Review & Adversarial QA (Antigravity) -> Project Leader Final Approval (ChatGPT) -> PR Merge & Epic Closure.
