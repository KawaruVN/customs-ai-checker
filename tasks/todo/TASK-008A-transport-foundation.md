# TASK-008A — Transport Extraction Foundation & Contracts

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-007 DONE  
Pre-task baseline: 1422 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. OBJECTIVE

Establish the foundational configuration, multilingual alias dictionaries (EN, VI, ZH), strict CWD-independent configuration loader, and provider-neutral typed result contracts for Bill of Lading and Air Waybill extraction, without implementing document interpretation or parser routing.

---

## 2. AUTHORITATIVE INPUTS & GOVERNANCE

- Follow `PROJECT_CONSTITUTION.md`, `MASTER_SPEC.md` (Section 13, Sections 54–56), `ARCHITECTURE.md` (Section 61), and `docs/DATA_SCHEMA.md`.
- `TransportDocument`, `CanonicalField`, `Party`, and `ValueOrigin` in `src/customs_ai/domain/schema.py` remain the authoritative canonical source of truth.
- Preserve existing Commercial Invoice and Packing List configurations, models, and test baselines.
- Reuse established primitives: `normalize_alias`, `parse_decimal`, `parse_date`, `ExtractionStatus`, `ExtractionIssue`, `ExtractionCandidate`.

---

## 3. IN SCOPE & DELIVERABLES

1. **Configuration Specification (`config/transport_extraction.yaml`)**:
   - Comprehensive multilingual aliases (English, Vietnamese, Traditional/Simplified Chinese) for ocean (B/L) and air (AWB) shipping.
   - Target header paths (24 paths):
     - Document ID: `document_number` (B/L No, AWB No, Waybill No)
     - Parties: `shipper.name`, `shipper.tax_id`, `shipper.address`, `consignee.name`, `consignee.tax_id`, `consignee.address`, `notify_party.name`, `notify_party.tax_id`, `notify_party.address`
     - Transport details: `vessel`, `voyage`, `flight`
     - Locations: `port_of_loading`, `port_of_discharge`, `place_of_receipt`, `place_of_delivery`
     - Dates: `etd`, `eta`
     - Cargo summary: `package_count`, `package_type`, `gross_weight`, `volume`
     - Commercial terms: `freight_term` (Prepaid, Collect)
   - Logistics reference list paths (2 paths):
     - `container_numbers`, `seal_numbers`
   - Non-header boundary labels (`_NON_HEADER_LABELS`) to prevent party/logistics cross-contamination.

2. **Configuration Loader & Validator (`src/customs_ai/extraction/transport_config.py`)**:
   - CWD-independent default configuration loading using `pathlib.Path(__file__)`.
   - Strict validation: exact approved path coverage, rejection of unknown/missing keys, malformed YAML, non-string/blank aliases, duplicate aliases, and within-context alias collisions.
   - Immutable configuration dataclass/model.

3. **Typed Result Contracts (`src/customs_ai/extraction/transport_models.py`)**:
   - `TransportExtractionResult` (and/or `TransportHeaderExtractionResult`) holding canonical `TransportDocument`, explicit `ExtractionStatus`, list of `ExtractionIssue`, and list of `ExtractionCandidate`.
   - Strict field definitions with no unauthorized business fields or mutable shared default containers.

4. **Comprehensive Unit Test Suite**:
   - `tests/unit/test_transport_config.py`: configuration validation, path verification, alias conflict detection, CWD independence.
   - `tests/unit/test_transport_models.py`: result contract instantiation, status invariants, candidate preservation, immutability.

---

## 4. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **Canonical Schema Stability**:
   - Zero changes to `src/customs_ai/domain/schema.py` and zero changes to the SQLite database schema.
   - `etd` and `eta` are typed `CanonicalField[date]`; `package_count`, `gross_weight`, and `volume` are typed `CanonicalField[Decimal]`.
   - `container_numbers` and `seal_numbers` are `list[CanonicalField[str]]`.

2. **Sea Waybill Classification Gap**:
   - `SEA_WAYBILL` is not present in `DocumentType`. Do NOT add `SEA_WAYBILL` to the enum or silently alias it to `BILL_OF_LADING`. Document this boundary explicitly.

3. **Party Role Separation**:
   - `shipper`, `consignee`, and `notify_party` represent distinct transport roles and must never be conflated with commercial `seller`/`buyer` or customs `importer`/`exporter`.

4. **No Container-Seal Pairing Assumption**:
   - Position in `container_numbers` does not imply pairing with the same position in `seal_numbers`.

5. **No Document Interpretation**:
   - No PDF or Excel parsing, no OCR invocation, no persistence calls, and no external AI services in TASK-008A.

---

## 5. OUT OF SCOPE

- Document parsing or extractor implementations (deferred to TASK-008B and TASK-008C).
- Persistence integration or database operations (deferred to TASK-008D).
- Classification engine alterations or new classification rules.
- Cross-document validation, matching, or normalization.
- UI, CLI endpoints, or REST API controllers.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: Canonical `TransportDocument` remains authoritative without modification.
- [ ] AC-02: `config/transport_extraction.yaml` covers all 24 approved header paths and 2 reference list paths in EN, VI, and ZH.
- [ ] AC-03: `transport_config.py` enforces exact path sets, rejects malformed/duplicate aliases, and resolves CWD-independently.
- [ ] AC-04: `transport_models.py` defines strict result contracts reusing canonical types, `ExtractionStatus`, `ExtractionIssue`, and `ExtractionCandidate`.
- [ ] AC-05: Unit tests pass 100% and pre-existing 1422 tests remain fully green.
- [ ] AC-06: Zero changes to production parsing, classification, or persistence code.

---

## 7. REVIEW & APPROVAL GATES

- **Developer Handoff**: Codex must present implementation diff, test evidence, and self-review.
- **Independent Technical Review**: Antigravity reviews code, contract compliance, and executes adversarial probes.
- **Project Leader Approval**: ChatGPT approves for Pull Request creation and merge.
