# Phase 3 — Hybrid Retrieval & Evidence Fusion: Execution Plan

*Companion to Phase3_Design.md. Ordered build/evaluation plan, mirroring Phase 1/2 discipline: design →
build → verify → evaluate → interpret, committing after each step. Unlike Phase 2, most of this phase
requires NEW LLM generation and NEW blind grading — fusion answers do not already exist in Phase-1 data,
because Phase 1 only ever ran each arm alone.*

---

## Step 0 — Freeze the inputs (prerequisite)

- Pin the current repo state (Phase 2 complete, `docs/Phase2_Results.md` committed) as the Phase-3 baseline
  commit, same convention as `phase2_step0_freeze.py`.
- Confirm `kg_arm.py`, `rag_arm.py`, `eval_pipeline.py` (the shared prompt/explain wrapper), and the
  51-question 3-disease benchmark are unchanged since Phase 2 froze them.
- **Produces:** a noted "Phase 3 baseline" reference.
- *No new code beyond a freeze/verify script — just pin what we're standing on.*

## Step 1 — Diagnose: do KG/RAG conflicts actually exist in this data?

- For every benchmark question, retrieve both `kg_arm.kg_facts(...)` and `rag_arm.rag_retrieve(...)`
  (both already deterministic, no LLM calls needed for this step) and compare them: do they state
  contradictory facts, is one silent where the other speaks, or are they simply redundant/consistent?
- **Produces:** `phase3_conflict_diagnosis.json` — a per-question classification (agree / redundant /
  one-sided-gap / apparent conflict) plus a handful of concrete examples of each.
- **Why first:** exactly the lesson from Phase 1's hierarchy-traversal category — do not build a
  conflict-handling evaluation on an assumption that conflicts exist. If they don't (KG and RAG are drawn
  from the same underlying BVL data, so genuine factual contradiction may be rare or absent), the Phase-3
  conflict metric needs to be scoped down honestly (see Design doc's scope discipline) rather than
  force-fit.
- **Verify:** manually read a sample of "apparent conflict" and "one-sided-gap" cases to confirm they are
  real, not artifacts of the RAG arm's top-k retrieval missing a relevant doc that exists elsewhere in the
  corpus.

## Step 2 — Build the fusion arm + pre-register prompts

- `src/fusion_arm.py`: a `fusion_facts(qid, question)` function that calls the existing `kg_arm` /
  `rag_arm` retrieval (no new retrieval logic) and returns both fact sets, labeled by provenance.
- Two prompt variants, pre-registered before any generation happens (same discipline as
  `llm_router.py`'s `ROUTER_PROMPT` — written from general principles, not tuned to any known answer,
  which is straightforward here since no fusion answers exist yet to tune against):
  - **Naive fusion prompt:** `SHARED_PROMPT` plus both fact sets concatenated, plus one added line: if the
    two sources disagree, say so rather than silently choosing one.
  - **Structured fusion prompt:** fact sets explicitly labeled ("KG FACTS (verified, authoritative)" /
    "RETRIEVED DOCUMENTS (may be incomplete)") with an explicit priority rule for conflicts (prefer KG for
    authorisation/relational facts, per Phase 1's finding; use RAG only to fill genuine gaps).
- **Produces:** `src/fusion_arm.py`, prompts committed in the same file/commit as this step (audit trail).

## Step 3 — Generate fusion answers (new LLM calls — unlike Phase 2)

- Run both fusion prompt variants over the full 51-question benchmark, **multi-run** from the start (Phase
  2's step 3c established that any LLM-involved condition must be checked under repetition before its
  numbers mean anything — no single-run fusion result should be reported as a finding).
- **Produces:** `data/phase3_fusion_answers.json` — raw generated answers, both variants, N runs each.
- **Verify:** spot-check a handful of answers by hand before committing to full blind grading, same
  "verify against authoritative sources rather than trusting pipeline outputs" practice used throughout.

## Step 4 — Blind grading

- Extend the Phase-1 blind-grading harness (`score_results.py`, grading-sheet conventions from
  `grading_sheet_BLIND.json`) to cover the new fusion answers: correctness + faithfulness as before.
- **If Step 1 confirms real conflict/gap cases exist:** add the third grading dimension from the Design
  doc (correctly-reflects-reliable-source / surfaces-disagreement / silently-picks-a-source /
  fabricates-synthesis) for those specific questions only.
- **Produces:** `phase3_grading_sheet_BLIND.json` + grading key, same format conventions as Phase 1/2 so
  existing scoring code (`score_results.py`, the `phase2_step1_oracle.py`-style aggregation) can be reused
  with minimal changes.

## Step 5 — Second grader / inter-rater agreement

- Grade a subset (or all, if time allows — Phase 1 graded the full set) with a second independent grader,
  compute Cohen's κ as in Phase 1 (`interrater_agreement.py`), for both the standard dimensions and, if
  applicable, the new conflict-handling dimension (which is more subjective and more likely to need
  validation).
- **Produces:** inter-rater agreement numbers; if κ is low specifically on the conflict dimension, that is
  reported honestly as a measurement-validity limitation, not smoothed over.

## Step 6 — Core analysis

- **Correctness & faithfulness:** naive fusion vs structured fusion vs Phase-2's deterministic-router
  baseline (52%) vs oracle-per-question ceiling (70%) — same table format as `Phase2_Step4_CostOfMisrouting.md`
  for direct comparability across phases.
- **Gain/loss per question vs the deterministic router:** does fusion help most on exactly the questions
  where routing had to discard useful evidence (the oracle-per-question vs oracle-category gap), or is any
  gain/loss spread unpredictably — mirrors the "systematic vs noise" check from `phase2_step2a_diagnose.py`.
- **Conflict-handling breakdown**, if applicable: rate of each outcome category on the conflict/gap
  subset specifically.
- **Multi-run stability:** does fusion's answer (and its correctness) change across repeated runs on the
  same question, same prompt — same check as `phase2_step3c_router_multirun.py`, applied here to answer
  quality rather than a routing label.
- **Produces:** `phase3_results_tables.json` + the comparison tables for the write-up.

## Step 7 — Interpretation & write-up

- Answer the Phase-3 RQ: does fusion beat the best single-arm baseline, how much of the oracle gap does it
  close, and does it preserve Phase 1's faithfulness discipline under real or constructed conflict?
- Report against the pre-registered prediction below — confirmed / disconfirmed, itemized, as done in
  `docs/Phase2_Results.md`.
- State the tiered-trust implication for this next rung: Phase 1 excluded the LLM from retrieval; Phase 2
  let it (or a rule) select between sources; Phase 3 asks it to reconcile them — does the evidence support
  that additional trust, or not?
- **Produces:** `docs/Phase3_Results.md`.

---

## Deliverables checklist

- [ ] `phase3_conflict_diagnosis.json` — do real conflicts exist? (Step 1)
- [ ] `src/fusion_arm.py` + pre-registered prompts (Step 2)
- [ ] `data/phase3_fusion_answers.json`, multi-run, both variants (Step 3)
- [ ] `phase3_grading_sheet_BLIND.json` + key (Step 4)
- [ ] inter-rater agreement numbers (Step 5)
- [ ] core analysis tables + conflict breakdown + stability check (Step 6)
- [ ] `Phase3_Results.md` interpretation (Step 7)
- [ ] committed after each step; documented for thesis + publication

## Pre-registered prediction (record before Step 3 runs)

Naive fusion will roughly match the deterministic router on questions where one source already dominates
(the added context is redundant there), but is expected to underperform on a nontrivial minority of
questions where the combined, longer context dilutes or confuses the 3B model's answer — consistent with
Phase 2's finding that additional prompt content does not reliably improve this model's behavior and can
introduce new failure modes (`Phase2_Step3c_MultiRunRobustness.md`). Structured fusion, given an explicit
source-priority rule, is expected to reduce silent-conflict-resolution failures relative to naive fusion,
but may increase hedging or abstention, which could lower correctness on questions a single source alone
would have answered confidently and correctly. Neither variant is expected to close more than a modest
fraction of the 52%→70% gap to the oracle-per-question ceiling — Phase 2 showed this model struggles to
reliably exploit fine-grained per-question signal even under direct instruction, and fusion asks more of it
(reconciliation) than routing did (selection). Report confirmation and disconfirmation honestly, as in
every prior phase.

## Scope discipline (see also Design doc)

- Reuse Phase 1/2 machinery wherever possible (both arms' retrieval, the grading harness, the scoring
  conventions) — Phase 3 adds a fusion layer and its evaluation, not a new pipeline.
- Do not reopen Phase 2's routing question; the deterministic router is the fixed single-arm baseline here.
- If Step 1 shows the current dataset has no real conflicts, do not manufacture a conflict narrative —
  scope the conflict-handling metric down honestly and say so, the same way Category 7 was handled in
  Phase 1.
- If a step reveals fusion is clearly worse or no better than the single-arm baseline with no nuance, that
  is a complete result — do not over-engineer additional fusion variants to force a more interesting story.