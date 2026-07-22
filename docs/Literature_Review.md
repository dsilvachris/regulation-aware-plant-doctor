# Stage 1 — Literature Review

**Status:** draft. **Every citation below must be independently verified** (author, venue, year, and that
the work states what is claimed) before it is relied on. This review positions the KG-vs-document-RAG study;
it is not itself an experiment.

---

## 1. Scope and questions

The review covers: agricultural knowledge graphs; domain-specific KG design; knowledge representation for
regulatory systems; retrieval-augmented generation; KG-augmented retrieval; evaluation of KGQA and RAG;
trustworthy/explainable AI and selective prediction (abstention); and reusable agricultural vocabularies.

GraphRAG is reviewed to position the work, not as an implementation target: this project uses a **curated**
regulatory graph queried by **deterministic** logic, not an LLM-constructed graph.

---

## 2. Closest prior work and how this study differs

**Crop GraphRAG (Wu et al.)** — the nearest existing system: crop disease/pest QA over a graph.
Differences to state precisely (after verifying the paper):
- large models (Qwen3-30B, DeepSeek-R1) vs local 3B/8B here;
- community-summary / GraphRAG-style traversal (LLM-built graph) vs a curated graph with deterministic queries;
- **no regulatory / jurisdictional axis** — it answers "what disease / what treatment," not
  "what is authorised *here versus there*." This regulatory-divergence axis is the core distinction.

_(Add other close papers here as verified.)_

---

## 3. The gap this study addresses

Existing agricultural KG / QA work answers *what disease* and *what treatment*. None of the surveyed work
addresses **cross-border regulatory divergence** — the same disease requiring different *authorised* products
by country. If dedicated searches for "cross-jurisdictional / multi-jurisdiction regulatory knowledge
representation" (incl. pharma and food-safety framings) confirm this absence, it is the strongest positioning
claim: the contribution is a curated agricultural *regulatory* KG plus a benchmark for region-correct,
relationship-based regulatory queries.

**To confirm before finalising:** that the jurisdictional-divergence searches were actually run and returned
little — "found nothing" and "did not look" must not be conflated.

---

## 4. Evaluation approaches worth borrowing

| purpose | precedents (verify) | metric convention to mirror |
|---|---|---|
| RAG faithfulness | RAGAS, ARES, TruLens | faithfulness, context/answer relevance |
| multi-hop KGQA | MetaQA, ComplexWebQuestions, PullNet / GRAFT-Net | Hits@1, F1, EM |
| hallucination detection | HaluEval, SelfCheckGPT, TruthfulQA | hallucination rate, factual consistency |
| abstention / selective prediction | Self-RAG, SelfCheckGPT | (connects to this project's faithfulness work) |

**Design note.** Several RAG frameworks (RAGAS, ARES, TruLens) are *reference-free LLM-as-judge*. This study
uses **deterministic, blind, manual** grading instead — justified by (a) known LLM-judge biases and (b) the
safety-critical framing, where a graded human judgment is more defensible than an automated one. State this
choice explicitly rather than adopting an LLM judge by default.

Mirroring the multi-hop metric convention (Hits@1 / F1 / EM) keeps this study's relationship-query results
comparable to prior KGQA work.

---

## 5. Vocabularies / ontologies to reuse (Stage 3 input)

Reusing published identifiers beats inventing new ones (interoperability + citability). To investigate and verify:
- **EPPO codes** — already used for pathogens; check for a linked-data / URI form.
- **AGROVOC** (FAO thesaurus) — crops, pests, agricultural concepts.
- **Crop Ontology / Plant Ontology** — crop and plant-part URIs.

Open question for Stage 3: adopt external URIs directly, or map to them from local identifiers.

---

## 6. Still to search before closing Stage 1

- Legal / regulatory knowledge graphs and compliance ontologies (where cross-jurisdictional modelling would live).
- Agricultural vocabularies above (AGROVOC, crop/plant ontology, EPPO linked data).
- German- and Norwegian-language regulatory-informatics sources (national work often not in English).

---

## 7. Benchmark table (raw survey)

_Paste the AI_Evaluation_Benchmarks_Table here. Keep it as an appendix; the synthesis above is what feeds
Stages 2–3. Verify each row before citing._