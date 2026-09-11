# TASK-006C — Invoice Item Tables

Status: TODO  
Priority: P1  
Parent: TASK-006  
Dependencies: TASK-006B DONE

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
