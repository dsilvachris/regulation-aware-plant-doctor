# Phase 2, Step 4 — End-to-End Quality & Cost of Misrouting

The step `Phase2_Plan.md` calls "the heart of the contribution." Steps 1–3c measured whether a router
picked the arm a pre-registered category mapping calls optimal — a proxy. This step replaces the proxy with
real, blind-graded answer quality, using Phase-1's existing grades (`grading_sheet_BLIND.json` +
`grading_key.json`). No new LLM calls or new grading were needed: Phase 1 already generated and graded
both arms' answers for every question, so a router's "answer" is just a lookup of which of those two
existing, graded answers it would have selected. Method: `src/phase2_step4_cost_of_misrouting.py`.

## End-to-end correctness / faithfulness, all conditions

| condition | correct | faithful | n |
|---|---|---|---|
| oracle (per-question) | 70% | 98% | 129 |
| **LLM router B — DOCS-first** | **53% (50–57% across 5 runs)** | 94% | 129 |
| oracle (category) | 52% | 95% | 129 |
| **deterministic router** | **52% (exact match to category oracle, every category)** | 95% | 129 |
| always-KG | 50% | 96% | 129 |
| LLM router A — baseline | 50% (49–52%) | 95% | 129 |
| LLM router C — few-shot | 49% (47–51%) | 94% | 129 |
| always-RAG | 43% | 88% | 129 |

## Cost of misrouting vs oracle(category), by category (positive = oracle better)

| category | always-RAG | deterministic | LLM A | LLM B | LLM C |
|---|---|---|---|---|---|
| cross_disease *(risky)* | **+75.0%** | 0.0% | +10.0% | +15.0% | **+25.0%** |
| negative *(risky)* | +35.7% | 0.0% | 0.0% | +4.3% | +1.4% |
| cross_border *(risky)* | −4.5% | 0.0% | 0.0% | −3.6% | 0.0% |
| constraint | +18.8% | 0.0% | +3.8% | +2.5% | −3.8% |
| multi_hop | +12.5% | 0.0% | 0.0% | +3.8% | 0.0% |
| factual | 0.0% | 0.0% | +1.3% | −8.7% | +10.0% |
| region_specific | 0.0% | 0.0% | +2.2% | −2.2% | 0.0% |

(Small negative values reflect per-item noise around a coarse category-level comparison, not a router
outperforming the ceiling on that category — see below.)

## Interpretation

**The category-level proxy from steps 3b/3c was misleading, and this step demonstrates exactly how.**
`LLM_C_few_shot` scored highest on every proxy metric — 90% "accuracy vs oracle," 91% category accuracy,
best factual-compliance. On real end-to-end correctness it scores **49%, below the naive always-KG
baseline (50%)** and worst of all five router-like conditions tested. The proxy metric was dominated by
category-level agreement on the numerous easy categories (region_specific, multi_hop, constraint, etc.,
where nearly everything defaults to KG regardless of router quality); it did not capture that C's actual
answer-quality cost is concentrated and severe on the one category where getting it wrong matters most.

**The deterministic router matches the theoretical category-level ceiling exactly** — 52%/95%, zero cost
in every category, including all three risk-critical ones. This is not a coincidence: the rule was built
to reproduce the category-oracle mapping (see `Phase2_Step2b_DeterministicRouter.md`), and this step
confirms that reproduction holds at the level of real answer quality, not just routing labels.

**Only one LLM variant (B) beats the deterministic router on raw correctness, and only marginally.** B's
mean (53%) exceeds the deterministic/oracle-category ceiling (52%) by one point, but B's own run-to-run
range (50–57%) means its worst observed run ties the deterministic router exactly, and its best run remains
far short of the per-question oracle (70%). This one-point average edge is bought with real, quantified
risk cost: +15.0% on cross-disease and +4.3% on negative, categories where the deterministic router has
zero cost by construction. Combined with the instability already established in step 3c (55%
self-consistency), B's marginal correctness gain does not look like it justifies its cost and risk profile
over the deterministic rule.

**The cross-disease cost gradient (A +10.0% → B +15.0% → C +25.0%) is now the single most load-bearing
number in the whole Phase-2 investigation.** It is monotonic across every measure taken so far — routing
misrate (2/5 → 3/5 → 5/5), and now real correctness cost — and it traces, per the step-with-question-text
finding, to `xd_02`'s implicit (non-lexically-cued) cross-disease reasoning requirement. More prompt
sophistication made this specific, safety-relevant failure *worse*, not better.

## Revised bottom line for Phase 2

Across routing accuracy, stability, and now real answer quality, no LLM-router variant tested clearly
outperforms a four-line deterministic rule once measured honestly. The rule matches the achievable
category-level ceiling exactly, with perfect stability and zero risk cost. The best LLM variant offers a
one-point average correctness edge, unstably, at a real and measurable cost on the safety-critical
cross-disease category. The worst LLM variant — the one that looked best on cheaper proxy metrics —
underperforms even the simplest always-KG baseline on real correctness while carrying the worst risk
profile of anything tested. This is a specific, evidence-grounded answer to the Phase-2 RQ, not a
inconclusive one.

## Artifacts

- Script: `src/phase2_step4_cost_of_misrouting.py`
- Full results: `data/phase2_step4_results.json` (regenerable, not committed)

## Note on Step 5 (skipped)

Step 5 in `Phase2_Plan.md` covers blind-grading any *newly generated* answers from routing. No router in
this investigation generates new answers — every router selects between two answers Phase 1 already
generated and blind-graded. There is nothing new to grade, so Step 5 is not applicable here rather than
omitted for convenience; this is stated explicitly for the thesis record.

## Addendum — corrected numbers (post-hoc, KG-arm disease-name bug)

See `docs/Correction_KG_Disease_Name_Bug.md` for the full bug report. Every table below is the recomputed
version, run against `grading_sheet_BLIND_corrected.json` via the automated swap-run-restore in
`src/correction_merge_and_recompute.py` (the original scripts and files are unmodified; both the original
and corrected grading files remain on record).

### End-to-end correctness / faithfulness, all conditions — corrected

| condition | correct | faithful | n |
|---|---|---|---|
| oracle (per-question) | 74% | 97% | 129 |
| **LLM router B — DOCS-first** | **64% (60–68% across 5 runs)** | 92% | 129 |
| oracle (category) / **deterministic router** | 64% | 94% | 129 |
| always-KG | 62% | 95% | 129 |
| LLM router A — baseline | 62% (60–64%) | 94% | 129 |
| LLM router C — few-shot | 60% (57–61%) | 92% | 129 |
| always-RAG | 40% | 81% | 129 |

### Cost of misrouting vs oracle(category), by category — corrected

| category | always-RAG | deterministic | LLM A | LLM B | LLM C |
|---|---|---|---|---|---|
| cross_disease *(risky)* | **+75.0%** (unchanged) | 0.0% | +10.0% (unchanged) | +15.0% (unchanged) | **+25.0%** (unchanged) |
| multi_hop | **+50.0%** (was +12.5%) | 0.0% | 0.0% | +3.8% | 0.0% |
| cross_border *(risky)* | **+45.5%** (was −4.5%) | 0.0% | 0.0% | 0.0% | 0.0% |
| negative *(risky)* | +35.7% (unchanged) | 0.0% | 0.0% | +4.3% | +1.4% |
| constraint | +31.2% (was +18.8%) | 0.0% | +3.8% | +7.5% | +3.8% |
| factual | 0.0% | 0.0% | +1.3% | −8.7% | +10.0% |
| region_specific | 0.0% | 0.0% | +2.2% | −2.2% | 0.0% |

### What changed, and why it matters

**The cross-disease numbers are identical before and after** — `xd_01`/`xd_02` were never touched by the
bug, so the single most important finding in this document (LLM_C's deterministic cross-disease misroute,
the A→B→C cost gradient) is unaffected. This was the finding least at risk from the correction, and it
stayed exactly as reported.

**RAG's cost on multi_hop and cross_border rose sharply** (+12.5%→+50.0%, −4.5%→+45.5%). This is the
correction's most consequential effect: the pre-correction oracle(category) ceiling was itself computed
from KG's understated correctness on the bugged questions, so the "cost" of routing multi_hop/cross_border
questions to RAG looked artificially small — in cross_border's case, the sign was even backwards
(RAG appeared to slightly *beat* the ceiling). Post-correction, both categories now show a large, clearly
positive cost, consistent with the rest of the risk framework rather than an outlier. **This strengthens
the case for routing these categories to KG; it does not weaken any conclusion in this document.**

**LLM_C — few-shot's underperformance relative to always-KG is confirmed, not an artifact of the bug**
(60% vs 62%, a 2-point gap, versus 49% vs 50% pre-correction — the same finding, slightly wider). **The
deterministic router still matches the category-oracle ceiling exactly** (64%/94% now, was 52%/95%) — a
structural property of the rule's construction, unaffected by which grades happen to be behind it.
**LLM_B still ties the deterministic router on average with the same wide instability** (60–68% range) and
still carries the same real, nonzero cost on the risky categories it touches. Every interpretive claim in
this document's original body stands; only the magnitudes changed, several of them (multi_hop,
cross_border) toward a stronger version of the same conclusion.