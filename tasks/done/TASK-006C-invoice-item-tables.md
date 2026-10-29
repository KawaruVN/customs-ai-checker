# TASK-006C — Invoice Item Tables

Status: DONE  
Priority: P1  
Parent: TASK-006  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Created: 2026-09-11  
Completed: 2026-10-28  
Merged PR: #3 (commit `8bbb7f8`)  
Dependencies: TASK-006B DONE  
Authoritative pre-task baseline: 249 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 291 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. OBJECTIVE

Extract `InvoiceItem` rows conservatively from generic Excel item tables (`ParsedWorkbook`) with explicit provenance, strict boundary detection, and clear abstention policies without parsing, calculation, semantic guessing, or external orchestration.

---

## 2. IN SCOPE

- Table-header candidate discovery at arbitrary row/column positions across worksheets.
- Approved item aliases from `config/invoice_extraction.yaml` across English, Vietnamese, and Chinese.
- Identity/content (`description`, `item_code`, `part_number`, `model`) and quantitative/numeric (`quantity`, `unit_price`, `amount`, `weight`) header requirements (`NO + QTY` alone is insufficient).
- Grounded body product identity requirement (descriptions made solely of numbers do not certify a table; native numeric item codes supported).
- Sheet and cell provenance per canonical field (`source_document_id`, `sheet`, `coordinate`, `confidence=0.95`).
- Conservative formula policy: formula cells and expression text are opaque, never serve as header sources; formula values remain `None` on canonical items, flag `UNRESOLVED_ITEM_FORMULA` with `NEEDS_REVIEW`, and retain raw expressions in candidate evidence.
- Explicit zero values (`0`, `0.0`, `"0"`, `"0.00"`) preserved without falsy dropping.
- Blank-business-row and implicit gap termination (unrelated note columns do not bridge gaps).
- Material hidden rows omitted with `HIDDEN_ITEM_ROW` review issue; hidden table headers flag `HIDDEN_ITEM_HEADER`; mapped hidden columns cause abstention (`HIDDEN_ITEM_COLUMN`); hidden worksheets flag `HIDDEN_ITEM_TABLE`.
- Summary row termination (`TOTAL`, `GRAND TOTAL`, `TỔNG CỘNG`, `合计`, etc.) and subtotal handling (`SUBTOTAL`, `小计` flag `ITEM_SUBTOTAL_BOUNDARY`).
- Product safety preserving product names starting with TOTAL (`TOTALIZER`, `TOTAL CONTROL`, `TOTAL LOSS`).
- Multi-table and cross-sheet ambiguity: competing credible tables produce `MULTIPLE_ITEM_TABLES` and abstain without guessing or arbitrary concatenation.
- Contiguous repeated identical headers continue table regions.
- Incomplete relevant rows remain partial canonical items with `INCOMPLETE_ITEM_ROW` review flag.
- Output mapping to canonical `InvoiceItem` models and `InvoiceItemExtractionResult` (`extra="forbid"`).

---

## 3. OUT OF SCOPE

- PDF spacing-based item guessing (TASK-006D / future).
- Database / extraction persistence (TASK-006D).
- Application service orchestration (TASK-006E).
- Semantic / hosted AI fallback.
- Matching / customs verification rules.
- TASK-009 semantic normalization.

---

## 4. KEY ACCEPTANCE CRITERIA (10/10 PASS)

1. [x] **No fixed customer row/column positions**: Tables are discovered at arbitrary row and column coordinates across visible sheets.
2. [x] **Conservative table discovery**: Requires both identity and numeric column evidence; body must establish grounded identity.
3. [x] **Unsafe multi-table situations require review**: Competing tables within the same sheet or across visible sheets abstain with `MULTIPLE_ITEM_TABLES`.
4. [x] **Hidden rows and sheets do not silently become items**: Material hidden rows are omitted with `HIDDEN_ITEM_ROW`; hidden tables flag `HIDDEN_ITEM_TABLE`.
5. [x] **Blank business rows terminate table**: Implicit row gaps and blank business rows terminate the table region; unrelated note columns cannot bridge gaps.
6. [x] **Summary and subtotal boundaries are strictly isolated**: Exact totals terminate regions; subtotals flag `ITEM_SUBTOTAL_BOUNDARY`; products starting with TOTAL (`TOTALIZER`, etc.) are preserved.
7. [x] **Formula quarantine**: Formula cells and expression text cannot supply headers; formula values in rows remain `None` with `UNRESOLVED_ITEM_FORMULA`. Cached displayed values are not blindly trusted.
8. [x] **Source raw and provenance preserved**: Exact raw representations, casing, leading zeroes, negative numbers, and cell coordinates are maintained across all 14 canonical fields.
9. [x] **Incomplete rows retained safely**: Incomplete rows are preserved as partial canonical items with `INCOMPLETE_ITEM_ROW` rather than dropped or fabricated.
10. [x] **Full regression stays green**: 291 passed, 0 failed, 2 warnings across the entire repository test suite.

---

## 5. VALIDATION EVIDENCE

Authoritative pytest commands and counts:

```text
python -m pytest tests/unit/extraction/test_items.py -v    # 42 passed in 1.26s
python -m pytest tests/unit/extraction/ -v                # 113 passed in 2.80s
python -m pytest -v                                       # 291 passed, 2 warnings in 5.42s
```

Detailed test metrics:
- Focused item table tests (`test_items.py`): 42 passed, 0 failed, 0 skipped
- Pre-existing regression suite: 249 passed (100% green)
- Total suite: 291 passed, 0 failed, 0 skipped, 2 warnings (Starlette/httpx testclient and AnyIO BlockingPortal deprecations)
- Independent probe suite: 42 distinct probes passed (0.032s on 500-item stress test)
- Environment: Windows, Python 3.13.14, pytest 9.1.1

---

## 6. DELIVERABLES

- `src/customs_ai/extraction/items.py` — Deterministic invoice item table extractor implementation (`DeterministicInvoiceItemExtractor`, `extract_invoice_items`).
- `src/customs_ai/extraction/models.py` — `InvoiceItemExtractionResult` model with strict `extra="forbid"`.
- `src/customs_ai/extraction/__init__.py` — Package exports (`DeterministicInvoiceItemExtractor`, `extract_invoice_items`, `InvoiceItemExtractionResult`).
- `tests/unit/extraction/test_items.py` — 42 comprehensive unit and integration tests.

---

## 7. DEFINITION OF DONE

- [x] Scope stayed within deterministic Excel item tables only
- [x] Table header discovery implemented with identity + numeric constraints
- [x] Grounded product identity in body enforced
- [x] Contiguous identical repeated headers supported
- [x] Blank business row and implicit gap termination enforced
- [x] Hidden rows, columns, and sheets handled conservatively
- [x] Exact summary tokens vs TOTAL-prefixed products distinguished
- [x] Conservative formula policy enforced
- [x] 10/10 key acceptance criteria PASS
- [x] 42 focused tests added
- [x] Pre-existing regression green (249/249 tests)
- [x] Antigravity independent review: APPROVE
- [x] Project Leader final technical approval: APPROVE

---

## 8. CLOSURE SUMMARY

- **Status**: CLOSED / DONE
- **Date**: 2026-10-28
- **Merged PR**: Pull Request #3 (commit `8bbb7f8`)
- **Key Acceptance**: 10/10 PASS
- **Developer**: Codex — Main Developer
- **Review Decision**: Antigravity — Independent Technical Reviewer / QA — APPROVE
- **Architectural Approval**: Project Leader — APPROVE
- **Baseline for TASK-006D**: 291 passed, 0 failed, 0 skipped, 2 warnings
