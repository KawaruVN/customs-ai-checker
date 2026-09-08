<img width="432" height="518" alt="image" src="https://github.com/user-attachments/assets/d9c5d697-4764-4ea6-aeb6-8c17f3e627e2" /># Customs AI Checker

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

- Python 3.12
- FastAPI
- SQLite
- Pydantic
- SQLAlchemy nếu cần
- YAML configuration
- Local file parsing
- AI provider abstraction
- Streamlit hoặc UI mỏng cho prototype nội bộ

V1 không mặc định dùng:

- microservices
- Kubernetes
- vector database
- agent swarm
- distributed queue

### Khởi chạy Application

Cài dependencies:

```bash
pip install -e ".[test]"
```

Chạy server:

```bash
uvicorn customs_ai.main:app --reload
```

Kiểm tra health endpoint:

```text
http://127.0.0.1:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok"
}
```
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
│   ├── todo/
│   ├── in_progress/
│   └── done/
└── test_documents/
```

Cấu trúc kỹ thuật chi tiết sẽ được Developer triển khai theo `ARCHITECTURE.md`.

---

## 5. Team Roles

### Project Owner

Quyết định nghiệp vụ, scope và release cuối cùng.

### ChatGPT — Project Leader / Architect

Phụ trách:

- architecture;
- specification;
- decomposition;
- task definition;
- technical decision;
- final review recommendation.

### Gemini #1 — Main Developer

Phụ trách:

- implementation;
- tests;
- documentation;
- self-review.

### Gemini #2 — Reviewer / QA

Phụ trách:

- review correctness;
- edge cases;
- false negative;
- false positive;
- security;
- cost;
- regression risk.

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

Task phải tuân theo `TASK_TEMPLATE.md`.

---

## 7. Source of Truth

Thứ tự ưu tiên:

```text
PROJECT_CONSTITUTION.md
→ MASTER_SPEC.md
→ ARCHITECTURE.md
→ DATA_SCHEMA / RULE FORMAT
→ TASK
→ IMPLEMENTATION
```

Nếu có conflict, không tự suy đoán. Báo Project Leader.

---

## 8. Security

Không commit:

- `.env`
- API keys
- passwords
- tokens
- dữ liệu khách hàng thật
- production database
- private certificates

`test_documents/` chỉ chứa dữ liệu:

- synthetic;
- anonymized;
- hoặc được phép sử dụng.

---

## 9. Current Status

Current phase:

`V1 — Foundation`

Current next task:

`TASK-001 — Project Foundation`

---

# END
