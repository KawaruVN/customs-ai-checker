# ADR-003 — Packing service and discriminated persistence

Date: 2026-10-29  
Status: Accepted (Reviewed and approved by Antigravity; approved by Project Leader; merged via PR #10, commit `f52ef033225a73aa57bca18cb7c336f66045e0a0`)  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Decision: Approved by Project Leader in the TASK-007D handoff  
Implementation: Implemented, independently reviewed, approved, and merged in PR #10

## Context and decision

Compose TASK-007A/B/C through a Packing-specific application service. Reuse the
existing document_extractions table and transaction engine. No canonical schema,
SQLite columns, constraints, indexes, foreign keys or DDL migration are changed.
schema_version remains 0.1; it is separate from the JSON codec format_version.

The exact wire pairs are (1, invoice), (1, invoice_items), (2, packing_list).
Packing v2 stores the existing PackingListHeaderExtractionResult with composed
items; standalone PackingItemExtractionResult is not a storage envelope. Keep
explicit candidate type tags, Decimal text/scale, ISO calendar dates, Unicode,
raw data and provenance. Reject duplicate keys, unknown pairs, malformed values
and v2 coercions/noncanonical shapes. Existing v1 serialization and old rows are
not rewritten or subjected to the new v2 shape comparison.

Repository writes enforce source/result family under BEGIN IMMEDIATE and reject
cross-family active replacement, including FAILED replacements. Invoice header
and item envelopes remain one Invoice family; legacy unclassified Invoice callers
remain supported. Packing writes require a PACKING_LIST SourceDocument. Source
hash/status/full snapshot, expected active ID, sequence, single active, rollback
and failed-history behavior remain in the one approved repository engine.

Historical family comes from its stored discriminator, not the SourceDocument's
mutable current classification. Reclassification cannot invalidate or reinterpret
an old v1/v2 record; it also cannot authorize a cross-family active replacement.
Known stored application methods additionally check envelope-family consistency.
Provenance/status are validated on reads; missing sources, multiple active rows
and corrupt history constraints fail closed. This is structural validation, not
cryptographic integrity against a privileged rewrite of an entire database.

## Application flow

Use authoritative IDs, secure resolve_source_path, current size/hash and stored
Packing classification. Parse once through parse_document_readonly. Independently
recompute current deterministic classification when a classifier is injected, so
arbitrary confidence/evidence assertions cannot authorize extraction. Hidden,
formula and ambiguously visible merged content do not establish classification.

Native PDF bypasses vision when safe. Otherwise resolve once through the existing
configured local infrastructure and verify identity, page coverage, native-page
text equality, verification/quality/review metadata using the approved Packing PDF
safety policy. Unsafe visual sources commit an empty NEEDS_REVIEW attempt after
verified source preflight; PDF items are always unsupported with an explicit issue.

For Excel, run item extraction to establish table context. Only clean supported
item results can route their actual accepted goods/header rows away from header
interpretation. Footer candidates are not goods rows. Mixed document labels outside
mapped item columns retain full context. Reviewable/failed item results retain full
context, and all returned issues/statuses remain sticky. This is service routing,
not a modification of approved header/item algorithms. Candidate paths receive
header. or items. prefixes and retain original physical source coordinates.

Revalidate nested component outputs and exact source spans/locations; raw substrings
of identifiers are insufficient. Verify safe typed values against approved lexical
parsers/native cells. No model-generated, inferred or cross-document values enter
the pipeline. Recheck source bytes/snapshot before transactional save/replacement.

## Outcomes, alternatives and limits

Refusals do not write. Verified-source execution failures may commit inactive FAILED
attempts; failed replacements preserve prior active data. A persistence error is
uncommitted FAILED with no retry. PackingExtractionOutcome exposes persisted,
result, committed record and the observed active record where available.

A separate table/transaction engine and rewriting legacy envelopes were rejected.
Applying mutable current classification to old records was rejected because legacy
CAS-race regressions demonstrated it breaks valid historical reads.

Hash checks bracket processing rather than locking files indefinitely. Managed
uploads are immutable; external writes after the last check are outside this file
contract. Conservative extractors can leave repeated/mixed/contiguous footer cases
reviewable. XLS cached-formula provenance and the approved visual-provider trust
boundary remain inherited limits. No semantic Packing AI, PDF items, business rules,
matching, endpoints, UI or background jobs are introduced.
