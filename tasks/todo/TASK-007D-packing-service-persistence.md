# TASK-007D — Packing List Service & Persistence

Status: TODO  
Priority: P1  
Parent: TASK-007  
Developer: Codex  
Reviewer: Antigravity  
Dependencies: TASK-007B and TASK-007C approved and merged; TASK-006D/E contracts

## Objective and inputs

Compose approved Packing extractors from authoritative SourceDocument IDs and
provide explicitly versioned, reviewed Packing persistence support. Before
implementation, the Project Leader must approve the persistence/codec extension
design and any migration plan. TASK-007A makes no such storage changes.

## In scope and output

- Packing-only classification gate using safe current evidence and stored metadata.
- Existing secure source path resolution, non-mutating parsing and approved visual
  safety behavior; canonical PackingList assembly and issue propagation.
- Repository-layer save/read/history and explicit replacement for Packing results,
  preserving the approved Invoice records and SQLite transaction guarantees.
- Typed service outcome distinguishing refused/uncommitted attempts from committed
  EXTRACTED, NEEDS_REVIEW and FAILED attempts.

## Safety invariants

Preserve source bytes, raw/provenance, list-valued Invoice references and typed
business values. No parser status downgrade, filename classification shortcut,
unsafe visual bypass, silent overwrite, hidden SQL in application code or
customer values/paths in logs. Reuse 006D optimistic source snapshot/active guards,
rollback and single-active/history policy where the reviewed design permits.
Latest attempt metadata and active result remain distinct. Failed replacement
must preserve prior usable active data and complete history.

## Acceptance and tests

- Only safely classified Packing Lists enter extraction; wrong types, unsafe visual
  evidence, missing sources, path escapes and stale requests fail conservatively.
- Production composition preserves header/item issues and does not infer missing
  business facts or use Invoice-only storage as an unchecked Packing envelope.
- Reviewed versioned serialization preserves canonical Decimal/date, candidate
  typed-value types, raw evidence and source IDs across actual SQLite round-trips.
- Isolated DB tests cover migration compatibility, foreign keys, one active row,
  deterministic history, explicit replacement, writer races and rollback before/
  after metadata and at commit; Invoice persistence remains backward compatible.
- No raw payload/path leakage, source mutation or duplicate unnecessary visual work.

## Out of scope and review

No hosted SDK, semantic provider implementation, PDF item recognition,
cross-document matching, normalization, rules, endpoints, UI or background jobs.
Do not redesign the database or canonical models without explicit architectural
approval. Independent review and Project Leader approval precede merge/closure.
