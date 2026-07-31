# Phase 3 Results — Hybrid Retrieval & Evidence Fusion: Can Reconciliation Be Trusted?

*Synthesis chapter (Step 7 of `docs/Phase3_Plan.md`). Draws on the conflict diagnosis (`Phase3_Step1_ConflictDiagnosis.md`),
the fusion arm and its two bug-fixes (`Phase3_Step2_FusionArm.md`), generation and grading
(`Phase3_Step3_FusionGeneration.md`), and scoring with the validity check (`Phase3_Step4_FusionResults.md`).
This chapter answers the pre-registered RQ against that evidence; it does not introduce new results.*

## The research question

> **RQ (Phase 3): Does combining KG and RAG evidence for a single question improve correctness over the
> best available single-arm answer (Phase 2's deterministic router) and approach the per-question oracle
> ceiling — and when the two sources disagree or one is silent, does the system preserve Phase 1's
> faithfulness discipline (support every claim, abstain on gaps) or introduce a new failure mode
> (fabricated synthesis, silent conflict resolution, or unwarranted hedging)?**

(`docs/Phase3_Design.md`)

## Answer

**Naive fusion delivers a small, real improvement. Structured fusion delivers a larger one that cannot yet
be fully trusted, and both variants confirm at least one genuinely new failure mode fusion introduces that
routing never could.**

| condition | correct | faithful | stability (3-run range) |
|---|---|---|---|
| oracle (per-question) | 74% | 97% | — |
| structured fusion | 76% (provisional — see below) | 84% | 75–78% (tight) |
| oracle (category) / deterministic router | 64% | 94% | — |
| naive fusion | 65% | 76% | 61–69% (wide) |
| always-KG | 62% | 95% | — |
| always-RAG | 40% | 81% | — |

Naive fusion's edge over the deterministic router (65% vs 64%) is small and directly attributable to
combining sources providing some incremental value even without careful reconciliation rules. Structured
fusion's larger jump, and its nominal exceeding of the oracle-per-question ceiling, rests on a single
grader's judgment that a stratified second-grading check could not independently validate — perfect
self-agreement (κ=1.0) confirmed the grading is systematic, not that it is unbiased
(`Phase3_Step4_FusionResults.md`). That number is reported here as provisional, not confirmed.

## Against the pre-registered prediction

`Phase3_Plan.md` recorded this prediction before Step 3 ran:

> *"Naive fusion will roughly match the deterministic router on questions where one source already
> dominates... but is expected to underperform on a nontrivial minority of questions where the combined,
> longer context dilutes or confuses the model... Structured fusion... is expected to reduce
> silent-conflict-resolution failures... but may increase hedging or abstention, which could lower
> correctness on questions a single source alone would have answered confidently and correctly. Neither
> variant is expected to close more than a modest fraction of the 52%→70% gap [64%→74% after the disease-
> name-bug correction] to the oracle-per-question ceiling."*

- **"Naive will roughly match the deterministic router" — confirmed, closely.** 65% vs 64%.
- **"Naive will underperform on a minority of questions due to dilution/confusion" — confirmed, vividly.**
  The Step 2 demo caught this directly and repeatedly: naive fusion got `m01` wrong across multiple runs,
  pulled toward RAG's 8 off-topic German documents over KG's single clean, complete, on-topic fact — and
  naive's weakest categories (constraint 39%, negative 43%) are exactly the categories requiring precise
  reconciliation rather than a dominant single source.
- **"Structured will increase hedging, lowering correctness on confidently-answerable questions" —
  confirmed precisely, with a documented mechanism.** Structured scores *below* naive on plain factual
  lookups (63% vs 77%), and the grading notes name the cause directly: over-hedging on cases that had a
  clear, fully-supported answer.
- **"Structured will reduce silent-conflict-resolution failures" — suggestively supported, not rigorously
  confirmed.** Step 1 found no real KG/RAG factual conflicts in this dataset to test this against directly.
  The closest available evidence — the demo's `n02`/`m01` cases — shows structured consistently handling
  country-scoped evidence correctly where naive was inconsistent, but this is demo-level evidence, not a
  systematic measurement.
- **"Neither variant will close more than a modest fraction of the gap" — confirmed for naive (7%),
  disconfirmed on the numbers for structured (>100%, i.e. nominally exceeds the ceiling) — but the
  disconfirming evidence itself carries the validity caveat above.** This is reported as an open question,
  not a clean disconfirmation, precisely because the tool built to resolve it (the second-grading check)
  came back uninformative rather than negative.

## What Phase 3 also found that wasn't in the prediction

**A genuinely new failure mode: fusion can fabricate a synthesis and misattribute it to the verified
source.** The `xd_02` investigation (`Phase3_Step2_FusionArm.md`) found both fusion variants confidently
stating a specific, partly-wrong disease breakdown for azoxystrobin and explicitly citing "the KG facts" as
the source — when the KG facts named no such breakdown. An explicit prompt rule against inventing
specifics did not fix this; the actual fix required rewriting the ambiguous source template itself. This is
the most important methodological finding of the phase: **faithfulness failures caused by ambiguous fact
presentation cannot always be patched with "don't invent" instructions — sometimes the retrieval or
verbalisation layer itself has to change.** It also surfaced a pre-existing bug (a Phase-1-era template
ambiguity that had already caused one mis-graded answer, `run2_xd_02`, before Phase 3 began) — the second
time in this project that a downstream diagnostic caught an upstream data-presentation defect, after the
disease-name bug in Phase 2.

## The tiered-trust implication

Phase 1 excluded the LLM from retrieval entirely. Phase 2 let it (or a rule) select between two already-
verified sources — and found a transparent rule matched the achievable ceiling with none of the LLM's
instability. Phase 3 asked the LLM to do something neither prior phase required: reconcile two sources
together, potentially conflicting, into a single answer.

**The evidence here is genuinely mixed, and that is the honest finding, not a deferral.** Structured fusion
shows real promise — tighter run-to-run stability than anything tested in Phase 2, and it addressed the
country-attribution risk the design anticipated. But it also introduces a concrete new risk (over-hedging,
confirmed with a specific mechanism) and its most striking result (beating the oracle ceiling) is not yet
independently validated. Naive fusion is safer to characterize but delivers only a marginal gain. Neither
variant should be read as "reconciliation can now be trusted" or "reconciliation clearly cannot be
trusted" — the honest position is that **this rung of delegation is harder to evaluate confidently than
Phase 2's, the tooling built to resolve it (independent second-grading) did not fully succeed, and the
one clearly-confirmed new risk (fabrication traceable to ambiguous source phrasing, and over-hedging on
easy cases) is reason enough not to deploy structured fusion without further validation**, even though its
topline number is the best in the whole three-phase investigation.

## What would change this conclusion

- **A genuinely independent second grader** (not a self-regrade) on the full 153 items, or at least a
  larger, time-separated sample — the single most valuable next step, since it directly targets the one
  unresolved question in this chapter.
- **A conflict-focused test set**, independently constructed or drawn from a larger corpus where real
  KG/RAG disagreements are known to exist — Step 1 found none in this dataset, so the "does fusion handle
  real disagreement well" half of the RQ remains genuinely untested, not just unconfirmed.
- **A targeted fix for the over-hedging failure mode** (e.g. an explicit "answer directly when a single
  source fully supports the answer, hedge only when it doesn't" rule), tested under the same multi-run +
  independent-grading protocol this phase called for but could not fully execute.

## Deliverables checklist (Phase3_Plan.md), final status

- [x] `phase3_conflict_diagnosis.json` — no real conflicts found, scope discipline applied (Step 1)
- [x] `src/fusion_arm.py` + pre-registered prompts, two bugs found and fixed during the demo (Step 2)
- [x] `phase3_fusion_runs.json`, multi-run, both variants, with a documented provenance gap for 16 items
      (Step 3)
- [x] `phase3_grading_sheet_BLIND.json` + key, 153/153 graded (Step 4)
- [~] Second-grading / inter-rater check attempted — came back uninformative (perfect self-agreement),
      limitation documented rather than treated as a pass (Step 5)
- [x] Core analysis tables + validity-calibrated interpretation (Step 4/6)
- [x] this document (Step 7)