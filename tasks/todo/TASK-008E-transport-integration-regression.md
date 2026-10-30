# TASK-008E — Transport Integration & Regression

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008D approved & merged, including separately approved exact-kind classifier dependency; separate implementation authorization<br>
Pre-task baseline: Established upon completion of TASK-008D

---

## 1. OBJECTIVE

Execute complete production-path integration testing and comprehensive regression verification for the Transport Document extraction pipeline (both Bill of Lading and Air Waybill), verifying that real document bytes flow seamlessly through ingestion, classification, visual inspection, deterministic extraction, SQLite persistence, and subsequent retrieval without corrupting prior Invoice or Packing List records.

This child remains TODO after the documentation-amendment closure gate and sequential TASK-008A..D approval/merge. It authorizes B/L/AWB integration only and does not certify declaration correctness, document reconciliation or shipment eligibility.

---

## 2. INTEGRATION MATRIX & SCOPE

1. **Ocean Bill of Lading (B/L) Integration**:
   - Single-page and multi-page native PDF files.
   - Authorized B/L in Excel (XLSX, XLS), including manifest-style tables inside that B/L. Standalone shipping/transport manifests are negative input cases, not B/L fixtures.
   - Extraction of all 24 canonical header paths, multi-container lists, and multi-seal lists.
   - Carrier variations (Maersk, MSC, CMA CGM, Evergreen style layouts).

2. **Air Waybill (AWB) Integration**:
   - Standard IATA-style Air Waybill PDFs (Master AWB, House AWB).
   - Authorized AWB in Excel, including tabular layouts within that AWB. Standalone air-cargo manifests are negative input cases, not AWB fixtures.
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

6. **Exact-Kind Negative Integration Matrix**:
   - AN containing an AWB number, Sea Waybill, standalone shipping/air-cargo/transport manifest, unsupported road/rail/multimodal kind, UNKNOWN/OTHER and conflicting classifications.
   - Include misleading supported-enum/high-confidence keyword predictions and Bill/AWB mentions in references; none alone authorizes transport routing. Refusals cause zero extraction persistence mutations.
   - Positive control: manifest-style reference tables inside an independently established B/L/AWB remain eligible layouts. Genuine supported B/L/AWB must still work.
   - The current classifier is not sufficient evidence for this contract. Verify the separately Project Leader-approved exact-kind dependency identified in [TASK-008D](TASK-008D-transport-service-persistence.md); unresolved gap blocks integration acceptance, with no classifier changes made by this documentation amendment.
   - GAP-CLASSIFIER-008 currently has no assigned task ID. Its proposed position is after TASK-008C and before TASK-008D; approval/review/merge/closure must precede this integration child. No dependency on TASK-016B or any post-008E task is permitted; AN implementation is not a prerequisite for safe B/L/AWB exclusion.

---

## 3. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Production Component Usage**:
   - Tests must invoke real production entry points (`IngestionService`, `ClassificationService`, `TransportExtractionService`, `DocumentExtractionRepository`) rather than test mocks.

2. **Zero Regressions**:
   - All pre-existing Invoice (TASK-006) and Packing List (TASK-007) test suites must remain 100% green.

3. **Unsupported-Kind Policy**:
   - Verify UNKNOWN/OTHER refusals and rejection of AN, Sea Waybill, standalone manifests and unsupported kinds despite misleading Bill/AWB references or classifier predictions. Do not silently alias them into B/L/AWB or rely solely on confidence. Preserve prior active records/history on refusal.

4. **Party and Identifier Isolation**:
   - Verify that `shipper` never populates `seller`, `consignee` never populates `buyer`, and container numbers never populate `document_number`.

5. **Source-Authority and Version Boundaries**:
   - B/L/AWB extraction preserves its own raw values and provenance. It does not execute [ADR-004](../../docs/decisions/ADR-004-arrival-declaration-source-policy.md) required-source decisions or imply business PASS. Future required AN absence/ambiguity or critical NOT_CHECKED coverage remains blocking under the [source matrix](../../docs/DECLARATION_FIELD_SOURCE_MATRIX.md).
   - Keep planned transport envelope `(3, "transport_document")`, Invoice v1 and Packing v2 compatibility separate from canonical schema `0.1` and DB/DDL versioning. No AN envelope version is allocated here.

---

## 4. OUT OF SCOPE

- Cross-document matching between B/L/AWB and Invoices or Packing Lists (TASK-010).
- Normalization of port codes or carrier names to UN/LOCODE (TASK-009).
- Tariff or customs legal checks.
- User interface or external REST endpoints.
- AN extraction, standalone manifest or road/rail/multimodal extraction, declaration intake, required-source checks or automatic declaration edits (planned [TASK-016](TASK-016-arrival-notice-evidence.md), [TASK-017](TASK-017-declaration-intake.md) and subsequent checking tasks).

---

## 5. ACCEPTANCE CRITERIA

- [ ] AC-01: End-to-end integration succeeds for diverse synthetic B/L and AWB files (PDF, XLSX, XLS).
- [ ] AC-02: Lossless persistence round-trip through envelope v3 verified in SQLite.
- [ ] AC-03: Security boundaries verified (source byte immutability, path traversal refusal, privacy in logs).
- [ ] AC-04: Tri-document coexistence verified with zero data corruption across Invoice, Packing, and Transport documents.
- [ ] AC-05: Full regression suite passes 100% with zero failures and zero skipped tests.
- [ ] AC-06: Independent adversarial QA passes all probes without unresolved critical/high blockers.
- [ ] AC-07: Exact-kind negative integration matrix refuses AN with AWB reference, Sea Waybill, standalone manifest and unsupported kinds with zero extraction database mutations, including keyword/high-confidence misclassification probes; authorized B/L/AWB with manifest-style layouts remain positive controls.

---

## 6. REVIEW & APPROVAL GATES

- Separate authorization after TASK-008D approval/merge and classifier-gap resolution -> Developer Handoff -> Independent Technical Review & Adversarial QA (Antigravity) -> Project Leader Final Approval (ChatGPT) -> Owner PR Merge & Epic Closure.
- No downstream AN/declaration task begins from this documentation amendment; each requires its own approved handoff. Design source-policy walkthroughs and reported baseline figures are not runtime integration test results.
