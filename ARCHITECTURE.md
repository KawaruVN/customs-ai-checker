# ARCHITECTURE.md

# Customs AI Checker — System Architecture

Version: 0.1  
Status: Draft  
Project: Customs AI Checker  
Applies to: V1

Amendment 2026-10-30: Sections 69–72 propose the architecture needed for the
Owner's versioned arrival/declaration policy (MASTER_SPEC Section 61). Business
requirements are Owner-approved; technical amendment review, merge and closure completed (commit c8032cc).
Descriptions of future modules are target design, not claims of implemented behavior.

---

# 1. PURPOSE

Tài liệu này mô tả kiến trúc kỹ thuật của Customs AI Checker V1.

Mục tiêu của kiến trúc:

- xử lý được chứng từ nhiều layout;
- giữ được nguồn gốc dữ liệu;
- kiểm tra deterministic khi có thể;
- chỉ gọi AI khi cần;
- chi phí vận hành thấp;
- dễ test;
- dễ thay model AI;
- dễ mở rộng sang loại hình, master data, HS và pháp lý sau V1;
- tránh over-engineering.

---

# 2. ARCHITECTURE STYLE

V1 sử dụng:

**Modular Monolith**

Không sử dụng microservices trong V1.

Các module được tách rõ trong cùng một codebase để sau này có thể thay thế hoặc tách riêng nếu thực sự cần.

Luồng tổng quát:

```text
User / UI
   ↓
Application Service
   ↓
Document Ingestion
   ↓
Parsing / Text Extraction
   ↓
Document Classification
   ↓
Structured Data Extraction
   ↓
Normalization
   ↓
Canonical Data Model
   ↓
Document & Item Matching
   ↓
Rule Engine
   ↓
AI Reasoning Gateway (chỉ khi cần)
   ↓
Check Results
   ↓
Report / Evidence
   ↓
Human Correction / Recheck
```

---

# 3. V1 TECHNOLOGY BASELINE

Ưu tiên công nghệ phổ biến, dễ bảo trì, chi phí thấp.

## 3.1 Language

Python 3.12 hoặc phiên bản stable tương thích.

## 3.2 Backend

FastAPI.

FastAPI chịu trách nhiệm:

- upload file;
- tạo shipment;
- gọi processing pipeline;
- trả extracted data;
- chạy checks;
- human correction;
- report API.

Business logic không được đặt trực tiếp trong route handler.

## 3.3 V1 UI

Ưu tiên một UI mỏng.

Phương án V1:

- Streamlit cho prototype nội bộ; hoặc
- giao diện web tối giản gọi FastAPI.

Business logic không được phụ thuộc Streamlit.

Nếu Streamlit được sử dụng, nó chỉ là presentation layer.

## 3.4 Database

SQLite cho V1.

Lý do:

- không cần server database riêng;
- dễ backup;
- chi phí bằng 0;
- đủ cho một người hoặc nhóm nhỏ dùng nội bộ;
- dễ migrate sang PostgreSQL sau này.

Không viết business logic phụ thuộc riêng SQLite.

Database access phải đi qua repository/data-access layer.

## 3.5 Structured Model Validation

Pydantic.

Dùng cho:

- API request/response;
- canonical schema;
- AI structured output validation;
- configuration validation.

## 3.6 Database Layer

Có thể dùng SQLAlchemy.

Không bắt buộc ORM phức tạp.

Ưu tiên schema rõ ràng và migration có kiểm soát.

## 3.7 Configuration

YAML + environment variables.

Ví dụ:

```text
config/
  app.yaml
  model_routing.yaml
  unit_mappings.yaml
  tolerances.yaml
```

Secrets không được lưu trong YAML commit lên GitHub.

---

# 4. REPOSITORY TARGET STRUCTURE

Cấu trúc đề xuất:

```text
customs-ai-checker/
│
├── README.md
├── PROJECT_CONSTITUTION.md
├── MASTER_SPEC.md
├── ARCHITECTURE.md
├── TASK_TEMPLATE.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── docs/
│   ├── DATA_SCHEMA.md
│   ├── RULE_FORMAT.md
│   ├── AI_PROVIDER_INTERFACE.md
│   └── decisions/
│
├── config/
│   ├── app.yaml
│   ├── model_routing.yaml
│   ├── unit_mappings.yaml
│   └── tolerances.yaml
│
├── rules/
│   ├── global/
│   ├── declaration_types/
│   └── customers/
│
├── tasks/
│   ├── todo/
│   ├── in_progress/
│   └── done/
│
├── reviews/
│
├── test_documents/
│
├── data/
│   ├── uploads/
│   ├── cache/
│   └── app.db
│
├── src/
│   └── customs_ai/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── api/
│       ├── application/
│       ├── domain/
│       ├── ingestion/
│       ├── parsers/
│       ├── classification/
│       ├── extraction/
│       ├── normalization/
│       ├── matching/
│       ├── rules/
│       ├── checks/
│       ├── ai/
│       ├── repositories/
│       ├── reporting/
│       ├── audit/
│       └── utils/
│
└── tests/
    ├── unit/
    ├── integration/
    ├── regression/
    └── fixtures/
```

`data/` không được commit nếu chứa dữ liệu thật.

---

# 5. DOMAIN MODEL

Các entity cốt lõi của V1:

```text
Shipment
SourceDocument
DocumentExtraction
CanonicalField
Party
Invoice
InvoiceItem
PackingList
PackingItem
TransportDocument
CustomsDeclaration
ItemMatch
Rule
CheckResult
Evidence
HumanCorrection
ProcessingRun
AIUsageRecord
```

Chi tiết schema sẽ được định nghĩa trong `docs/DATA_SCHEMA.md`.

---

# 6. SHIPMENT

`Shipment` là container logic cho một lần kiểm tra bộ chứng từ.

Một Shipment có thể chứa:

- 0..N Invoice;
- 0..N Packing List;
- 0..N Bill/AWB;
- 0..N Customs Declaration;
- các chứng từ khác.

Shipment không được giả định chỉ có một invoice.

Ví dụ ID:

```text
SHP-2026-000001
```

---

# 7. SOURCE DOCUMENT

Mỗi file upload tạo một `SourceDocument`.

Tối thiểu lưu:

```text
document_id
shipment_id
original_filename
stored_path
file_hash
mime_type
file_size
page_count
sheet_count
detected_document_type
classification_confidence
processing_status
created_at
```

Không lưu file bằng tên người dùng làm primary identifier.

---

# 8. FILE STORAGE

V1 lưu file local.

Ví dụ:

```text
data/uploads/{shipment_id}/{document_id}/original.ext
```

Không dựa vào tên file để xác định loại chứng từ.

File hash dùng SHA-256.

Hash phục vụ:

- duplicate detection;
- cache;
- audit.

---

# 9. INGESTION MODULE

Module:

```text
src/customs_ai/ingestion/
```

Nhiệm vụ:

1. nhận file;
2. validate file;
3. xác định MIME;
4. giới hạn dung lượng;
5. tính SHA-256;
6. kiểm duplicate;
7. lưu file;
8. tạo SourceDocument;
9. chuyển cho parser router.

Không thực hiện business rule tại ingestion.

---

# 10. PARSER ROUTER

Module:

```text
src/customs_ai/parsers/
```

Parser Router quyết định parser nào xử lý file.

Ví dụ:

```text
PDF → PDFParser
XLS/XLSX → ExcelParser
CSV → CSVParser
DOCX → DocxParser
JPG/PNG → ImageParser
```

Parser chỉ có nhiệm vụ lấy nội dung kỹ thuật.

Không tự kết luận:

"đây là invoice"

trừ khi metadata kỹ thuật rõ ràng.

---

# 11. PDF PROCESSING

Ưu tiên local text extraction trước.

Pipeline:

```text
PDF
 ↓
Có text layer?
 ├─ YES → Local text extraction
 └─ NO  → OCR / vision fallback
```

Không dùng model vision cho mọi PDF nếu text extraction local đủ dùng.

Output parser cần giữ page boundaries.

Ví dụ:

```json
{
  "pages": [
    {
      "page": 1,
      "text": "..."
    }
  ]
}
```

---

# 12. EXCEL PROCESSING

Excel phải được đọc bằng parser local.

Ưu tiên:

- `openpyxl` cho XLSX;
- parser tương thích cho XLS nếu cần.

Parser phải giữ:

- workbook name;
- sheet name;
- cell location;
- raw value;
- displayed value nếu khả thi;
- merged cells;
- hidden sheet/row metadata khi cần.

Không gửi nguyên workbook sang LLM nếu có thể lấy dữ liệu local trước.

---

# 13. IMAGE / SCAN PROCESSING

Image/scan pipeline:

```text
Image
 ↓
Basic validation
 ↓
OCR / multimodal extraction
 ↓
Text + location/evidence
```

OCR là fallback, không phải mặc định cho file có text layer tốt.

Nếu OCR confidence thấp:

`NEEDS_REVIEW`.

---

# 14. DOCUMENT CLASSIFICATION

Module:

```text
src/customs_ai/classification/
```

Nhiệm vụ:

Xác định:

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

Classification sử dụng:

1. deterministic clues nếu rõ;
2. model nhỏ nếu cần;
3. human confirmation khi confidence thấp.

Không dùng filename làm bằng chứng duy nhất.

---

# 15. CLASSIFICATION OUTPUT

Ví dụ:

```json
{
  "document_id": "DOC-001",
  "document_type": "COMMERCIAL_INVOICE",
  "confidence": 0.97,
  "method": "llm",
  "evidence": [
    "COMMERCIAL INVOICE",
    "Invoice No.",
    "Unit Price",
    "Amount"
  ]
}
```

Nếu không chắc:

```json
{
  "document_type": "UNKNOWN",
  "confidence": 0.42
}
```

---

# 16. EXTRACTION MODULE

Module:

```text
src/customs_ai/extraction/
```

Extraction chuyển parsed content thành structured document data.

Không viết một extractor riêng theo từng khách hàng trừ khi có adapter chính thức.

Ưu tiên schema theo document type.

Ví dụ:

```text
InvoiceExtractionSchema
PackingListExtractionSchema
TransportDocumentExtractionSchema
DeclarationExtractionSchema
```

---

# 17. EXTRACTION STRATEGY

Thứ tự ưu tiên:

```text
Deterministic/local extraction
→ inexpensive LLM structured extraction
→ stronger LLM fallback
→ NEEDS_REVIEW
```

Ví dụ:

Excel có bảng rõ:

local parser có thể lấy table trước.

LLM chỉ map table đó vào semantic field.

Không gửi binary file sang model nhiều lần nếu không cần.

---

# 18. EXTRACTION EVIDENCE

Mỗi extracted field phải cố gắng giữ provenance.

Ví dụ:

```json
{
  "field_name": "invoice_number",
  "raw_value": "INV-260901",
  "normalized_value": "INV-260901",
  "origin": "EXTRACTED",
  "source_document_id": "DOC-001",
  "page": 1,
  "sheet": null,
  "cell": null,
  "confidence": 0.99
}
```

---

# 19. NORMALIZATION MODULE

Module:

```text
src/customs_ai/normalization/
```

Normalization là deterministic nếu có thể.

Các normalizer dự kiến:

```text
DateNormalizer
NumberNormalizer
CurrencyNormalizer
UnitNormalizer
PartyNameNormalizer
TextNormalizer
CountryNormalizer
ItemCodeNormalizer
```

Normalization không được xóa raw value.

---

# 20. UNIT MAPPING

Unit mapping nằm trong configuration.

Ví dụ:

```yaml
PCS:
  - PCS
  - PC
  - PIECE
  - PIECES

SET:
  - SET
  - SETS
```

Không map `PCS` sang `SET`.

Mapping mơ hồ phải yêu cầu review hoặc rule riêng.

---

# 21. CANONICAL DATA MODEL

Sau extraction + normalization, tất cả downstream logic chỉ làm việc chủ yếu với Canonical Model.

Không để Rule Engine phải hiểu:

```text
Invoice A layout
Invoice B layout
Invoice C layout
```

Rule Engine chỉ hiểu:

```text
invoice.total_amount
invoice.items[].quantity
packing_list.items[].quantity
```

---

# 22. MATCHING MODULE

Module:

```text
src/customs_ai/matching/
```

Có hai nhóm matching:

1. Document relationship matching.
2. Item matching.

Ví dụ document relationship:

```text
Packing List → Invoice reference
C/O → Invoice
Declaration → Invoice
```

---

# 23. ITEM MATCHING PIPELINE

Ưu tiên:

```text
Exact item code
→ Exact part number
→ Exact model
→ Normalized identifier
→ Multi-field deterministic score
→ Semantic similarity
→ AI reasoning fallback
→ UNMATCHED
```

Không dùng semantic AI nếu exact ID đã match chắc chắn.

---

# 24. ITEM MATCH RESULT

Ví dụ:

```json
{
  "invoice_item_id": "INVITEM-01",
  "packing_item_id": "PLITEM-04",
  "match_type": "EXACT_ITEM_CODE",
  "confidence": 1.0,
  "evidence": {
    "invoice_item_code": "ABG-1012H1",
    "packing_item_code": "ABG-1012H1"
  }
}
```

---

# 25. RULE ENGINE

Module:

```text
src/customs_ai/rules/
```

Rule Engine không được chứa toàn bộ business rules hard-code trong Python.

Python chịu trách nhiệm:

- load rule;
- validate rule schema;
- xác định rule applicable;
- lấy required input;
- evaluate operator;
- tạo CheckResult.

Rule configuration chịu trách nhiệm:

- rule áp dụng khi nào;
- check field nào;
- tolerance;
- severity;
- output message;
- source/category.

---

# 26. RULE STORAGE

Rule nằm tại:

```text
rules/global/
rules/declaration_types/
rules/customers/
```

Ví dụ:

```text
rules/global/invoice_total.yaml
rules/declaration_types/E13.yaml
rules/customers/CUSTOMER_A.yaml
```

Không trộn customer rule vào global rule.

---

# 27. RULE CATEGORIES

Rule phải phân biệt:

```text
DATA_VALIDATION
CROSS_DOCUMENT
INTERNAL_POLICY
CUSTOMER_SPECIFIC
LEGAL
HEURISTIC
```

Rule `LEGAL` cần source được xác minh.

---

# 28. RULE RESULT

Rule Engine tạo `CheckResult`.

Ví dụ:

```json
{
  "rule_id": "QTY_MATCH_001",
  "status": "ERROR",
  "severity": "HIGH",
  "title": "Quantity mismatch",
  "message": "Invoice and Packing List quantities differ.",
  "evidence_ids": [
    "EVD-101",
    "EVD-102"
  ]
}
```

---

# 29. CHECK ENGINE

Module:

```text
src/customs_ai/checks/
```

Check Engine orchestration:

```text
Canonical Shipment
 ↓
Applicable Rules
 ↓
Resolve Inputs
 ↓
Execute deterministic checks
 ↓
Collect unresolved checks
 ↓
Optional AI reasoning
 ↓
CheckResults
```

Không gọi AI cho tất cả rule.

---

# 30. TOLERANCE

Tolerance phải configurable.

Ví dụ:

```yaml
weight:
  absolute_kg: 0.5
  relative_percent: 0.1

money:
  absolute: 0.01
```

Tolerance không hard-code rải rác.

---

# 31. AI PROVIDER LAYER

Module:

```text
src/customs_ai/ai/
```

Interface chung:

```text
AIProvider
├── classify_document()
├── extract_structured_data()
├── semantic_match()
└── reason_about_anomaly()
```

Provider adapters:

```text
OpenAIProvider
GeminiProvider
```

Core business logic không import trực tiếp SDK vendor ở nhiều nơi.

---

# 32. MODEL ROUTER

Model Router quyết định model nào được dùng.

Ví dụ policy:

```text
classification → cheap model
standard extraction → cheap model
hard scan → stronger model
ambiguous semantic matching → stronger model
arithmetic validation → no AI
```

Routing config nằm ngoài code khi có thể.

---

# 33. AI REQUEST CONTRACT

Mỗi AI call phải có:

```text
task_type
provider
model
prompt_id
prompt_version
input_reference
expected_schema
timeout
retry_policy
```

Mỗi response phải được validate.

---

# 34. STRUCTURED OUTPUT VALIDATION

AI structured output phải qua Pydantic trước khi được lưu hoặc dùng downstream.

Nếu invalid:

```text
retry once if appropriate
→ fallback model if policy permits
→ NEEDS_REVIEW
```

Không để malformed JSON chảy thẳng vào Rule Engine.

---

# 35. AI CACHE

Cache key nên bao gồm:

```text
file_hash
task_type
prompt_version
schema_version
provider/model version
```

Nếu các thành phần liên quan không đổi:

reuse result.

---

# 36. DATABASE RESPONSIBILITIES

SQLite lưu:

- shipments;
- source documents;
- extraction records;
- canonical data;
- item matches;
- check results;
- human corrections;
- processing runs;
- rule versions used;
- AI usage records;
- audit events.

Không lưu secrets.

---

# 37. REPOSITORY LAYER

Business layer không query SQL trực tiếp.

Repository interface ví dụ:

```text
ShipmentRepository
DocumentRepository
ExtractionRepository
CheckResultRepository
AuditRepository
```

Điều này cho phép migrate SQLite → PostgreSQL mà không viết lại business logic.

---

# 38. AUDIT MODULE

Module:

```text
src/customs_ai/audit/
```

Audit event tối thiểu:

```text
event_id
timestamp
shipment_id
document_id
action
actor
rule_id
rule_version
model
prompt_version
result_reference
```

Không log dữ liệu nhạy cảm quá mức.

---

# 39. HUMAN CORRECTION

Correction flow:

```text
AI extracted value
 ↓
User edits value
 ↓
Create HumanCorrection record
 ↓
Canonical value updated as active value
 ↓
Affected matching/checks invalidated
 ↓
Selective re-run
```

Không xóa original extraction.

---

# 40. DEPENDENCY TRACKING FOR RECHECK

V1 không cần dependency graph phức tạp.

Có thể dùng mapping đơn giản:

```text
field changed
→ identify affected checks
→ rerun those checks
```

Nếu khó triển khai ban đầu:

rerun all deterministic checks của Shipment vẫn chấp nhận được.

Không cần re-extract file nếu chỉ sửa normalized value.

---

# 41. REPORTING MODULE

Module:

```text
src/customs_ai/reporting/
```

Report builder nhận CheckResults.

Không tự chạy business checks.

Output V1:

- JSON;
- UI view;
- Excel export sau khi core ổn định.

---

# 42. REPORT ORDER

Ưu tiên hiển thị:

```text
CRITICAL
ERROR / HIGH
WARNING
MISSING
NEEDS_REVIEW
PASS
NOT_CHECKED
```

Người dùng phải thấy vấn đề quan trọng trước.

---

# 43. EVIDENCE

Evidence object nên chứa:

```text
evidence_id
document_id
field_name
raw_value
normalized_value
page
sheet
cell
bounding_box nếu có
extraction_id
```

Không bắt buộc bounding box trong V1 nếu parser chưa hỗ trợ.

---

# 44. API LAYER

Module:

```text
src/customs_ai/api/
```

Endpoint định hướng:

```text
POST   /shipments
GET    /shipments/{id}

POST   /shipments/{id}/documents
GET    /shipments/{id}/documents

POST   /shipments/{id}/process
GET    /shipments/{id}/extractions

POST   /shipments/{id}/checks
GET    /shipments/{id}/checks

PATCH  /shipments/{id}/fields/{field_id}
POST   /shipments/{id}/recheck

GET    /shipments/{id}/report
```

API exact schema sẽ được xác định theo task.

---

# 45. APPLICATION SERVICES

Module:

```text
src/customs_ai/application/
```

Application service điều phối use case.

Ví dụ:

```text
CreateShipmentService
UploadDocumentService
ProcessShipmentService
RunChecksService
CorrectFieldService
GenerateReportService
```

Route handler không chứa pipeline logic.

---

# 46. ERROR MODEL

Internal error nên có code rõ ràng.

Ví dụ:

```text
FILE_UNSUPPORTED
FILE_CORRUPTED
PDF_ENCRYPTED
PARSER_FAILED
CLASSIFICATION_FAILED
EXTRACTION_FAILED
SCHEMA_VALIDATION_FAILED
AI_TIMEOUT
RULE_INPUT_MISSING
RULE_EXECUTION_FAILED
```

Không chỉ trả generic:

`Something went wrong`.

---

# 47. PROCESSING STATUS

Document status có thể dùng:

```text
UPLOADED
VALIDATED
PARSED
CLASSIFIED
EXTRACTED
NORMALIZED
FAILED
NEEDS_REVIEW
```

Shipment processing status:

```text
NEW
PROCESSING
READY_FOR_CHECK
CHECKED
NEEDS_REVIEW
FAILED
```

---

# 48. OBSERVABILITY

V1 logging tối thiểu phải trả lời được:

- file nào lỗi;
- parser nào lỗi;
- AI call nào lỗi;
- rule nào tạo warning/error;
- processing mất bao lâu;
- model nào được gọi;
- estimated AI cost.

Không cần hệ monitoring cloud đắt tiền trong V1.

---

# 49. COST ACCOUNTING

Mỗi AI call lưu:

```text
provider
model
input_tokens
output_tokens
estimated_cost
task_type
shipment_id
document_id
timestamp
```

Nếu provider không trả token chính xác thì có thể lưu estimated usage.

---

# 50. SECURITY BASELINE

Tối thiểu:

- `.env` không commit;
- validate upload;
- giới hạn file size;
- sanitize filename;
- không execute macro;
- không execute file content;
- không render HTML từ document mà không sanitize;
- không log API key;
- không public production data.

---

# 51. PRIVACY BASELINE

Production documents nằm ngoài Git repo.

Test public chỉ dùng:

- synthetic;
- anonymized;
- permitted documents.

Nếu gửi dữ liệu lên AI API:

chỉ gửi phần cần thiết cho task.

---

# 52. TEST STRATEGY

## Unit Tests

Test từng:

- normalizer;
- parser helper;
- rule operator;
- matching function;
- validator.

## Integration Tests

Test:

```text
upload
→ parse
→ classify
→ extract
→ normalize
→ check
```

## Regression Tests

Dùng Golden Test Dataset.

## Failure Tests

Test:

- corrupted file;
- invalid model JSON;
- API timeout;
- low confidence;
- missing rule input.

---

# 53. GOLDEN DATASET STRUCTURE

Ví dụ:

```text
tests/fixtures/golden/
  case_001/
    invoice.pdf
    packing_list.xlsx
    expected_extraction.json
    expected_checks.json

  case_002/
    ...
```

Nếu file là dữ liệu thật:

phải anonymize trước khi commit.

---

# 54. DEPENDENCY PRINCIPLE

Không thêm library nếu standard library hoặc dependency hiện tại giải quyết tốt.

Mỗi dependency lớn phải được review.

Không đưa LangChain/LlamaIndex/agent framework vào V1 trừ khi có requirement rõ ràng.

Core system nên dùng SDK/provider interface trực tiếp để giảm complexity.

---

# 55. NO AGENT SWARM IN V1

Production V1 không sử dụng multi-agent swarm.

ChatGPT và Gemini hiện được dùng để **xây dự án**, không phải mặc định là kiến trúc production.

Production V1 là pipeline có kiểm soát.

Điều này giúp:

- predictable;
- cheaper;
- easier to debug;
- easier to audit.

---

# 56. EXECUTION MODEL

V1 có thể xử lý đồng bộ với bộ chứng từ nhỏ.

Nếu processing dài:

có thể thêm background task sau.

Không triển khai distributed queue ở giai đoạn đầu.

Nếu cần background processing V1:

ưu tiên giải pháp nhẹ trước.

---

# 57. DEPLOYMENT — DEVELOPMENT

Chạy local:

```text
Python
SQLite
Local file storage
FastAPI
Optional Streamlit UI
AI API via environment variables
```

Không yêu cầu Docker trong task đầu tiên.

Có thể thêm Docker sau khi core pipeline ổn.

---

# 58. DEPLOYMENT — FUTURE

Khi cần nhiều người dùng:

```text
FastAPI
PostgreSQL
Object Storage
Background worker
Authentication
Central logging
```

Việc migrate này không được yêu cầu trong V1.

---

# 59. DATABASE MIGRATION PATH

V1:

```text
SQLite
```

Future:

```text
PostgreSQL
```

Do đó:

- không dùng SQLite-specific business logic;
- dùng repository layer;
- dùng migration tool khi schema bắt đầu ổn định.

---

# 60. MODEL MIGRATION PATH

V1 phải cho phép:

```text
Gemini model A
→ OpenAI model B
```

hoặc ngược lại mà không thay Rule Engine.

Chỉ provider adapter + routing config cần thay đổi.

---

# 61. INITIAL DEVELOPMENT ORDER

Thứ tự triển khai đề xuất:

```text
TASK-001 Project Foundation
TASK-002 Canonical Data Schema
TASK-003 File Ingestion + Hashing
TASK-004 Local PDF/Excel Parsers
TASK-005 Document Classification
TASK-006 Invoice Extraction
TASK-007 Packing List Extraction
Docs amendment review / approval / merge / closure (before TASK-008A)
TASK-008A -> B -> C -> D -> E Transport Document Extraction (B/L-AWB only)
TASK-016A -> B -> C -> D Arrival Notice SEA/AIR & Operational Evidence
TASK-017 Declaration Intake (structured/manual first)
TASK-009 Normalization
TASK-010 Document Relationship + Item Matching
TASK-011 Rule Engine Foundation
TASK-012 A Document-to-document; B Required source-to-declaration + coverage
TASK-013 Report Generation
TASK-014 Human Correction
TASK-015 Golden Dataset Regression
```

Không triển khai HS / legal engine trước khi core checker ổn.

---

# 62. TASK-001 TARGET

Task đầu tiên không được cố build full product.

TASK-001 chỉ nên dựng:

- Python project;
- package structure;
- basic configuration;
- logging;
- test setup;
- `.gitignore`;
- `.env.example`;
- health endpoint hoặc minimal app startup;
- CI optional nếu đơn giản.

Không gọi AI trong TASK-001.

---

# 63. ARCHITECTURE BOUNDARIES

Các boundary không được phá tùy tiện:

```text
API/UI
    ↓
Application Services
    ↓
Domain / Pipeline
    ↓
Infrastructure Adapters
```

Domain logic không import UI.

Rule Engine không import FastAPI.

Normalizer không gọi database nếu không cần.

Parser không tự chạy rules.

AI provider không quyết định business severity.

---

# 64. SOURCE OF TRUTH

Thứ tự nguồn quyết định:

```text
PROJECT_CONSTITUTION.md
→ MASTER_SPEC.md
→ ARCHITECTURE.md
→ DATA_SCHEMA.md / RULE_FORMAT.md
→ TASK
→ Implementation
```

Nếu Developer thấy conflict:

dừng phần bị conflict và báo Project Leader.

Không tự chọn một interpretation rồi âm thầm code.

---

# 65. ARCHITECTURE CHANGE POLICY

Các thay đổi sau cần ADR:

- đổi database chính;
- đổi architecture style;
- thêm queue;
- thêm vector database;
- đổi canonical schema lớn;
- thêm orchestration framework;
- thay AI provider abstraction;
- thêm external storage;
- thay security model.

ADR lưu tại:

```text
docs/decisions/
```

---

# 66. V1 NON-GOALS

Architecture V1 không cần:

- Kubernetes;
- microservices;
- Redis;
- Kafka;
- vector database mặc định;
- autonomous agents;
- VNACCS automation;
- browser automation;
- legal auto-decision;
- final HS classification;
- mobile app.

---

# 67. SUCCESS CONDITION

Kiến trúc V1 đạt yêu cầu khi có thể xử lý flow:

```text
Create Shipment
→ Upload Invoice + Packing List + Bill
→ Obtain mandatory Arrival Notice SEA/AIR + declaration data for applicable workflow
→ Parse locally where possible
→ Classify documents
→ Extract structured data
→ Normalize
→ Match items
→ Run deterministic checks
→ Use AI only for unresolved semantic tasks
→ Produce evidence-backed report
→ Allow correction
→ Recheck
```

mà không phụ thuộc vào layout cố định của một khách hàng.

---

# 68. FINAL ARCHITECTURE PRINCIPLES

```text
AI for ambiguity.
Code for certainty.

Extract once.
Reuse often.

Preserve raw data.
Preserve evidence.

Rules outside application code where practical.

Model providers are replaceable.

SQLite first.
PostgreSQL when justified.

Modular monolith first.
Distributed systems only when justified.

No expensive AI call without a reason.

No PASS without an executed check.

No legal claim without verified evidence.
```

---

# 69. ARRIVAL / DECLARATION AMENDMENT — BOUNDARIES

See [ADR-004](docs/decisions/ADR-004-arrival-declaration-source-policy.md),
[inventory](docs/DOCUMENT_INVENTORY.md) and
[field/source matrix](docs/DECLARATION_FIELD_SOURCE_MATRIX.md). Policy OP-AN-DECL v1
is an Owner operational policy, not an unverified legal rule. No production code,
canonical model, classifier, codec, database or API is changed in this docs task.

Proposed separation of responsibilities:

| Layer | Responsibility | Approval/implementation boundary |
|---|---|---|
| Intake / classification | Preserve raw documents and dimensional identity: family, exact kind, mode, master/house hierarchy, checking context; retain uncertain classification | TASK-008 B/L–AWB boundary; later TASK-016 AN; classifier extension requires separate Leader approval |
| Per-document extraction | Extract only source-grounded values and issues; keep units, weight kind and physical scope | TASK-008 existing contract; proposed ArrivalNotice is separate in TASK-016 |
| Declaration intake | Capture structured/manual values plus actor, input version and field identity; never synthesize declaration from winning source | TASK-017, structured/manual before PDF/OCR |
| Normalization | Explicit versioned catalogs, units/currency/date transformations; preserve source | TASK-009; proposed mapping/derivation evidence required |
| Document relationship | Prove shipment, master/house, split/consolidated and active-revision scope before value comparison | TASK-010; no same-number or upload-order shortcut |
| Rule engine | Versioned rule execution with applicability, coverage and exceptions | TASK-011 foundation; no source priority decided by AI confidence |
| Checks | Two lanes: A document ↔ document, B required source ↔ declaration | TASK-012; preserve discrepancy even when declaration follows required source |
| Report / correction | Separate A declaration compliance, B reconciliation, C readiness; immutable historical reports and invalidation/recheck | TASK-013/014/015; no automatic declaration mutation/transmission |

The proposed source resolver runs only after identity/scope/active/unit gates. It
uses the field registry and OP rule ID/version, returns required source/value plus
reason/evidence or an unresolved BLOCK, and preserves all losing/differing candidates.
AIR actual pieces/gross require AN without requiring a separate weigh ticket. SEA
loading-place indicator requires AN with exact field/catalog mapping. SEA totals
conflict has no automatic winning source; B/L totals require agreement with AN.
Never substitute chargeable/net for gross, infer measurement evidence, average values,
fallback to Bill when mandatory AN is unusable, or turn ETA into actual arrival.

# 70. PROPOSED CONTRACTS AND VERSION BOUNDARIES

The implemented contract is [DATA_SCHEMA Sections 1–8](docs/DATA_SCHEMA.md).
Proposed extensions are isolated in its Section 9. `ArrivalNotice` is a new separate
document contract proposal, not another interpretation of TransportDocument and not
an alias in transport configuration. It needs explicit revision/source links,
shipment/hierarchy/scope, units and weight kind, AN places with field semantics,
planned vs actual event types, operational parties and containers. No weighing time,
measurement ID or certificate may be fabricated to complete missing evidence.

Existing CanonicalField stores raw/normalized values, origin and physical provenance;
Evidence can reference extraction ID. Proposed decision evidence must join exact
document + extraction + field + page or sheet/cell (bbox where available), plus
source bytes/revision, mapping/policy versions and correction references. Do not claim
these full decision/revision structures already exist. Calculated results need a
separately approved derivation contract (inputs/formula/conversion/rounding/version),
with a non-EXTRACTED origin; no new origin enum is silently introduced by this design.

Three independent version domains:

| Domain | Current / plan | Required treatment |
|---|---|---|
| Canonical schema | Implemented `CanonicalShipment.schema_version="0.1"` | New AN/registry/decision structures need reviewed schema/compatibility design; do not assign a new version in this amendment |
| Extraction envelope | Implemented `(1, invoice)`, `(1, invoice_items)`, `(2, packing_list)`; planned `(3, transport_document)` in TASK-008D | Keep exact pairs and old payloads; **no AN envelope version reserved**; decide AN discrimination after compatibility review |
| Database schema/migration | Existing SQLite tables/DDL from accepted ADRs | Independent migration decision; `schema_version="0.1"` is not the database version; no DDL/migration in this task |

Reuse repository transaction/history engine where approved. Active extraction means
current stored attempt, not verified active business document or approved source.
Document revision selection needs evidence and authorized actor; newer upload/time/hash
alone is insufficient. Preserve all raw/extracted values, superseded history, manual
corrections, source decisions and exceptions. Persistence for new structures requires
separate technical approval; append-only history, single-active, CAS/rollback and
failed replacement behavior of ADR-001/003 must remain compatible.

# 71. REGISTRY, COVERAGE, EXCEPTIONS AND READINESS

The proposed declaration field registry in the matrix must hold ID/name/definition,
mode/context applicability, required source and forbidden overrides, comparison,
aggregation/conversion/tolerance, evidence, severity/blocking/exception behavior and
support/coverage status. Registry IDs are internal design identifiers, not asserted
official customs field codes. Unknown critical field semantics or catalog is BLOCK.

Check-result status and dossier readiness are separate. BLOCK is a proposed workflow
disposition; it is not a new implemented enum or a synonym for extraction failure.
Critical applicable fields lacking implementation, inputs or an executed current check
are NOT_CHECKED + BLOCK. Explicit supported evidence is needed for N/A applicability;
unknown applicability cannot increase readiness. A PASS in lane B never erases an
OPEN lane A conflict. High-risk unresolved conflicts block until resolved or accepted
under a named, authorized exception allowed by the policy. Exceptions retain finding,
fields/docs, differing values, reason/evidence, acceptor, time and policy version; they
cannot waive required AN, permit the wrong required value or bypass shipment identity.

Source, extraction, active revision, correction, declaration, context, mapping, rule
or policy changes invalidate affected current decisions/checks/readiness and require
recheck. Evaluate whether each exception still covers the new evidence; old exceptions
cannot silently authorize new values. Historical report remains inspectable but stale.
Freight/insurance calculations trace charge vs insured-value semantics and included
costs to prevent double counting; HS remains the declarant's decision, with description
reconciliation and no automatic historical copying or legal correctness claim.

# 72. KNOWN GAPS AND RELEASE GATES

Current classification has broad B/L/AWB categories and keyword clues, without a
separate AN/Sea Waybill/manifest kind or independent mode/hierarchy/context. An AN
containing an AWB number can therefore not be authorized merely by enum + confidence.
TASK-008D needs exact-kind content exclusion/authorization evidence and a separately
Leader-approved classifier dependency if the existing classifier cannot enforce it.
Do not silently add enum values, aliases, new schemas or broader input authorization
in TASK-008A. Negative designs cover AN with AWB number, Sea Waybill, standalone
manifest and unsupported kinds. A manifest-like table *inside an accepted B/L/AWB*
is a layout only. ROAD/RAIL/MULTIMODAL remain inventory/extension design, not TASK-008
extractor inputs. PDF geometry absence must not lead to fabricated bounding boxes.

TASK-016 contracts/compatibility → classification/extraction → service/persistence →
integration/regression precedes TASK-017 intake and TASK-009 onward (Section 61).
TASK-009–015 keep their IDs and purposes. Each technical schema/classifier/persistence
change needs its task's explicit Leader authorization after dependencies close.
Docs amendment must be independently reviewed, approved, merged and closed before
TASK-008A can start. All TASK-008 children and new planned tasks remain TODO.

# END OF ARCHITECTURE

