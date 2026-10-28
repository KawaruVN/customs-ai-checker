# TASK-006A — Extraction Foundation

Status: DONE  
Priority: P1  
Parent: TASK-006  
Owner: Antigravity — Main Developer  
Reviewer: Codex — Technical Reviewer / QA  
Created: 2026-09-11  
Completed: 2026-10-28  
Merged PR: #1 (commit `02a748e`)  
Dependencies: TASK-001..TASK-005A DONE  
Authoritative pre-task baseline: 178 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 207 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. OBJECTIVE

Create the small, reusable foundation required by later Invoice extraction tasks.

TASK-006A is deliberately limited to:

```text
typed extraction primitives
+ alias configuration
+ strict lexical parsing
```

It must NOT extract any document yet.

---

## 2. IN SCOPE

### A. Extraction enums / issue models

Provide strict models for concepts needed by later tasks, for example:

```text
ExtractionStatus:
- EXTRACTED
- NEEDS_REVIEW
- FAILED
```

and a typed issue model with at least:

```text
code
message
field_path optional
is_review_required
```

Messages must be safe and must not contain raw customer values.

### B. Generic source-grounded candidate primitive

If a reusable candidate model is introduced, it must support source evidence such as:

```text
field_path
raw_value
source_document_id
page
sheet
cell
confidence
extraction_method
```

It must remain provider-neutral.

Do NOT create an alternate canonical Invoice schema.

### C. Invoice alias configuration

Create a CWD-independent config file for approved canonical paths.

Header paths must cover:

```text
invoice_number
invoice_date
seller.name
seller.tax_id
seller.address
buyer.name
buyer.tax_id
buyer.address
ship_to.name
ship_to.address
currency
incoterm
payment_term
total_amount
freight
insurance
discount
```

Item paths must cover:

```text
item_number
item_code
part_number
model
description
brand
manufacturer
quantity
unit
unit_price
amount
origin
weight
package_information
```

Config validation must:

- reject unknown field paths;
- reject empty alias lists;
- reject blank aliases;
- reject exact duplicate aliases that conflict inside the same extraction context;
- normalize aliases deterministically for validation;
- remain customer-neutral;
- allow EN/VI/ZH aliases;
- not claim to solve document matching itself.

Prefix overlap such as `SELLER` / `SELLER ADDRESS` may remain allowed because TASK-006B owns the actual longest/specific label resolver. Document this explicitly.

### D. Strict lexical Decimal parser

Implement a conservative helper for minimum typed conversion.

Required behavior:

```text
"1200"       -> Decimal("1200")
"1200.50"    -> Decimal("1200.50")
"12,5"       -> Decimal("12.5")
"1,200.50"   -> Decimal("1200.50")
"1.200,50"   -> Decimal("1200.50")

"1,200"      -> None
"1.200"      -> None
"1,200,000"  -> None
"=B4*C4"     -> None
"abc1200"    -> None
"USD 1200"   -> None unless a documented whole-token grammar explicitly supports it
```

Do not strip arbitrary non-numeric text and parse whatever digits remain.

### E. Strict lexical date parser

Safe explicit forms may include:

```text
YYYY-MM-DD
YYYY/MM/DD
YYYY.MM.DD
```

Ambiguous day/month forms such as:

```text
01/02/2026
11-09-2026
```

must remain unresolved in TASK-006A unless an unambiguous policy exists.

---

## 3. OUT OF SCOPE

Do NOT implement any of the following:

- PDF header extraction;
- Excel header extraction;
- InvoiceItem table detection;
- document parsing orchestration;
- TASK-005A vision orchestration;
- InvoiceExtractionService;
- semantic/AI provider protocol;
- semantic candidate merge;
- SQLite extraction table;
- extraction history;
- SourceDocument status updates;
- re-extraction;
- composition factory;
- hosted AI/network;
- TASK-009 normalization;
- item matching;
- rules/checks;
- UI.

If implementation code starts needing `ParsedPdfDocument`, `ParsedWorkbook`, `DocumentParsingService`, repositories, or DB connections, the task has exceeded scope.

---

## 4. EXPECTED MODULES

Keep the module set small.

Likely:

```text
config/invoice_extraction.yaml

src/customs_ai/extraction/
    __init__.py
    enums.py
    models.py
    config.py
    mapper.py
```

Do not create empty future modules just to reserve names.

---

## 5. ACCEPTANCE CRITERIA

- AC-01: [PASS] extraction package imports successfully on Python 3.13.14.
- AC-02: [PASS] strict issue/status models reject undeclared fields where appropriate.
- AC-03: [PASS] config loads independent of current working directory.
- AC-04: [PASS] all approved header paths are accepted; party role boundaries strictly maintained.
- AC-05: [PASS] all approved item paths are accepted.
- AC-06: [PASS] unknown paths are rejected.
- AC-07: [PASS] blank aliases are rejected.
- AC-08: [PASS] conflicting exact duplicate aliases inside the same context are rejected.
- AC-09: [PASS] header and item alias namespaces are validated intentionally, not accidentally coupled.
- AC-10: [PASS] numeric safe cases parse exactly to Decimal; non-finite Decimals rejected.
- AC-11: [PASS] `1,200`, `1.200`, and grouping-only ambiguous forms return None.
- AC-12: [PASS] formulas/arbitrary text do not become numbers.
- AC-13: [PASS] safe ISO-like dates parse; datetime safely converted to pure date.
- AC-14: [PASS] ambiguous day/month dates return None.
- AC-15: [PASS] no parser/repository/network dependency is introduced by TASK-006A.
- AC-16: [PASS] all pre-existing 178 tests remain green.
- AC-17: [PASS] final full suite result is exact: 207 passed, 2 warnings (178 baseline + 29 TASK-006A tests).

All 17/17 Acceptance Criteria verified PASS.

---

## 6. TEST REQUIREMENTS

Keep the test surface focused.

Target roughly 15–25 clear test items, not a huge synthetic suite.

Required groups:

### Models

- status enum values;
- strict issue model;
- confidence bounds if candidate confidence exists;
- extra fields rejected where intended.

### Config

- normal load;
- CWD independence;
- complete approved path coverage;
- unknown path rejection;
- empty alias rejection;
- blank alias rejection;
- duplicate conflict rejection;
- harmless reuse across separate header/item contexts behaves according to documented policy;
- party role separation guarantee (regression test).

### Decimal

- plain integer;
- plain decimal;
- decimal comma;
- US grouped + decimal;
- EU grouped + decimal;
- ambiguous single comma;
- ambiguous single dot;
- repeated grouping only;
- formula;
- arbitrary alphabetic text;
- non-finite Decimals (NaN, sNaN, Infinity);
- None / blank.

### Date

- YYYY-MM-DD;
- YYYY/MM/DD;
- YYYY.MM.DD;
- typed datetime (naive and timezone-aware) converted to pure date;
- invalid calendar date;
- ambiguous day/month;
- arbitrary text.

No document fixtures are needed.

---

## 7. VALIDATION EVIDENCE

Authoritative pytest commands and counts:

```text
python -m pytest tests/unit/extraction --collect-only -q  # 29 tests collected
python -m pytest --collect-only -q                       # 207 tests collected
python -m pytest -v                                      # 207 passed, 2 warnings in 3.54s
```

Detailed test metrics:
- Focused extraction tests: 29 passed, 0 failed, 0 skipped
- Pre-existing regression suite: 178 passed (100% green)
- Total suite: 207 passed, 0 failed, 0 skipped, 2 warnings (Starlette/httpx testclient deprecations)
- Environment: Windows, Python 3.13.14, pytest 9.1.1

---

## 8. DELIVERABLE

- `config/invoice_extraction.yaml`
- `src/customs_ai/extraction/__init__.py`
- `src/customs_ai/extraction/enums.py`
- `src/customs_ai/extraction/models.py`
- `src/customs_ai/extraction/config.py`
- `src/customs_ai/extraction/mapper.py`
- `tests/unit/extraction/__init__.py`
- `tests/unit/extraction/test_config.py`
- `tests/unit/extraction/test_mapper.py`
- `tests/unit/extraction/test_models.py`

---

## 9. DEFINITION OF DONE

- [x] scope stayed within foundation only
- [x] extraction package primitives implemented
- [x] config implemented and validated
- [x] strict Decimal parser implemented
- [x] strict date parser implemented
- [x] focused tests added (29 tests)
- [x] pre-existing regression green (178/178 tests)
- [x] Codex APPROVE
- [x] Project Leader APPROVE

---

## 10. CLOSURE SUMMARY

- **Status**: CLOSED / DONE
- **Date**: 2026-10-28
- **Merged PR**: Pull Request #1 (`02a748e`)
- **Acceptance Criteria**: 17/17 PASS
- **Review Decision**: Codex — Technical Reviewer / QA — APPROVE
- **Architectural Approval**: ChatGPT — Project Leader / Architect — APPROVE
- **Baseline for TASK-006B**: 207 passed, 0 failed, 0 skipped, 2 warnings
