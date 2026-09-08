# TASK-001 — Project Foundation

Status: TODO  
Priority: P1  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Target Version: V1  
Dependencies: None  
Related ADR: None

---

## 1. OBJECTIVE

Dựng nền tảng code tối thiểu cho Customs AI Checker theo `PROJECT_CONSTITUTION.md`, `MASTER_SPEC.md` và `ARCHITECTURE.md`.

Sau task này, repository phải trở thành một Python project có cấu trúc rõ ràng, chạy được, test được và sẵn sàng cho các task nghiệp vụ tiếp theo.

---

## 2. BACKGROUND

Hiện repository mới có các tài liệu kiến trúc và thư mục khung.

Chưa có application foundation chính thức.

Task này chỉ tạo nền móng kỹ thuật.

Không triển khai document AI, OCR, extraction, rule engine hay business logic trong task này.

---

## 3. SCOPE

Task này PHẢI:

1. Khởi tạo Python project.
2. Tạo package `customs_ai`.
3. Tạo cấu trúc module nền tảng theo `ARCHITECTURE.md`.
4. Tạo FastAPI application tối thiểu.
5. Tạo endpoint health check.
6. Tạo configuration foundation.
7. Tạo logging foundation.
8. Tạo test framework.
9. Tạo `.gitignore`.
10. Tạo `.env.example`.
11. Tạo dependency/project configuration.
12. Đảm bảo project chạy local.
13. Viết unit/integration test tối thiểu cho foundation.

---

## 4. OUT OF SCOPE

KHÔNG triển khai:

- PDF parsing;
- Excel parsing;
- OCR;
- document classification;
- AI provider thực;
- Gemini API;
- OpenAI API;
- document extraction;
- canonical customs schema chi tiết;
- rule engine;
- HS code;
- legal checking;
- customer profile;
- production authentication;
- Docker;
- PostgreSQL;
- Streamlit UI đầy đủ.

Không gọi bất kỳ LLM/API AI nào trong TASK-001.

---

## 5. EXPECTED PROJECT STRUCTURE

Developer có thể điều chỉnh nhẹ nếu có lý do kỹ thuật hợp lý, nhưng phải giữ architecture boundaries.

Mục tiêu tối thiểu:

```text
customs-ai-checker/
│
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── config/
│   └── app.yaml
│
├── src/
│   └── customs_ai/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       └── health.py
│       ├── application/
│       │   └── __init__.py
│       ├── domain/
│       │   └── __init__.py
│       ├── ingestion/
│       │   └── __init__.py
│       ├── parsers/
│       │   └── __init__.py
│       ├── classification/
│       │   └── __init__.py
│       ├── extraction/
│       │   └── __init__.py
│       ├── normalization/
│       │   └── __init__.py
│       ├── matching/
│       │   └── __init__.py
│       ├── rules/
│       │   └── __init__.py
│       ├── checks/
│       │   └── __init__.py
│       ├── ai/
│       │   └── __init__.py
│       ├── repositories/
│       │   └── __init__.py
│       ├── reporting/
│       │   └── __init__.py
│       ├── audit/
│       │   └── __init__.py
│       └── utils/
│           └── __init__.py
│
└── tests/
    ├── unit/
    └── integration/
```

Không cần tạo file rỗng vô nghĩa nếu package structure có thể giữ bằng cách khác, nhưng import path phải rõ ràng.

---

## 6. INPUT

Không có business input.

Developer sử dụng:

- repository hiện tại;
- project documents;
- Python environment.

---

## 7. OUTPUT

Sau task này phải có:

1. Python package import được.
2. FastAPI app khởi động được.
3. Health endpoint hoạt động.
4. Configuration load được.
5. Logging hoạt động.
6. Test runner chạy được.
7. `.gitignore` hợp lệ.
8. `.env.example` không chứa secret thật.

---

## 8. FUNCTIONAL REQUIREMENTS

### FR-01 — Application startup

Phải có FastAPI application entry point.

Ví dụ:

```python
app = FastAPI(...)
```

Application phải chạy được bằng command được ghi trong README hoặc Developer completion report.

### FR-02 — Health endpoint

Tạo:

```text
GET /health
```

Expected HTTP status:

```text
200
```

Expected response tối thiểu:

```json
{
  "status": "ok"
}
```

Có thể thêm version/app name nếu hợp lý.

### FR-03 — Configuration

Tạo configuration mechanism cho non-secret settings.

Phải hỗ trợ ít nhất:

- app name;
- environment;
- log level.

Ưu tiên:

```text
config/app.yaml
+
environment variable override
```

Không hard-code config rải rác.

### FR-04 — Logging

Tạo logging configuration cơ bản.

Log startup được phép.

Không log secret.

### FR-05 — Python package

`customs_ai` phải import được trong test/runtime.

### FR-06 — Test foundation

`pytest` hoặc lựa chọn tương đương phải hoạt động.

### FR-07 — Dependency management

Dependency phải được định nghĩa tập trung trong:

```text
pyproject.toml
```

Không tạo nhiều file dependency trùng lặp nếu không có lý do.

---

## 9. NON-FUNCTIONAL REQUIREMENTS

### NFR-01

AI allowed: NO.

### NFR-02

Không thêm framework agent.

### NFR-03

Không thêm vector database.

### NFR-04

Không thêm Redis, Celery, Kafka hoặc queue system.

### NFR-05

Không thêm Docker nếu không thực sự cần cho task.

### NFR-06

Code phải đơn giản và dễ hiểu.

### NFR-07

Business logic không được đặt trong FastAPI route.

### NFR-08

Không có dependency vendor AI trong task này nếu chưa cần.

### NFR-09

Không commit generated cache/build artifacts.

---

## 10. BUSINESS RULES

None.

TASK-001 không triển khai nghiệp vụ hải quan.

---

## 11. DATA MODEL IMPACT

Không tạo canonical customs schema hoàn chỉnh.

Có thể tạo model/config tối thiểu phục vụ app startup nếu cần.

Không được tự thiết kế sâu:

- Invoice;
- PackingList;
- CustomsDeclaration;
- Rule;
- CheckResult.

Các entity đó thuộc task sau.

---

## 12. CONSTRAINTS

Developer phải đọc trước:

```text
PROJECT_CONSTITUTION.md
MASTER_SPEC.md
ARCHITECTURE.md
TASK_TEMPLATE.md
```

Developer không được:

- thay đổi các file trên nếu task không yêu cầu;
- thay architecture;
- thêm dependency lớn vô lý;
- tạo secret;
- implement feature ngoài scope.

Nếu phát hiện conflict giữa các tài liệu:

dừng phần bị conflict và báo Project Leader.

---

## 13. EDGE CASES

Phải xem xét tối thiểu:

- thiếu `config/app.yaml`;
- environment variable override;
- invalid log level;
- import package trong test;
- app startup trong môi trường development;
- config không chứa secret thật.

Không cần xử lý file upload trong task này.

---

## 14. ACCEPTANCE CRITERIA

### AC-01

Given repository sau implementation  
When cài dependencies theo hướng dẫn  
Then application khởi động thành công.

### AC-02

Given application đang chạy  
When gọi:

```text
GET /health
```

Then trả HTTP 200.

### AC-03

Health response có:

```json
{
  "status": "ok"
}
```

hoặc response tương đương được document rõ.

### AC-04

`pytest` chạy thành công.

### AC-05

Có ít nhất một integration test xác minh health endpoint.

### AC-06

Có test hoặc validation cho configuration loading.

### AC-07

Không có API key/password/token thật trong repository.

### AC-08

`.gitignore` bỏ qua tối thiểu:

```text
.env
.venv/
__pycache__/
.pytest_cache/
*.pyc
data/uploads/
data/cache/
*.db
```

Có thể điều chỉnh để không ignore file database fixture cần test.

### AC-09

`.env.example` chỉ chứa placeholder.

Ví dụ:

```text
APP_ENV=development
LOG_LEVEL=INFO
```

Không có credential thật.

### AC-10

Developer không triển khai functionality ngoài phạm vi task một cách đáng kể.

---

## 15. TEST REQUIREMENTS

### Unit Tests

Tối thiểu:

- configuration load;
- configuration defaults/override nếu được implement;
- health response model nếu có.

### Integration Tests

Tối thiểu:

- FastAPI app startup;
- `GET /health` trả HTTP 200.

### Failure Tests

Nếu config có validation:

- invalid configuration phải fail rõ ràng.

### Regression Tests

Chưa yêu cầu Golden Dataset trong TASK-001.

---

## 16. TEST DATA

Chỉ dùng synthetic test data.

Không cần document thực.

---

## 17. OBSERVABILITY REQUIREMENTS

Application startup nên log tối thiểu:

- app name;
- environment;
- startup success.

Không log:

- environment secrets;
- toàn bộ environment variables.

---

## 18. COST REQUIREMENTS

```text
AI allowed: NO
External paid API allowed: NO
```

TASK-001 phải chạy với chi phí vận hành AI bằng 0.

---

## 19. SECURITY / PRIVACY REQUIREMENTS

Phải có `.gitignore`.

Không commit:

- `.env`;
- secret;
- local production database;
- customer files.

`.env.example` chỉ chứa tên biến + placeholder an toàn.

---

## 20. DEPENDENCIES

Depends on:

```text
None
```

Nhưng phải tuân thủ:

```text
PROJECT_CONSTITUTION.md
MASTER_SPEC.md
ARCHITECTURE.md
```

---

## 21. DELIVERABLES

Gemini #1 phải cung cấp:

1. Source code.
2. `pyproject.toml`.
3. `.gitignore`.
4. `.env.example`.
5. configuration file(s).
6. tests.
7. hướng dẫn chạy ngắn.
8. Developer Completion Report.

---

## 22. DEFINITION OF DONE

- [ ] Python project đã khởi tạo.
- [ ] `customs_ai` import được.
- [ ] FastAPI app chạy được.
- [ ] `/health` trả HTTP 200.
- [ ] Configuration foundation hoạt động.
- [ ] Logging foundation hoạt động.
- [ ] Tests pass.
- [ ] Không gọi AI.
- [ ] Không thêm dependency lớn ngoài scope.
- [ ] Không có secrets.
- [ ] Reviewer Gemini #2 APPROVE.
- [ ] Project Leader đồng ý đóng task.

---

## 23. DEVELOPER NOTES

Gemini #1 cập nhật tại đây nếu cần.

---

## 24. REVIEW NOTES

Gemini #2 cập nhật tại đây khi review.

---

## 25. PROJECT LEADER DECISION

Pending.

---

# END OF TASK-001
