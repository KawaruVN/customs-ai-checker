# MASTER_SPEC.md

# Customs AI Checker — Master Specification

Version: 0.1  
Status: Draft  
Project: Customs AI Checker

---

# 1. PURPOSE

Customs AI Checker là hệ thống hỗ trợ nhân viên khai báo hải quan kiểm tra chứng từ và dữ liệu khai báo trước khi thực hiện hoặc hoàn tất khai báo hải quan.

Hệ thống hướng tới việc:

- giảm lỗi nhập liệu;
- giảm bỏ sót thông tin;
- giảm thời gian đối chiếu chứng từ;
- chuẩn hóa quy trình kiểm tra;
- hỗ trợ kiểm tra theo loại hình tờ khai;
- truy vết được nguồn của mỗi kết luận;
- tận dụng dữ liệu lịch sử và master data;
- giữ chi phí AI ở mức thấp.

Hệ thống không được coi là nguồn pháp lý cuối cùng và không thay thế trách nhiệm kiểm tra của người khai hải quan.

---

# 2. CORE USER

Người dùng chính:

Nhân viên khai báo hải quan / customs declarant.

Người dùng có thể:

- nhận bộ chứng từ từ khách hàng;
- upload chứng từ;
- chọn hoặc nhập loại hình;
- yêu cầu hệ thống kiểm tra;
- xem các lỗi và cảnh báo;
- mở lại nguồn chứng từ;
- sửa dữ liệu AI đọc sai;
- xác nhận kết quả;
- tái kiểm tra sau khi sửa chứng từ.

---

# 3. CORE USE CASE

Use Case chính của V1:

Người dùng đưa một bộ chứng từ vào hệ thống.

Ví dụ:

- Commercial Invoice
- Packing List
- Bill of Lading
- AWB
- Contract
- Purchase Order
- C/O
- Catalogue
- Specification
- File Excel dữ liệu khai báo
- Tờ khai dự kiến

Hệ thống thực hiện:

1. Nhận file.
2. Xác định loại file.
3. Phân loại loại chứng từ.
4. Extract thông tin.
5. Chuẩn hóa dữ liệu.
6. Ghép các item tương ứng.
7. Kiểm tra consistency.
8. Chạy rule phù hợp.
9. Phát hiện lỗi và điểm đáng nghi.
10. Hiển thị report.
11. Cho phép người dùng kiểm tra evidence.

---

# 4. SUPPORTED INPUT TYPES

V1 phải thiết kế để hỗ trợ:

- PDF text
- PDF scan
- XLS
- XLSX
- CSV
- DOCX
- JPG
- JPEG
- PNG

Không bắt buộc tất cả format phải hoàn thiện ngay TASK đầu tiên.

Architecture phải cho phép mở rộng các format trên.

---

# 5. SUPPORTED DOCUMENT TYPES

Các loại chứng từ dự kiến gồm:

- Commercial Invoice
- Packing List
- Bill of Lading
- Sea Waybill
- Air Waybill
- Contract
- Purchase Order
- Certificate of Origin
- Customs Declaration
- Catalogue
- Product Specification
- Shipping Advice
- Debit Note
- Credit Note
- Freight Invoice
- Insurance Document
- Other

Document classification phải hỗ trợ:

UNKNOWN

nếu không đủ cơ sở phân loại.

---

# 6. MULTIPLE CUSTOMER LAYOUTS

Hệ thống phải hoạt động với chứng từ của nhiều khách hàng khác nhau.

Không giả định:

- vị trí invoice number cố định;
- tên cột cố định;
- thứ tự item cố định;
- ngôn ngữ cố định;
- một khách chỉ dùng một template.

Ví dụ hệ thống phải có thể hiểu các trường tương đương:

- Invoice No
- Invoice Number
- Inv No.
- Commercial Invoice No.
- 发票号码
- 发票号
- Số hóa đơn

và normalize về cùng một field:

invoice_number

---

# 7. LANGUAGE SUPPORT

V1 ưu tiên:

- Vietnamese
- English
- Chinese

Một chứng từ có thể chứa đồng thời nhiều ngôn ngữ.

Hệ thống không được yêu cầu người dùng tự dịch chứng từ trước khi upload.

---

# 8. SHIPMENT CONCEPT

Mỗi lần kiểm tra một bộ chứng từ được tổ chức dưới entity:

Shipment

Một Shipment có thể chứa:

- nhiều Invoice;
- nhiều Packing List;
- nhiều PO;
- nhiều vận đơn;
- nhiều C/O;
- nhiều file khác nhau.

Không giả định:

1 Shipment = 1 Invoice.

---

# 9. DOCUMENT INGESTION

Khi file được upload, hệ thống phải tạo một SourceDocument.

SourceDocument tối thiểu chứa:

- document_id
- original_filename
- file_type
- file_hash
- upload_time
- processing_status
- detected_document_type
- classification_confidence
- page_count hoặc sheet_count nếu có
- parser_used
- extraction_status

File hash được sử dụng để phát hiện duplicate và cache.

---

# 10. DOCUMENT CLASSIFICATION

Hệ thống phải xác định document type trước khi extraction chuyên sâu nếu có thể.

Output ví dụ:

{
  "document_type": "COMMERCIAL_INVOICE",
  "confidence": 0.97
}

Nếu không chắc chắn:

{
  "document_type": "UNKNOWN",
  "confidence": 0.43
}

Không ép phân loại khi evidence yếu.

---

# 11. DATA EXTRACTION

Extraction phải lấy dữ liệu theo nghĩa của chứng từ, không phụ thuộc vị trí cố định.

Ví dụ với Invoice:

- invoice_number
- invoice_date
- seller
- buyer
- ship_to
- currency
- incoterm
- payment_term
- total_amount
- freight
- insurance
- discount
- item list

Item có thể chứa:

- item_number
- item_code
- part_number
- model
- description
- brand
- manufacturer
- quantity
- unit
- unit_price
- amount
- origin
- weight
- package information

Không yêu cầu mọi field phải tồn tại.

Field không tồn tại phải để null / missing thay vì tự suy đoán.

---

# 12. PACKING LIST EXTRACTION

Packing List có thể chứa:

- packing_list_number
- date
- seller
- buyer
- shipment reference
- invoice reference
- package count
- package type
- gross weight
- net weight
- dimensions
- volume
- item list

Item có thể chứa:

- item_code
- description
- quantity
- unit
- package number
- gross weight
- net weight

---

# 13. TRANSPORT DOCUMENT EXTRACTION

Bill of Lading / AWB có thể chứa:

- document_number
- shipper
- consignee
- notify_party
- vessel
- voyage
- flight
- port_of_loading
- port_of_discharge
- place_of_receipt
- place_of_delivery
- ETD
- ETA
- package_count
- package_type
- gross_weight
- volume
- container_number
- seal_number
- freight_term

Không bắt buộc tất cả field phải tồn tại.

---

# 14. CUSTOMS DECLARATION DATA

Hệ thống phải có khả năng nhận dữ liệu tờ khai từ:

- PDF;
- Excel;
- exported data;
- structured form;
- manual input.

Các nhóm dữ liệu có thể gồm:

- declaration_type
- customs office
- importer
- exporter
- invoice information
- transport information
- currency
- exchange rate
- delivery term
- value
- freight
- insurance
- item lines
- HS code
- origin
- quantity
- unit
- tax-related fields
- permit / policy information

Chi tiết schema sẽ được định nghĩa riêng.

---

# 15. NORMALIZATION

Các dữ liệu tương đương phải được chuyển về format chuẩn.

Ví dụ:

"1,000 PCS"

"1000 pcs"

"1.000 PCS"

sau khi hiểu đúng locale có thể normalize thành:

quantity = 1000

unit = "PCS"

Tuy nhiên phải giữ raw value.

---

# 16. DATE NORMALIZATION

Hệ thống phải xử lý nhiều format:

2026-09-08

08/09/2026

Sep 8, 2026

08 SEP 2026

2026年9月8日

Normalized format ưu tiên:

YYYY-MM-DD

Nếu ngày mơ hồ:

03/04/2026

và không đủ context xác định là 3 April hay 4 March:

NEEDS_REVIEW.

Không tự đoán.

---

# 17. NUMBER NORMALIZATION

Phải hỗ trợ:

1,000.50

1.000,50

1000.50

1000,50

Hệ thống phải xác định decimal separator bằng context.

Nếu không đủ cơ sở:

NEEDS_REVIEW.

---

# 18. UNIT NORMALIZATION

Ví dụ:

PCS
PC
PIECE
PIECES
个
件

có thể map về normalized unit phù hợp.

Tuy nhiên không được tự coi:

PCS = SET

hoặc:

KG = PCS.

Unit mapping phải cấu hình được.

---

# 19. CURRENCY NORMALIZATION

Các biểu diễn như:

USD
US$
$
USD Dollars

có thể normalize về:

USD

nhưng ký hiệu "$" đơn lẻ có thể không đủ evidence để xác định currency trong mọi trường hợp.

Nếu không chắc:

NEEDS_REVIEW.

---

# 20. PARTY NORMALIZATION

Party có thể gồm:

- exporter
- seller
- shipper
- importer
- buyer
- consignee
- notify party
- manufacturer

Hệ thống không được mặc định:

Seller = Shipper

hoặc:

Buyer = Consignee

trong mọi trường hợp.

Có thể so sánh và cảnh báo nhưng phải giữ role riêng.

---

# 21. ITEM MATCHING

Hệ thống phải ghép item giữa các chứng từ.

Ưu tiên evidence:

1. item code
2. part number
3. model
4. SKU
5. exact description
6. quantity/unit
7. semantic similarity

Item order không được dùng làm bằng chứng duy nhất.

Ví dụ:

Invoice:

1. Motor
2. Cable
3. Sensor

Packing List:

1. Cable
2. Sensor
3. Motor

Hệ thống vẫn phải có khả năng match đúng.

---

# 22. ITEM MATCH CONFIDENCE

Matching phải có confidence hoặc trạng thái tương đương.

Ví dụ:

EXACT_MATCH

HIGH_CONFIDENCE_MATCH

POSSIBLE_MATCH

UNMATCHED

Nếu chỉ dựa vào semantic similarity yếu:

không được tự tạo exact match.

---

# 23. CROSS-DOCUMENT VALIDATION

Hệ thống phải hỗ trợ kiểm tra giữa nhiều chứng từ.

Ví dụ:

Invoice ↔ Packing List

Invoice ↔ Bill

Packing List ↔ Bill

Invoice ↔ Customs Declaration

Packing List ↔ Customs Declaration

Bill ↔ Customs Declaration

C/O ↔ Invoice

C/O ↔ Declaration

---

# 24. BASIC CHECKS

V1 nên hỗ trợ tối thiểu các nhóm check sau.

## 24.1 Document Presence

Ví dụ:

- có Invoice không;
- có Packing List không;
- có Bill/AWB không;
- loại hình này yêu cầu document nào theo rule nội bộ.

---

## 24.2 Invoice Number

So sánh:

- Invoice;
- Packing List reference;
- C/O reference;
- Declaration.

---

## 24.3 Invoice Date

Kiểm:

- format;
- consistency;
- chronology nếu có rule.

---

## 24.4 Party Information

So sánh:

- seller;
- buyer;
- shipper;
- consignee;
- exporter;
- importer.

Không chỉ exact string.

Có thể normalize:

CÔNG TY TNHH ABC

ABC CO., LTD.

nhưng fuzzy match phải có threshold và evidence.

---

## 24.5 Quantity

So sánh:

- Invoice quantity;
- Packing List quantity;
- Declaration quantity.

Phải xét:

- unit;
- item matching;
- aggregation;
- conversion rule nếu có.

Không chỉ so con số.

---

## 24.6 Amount

Kiểm:

item amount ≈ quantity × unit price

Invoice total ≈ tổng item amount

Sai số rounding phải configurable.

---

## 24.7 Currency

So sánh currency giữa các nguồn liên quan.

---

## 24.8 Weight

So sánh:

- Packing List gross weight;
- Bill gross weight;
- Declaration gross weight.

Tolerance phải configurable.

---

## 24.9 Packages

So sánh:

- number of packages;
- package type;
- bill;
- packing list;
- declaration.

---

## 24.10 Description

Hệ thống có thể cảnh báo:

- mô tả quá ngắn;
- khác đáng kể giữa Invoice và Declaration;
- thiếu model;
- thiếu material;
- thiếu usage;
- thiếu specification;

nếu rule tương ứng tồn tại.

Các check ngữ nghĩa nên ưu tiên WARNING thay vì ERROR khi không có rule chắc chắn.

---

# 25. DECLARATION TYPE

Người dùng phải có thể:

- chọn loại hình;
- hoặc để hệ thống đề xuất.

Trong V1, lựa chọn của người dùng được ưu tiên.

Ví dụ:

E11
E13
E15
E21
E31
A11
A12
A41
B11

Danh sách chính xác và rule sẽ được quản lý riêng.

AI không được tự thay đổi loại hình người dùng đã xác nhận.

---

# 26. RULES BY DECLARATION TYPE

Mỗi loại hình có thể kích hoạt checklist khác nhau.

Ví dụ logic khái niệm:

E13

→ Rule group A
→ Rule group B
→ Rule group C

A11

→ Rule group A
→ Rule group D
→ Rule group E

Không hard-code toàn bộ logic loại hình trực tiếp vào UI.

---

# 27. CUSTOMER PROFILE

Hệ thống có thể hỗ trợ Customer Profile.

Ví dụ:

Customer A thường có:

- Invoice
- PL
- AWB
- file Excel nội bộ

Customer B thường có:

- Invoice
- PL
- Bill
- Contract

Customer profile có thể định nghĩa:

- document expectation;
- naming convention;
- internal checks;
- tolerance;
- mappings;
- preferred output.

Customer-specific rule không được tự biến thành legal rule.

---

# 28. MASTER DATA

Hệ thống phải có khả năng sử dụng master data hàng hóa.

Master có thể chứa:

- item code
- description
- HS code history
- unit
- brand
- model
- material
- usage
- manufacturer
- origin
- customer
- previous declaration data

Master dùng để hỗ trợ:

- item matching;
- description suggestion;
- anomaly detection;
- historical comparison;
- HS candidate retrieval.

Không coi master là nguồn tuyệt đối chính xác.

---

# 29. HISTORICAL CHECK

Hệ thống có thể cảnh báo:

"Mặt hàng ITEM-001 trước đây thường khai HS 8501..., nhưng bộ hiện tại đang dùng 8537..."

Đây là:

WARNING / HISTORICAL_DIFFERENCE

không tự động kết luận mã hiện tại sai.

---

# 30. LEGAL KNOWLEDGE

Legal knowledge không thuộc V1 core document checker.

Architecture phải cho phép mở rộng về sau.

Legal module có thể sử dụng:

- verified documents;
- official sources;
- internal legal database;
- retrieval.

Không dùng knowledge của LLM làm bằng chứng duy nhất.

---

# 31. CHECK RESULT MODEL

Mỗi check nên tạo một CheckResult.

Ví dụ:

{
  "check_id": "CHK-000123",
  "rule_id": "QTY_MATCH_001",
  "status": "ERROR",
  "severity": "HIGH",
  "title": "Quantity mismatch",
  "message": "Invoice quantity differs from Packing List quantity.",
  "evidence": [
    {
      "document": "INV001.pdf",
      "page": 1,
      "value": "1000 PCS"
    },
    {
      "document": "PL001.pdf",
      "page": 1,
      "value": "980 PCS"
    }
  ]
}

---

# 32. RESULT STATUS

Supported states:

PASS

ERROR

WARNING

MISSING

NOT_CHECKED

NEEDS_REVIEW

INSUFFICIENT_EVIDENCE

---

# 33. REPORT

Sau khi check, hệ thống phải tạo report dễ đọc.

Ví dụ:

CUSTOMS DOCUMENT CHECK REPORT

Shipment:
ABC-2026-001

Declaration Type:
E13

Documents:
5

Checks:
42

PASS:
35

ERROR:
2

WARNING:
3

MISSING:
1

NEEDS REVIEW:
1

---

# 34. ERROR REPORT

Mỗi ERROR phải trả lời:

- lỗi gì;
- liên quan item nào;
- giá trị nào khác nhau;
- lấy từ file nào;
- page/sheet nào;
- rule nào tạo lỗi;
- severity.

---

# 35. WARNING REPORT

WARNING phải giải thích tại sao hệ thống nghi ngờ.

Ví dụ:

WARNING — Product description difference

Invoice:
AC MOTOR

Declaration:
Electric motor for CNC machine

Reason:
Descriptions are semantically related but not equivalent enough for automatic PASS.

Action:
Review description manually.

---

# 36. PASS

PASS chỉ được tạo khi phép check thực sự đã chạy.

Không được coi:

"không tìm thấy lỗi"

đồng nghĩa:

"PASS".

Nếu check chưa chạy:

NOT_CHECKED.

---

# 37. EVIDENCE NAVIGATION

Mục tiêu UI tương lai:

Người dùng click vào evidence:

INV001.pdf — Page 2

và hệ thống mở đúng vị trí liên quan.

V1 có thể chỉ cần hiển thị:

filename + page/sheet.

---

# 38. HUMAN CORRECTION

Người dùng phải có khả năng sửa extraction.

Ví dụ:

AI đọc:

8,000 PCS

Người dùng sửa:

6,000 PCS

Sau khi sửa:

- giữ raw extraction;
- ghi human correction;
- re-run affected checks;
- không cần xử lý lại toàn bộ file nếu không cần.

---

# 39. HUMAN CONFIRMATION

Người dùng có thể xác nhận:

- document type;
- extracted field;
- item matching;
- declaration type;
- check result.

Human-confirmed value phải được đánh dấu rõ.

---

# 40. RECHECK

Sau khi:

- sửa field;
- thay file;
- upload revised invoice;
- đổi declaration type;

người dùng có thể chạy lại check.

Hệ thống chỉ nên reprocess phần bị ảnh hưởng nếu có thể.

---

# 41. DUPLICATE DOCUMENT

Nếu upload lại file giống hệt:

file_hash giống nhau

hệ thống phải phát hiện duplicate.

Không gọi extraction model lại nếu cache hợp lệ.

---

# 42. REVISED DOCUMENT

Nếu file khác hash nhưng:

- invoice number giống;
- document type giống;
- content gần giống;

hệ thống có thể cảnh báo:

POSSIBLE_REVISED_DOCUMENT.

Người dùng quyết định file active.

---

# 43. V1 USER INTERFACE

UI V1 không cần phức tạp.

Tối thiểu cần:

1. Create Shipment
2. Upload Documents
3. Select Declaration Type
4. Process Documents
5. View Extracted Data
6. Run Checks
7. View Report
8. Correct Extraction
9. Re-run Checks

---

# 44. V1 REPORT VIEW

Nên hiển thị theo nhóm:

Summary

Documents

Errors

Warnings

Missing Data

Checks Passed

Items

Raw Extraction / Evidence

---

# 45. SEARCH

Không bắt buộc ở bản đầu tiên.

Architecture nên cho phép tìm kiếm theo:

- shipment;
- invoice number;
- customer;
- item code;
- HS code;
- date.

---

# 46. EXPORT

V1 nên hướng tới khả năng export:

- JSON
- Excel

PDF report có thể làm sau.

---

# 47. COST TARGET

Mục tiêu kiến trúc:

Không phụ thuộc vào subscription ChatGPT/Gemini để production hoạt động.

Production có thể chạy bằng:

- local code;
- database;
- API model theo usage.

Mọi AI call phải có lý do.

---

# 48. MODEL STRATEGY

Model nhỏ/rẻ:

- document classification;
- straightforward extraction;
- simple semantic normalization.

Model mạnh:

- difficult extraction;
- ambiguous item matching;
- semantic reasoning;
- complex anomaly analysis.

Không gọi model mạnh mặc định.

---

# 49. FALLBACK

Nếu model nhỏ thất bại:

small model

→ retry hợp lý

→ stronger model nếu policy cho phép

→ NEEDS_REVIEW

Không fallback vô hạn.

---

# 50. LOCAL-FIRST OPPORTUNITIES

Khi khả thi, ưu tiên xử lý local cho:

- Excel parsing;
- PDF text extraction;
- hashing;
- arithmetic;
- normalization;
- validation;
- rule engine;
- database lookup.

LLM chỉ nhận phần dữ liệu cần thiết.

---

# 51. PRODUCTION DATA

Không dùng chứng từ thực tế trong public GitHub repo.

`test_documents/` trong repo public chỉ chứa:

- synthetic documents;
- anonymized documents;
- documents được phép sử dụng.

Dữ liệu production phải nằm ngoài source repository.

---

# 52. NON-GOALS OF V1

V1 KHÔNG cần:

- tự động truyền tờ khai VNACCS;
- tự ký số;
- tự nộp thuế;
- tự quyết định HS code cuối cùng;
- tự đưa ra kết luận pháp lý cuối cùng;
- tự động gửi email khách hàng;
- autonomous multi-agent swarm;
- Kubernetes;
- microservices;
- mobile app.

---

# 53. V1 FUNCTIONAL SCOPE

V1 tập trung vào:

A. Upload chứng từ

B. Document classification

C. Data extraction

D. Canonical normalization

E. Item matching

F. Cross-document checks

G. Rule execution

H. Report

I. Evidence

J. Human correction

---

# 54. V1 INITIAL DOCUMENT SCOPE

Ưu tiên triển khai đầu tiên:

1. Commercial Invoice
2. Packing List
3. Bill of Lading / AWB
4. Customs Declaration / declaration data

Sau khi ổn định:

5. Contract / PO
6. C/O
7. Catalogue / Specification

---

# 55. V1 INITIAL CHECK SCOPE

Ưu tiên đầu tiên:

- document presence;
- invoice number;
- invoice date;
- parties;
- item code;
- model;
- quantity;
- unit;
- unit price;
- item amount;
- total amount;
- currency;
- package count;
- gross weight;
- net weight;
- basic item description difference.

Không triển khai toàn bộ pháp luật hải quan ngay trong V1.

---

# 56. V1 DEVELOPMENT PHASES

## Phase 1 — Foundation

- project structure
- configuration
- canonical schema
- document model
- test framework
- logging

## Phase 2 — Ingestion

- upload
- validation
- hashing
- file storage
- parser routing

## Phase 3 — Classification

- document classification
- confidence
- manual override

## Phase 4 — Extraction

- Invoice
- Packing List
- Bill/AWB

## Phase 5 — Normalization

- date
- number
- currency
- quantity
- unit
- parties

## Phase 6 — Matching

- document relationships
- item matching

## Phase 7 — Rule Engine

- rule model
- rule execution
- result generation

## Phase 8 — Report

- summary
- error
- warning
- evidence

## Phase 9 — Human Correction

- edit extracted values
- rerun checks

## Phase 10 — Real Test Dataset

- anonymized customer samples
- regression test
- accuracy evaluation

---

# 57. ACCEPTANCE TARGET — V1

V1 phải đạt được luồng:

Upload:

Invoice.pdf
PackingList.xlsx
Bill.pdf

↓

System detects:

Invoice
Packing List
Bill

↓

System extracts:

Shipment-level data
Item-level data

↓

System matches items

↓

System checks:

quantity
amount
currency
weight
packages
selected fields

↓

System returns:

PASS
ERROR
WARNING
MISSING
NEEDS_REVIEW

↓

User can inspect evidence.

---

# 58. SAMPLE USER EXPERIENCE

User:

Upload 3 files.

Select:

Declaration Type = E13

Press:

CHECK

System:

Processing 3 documents...

Result:

42 checks completed

2 ERROR
3 WARNING
1 MISSING
36 PASS

Example:

ERROR — Quantity mismatch

Item:
ABG-1012H1

Invoice:
100 PCS

Packing List:
90 PCS

Evidence:
Invoice_001.pdf — page 1
Packing_List.xlsx — Sheet1

---

# 59. FUTURE PHASES

Sau V1 có thể mở rộng:

## V2

- declaration type-specific checklist
- customer profiles
- master data integration

## V3

- HS code assistance
- historical declaration comparison
- product description assistant

## V4

- legal document retrieval
- policy checking
- tax / permit warning

## V5

- declaration preparation
- Excel auto-fill
- internal workflow integration

## V6

- optional advanced automation
- email intake
- automated job processing
- approval workflow

---

# 60. PRODUCT PRINCIPLE

Customs AI Checker không được cố trở thành "AI biết tất cả".

Nó phải trở thành:

"một checker đáng tin cậy, có bằng chứng, biết khi nào cần gọi con người."

Ưu tiên:

correctness

→ traceability

→ usability

→ speed

→ cost

→ advanced AI features.

---

# END OF MASTER SPECIFICATION
