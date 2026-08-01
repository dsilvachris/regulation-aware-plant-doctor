# Phase 4, Step 0 — Feasibility Gate: Confirmed

All three required data sources were queried live (not just documentation-checked) before committing to
Phase 4's scope.

## What was verified, live

| source | URL | status | what it returned |
|---|---|---|---|
| openFDA Drugs@FDA | `api.fda.gov/drug/drugsfda.json` | **LIVE, no auth** | Real record (AMCINONIDE, ANDA076367): sponsor, active ingredients, dosage form, route, marketing status, and `rxcui` — 29,174 total records |
| RxClass (NLM) | `rxnav.nlm.nih.gov/REST/rxclass` | **LIVE, no auth** | Real ATC1-4 lookup by RxCUI: morphine (rxcui 7052) → `N02AA` "Natural opium alkaloids", full hierarchy |
| EMA medicines data | `ema.europa.eu/.../medicines_json-report_en.json` | **LIVE, no auth** | 2,701 real medicine records, each with `active_substance`, **`atc_code_human` natively**, `medicine_status`, `therapeutic_area_mesh` |

## A finding that changes (and simplifies) the design

The original design assumed ATC would need to be joined onto both regions via RxClass. **EMA's own data
already carries `atc_code_human` natively** — no bridge needed for the EU side. RxClass is still needed,
but only for the US side, since openFDA classifies drugs via its own `pharm_class_epc`/`pharm_class_moa`
system, not ATC. The join path is:

```
openFDA record --rxcui--> RxClass (relaSource=ATC) --> ATC1-4 code
EMA record --atc_code_human (native)--> ATC1-4 code
```

Both paths land on the same WHO ATC codespace, so a substance's ATC class is comparable across regions
regardless of which regulator's data it came from — exactly what Category 7 (hierarchy-traversal) needs.

## Real cross-region divergence — spot-checked, not assumed

Same discipline as Phase 1 ("the asymmetry is the finding, not a data gap — checked, not assumed"): a
well-documented real case exists — aducanumab (marketed as Aduhelm), FDA-approved in 2021, was refused
marketing authorisation by EMA the same year. This is public record, not inferred from the API responses
above, and confirms genuine divergence is findable, the same property that made Phase 1's DE/NO
cross-border category real rather than manufactured. The actual candidate-set divergence check (beyond
this one anecdote) is left to the Step 0 script's live run — see below.

## Critical scope-boundary finding (confirmed via live rerun + verification)

The first candidate-set run found divergence in 4/9 substances; on inspection, 3 of those 4 (morphine,
oxycodone, aspirin) are **false positives** — not real regulatory divergence, but an artifact of EMA's
dataset scope. EMA's medicines JSON file covers only the **centralised procedure**, which is mandatory
for biotech/ATMP/orphan medicines and new active substances treating cancer, HIV, diabetes,
neurodegenerative, autoimmune, and viral diseases (confirmed via EMA's own published eligibility
criteria). Old, universally-authorised generics like morphine went through **national** authorisation
routes decades before EMA existed and simply never appear in this dataset — their absence means "not
centrally authorised," not "not authorised in the EU."

**Only aducanumab is a confirmed real divergence** in this candidate set: its EMA status is "Application
withdrawn" (Biogen withdrew the EU filing in 2021 after signals the CHMP opinion would be negative — this
matches the well-documented public record), and it falls squarely in the mandatory-centralised category
(neurodegenerative disease, new active substance), so its absence from EMA's authorised list is a genuine
regulatory fact, not a coverage gap.

**Design implication, not a feasibility failure:** Phase 4's candidate substances must be drawn from
EMA's centralised-eligible categories (oncology, HIV, diabetes, neurodegenerative, autoimmune, viral,
orphan designation, biotech/ATMP) for the FDA-vs-EMA comparison to be meaningful. This is directly
analogous to Phase 1's own scope-bounding (3 diseases, not the whole plant-protection domain) — a
deliberate, stated boundary, not an oversight. Outside centralised-eligible categories, "not in EMA's
data" carries no regulatory meaning and must not be used as a divergence signal.

## Go/no-go: GO, with the candidate set restricted to EMA-centralised-eligible categories

- [x] openFDA returns real, status-checkable records
- [x] EMA returns real, status-checkable records with native ATC codes
- [x] A genuine, confirmed divergence case exists (aducanumab) within centralised-eligible scope
- [x] ATC hierarchy is real and multi-level (confirmed shared subgroups: A10, N02, N06 across candidates)
- [x] **New constraint, now explicit:** candidate substances must be drawn from EMA's centralised-eligible
      categories (oncology, HIV, diabetes, neurodegenerative, autoimmune, viral, orphan, biotech/ATMP),
      not general/OTC medicines — confirmed necessary by the morphine/oxycodone/aspirin false-positive
      pattern above.

## Final verified candidate roster (locked in for Step 1)

| substance | FDA | EMA | ATC (EMA native) | cluster |
|---|---|---|---|---|
| aducanumab | Approved (2021, accelerated) | **Application withdrawn** | N07 | N06D (Alzheimer's) — **DIVERGENT** |
| lecanemab | Approved | Authorised | N06DX04 | N06D (Alzheimer's) |
| donanemab | Approved | Authorised (after an initial rejection, later reversed) | N06DX05 | N06D (Alzheimer's) |
| niraparib | Approved | Authorised, **orphan designation** | L01XK02 | L01 (oncology) |
| isatuximab | Approved | Authorised | L01XC38 | L01 (oncology) |
| epcoritamab | Approved | Authorised | L01FX27 | L01 (oncology) |
| dostarlimab | Approved | Authorised | L01FF07 | L01 (oncology) |
| melphalan flufenamide | **Withdrawn Feb 2024** (confirmed via FDA press release; absent from current openFDA index) | Authorised (as Pepaxti) | L01AA10 | L01 (oncology) — **DIVERGENT** |

Confirmed 2/8 genuine, non-transient divergence, bidirectional (aducanumab: FDA-yes/EMA-no; melflufen:
FDA-no/EMA-yes), plus real hierarchy structure across two ATC clusters (L01, N06D). **GO — this is the
locked candidate set for Step 1's benchmark.**

## Step 0 complete

Three iterations of the candidate-set script were needed (initial run: divergence miscounted due to a
status-checking bug; second run: candidates too settled/convergent, correctly triggering a NO-GO; third
run: melflufen's actual INN corrected a naming mismatch) before landing on the verified roster above. Each
iteration is preserved in the commit history rather than silently overwritten — the NO-GO result from the
second run was reported honestly, not hidden, consistent with this project's standing discipline.
Proceeding to Step 1 (benchmark design) using exactly the 8-substance roster above.