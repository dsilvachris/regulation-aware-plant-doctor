# Thesis Structure & Source Map

**Working title:** Trustworthy Regulation-Aware Retrieval: A Controlled Comparison of Knowledge-Graph
and Document-Based RAG for Cross-Jurisdictional Agricultural Regulation

> **BEFORE DRAFTING FULL CHAPTERS:** confirm your programme's required thesis template (chapter order,
> whether Related Work is standalone, word limits, abstract format). This outline is standard academic
> structure and maps to most requirements, but verify against your handbook / supervisor first.

**Legend:** [WRITTEN] = existing doc covers it · [ADAPT] = existing doc needs reshaping into prose ·
[NEW] = must be written fresh · [THIN] = have material but needs expansion.

---

## Abstract  [NEW]
~250 words. The gap (single-jurisdiction KGs), the study (controlled KG-vs-RAG on identical data across
DE/NO), the headline result (KG improves correctness + consistency; RAG more faithful via abstention in the
single-disease run; cross-disease KG 100% vs 25%), validated blind (κ 0.99/1.00). Write LAST.

## Chapter 1 — Introduction  [ADAPT from Feasibility_Report §1 + one-page summary]
- Motivation: regulation-aware AI, faithfulness over confidence.
- Problem: cross-jurisdictional regulatory divergence; why single-jurisdiction systems can't express it.
- Research questions (state explicitly — see below).
- Contributions (bulleted).
- Thesis outline (one line per chapter).

## Chapter 2 — Background & Related Work  [WRITTEN: Literature_Review.md + Verification_Register]
- Regulatory KGs: E-PHY, C3PO, GMRDF — all single-jurisdiction (the gap).
- RAG vs KG-augmented retrieval; faithfulness/hallucination literature.
- Evaluation methods (RAGAS/ARES; why blind manual grading chosen).
- Vocabularies reused: EPPO, AGROVOC.
- *Source is solid — Literature_Verification_Register_v3 gives you citation confidence.*

## Chapter 3 — Methodology  [WRITTEN: Benchmark_Design_Stage2 + methodology from Feasibility §2]
- The 7-stage controlled-comparison design; data-parity principle.
- Benchmark: 7 categories + pre-registered predictions (the bias-control mechanism).
- Deterministic-query principle (LLM never writes queries).
- Blind, multi-run, multi-grader evaluation protocol.
- *This chapter is your methodological backbone — it's already well-documented.*

## Chapter 4 — Data & Knowledge Graph Construction  [ADAPT: Feasibility §3 + Stage 3/4 notes + crop addendum]
- Sources: BVL PSM API (DE), Mattilsynet (NO); extraction + verification discipline.
- The divergence data (112/4, 9/1, 1/1; substance-divergence-at-parity in mildew).
- KG schema: n-ary Authorisation node (E-PHY "Use" parallel); EPPO/AGROVOC identifiers.
- Substance normalisation; real crops from awg_kultur.
- Parallel RAG document construction (data-parity).

## Chapter 5 — Evaluation & Results  [WRITTEN: Stage7_Interpretation + Phase1_Results]
- Both arms (KG / document-RAG), shared LLM + prompt.
- Single-disease result (Stage 6): KG 41% vs 26% correct; faithfulness inversion.
- Three-disease result (Phase 1): KG 50% vs 43%; cross-disease 100% vs 25%; faithfulness now KG-ahead.
- The faithfulness-flip analysis (82%→95% on identical Qs — proven pipeline effect).
- Inter-rater agreement (κ 0.99/1.00).
- Consistency across runs.

## Chapter 6 — Discussion  [ADAPT from Stage7 interpretation + Phase1 findings]
- When/why structure helps (relational, absence, cross-border, cross-disease).
- The correctness↔faithfulness tension (your most sophisticated finding).
- Practical implication: hybrid (KG precision + abstention discipline).
- Threats to validity: corpus imbalance, absolute numbers, small counts.

## Chapter 7 — Limitations & Future Work  [WRITTEN: limitations across Stage7/Phase1 + crop addendum]
- Limitations: single grader→resolved (κ); low absolute numbers; corpus imbalance; single-model.
- Category 7 not-instantiable (pre-registered, data flat for these crops) — honest negative.
- Future: hybrid arm; other domains (healthcare/finance/legal); larger models; hierarchy on cereals.
- (This is Programme B from the supervisor split.)

## Chapter 8 — Conclusion  [ADAPT: Feasibility conclusion]
- Restate contributions, the nuanced result, and what it means for trustworthy regulatory AI.

## Appendices  [WRITTEN: your data + code]
- Benchmark questions + ground truth; KG schema; key SPARQL; repo link; grading protocol.

---

## Research questions (draft — refine with supervisor)
- RQ1: Does representing regulatory knowledge as a curated KG improve answer correctness over document-RAG
  on identical data?
- RQ2: How does representation affect faithfulness (avoiding unsupported claims)?
- RQ3: On which query types does structure help most — and where does document retrieval suffice?
- RQ4: Can a KG express cross-jurisdictional (and cross-disease) regulatory relationships that
  single-jurisdiction / document approaches cannot?

## What's already written vs. what's new
- **Strong / mostly written:** Ch 2, 3, 5 (your stage docs are essentially chapter drafts).
- **Adapt existing prose:** Ch 1, 4, 6, 8.
- **Genuinely new writing:** Abstract, RQ framing, connective tissue between chapters, and expanding
  Discussion into full argument.
- **Biggest single task:** Chapter 4 (weaving Stage 3+4+crop work into one narrative) and Chapter 6
  (turning findings into a discussion argument rather than a results list).