# Customs AI Checker

Customs AI Checker là dự án xây dựng hệ thống hỗ trợ kiểm tra chứng từ và dữ liệu khai báo hải quan Việt Nam bằng kết hợp giữa:

- deterministic code;
- document parsing;
- AI extraction / reasoning khi cần;
- rule engine;
- master data;
- human review.

Mục tiêu của dự án là tạo một công cụ có thể dùng thực tế, có khả năng truy vết nguồn dữ liệu, kiểm tra nhất quán giữa nhiều chứng từ và giữ chi phí AI ở mức thấp.

---

## 1. Core Principles

Dự án tuân theo các nguyên tắc:

- AI xử lý ambiguity.
- Code xử lý certainty.
- Không hard-code layout của từng khách hàng.
- Không coi output AI là nguồn pháp lý.
- Không tạo PASS nếu phép check chưa thực sự chạy.
- Mọi ERROR/WARNING quan trọng phải có evidence.
- Giữ raw data và provenance.
- Ưu tiên local processing trước AI API.
- Model AI phải có thể thay thế.
- V1 là decision-support system, không phải hệ thống tự động khai VNACCS.

Chi tiết xem:

- `PROJECT_CONSTITUTION.md`
- `MASTER_SPEC.md`
- `ARCHITECTURE.md`

---

## 2. V1 Scope

V1 tập trung vào:

1. Tạo Shipment.
2. Upload chứng từ.
3. Nhận diện loại chứng từ.
4. Extract dữ liệu.
5. Normalize dữ liệu.
6. Match item giữa các chứng từ.
7. Chạy cross-document checks.
8. Trả PASS / ERROR / WARNING / MISSING / NEEDS_REVIEW.
9. Hiển thị evidence.
10. Cho phép human correction và recheck.

Ưu tiên chứng từ:

- Commercial Invoice
- Packing List
- Bill of Lading / AWB
- Customs Declaration / declaration data

---

## 3. V1 Technology Baseline

- Python 3.12+
- FastAPI
- SQLite
- Pydantic
- YAML configuration
- Local file parsing
- AI provider abstraction
- Streamlit hoặc UI mỏng cho prototype nội bộ

### Khởi chạy application

Cài dependencies:

```bash
pip install -e ".[test]"
```

Chạy server:

```bash
uvicorn customs_ai.main:app --reload
```

Health endpoint:

```text
GET http://127.0.0.1:8000/health
```

### Ingestion API

Upload chứng từ:

```text
POST /shipments/{shipment_id}/documents
Content-Type: multipart/form-data
```

V1 hỗ trợ `.pdf`, `.xls`, `.xlsx`, `.csv`, `.docx`, `.jpg`, `.jpeg`, `.png`. Giới hạn mặc định là 50 MiB và có thể cấu hình bằng `MAX_UPLOAD_SIZE_MB`.

Trong TASK-003, file được stream xuống temporary storage, kiểm tra size, tính SHA-256, kiểm tra loại nội dung/MIME và duplicate theo từng Shipment, sau đó lưu metadata vào SQLite. Runtime paths mặc định là `data/uploads` và `data/app.db`; các path tương đối luôn được resolve theo project root, không theo current working directory.

TASK-003 chỉ thực hiện ingestion. Chưa chạy OCR, parser nội dung, document classification hay AI extraction.

---

## 4. Repository Structure

```text
customs-ai-checker/
│
├── README.md
├── PROJECT_CONSTITUTION.md
├── MASTER_SPEC.md
├── ARCHITECTURE.md
├── TASK_TEMPLATE.md
│
├── docs/
├── reviews/
├── rules/
├── src/
├── tasks/
└── test_documents/
```

Cấu trúc kỹ thuật chi tiết xem `ARCHITECTURE.md`.

---

## 5. Team Roles

### Project Owner

Quyết định nghiệp vụ, scope và release cuối cùng.

### ChatGPT — Project Leader / Architect

Phụ trách kiến trúc, spec và duyệt kỹ thuật.

### Gemini #1 — Main Developer

Phụ trách implementation, tests, documentation.

### Gemini #2 — Reviewer / QA

Phụ trách review edge cases, security, cost.

---

## 6. Development Workflow

```text
Project Leader writes Task
        ↓
tasks/todo/
        ↓
Gemini #1 implements
        ↓
tasks/in_progress/
        ↓
Gemini #2 reviews
        ↓
APPROVE or REQUEST CHANGES
        ↓
Project Leader final decision
        ↓
tasks/done/
```

---

## 7. Security

Không commit:

- `.env`
- API keys, passwords, tokens
- dữ liệu khách hàng thật
- production database (`app.db`)
- files lưu trữ nội bộ (`data/uploads`)

`test_documents/` chỉ chứa dữ liệu synthetic, anonymized hoặc được phép sử dụng.

---

## 8. Current Status

Current phase: `V1 — Foundation`

Current task: `TASK-003 — File Ingestion + Hashing`

## Local parser layer

TASK-004 adds deterministic local parsing for persisted PDF, XLSX, and legacy XLS files.

- PDF uses `pypdf`, preserves page boundaries, and flags documents with no locally extractable text as `needs_ocr=true`; OCR is not performed in this task.
- XLSX uses `openpyxl` and preserves populated-cell coordinates, formulas, number formats, merged ranges, sheet state, and hidden row/column metadata.
- XLS uses `xlrd` and preserves sheet/cell provenance plus available merged/hidden metadata.
- Parsing starts from a persisted `SourceDocument`; stored paths are resolved and constrained to the configured upload root.
- Parsers never classify document business type, execute formulas/macros, call AI/network services, or modify uploaded source files.
