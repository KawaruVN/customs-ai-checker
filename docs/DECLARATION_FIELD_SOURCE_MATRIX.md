# Declaration field / source / coverage matrix

Date: 2026-10-30  
Status: Proposed technical registry — not implemented; pending amendment review/approval/merge/closure  
Business policy: OP-AN-DECL v1, Owner-approved operational requirements (not universal legal rules)

Authority: [MASTER_SPEC Section 61](../MASTER_SPEC.md),
[ARCHITECTURE Sections 69–72](../ARCHITECTURE.md),
[ADR-004](decisions/ADR-004-arrival-declaration-source-policy.md),
[inventory](DOCUMENT_INVENTORY.md), [implemented/proposed schema](DATA_SCHEMA.md).
This is an initial internal registry design. `DF-*` IDs are **not official customs
field codes**. Exact official indicator/catalog and context applicability must be
approved before an applicable declaration field can be checked.

## 1. Registry and evidence contract

Each future registry entry must store separately: ID, name/semantic definition,
mode/context applicability, required source, forbidden overrides, comparison,
aggregation/conversion/tolerance rules and their versions, required evidence,
severity/blocking/exception behavior and coverage/support status. The table combines
columns for readability; it does not make any metadata optional.

Common evidence **E**: exact source document + extraction + field path, raw and typed
value, page or sheet/cell (bbox where available), source hash/revision/active-selection
evidence, shipment/master-house scope and units/kind when relevant, declaration input
version/field, applied mapping/catalog/rule/OP version and reason. Manual declaration
input records actor/time/input version with MANUAL origin; never fake physical evidence.
Source decision and every differing candidate remain inspectable. Calculations retain
input evidence IDs/formula/conversion/rounding; no calculation is marked EXTRACTED.

**H** = high-risk discrepancy: unresolved means BLOCK. **C** = critical applicable
field: unsupported/missing/unexecuted current check means NOT_CHECKED + BLOCK.
The high-risk fields named by Owner use H/C below. Additional criticality and
applicability depend on an explicitly approved field/context policy; until resolved,
unknown critical applicability is BLOCK. **EX** = only an explicitly permitted named
exception under OP-EXC-01 may accept a document discrepancy. It cannot waive required
AN, a wrong required value or unidentified shipment. No entry grants automatic waiver.

Support **M** = some scalar/list canonical fields exist, but intake/source/check
execution is not implemented. **P** = requires proposed extension. Every row's current
check coverage is **NOT_IMPLEMENTED**, not PASS; presence of a model/extractor alone
does not establish an executed check. After implementation coverage must distinguish
supported+executed, missing inputs, unsupported, not executed and evidenced N/A.
NOT_IMPLEMENTED registry support maps to NOT_CHECKED + BLOCK whenever applicable C.

Comparison defaults: exact identifiers (preserve leading zeros); no fuzzy role merge;
numeric comparisons only at same scope/kind/unit/currency. No implicit aggregation,
unit conversion or tolerance is granted. Numeric tolerance/rounding must be approved,
versioned and visible; if missing for a check that needs it, BLOCK. A tolerance cannot
authorize the wrong required-source policy or erase a material source discrepancy.

## 2. Two independent check directions

- **Lane A, document ↔ document:** compare all relevant documents at proven scope;
  retain differences and OPEN findings even if one source has priority for declaration.
- **Lane B, required source ↔ declaration:** resolve eligible required source/value
  by rule ID/version, compare declaration, record value/source/reason and violations.
- **Readiness C:** evaluate both lanes, mandatory documents, current coverage and
  exceptions. Lane B PASS alone cannot create dossier PASS. Bill fallback, averaging,
  majority vote and confidence override are forbidden.

Crosswalk: outcome **A** (declaration compliance in MASTER_SPEC/ADR-004) is produced
by check **lane B**; outcome **B** (document reconciliation) by check **lane A**.
Outcome **C** is dossier readiness. Outcome letters and roadmap lane letters label
different dimensions; never map statuses by letter alone.

## 3. Initial declaration field registry

All rows require E plus the field-specific evidence listed. “All” means applicable
SEA/AIR checking contexts initially, with ROAD/RAIL/MULTIMODAL design-only extension;
it is not a claim of a current extractor for those modes.

| ID / name and definition | Mode / context | Lane B required source; forbidden overrides | Lane A comparison; aggregation / conversion / tolerance | Evidence beyond E; severity / exception | Current support / coverage |
|---|---|---|---|---|---|
| DF-01 Actual Bill/AWB reference: transport identifier for the lot being declared | SEA/AIR; master/house relation explicit | Active identified B/L or AWB, linked and reconciled to AN; no filename, incidental reference, container or unrelated bill | Reconcile AN/Bill/declaration references at correct hierarchy; exact string; no stripping zeros or ungrounded master=house | Actual-lot and scope relation; H/C, EX cannot bypass shipment identification | M `transport_references` / NOT_IMPLEMENTED |
| DF-02 SEA “địa điểm xếp hàng”: exact declaration indicator, not generic port/place | SEA Owner workflow | **AN, OP-SEA-01**; forbid B/L substitution, generic Port of Loading/Place of Receipt/storage/customs-code equivalence | Retain B/L↔AN difference; AN name→declaration code via exact indicator/catalog version; no fuzzy shortcut | Approved indicator definition, AN name, code/catalog mapping evidence; H/C; wrong required AN value cannot be excepted | P / NOT_IMPLEMENTED |
| DF-03 Actual pieces: shipment package/piece count at declared scope | AIR | **AN, OP-AIR-01**; no AWB/PL priority, confidence override or weigh-ticket prerequisite | AWB/PL↔AN reconcile; do not sum master/house/split without relation and approved package-kind mapping; exact count unless approved rule | Actual count/package kind/scope; H/C; EX only for permitted discrepancy after declaration follows AN | P declaration field; M sources / NOT_IMPLEMENTED |
| DF-04 Gross weight: gross shipment mass, separate from net/chargeable | AIR | **AN, OP-AIR-01**; no AWB/net/chargeable fallback, no invented weighing record | AWB/PL↔AN reconcile; same gross scope/unit; approved exact conversion only, tolerance version required | Explicit gross label/unit, scope; separate ticket not required; H/C; wrong AN value not exceptable | P declaration/unit/scope; M sources / NOT_IMPLEMENTED |
| DF-05 Package count/type: SEA shipment packages at declared scope | SEA | B/L eligible **only if matching AN, OP-SEA-02**; conflict has no automatic winning source, even AN | B/L↔AN↔PL; preserve package kind and scope; no average or majority/ungrounded sum | Matching AN plus B/L, package-kind mapping; C; unresolved totals conflict BLOCK; no automatic exception/winner | P declaration; M sources / NOT_IMPLEMENTED |
| DF-06 Gross weight: SEA shipment gross mass | SEA | B/L eligible only with AN agreement; no automatic AN/Bill winner on conflict | Reconcile B/L/AN/PL gross; no net/chargeable substitution; approved same-scope unit conversion/tolerance | Gross label/unit and matching AN/B/L; C; conflicting totals BLOCK pending explicit resolution/policy | P declaration/unit/scope; M sources / NOT_IMPLEMENTED |
| DF-07 Vessel / voyage: identified sea movement | SEA | Identified B/L values must reconcile against active AN; no automatic Bill winner if different | Compare each movement element and operational leg; no inferred schedule or flight substitution | B/L and AN leg/revision; H/C, EX only if permitted/evidenced | P declaration; M transport / NOT_IMPLEMENTED |
| DF-08 Flight: identified air movement | AIR | Identified AWB movement must reconcile against AN; no guessed schedule | Compare correct flight/leg vs AN; no voyage-to-flight or unrelated-leg match | AWB/AN leg and date context; H/C, EX only if permitted/evidenced | P declaration; M transport / NOT_IMPLEMENTED |
| DF-09 Arrival: actual arrival fact vs estimated ETA | SEA/AIR | AN operational evidence appropriate to exact indicator; ETA cannot satisfy actual arrival; no event/time fabrication | Compare AN vs transport dates at same event type/time context; dates do not imply actual event | Estimated/actual flag and date precision/time zone where supplied; H/C, EX cannot create missing actual evidence | P actual event/declaration; M transport ETA / NOT_IMPLEMENTED |
| DF-10 Container / seal references: independent identifiers | SEA; AIR only explicit applicable reference kind | Bill references reconciled to AN; no positional container/seal pairing, invented IDs or ULD=ISO assumption | Compare independently by grounded kind/scope; no inferred pairing or blind list alignment | Per-token provenance and any explicit relation; C when applicable, EX per approved policy | P declaration; M transport lists / NOT_IMPLEMENTED |
| DF-11 Importer identity: legal declarant-side importing party | All applicable dossiers | Authoritative structured/manual declaration identity plus verified role/authority evidence; source checklist to be approved in TASK-017, no default buyer/consignee/AN notify replacement | Reconcile role-specific consignee/buyer/AN notify relationships, not forced equality; IDs exact, names only under approved normalization | Identity and role/authority relation; H/C; unresolved source checklist BLOCK; EX cannot hide wrong lot/identity | M importer; P relations / NOT_IMPLEMENTED |
| DF-12 Exporter identity: declaration exporting party | All applicable dossiers | Structured/manual declaration plus approved role/authority evidence; no automatic seller=shipper=exporter | Compare commercial seller and transport shipper by role and documented relations; no fuzzy identity decision alone | Legal identity and applicable role relation; criticality per context, EX named if legitimate difference | M exporter; P relations / NOT_IMPLEMENTED |
| DF-13 Invoice number: all invoices referenced by declaration | All with Invoice | Active identified commercial invoice(s); PL/C/O/AN references do not overwrite invoice identity | Reconcile each reference vs Invoice and declaration, no ungrounded one-invoice assumption or leading-zero loss | Invoice relationships/revisions; H/C, permitted discrepancy EX only after correct required value | M invoice_references / NOT_IMPLEMENTED |
| DF-14 Invoice date: date associated with each referenced Invoice | All with Invoice | Relevant active Invoice, no delivery/date label substitution or guessed date order | Invoice↔references/declaration at matched invoice scope; calendar exact unless explicit chronology rule; ambiguous date BLOCK | Per-invoice date and format evidence; H/C, EX cannot manufacture date | P declaration date association; M Invoice / NOT_IMPLEMENTED |
| DF-15 Currency: monetary denomination for applicable declaration amount | All monetary | Relevant Invoice and approved valuation context; no symbol guessing or implicit mixed-currency merging | Reconcile Invoice/declaration amounts and currencies, supporting cost docs; conversion explicit and versioned | Currency for each input; H/C, no exception for unsupported conversion | M currency / NOT_IMPLEMENTED |
| DF-16 Incoterms / delivery term: commercial term and relevant place/version | All applicable Invoice | Active Invoice term; AWB/Bill freight prepaid/collect does not override Incoterms | Invoice↔declaration term; reconcile transport freight terms separately, no semantic equivalence | Term/place/version as evidenced; H/C, EX per explicit policy | M delivery_term; P detailed term context / NOT_IMPLEMENTED |
| DF-17 Invoice / declaration value: invoiced amount vs applicable declaration value basis | All monetary | Invoice totals plus separately supported approved adjustments; no direct equation of customs value and Invoice total without basis | Reconcile Invoice arithmetic and declaration basis; sum matched items/invoices only with scope/currency/rounding evidence | Inputs/formula/inclusion/rounding and valuation basis; H/C, unknown basis BLOCK, no legal valuation conclusion | M total_value / NOT_IMPLEMENTED |
| DF-18 Freight adjustment: charge eligible under declared value basis | Applicable charge context | Invoice/actual freight charge evidence with inclusion test; not just prepaid/collect flag or guessed rate | Compare charges and Invoice inclusion; add only eligible not-already-included cost with approved allocation | Charge evidence, currency, inclusion/Incoterms, allocation/formula; C when value-critical; unresolved inclusion BLOCK | M freight; P charge/inclusion evidence / NOT_IMPLEMENTED |
| DF-19 Insurance charge: premium eligible under value basis | Applicable insured/charge context | Actual premium/charge evidence + inclusion test; **insured value forbidden as premium** | Reconcile premium/invoice inclusion; no double counting; absent evidence is not arbitrary zero | Separate insured value vs premium, currency/inclusion/derivation; C when value-critical; unknown BLOCK | M insurance; P premium semantics / NOT_IMPLEMENTED |
| DF-20 Exchange rate: conversion rate for exact declaration context | When conversion required | Approved dated/contextual rate source; no model/historical guessed rate | Compare rate/date/currency basis; conversions trace formula and rounding, no silent cross-currency sum | Source/version/effective date and pair; C when applicable; missing approved source BLOCK | M exchange_rate / NOT_IMPLEMENTED |
| DF-21 Item quantity / unit: amount of goods per matched declaration line | Goods lines | Matched Invoice/PL and approved declaration unit definition, no guessing PCS=SET or unmatched aggregation | Invoice↔PL↔declaration at proven item mapping, unit conversions/aggregation explicit; retain differences | ItemMatch evidence, unit/catalog, formula; C when applicable; unresolved matching BLOCK | M quantity/unit / NOT_IMPLEMENTED |
| DF-22 Item description / origin: classification-relevant goods facts | Goods lines; C/O conditional | Matched Invoice/PL/specification; origin evidence/C/O only when applicable; no description inferred from HS history | Reconcile role/line descriptions, models and origin, semantic difference not automatic equivalence | Line provenance, origin applicability and conditional source evidence; criticality per context; EX named if legitimate | M description/origin / NOT_IMPLEMENTED |
| DF-23 HS code: declarant's selected classification | Goods lines | Declarant input; no automatic historical copying or source/model final HS decision | Reconcile classification descriptions and supporting docs; code format/coverage checks distinct from legal correctness | Declarant input/version, descriptive support; C for required coverage, legal determination unsupported explicitly | M hs_code / NOT_IMPLEMENTED |
| DF-24 Permit / C/O / specialized references: applicable conditional evidence | Only goods/context that need them | Applicable approved checklist and actual documents; never require on every shipment or mark unknown as N/A | Reconcile exact references/validity/item scope to declaration; legal applicability needs verified source/approved policy | Applicability basis, source/version and item/document link; C if required, missing/unknown BLOCK | M permit_references; P applicability / NOT_IMPLEMENTED |
| DF-25 Declaration type / customs office: exact procedure/checking context | All declaration inputs | Structured/manual authorized input + approved procedure/office catalogs; no inference from filename | Check against dossier/role context and applicable rules; no numeric/code coercion | Input actor/version, catalog and applicability; C; unknown context BLOCK | M declaration_type/customs_office / NOT_IMPLEMENTED |
| DF-26 Line reference / item value / tax fields: declared line identity and amounts | Goods lines and applicable tax context | Structured/manual declaration plus matched Invoice and approved arithmetic/rule source; no inferred tax treatment or rate | Preserve line mapping; item amount and total reconciliation; taxes only when explicitly supported, not presumed legally correct | Line IDs, value/currency/rounding and verified tax-rule authority; C when applicable; unsupported critical tax check BLOCK | M line_reference/item_value/tax_fields; P typed rule coverage / NOT_IMPLEMENTED |

## 4. Source resolution and readiness gates

1. Resolve applicable mode/context and exact field definition. Maintain explicit
   unsupported/unknown state; do not equate SEA loading place to any convenient code.
2. Identify actual shipment and active business documents/revisions using evidence.
   AN master vs HAWB scope cannot be assumed; splits/sums need approved relationships.
3. Require eligible AN for applicable AIR/SEA policy. Missing/wrong lot/unclear active/
   wrong weight kind/missing required unit means BLOCK; no Bill fallback. Separate
   measurement ticket is not needed to establish AIR AN priority.
4. Execute lane A and lane B separately and retain findings. AWB108 / AN113 /
   declaration113 may satisfy B but leaves A OPEN; declaration108 violates required
   value. SEA totals discrepancy always unresolved BLOCK with no automatic winner.
5. Require current critical coverage. Unsupported/unexecuted = NOT_CHECKED + BLOCK,
   including fields not yet represented by current canonical models. Supported N/A
   requires applicability evidence; absence of extracted value is not evidence of N/A.
6. Validate named exception permissions, authorized acceptor and exact evidence
   snapshot; retain differing values and OPEN finding. No exception permits wrong
   required value, omission of AN or bypass of actual shipment identification.
7. Produce readiness only for current data and rules. Source/extraction/revision/
   correction/declaration/context/catalog/policy changes invalidate affected checks
   and require exception re-evaluation and recheck. Historical reports are stale.

## 5. Report contract and implementation gates

Every conflict view must show declaration value, each document value, required source
and value (or unresolved source), rule ID/version and reason, discrepancy, OPEN/resolved
state, blocking disposition, exception evidence/authority and next user action. Do not
rewrite declaration automatically. A design walkthrough is not an executed runtime
check; ADR-004 includes all twelve required walkthroughs with expected outcomes.

TASK-008 remains B/L–AWB extraction only, exactly 24 header + 2 reference-list paths
in 008A. AN/declaration fields in this matrix are not transport aliases. TASK-016
provides AN contracts/extraction/service/storage/integration, TASK-017 structured/manual
declaration intake, TASK-009 transformations, TASK-010 relationship/item matching,
TASK-011 engine, TASK-012 both lanes/coverage, TASK-013/014/015 report/recheck/regression.
Schema/classifier/codec/persistence/derivation/authority contracts require separate
Leader approval. No AN envelope version assigned; preserve Invoice v1, Packing v2
and planned Transport v3 without conflating canonical schema or database version.
