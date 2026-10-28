# TASK-006C — Invoice Item Tables

Status: IN_PROGRESS  
Priority: P1  
Parent: TASK-006  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Updated: 2026-10-28  
Dependencies: TASK-006B DONE  
Authoritative pre-task baseline: 249 passed / 0 failed / 0 skipped / 2 warnings.

## Objective

Extract InvoiceItem rows conservatively from generic Excel item tables.

## In scope

- table-header candidate discovery;
- approved item aliases;
- identity/content + quantitative/value header evidence;
- sheet/cell provenance per field;
- formulas with raw formula provenance and safe cached/displayed values;
- explicit zero values;
- blank-business-row termination;
- hidden sheet/row policy;
- TOTAL/SUBTOTAL/GRAND TOTAL exact summary-row handling;
- TOTALIZER / TOTAL CONTROL / TOTAL LOSS product safety;
- multi-table / multi-sheet ambiguity;
- canonical InvoiceItem output.

## Out of scope

- PDF spacing-based item guessing;
- persistence;
- semantic fallback;
- application service;
- matching/rules.

## Key acceptance

- no fixed customer row/column positions;
- unsafe two-table situations require review;
- hidden rows do not silently become items;
- unrelated note columns do not keep a table alive across a blank business row;
- source raw/provenance preserved;
- full regression stays green.

Baseline is the exact approved TASK-006B full-suite result.

## Implementation policies for independent review

- API: `extract_invoice_items(ParsedWorkbook, config=None)` / `DeterministicInvoiceItemExtractor.extract()`; result `InvoiceItemExtractionResult` contains canonical items, status, safe typed issues and candidates. No canonical schema change.
- Whole-cell configured aliases are normalized for case/whitespace; an optional final colon is allowed. Product identity/content requires description, item code, part number or model; numeric headers require quantity, unit price, amount or weight. NO + QTY alone is insufficient. Grounded product identity must also exist in the body before publishing items; a description made solely of numbers is not identity evidence (explicit native numeric item codes remain supported).
- Duplicate/compound/merged column interpretation and mapped hidden columns cause abstention. Two separated header-column blocks, each independently containing identity and numeric evidence, also cause abstention even if their field paths differ. Header position and sheet position are not fixed.
- A missing/blank business row ends the region even when unrelated note columns contain text. Contiguous repeated headers with identical column signatures are supported. No cross-sheet or separated-table continuation is inferred; competing credible tables produce no item list and require review.
- Only visible sheets are eligible. Hidden table headers/worksheets with table evidence produce review issues. Material hidden rows within an active region are omitted with review. A hidden summary/footer or different hidden header stops the region. Hidden content is never appended silently.
- Summary comparison uses exact EN/VI/ZH tokens and configured header total-amount aliases, never TOTAL prefixes. A summary marker plus amount alone terminates the region. A marker with independent product identity remains an item with review; other product-like summary cases preserve evidence and stop unresolved. SUBTOTAL ends the section with review; sections are not automatically joined.
- Incomplete relevant rows remain partial canonical items with review. Ambiguous boundary/footer rows retain candidates and stop rather than being fabricated into items.
- Raw evidence is `str(cell.raw_value)` without trimming; string conversion uses a separate copy. Native finite numerics convert to Decimal locally; boolean/date/time are not numeric facts. Plain zero-padding identifier formats (`000...`) are interpreted only for integral native identifiers; other formats are not reconstructed.
- Formula cells and expression text cannot provide headers. All formula values retain their full expression in candidates, leave the canonical field None and require review. Cached/displayed formula results are deliberately not used in this task.
- `EXTRACTED` means one unambiguous supported region with no review issue; it does not certify that optional/missing business fields are complete or that business checks have run.

## Review state

Implementation and test evidence are to be independently reviewed by Antigravity. This task is not approved or DONE by the developer.
