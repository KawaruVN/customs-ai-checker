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

### Antigravity — Main Developer

Phụ trách implementation, tests, documentation (mặc định).

### Codex — Technical Reviewer / QA

Phụ trách review edge cases, security, cost (mặc định).

> [!NOTE]
> **Thử nghiệm hoán đổi vai trò cho TASK-006C:** Để đánh giá chéo hiệu quả phát triển và kiểm thử độc lập, Codex sẽ đảm nhiệm vai trò Main Developer (phụ trách implementation và unit tests), và Antigravity đảm nhiệm vai trò Technical Reviewer / QA (phụ trách review độc lập, audit probes và verification).

---

## 6. Development Workflow

```text
Project Leader writes Task
        ↓
tasks/todo/
        ↓
Main Developer implements
        ↓
tasks/in_progress/
        ↓
Technical Reviewer reviews
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

Current phase: `TASK-007 — Packing List Extraction` (Phase: `V1 — Document Understanding` — DONE)

Current task: `TASK-007 — Packing List Extraction (EPIC)` (DONE — Nghiệm thu và đóng Epic; PR #7–#11 merged; 1422 passed, 2 warnings)

Authoritative baseline: 1422 passed, 0 failed, 0 skipped, 2 warnings (Python 3.13.14, pytest 9.1.1).

> [!NOTE]
> **Phạm vi hoàn thành V1 của TASK-007:**
> Trích xuất bảng hàng hóa từ PDF (`PDF_PACKING_ITEMS_UNSUPPORTED`), đối soát chéo chứng từ (cross-document matching), chuẩn hóa dữ liệu nâng cao (normalization), và các quy tắc nghiệp vụ hải quan/thuế (customs/HS/VAT rules) nằm ngoài phạm vi hoàn thành của Epic TASK-007 và được hoãn lại cho các giai đoạn tiếp theo.

Recently completed:
- `TASK-007 — Packing List Extraction (EPIC)` (DONE — Hoàn thành toàn diện Epic qua PR #7–#11, merge commit cuối `6d60351`)
  - Hoàn thành đầy đủ 5 nhiệm vụ thành phần: TASK-007A (Foundation/Contracts), TASK-007B (Deterministic Headers), TASK-007C (Deterministic Excel Items), TASK-007D (Service & Persistence Envelope v2), TASK-007E (Integration & Regression).
  - Đảm bảo 100% tính tương thích ngược với luồng trích xuất Commercial Invoice v1; bảo vệ tính bất biến của source file và lưu trữ an toàn với SQLite schema v0.1.
  - Bộ kiểm thử toàn hệ thống: 1422 passed, 2 warnings; 49/50 independent adversarial QA probes passed (1 variant NOT RUN do giới hạn quyền Windows symlink, thay thế bằng NTFS junction PASS).
- `TASK-007E — Packing List Integration & Regression` (DONE — Merged via PR #11, commit `6d60351`)
  - Tích hợp toàn diện pipeline trích xuất Packing List production từ byte upload qua `IngestionService`, phân loại `build_classification_service`, phân giải trực quan, bóc tách deterministic headers/items, lưu trữ qua codec envelope v2 vào SQLite, đến truy xuất lại từ `DocumentExtractionRepository`.
  - Kiểm thử tích hợp PDF native 1 và 2 trang: trích xuất chính xác 16 header canonical, bảo toàn số trang vật lý, bỏ qua hoàn toàn OCR khi text layer sạch; tuân thủ nghiêm ngặt giới hạn V1 chưa hỗ trợ bảng hàng trong PDF (`PDF_PACKING_ITEMS_UNSUPPORTED`, `items=[]`, `NEEDS_REVIEW`).
  - Kiểm thử tích hợp bảng tính Excel XLSX và XLS: nhận diện bảng hàng dịch chuyển tọa độ (shifted offsets), nhiều sheet, dữ liệu đa ngữ (EN, VI, ZH); bảo vệ toàn diện trước ô ẩn, ô công thức (giữ biểu thức trong candidate, không tin cậy giá trị cache), ô gộp và các bảng cạnh tranh (`MULTIPLE_PACKING_TABLES`).
  - Cổng an toàn phân loại: nội dung chứng từ áp đảo tên file đánh lừa; từ chối dứt khoát tài liệu sai hoặc chưa phân loại; sửa lỗi hợp đồng danh tính phân loại (E-01) và revalidation confidence NaN (E-02).
  - Cổng an toàn trực quan: giữ tính review dính (`requires_review=True`) cho các trang scan/chất lượng kém; từ chối hoặc review bảo thủ khi metadata trực quan xung đột/bị sửa đổi.
  - Phân định rõ ràng ngữ cảnh tài liệu và ngữ cảnh dòng hàng: tách biệt rạch ròi tổng số kiện, trọng lượng cả bì/tịnh của chứng từ với số lượng và trọng lượng dòng hàng.
  - Chu trình lưu trữ và tương thích ngược Invoice v1: kiểm chứng round-trip envelope v2 `(2, "packing_list")`; đồng tồn tại an toàn với bản ghi Invoice v1 trong cùng database mà không ghi đè hay biến đổi; đảm bảo duy nhất 1 bản ghi active qua partial index `one_active_extraction_per_document`; rollback toàn vẹn khi gặp trigger abort.
  - Bất biến nguồn và bảo mật: hash SHA-256 của file tải lên không đổi trước và sau trích xuất; chặn đứng path traversal và directory link escape qua `resolve_source_path`; không rò rỉ dữ liệu nhạy cảm của khách hàng trong log.
  - Bộ kiểm thử: 95 test cases integration mới (26 native/excel, 28 visual safety, 15 cross-module, 17 persistence history, 9 source security), 1422 tests full-suite passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 49/50 independent adversarial scenarios passed, 1 variant NOT RUN (symlink native do đặc quyền Windows, thay thế bằng NTFS junction passed 100%).
- `TASK-007D — Packing List Service & Persistence` (DONE — Merged via PR #10, commit `f52ef03`)
  - Xây dựng tầng application orchestration (`PackingExtractionService`, `build_packing_extraction_service`) kết hợp deterministic headers (TASK-007B) và Excel item tables (TASK-007C) từ `SourceDocument` ID có căn cứ.
  - Cổng phân loại kép (classification gate): chỉ xử lý tài liệu được phân loại an toàn là `PACKING_LIST` với confidence >= 0.50; từ chối dứt khoát tài liệu sai nội dung (Invoice mang tên Packing List) mà không ghi nhận attempt hay làm thay đổi metadata.
  - Phân tầng an toàn trực quan PDF: PDF native sạch bỏ qua hoàn toàn OCR; tài liệu ảnh/scan yêu cầu kiểm tra toàn diện chất lượng và phân giải; tuân thủ chính sách V1 chưa hỗ trợ bảng hàng hóa trong PDF (`PDF_PACKING_ITEMS_UNSUPPORTED`, `items=[]`, `NEEDS_REVIEW`), tuyệt đối không bịa đặt số liệu.
  - Tách biệt ngữ cảnh dòng hàng trong Excel: cách ly các dòng hàng hóa hợp lệ để nhãn cột trọng lượng trong bảng không bị nhận diện nhầm thành header chứng từ; bảo toàn đầy đủ provenance (sheet, cell, bounding box) và prefix `header.`/`items.` cho candidates.
  - Mở rộng persistence codec có phân biệt (discriminated persistence envelope v2): hỗ trợ đồng thời v1 Invoice (`(1, invoice)`, `(1, invoice_items)`) và v2 Packing List (`(2, packing_list)`) mà không thay đổi DDL/schema SQLite (`schema_version = "0.1"` giữ nguyên).
  - Bảo toàn toàn vẹn kiểu dữ liệu và độ chính xác: Decimal scale (`0.00`, 20 chữ số nguyên), ngày tháng (`datetime.date`), danh sách đa tham chiếu hóa đơn, và văn bản Unicode đa ngữ (Tiếng Việt, Tiếng Trung) qua round-trip SQLite thực tế; xác thực snapshot wire JSON khắt khe ngăn chặn ép kiểu ngầm.
  - Chu trình giao dịch SQLite an toàn: cơ chế khóa ghi `BEGIN IMMEDIATE`; đảm bảo duy nhất 1 bản ghi active qua partial index; lịch sử attempt đơn điệu tăng dần; bảo vệ tối thượng cho bản ghi active khi gặp attempt `FAILED` (không deactive dữ liệu hợp lệ trước đó); rollback toàn diện khi trigger/commit thất bại.
  - Bộ kiểm thử: 149 test cases mới (74 service, 75 persistence), 1327 tests full-suite passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 50/50 independent adversarial probes passed.
- `TASK-007C — Deterministic Packing Item Tables` (DONE — Merged via PR #9, commit `bde5e61`)
  - Trích xuất bảng hàng hóa (item tables) của Packing List từ file Excel (XLSX, XLS) dựa trên canonical `PackingItem` và 7 trường canonical đã phê duyệt trong `config/packing_extraction.yaml`.
  - Cơ chế nhận diện bảng 2 tầng chặt chẽ: yêu cầu đồng thời cột định danh (item_code/description) và cột số lượng/trọng lượng; chỉ công nhận bảng hợp lệ khi có ít nhất một dòng dữ liệu thực tế chứa cả định danh và số liệu an toàn trên cùng một hàng.
  - Phân định rõ ràng giữa tổng chứng từ (document totals) và số liệu từng dòng hàng; bảo toàn nguyên vẹn mã kiện (package_number), số lượng (quantity), trọng lượng cả bì/tịnh (gross/net weight).
  - Tự động dừng tại các biên phân cách (TOTAL, GRAND TOTAL, SUBTOTAL, NOTES, REMARKS, GHI CHÚ, 备注) mà không loại bỏ các mô tả hàng hóa hợp lệ chứa từ khóa tổng (TOTALIZER FLOW SENSOR).
  - Phòng thủ toàn diện trước ô ẩn, ô công thức, và ô gộp (merged cells); bảo vệ nguyên vẹn tính chính xác của Decimal và chuỗi ký tự có số 0 ở đầu.
  - Xử lý xung đột đa bảng bảo thủ: tự động từ chối và yêu cầu review (`MULTIPLE_PACKING_TABLES`, `items=[]`) khi xuất hiện nhiều bảng khả tín cạnh tranh, tuyệt đối không dùng đa số phiếu hay gộp ngầm.
  - Bộ kiểm thử: 216 test cases mới (69 tables, 109 safety, 25 adversarial, 13 integration), 1178 tests full-suite passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 40/40 independent adversarial probes passed.
- `TASK-007B — Deterministic Packing List Headers` (DONE — Merged via PR #8, commit `3e7e1d8`)
  - Trích xuất deterministic header của Packing List từ PDF và Excel dựa trên canonical `PackingList` và 16 canonical paths đã phê duyệt trong `config/packing_extraction.yaml`.
  - Phân định vai trò nghiêm ngặt giữa commercial parties (`seller`, `buyer`) và logistics roles (`SHIPPER`, `CONSIGNEE`, `NOTIFY PARTY` được đưa vào `_NON_HEADER_LABELS` để làm biên chắn bảo vệ dỿ liệu).
  - Trích xuất danh sách tham chiếu hóa đơn (`invoice_references`) dạng list `CanonicalField[str]`, giữ nguyên từng token độc lập, không gộp mất mát hay suy diễn khoảng giá trị.
  - Sửa lỗi parser openpyxl grouped hidden columns trong `src/customs_ai/parsers/excel.py` (mở rộng `min..max` chính xác sang từng ký tự cột), bảo vệ an toàn cho cả pipeline Packing List và Commercial Invoice.
  - Chính sách visual safety và layout safety nghiêm ngặt: toàn bộ PDF abstains nếu có trang visual không an toàn; các ô công thức/ẩn/merged trong Excel được xử lý bảo thủ.
  - Bộ kiểm thử: 265 test cases mới (112 PDF, 91 workbook, 54 adversarial, 8 parser), 962 tests full-suite passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 34/34 independent adversarial probes passed.
- `TASK-007A — Packing List Extraction Foundation & Contracts` (DONE — Merged via PR #7, commit `57957a4`)
  - Thiết lập từ điển alias Packing List (`config/packing_extraction.yaml`) cho 16 trường header và 7 trường item bằng EN/VI/ZH với phân định vai trò nghiêm ngặt (seller/buyer tách biệt shipper/consignee; package count tách biệt quantity; gross weight tách biệt net weight; dimensions tách biệt volume).
  - Trình tải cấu hình độc lập với CWD, ngăn chặn trùng lặp key YAML và chặn mã độc thực thi (`_UniqueKeySafeLoader`).
  - Sửa lỗi runtime type annotation cho `PackingList.date` (`CanonicalField[datetime.date]`) được Project Leader phê duyệt, khắc phục hiện tượng field name che khuất kiểu dữ liệu mà không làm thay đổi canonical schema hay database models.
  - Xây dựng result contracts chặt chẽ (`PackingListHeaderExtractionResult`, `PackingItemExtractionResult`) với cơ chế kiểm soát status, issue gating và revalidation snapshot phòng thủ.
  - Tái sử dụng trọn vẹn các thành phần đã được kiểm chứng từ TASK-006 (`normalize_alias`, `parse_decimal`, `parse_date`, `ExtractionStatus`, `ExtractionIssue`, `ExtractionCandidate`).
  - Bộ kiểm thử: 81 test cases mới, 697 tests full-suite passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 27/27 adversarial probes độc lập passed.
- `TASK-006 — Invoice Extraction (EPIC)` (DONE — 2026-10-29, all child tasks TASK-006A..F merged and verified)
  - Hoàn thành toàn diện pipeline trích xuất Commercial Invoice cho PDF và Excel.
  - Bao gồm: extraction primitives & config (006A), deterministic headers & party extraction (006B), Excel item tables (006C), transactional persistence & history (006D), application extraction service & visual/semantic safety gates (006E), và end-to-end integration & regression (006F).
  - Giới hạn được chấp thuận: PDF item table extraction chưa hỗ trợ trong V1 (`PDF_ITEMS_UNSUPPORTED`), tự động trả `NEEDS_REVIEW` để người dùng kiểm tra thủ công.
- `TASK-006F — Invoice Integration & Regression` (DONE — Merged via PR #6, commit `be6c7d9`)
  - End-to-end production pipeline integration connecting ingestion, classification, parsing, deterministic extraction, visual safety, semantic boundary, and persistence.
  - Native 2-page PDF integration: verified zero visual/OCR provider calls, exact decimal/date provenance, empty items list, and explicit `PDF_ITEMS_UNSUPPORTED` review issue.
  - Excel XLSX and XLS integration: exact decimal precision, zero/negative values, multi-sheet/shifted coordinates, formula opaqueness, and multi-table/hidden content abstention.
  - Visual safety gates: whole-document review and zero semantic fallback calls on unresolved/conflicted pages; regression fix in `_resolve_pdf` enforcing strict metadata identity.
  - Semantic boundary: verified fill-only policy, sticky deterministic conflicts, privacy sanitization, and grounded missing-header fill.
  - SQLite persistence: verified 4-attempt lifecycle, single-active-record invariant, failed replacement deactivation safety, trigger rollback, and writer-lock CAS guards.
  - Test suite: 50 new integration tests (21 True E2E, 29 Cross-Module), 616 full-suite tests passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 14 independent adversarial probes verified.
- `TASK-006E — Invoice Extraction Service` (DONE — Merged via PR #5, commit `b6932c6`)
  - Application extraction service orchestration (`InvoiceExtractionService`, `build_invoice_extraction_service`).
  - Non-mutating downstream read/parse pipeline (`parse_document_readonly`), preventing status downgrade from `CLASSIFIED`/`NEEDS_REVIEW` to `PARSED`.
  - Content and metadata dual classification gate rejecting misclassified documents and misleading filenames.
  - Visual quality and safety gates: unusable or conflicting visual pages terminate immediately with `NEEDS_REVIEW` and bypass semantic fallback with exactly 0 calls.
  - Canonical invoice composition: deterministic headers (TASK-006B) and Excel item tables (TASK-006C) assembled with typed candidates and full provenance; PDF item extraction explicitly unsupported with `PDF_ITEMS_UNSUPPORTED` review flag.
  - Semantic fallback grounding: role-labeled source extraction, strict raw/coordinate/type matching, fill-only policy rejecting overwrites or ungrounded proposals, sticky deterministic review issues.
  - Transactional CAS persistence under `BEGIN IMMEDIATE` with `expected_active_extraction_id` and atomic `expected_source_document` snapshot verification.
  - Test suite: 131 new focused tests, 566 full-suite tests passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 14 independent adversarial probes verified.
- `TASK-006D — Extraction Persistence & State` (DONE — Merged via PR #4, commit `cd875b9`)
  - Local extraction persistence and state management in SQLite repository layer (`document_extractions` table).
  - Single active extraction per document enforced at database engine level via unique partial index (`WHERE is_active = 1`).
  - Append-only extraction history with strictly monotonic per-document attempt numbering (`UNIQUE(document_id, attempt_number)`).
  - Transactional atomicity: `BEGIN IMMEDIATE` writer lock; atomic deactivation, insert, and `SourceDocument` metadata update; explicit rowcount assertion (`rowcount == 1`) and full rollback on constraint, trigger, or commit errors.
  - Distinct failure semantics: `FAILED` attempts are stored as inactive history (`is_active = 0`) and never deactivate or overwrite prior valid active extractions (`EXTRACTED` / `NEEDS_REVIEW`).
  - Explicit re-extraction policy: initial save requires no active extraction; replacement requires exact `expected_active_extraction_id` plus optimistic source hash and status verification.
  - Storage codec envelope v1 with explicit scalar type-tagging for candidate unions; full preservation of canonical `Decimal` scale/precision, dates, and multilingual CJK/Vietnamese text.
  - Privacy and immutability: zero customer data in logs/exceptions; static sanitized error messages; no modification of source files.
  - Test suite: 144 new focused repository tests, 435 full-suite tests passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 23 independent adversarial and concurrency probes verified.
- `TASK-006C — Invoice Item Tables` (DONE — Merged via PR #3, commit `8bbb7f8`)
  - Conservative extraction of `InvoiceItem` rows from generic Excel item tables (`ParsedWorkbook`).
  - Table-header candidate discovery at arbitrary row/column positions across visible sheets using approved EN/VI/ZH item aliases.
  - Dual-constraint header validation (requires identity/content and numeric fields; `NO + QTY` alone is insufficient).
  - Grounded body product identity requirement (descriptions made solely of numbers do not certify a table).
  - Exact summary boundaries (`TOTAL`, `GRAND TOTAL`, `TỔNG CỘNG`, `合计`) and subtotal flags (`ITEM_SUBTOTAL_BOUNDARY`); product safety for names prefixed with total (`TOTALIZER`, `TOTAL CONTROL`, `TOTAL LOSS`).
  - Strict abstention on competing tables across sheets or within same sheet (`MULTIPLE_ITEM_TABLES`), compound/duplicate columns, and merged headers.
  - Conservative formula policy: formula cells/text never act as headers; formula values flag `UNRESOLVED_ITEM_FORMULA` with `NEEDS_REVIEW` and retain raw expressions in candidates.
  - Full provenance across all 14 canonical fields (`source_document_id`, `sheet`, `coordinate`, `confidence=0.95`).
  - Test suite: 42 new focused tests, 291 full-suite tests passed, 2 warnings (Python 3.13.14, pytest 9.1.1); 42 independent probes verified.
- `TASK-006B — Deterministic Invoice Headers` (DONE — Merged via PR #2, commit `29c4da2`)
  - Deterministic invoice header and party extraction from `ParsedPdfDocument`, safe `ResolvedPdfDocument`, and `ParsedWorkbook`.
  - Strict party role separation for seller, buyer, and ship-to (MASTER_SPEC.md:499).
  - Exact source evidence: raw value, casing, page/sheet/cell provenance.
  - Conservative formula policy: formula cells and expression text are opaque, never serve as label sources, and formulas as values trigger `UNRESOLVED_FORMULA_FIELD` with `NEEDS_REVIEW`.
  - Strict rejection of boolean and native time cells for numeric/date fields without invalid coercion.
  - Inline value span parsing (amount, date, zero, negative).
  - Test suite: 42 new focused tests, 249 full-suite tests passed, 2 warnings (Python 3.13.14, pytest 9.1.1).
- `TASK-006A — Extraction Foundation` (DONE — Merged via PR #1)
  - Primitives: `ExtractionStatus`, typed `ExtractionIssue`, provider-neutral `ExtractionCandidate`.
  - Configuration: `config/invoice_extraction.yaml` covering 17 approved header paths and 14 item paths with strict EN/VI/ZH aliases and party role separation (MASTER_SPEC.md:499).
  - Lexical parsing: strict `parse_decimal` (safe integers, decimals, grouped formats; rejection of ambiguous single separators and non-finite numbers) and `parse_date` (explicit ISO-like formats; datetime truncation to pure date).
  - Test suite: 207 passed, 2 warnings (Python 3.13.14, pytest 9.1.1).

## Local parser layer

TASK-004 adds deterministic local parsing for persisted PDF, XLSX, and legacy XLS files.

- PDF uses `pypdf`, preserves page boundaries, and flags documents with no locally extractable text as `needs_ocr=true`; OCR is not performed in this task.
- XLSX uses `openpyxl` and preserves populated-cell coordinates, formulas, number formats, merged ranges, sheet state, and hidden row/column metadata.
- XLS uses `xlrd` and preserves sheet/cell provenance plus available merged/hidden metadata.
- Parsing starts from a persisted `SourceDocument`; stored paths are resolved and constrained to the configured upload root.
- Parsers never classify document business type, execute formulas/macros, call AI/network services, or modify uploaded source files.

### Document Classification
Classification evaluates technical parsed content deterministically against configured clues (no AI/network calls). 
- Filename is entirely ignored for scoring. Content is the sole source of truth.
- Resolves conflicts conservatively: weak or conflicting evidence securely defaults to `UNKNOWN` (needs review).
- `OTHER` is reserved for explicit manual classification, and is never inferred merely by the absence of clues.
- Generic references such as `PO NO`, `FORM E`, and `C/O` are supporting clues only and cannot classify a document by themselves.

### Local scanned-PDF vision layer

TASK-005A adds an accuracy-first visual fallback for PDF pages whose native text is unusable.

- Clean/native PDF pages keep the existing `pypdf` text and do not invoke visual providers.
- Visual pages are rendered once in memory and reused by both providers.
- PaddleOCR-VL 1.6 runs as the primary local full-pipeline document parser through the official PaddleX loopback serving API.
- RapidOCR 3.x runs locally as an independent literal OCR verifier/fallback.
- Provider output is accepted only after a shared text-quality gate.
- Material numeric/date/identifier/document-clue conflicts become `NEEDS_REVIEW`; outputs are never concatenated to manufacture agreement.
- The VLM endpoint is restricted to loopback hosts and local inference concurrency defaults to one request.
- Normal document processing uses no hosted AI API.
