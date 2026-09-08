# TASK_TEMPLATE.md

# Customs AI Checker — Task Template

Version: 0.1  
Status: Active  
Purpose: Mẫu chuẩn để tạo và giao task trong dự án Customs AI Checker.

---

# 1. TASK HEADER

```text
Task ID:
Title:
Status:
Priority:
Owner:
Reviewer:
Created:
Updated:
Target Version:
Dependencies:
Related ADR:
```

Giá trị `Status` hợp lệ:

```text
TODO
IN_PROGRESS
REVIEW
CHANGES_REQUESTED
APPROVED
DONE
BLOCKED
```

Giá trị `Priority` đề xuất:

```text
P0 — Critical
P1 — High
P2 — Normal
P3 — Low
```

---

# 2. OBJECTIVE

Mô tả ngắn gọn task này phải đạt được điều gì.

Yêu cầu:

- viết theo kết quả cần đạt;
- không viết mơ hồ;
- không mô tả giải pháp kỹ thuật nếu chưa cần;
- đủ rõ để Developer biết khi nào task hoàn thành.

Ví dụ:

> Xây module tiếp nhận file upload, kiểm tra loại file, tính SHA-256 và lưu `SourceDocument` vào database.

---

# 3. BACKGROUND

Giải thích ngắn tại sao task này cần tồn tại.

Có thể nêu:

- vấn đề hiện tại;
- task trước đó liên quan;
- requirement từ `MASTER_SPEC.md`;
- giới hạn từ `PROJECT_CONSTITUTION.md`;
- quyết định kỹ thuật từ `ARCHITECTURE.md`.

Không lặp lại toàn bộ tài liệu gốc.

---

# 4. SCOPE

Những việc task này PHẢI làm.

Ví dụ:

- nhận file từ API;
- validate extension và MIME;
- tính SHA-256;
- detect duplicate;
- lưu metadata;
- trả `document_id`.

---

# 5. OUT OF SCOPE

Những việc KHÔNG làm trong task này.

Ví dụ:

- OCR;
- document classification;
- AI extraction;
- UI;
- rule engine.

Mục này rất quan trọng để tránh Developer mở rộng phạm vi không kiểm soát.

---

# 6. INPUT

Liệt kê input của task.

Ví dụ:

```text
File binary
Shipment ID
Original filename
MIME type
```

Nếu có schema, ghi rõ.

Ví dụ:

```json
{
  "shipment_id": "SHP-2026-000001",
  "filename": "invoice.pdf"
}
```

---

# 7. OUTPUT

Liệt kê output mong muốn.

Ví dụ:

```json
{
  "document_id": "DOC-000001",
  "shipment_id": "SHP-2026-000001",
  "status": "UPLOADED",
  "sha256": "..."
}
```

Nếu output là file, database record hoặc side effect, phải ghi rõ.

---

# 8. FUNCTIONAL REQUIREMENTS

Liệt kê requirement chức năng.

Mỗi requirement nên có ID.

Ví dụ:

```text
FR-01: Hệ thống phải tính SHA-256 cho mỗi file upload.

FR-02: Nếu cùng SHA-256 đã tồn tại trong cùng Shipment, hệ thống phải phát hiện duplicate.

FR-03: Tên file người dùng không được dùng làm primary identifier.

FR-04: File không hợp lệ phải bị từ chối với error code rõ ràng.
```

---

# 9. NON-FUNCTIONAL REQUIREMENTS

Có thể gồm:

```text
NFR-01: Không gọi LLM trong task này.

NFR-02: Không log file content.

NFR-03: Code phải chạy trên Python version được quy định trong ARCHITECTURE.md.

NFR-04: Không hard-code secret.

NFR-05: Module phải có unit test.
```

---

# 10. BUSINESS RULES

Nếu task có nghiệp vụ, liệt kê rule liên quan.

Mỗi rule cần ghi:

```text
Rule ID:
Rule Type:
Applies To:
Condition:
Expected Result:
Source:
Version:
```

Không tạo legal rule nếu chưa có nguồn được xác minh.

Nếu task không có business rule:

```text
None
```

---

# 11. DATA MODEL IMPACT

Ghi rõ task có tạo hoặc sửa entity/schema nào không.

Ví dụ:

```text
Creates:
- SourceDocument

Modifies:
- Shipment.processing_status

No schema-breaking changes.
```

Nếu thay đổi canonical schema lớn, phải xem xét ADR.

---

# 12. FILES / MODULES EXPECTED

Liệt kê khu vực dự kiến bị ảnh hưởng.

Ví dụ:

```text
src/customs_ai/ingestion/
src/customs_ai/repositories/
src/customs_ai/domain/
tests/unit/
tests/integration/
```

Đây là định hướng, không phải yêu cầu Developer phải tạo đúng mọi file nếu implementation hợp lý hơn.

---

# 13. CONSTRAINTS

Các giới hạn bắt buộc.

Ví dụ:

- tuân thủ `PROJECT_CONSTITUTION.md`;
- không thay đổi architecture ngoài scope;
- không thêm dependency lớn nếu chưa được duyệt;
- không dùng AI nếu deterministic code đủ;
- không commit dữ liệu khách hàng thật;
- không đổi canonical schema nếu task không cho phép;
- không tạo API key hoặc secret trong source.

---

# 14. EDGE CASES

Liệt kê các trường hợp phải xem xét.

Ví dụ:

```text
- file rỗng;
- file bị hỏng;
- extension giả;
- MIME không khớp extension;
- tên file Unicode;
- tên file rất dài;
- upload cùng file 2 lần;
- file lớn hơn limit;
- encrypted PDF;
- duplicate ở Shipment khác.
```

Không chỉ test happy path.

---

# 15. ACCEPTANCE CRITERIA

Mỗi tiêu chí phải kiểm chứng được.

Ví dụ:

```text
AC-01:
Given một file PDF hợp lệ
When upload vào Shipment
Then hệ thống tạo SourceDocument và trả document_id.

AC-02:
Given cùng một file đã tồn tại trong Shipment
When upload lại
Then hệ thống phát hiện duplicate và không xử lý lại file như tài liệu mới.

AC-03:
Given file vượt quá size limit
When upload
Then request bị từ chối với error code FILE_TOO_LARGE.

AC-04:
All automated tests pass.
```

Không dùng tiêu chí mơ hồ như:

> "Hoạt động tốt."

---

# 16. TEST REQUIREMENTS

Developer phải triển khai các test cần thiết.

## Unit Tests

```text
- ...
```

## Integration Tests

```text
- ...
```

## Failure Tests

```text
- ...
```

## Regression Tests

```text
- ...
```

Nếu loại test nào không cần, ghi rõ:

```text
Not required for this task.
```

---

# 17. TEST DATA

Ghi rõ dữ liệu test được phép sử dụng.

Ưu tiên:

- synthetic;
- anonymized;
- fixtures trong repo.

Không dùng production documents chưa anonymize.

---

# 18. OBSERVABILITY REQUIREMENTS

Nếu task tạo operation quan trọng, quy định log/audit cần có.

Ví dụ:

```text
Log:
- shipment_id
- document_id
- processing status
- error code

Do not log:
- document full text
- credentials
- API keys
```

---

# 19. COST REQUIREMENTS

Nếu task sử dụng AI, ghi rõ:

```text
AI allowed: YES / NO

Allowed task types:
- ...

Preferred model tier:
- cheap / standard / strong

Caching required:
- YES / NO

Fallback:
- ...
```

Nếu không cần AI:

```text
AI allowed: NO
```

---

# 20. SECURITY / PRIVACY REQUIREMENTS

Liệt kê yêu cầu riêng nếu có.

Ví dụ:

- sanitize filename;
- không execute macro;
- không public upload folder;
- không log file content;
- `.env` không commit;
- validate MIME;
- giới hạn dung lượng file.

---

# 21. DEPENDENCIES

Liệt kê task/phần khác cần có trước.

Ví dụ:

```text
TASK-001 depends on: None

TASK-006 depends on:
- TASK-002 Canonical Data Schema
- TASK-004 Local Parsers
- TASK-005 Document Classification
```

Nếu dependency chưa hoàn thành và task không thể làm an toàn:

đánh dấu `BLOCKED`.

---

# 22. DELIVERABLES

Developer phải trả:

```text
- source code;
- tests;
- migration nếu có;
- documentation nếu hành vi thay đổi;
- completion report;
- known limitations.
```

Không đánh dấu task xong chỉ vì code đã được viết.

---

# 23. DEFINITION OF DONE

Task chỉ được coi là hoàn thành khi:

1. Scope đã implement.
2. Acceptance Criteria đạt.
3. Tests pass.
4. Không còn CRITICAL issue.
5. Reviewer đã `APPROVE`, hoặc Project Leader override có lý do.
6. Không chứa secret.
7. Documentation liên quan đã cập nhật.
8. Không phá regression hiện có.
9. Known limitations đã được ghi nhận.
10. Task được chuyển đúng lifecycle.

---

# 24. DEVELOPER COMPLETION REPORT

Gemini #1 / Main Developer phải trả theo format:

```text
TASK COMPLETED:
[Task ID + Title]

IMPLEMENTATION SUMMARY:
[...]

FILES CREATED:
[...]

FILES MODIFIED:
[...]

TESTS ADDED:
[...]

TEST RESULT:
[...]

DEPENDENCIES ADDED:
[...]

ARCHITECTURE DEVIATIONS:
None / [...]

KNOWN LIMITATIONS:
[...]

RISKS:
[...]

QUESTIONS FOR PROJECT LEADER:
None / [...]

READY FOR REVIEW:
YES / NO
```

Nếu có `ARCHITECTURE DEVIATIONS`, Developer không được tự coi chúng đã được duyệt.

---

# 25. REVIEWER REPORT

Gemini #2 / Reviewer phải trả theo format:

```text
REVIEW RESULT:
PASS / PASS WITH ISSUES / FAIL

TASK:
[...]

CRITICAL:
[...]

HIGH:
[...]

MEDIUM:
[...]

LOW:
[...]

FALSE NEGATIVE RISKS:
[...]

FALSE POSITIVE RISKS:
[...]

SECURITY / PRIVACY:
[...]

COST ISSUES:
[...]

TESTS MISSING:
[...]

REQUIRED CHANGES:
[...]

OPTIONAL IMPROVEMENTS:
[...]

ACCEPTANCE DECISION:
APPROVE / REQUEST CHANGES / REJECT
```

Không dùng câu mơ hồ như:

> Looks good.

---

# 26. CHANGE REQUEST CYCLE

Nếu Reviewer trả:

`REQUEST CHANGES`

thì task quay lại:

```text
CHANGES_REQUESTED
→ IN_PROGRESS
→ REVIEW
```

Developer phải xử lý từng required change hoặc giải thích vì sao không áp dụng.

Reviewer review lại.

Không tạo task mới chỉ để sửa lỗi thuộc acceptance criteria của task hiện tại.

---

# 27. PROJECT LEADER DECISION

Project Leader có thể:

```text
APPROVE
REQUEST CHANGES
REJECT
BLOCK
OVERRIDE REVIEW
```

Nếu override Reviewer ở issue quan trọng, phải ghi lý do.

Nếu thay đổi architecture lớn:

tạo ADR.

---

# 28. TASK FILE LOCATION

Khi tạo task:

```text
tasks/todo/TASK-XXX-short-name.md
```

Khi bắt đầu:

```text
tasks/in_progress/TASK-XXX-short-name.md
```

Khi hoàn thành:

```text
tasks/done/TASK-XXX-short-name.md
```

Git history là nguồn theo dõi thay đổi chính.

---

# 29. TASK NAMING

Format:

```text
TASK-001-project-foundation.md
TASK-002-canonical-data-schema.md
TASK-003-file-ingestion.md
```

Tên:

- ngắn;
- có ý nghĩa;
- lowercase;
- dùng dấu `-`;
- không dùng tên kiểu `final`, `new`, `fix2`.

---

# 30. COMMIT MESSAGE

Commit nên liên kết tới Task ID.

Ví dụ:

```text
TASK-003: implement file hashing
TASK-003: add duplicate detection tests
TASK-003: handle corrupted upload
```

Bug riêng:

```text
BUG-004: fix invoice decimal normalization
```

---

# 31. READY-TO-USE TASK SKELETON

Copy phần dưới đây khi tạo một task mới.

```md
# TASK-XXX — [TITLE]

Status: TODO  
Priority: P2  
Owner: Gemini #1 — Main Developer  
Reviewer: Gemini #2 — Reviewer / QA  
Created: YYYY-MM-DD  
Updated: YYYY-MM-DD  
Target Version: V1  
Dependencies: None  
Related ADR: None

---

## 1. OBJECTIVE

[Task này phải đạt được điều gì?]

---

## 2. BACKGROUND

[Tại sao task này cần tồn tại?]

---

## 3. SCOPE

- [...]
- [...]

---

## 4. OUT OF SCOPE

- [...]
- [...]

---

## 5. INPUT

```text
[Input]
```

---

## 6. OUTPUT

```text
[Output]
```

---

## 7. FUNCTIONAL REQUIREMENTS

- FR-01: [...]
- FR-02: [...]
- FR-03: [...]

---

## 8. NON-FUNCTIONAL REQUIREMENTS

- NFR-01: [...]
- NFR-02: [...]

---

## 9. BUSINESS RULES

None / [...]

---

## 10. DATA MODEL IMPACT

[...]

---

## 11. FILES / MODULES EXPECTED

```text
[...]
```

---

## 12. CONSTRAINTS

- [...]
- [...]

---

## 13. EDGE CASES

- [...]
- [...]
- [...]

---

## 14. ACCEPTANCE CRITERIA

- AC-01: [...]
- AC-02: [...]
- AC-03: [...]

---

## 15. TEST REQUIREMENTS

### Unit Tests

- [...]

### Integration Tests

- [...]

### Failure Tests

- [...]

### Regression Tests

- [...]

---

## 16. TEST DATA

[...]

---

## 17. OBSERVABILITY REQUIREMENTS

[...]

---

## 18. COST REQUIREMENTS

AI allowed: YES / NO

[...]

---

## 19. SECURITY / PRIVACY REQUIREMENTS

- [...]
- [...]

---

## 20. DEPENDENCIES

[...]

---

## 21. DELIVERABLES

- source code
- tests
- documentation if required
- developer completion report

---

## 22. DEFINITION OF DONE

- [ ] Scope implemented
- [ ] Acceptance Criteria passed
- [ ] Tests passed
- [ ] No unresolved CRITICAL issues
- [ ] Reviewer approved
- [ ] Documentation updated if required
- [ ] No secrets committed
- [ ] Ready to move to `tasks/done/`

---

## 23. DEVELOPER NOTES

[Gemini #1 cập nhật khi cần.]

---

## 24. REVIEW NOTES

[Gemini #2 cập nhật khi review.]

---

## 25. PROJECT LEADER DECISION

Pending.
```

---

# 32. FINAL RULE

Một Task tốt phải giúp Developer trả lời được 4 câu hỏi trước khi code:

1. Tôi đang xây cái gì?
2. Tôi không được xây cái gì?
3. Làm thế nào biết tôi đã hoàn thành?
4. Reviewer sẽ kiểm tôi dựa trên tiêu chí nào?

Nếu 4 câu hỏi trên chưa rõ, Task chưa sẵn sàng để đưa vào `IN_PROGRESS`.

---

# END OF TASK TEMPLATE

