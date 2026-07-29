# Correction — KG-Arm Disease-Name Bug (found via Phase 3 Step 1)

## What happened

`src/phase3_step1_diagnose_conflicts.py` (Phase 3, Step 1: checking whether real KG/RAG conflicts exist
in the data) surfaced a negation-mismatch candidate on `n02` that, on inspection, was not a KG/RAG
disagreement at all — it was a bug in `kg_verbalise.py`. Several branches of `verbalise()` and
`verbalise2()` hardcoded the string **"late blight"** into the facts text handed to the LLM, regardless of
which disease was actually being queried. The underlying SPARQL retrieval (`kg_arm.py`) was always
disease-correctly filtered; only the sentence *phrasing* that text was wrong.

**Scope, confirmed by direct testing (not inferred):** all 12 of the apple-scab/powdery-mildew extension
questions across the `region_specific`, `multi_hop`/`constraint`, `negative`, `cross_border`, and
`products_with_substance`/`substance_in_both` verbaliser branches:

```
as_m01, as_m02, as_c01, as_c02, as_n01, as_d01, as_d02, pm_n01, pm_n02, pm_d01, pm_d02, pm_d03
```

The 33 original late-blight questions and `xd_01`/`xd_02` (cross-disease) were unaffected — verified by
direct regression check against six representative late-blight questions and the cross-disease template
(which correctly enumerates all three diseases by design).

## Measured impact on existing grades

Reading the actual graded transcripts (not inferring from category alone): **17 of 24 graded KG-arm items
(71%) across these 12 questions were marked incorrect**, and all 17 explicitly cite the disease mismatch as
the stated reason for an abstaining answer — e.g. *"The products mentioned...are listed as late-blight
products in Germany. The question asks about apple scab"*; *"No information is available on authorised
cucurbit powdery mildew products in Germany. The facts only mention [late blight]."* Faithfulness was
essentially unaffected (the model correctly refused to overclaim given the mismatched text) — only
correctness was depressed, because a genuinely faithful abstention was scored as if it were a reasoning
failure, when the real cause was a broken input it had no way to know was broken.

This means Phase 1's KG-arm correctness on this subset — and everything built on top of those grades in
Phase 2 (the oracle ceiling, the deterministic router's exact match to it, every LLM-router quality number,
every cost-of-misrouting table) — is very likely a conservative underestimate of KG's real performance.
Since this bug never affected RAG's answers, the correction is expected to widen KG's advantage, not narrow
it, on this subset specifically — but the precise numbers in `Phase1_Results.md`, `Phase2_Results.md`, and
`Phase2_Step4_CostOfMisrouting.md` are known to be built on a fixable defect until this correction is
merged.

## The fix

`src/kg_verbalise.py`: every hardcoded `"late blight"` string in `verbalise()` and `verbalise2()` now uses
`facts.get("disease")`, mapped through a small `DISEASE_LABEL` dict (kept in sync with
`build_kg.py`'s `DISEASES[...]["label"]`, duplicated rather than imported since `build_kg.py` runs its full
pipeline at import time). Verified against all 12 previously-affected questions (all now correctly name
their disease) and regression-checked against six original late-blight questions (unchanged).

## Remediation plan (full — chosen over a lightweight note)

Because the bug only ever affected the *phrasing* handed to the LLM, not retrieval, and because RAG's
answers for these 12 questions are entirely unaffected and don't need to change, the correction is scoped
narrowly:

1. **`src/correction_regenerate_kg_answers.py`** — regenerates ONLY the KG-arm answer for these 12
   questions, at the same run count the original grading used (`run1`, `run2` — these questions were only
   graded for 2 of Phase 1's 3 runs). RAG's existing graded answer is reused unchanged. Produces a small,
   independently-shuffled blind grading sheet (`grading_sheet_BLIND_correction.json` + key) — 24 items,
   same blind-grading convention as `stage6_eval.py`.
2. **Grade the correction sheet** the same way as the original (blind, fill `grade_*_correct`/`faithful`,
   don't open the key first).
3. **`src/correction_merge_and_recompute.py`** — merges the graded correction into a NEW master file
   (`grading_sheet_BLIND_corrected.json`; the original 105 untouched items + these 24 corrected ones =
   129 total, same as before). The original `grading_sheet_BLIND.json` is never overwritten — both versions
   remain on record. It then automatically re-derives every downstream Phase 2 number
   (`oracle_results_corrected.json`, `phase2_deterministic_router_corrected.json`,
   `phase2_step4_results_corrected.json`) by safely swapping the corrected files in for the existing
   Phase 2 scripts' hardcoded filenames, running them unmodified, and restoring the originals — no changes
   to the well-tested Phase 2 scripts themselves.

## Status

- [x] Bug found, scope confirmed (12/12 affected questions verified directly)
- [x] Fix written and verified (12/12 fixed, 6/6 regression-checked)
- [x] Correction scripts written (`correction_regenerate_kg_answers.py`, `correction_merge_and_recompute.py`)
- [x] Correction batch generated (24 items, KG regenerated, RAG reused)
- [x] Correction batch graded (blind, same convention as original)
- [x] Merged + recomputed; `Phase1_Results.md`, `Phase2_Results.md`, `Phase2_Step4_CostOfMisrouting.md`
      updated with corrected numbers and an explicit changelog/addendum in each
- [ ] Phase 3 Step 1's conflict diagnostic re-read once the corrected facts_text is in place (the
      remaining, non-bug negation candidates should be re-examined with clean data) — next step

## Final numbers (for the record)

| metric | before | after | delta |
|---|---|---|---|
| KG correctness (all 129 items) | 50.4% | 62.0% | +11.6 pts |
| KG faithfulness | 96.1% | 94.6% | −1.6 pts |
| RAG correctness | 42.6% | 39.5% | −3.1 pts |
| RAG faithfulness | 87.6% | 80.6% | −7.0 pts |
| KG correctness, 12-question affected subset | 29.2% | 91.7% | +62.5 pts |
| RAG correctness, 12-question affected subset | 70.8% | 54.2% | −16.7 pts (grading-session variance, RAG text unchanged) |
| oracle (category) / deterministic router | 52.0% | 64.0% | +12.0 pts |
| oracle (per-question) | 70.0% | 74.0% | +4.0 pts |

Full corrected cost-of-misrouting tables are in `Phase2_Step4_CostOfMisrouting.md`'s addendum. Raw
before/after JSON: `data/correction_before_after.json`, `data/oracle_results_corrected.json`,
`data/phase2_deterministic_router_corrected.json`, `data/phase2_step4_results_corrected.json`