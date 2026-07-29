# Phase 3 — Hybrid Retrieval & Evidence Fusion: Design

*Programme B, Phase 3. Documented to thesis/publication standard, mirroring Phase 1 and Phase 2 discipline:
design → build → verify → evaluate → interpret, committing after each step.*

## Motivation

Phase 1 established that KG and document-RAG have complementary strengths (KG wins relational, absence,
cross-border, cross-disease; RAG matches on simple lookup and is more faithful by abstaining). Phase 2
asked whether a system could *choose* the better arm per question, and found: a simple deterministic rule
matches the achievable category-level ceiling (52% correctness) exactly, and no LLM-router variant tested
beats it once measured on real answer quality, stability, and risk together
(`docs/Phase2_Results.md`).

Routing is exclusive by construction — for a given question, the system commits to *one* arm's evidence and
discards the other, even when the discarded arm might have contained a fact the chosen arm lacked. The
per-question oracle ceiling (70% correctness, `phase2_step1_oracle.py`) exists precisely because sometimes
the "wrong" arm for a category still happens to answer a specific instance correctly — evidence that gets
thrown away under routing. The natural next question:

> **What if the system didn't have to choose — what if it used both arms' evidence together?**

This is *evidence fusion*: retrieving via both KG and RAG for the same question (both retrievals are already
deterministic, per Phase 1's principle) and letting the answering step draw on both simultaneously, rather
than on whichever single arm was selected.

## The core research tension

Phase 1's principle: retrieval is deterministic, the LLM only phrases already-verified facts, and abstains
when the facts don't support an answer. Phase 2 kept this fully intact — routing only decided *which*
already-verified fact set to hand the LLM; the LLM never combined or reconciled anything.

Fusion changes this. When both sources are handed to the LLM together, it must now do something Phase 1 and
Phase 2 never asked of it: **reconcile two evidence sources that may agree, may be redundant, may disagree,
or may leave one silent where the other speaks.** This is a materially higher-stakes decision than routing.
A misroute in Phase 2 costs you the better arm's answer; a fusion failure could actively fabricate a
synthesis that neither source supports, or silently prefer one source over a real conflict without
surfacing it — undermining exactly the faithfulness discipline that made Phase 1's comparison trustworthy
in the first place.

Phase 3 does not assume fusion is beneficial or safe. It measures both, with the conflict-handling question
treated as a first-class outcome, not an afterthought:

> **RQ (Phase 3): Does combining KG and RAG evidence for a single question improve correctness over the
> best available single-arm answer (Phase 2's deterministic router) and approach the per-question oracle
> ceiling — and when the two sources disagree or one is silent, does the system preserve Phase 1's
> faithfulness discipline (support every claim, abstain on gaps) or introduce a new failure mode
> (fabricated synthesis, silent conflict resolution, or unwarranted hedging)?**

This is the next step in the thesis's tiered-trust theme: Phase 1 kept the LLM out of retrieval entirely;
Phase 2 let it (or a rule) select between verified sources; Phase 3 tests whether it can be trusted to
reconcile them.

## What already exists to build on

Both arms already retrieve deterministically for every benchmark question and funnel through the same
prompt template, differing only in the `{facts}` content (`src/eval_pipeline.py`):

- `kg_answer_by_id(qid, question)` → `kg_arm.kg_facts(...)` (deterministic SPARQL, routed per-question via
  the hand-written `ROUTING` table) → verbalised to text.
- `rag_answer(question)` → `rag_arm.rag_retrieve(question, k=8)` (semantic top-k over the same underlying
  data rendered as prose).
- Both call the identical `explain(question, facts_text)` / `SHARED_PROMPT`.

Fusion is therefore a small, well-scoped addition, not a new pipeline: retrieve via both existing arms
(no new retrieval code needed), combine the two fact sets with clear provenance labels, and answer with a
fusion-specific prompt that explicitly extends `SHARED_PROMPT`'s faithfulness instruction to cover
disagreement between sources.

## Design

### Conditions compared

1. **Best single-arm baseline.** Phase 2's deterministic router (matches the category-oracle ceiling
   exactly, 52% correctness, `Phase2_Step2b_DeterministicRouter.md`). This is the bar fusion must clear to
   justify its added complexity and risk surface.
2. **Naive fusion.** Both fact sets concatenated with minimal structure (KG facts, then RAG docs), answered
   with a fusion prompt that is `SHARED_PROMPT` plus one added instruction: if the two sources conflict,
   say so rather than picking one silently. Tests whether simply giving the model more (verified) context
   helps or dilutes/confuses it.
3. **Structured, provenance-labeled fusion.** Facts are explicitly tagged by source ("KG FACTS (verified,
   authoritative):" / "RETRIEVED DOCUMENTS (may be incomplete):") with an explicit conflict-resolution
   policy in the prompt (prefer KG for authorisation/relational facts per Phase 1's finding that KG is the
   stronger arm there; use RAG only to fill gaps KG's deterministic query didn't cover). Tests whether
   giving the model a stated priority rule, rather than leaving reconciliation open-ended, changes outcomes.
4. **(Reference) oracle per-question ceiling.** 70% correctness, already established
   (`phase2_step1_oracle.py`) — the natural target fusion should be compared against, since fusion has
   access to *both* arms' evidence for every question, i.e. strictly more information than any single-arm
   choice.

### What "conflict" means here, and whether it exists in the data (must be checked, not assumed)

Before building a conflict-focused evaluation, it must be verified that KG/RAG disagreements actually occur
in the current 3-disease dataset — Phase 1's hierarchy-traversal category was pre-registered but turned out
not to be instantiable in the data, and that lesson applies here too. A short diagnostic step (proposed as
Step 1 below) checks, for every benchmark question, whether the KG-arm's facts and the RAG-arm's retrieved
docs actually conflict, are redundant, or leave a genuine gap (one source states something the other is
silent on). Only if real conflict/gap cases exist is a dedicated conflict-focused sub-benchmark meaningful;
if the current data is too clean (KG and RAG effectively agree everywhere they overlap), that is reported
as a pre-registered category the data could not support, exactly as Category 7 was in Phase 1.

### Metrics

- **Correctness & faithfulness** — the Phase 1/2 metrics, unchanged in definition, now requiring NEW
  generation and NEW blind grading (unlike Phase 2 — fusion produces answers that don't already exist in
  Phase-1 data; see Step 5).
- **Conflict handling (new metric, needed only if Step 1 confirms conflicts exist)** — for questions where
  the two sources disagree or one is silent, a third grading dimension: did the answer (a) correctly
  reflect the more reliable source, (b) surface the disagreement/gap explicitly, (c) silently pick a source
  without justification, or (d) fabricate a synthesis unsupported by either source? (a) and (b) are
  acceptable outcomes; (c) is a faithfulness violation; (d) is the worst-case failure this phase is designed
  to catch. Grading rubric to be finalized once Step 1 shows what real cases look like.
- **Gain over best single-arm and gap to oracle-per-question** — the two headline numbers: does fusion beat
  52% (the ceiling routing alone can already reach for free), and how much of the 52→70 gap does it close.

## Risk framing (carried over from Phase 2's discipline)

Phase 2 showed that adding LLM judgment without measuring it under repetition produces misleading proxy
results (`LLM_C_few_shot` looked best on category accuracy and was in fact the worst on real correctness).
Fusion has strictly more surface area for this kind of illusion — a fused answer can *look* more thorough
(longer, cites more) while being less faithful. Every fusion variant will therefore be run multi-run (as
Phase 2's step 3c established is necessary for LLM-involved conditions) and scored on real blind-graded
correctness/faithfulness before any conclusion is drawn from a cheaper proxy.

## Scope discipline (avoid ballooning, per Phase 2's own note)

- Phase 3 is *fusion of already-retrieved evidence only*. It does not change how either arm retrieves
  (both stay exactly as built in Phase 1), and it does not reopen the routing question (Phase 2's
  deterministic router remains the single-arm baseline, not up for re-litigation here).
- It does not introduce a third retrieval strategy or external data source.
- If Step 1's diagnostic shows the current 3-disease dataset has no real KG/RAG conflicts to test, the
  conflict-handling metric is scoped down to a smaller, possibly synthetic/adversarial probe set (clearly
  labeled as such) rather than force-fitting a conflict narrative onto data that doesn't have one — same
  honesty standard as Phase 1's hierarchy-traversal finding.