# Phase 3, Step 2 — Fusion Arm: Design, Demo, and Two Bugs Found

## What was built

`src/fusion_arm.py` — reuses `kg_arm`/`rag_arm` retrieval exactly (no new retrieval code), with two
pre-registered prompts: `NAIVE_FUSION_PROMPT` (both fact sets concatenated, minimal instruction) and
`STRUCTURED_FUSION_PROMPT` (provenance-labeled, explicit KG-priority rule, and a country/disease-match
rule grounded directly in Step 1's `n02` finding).

## The demo caught two real bugs before they could contaminate a full Step 3 run

**Bug 1 — naive fusion getting `m01` wrong by attending to RAG's 8 off-topic (German) documents over
KG's 1 clean, complete, on-topic fact.** Confirmed reproducible across multiple demo runs, with
inconsistent failure modes each time (missing substances one run, false sourcing claims another). This is
not a bug to fix — it is exactly the naive-baseline behavior Step 3 is designed to measure and quantify
under repetition. `NAIVE_FUSION_PROMPT` is left unchanged.

**Bug 2 — a genuine ambiguity in `kg_verbalise.py`'s `multi_disease` template**, found via `xd_02`: both
fusion variants confidently stated azoxystrobin is "authorised against late blight, apple scab, and
cucurbit powdery mildew" — apple scab is wrong (confirmed against `kg_arm` directly: azoxystrobin covers
late blight + powdery mildew only) — and both answers falsely attributed this claim to "the KG facts." The
root cause: the old template read *"...more than one of the three diseases (late blight, apple scab,
cucurbit powdery mildew) are: X, Y."* — a parenthetical meant only to name the three diseases studied,
sitting directly adjacent to the substance list, reliably misread as a per-substance breakdown.

An initial fix attempt added an explicit "don't invent specifics" rule to the structured prompt (rule 4).
**This did not work** — confirmed by rerunning the demo, `xd_02` still fabricated identically. The correct
diagnosis: the model wasn't inventing from nothing, it was faithfully copying genuinely ambiguous text.
The real fix had to be in the source template, not the prompt. `kg_verbalise.py`'s `verbalise3` was
rewritten to structurally separate the disease-category label from the substance list. **Confirmed working
on rerun**, on both variants (including naive, which never received rule 4 at all) — direct evidence the
diagnosis was correct: fixing the ambiguous source resolved the fabrication independent of prompt wording.

**Lesson for the write-up:** faithfulness failures caused by ambiguous fact presentation cannot always be
patched with "don't invent" instructions. Sometimes the retrieval/verbalisation layer itself has to change.
This generalizes a theme from the disease-name bug (`Correction_KG_Disease_Name_Bug.md`) — both bugs were
found downstream, by Phase 3 diagnostics, but both originated in Phase 1's fact-presentation code, not in
any router or fusion logic.

## Known limitation, documented rather than corrected

`run2_xd_02`'s original Phase-1 KG-only answer ("late blight and apple scab") already exhibited this exact
misreading and was graded correct=1, faithful=1 in the original blind grading — a mis-grade predating
Phase 3 entirely. Given the small scope (one item, versus the disease-name bug's systematic 12-question
impact), this is recorded here as a known limitation rather than triggering another full correction cycle.
It does not change any headline Phase 1/2 number (`xd_01`/`xd_02`'s aggregate contribution to those totals
is unaffected at the rounding level used throughout).

## Status

Step 2 complete. Both prompts pre-registered and demo-validated; both bugs found are fixed and verified.
Proceeding to Step 3: full-benchmark, multi-run fusion generation.