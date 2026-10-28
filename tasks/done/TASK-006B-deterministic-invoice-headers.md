# TASK-006B — Deterministic Invoice Headers

Status: DONE  
Priority: P1  
Parent: TASK-006  
Owner: Antigravity — Main Developer  
Reviewer: Codex — Technical Reviewer / QA  
Created: 2026-09-11  
Completed: 2026-10-28  
Merged PR: #2 (commit `29c4da2`)  
Dependencies: TASK-006A DONE  
Authoritative pre-task baseline: 207 passed / 0 failed / 0 skipped / 2 warnings  
Post-task baseline: 249 passed / 0 failed / 0 skipped / 2 warnings (Python 3.13.14, pytest 9.1.1)

---

## 1. OBJECTIVE

Extract Commercial Invoice header and party fields deterministically from existing technical parser output:
- `ParsedPdfDocument`
- `ResolvedPdfDocument` (where source safety allows extraction)
- `ParsedWorkbook`

Map approved invoice header fields into existing canonical `Invoice`, `Party`, and `CanonicalField[T]` models with exact source provenance evidence.

---

## 2. IN SCOPE

- `ParsedPdfDocument` / `ResolvedPdfDocument` header fields.
- `ParsedWorkbook` header fields.
- Party: seller / buyer / ship_to (name, tax_id, address).
- Exact source `raw_value`.
- PDF page provenance.
- Excel sheet / cell provenance.
- Config-driven EN / VI / ZH aliases from TASK-006A (`config/invoice_extraction.yaml`).
- Longest / specific exact-key matching.
- Boundary scanning preserving identifiers and signs (negative amounts, leading dashes).
- Repeated-identical candidate deduplication without spurious conflict.
- Sticky conflicting-field detection (two-way and three-way).
- Stable documented confidence policy (0.95 for specific labels, 0.70 for generic labels).
- Strict boolean and native time rejection for numeric/date fields without invalid coercion.
- Conservative formula policy: formula cells and expression text are opaque, never serve as label sources, and formulas as values trigger `UNRESOLVED_FORMULA_FIELD` with `NEEDS_REVIEW`.
- Inline value span parsing (amounts, dates, zero, negative).
- Canonical `Invoice` mapping.

---

## 3. OUT OF SCOPE

- InvoiceItem tables (TASK-006C).
- DB / persistence (TASK-006D).
- Application service orchestration (TASK-006E).
- Semantic / hosted AI fallback.
- Hosted network dependencies.
- TASK-009 normalization.

---

## 4. KEY ACCEPTANCE CRITERIA (10/10 PASS)

1. [x] **DELIVERY DATE does not become invoice_date**: non-invoice dates terminate prior spans or are ignored; never mapped to invoice_date.
2. [x] **SELLER ADDRESS does not become seller.name**: party subfields remain separated; compound labels or addresses never conflate into names.
3. [x] **BUYER ADDRESS does not become buyer.name**: buyer address and name boundaries are strictly isolated.
4. [x] **PDF casing/raw source is preserved**: exact raw source casing, leading zeroes, negative signs, and identifiers are preserved.
5. [x] **Excel formula evidence is preserved conservatively**: formula cells and expression text never act as label sources; formula values are kept in candidate evidence and flagged as `UNRESOLVED_FORMULA_FIELD` with `NEEDS_REVIEW`.
6. [x] **Zero values are not dropped**: numeric zeroes (`0`, `0.0`, `"0"`, `"0.00"`) are cleanly preserved in both native and inline representations.
7. [x] **Three-way conflict remains unresolved**: conflicting values strictly trigger `CONFLICTING_FIELD_VALUES` with `is_review_required=True` regardless of 2-to-1 majority.
8. [x] **Missing fields remain None**: absent header fields remain `None` on the canonical Invoice without synthetic defaults.
9. [x] **No customer-specific fixed coordinates/row numbers**: all extraction relies purely on label matching, boundary scanning, and relative topological cell search.
10. [x] **Full regression stays green**: 249 passed, 0 failed, 2 warnings across the entire repository test suite.

---

## 5. VALIDATION EVIDENCE

Authoritative pytest commands and counts:

```text
python -m pytest tests/unit/extraction/test_headers.py -v  # 42 passed in 1.44s
python -m pytest tests/unit/extraction/ -v                # 71 passed in 1.75s
python -m pytest -v                                       # 249 passed, 2 warnings in 4.78s
```

Detailed test metrics:
- Focused header tests (`test_headers.py`): 42 passed, 0 failed, 0 skipped
- Pre-existing regression suite: 207 passed (100% green)
- Total suite: 249 passed, 0 failed, 0 skipped, 2 warnings (Starlette/httpx testclient and AnyIO BlockingPortal deprecations)
- Environment: Windows, Python 3.13.14, pytest 9.1.1

---

## 6. DELIVERABLES

- `src/customs_ai/extraction/headers.py` — Deterministic invoice header extractor implementation
- `src/customs_ai/extraction/models.py` — `CandidateTypedValue` union type and extraction result models
- `src/customs_ai/extraction/__init__.py` — Package exports
- `tests/unit/extraction/test_headers.py` — 42 comprehensive unit and probe regression tests

---

## 7. DEFINITION OF DONE

- [x] scope stayed within deterministic invoice headers and parties only
- [x] PDF header extraction implemented with provenance
- [x] Excel header extraction implemented with sheet/cell provenance
- [x] conservative formula policy enforced
- [x] boolean and native time rejection enforced
- [x] inline amount/date parsing implemented
- [x] 10/10 key acceptance criteria PASS
- [x] 42 focused tests added
- [x] pre-existing regression green (207/207 tests)
- [x] Codex APPROVE
- [x] Project Leader APPROVE

---

## 8. CLOSURE SUMMARY

- **Status**: CLOSED / DONE
- **Date**: 2026-10-28
- **Merged PR**: Pull Request #2 (`29c4da2`)
- **Key Acceptance**: 10/10 PASS
- **Review Decision**: Codex — Technical Reviewer / QA — APPROVE
- **Architectural Approval**: Project Leader — APPROVE
- **Baseline for TASK-006C**: 249 passed, 0 failed, 0 skipped, 2 warnings
