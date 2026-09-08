# PROJECT_CONSTITUTION.md

# Customs AI Checker — Project Constitution

Version: 0.1  
Status: Active  
Project: Customs AI Checker  
Purpose: Hệ thống AI hỗ trợ kiểm tra chứng từ và dữ liệu khai báo hải quan Việt Nam.

---

# 1. MỤC ĐÍCH CỦA TÀI LIỆU

Tài liệu này là bộ nguyên tắc cao nhất của dự án Customs AI Checker.

Mọi thành phần của dự án, bao gồm:

- ChatGPT / Project Leader
- Gemini Main Developer
- Gemini Reviewer / QA
- Developer khác
- AI agent khác
- Code
- Prompt
- Rule
- Database
- Workflow
- Documentation

đều phải tuân thủ tài liệu này.

Nếu một Task, Prompt, Implementation hoặc đề xuất kỹ thuật xung đột với PROJECT_CONSTITUTION.md thì PROJECT_CONSTITUTION.md được ưu tiên.

Thứ tự ưu tiên tài liệu:

1. PROJECT_CONSTITUTION.md
2. MASTER_SPEC.md
3. ARCHITECTURE.md
4. Data Schema / Rule specification
5. Task specification
6. Implementation
7. AI suggestion

Không AI nào được tự ý thay đổi Constitution.

Mọi thay đổi Constitution phải được Project Owner phê duyệt.

---

# 2. PROJECT OWNER

Project Owner là người sử dụng và chịu trách nhiệm cuối cùng đối với hệ thống.

Project Owner quyết định:

- phạm vi dự án;
- nghiệp vụ cần triển khai;
- quy tắc nội bộ;
- mức độ automation;
- dữ liệu nào được sử dụng;
- thay đổi architecture lớn;
- release production.

AI không được tự nhận quyền quyết định thay Project Owner.

---

# 3. MỤC TIÊU CỐT LÕI

Customs AI Checker được xây dựng để hỗ trợ nhân viên khai báo hải quan kiểm tra chứng từ nhanh hơn, có hệ thống hơn và giảm lỗi nghiệp vụ.

Hệ thống phải hướng tới khả năng:

1. Nhận nhiều loại chứng từ khác nhau.
2. Hiểu chứng từ có layout không cố định.
3. Chuẩn hóa dữ liệu từ nhiều nguồn.
4. Đối chiếu dữ liệu giữa các chứng từ.
5. Kiểm tra theo loại hình tờ khai.
6. Kiểm tra theo rule nghiệp vụ.
7. Phát hiện dữ liệu thiếu, sai hoặc bất thường.
8. Truy vết được kết luận về chứng từ nguồn.
9. Biết rõ khi nào hệ thống không đủ cơ sở kết luận.
10. Giảm tối đa chi phí vận hành AI.

Mục tiêu không phải tạo một chatbot trả lời nghe thông minh.

Mục tiêu là tạo một công cụ có thể sử dụng trong nghiệp vụ thực tế.

---

# 4. PHẠM VI HỆ THỐNG

Hệ thống có thể xử lý các loại dữ liệu như:

- Commercial Invoice
- Packing List
- Bill of Lading
- Air Waybill
- Contract
- Purchase Order
- Certificate of Origin
- Catalogue
- Specification
- Customs Declaration
- Excel khai báo
- PDF
- Word
- Image
- Scan
- Email attachment
- Master data hàng hóa
- Rule nghiệp vụ
- Văn bản pháp luật đã được xác minh

Ngôn ngữ có thể bao gồm:

- Tiếng Việt
- Tiếng Anh
- Tiếng Trung
- Chứng từ song ngữ

Layout chứng từ không được giả định là cố định.

---

# 5. NGUYÊN TẮC THIẾT KẾ CỐT LÕI

## 5.1 AI xử lý sự không chắc chắn

AI được ưu tiên cho:

- hiểu tài liệu phi cấu trúc;
- nhận diện loại chứng từ;
- hiểu ngữ nghĩa mô tả hàng;
- mapping dữ liệu khác layout;
- phân tích trường hợp không thể biểu diễn bằng rule đơn giản;
- hỗ trợ người dùng hiểu lỗi.

AI không phải lựa chọn mặc định cho mọi tác vụ.

---

## 5.2 Deterministic code xử lý điều chắc chắn

Các tác vụ sau phải ưu tiên code deterministic:

- cộng trừ;
- kiểm tra tổng;
- so sánh số;
- so sánh ngày;
- so sánh currency;
- validation format;
- duplicate detection;
- mapping dictionary;
- database lookup;
- rule có điều kiện rõ ràng;
- kiểm tra consistency;
- unit conversion khi công thức xác định.

Không dùng LLM nếu Python hoặc rule engine làm chính xác hơn.

---

## 5.3 Không hard-code layout khách hàng

Không được xây hệ thống dựa trên giả định kiểu:

- Invoice number luôn nằm ở ô B7;
- Quantity luôn ở cột F;
- Total luôn nằm ở cuối trang;
- khách A luôn dùng một template duy nhất.

Có thể tạo customer-specific adapter khi thực sự cần thiết, nhưng:

- adapter phải là lớp bổ sung;
- hệ thống chung vẫn phải hoạt động độc lập;
- không được làm kiến trúc phụ thuộc vào một khách hàng.

---

# 6. KIẾN TRÚC TỐI THIỂU

Luồng xử lý chuẩn:

Document Input

→ File Validation

→ Document Classification

→ Data Extraction

→ Normalization

→ Canonical Data Model

→ Rule Engine

→ Cross-document Validation

→ AI Reasoning nếu cần

→ Result Aggregation

→ Human-readable Report

→ Audit Log

Không được bỏ qua Normalization và đưa trực tiếp dữ liệu extraction vào toàn bộ business logic.

---

# 7. CANONICAL DATA MODEL

Mọi chứng từ phải được chuyển về một cấu trúc dữ liệu chuẩn chung.

Ví dụ các entity:

- Shipment
- Party
- Invoice
- InvoiceItem
- PackingList
- PackingItem
- TransportDocument
- CustomsDeclaration
- Product
- OriginDocument
- Rule
- CheckResult
- Evidence
- SourceDocument

Canonical Model phải có version.

Ví dụ:

schema_version: "1.0"

Không thay đổi schema làm mất backward compatibility nếu chưa có migration plan.

---

# 8. RAW DATA KHÔNG ĐƯỢC BỊ MẤT

Khi normalize dữ liệu phải giữ ít nhất:

- `raw_value`
- `normalized_value`
- `source_document`
- `page` hoặc `sheet`
- vị trí nếu xác định được
- `extraction_method`
- `confidence` nếu do AI tạo ra

Ví dụ:

```json
{
  "field": "invoice_total",
  "raw_value": "USD 12,500.00",
  "normalized_value": 12500.00,
  "currency": "USD",
  "source_document": "INV001.pdf",
  "page": 1,
  "confidence": 0.99
}
```

Không được chỉ lưu:

```json
{
  "invoice_total": 12500
}
```

nếu việc đó làm mất khả năng truy vết.

---

# 9. PROVENANCE — NGUỒN GỐC DỮ LIỆU

Mọi dữ liệu quan trọng phải có khả năng trả lời:

> "Thông tin này lấy từ đâu?"

Một `CheckResult` phải liên kết được tới `Evidence`.

Ví dụ:

```text
ERROR — Quantity mismatch

Invoice:
1000 PCS

Packing List:
980 PCS

Evidence:
- INV001.pdf — page 1
- PL001.pdf — page 2
```

Không được tạo `ERROR` chỉ dựa trên kết luận của AI mà không có dữ liệu nguồn nếu dữ liệu nguồn có thể xác định.

---

# 10. TRẠNG THÁI KẾT QUẢ

Hệ thống phải phân biệt tối thiểu:

PASS

Dữ liệu đã được kiểm và phù hợp.

ERROR

Có mâu thuẫn hoặc lỗi xác định được bằng rule hoặc evidence đủ mạnh.

WARNING

Có dấu hiệu bất thường nhưng chưa đủ cơ sở kết luận sai.

MISSING

Thiếu dữ liệu cần thiết.

NOT_CHECKED

Hệ thống chưa thực hiện hoặc không thể thực hiện phép kiểm.

NEEDS_REVIEW

Cần con người kiểm tra.

INSUFFICIENT_EVIDENCE

Không đủ bằng chứng để kết luận.

Không được biến:

UNKNOWN

thành:

PASS.

11. CONFIDENCE

Kết quả AI extraction hoặc AI reasoning phải có confidence khi phù hợp.

Confidence không được sử dụng như bằng chứng pháp lý.

Ví dụ:

confidence = 0.96

chỉ biểu thị mức tự tin của hệ thống.

Không có nghĩa dữ liệu chắc chắn đúng 96%.

Các field có confidence thấp phải được đánh dấu để review.

Threshold phải có thể config.

Không hard-code threshold rải rác trong source code.

12. NGUYÊN TẮC "KHÔNG BIẾT"

Hệ thống phải có khả năng nói:

không xác định được;
thiếu dữ liệu;
cần người dùng xác nhận;
không đủ nguồn;
không áp dụng được rule.

Đây là hành vi đúng.

Hệ thống không được tạo câu trả lời chỉ để tránh trạng thái UNKNOWN.

Nguyên tắc:

Unknown > Fabricated Answer.

13. HALLUCINATION POLICY

Nghiêm cấm AI tự tạo:

invoice number;
quantity;
amount;
HS code;
loại hình;
xuất xứ;
tax rate;
tên doanh nghiệp;
số văn bản;
điều khoản pháp luật;
policy requirement;
thông tin chứng từ không tồn tại.

Nếu AI suy luận từ context thì phải ghi rõ:

INFERRED

không được ghi thành:

EXTRACTED.

14. PHÂN BIỆT EXTRACTION VÀ INFERENCE

Hai loại dữ liệu phải được phân biệt.

EXTRACTED:

Dữ liệu thực sự xuất hiện trong chứng từ.

Ví dụ:

Invoice ghi:

1000 PCS

INFERRED:

Hệ thống suy ra từ context.

Ví dụ:

"Đây có khả năng là đơn vị SET."

Hai loại này không được lưu như nhau.

Canonical model nên cho phép:

{
  "value": "SET",
  "origin": "inferred",
  "confidence": 0.71
}
15. NGUYÊN TẮC PHÁP LÝ

Customs AI Checker là công cụ hỗ trợ nghiệp vụ.

Không coi output AI là nguồn pháp lý.

Đối với các nội dung như:

Luật;
Nghị định;
Thông tư;
Quyết định;
Công văn;
QCVN;
TCVN;
chính sách quản lý hàng hóa;
thuế suất;
HS classification;
điều kiện miễn giảm thuế;
thủ tục Hải quan;

nếu hệ thống đưa ra kết luận pháp lý, phải có nguồn được xác minh.

Không được bịa:

số văn bản;
ngày ban hành;
cơ quan ban hành;
điều;
khoản;
nội dung.

Nếu không xác minh được:

INSUFFICIENT_EVIDENCE

hoặc:

NEEDS_LEGAL_REVIEW.

16. HS CODE POLICY

Hệ thống không được mặc định AI prediction là HS code chính xác.

AI có thể:

đề xuất candidate HS;
tìm mặt hàng tương tự;
phân tích đặc điểm;
phát hiện mô tả thiếu;
so sánh với master data.

Nhưng kết quả phải phân biệt:

MASTER_MATCH

RULE_BASED_SUGGESTION

AI_SUGGESTION

VERIFIED_CLASSIFICATION

Không được gộp tất cả thành:

HS CODE.

17. MASTER DATA

Master data là nguồn tham khảo quan trọng.

Hệ thống phải ưu tiên:

Database lookup

→ similarity search

→ retrieval

→ AI reasoning

Không đưa toàn bộ master data vào prompt nếu không cần thiết.

Master data phải có khả năng versioning và audit.

Nếu một record master cũ có thể sai thì không được coi nó là "ground truth" tuyệt đối.

18. RULE ENGINE

Business Rules phải được tách khỏi code tối đa có thể.

Rule có thể lưu bằng:

YAML
JSON
Database
Rule configuration

Rule tối thiểu nên chứa:

rule_id
name
description
category
applicable_declaration_types
required_inputs
condition
severity
result
effective_from
effective_to
version
source
notes

Ví dụ:

rule_id: INV_TOTAL_001
name: Invoice total reconciliation
category: financial
severity: ERROR

applies_to:
  - E13
  - E11

condition:
  invoice_total == sum(invoice_items.amount)

result_if_false:
  ERROR
19. KHÔNG TẠO "IF/ELSE HELL"

Không được triển khai toàn bộ nghiệp vụ bằng một chuỗi:

if declaration_type == ...
elif customer == ...
elif ...

Nếu business logic thay đổi thường xuyên thì phải cân nhắc:

configuration;
rule engine;
mapping table;
strategy pattern;
plugin architecture.

Code phải chịu trách nhiệm thực thi rule.

Rule phải chịu trách nhiệm mô tả nghiệp vụ.

20. VERSIONING RULE

Rule phải hỗ trợ thời gian hiệu lực.

Ví dụ:

Rule A áp dụng từ:

2026-01-01

Rule B thay thế từ:

2026-07-01

Không được overwrite lịch sử khiến hệ thống không thể tái tạo kết quả cũ.

21. DOCUMENT VERSION

Một shipment có thể có:

Original Invoice
Revised Invoice
Invoice V2
Packing List revised

Hệ thống không được mặc định file upload cuối cùng luôn là file đúng.

Phải có khả năng xác định:

revision;
duplicate;
document replacement;
conflicting versions.

Nếu không chắc:

WARNING / NEEDS_REVIEW.

22. ITEM MATCHING

Không được match item chỉ bằng vị trí dòng.

Invoice item #1 không nhất thiết tương ứng Packing List item #1.

Item matching có thể sử dụng:

item code;
SKU;
part number;
model;
description;
quantity;
semantic similarity.

Nếu matching không chắc chắn phải biểu thị confidence.

Không được cưỡng ép match.

23. CHI PHÍ VẬN HÀNH

Chi phí thấp là một requirement chính thức của dự án.

Ưu tiên theo thứ tự:

deterministic code;
local parsing;
cached result;
database query;
search / retrieval;
model nhỏ;
model mạnh.

Model mạnh chỉ được gọi khi có giá trị rõ ràng.

Không sử dụng model đắt tiền để:

cộng số;
kiểm format;
so sánh field;
detect duplicate đơn giản;
lookup database;
làm việc có thể giải quyết bằng code.
24. CACHE

Không xử lý lại tài liệu nếu nội dung không thay đổi.

File phải có fingerprint/hash.

Ví dụ:

SHA-256.

Nếu file đã được extract trước đó:

reuse extraction result

thay vì gọi LLM lại.

Cache phải có version theo:

extraction model;
prompt version;
schema version.
25. MODEL INDEPENDENCE

Core system không được phụ thuộc hoàn toàn vào một AI vendor.

Model interface phải có khả năng thay đổi giữa:

OpenAI
Gemini
model khác

mà không cần viết lại toàn bộ business logic.

Vendor-specific code phải được cô lập trong adapter/provider layer.

26. SECURITY

Chứng từ Hải quan có thể chứa thông tin doanh nghiệp nhạy cảm.

Nghiêm cấm hard-code:

API keys
passwords
tokens
credentials
database secrets

Secrets phải lưu bằng:

environment variables;
secret manager;
secure local config không commit.

.env phải được đưa vào .gitignore.

Không commit tài liệu nhạy cảm lên public repository.

27. DATA MINIMIZATION

Chỉ gửi dữ liệu cần thiết cho API.

Không gửi nguyên bộ chứng từ tới nhiều model nếu một đoạn nhỏ đủ để giải quyết task.

Ưu tiên:

extract once

→ store structured data

→ downstream modules dùng structured data.

28. LOGGING

Logging phải đủ để debug nhưng không được chứa dữ liệu nhạy cảm không cần thiết.

Log nên có:

document ID
task ID
module
timestamp
model
prompt version
execution result
error code

Không log toàn bộ:

invoice;
contract;
token;
credential;

nếu không cần.

29. AUDITABILITY

Hệ thống phải có khả năng trả lời:

rule nào tạo kết quả này?
rule version nào?
dữ liệu nguồn nào?
model nào được sử dụng?
prompt version nào?
lúc nào xử lý?
extraction nào được dùng?
người dùng có override kết quả không?

Các quyết định quan trọng phải có audit trail.

30. HUMAN OVERRIDE

Người dùng phải có quyền sửa dữ liệu AI đọc sai.

Ví dụ:

AI:

Quantity = 100

Người dùng sửa:

Quantity = 1000

Hệ thống phải giữ:

original extraction

và:

human corrected value.

Không overwrite làm mất lịch sử.

Human confirmed data được ưu tiên hơn AI extraction.

31. ERROR HANDLING

Không được silent failure.

Nếu một module lỗi phải:

ghi nhận lỗi;
không giả định dữ liệu mặc định;
không tiếp tục tạo PASS giả;
thông báo module nào thất bại.

Ví dụ:

OCR FAILED

không được biến thành:

Quantity = 0.

32. TESTING PHILOSOPHY

Test phải cố gắng phá hệ thống.

Không chỉ test happy path.

Phải có test cho:

missing fields;
null;
duplicate;
malformed file;
scan mờ;
scan nghiêng;
bảng nhiều trang;
nhiều Invoice;
nhiều Packing List;
nhiều currency;
decimal separator;
merged cell;
hidden row;
formulas;
Chinese text;
item order khác nhau;
quantity giống nhưng unit khác;
description gần giống;
revised document;
rounding;
weight mismatch;
inconsistent total;
corrupted PDF.
33. GOLDEN TEST DATASET

Dự án phải dần xây một bộ:

Golden Test Dataset.

Mỗi case nên có:

input documents;
expected extraction;
expected checks;
expected warnings;
expected errors.

Khi thay model, prompt hoặc rule:

chạy regression test.

Không deploy nếu làm giảm đáng kể độ chính xác trên golden dataset.

34. FALSE NEGATIVE ƯU TIÊN CAO

Trong nghiệp vụ kiểm tra chứng từ:

False Negative thường nguy hiểm hơn False Positive.

False Negative:

Có lỗi nhưng hệ thống báo PASS.

Do đó:

khi evidence chưa đủ mạnh để PASS,

ưu tiên:

WARNING / NEEDS_REVIEW

thay vì PASS.

Tuy nhiên hệ thống không được tạo quá nhiều WARNING vô nghĩa.

35. SEVERITY

Các issue nên có severity:

CRITICAL

Có thể dẫn tới kết luận nghiệp vụ nghiêm trọng sai.

HIGH

Lỗi quan trọng có khả năng ảnh hưởng khai báo.

MEDIUM

Vấn đề cần kiểm tra nhưng không nhất thiết ngăn khai báo.

LOW

Vấn đề nhỏ hoặc chất lượng dữ liệu.

INFO

Thông tin bổ sung.

Severity phải do rule hoặc policy xác định, không để LLM tùy ý chọn nếu có thể.

36. DEVELOPMENT PRINCIPLES

Code phải ưu tiên:

simplicity;
readability;
maintainability;
testability;
observability;
low cost.

Không ưu tiên:

clever code;
framework phức tạp;
công nghệ mới chỉ vì mới;
abstraction không cần thiết.
37. KHÔNG OVER-ENGINEER

Không xây microservices nếu một modular monolith đủ dùng.

Không triển khai:

Kubernetes;
distributed queue;
vector database;
agent swarm;
complex orchestration;

chỉ vì nghe hiện đại.

Chỉ thêm complexity khi có requirement thực tế.

38. TECHNOLOGY DECISION

Mỗi dependency lớn phải trả lời được:

Nó giải quyết vấn đề gì?
Có giải pháp đơn giản hơn không?
Chi phí vận hành?
Vendor lock-in?
Khả năng bảo trì?

Nếu không có lý do rõ ràng:

không thêm dependency.

39. ROLE — PROJECT LEADER

Project Leader chịu trách nhiệm:

architecture;
specification;
decomposition;
priority;
task definition;
design review;
final technical decision;
merge recommendation.

Project Leader không được:

bịa yêu cầu nghiệp vụ;
thay đổi scope không có lý do;
bỏ qua evidence từ Reviewer.
40. ROLE — MAIN DEVELOPER

Main Developer chịu trách nhiệm:

implementation;
tests;
documentation;
self-review;
technical questions;
báo cáo limitation.

Main Developer không được tự ý:

thay đổi Constitution;
thay đổi architecture lớn;
thay đổi canonical schema;
xóa rule;
thay business logic đã duyệt.

Nếu cần thay đổi phải tạo đề xuất.

41. ROLE — REVIEWER / QA

Reviewer có nhiệm vụ tìm lỗi.

Reviewer không có nghĩa vụ đồng ý với Developer.

Reviewer phải tập trung vào:

correctness;
false negative;
false positive;
edge cases;
cost;
security;
maintainability;
hallucination;
legal risk.

Reviewer có quyền:

REQUEST CHANGES.

42. TASK WORKFLOW

Task lifecycle:

TODO

→ IN_PROGRESS

→ REVIEW

→ CHANGES_REQUESTED nếu cần

→ APPROVED

→ DONE

File task nằm tại:

tasks/todo/

Khi bắt đầu:

tasks/in_progress/

Khi hoàn thành:

tasks/done/

Không đánh dấu DONE khi chưa đạt acceptance criteria.

43. TASK ID

Mỗi task phải có ID duy nhất.

Ví dụ:

TASK-001
TASK-002
TASK-003

Tên file:

TASK-001-document-ingestion.md

Không tái sử dụng ID.

44. TASK SPECIFICATION

Mỗi Task tối thiểu phải có:

Objective
Background
Scope
Out of Scope
Input
Output
Requirements
Constraints
Acceptance Criteria
Tests
Dependencies

Developer không được code khi task mơ hồ đến mức không xác định được acceptance criteria.

45. DEFINITION OF DONE

Một task chỉ được xem là DONE khi:

Implementation hoàn thành.
Code chạy.
Acceptance criteria đạt.
Tests pass.
Không có Critical issue chưa xử lý.
Reviewer approve hoặc Project Leader override có lý do.
Documentation được cập nhật nếu cần.
Không chứa secrets.
Không phá regression tests.
46. REVIEW DECISION

Reviewer phải trả một trong:

APPROVE

REQUEST CHANGES

REJECT

Không sử dụng trạng thái mơ hồ như:

"Looks good."

Nếu REQUEST CHANGES phải ghi rõ điều kiện cần sửa.

47. CHANGE CONTROL

Thay đổi ảnh hưởng tới:

architecture;
canonical schema;
rule format;
provider interface;
database;
security;
Constitution;

phải có Decision Record.

Lưu tại:

docs/decisions/

Ví dụ:

ADR-001-use-sqlite-for-v1.md

48. ARCHITECTURE DECISION RECORD

ADR tối thiểu gồm:

Title

Context

Decision

Alternatives

Reason

Consequences

Date

Status

Không thay architecture lớn chỉ qua chat rồi quên ghi lại.

49. DOCUMENTATION IS PART OF THE PRODUCT

Nếu code thay đổi hành vi của hệ thống thì documentation liên quan phải cập nhật.

Không chấp nhận trạng thái:

Code nói một kiểu.

Documentation nói một kiểu.

50. PROMPT VERSIONING

Prompt dùng trong production phải có:

prompt_id
version
purpose
model
expected output schema

Ví dụ:

DOC_EXTRACT_INVOICE_V1

Không chỉnh production prompt trực tiếp mà không version.

51. STRUCTURED OUTPUT

Khi AI dùng để cung cấp dữ liệu cho code downstream:

ưu tiên JSON/schema.

Không parse prose nếu có thể yêu cầu structured output.

Schema validation phải diễn ra trước khi dữ liệu được đưa vào Rule Engine.

52. AI OUTPUT KHÔNG ĐƯỢC TIN MÙ QUÁNG

Mọi LLM output phải được coi là untrusted input.

Phải validate:

schema;
type;
enum;
number;
required fields;
consistency.

AI trả JSON hợp lệ không đồng nghĩa nội dung đúng.

53. MODEL ROUTING

Hệ thống nên hỗ trợ routing.

Ví dụ:

Simple extraction
→ cheap model

Complex document
→ stronger model

Semantic reasoning
→ stronger model

Deterministic validation
→ no LLM

Routing policy phải cấu hình được.

54. RETRY POLICY

Không retry LLM vô hạn.

Retry phải có giới hạn.

Nếu vẫn thất bại:

NEEDS_REVIEW.

Retry nên xem xét:

parsing failure;
timeout;
invalid schema;
transient API error.

Không retry chỉ để ép AI đưa ra câu trả lời mong muốn.

55. COST OBSERVABILITY

Mỗi AI request nên có khả năng ghi nhận:

provider;
model;
input tokens;
output tokens;
estimated cost;
task;
document ID.

Mục tiêu là sau này trả lời được:

"1000 bộ chứng từ/tháng tốn bao nhiêu tiền?"

56. PERFORMANCE

Không tối ưu hiệu năng sớm khi chưa cần.

Nhưng không được thiết kế cố ý kém hiệu quả.

Ưu tiên:

batch operations;
caching;
async khi phù hợp;
tránh duplicate processing.
57. FILE HANDLING

File input phải được coi là không đáng tin cậy.

Phải kiểm tra:

extension;
MIME;
size;
corrupted file;
encrypted file;
unsupported type.

Không crash toàn hệ thống vì một file lỗi.

58. CUSTOMER-SPECIFIC LOGIC

Nếu khách hàng có rule riêng:

phải tách thành configuration/profile.

Ví dụ:

customer_profiles/
CUSTOMER_A.yaml

Không trộn rule riêng của Customer A vào global rule.

Global logic phải hoạt động khi không có customer profile.

59. INTERNAL RULE VS LEGAL RULE

Mỗi rule phải phân biệt:

LEGAL

INTERNAL_POLICY

DATA_VALIDATION

CUSTOMER_SPECIFIC

HEURISTIC

Không được trình bày internal policy như yêu cầu pháp luật.

60. HEURISTIC

Heuristic không được tạo ERROR nếu không có cơ sở đủ mạnh.

Ví dụ:

"Mô tả hàng có vẻ quá ngắn"

nên là:

WARNING

không phải:

ERROR.

61. EXPLAINABILITY

Mỗi issue quan trọng phải giải thích được bằng ngôn ngữ con người.

Ví dụ tốt:

ERROR — Invoice total mismatch

Invoice total:
12,500 USD

Calculated item total:
12,050 USD

Difference:
450 USD

Source:
INV-001.pdf, page 1

Không chỉ trả:

ERROR_CODE_382.

62. UI KHÔNG ĐƯỢC CHE GIẤU SỰ KHÔNG CHẮC CHẮN

UI phải phân biệt rõ:

PASS

WARNING

ERROR

NOT CHECKED

NEEDS REVIEW.

Không dùng dấu xanh nếu hệ thống chưa thực sự kiểm.

63. PRIVACY

Dữ liệu thực tế không được dùng:

public demo;
public repository;
benchmark công khai;

nếu chưa được ẩn thông tin phù hợp.

Test document public phải là:

synthetic;
anonymized;
được phép sử dụng.
64. REPOSITORY RULES

Không commit:

.env

API keys

password

access token

private certificate

customer confidential documents

production database

Các file này phải được .gitignore.

65. BRANCH / CHANGE DISCIPLINE

Mỗi thay đổi lớn nên gắn với Task ID.

Commit message nên có dạng:

TASK-001: implement document classifier

TASK-001: add classifier tests

BUG-004: fix invoice total normalization

Không dùng commit message kiểu:

update

fix

final2

66. BUG POLICY

Bug phải được ghi nhận nếu ảnh hưởng:

extraction;
normalization;
validation;
legal conclusion;
business rule;
data loss;
security.

Bug nghiêm trọng phải có regression test trước khi đóng.

67. PRODUCTION SAFETY

Không tự động gửi tờ khai hoặc thực hiện hành động pháp lý bên ngoài chỉ dựa trên AI output trong V1.

V1 là:

decision-support system.

Không phải:

fully autonomous customs declaration system.

Automation mức cao hơn chỉ được triển khai khi Project Owner phê duyệt rõ ràng.

68. PHASED DEVELOPMENT

Ưu tiên triển khai theo giai đoạn.

V1:

Document intake
→ Classification
→ Extraction
→ Normalization
→ Cross-document check
→ Checklist report

Sau khi V1 ổn định mới mở rộng:

declaration type rules;
master data;
HS assistance;
policy retrieval;
declaration preparation;
advanced automation.

Không xây toàn bộ cùng lúc.

69. V1 SUCCESS CRITERIA

V1 được coi là thành công khi người dùng có thể:

Upload một bộ chứng từ.
Hệ thống nhận diện từng file.
Extract dữ liệu chính.
Normalize dữ liệu.
So sánh dữ liệu giữa chứng từ.
Hiển thị lỗi/cảnh báo.
Cho biết nguồn của lỗi.
Cho phép người dùng kiểm tra lại.
Không cần cấu hình riêng cho từng layout phổ biến.
Chi phí xử lý hợp lý.
70. NGUYÊN TẮC CUỐI CÙNG

Accuracy > Appearance.

Evidence > Confidence.

Traceability > Cleverness.

Deterministic Validation > AI Guess.

Simple Architecture > Unnecessary Complexity.

Low Operational Cost > Impressive Demo.

Human Review > Fabricated Certainty.

Unknown > Wrong Answer.

Một hệ thống tốt không phải hệ thống luôn có câu trả lời.

Một hệ thống tốt là hệ thống biết:

điều gì nó biết;
điều gì nó suy luận;
điều gì nó chưa biết;
và bằng chứng cho mỗi kết luận nằm ở đâu.
71. CONSTITUTION CHANGE POLICY

Bất kỳ thay đổi nào đối với tài liệu này phải:

Có lý do cụ thể.
Không làm giảm độ an toàn của hệ thống mà không có đánh giá.
Được Project Owner phê duyệt.
Tăng version.
Ghi lại thay đổi.

Ví dụ:

Version 0.1 → 0.2

Không được silently edit Constitution trong quá trình implement.

END OF PROJECT CONSTITUTION

Có một việc tôi muốn chỉnh cấu trúc repo của bạn ngay từ đầu: sau này trong `docs/` nên thêm `decisions/`, để các quyết định kiểu “tại sao chọn SQLite”, “tại sao dùng model A thay model B” không bị thất lạc.

Sau file này, file quan trọng nhất tiếp theo là **`MASTER_SPEC.md`** — Constitution nói “phải làm dự án theo nguyên tắc nào”, còn Master Spec sẽ quy định **con Customs AI của bạn thực tế phải check những gì, input/output ra sao và V1 có những chức năng nào**.
