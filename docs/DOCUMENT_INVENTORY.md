# Document Inventory — Transport, Arrival and Declaration Evidence

Date: 2026-10-30  
Status: Documentation amendment proposed for independent review; runtime extensions NOT IMPLEMENTED  
Policy basis: Project Owner operational decision recorded in [ADR-004](decisions/ADR-004-arrival-declaration-source-policy.md)  
Related registry: [Declaration field/source/coverage matrix](DECLARATION_FIELD_SOURCE_MATRIX.md)

## 1. Purpose and interpretation

This inventory distinguishes documents that a shipment may contain from kinds currently authorized for extraction. Product scope, a canonical model, classification output and a working extractor are separate capabilities. Successful extraction does not establish a declaration comparison PASS, reconciled documents or readiness to proceed.

The SEA/AIR source priorities below are versioned Owner operational policy for this workflow. They are not universal legal conclusions. Conditional documents become required only when an applicable, evidenced shipment/item policy requires them. The inventory does not require every shipment to contain C/O, permits, specialized inspection documents or insurance.

## 2. Independent document dimensions — proposed contract

| Dimension | Meaning and examples | Safety requirement |
|---|---|---|
| Family | Commercial, packing, transport, arrival/operational evidence, declaration, origin, permits, insurance, technical specification | A family is not authority to use every document kind as a source. Arrival Notice has a separate proposed `ArrivalNotice` contract, not a Bill alias. |
| Kind | Commercial Invoice, Packing List, B/L, AWB, Arrival Notice, Sea Waybill, standalone manifest, declaration export | Identify the actual document, not a reference printed on it. An AN containing an AWB number remains AN. |
| Mode | SEA, AIR, ROAD, RAIL, MULTIMODAL; unknown when not evidenced | Do not infer mode solely from a word, filename or the presence of a container. |
| Hierarchy | Master, house, direct or unknown, where evidenced | MAWB/HAWB or master/house B/L are distinct scopes. Never apply a master total to a house shipment without an explicit evidenced relationship. |
| Context | Shipment identity, declaration/checking context, consignment/leg, parties and document relationships | One file may reference several shipments; shared numbers alone do not establish correct source scope. |
| Revision / active status | Issuer revision/correction evidence and an explicitly resolved active source within the same kind and scope | Latest upload or latest extraction is not automatically the latest document revision. Ambiguous active source blocks source resolution. |

These are design requirements for future contracts. Current `DocumentType` and `DocumentClassificationResult` do not implement these independent dimensions. Existing extraction-record active history must not be reinterpreted as proof of the legally or operationally active source document.

## 3. Inventory by transport mode

“Required” in this table refers to this Owner workflow and an applicable field policy. A document may be present but unusable because identity, revision, provenance, units or scope is unresolved.

| Mode | Document kinds and role | Required-source / reconciliation treatment | Implementation boundary |
|---|---|---|---|
| SEA | B/L; house/master context if evidenced | Shipment identity, bill number, transport parties, routing and freight terms are Bill evidence. Preserve each source value. B/L packages/weight are eligible only when matching AN with compatible units, weight kind and shipment scope. | TASK-008 plans B/L extraction only; no business-rule PASS from extraction. |
| SEA | Arrival Notice; evidenced corrections/revisions | AN is mandatory for the declaration indicator **“địa điểm xếp hàng”**. Declaration follows the required AN value; if only a place name exists, map using the correct catalog and declaration field definition. Reconcile vessel/voyage, arrival/ETA and containers against AN. | Separate TASK-016 proposed contract/extraction/service/integration sequence; not a TASK-008 alias or implemented model. |
| SEA | Sea Waybill; standalone cargo/shipping manifest; shipping advice | Retain as distinct kinds for future design. They cannot silently authorize B/L extraction or supply mandatory AN values. A manifest-like table inside an accepted B/L is only a layout, not authorization for a standalone manifest. | Unsupported TASK-008 input kinds; exact-kind classifier gap requires a separately approved change. |
| AIR | AWB, including master/house/direct context if evidenced | AWB remains source evidence for shipment identity, bill number, transport parties, routing and freight terms. Its pieces/weight remain visible for reconciliation even where AN is required. | TASK-008 plans AWB extraction only; MAWB↔HAWB source relationships are not established by the existing scalar bill field. |
| AIR | Arrival Notice; evidenced corrections/revisions | AN is required for **actual pieces and gross weight**. A differing AWB does not override AN. A separate weigh ticket is not a prerequisite to AN priority. AN with only chargeable weight cannot supply gross weight. | TASK-016 proposed; not implemented or authorized by an AWB keyword. |
| AIR | Air cargo manifest, flight advice and optional weighing evidence | Supporting evidence only within its own verified kind/scope; not an AWB or AN substitute. Preserve an actual weigh ticket if supplied; never fabricate measurement ID, weighing time or weighing evidence. | Standalone manifests and these extractors are outside TASK-008. |
| ROAD | Road consignment note, carrier receipt, border/arrival advice; evidenced operational records | Inventory and future extension design only. ROAD required sources, units, scope and conflict policy need Owner decisions before implementation; do not transplant SEA/AIR priority automatically. | No ROAD extractor in TASK-008 or implied implementation authorization. |
| RAIL | Rail consignment note, wagon/container list, rail arrival advice | Inventory and future extension design only. Preserve wagon/leg and consignment scope; required sources need Owner decisions. | No RAIL extractor in TASK-008. |
| MULTIMODAL | Multimodal transport document, leg-specific documents, transfer/arrival notices | Keep mode per leg, hierarchy and through-consignment relationships separate. No automatic consolidation or winning source across legs; unresolved applicability remains unsupported/NOT_CHECKED and blocks a critical check. | Inventory and extension design only; no standalone multimodal-document extractor in TASK-008. |

For SEA the declaration indicator “địa điểm xếp hàng” must retain its own field definition. It is **not automatically equivalent** to a Bill's `port_of_loading`, `place_of_receipt`, a storage location, or a customs location code. Catalog name-to-code mapping must retain catalog version, source AN place and mapping evidence. A missing or ambiguous mapping blocks the affected declaration check.

ETA is estimated arrival, not actual arrival. Neither ETA nor a schedule is evidence of an actual arrival event. Missing AN, wrong shipment, unclear active revision, wrong weight kind or missing necessary units blocks the required-source decision; there is no Bill fallback. For SEA packages/weight disagreement, keep a conflict and BLOCK; the Owner has not authorized an automatic winning source.

## 4. Cross-mode commercial, regulatory and declaration evidence

| Kind | Role and applicability | Forbidden assumptions / coverage boundary |
|---|---|---|
| Commercial Invoice | Commercial document identity/date, seller/buyer/ship-to, currency, Incoterms and values; compare relevant declaration and other document references. TASK-006 implementation is completed. | Seller is not automatically shipper; buyer is not automatically importer/consignee/AN notify. Invoice number/date/currency/Incoterms/value unresolved high-risk conflicts block readiness. |
| Packing List | Item/quantity/package/weight information with its own units, scope and provenance. TASK-007 implementation is completed. | Do not use Packing List totals to override required AN values, or assume item totals and shipment totals have the same scope. |
| Customs declaration data | Actual proposed declaration values to check, received through structured export/manual intake first under TASK-017. PDF/OCR intake is later scope needing separate authorization. | The current canonical skeleton is not an implemented intake or checker. Preserve entered/source values; never automatically rewrite the declaration to match a selected source. |
| Contract / Purchase Order | Commercial relationships, terms and references when relevant | Neither historical records nor a PO silently override current Invoice/AN policy. Current presence of classification kinds is not evidence of extraction/check coverage. |
| C/O | Origin evidence when applicable to the shipment/item and an approved policy | Conditional; not required for every shipment. A C/O reference is not evidence that the C/O exists or is valid. |
| Permits / specialized inspection or policy documents | Conditional evidence linked to applicable items, declaration context and an approved requirement | Applicability must be recorded; unknown critical applicability cannot become PASS. No blanket document-presence requirement. |
| Catalogue / specification | Description, technical attributes and classification support | Reconcile description across relevant sources. HS remains the declarant's decision; do not auto-copy historical HS or present AI inference as verified legal classification. |
| Freight invoice / debit-credit adjustment evidence | Actual freight charges and approved adjustments, with currency, basis, included-cost status and scope | A freight term is not a freight amount. Prevent double-counting amounts already included in commercial values. |
| Insurance policy / certificate / premium evidence | Separate **insured value** from **insurance premium/charge**, retain coverage scope and currency | Insured value is not a premium to add to declaration value. Freight/insurance adjustments need evidenced inclusion/exclusion and a traceable calculation; no double-counting. Conditional insurance documents are not required for every shipment. |
| Human correction / accepted exception evidence | Attributed correction history and policy-controlled disposition of an identified discrepancy | Preserve all original source values. An exception cannot permit a declaration contrary to mandatory AN value, omit AN, or bypass unresolved shipment identity. |

Importer, consignee, buyer and AN notify roles must be compared through explicit evidenced relationships. Legitimate role differences need a named accepted exception under the applicable policy; do not force identity equality or hide the discrepancy.

## 5. Evidence required before a source can be used

For each applicable field the proposed source decision retains:

- Source document ID, extraction ID, canonical field path and exact raw/normalized values; page or sheet/cell and bounding box where available. Keep casing and leading zeroes in identifiers.
- Document kind, mode, master/house/direct hierarchy, shipment/leg/consignment scope and the evidence establishing those relationships.
- Document revision and active-source decision evidence. Preserve all alternative and superseded values, correction history and actors; upload order and extraction confidence cannot resolve source precedence.
- Unit and quantity type: pieces/packages and package type; gross, net and chargeable weight separately; shipment versus line/container/house scope. Convert or aggregate only under an approved, traceable rule with all inputs present.
- Policy rule ID/version, required source/value and the reason for selection or refusal. Higher confidence does not override required-source policy, and conflicting values are never averaged.
- Any calculated value's inputs and formula; it is not an `EXTRACTED` source fact. An evidenced unit conversion must not erase original units or source text.

Measurement time/ID may be recorded only if real evidence supplies them. The absence of a separate weigh ticket does not remove AIR AN priority. Missing critical evidence yields NOT_CHECKED plus readiness BLOCK, rather than invented evidence or a default Bill winner.

## 6. Outcomes and exception evidence

Keep three independent results: **(A)** declaration versus required source/value, **(B)** document-to-document reconciliation, and **(C)** dossier readiness. For AWB gross 108 kg and AN gross 113 kg, declaration 108 kg blocks A/C; declaration 113 kg may pass A, while B still contains an OPEN AWB discrepancy. C can proceed only when the discrepancy is resolved or a policy-authorized exception is accepted without violating the mandatory AN value.

An accepted exception identifies finding, affected fields/documents, every differing value, reason/evidence, authorized acceptor, acceptance time and policy version. Unresolved high-risk conflicts include SEA loading place, AIR actual pieces/gross weight, actual shipment Bill number, importer/consignee relationships, Invoice number/date/currency/Incoterms/value, and arrival plus flight or vessel/voyage versus AN. These remain blocking. Unsupported or unexecuted critical coverage is NOT_CHECKED + BLOCK.

The future report must show declaration value, every document value, required source/value and selection reason, discrepancy, blocking disposition, exception and required action. Corrections, new revisions, changed source relationships or policy changes invalidate dependent results; old PASS results cannot authorize a changed dossier.

## 7. Current implementation versus proposed work

| Capability | State at base `66839bf` | Planned ownership / gate |
|---|---|---|
| Invoice extraction/history and Packing List extraction/history | Implemented through completed TASK-006/TASK-007; Invoice envelope v1 and Packing envelope v2 | Preserve existing behavior and compatibility. Reported baseline is 1422 passed / 2 warnings; this docs amendment does not rerun it. |
| Transport canonical values | `TransportDocument` exists; document semantics alone do not authorize every kind the model could represent | TASK-008A remains exactly 24 approved header paths plus 2 reference-list paths, including shipper/consignee/notify tax IDs; no AN aliases or expanded validator. |
| B/L and AWB extraction/service/persistence | TASK-008A..E are TODO under IN_PROGRESS epic | First review, approve, merge and close this docs amendment; then authorize each child sequentially. Planned transport envelope v3 remains a future TASK-008D change. |
| Exact kind / mode / hierarchy / context authorization | Existing classifier returns broad `DocumentType`, confidence and clue evidence; no independent dimension contracts | Separately approved classifier dependency must establish the exact input boundary before transport service authorization. AN with AWB number, Sea Waybill, standalone manifest and other unsupported kinds are mandatory negatives. |
| Arrival Notice and operational evidence | No `ArrivalNotice` canonical model or aggregate collection exists | [TASK-016](../tasks/todo/TASK-016-arrival-notice-evidence.md): contracts/compatibility → classification/extraction → service/persistence → integration/regression, each reviewed sequentially. |
| Declaration intake / registry / source comparison | `CustomsDeclaration` skeleton exists; intake and two-direction checks are not implemented | [TASK-017](../tasks/todo/TASK-017-declaration-intake.md), followed by original TASK-009 Normalization, TASK-010 Document Relationship + Item Matching, TASK-011 Rule Engine, TASK-012 A/B checks, TASK-013/014/015 report/correction-regression. |

Canonical schema version, extraction-envelope format version and database schema/migration version are separate axes. Canonical aggregate currently declares `schema_version="0.1"`; this is not a SQLite migration version. Preserve existing Invoice v1 and Packing v2; transport v3 is planned. This amendment assigns **no Arrival Notice envelope version** and changes no runtime schema, classifier, codec, repository or database. Those technical changes require separate Leader approval and task review.

## 8. Review handoff

This inventory and its linked policy/coverage documents are design inputs for Antigravity READ-ONLY review. They neither implement the two-direction checker nor mark future tasks approved or DONE. Design walkthroughs belong to documentation validation; they are not runtime test PASS evidence.
