# ADR-004 — Arrival Notice and declaration source policy

Date: 2026-10-30  
Status: Proposed — technical docs amendment pending independent review, Leader decision, merge and closure  
Developer: Codex — Main Developer  
Reviewer: Antigravity — Independent Technical Reviewer / QA  
Business authority: Project Owner requirements supplied through Project Leader  
Policy identifier: OP-AN-DECL, version 1, recorded 2026-10-30  
Implementation: NOT IMPLEMENTED by this amendment

## Context and authority

Reducing errors requiring declaration amendment/cancellation is the primary product
goal. Existing Invoice/Packing extraction completion cannot establish business
correctness, document agreement or readiness to transmit. TASK-008 only plans B/L/AWB
extraction. AN and declaration intake, source resolution and coverage gates are absent.

The source requirements below are **Owner-approved operational policy**, classified
INTERNAL_POLICY, not universal legal conclusions or model opinion. This ADR records
those requirements while proposing technical realization for separate approval. It
does not claim reviewer/Leader acceptance of this amendment or authorize code changes.
Authority order remains Constitution → Master → Architecture → schema/rule docs → task
→ implementation. Any conflict still requires Leader resolution.

## Decision record: source rules

| Rule ID (policy v1) | Applicability / condition | Required outcome |
|---|---|---|
| OP-AIR-01 | AIR actual pieces or gross weight | Use AN at the correct shipment scope; AWB disagreement stays a finding. No separate weigh-ticket prerequisite; no invented weighing event/time/measurement ID. AWB remains identity/bill/transport parties/routing/freight source. |
| OP-SEA-01 | SEA declaration “địa điểm xếp hàng” | AN mandatory. Declaration follows AN; map name to code using the exact indicator definition and correct catalog/version. B/L Port of Loading, Place of Receipt, warehouse and customs location codes are not interchangeable. |
| OP-SEA-02 | SEA movement/arrival/containers and totals | Reconcile vessel/voyage, arrival/ETA and containers against AN; ETA is never actual arrival. B/L packages/weight eligible only when matching AN. Different SEA totals: conflict + BLOCK, no automatically selected winner. |
| OP-GATE-01 | Any required-source resolution | Missing AN, wrong shipment, unresolved master/house scope, unclear active revision, wrong weight kind or missing necessary unit: BLOCK, no Bill fallback. Upload-newer is not revision-newer. |
| OP-READY-01 | Every applicable critical field and dossier | Separate A declaration compliance, B document reconciliation and C readiness. Critical unsupported/unexecuted check = NOT_CHECKED + BLOCK; extraction/confidence is insufficient. |
| OP-EXC-01 | A policy-permitted discrepancy remains | Preserve OPEN finding and all values; named authorized exception may allow proceeding only after all mandatory required-value/identity gates pass. No waiver of mandatory AN, correct required value or actual shipment identification. |
| OP-RECHECK-01 | Source, extraction, correction, declaration, context, mapping or policy changes | Invalidate affected current outcomes/readiness; retain historical report and re-evaluate exception applicability against new evidence; recheck before a current outcome. |

No average of conflicting sources, majority vote, default Bill winner or confidence
override is allowed. Preserve each document's values, even when it is not the required
source. Gross/net/chargeable and unit/shipment scope remain distinct.

## Decision record: A / B / C and exceptions

For AWB gross 108 kg and AN gross 113 kg, declaration 108 kg is BLOCK for wrong
required value. Declaration 113 kg may PASS A; AWB discrepancy remains OPEN in B.
C stays BLOCK until reconciliation resolves it or a policy-permitted exception is
explicitly accepted. Acceptance never turns documents into agreement or erases finding.

Exception evidence must store finding ID, related field IDs/documents, all differing
values, reason/evidence references, authorized accepting person and authority, timestamp,
policy version and the exact input/revision snapshot it covers. Expired/superseded
evidence or changed inputs need renewed evaluation. No implicit exception by clicking
“continue”, high confidence, or choosing the latest upload. Identity must be established
before accepting a role-related legitimate difference; no exception hides a wrong lot.

Unresolved high-risk conflicts BLOCK: SEA loading place, AIR pieces/gross, actual
shipment Bill number, importer/consignee identity and relations to buyer/AN notify,
invoice number/date/currency/Incoterms/value, arrival and flight or vessel/voyage
against AN. Legitimate parties may differ; never force seller=shipper or
importer=buyer=consignee=notify. Require role-specific relation evidence and a named
exception where a legitimate difference remains. Exception permission/authority is a
policy registry requirement, not a discretionary source-priority override.

## Proposed technical realization — separate approval required

1. Separate ArrivalNotice canonical contract; independent document family/kind/mode/
   master-house hierarchy/context and scope. Preserve unknown states and evidence.
2. Provenance joins source document, extraction, field, physical page or sheet/cell,
   raw/typed values, source hash/revision and corrections. No fabricated bbox when
   parser lacks geometry, no invented operational measurement.
3. A declaration registry defines field identity/semantics, applicability, required
   source, forbidden overrides, comparison/aggregation/conversion/tolerance, evidence,
   severity/blocking, exception permission and support/coverage. See the
   [field/source/coverage matrix](../DECLARATION_FIELD_SOURCE_MATRIX.md).
4. Source decisions retain rule ID/version, eligibility and winning-source reason,
   required value/source or unresolved BLOCK, all differing candidates and evidence.
   Never auto-edit declaration. Calculations trace inputs/formula/conversions/rounding;
   calculated values are not EXTRACTED. New derivation/origin contracts need approval.
5. Reports show declaration value, every document value, required value/source/reason,
   discrepancy, blocking state, exception and needed action. Readiness is distinct
   from per-check status and from document processing status.
6. Preserve source/revision/correction/check histories; evidence-based active business
   document selection differs from repository active extraction. Check snapshots and
   invalidation cover context/catalog/rule/policy/exception versions as well as data.
7. Conditional C/O, permits and specialized docs require applicability evidence; not
   universal prerequisites. Insurance insured value ≠ premium. Included freight and
   insurance costs must not be charged twice. HS remains declarant decision; no
   historical auto-copy, while classification descriptions must reconcile.

No schema, classifier, codec or DDL changes occur here. The
[proposed schema section](../DATA_SCHEMA.md) separates implemented0.1 from future models.
Canonical schema version, extraction envelope version and database migration/version
are independent. Preserve Invoice `(1, invoice)`/`(1, invoice_items)` and Packing
`(2, packing_list)`; retain planned Transport `(3, transport_document)` in TASK-008D.
**No AN envelope version is reserved.** AN compatibility/version/storage design needs
Leader approval in TASK-016A/C. Never reinterpret or rewrite old envelopes silently.

## Scope corrections and known gaps

TASK-008A remains exactly 24 header paths + 2 reference-list paths, including all
three transport party tax IDs; no AN aliases or relaxed exact-path validator. TASK-008C/E
accept manifest-like layouts only inside an authorized B/L/AWB, not standalone
manifests, AN, Sea Waybill or multimodal document kinds. ROAD/RAIL/MULTIMODAL are in
[inventory](../DOCUMENT_INVENTORY.md) and extension design only.

Current enum/keyword classification does not prove exact kind: AN may contain an AWB
number or Bill clues. Do not authorize extraction from a keyword + confidence alone.
TASK-008D must demonstrate the exact-kind boundary or wait for a separately approved
classifier dependency. Negative tests in future tasks must include AN with AWB number,
Sea Waybill, standalone manifest, unsupported kind, ambiguous title and wrong scope.
No new classifier/schema feature is implicitly authorized by this docs amendment.

Canonical CustomsDeclaration is a skeleton, not a current intake/check/coverage
implementation. Units/scope, AN, registry/decisions/exception history and business
revision/active selection require future reviewed contracts. The current PDF parser's
page text cannot imply that geometric bounding boxes are available for every field.

## Execution order and alternatives

Docs amendment independent review → Leader approval → Owner commit/push → Leader
remote verification → Owner merge → closure → TASK-008A..E sequential child approvals
→ [TASK-016](../../tasks/todo/TASK-016-arrival-notice-evidence.md) AN contracts/
compatibility → classification/extraction → service/persistence → integration/regression
→ [TASK-017](../../tasks/todo/TASK-017-declaration-intake.md) structured/manual intake
→ TASK-009 Normalization → TASK-010 Document Relationship + Item Matching → TASK-011
Rule Engine Foundation → TASK-012 A doc↔doc / B required source↔declaration+coverage
→ TASK-013 report → TASK-014 correction/recheck → TASK-015 golden regression.
Existing 009–015 IDs retain purpose; 016/017 use previously unused IDs.

Rejected alternatives: Bill as default source; AN as Bill alias; confidence/majority
source selection; chargeable for gross; upload order as revision order; a single PASS
covering extraction and readiness; accepting exceptions without evidence/authority;
adding all future features to TASK-008A; treating operational policy as universal law.

## Design validation walkthroughs — not runtime tests

The following are expected design outcomes checked against the policy and matrix.
No runtime rules/checks are implemented or executed by these walkthroughs.

| # | Scenario | A declaration / B reconciliation / C readiness and action |
|---|---|---|
| 1 | AIR AWB108kg / AN113kg / declaration108kg | A wrong required value; B OPEN; C BLOCK. Correct declaration to required AN value through user action. |
| 2 | Same documents / declaration113kg | A may PASS after executed checks; B AWB discrepancy OPEN; C BLOCK until resolved or authorized named exception. |
| 3 | AN has actual pieces/gross, no separate weigh ticket | AN remains AIR required source; missing ticket alone does not remove priority. Do not invent weighing evidence. Other gates still apply. |
| 4 | AN only chargeable weight | No eligible AN gross value; gross check lacks evidence; C BLOCK, no AWB substitution or chargeable→gross. |
| 5 | SEA AN placeA / B/L placeB / declarationB | A wrong required AN place; B OPEN; C BLOCK. Map A through correct field/catalog; no generic port-code substitution. |
| 6 | Required AN missing | A cannot resolve required source; C BLOCK. No Bill fallback, even if all other documents agree. |
| 7 | AN master scope differs from HAWB | Identity/reference matching alone is insufficient; C BLOCK until evidenced scope mapping, no ungrounded split/sum. |
| 8 | Two revisions, active unclear | No source winner; C BLOCK pending evidence-based authorized active selection; latest upload cannot decide. |
| 9 | SEA B/L packages/weight differ from AN | B conflict OPEN; source decision unresolved; C BLOCK; no average, majority or automatic AN/Bill totals winner. |
| 10 | Parties differ legitimately by role | Preserve role-specific values; establish actual shipment/importer identity and relation evidence; named authorized exception for permitted discrepancy; no forced equality. |
| 11 | Critical field unsupported or not checked | Coverage NOT_CHECKED; C BLOCK regardless of all executed checks PASS. Never infer shipment PASS. |
| 12 | Source/declaration/correction changes after check | Old report stays historical/stale; invalidate affected A/B/C and exception applicability; require current recheck before proceeding. |

Additional design obligations: differing/unknown units block; ambiguous gross/net/
chargeable labels block; ETA does not satisfy actual arrival; insured value cannot
be premium; missing cost inclusion evidence prevents valuation PASS; conditional
permit applicability unknown is not N/A. These are design requirements, not test counts.

## Review and consequences

Benefits: independent source decisions and discrepancies remain visible; critical
coverage prevents false PASS; provenance/version snapshots support correction/recheck.
Cost: conservative BLOCK/review until AN, intake, mappings and rule coverage exist.
No claim of runtime readiness is made. Baseline1422 is reported from TASK-007 closure;
pytest may be NOT RUN for this docs-only amendment. Developer validation and Antigravity
independent review apply to the exact tracked + untracked documentation diff.

Reviewer decision: Pending. Project Leader technical decision: Pending.
