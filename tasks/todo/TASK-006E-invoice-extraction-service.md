# TASK-006E — Invoice Extraction Service

Status: TODO  
Priority: P1  
Parent: TASK-006  
Dependencies: TASK-006B DONE, TASK-006C DONE, TASK-006D DONE

## Objective

Compose the approved Invoice extraction components into the production application service.

## In scope

- primary input document_id;
- safely classified COMMERCIAL_INVOICE gate;
- non-mutating downstream parse/read path;
- TASK-005A visual safety gate;
- deterministic headers + items;
- provider-neutral semantic fallback interface;
- strict semantic grounding/type validation;
- conservative fill-only merge;
- deterministic conflicts remain sticky;
- unsafe visual conflict bypasses semantic fallback and goes directly to NEEDS_REVIEW;
- explicit safe re-extraction through TASK-006D policy;
- privacy-safe logs;
- production composition factory.

## Out of scope

- hosted AI/provider SDK;
- TASK-009 normalization;
- matching/rules;
- Packing/Bill extraction.

## Key acceptance

- unsafe visual document is never sent to semantic fallback;
- wrong semantic document/provenance/type -> typed issue + review;
- semantic cannot overwrite deterministic accepted values/conflicts;
- source file remains immutable;
- no parser status downgrade;
- no SQL in application service;
- full regression stays green.

Baseline is the exact approved TASK-006D full-suite result.
