# Phase 2 — Adaptive Retrieval: Execution Plan

*Companion to Phase2_Design.md. This is the ordered build/evaluation plan — what we do, in what order, and
what each step produces. Each step is documented as it completes (thesis/publication-ready), mirroring the
Phase 1 discipline: design → build → verify → evaluate → interpret, committing after each.*

---

## Step 0 — Freeze the inputs (prerequisite)
- Confirm the Phase-1 artifacts Phase 2 builds on are stable: `kg_all.ttl`, `rag_docs_all.json`, the
  ~51-question 3-disease benchmark, the Phase-1 per-category results, and the two arms (`kg_arm`, `rag_arm`)
  behind the shared explanation wrapper.
- **Produces:** a noted "Phase 2 baseline" reference (Phase-1 results are the comparison point).
- *No new code — just pin what we're standing on.*

## Step 1 — Oracle routing (establish the ceiling) ★ start here
- Using the pre-registered optimal-arm-per-category mapping (in Phase2_Design.md), route each benchmark
  question to its optimal arm and score the resulting answers.
- Since Phase 1 already produced KG and RAG answers for every question, oracle routing = *select* the
  optimal arm's answer per question (no new LLM calls). Compute correctness + faithfulness.
- **Produces:** `oracle_results.json` + a ceiling number ("optimal routing achieves X% correct / Y% faithful").
- **Why first:** it's nearly free, and it defines the target every router is measured against. It also
  quantifies the *upside* of adaptivity vs the always-KG / always-RAG single-arm baselines.
- **Verify:** oracle should beat or equal both single-arm baselines by construction — if it doesn't,
  the optimal-arm mapping is wrong and we fix it before proceeding.

## Step 2 — Deterministic router (the no-LLM baseline)
- Build a rules/feature classifier: keyword + structural cues map a question to a strategy
  (e.g. "which/list ... substances/products across" → KG; "what pathogen causes" → either/RAG;
  "is X authorised / not" → KG absence; "both countries / differ" → KG cross-border).
- Route the benchmark through it; score end-to-end.
- **Produces:** `det_router_results.json` + routing-accuracy vs oracle.
- **Why:** isolates how much (if any) an LLM adds over simple rules. If rules already near-match oracle,
  that's a finding in itself (and the safer design).

## Step 3 — LLM router (the system under test)
- Fixed prompt: the LLM classifies each question into {KG, RAG} (or into the 7 categories → mapped to an
  arm — decide granularity here). The LLM classifies only; it never writes queries or answers from
  unverified text (Phase-1 principle preserved for everything downstream of the routing decision).
- Route the benchmark through it; score end-to-end, **multi-run** (the LLM router may be inconsistent).
- **Produces:** `llm_router_results.json` + routing decisions per run.
- **Verify:** log every routing decision so misroutes are auditable (which question, chosen arm, optimal arm).

## Step 4 — Core analysis: gap + cost of misrouting
- **Routing accuracy:** LLM router and deterministic router vs oracle (% sent to optimal arm).
- **End-to-end quality:** correctness + faithfulness for each condition (oracle / det / LLM / always-KG /
  always-RAG), blind-graded, multi-run, mean + spread — directly comparable to Phase 1.
- **Cost-of-misrouting:** for each misrouted question, the quality drop vs oracle, broken down by category,
  with explicit focus on the safety-critical categories (absence, cross-border) where the wrong arm fails
  worst. This is the heart of the contribution.
- **Router consistency:** does the LLM router route the same question the same way across runs?
- **Produces:** the Phase-2 results tables + the cost-weighted misrouting analysis.

## Step 5 — Blind grading + (if feasible) second grader
- Any *new* generated answers (from routing to an arm not used in Phase 1 for that question) get blind,
  multi-run grading as in Phase 1. Reuse Phase-1 grades where the routed arm+question already has them.
- Second grader on a subset for inter-rater agreement, as in Phase 1.
- **Produces:** validated Phase-2 scores.

## Step 6 — Interpretation & write-up
- Answer the Phase-2 RQ: how close does the LLM router get to oracle, and what does misrouting cost?
- Report against the pre-registered prediction (approaches oracle on clear questions; loses on ambiguous
  ones; worst misroutes are the costliest categories) — where it held, where it didn't.
- State the tiered-trust implication: does the evidence support delegating the *routing* decision to an LLM
  in a regulated domain, or not?
- **Produces:** `Phase2_Results.md` (thesis chapter / paper section material).

---

## Deliverables checklist
- [ ] `oracle_results.json` + ceiling number (Step 1)
- [ ] `det_router.py` + `det_router_results.json` (Step 2)
- [ ] `llm_router.py` + `llm_router_results.json`, multi-run (Step 3)
- [ ] cost-of-misrouting analysis + results tables (Step 4)
- [ ] blind grades + inter-rater agreement (Step 5)
- [ ] `Phase2_Results.md` interpretation (Step 6)
- [ ] committed after each step; documented for thesis + publication

## Pre-registered prediction (record before Step 3 runs)
The LLM router will approach oracle routing on clearly-typed questions (factual, explicit cross-border) but
lose ground on ambiguously-phrased ones. Its costliest errors will be routing absence / cross-border
questions to document-RAG, where Phase 1 showed that arm fails hardest. Deterministic rules will be
competitive on the clearly-cued categories. Report confirmation and disconfirmation honestly.

## Scope discipline (avoid ballooning)
- Phase 2 is *routing only*. It does NOT build the hybrid/fusion system (that is Phase 3 — combining both
  arms' evidence for a single question). Keep them separate; do not drift into fusion here.
- Reuse Phase-1 machinery (benchmark, arms, grading harness, scorer) — Phase 2 adds a router layer on top,
  not a new pipeline.
- If a step reveals the LLM router is clearly worse/better than oracle with no nuance, that's a complete
  result — don't over-engineer to force a more interesting story.