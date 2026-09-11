# TASK-005 — Document Classification

Status: IN_PROGRESS  
Priority: P1  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Created: 2026-09-11  
Updated: 2026-09-11  
Target Version: V1  
Dependencies: TASK-001 — Project Foundation (DONE); TASK-002 — Canonical Data Schema (DONE); TASK-003 — File Ingestion + Hashing (DONE); TASK-004 — Local PDF / Excel Parsers (DONE)  
Related ADR: None

---

## 1. OBJECTIVE

Implement the V1 document-classification layer that classifies parsed document content into a supported semantic document type while remaining conservative, evidence-backed, layout-agnostic, and cheap.

The classifier must consume technical parsed content from TASK-004 and produce a typed classification result containing:

- `document_id`
- `document_type`
- `confidence`
- `method`
- evidence/clues used for the decision

The system must support `UNKNOWN` and MUST NOT force a classification when evidence is weak or conflicting.

TASK-005 is classification only. It does not extract canonical business fields.

---

## 2. BACKGROUND

Architecture requires classification after parsing and before structured extraction.

Supported classification targets:

```text
COMMERCIAL_INVOICE
PACKING_LIST
BILL_OF_LADING
AIR_WAYBILL
CUSTOMS_DECLARATION
CONTRACT
PURCHASE_ORDER
CERTIFICATE_OF_ORIGIN
CATALOGUE
SPECIFICATION
OTHER
UNKNOWN
```

Architecture principles:

1. deterministic clues first when evidence is clear;
2. cheap/model fallback may be added when justified;
3. human confirmation for low confidence;
4. filename MUST NOT be the sole evidence;
5. weak evidence must result in `UNKNOWN`, not a guessed type.

For this task, production classification must remain deterministic/local-first. No external AI/provider call is required. The design should leave a clean interface for a future model fallback without coupling the core classifier to a vendor SDK.

---

## 3. SCOPE

TASK-005 MUST:

1. Add a document-type enum containing all V1 types above.
2. Add strict typed/Pydantic classification result/evidence models.
3. Add a classifier interface/contract.
4. Add deterministic classification rules/clue configuration outside business orchestration code where practical.
5. Classify based on parsed content from TASK-004:
   - PDF page text;
   - XLS/XLSX populated cell values converted to classification text/tokens without losing source references.
6. Preserve evidence provenance at least to:
   - PDF page;
   - Excel sheet + cell where the clue originated.
7. Support Vietnamese, English, and Chinese clue phrases where useful.
8. Use multiple clue categories/weighted evidence rather than a single keyword whenever practical.
9. Detect conflicting signals.
10. Apply explicit confidence calculation bounded to `[0.0, 1.0]`.
11. Return `UNKNOWN` below a documented classification threshold or when conflict is unresolved.
12. Avoid classifying from filename alone.
13. Treat filename only as optional weak supporting metadata if used at all; it can never independently produce a non-UNKNOWN result.
14. Load `SourceDocument` through repository boundary.
15. Reuse TASK-004 parsed result through a coherent application service; do not duplicate parser logic.
16. Persist successful classification metadata through repository boundary:
   - `detected_document_type`
   - `classification_confidence`
   - `processing_status`
17. For confident classification:
   - `processing_status = CLASSIFIED`
18. For `UNKNOWN` / low-confidence:
   - `processing_status = NEEDS_REVIEW`
19. Preserve parser metadata (`parser_used`, page_count/sheet_count).
20. Do not modify uploaded source files.
21. Add unit, service/integration, failure, and regression tests.
22. Keep all existing TASK-001..004 tests passing.

---

## 4. OUT OF SCOPE

TASK-005 MUST NOT implement:

- canonical Invoice/Packing/Bill/Declaration field extraction;
- item extraction;
- normalization;
- item matching;
- rule/check engine;
- HS recommendation/classification;
- legal decisions;
- customer-specific templates;
- OCR;
- image/vision OCR;
- DOCX/CSV parser work beyond existing parsed types;
- report generation;
- human field correction workflow;
- UI;
- external network calls;
- vendor-specific AI SDK integration;
- strong-model fallback;
- autonomous agents.

No paid AI call is required in TASK-005.

---

## 5. INPUT

Primary use case input:

```text
document_id
```

The classification service retrieves:

```text
SourceDocument
→ parsed technical content from TASK-004
→ deterministic classifier
```

Supported parsed inputs in TASK-005:

```text
PDF
XLSX
XLS
```

Files that TASK-004 cannot parse locally must not be fabricated into classification input.

---

## 6. OUTPUT

Conceptual result:

```json
{
  "document_id": "DOC-001",
  "document_type": "COMMERCIAL_INVOICE",
  "confidence": 0.96,
  "method": "DETERMINISTIC",
  "evidence": [
    {
      "clue": "COMMERCIAL INVOICE",
      "page": 1,
      "sheet": null,
      "cell": null,
      "weight": 0.45
    },
    {
      "clue": "Invoice No.",
      "page": 1,
      "sheet": null,
      "cell": null,
      "weight": 0.20
    }
  ]
}
```

Weak result:

```json
{
  "document_id": "DOC-002",
  "document_type": "UNKNOWN",
  "confidence": 0.42,
  "method": "DETERMINISTIC",
  "evidence": []
}
```

---

## 7. FUNCTIONAL REQUIREMENTS

### FR-01 — DocumentType enum

Must include exactly or equivalently:

```text
COMMERCIAL_INVOICE
PACKING_LIST
BILL_OF_LADING
AIR_WAYBILL
CUSTOMS_DECLARATION
CONTRACT
PURCHASE_ORDER
CERTIFICATE_OF_ORIGIN
CATALOGUE
SPECIFICATION
OTHER
UNKNOWN
```

### FR-02 — Classification result

Typed result with:

```text
document_id
document_type
confidence
method
evidence[]
```

`confidence` bounded `[0,1]`.

Extra fields forbidden.

### FR-03 — Evidence provenance

Each evidence item should preserve enough technical provenance to find the clue:

```text
clue / matched_phrase
page
sheet
cell
weight / score contribution
```

Do not invent page/sheet/cell coordinates.

### FR-04 — Deterministic clue configuration

Keep classification clue definitions external/configurable where practical, preferably under:

```text
config/document_classification.yaml
```

or a similarly clear versioned configuration.

Avoid scattering document-specific keyword lists across application code.

### FR-05 — Initial deterministic clue families

At minimum support meaningful clues for:

#### Commercial Invoice
Examples:
- COMMERCIAL INVOICE
- INVOICE NO / INVOICE NUMBER
- 发票 / 商业发票
- HÓA ĐƠN / HÓA ĐƠN THƯƠNG MẠI
- UNIT PRICE
- AMOUNT / TOTAL AMOUNT

#### Packing List
- PACKING LIST
- 装箱单
- PHIẾU ĐÓNG GÓI / BẢNG KÊ ĐÓNG GÓI
- GROSS WEIGHT
- NET WEIGHT
- PACKAGE / CARTON

#### Bill of Lading
- BILL OF LADING
- B/L
- 提单
- SHIPPER
- CONSIGNEE
- VESSEL / VOYAGE
- PORT OF LOADING / DISCHARGE

#### Air Waybill
- AIR WAYBILL
- AWB
- 航空运单
- FLIGHT
- AIRPORT OF DEPARTURE / DESTINATION

#### Customs Declaration
- CUSTOMS DECLARATION
- TỜ KHAI HẢI QUAN
- 海关申报 / 报关单
- DECLARATION NO
- HS CODE
- CUSTOMS OFFICE

#### Contract
- CONTRACT
- SALES CONTRACT / PURCHASE CONTRACT
- 合同
- HỢP ĐỒNG
- PARTY A / PARTY B or equivalent

#### Purchase Order
- PURCHASE ORDER
- PO NO
- 采购订单
- ĐƠN ĐẶT HÀNG

#### Certificate of Origin
- CERTIFICATE OF ORIGIN
- C/O
- 原产地证
- GIẤY CHỨNG NHẬN XUẤT XỨ
- FORM E / FORM D / etc. only as supporting clues, not sole decisive clue

#### Catalogue
- CATALOGUE / CATALOG
- 产品目录
- DANH MỤC SẢN PHẨM
- product-specification-like content without transactional document structure

#### Specification
- SPECIFICATION
- TECHNICAL SPECIFICATION
- 技术规格
- THÔNG SỐ KỸ THUẬT
- model/parameter/property patterns

The actual config must be conservative and tested against cross-type collisions.

### FR-06 — Strong vs supporting clues

The classifier must distinguish strong title/header clues from generic supporting terms.

Example:
`COMMERCIAL INVOICE` is stronger than `AMOUNT`.

Generic terms like:
`QUANTITY`, `DATE`, `ADDRESS`, `DESCRIPTION`
must never classify a document on their own.

### FR-07 — Multiple clues

A non-UNKNOWN result should normally require:
- one strong clue; or
- multiple independent supporting clues reaching threshold.

A single generic keyword must not be enough.

### FR-08 — Confidence

Confidence must be deterministic and documented.

Requirements:
- `[0,1]`;
- monotonic with stronger/more coherent evidence;
- capped at 1.0;
- weak evidence stays below threshold;
- no artificial 0.99/1.0 solely from one generic word.

### FR-09 — Conflict

If two incompatible document types receive similarly strong evidence and the margin is below a documented minimum:

```text
document_type = UNKNOWN
processing_status = NEEDS_REVIEW
```

Do not arbitrarily choose first enum/order.

### FR-10 — Filename

Filename may not be sole evidence.

Preferred V1 behavior: do not use filename in score at all.

If used as weak metadata:
- weight must be lower than content evidence;
- filename-only result remains UNKNOWN.

### FR-11 — PDF flattening

Classifier may inspect normalized lines/tokens from all parsed pages, but evidence must retain page provenance.

Do not remove page boundaries from evidence.

### FR-12 — Excel flattening

Classifier may inspect populated cell strings, but evidence must retain sheet + coordinate provenance.

Do not classify based on workbook/sheet filename/name alone without content evidence.

### FR-13 — Parsing dependency

Classification application service may call/reuse `DocumentParsingService`.

It must not reimplement PDF/XLS/XLSX parsing.

### FR-14 — SourceDocument persistence

Repository must support a classification metadata update behind its boundary.

On confident result:

```text
detected_document_type = result.document_type
classification_confidence = result.confidence
processing_status = CLASSIFIED
```

On UNKNOWN/low confidence:

```text
detected_document_type = UNKNOWN
classification_confidence = result.confidence
processing_status = NEEDS_REVIEW
```

Parser metadata must remain unchanged.

### FR-15 — Failure behavior

If parser/classifier/repository update fails:
- do not falsely persist CLASSIFIED;
- do not modify source file;
- raise deterministic application error;
- do not expose full document text or absolute filesystem path.

### FR-16 — Idempotence

Running classification repeatedly on unchanged parsed content/config must produce the same classification output and must not create duplicate side effects.

### FR-17 — No semantic extraction

Classification evidence may mention matched phrases but must not create canonical invoice numbers, totals, parties, item lines, etc.

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- NFR-01: External AI allowed: NO for TASK-005 implementation.
- NFR-02: Network/API calls: NO.
- NFR-03: Deterministic for same parsed input + config version.
- NFR-04: No document full-text logging.
- NFR-05: No customer data in fixtures.
- NFR-06: No hard-coded customer layouts.
- NFR-07: Business orchestration not in FastAPI routes.
- NFR-08: Persistence behind repository boundary.
- NFR-09: No heavy ML/NLP framework.
- NFR-10: Python >=3.12, including user Python 3.13.
- NFR-11: Existing 100-test TASK-001..004 suite must not regress.
- NFR-12: Config changes versioned in Git.
- NFR-13: No secret/API-key requirement.

---

## 9. BUSINESS RULES

None.

Document classification is technical/semantic routing, not customs/legal judgment.

---

## 10. DATA MODEL IMPACT

Creates classification-specific models only, for example:

```text
DocumentType
ClassificationMethod
ClassificationEvidence
DocumentClassificationResult
```

Do not modify TASK-002 canonical Invoice/PackingList/TransportDocument/CustomsDeclaration semantics.

---

## 11. FILES / MODULES EXPECTED

Expected:

```text
config/document_classification.yaml

src/customs_ai/classification/
    __init__.py
    enums.py
    models.py
    errors.py
    config.py
    deterministic.py
    service.py

src/customs_ai/repositories/source_documents.py

tests/unit/classification/
tests/unit/repositories/
```

Exact split is flexible if coherent.

No new classification HTTP endpoint is required.

---

## 12. DEPENDENCIES

Prefer no new runtime dependency.

Use:
- stdlib
- PyYAML already present
- existing Pydantic

Do NOT add:
- scikit-learn
- pandas
- transformers
- spaCy
- LangChain/LlamaIndex
- vendor AI SDK

without Project Leader approval.

---

## 13. EDGE CASES

Must consider:

- empty parsed PDF text;
- PDF with only generic words;
- multilingual clues;
- same phrase repeated many times;
- strong clue + generic clues;
- conflicting strong clues;
- invoice vs packing list overlap;
- bill of lading vs air waybill overlap;
- catalogue vs specification overlap;
- C/O `FORM E` without `CERTIFICATE OF ORIGIN`;
- Excel with clues spread across sheets;
- Unicode casefold/normalization;
- punctuation variants (`B/L`, `B.L.`, `BILL OF LADING`);
- filename says invoice but content says packing list;
- unknown source document;
- parser failure;
- repository metadata update failure;
- reclassification idempotence.

Repeated same clue occurrence must not inflate confidence without bound.

---

## 14. ACCEPTANCE CRITERIA

### AC-01
Clear Commercial Invoice synthetic content classifies `COMMERCIAL_INVOICE` with confidence above threshold.

### AC-02
Clear Packing List classifies `PACKING_LIST`.

### AC-03
Clear B/L and AWB samples are distinguished.

### AC-04
Customs Declaration synthetic content classifies correctly.

### AC-05
Contract, PO, C/O, Catalogue, Specification each have at least one positive fixture/test.

### AC-06
Weak/generic content returns `UNKNOWN`.

### AC-07
Conflicting high-signal content returns `UNKNOWN`/NEEDS_REVIEW when score margin is insufficient.

### AC-08
Filename-only clue cannot produce confident non-UNKNOWN classification.

### AC-09
PDF evidence retains page provenance.

### AC-10
Excel evidence retains sheet + cell provenance.

### AC-11
Confidence is bounded and deterministic.

### AC-12
Successful classification updates SourceDocument classification fields/status without changing parser metadata.

### AC-13
UNKNOWN classification persists UNKNOWN + NEEDS_REVIEW without fabricated certainty.

### AC-14
Repository update failure does not modify source file or falsely report success.

### AC-15
Full pytest suite passes including all previous 100 tests.

### AC-16
No extraction/normalization/matching/rules/AI/network scope creep.

---

## 15. TEST REQUIREMENTS

### Unit — Config/models/scoring
- enum coverage;
- strict model validation;
- confidence bounds;
- config loads CWD-independently;
- malformed config fails clearly;
- duplicate repeated clue does not inflate score unboundedly;
- strong vs supporting clue behavior;
- conflict margin behavior.

### Positive classification
At minimum test:
- Commercial Invoice;
- Packing List;
- Bill of Lading;
- Air Waybill;
- Customs Declaration;
- Contract;
- Purchase Order;
- Certificate of Origin;
- Catalogue;
- Specification.

Use synthetic multilingual samples where useful.

### Negative/ambiguity
- empty;
- generic quantity/date/description only;
- invoice/packing conflict;
- B/L/AWB conflict;
- filename contradiction;
- `FORM E` alone;
- OTHER/UNKNOWN behavior documented and tested.

### Provenance
- PDF evidence page;
- Excel evidence sheet/cell.

### Application/repository
- SourceDocument lookup;
- successful metadata persistence;
- UNKNOWN → NEEDS_REVIEW;
- parser metadata preserved;
- repository failure no false success;
- idempotent repeat.

### Regression
Run entire suite.

Pre-TASK-005 authoritative baseline:

```text
100 passed, 2 warnings
```

Final count must be greater than 100.
Do not hard-code the final expected count in production code.

---

## 16. TEST DATA

Synthetic/anonymized only.

Examples may use:

```text
COMMERCIAL INVOICE
Invoice No: INV-TEST-001
测试发票
Hóa đơn thử nghiệm
```

No real customer documents or identities.

---

## 17. OBSERVABILITY

Safe logs:
- document_id;
- final document_type;
- confidence;
- method;
- processing status;
- error code.

Do NOT log:
- full parsed text;
- full Excel cell values;
- absolute source path;
- credentials.

---

## 18. COST REQUIREMENTS

```text
AI allowed: NO
External network calls: NO
New paid services: NO
```

Deterministic/local classification first.

Architecture may later add a cheap-model fallback behind a provider-neutral interface in a separate approved task/change.

---

## 19. SECURITY / PRIVACY

- no source file mutation;
- no secret/API keys;
- no production documents in tests;
- no content logging;
- repository boundary;
- deterministic config;
- no code execution from document content;
- no external model calls.

---

## 20. DEPENDENCIES

Depends on TASK-004 because classification consumes parsed content.

TASK-006 Invoice Extraction depends on TASK-005 and TASK-004.

---

## 21. DELIVERABLES

- classification enum/models;
- deterministic clue config;
- deterministic classifier;
- classification orchestration service;
- repository update support;
- tests;
- README documentation;
- Developer Completion Report;
- exact created/modified file list;
- local validation commands.

---

## 22. DEFINITION OF DONE

- [ ] TASK-004 already DONE/pushed
- [ ] all V1 document types represented
- [ ] deterministic config-backed classifier implemented
- [ ] confidence deterministic and bounded
- [ ] weak/conflicting evidence → UNKNOWN
- [ ] filename not sole evidence
- [ ] PDF/Excel evidence provenance retained
- [ ] SourceDocument classification metadata persisted
- [ ] UNKNOWN → NEEDS_REVIEW
- [ ] parser metadata preserved
- [ ] no extraction/AI/network scope creep
- [ ] all TASK-005 tests pass
- [ ] all prior 100 regression tests pass
- [ ] no unresolved CRITICAL/HIGH
- [ ] Gemini #2 APPROVE
- [ ] Project Leader APPROVE
- [ ] no secrets/customer data
- [ ] ready to move to tasks/done/

---

## 23. DEVELOPER NOTES

Gemini #1 updates when necessary.

If deterministic clues are not sufficient for a sample, return UNKNOWN. Do not silently add a paid/model fallback inside this task.

---

## 24. REVIEW NOTES

Gemini #2 updates during review.

---

## 25. PROJECT LEADER DECISION

Pending.
