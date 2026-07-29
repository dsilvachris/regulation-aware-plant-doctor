# Phase 2, Step 3c — Multi-Run Stability & Robustness Check

Follow-on to `docs/Phase2_Step3b_PromptSensitivity.md`, which flagged that a single run per prompt variant
could not distinguish real prompt effects from LLM sampling noise (PROMPT A itself scored 1/12 systematic
RAG-wins in the original router run and 2/12 on an identical re-run). This step repeats each variant 5x
(`src/phase2_step3c_router_multirun.py`, N_RUNS=5, 765 total routing calls) and checks (1) whether each
variant's routing decisions are stable across runs, and (2) whether the step-3b comparison between variants
survives repetition.

## Results (5 runs/variant, 51 non-hierarchy questions)

| variant | acc vs oracle (mean, range) | systematic RAG-wins/run | factual→DOCS/run | stable questions |
|---|---|---|---|---|
| A — baseline | 84% (78–88%) | 1, 3, 2, 1, 1 | 3, 5, 3, 2, 1 | 39/51 (76%) |
| B — DOCS-first | 81% (75–86%) | 6, 4, 6, 5, 5 | 9, 8, 10, 7, 7 | 28/51 (55%) |
| C — few-shot | 91% (84–96%) | 4, 3, 5, 3, 4 | 9, 8, 9, 9, 10 | 40/51 (78%) |

Risky-category (negative / cross_border / cross_disease) misroutes to RAG:

| variant | consistent (every run) | intermittent (flips) |
|---|---|---|
| A | none | d05 (cross_border), xd_02 (cross_disease) |
| B | none | n02, n04, pm_n02 (negative); pm_d03 (cross_border); xd_02 (cross_disease) — 5 distinct items |
| C | **xd_02 (cross_disease) — 5/5 runs** | n04 (negative) |

## What survived repetition (real effects)

**B's RAG-win capture advantage over A is not noise.** A never exceeds 3/12 systematic RAG-wins across 5
runs; B never drops below 4/12. The ranges do not overlap. This confirms the step-3b finding: DOCS-first
ordering captures a genuinely larger share of the available routing headroom than baseline, consistently.

**C's cross-disease misroute is not noise — it is deterministic.** `xd_02` routes to RAG in all 5 of C's
runs. This is a reproducible failure mode of the few-shot prompt on that specific question, not one unlucky
sample — despite the prompt containing an explicit worked example teaching "joins facts across diseases →
KG."

## What the single step-3b run did not show

**B is the least stable variant, not the safest.** Only 28/51 questions (55%) route to the same arm on
every run under B, versus 76% under A and 78% under C. DOCS-first ordering does not just shift B's *average*
behaviour toward RAG — it makes individual routing decisions substantially less reproducible. A router that
answers differently on roughly 45% of questions from one call to the next is difficult to justify deploying
regardless of its mean performance.

**B's risky-category footprint is broader than step 3b suggested, not narrower.** The single step-3b run
showed zero risky misroutes for B; that was a favourable sample, not a property of the prompt. Across 5
runs, B intermittently misroutes 5 distinct risky-category questions (versus A's 2). None are consistent,
but "intermittent across more questions" is a real regression from what step 3b appeared to show.

**A specific, striking pattern: `xd_02` gets *worse* as the prompt is elaborated.** Misrouted in 2/5 runs
under A, 3/5 under B, 5/5 under C — monotonically increasing with the amount of instructional content in
the prompt. `xd_01`, the other cross-disease question, is routed correctly (KG) in every run of every
variant. This asymmetry is worth investigating at the question level — inspect the literal wording of
`xd_02` for a surface feature (e.g. a phrase that reads as a single-fact lookup) that may be driving this
independently of how the routing criteria are phrased. Not yet investigated.

## Revised conclusion

No variant dominates on all three axes that matter — RAG-opportunity capture, stability, and risky-category
safety:

- **A**: worst capture (mean 1.6/12), but narrowest and most stable risk profile (2 items, both intermittent)
- **B**: best capture (mean 5.2/12), but least stable overall (55%) and broadest intermittent risk footprint
  (5 items)
- **C**: best category-level accuracy and near-best stability (78%), but the only variant with a
  deterministic risky failure (xd_02, 5/5)

This is a stronger and more cautious finding than step 3b's provisional read, and it shifts the balance
toward **Conclusion A** (a 3B model cannot reliably do this routing) rather than Conclusion B (baseline's
failure was "just" the prompt). The improvement from reordering (B) is real but partial, and it is bought at
the cost of reliability: even the best-performing variant is only self-consistent on 55% of questions. That
argues the underlying routing judgment is fragile at the model level, not merely under-instructed at the
prompt level.

## Artifacts

- Script: `src/phase2_step3c_router_multirun.py`
- Raw per-run decisions + summaries: `data/phase2_router_multirun.json` (regenerable, not committed)

## Open items / next steps

1. Inspect `xd_02`'s question text directly — is there a plausible surface reason it reads as simpler than
   `xd_01`? This is a concrete, checkable next action before writing anything conclusive about the
   cross-disease category as a whole.
2. Decide the Phase-2 framing given this result: either (a) report the LLM-router line of investigation as
   a negative result — a 3B model's routing is too unstable to trust even under prompt iteration — and pivot
   Phase 2's contribution toward the oracle-ceiling / deterministic-router comparison instead, or (b) test
   whether a larger model (still local/feasible) shows the same instability, to establish whether this is a
   3B-specific limitation or general to LLM routing at this task. Not yet decided — worth a short discussion
   before committing further compute to either path.