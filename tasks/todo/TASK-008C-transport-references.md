# TASK-008C — Transport Container & Seal References

Status: TODO  
Priority: P1  
Parent: TASK-008  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Final Approver: ChatGPT — Project Leader / Architect  
Dependencies: TASK-008B approved & merged  
Pre-task baseline: Established upon completion of TASK-008B

---

## 1. OBJECTIVE

Implement robust, conservative extraction of container numbers (`container_numbers`) and seal numbers (`seal_numbers`) from Bill of Lading, multimodal transport documents, and transport manifests, supporting multi-container shipments while enforcing strict context safety.

---

## 2. CANONICAL CONTRACT & FIELDS IN SCOPE

From `TransportDocument`:
- `container_numbers: list[CanonicalField[str]] = Field(default_factory=list)`
- `seal_numbers: list[CanonicalField[str]] = Field(default_factory=list)`

Both fields are canonical lists of string tokens. Each token retains independent `CanonicalField` provenance (`ValueOrigin.EXTRACTED`, document ID, page/cell coordinates, raw string).

---

## 3. IN SCOPE

1. **Container Identifier Extraction & ISO 6346 Awareness**:
   - Extraction of standard ISO 6346 container numbers (4 letters [3 owner code + 'U'/'J'/'Z'] + 6 digits + 1 check digit, e.g., `MSKU0123456`, `TGHU7890123`).
   - Support for common layout formats: spaced (`MSKU 012345 6`), hyphenated (`MSKU-012345-6`), and consolidated.
   - Conservative handling of non-standard container formats when explicitly anchored under container column headers or labels.

2. **Seal Identifier Extraction**:
   - Extraction of customs and carrier seal numbers (e.g., `ML-VN123456`, `EMC789456`, `SEAL: 098765`).
   - Anchored extraction from dedicated seal columns, "SEAL NO", "CARRIER SEAL", or "CUSTOMS SEAL" labels.

3. **Multi-Value Extraction in PDF & Excel**:
   - Handling documents with multiple containers and seals (FCL shipments, multi-container manifests).
   - Dedicated tabular blocks: container table rows where container, seal, package count, and weight coexist on a row.
   - Inline comma/slash separated lists: conservative tokenization without losing check digits or prefixes.

4. **Context Safety & Disambiguation**:
   - Strict boundaries to prevent container numbers from leaking into `document_number` (B/L number) or vice versa.
   - Prevent seal numbers from being mistaken for container numbers, invoice references, or phone/tax numbers.

---

## 4. ARCHITECTURAL BOUNDARIES & SAFETY INVARIANTS

1. **No Positional Pairing Assumption**:
   - `container_numbers` and `seal_numbers` are independent lists.
   - Positional index (e.g. `container_numbers[i]` and `seal_numbers[i]`) MUST NEVER be assumed to establish container-to-seal pairing. The schema does not model paired container objects; treating them as ordered pairs is strictly forbidden.

2. **No Value Fabrication**:
   - Missing container numbers or seal numbers remain empty lists `[]`.
   - No placeholder or dummy container identifiers may be inserted.

3. **Air Waybill Context**:
   - Air Waybills typically do not feature standard intermodal ocean containers (they use ULDs / air pallets). If ULD containers appear under AWB container labels, they are recorded as string tokens; absence of containers in AWBs is normal and must not trigger false warnings.

4. **Provenance Integrity**:
   - Each individual container number and seal number must have its own distinct provenance bounding box or cell reference.

---

## 5. OUT OF SCOPE

- Full transport extraction orchestration and database persistence (TASK-008D).
- Cross-document validation (e.g., comparing B/L container numbers against Packing List container numbers).
- Container tare weight calculation or TEU/FEU aggregation.
- Sea Waybill classification or modifications.

---

## 6. ACCEPTANCE CRITERIA

- [ ] AC-01: Multi-container and single-container documents extract all valid container numbers losslessly.
- [ ] AC-02: Multi-seal and single-seal references extract without truncation or concatenation.
- [ ] AC-03: ISO 6346 container formats (spaced, hyphenated, solid) normalize cleanly into canonical string values while preserving raw tokens.
- [ ] AC-04: Container numbers never leak into B/L document number, booking number, or voyage.
- [ ] AC-05: Container numbers and seal numbers remain independent lists with zero implicit positional pairing.
- [ ] AC-06: Full test suite passes with zero regressions.

---

## 7. REVIEW & APPROVAL GATES

- Developer Handoff -> Independent Technical Review (Antigravity) -> Project Leader Approval (ChatGPT).
