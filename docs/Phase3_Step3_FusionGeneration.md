# Phase 3, Step 3 — Fusion Generation & Grading: Complete

## Generation

`src/phase3_step3_fusion_generate.py --runs 3` — 51 questions x 3 runs x 2 variants (naive, structured) =
306 LLM calls. Raw output: `data/phase3_fusion_runs.json`.

## Grading

`data/phase3_grading_sheet_BLIND.json` — 153 items (51 questions x 3 runs), blind (System A/B, naive vs
structured shuffled per item), graded against each question's pre-registered `answer` field in the
benchmark files. **153/153 complete, all grade fields valid, no duplicates, verified against the key
(`data/phase3_grading_key.json`).**

## Known data-provenance note: 16 run3 items

During grading, a system crash interrupted the session; `data/phase3_fusion_runs.json` was recovered from
a backup taken after a re-run of the generation step. Ollama's output is not deterministic run-to-run, so
the recovered file's `run3` content differs from what was shown for the **first 16 `run3` items already
graded before the crash** (`f01`–`f10`, `r01`, `r02`, `m01`, `m02`, `c01`, `d01`). The remaining 35 `run3`
items were graded against the recovered file directly (reconstructed and handed back for grading after the
gap was found), so those match exactly.

**What this does and doesn't affect:**
- Does NOT affect grade validity — each of the 16 items' `grade_*` fields and notes are legitimate
  judgments of the exact text that was shown at grading time; that text remains preserved in the sheet
  itself (the sheet is self-contained, not re-derived from the raw file at scoring time).
- DOES mean those 16 items are not re-derivable from the currently-committed `phase3_fusion_runs.json` —
  a reproducibility gap, stated here rather than left implicit.
- Decision (consistent with the `run2_xd_02` precedent in `Correction_KG_Disease_Name_Bug.md`): given the
  small scope (16 of 153 items, all pre-existing valid grades, no known incorrect grades caused by this),
  this is documented as a known limitation rather than triggering a re-generation + re-grading cycle.

## Status

Step 3 complete. Proceeding to Step 4: score naive vs structured fusion against the deterministic-router
baseline (64%) and the oracle-per-question ceiling (74%) from Phase 2, using the same scoring conventions
throughout this project.