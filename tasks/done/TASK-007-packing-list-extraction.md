# TASK-007 — Packing List Extraction

Status: DONE  
Type: EPIC  
Priority: P1  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Owner / Final Approver: Project Leader (ChatGPT)  
Created: 2026-10-29  
Completed: 2026-10-29  
Dependencies: TASK-006 DONE  
Children: TASK-007A..TASK-007E (ALL DONE)  
Project Leader: APPROVE (Epic Closed: 2026-10-29)  
Final Merged PR: PR #11 (commit `6d603511243c02d4a913a1a9979f1bf9fe41085d`)  
Documentation Closure Commit: `bb7ce06c370e42f6540a10eceae993eaa0d5cc28`  
Authoritative Baseline: 1422 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)  
Adversarial Verification: 49 passed, 0 failed, 1 native-symlink variant NOT RUN (Windows privilege constraint; real NTFS directory junction alternative PASS)

---

## 1. PURPOSE & OBJECTIVE

Implement conservative Packing List extraction using the existing canonical models and the proven local parsing, provenance, safety, and transactional persistence patterns established in TASK-006.

The completed epic supports:

```text
classified PACKING_LIST
→ safe technical content
→ canonical PackingList / PackingItem
→ exact source provenance (page & cell coordinates)
→ conservative review behavior (requires_review / flags)
→ discriminated envelope v2 persistence & history
→ production application orchestration
```

---

## 2. CANONICAL CONTRACT & ARCHITECTURAL FOUNDATIONS

1. **Authoritative Canonical Models**:
   - `PackingList`, `PackingItem`, `CanonicalField`, `Party`, and `ValueOrigin` in `src/customs_ai/domain/schema.py` remain authoritative.
   - The runtime annotation bug for `PackingList.date` was corrected from `CanonicalField[NoneType]` to `CanonicalField[datetime.date]` in TASK-007A with Project Leader approval.
   - All other canonical fields and SQLite schema remain strictly backward-compatible.

2. **Approved Header Alias Paths (16 paths)**:
   - `packing_list_number`, `date`, `seller.name`, `seller.tax_id`, `seller.address`, `buyer.name`, `buyer.tax_id`, `buyer.address`, `shipment_reference`, `invoice_references` (list-valued), `package_count`, `package_type`, `gross_weight`, `net_weight`, `dimensions`, `volume`.
   - Seller and buyer are strictly separated from shipper, consignee, exporter, and importer.

3. **Approved Item Paths (7 fields)**:
   - `item_code`, `description`, `quantity`, `unit`, `package_number`, `gross_weight`, `net_weight`.
   - `items` remains `list[PackingItem]`.

4. **Discriminated Persistence Envelope v2**:
   - Schema version 2 envelope `(2, "packing_list")` introduced in `DocumentExtractionRepository` without modifying database schema.
   - Partial index `one_active_extraction_per_document` (`document_id` WHERE `is_active = 1`) guarantees unique active record.
   - Historical records are preserved monotonically with CAS re-extraction guards.

---

## 3. CHILD TASK DECOMPOSITION & MERGE HISTORY

| Child | Status | Description | Merged PR | Merge Commit | Baseline Tests |
|---|---|---|---|---|---|
| **TASK-007A** | DONE | Packing aliases, validation, typed result contracts, date annotation fix | PR #7 | `57957a4` | 697 passed |
| **TASK-007B** | DONE | Deterministic Packing List headers (PDF, XLSX, XLS) | PR #8 | `3e7e1d8` | 962 passed |
| **TASK-007C** | DONE | Conservative deterministic Excel packing item tables | PR #9 | `bde5e61` | 1178 passed |
| **TASK-007D** | DONE | Packing service composition, classification gate, envelope v2 persistence | PR #10 | `f52ef03` | 1327 passed |
| **TASK-007E** | DONE | Production-path integration, security boundaries, and full regression | PR #11 | `6d60351` | 1422 passed |

---

## 4. CHILD COMPLETION EVIDENCE

All technical criteria and safety guarantees have been verified across the completed child tasks:

1. **Foundation & Contracts (TASK-007A):**
   - Canonical `PackingList`/`PackingItem` contracts established with full YAML configuration (`config/packing_list_aliases.yaml`).
   - Party role segregation enforced (zero party conflation).
   - Numeric and date parsing primitives (`normalize_alias`, `parse_decimal`, `parse_date`) validated. (81 new tests, baseline 697 passed).

2. **Deterministic Headers (TASK-007B):**
   - Deterministic extraction of all 16 canonical header paths from PDF, XLSX, and XLS with physical coordinates and page/cell provenance.
   - Openpyxl hidden-column grouping bug resolved. (265 new tests, baseline 962 passed).

3. **Deterministic Excel Items (TASK-007C):**
   - Conservative extraction of 7 canonical item fields from Excel workbooks.
   - Dual-constraint candidate header validation, grounded product identity, exact summary boundaries, formula opaqueness, and multi-table abstention verified. (216 new tests, baseline 1178 passed).

4. **Service & Persistence (TASK-007D):**
   - `PackingExtractionService` with content-based reclassification gate implemented.
   - Table-header context isolation strictly enforced.
   - Discriminated persistence envelope v2 (`(2, "packing_list")`), single-active enforcement via unique partial index `one_active_extraction_per_document`, monotonic attempt history, and CAS replacement verified. (149 new tests, baseline 1327 passed).

5. **Integration & Regression (TASK-007E):**
   - Fully verified end-to-end production path from byte upload through classification, read-only parsing, deterministic extraction, SQLite persistence, and fresh repository retrieval. (95 new integration tests, baseline 1422 passed).

6. **Invoice Backward Compatibility:**
   - Commercial Invoice v1 pipeline verified 100% green; shared SQLite database coexistence with zero payload rewriting or schema drift.

7. **Storage History & Invariants:**
   - Monotonic attempt numbering, single active record invariant, and atomic transaction rollback on simulated aborts verified.

8. **Data Safety & Precision:**
   - Lossless Decimal precision/scale tuples, date types, and leading-zero strings preserved.

9. **Source Immutability & Visual Safety:**
   - Source bytes unchanged before/after extraction; path traversal and directory link escapes blocked; visual uncertainty remains sticky with zero unverified canonical text.

10. **Zero Unresolved Blockers:**
    - 0 unresolved CRITICAL or HIGH findings across all child tasks.

---

## 5. KNOWN V1 SCOPE BOUNDARIES & LIMITATIONS

The following items are explicitly **OUT OF SCOPE** for TASK-007 and remain deferred to future tasks/epics:

1. **PDF Item Table Extraction**:
   - V1 does not extract item tables from PDF Packing Lists (`PDF_PACKING_ITEMS_UNSUPPORTED`, `items=[]`, `requires_review=True`, `NEEDS_REVIEW`). PDF header extraction operates normally.

2. **Cross-Document Matching**:
   - Reconciliation between Commercial Invoice and Packing List items, quantities, weights, and references is deferred to downstream reconciliation modules.

3. **Normalization & Customs Rules**:
   - Unit conversion, HS code assignment, tariff classification, and customs valuation rules remain strictly out of scope.

4. **Hosted AI / External APIs**:
   - No external LLM or cloud API dependencies; local processing and deterministic extraction only.

5. **User Interface & REST API Endpoints**:
   - Web UI, client portals, and public HTTP endpoints are deferred to subsequent development phases.

---

## 6. EPIC DEFINITION OF DONE

TASK-007 is formally DONE:

- [x] TASK-007A DONE (Packing Extraction Foundation & Contracts)
- [x] TASK-007B DONE (Deterministic Packing List Headers)
- [x] TASK-007C DONE (Conservative Deterministic Excel Packing Item Tables)
- [x] TASK-007D DONE (Packing Service & Persistence)
- [x] TASK-007E DONE (Packing List Integration & Regression)
- [x] Final Packing List extraction flow passes full regression (1422 passed, 0 failed, 0 skipped, 2 warnings)
- [x] 49/50 independent adversarial QA probes passed (1 variant NOT RUN due to Windows symlink privilege, replaced by NTFS junction PASS)
- [x] Commercial Invoice v1 backward compatibility verified 100% green
- [x] No unresolved CRITICAL/HIGH issues
- [x] Project Leader formally closes the epic

---

## 7. PROJECT LEADER DECISIONS & CLOSURE

### 2026-10-29 — Epic Acceptance & Formal Closure
- **Epic Status**: DONE
- **Closure Date**: 2026-10-29
- **Project Leader / Architect**: ChatGPT — APPROVE
- **Technical Reviewer / QA**: Antigravity — APPROVE
- **Main Developer**: Codex
- **Merged PR Range**: PR #7 through PR #11
- **Final Integration PR**: PR #11 (merge commit `6d603511243c02d4a913a1a9979f1bf9fe41085d`)
- **Documentation Closure Commit**: `bb7ce06c370e42f6540a10eceae993eaa0d5cc28`
- **Full Test Suite Baseline**: 1422 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1)
- **Next Epic Authorized**: TASK-008 — Transport Document Extraction (TASK-008A: Transport Foundation, TODO)
