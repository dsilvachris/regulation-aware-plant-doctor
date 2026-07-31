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

## Go/no-go: GO

All three feasibility conditions from `Phase4_Plan.md` Step 0 are met:
- [x] openFDA returns real, parseable records
- [x] EMA returns real, parseable records with native ATC codes
- [x] A genuine divergence case is known to exist (aducanumab), pending confirmation at candidate-set scale
- [x] ATC hierarchy is real and multi-level (confirmed: `N02AA` = anatomical group N, therapeutic subgroup
      02, pharmacological subgroup A, chemical subgroup A)

## What's left before Step 1 (benchmark design)

Run `src/phase4_step0_feasibility.py` (below) against a real candidate set of ~10-15 substances spanning
2-3 ATC classes, to confirm — at the scale Phase 4 will actually use, not just via one anecdote — that
divergence and hierarchy richness hold up. This needs to run on a machine with open internet access (the
three domains above are not on this environment's network allowlist, though every live check documented
here was performed via this conversation's search/fetch tools).