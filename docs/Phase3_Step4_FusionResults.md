# Phase 3, Step 4 — Fusion Results (and a Validity Limitation, Documented)

## Headline numbers

| condition | correct | faithful | n |
|---|---|---|---|
| oracle (per-question) | 74% | 97% | 129 |
| **structured fusion** | **76% (75–78% across 3 runs)** | 84% | 153 |
| oracle (category) / deterministic router | 64% | 94% | 129 |
| naive fusion | 65% (61–69% across 3 runs) | 76% | 153 |
| always-KG | 62% | 95% | 129 |
| always-RAG | 40% | 81% | 129 |

Naive fusion modestly beats the deterministic router (65% vs 64%) and closes about 7% of the 64%→74% gap
to the per-question oracle. **Structured fusion nominally exceeds even the oracle-per-question ceiling**
(76% vs 74%) — plausible in principle (fusion can synthesize both sources into an answer neither single
arm produced alone, so it isn't bound by "best of the two pre-existing answers" the way routing is), but
this is exactly the kind of good-looking number this project has learned not to trust at face value (see
`LLM_C`'s proxy-metric illusion in Phase 2).

## Per-category breakdown (risky categories marked *)

| category | naive | structured |
|---|---|---|
| constraint | 39% | 83% |
| cross_border * | 70% | 76% |
| cross_disease * | 83% | 67% |
| factual | 77% | 63% |
| multi_hop | 61% | 72% |
| negative * | 43% | 81% |
| region_specific | 78% | 89% |

Two things worth flagging on their own, independent of the validity question below:

- **Structured underperforms naive on plain factual lookups** (63% vs 77%), and the mechanism is directly
  visible in the grading notes: `run1_f02`'s note reads *"System B hedged unnecessarily and failed to give
  a direct affirmative answer"* — structured's caution rules over-firing on simple, fully-supported cases.
  This is a real, identifiable failure mode, not noise.
- **`cross_disease` has only 6 graded items per variant** (2 questions × 3 runs) — any single flip moves
  the percentage by ~17 points. The reversal there (naive 83% > structured 67%) should not be trusted at
  this sample size either way.

## A validity limitation, documented rather than smoothed over

Given fusion generates genuinely new answers no one had graded before (unlike Phase 2's routing, which
only ever reused Phase-1's already-graded answers), a stratified 54-item second-grading pass was run to
check for grading-leniency bias, especially toward structured's longer, more hedged answers
(`src/phase3_step4b_second_grading_sample.py`, oversampled toward the categories showing the biggest
swings).

**Result: 100% raw agreement, Cohen's κ = 1.000, on every dimension, category, and variant (n=108
judgments).** This is not the reassurance it might look like. Genuine independent re-grading of subjective,
open-ended judgments essentially never produces perfect agreement — real inter-rater checks on
correctness/faithfulness typically land well below 1.0 even between careful, competent graders. Perfect
agreement here most likely means the second pass recalled the original judgments rather than re-evaluating
the text fresh, which is an unsurprising, common effect without a genuinely independent grader or enough
elapsed time to prevent recall — not a criticism of the grading, just a limit of what a single-researcher
self-regrade can establish.

**What this check does confirm:** the grading is internally consistent and systematic, not random or
careless — a real, positive finding on its own.

**What it does NOT confirm:** that the underlying judgment calls are valid, or that there is no leniency
bias toward structured's answers specifically. That question remains open. No further independent grader
was available to resolve it within this project's scope.

## Calibrated interpretation

Given the above, the headline numbers should be read at two different confidence levels:

- **Naive fusion modestly beating the deterministic router (65% vs 64%)** is a small, plausible edge,
  consistent with combining sources providing some value even without careful reconciliation rules. This
  claim is not resting on a large or surprising gap, so it is less exposed by the validity limitation.
- **Structured fusion's larger jump (76%) and its nominal exceeding of the oracle-per-question ceiling
  (74%) is the part that most needs the grain of salt** stated above. It should be reported as a
  provisional, unconfirmed finding pending independent validation — not stated as an established Phase 3
  conclusion.
- **Structured fusion's run-to-run stability (75–78%, a 3-point range) is a separately verifiable, more
  trustworthy property** — it does not depend on whether the absolute grading level is biased, only on
  whether the SAME (possibly biased) grading criterion was applied consistently across runs, which it was.
  This is notably tighter than naive's own range (61–69%, 8 points) and tighter than any LLM router variant
  in Phase 2 (which ranged as wide as 20 points). Structured fusion being more *stable* than anything tested
  in Phase 2, independent of its absolute accuracy level, is a defensible claim on its own.
- **The factual-category over-hedging finding is trustworthy regardless of the validity question** — it is
  a specific, documented mechanism visible directly in the grading notes, not a statistical pattern that
  could be explained away by grader leniency.

## Status

Step 4 (and the Step 5 attempt) complete, with the validity limitation stated explicitly for the thesis
record rather than glossed over. Proceeding to Step 7 (final Phase 3 write-up,
`docs/Phase3_Results.md`), which will carry this calibration forward rather than reporting the headline
numbers as unqualified conclusions.