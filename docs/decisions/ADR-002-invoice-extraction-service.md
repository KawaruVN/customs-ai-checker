# ADR-002 — Safe local invoice extraction composition

Date: 2026-10-29  
Status: Implemented for TASK-006E; pending independent review

## Context

Compose approved 005A and 006A/B/C/D contracts without new canonical schemas,
database semantics, hosted providers or HTTP endpoints. The existing parsing
operation sets PARSED and is unsuitable for downstream extraction.

## Decision

Introduce a separately named non-mutating parser operation and an invoice service
using authoritative document IDs. Parse once; use the existing deterministic
classifier on safe current content without writing classification metadata. Both
stored classification and current content must establish Commercial Invoice.
Hidden/formula Excel cells do not provide classification clues. A misleading
filename is never passed as evidence.

Verify secure source paths and hashes before parsing and before saving, and reject
changed SourceDocument snapshots. Hash checks bracket processing; they do not lock
files against arbitrary external writes after the final check. Uploaded sources
remain immutable under the managed application contracts. Caller-supplied hash
and processing-state preconditions are optional additional guards; the loaded
snapshot is always passed to persistence. Existing active extraction always
requires an explicit expected active ID, and 006D repeats its guards atomically.

An internal race probe showed that hash/status guards alone cannot detect a
classification change keeping both values unchanged after the service's final
read. Therefore the 006D attempt input receives an optional
`expected_source_document` using the existing SourceDocument model. The repository
compares it with the row already loaded under BEGIN IMMEDIATE. It is not stored
in payloads/history, changes no SQLite schema or active/history semantics, and is
optional for backward-compatible 006D callers. The invoice service always supplies
it, making classification/path/identity metadata checks part of the atomic CAS.

Native PDF pages passing the shared quality gate do not invoke vision. Any unsafe
page causes whole-document abstention if safe visual resolution is unavailable.
Resolution is called at most once. Review flags, unresolved lists, unverified or
conflicting visual pages and low-quality results cannot reach semantic fallback.
005A single-provider/cross-verified results remain governed by its approved
quality policy. This service does not claim independent OCR certainty beyond it.
PDF headers can be extracted from safe documents; PDF items remain unsupported
and always require review. No spacing heuristics or fabricated item list.

Excel combines the approved deterministic extractors; header interpretation sees
only visible business cells, while item extraction retains its approved hidden
content/ambiguity policies. All candidates/issues remain available and every
assembled payload is freshly validated through the approved persistence contract.

## Semantic trust boundary

No default semantic provider exists. A future provider implements a strict
provider-neutral protocol and receives only eligible labeled source evidence.
Supported fills are header paths only; item identity/correspondence is not guessed.
The local boundary independently verifies source document, exact location/raw
representation, explicit label role, canonical type and conservative numeric/date
conversion. Literal source occurrence alone does not prove a value's field role.
Only None fields may be filled. Deterministic issues/conflicts/formulas remain
sticky and semantic conflicts never use majority voting. Rejected output or
provider failure becomes a review issue, with no raw provider exception logging.

## Persistence and error semantics

Use InvoiceHeaderExtractionResult containing the assembled canonical Invoice and
items, as supported by 006D. Preconditions/refusals do not create attempts. After
verified-source preflight, technical parsing/deterministic failures are FAILED
attempts; unresolved visual evidence is NEEDS_REVIEW. Database failures return a
typed failure/refusal without a second save. SourceDocument is latest-attempt
metadata; get_active remains the explicit current usable result. A failed
replacement preserves the old active result. Application code executes no SQL.

## Alternatives

- Reuse mutating parsing/classification services: rejected because of state
  downgrades and duplicate work.
- Arbitrary semantic business values with provenance strings: rejected because
  claimed evidence and field roles must be independently verified.
- New combined persistence schema: unnecessary; existing canonical Invoice carries
  item rows and approved extraction issues/candidates.

## Consequences and limits

Conservative abstention reduces extraction coverage, including blank/unsafe PDF
pages and unsupported PDF items. Semantic fills support only independently
verifiable labeled header evidence, with no free-form semantic reinterpretation,
cross-document inference or item matching. Missing optional canonical fields stay
None. EXTRACTED means the supported extraction contract completed; it does not
certify business completeness, normalization, legal correctness or human approval.
This layer does not implement user authentication or background retries. Local
vision uses only the existing configured loopback/lazy providers when enabled.
