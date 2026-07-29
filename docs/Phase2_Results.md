# Phase 2 Results — Adaptive Retrieval: Can Routing Be Delegated to an LLM?

*Synthesis chapter (Step 6 of `docs/Phase2_Plan.md`). Draws on `Phase2_Step1` (oracle ceiling, in
`phase2_step1_oracle.py`), the LLM-router investigation (`phase2_step2a_diagnose.py`,
`Phase2_Step3b_PromptSensitivity.md`, `Phase2_Step3c_MultiRunRobustness.md`), the deterministic baseline
(`Phase2_Step2b_DeterministicRouter.md`), and the end-to-end quality analysis
(`Phase2_Step4_CostOfMisrouting.md`). This chapter answers the pre-registered RQ against that evidence;
it does not introduce new results.*

## The research question

> **RQ (Phase 2): How closely can an LLM-based router approach optimal routing, and what is the cost of
> its misrouting — particularly on the safety-critical query types where the wrong strategy fails worst?**

(`docs/Phase2_Design.md`)

## Answer

**Not closely, and the cost is concentrated exactly where the design predicted it would matter most —
but the evidence does not support the intuitive fixes, and a router with no LLM at all matches the
achievable ceiling with none of the downsides.**

The oracle ceiling (`phase2_step1_oracle.py`) shows real headroom exists: routing perfectly by
pre-registered category reaches 52% correctness against Phase 1's single-arm best of 50% (always-KG); a
per-question oracle reaches 70%, though `phase2_step2a_diagnose.py` establishes most of that additional
gap is run-to-run noise rather than real, exploitable signal (only 12 of 13 apparent per-question RAG-wins
are systematic across Phase-1's 3 runs).

Three prompt variants of a 3B-model LLM router were tested (`llm_router.py`; DOCS-first and few-shot
variants in `phase2_step3b_prompt_sensitivity.py`), each repeated 5x (`phase2_step3c_router_multirun.py`),
and scored on real end-to-end correctness/faithfulness using Phase-1's existing blind grades
(`phase2_step4_cost_of_misrouting.py` — no new generation or grading was needed, since routing only
selects between two answers Phase 1 already produced and graded for every question):

| condition | correct | faithful | stability | cross-disease cost vs oracle |
|---|---|---|---|---|
| oracle (per-question) | 70% | 98% | — | — |
| oracle (category) / **deterministic router** | 52% | 95% | **100%** | **0.0%** |
| LLM router B — DOCS-first | 53% (50–57%) | 94% | 55% | +15.0% |
| always-KG | 50% | 96% | — | — |
| LLM router A — baseline | 50% (49–52%) | 95% | 76% | +10.0% |
| LLM router C — few-shot | 49% (47–51%) | 94% | 78% | **+25.0%** |
| always-RAG | 43% | 88% | — | +75.0% |

No LLM-router variant robustly and stably beats a four-line deterministic rule (`FACTUAL_PATTERNS` in
`phase2_step2b_deterministic_router.py`) that requires zero LLM calls. The rule matches the category-level
oracle exactly, in every category, with perfect run-to-run stability. The one variant with a real (if
marginal) correctness edge over the rule — B, +1 point on average — is also the least self-consistent
(55%, i.e. routes almost half its questions differently from one call to the next) and carries a
quantified risk cost the rule does not: +15.0% correctness lost to oracle on cross-disease questions,
+4.3% on absence/negative questions.

## Against the pre-registered prediction

`Phase2_Plan.md` recorded this prediction before Step 3 ran:

> *"The LLM router will approach oracle routing on clearly-typed questions (factual, explicit
> cross-border) but lose ground on ambiguously-phrased ones. Its costliest errors will be routing
> absence / cross-border questions to document-RAG... Deterministic rules will be competitive on the
> clearly-cued categories."*

- **"Deterministic rules will be competitive on clearly-cued categories" — confirmed, and exceeded.** The
  rule did not merely stay competitive; it matched the full category-oracle ceiling exactly and
  outperformed two of three LLM variants on real correctness.
- **"Lose ground on ambiguously-phrased ones" — confirmed, sharply.** The single clearest case in the
  entire investigation is `xd_02` ("Is azoxystrobin used against only a single disease among the three
  studied?") — cross-disease reasoning stated implicitly rather than with explicit relational language
  (contrast `xd_01`, which is always routed correctly). Its misroute rate rose monotonically with prompt
  sophistication: 2/5 runs (A) → 3/5 (B) → 5/5, i.e. deterministic (C) — the opposite of what more
  instruction was intended to produce.
- **"Costliest errors will be routing absence / cross-border questions to RAG" — partially disconfirmed,
  informatively.** The risk category set (negative, cross_border, cross_disease) was correctly identified
  in `Phase2_Design.md`, but the specific costliest category was cross-disease, not negative or
  cross-border as the prediction named — the LLM routers rarely misrouted negative/cross_border questions
  in practice (cost near zero for A and C, +4.3%/-3.6% for B) but consistently struggled with the
  implicit-relational-language failure mode on cross-disease. The general risk framing held; the specific
  prediction of which risky category would dominate did not, and the reason (surface-cue dependence, not
  a general cross-disease reasoning deficit — `xd_01` proves the model *can* reason across diseases when
  the question states the relation explicitly) is itself a finding worth stating on its own.
- **"Approach oracle routing on clearly-typed questions" — weakly confirmed, with a caveat.** LLM routers
  did route cross-border and other KG-favoring categories to KG at high rates — but this largely
  reproduces baseline's default-to-KG behaviour rather than demonstrating calibrated judgment; the
  deterministic rule achieves the identical outcome on these categories without needing to "approach"
  anything, since it encodes the mapping directly.

## The tiered-trust implication

Phase 1's central design principle excluded the LLM from the retrieval-control path. Phase 2's motivating
sub-claim was that routing might be a *lower-stakes* place to reintroduce it: a misroute yields a
suboptimal-but-still-grounded answer, not a fabricated fact. **That structural claim holds** — nothing in
this investigation produced a hallucinated or ungrounded answer; every failure was a suboptimal arm
selection, exactly as designed. But *lower risk of catastrophic failure* is not the same question as
*worth delegating*, and on that second question the evidence is negative: an LLM router, even after two
rounds of prompt iteration and multi-run verification, does not produce a net benefit over a transparent,
auditable rule that a domain expert could write directly from the category definitions. Where the LLM
router's best variant does edge out the rule, it does so unstably and with a real, measured cost
concentrated on the exact category type the risk framework flagged as most consequential to get wrong.

For a regulated domain, the practical implication is specific rather than sweeping: **this decision, at
this model scale, should not be delegated to the LLM when a transparent rule achieves the same ceiling
with none of the instability or risk concentration.** This is not a claim that LLM routing is impossible
in general — a larger model, a different task, or a hybrid design (rule handles confidently-cued cases,
LLM is only consulted where the rule is unsure) are all open questions this investigation does not
settle, and are noted as future work rather than tested here.

## What would change this conclusion

- A larger local model showing materially higher stability and no growth in the cross-disease-cost gradient
  under few-shot prompting.
- A hybrid rule+LLM design that only calls the LLM outside the deterministic rule's confident cases, tested
  under the same multi-run + cost-of-misrouting protocol used here.
- Evidence that the `xd_02`-style implicit-relation failure mode is an isolated benchmark artifact rather
  than representative of a broader class of real-world questions — this has not been checked against a
  larger or independently constructed question set.

## Deliverables checklist (Phase2_Plan.md), final status

- [x] `oracle_results.json` + ceiling number (Step 1)
- [x] `phase2_step2b_deterministic_router.py` + results (Step 2)
- [x] `llm_router.py` + multi-run results, 3 prompt variants (Step 3 / 3b / 3c)
- [x] cost-of-misrouting analysis + results tables (Step 4)
- [~] Step 5 — not applicable; no new answers were generated by any router (stated in
  `Phase2_Step4_CostOfMisrouting.md`)
- [x] this document (Step 6)

## Addendum — corrected numbers (post-hoc, KG-arm disease-name bug)

`docs/Correction_KG_Disease_Name_Bug.md` and `Phase1_Results.md`'s addendum describe a bug found via
Phase 3's Step 1 diagnostic: 12 apple-scab/powdery-mildew questions' KG facts text incorrectly named
"late blight" regardless of actual disease, depressing KG's measured correctness on that subset. It has
been fixed, the affected answers regenerated and re-graded, and every table above has been recomputed
against the corrected grading data.

**What changed:**

| condition | correctness before | correctness after |
|---|---|---|
| always-KG | 50% | **62%** |
| always-RAG | 43% | 40% |
| oracle (category) / deterministic router | 52% | **64%** |
| oracle (per-question) | 70% | 74% |
| LLM router A — baseline | 50% | 62% |
| LLM router B — DOCS-first | 53% | 64% |
| LLM router C — few-shot | 49% | 60% |

**What did not change, qualitatively:**

- The deterministic router still matches the category-oracle ceiling exactly (now 64%/94% instead of
  52%/95%) — this is a mathematical property of how the rule is constructed, not something the correction
  could have disturbed.
- LLM router C — few-shot is still the worst-performing variant and still underperforms the naive
  always-KG baseline (60% vs 62%, previously 49% vs 50%) — the finding that proxy routing-accuracy metrics
  misled about C's real quality is unaffected.
- **The cross-disease cost gradient (A +10.0% → B +15.0% → C +25.0%) is numerically identical before and
  after** — `xd_01`/`xd_02` were never affected by the bug, so Phase 2's single most load-bearing finding
  is untouched.
- LLM router B still ties the deterministic router on average (64%) with the same wide run-to-run range
  (60–68%) and still carries real, nonzero cost on cross-disease and negative categories that the
  deterministic router does not — the "marginal, unstable, risk-bearing edge" characterization of B stands.

**What strengthened:** always-RAG's cost of misrouting on multi_hop (+12.5%→+50.0%) and cross_border
(−4.5%→+45.5%) rose sharply. This is not noise — it reflects that the pre-correction oracle/ceiling
comparison point was itself artificially low on categories containing the bugged questions, masking how
costly a RAG misroute on these categories really is. Post-correction, the case for routing multi_hop and
cross_border questions to KG is quantitatively stronger than originally reported, not weaker.

**Bottom line:** this correction changes magnitudes, not the shape of the conclusion. Every qualitative
claim in this document — deterministic routing matches the achievable ceiling and is the safer choice,
no LLM variant tested justifies its instability and risk profile over that rule, and the cross-disease
failure mode is real and gets worse with more prompt sophistication — survives the correction. The
corrected numbers are the ones that should be cited going forward; see
`docs/Phase2_Step4_CostOfMisrouting.md`'s own addendum for the full corrected cost-of-misrouting tables.