# Feasibility Report — Knowledge Graph vs Document-RAG for Cross-Jurisdictional Agricultural Regulatory Reasoning

**Question this report answers:** is a controlled comparison of knowledge-graph vs document-based
retrieval for cross-jurisdictional plant-protection regulation a viable and worthwhile basis for a thesis
(and potentially a publication)?

**Short answer:** yes. A complete 7-stage study was executed end to end on real regulatory data from two
jurisdictions, producing a blind-graded, multi-run result with a defensible and non-trivial finding. What
follows summarises the evidence for feasibility, the result, and what a full thesis would add.

---

## 1. Motivation and gap

_(from Stage 1 — Literature_Review.md)_

Plant-protection regulatory knowledge graphs already exist (E-PHY/ANSES, France; C3PO; the GMRDF crop-pest
ontology, Greece) — so the contribution is **not** a first agricultural regulatory KG. Each models a
**single national jurisdiction**. Two gaps remain, and this study addresses both:

1. **Cross-border regulatory divergence** — the same crop and disease requiring different *authorised*
   products by country (a consequence of the EU's dual system: central active-substance approval, national
   product authorisation, Reg. (EC) No 1107/2009; non-EU EEA Norway diverges further). No prior
   single-jurisdiction system can express this.
2. **A controlled representation comparison** — no prior work holds the knowledge constant and compares a
   curated KG against an unstructured document collection within an identical pipeline.

Prior vocabularies are reused rather than reinvented: EPPO codes for pathogens, AGROVOC concepts for crops.

---

## 2. Method

_(from the adopted 7-stage methodology + Stages 0, 2, 5)_

- **Stage 0 — frozen baseline** as experimental control (`baseline-v1.0`).
- **Stage 2 — benchmark designed before implementation**: 7 categories with **pre-registered predictions**
  (factual [control], region-specific, multi-hop, constraint, negative/absence, cross-border divergence,
  hierarchy). Ground truth from official sources only.
- **Stage 3 — both arms built from identical data (data parity)**: an RDFLib KG (n-ary Authorisation node
  mirroring E-PHY's "Use") and a parallel prose-document set — same facts, different representation.
- **Stage 5 — identical pipeline, single variable**: same LLM (Llama 3.2 3B) and prompt for both arms;
  only retrieval differs (deterministic category-based SPARQL vs top-k semantic document retrieval). The
  KG arm's facts are verbalised to prose so the *only* difference is which facts, not their format. The LLM
  never writes queries — safety-critical retrieval stays deterministic.
- **Stage 6 — blind, multi-run evaluation**: 3 runs; answers anonymised (System A/B, shuffled) and graded
  blind against ground truth on **correctness** and **faithfulness** separately.

---

## 3. Data

_(from Stage 4)_

Authorised plant-protection products for late blight, from official regulators — Germany via the **BVL PSM
REST API**, Norway via **Mattilsynet** (manual extraction, each product verified against its official
label). Substance names normalised across German/English/Norwegian spellings so cross-border comparison
matches on chemistry, not string.

Authorised-product counts (the divergence, as data):

| disease | Germany | Norway |
|---|---|---|
| late blight | 112 | 4 |
| apple scab | 9 | 1 |
| cucurbit powdery mildew | 1 | 1 |

The asymmetry is a finding, not a gap: coverage was matched deliberately by disease; the divergence
reflects real regulatory difference (Norway actively restricts late-blight products).

---

## 4. Result

_(from Stages 6–7 — full detail in Stage7_Interpretation.md)_

**Correctness (KG vs RAG):** overall **41% vs 26%**; KG wins 5/6 categories; largest gaps in the predicted
relational/absence categories (multi-hop 67% vs 25%; negative 33% vs 8%). Region-specific lookup is the one
category document-RAG matches (48% vs 44%) — a healthy control result showing the KG does not win everything.

**Faithfulness inverts:** document-RAG is *more* faithful overall (**92% vs 82%**) — because when its
retrieval fails it tends to **abstain** ("no information about Norway") rather than fabricate, scoring as
faithful-but-unhelpful; while the KG's precise facts occasionally tempt the LLM to overclaim.

**Consistency:** the KG is stable across runs (38–46%); document-RAG swings widely (16–38%).

**Interpretation:** structured representation improves correctness and consistency *exactly where document
retrieval is weakest* — relationships, absence, cross-border comparison — at a manageable, addressable cost
to faithfulness. The finding is not "the KG wins" but a characterisation of *when and why* structure helps.
Both the positive result and its qualification were pre-registered as valid outcomes.

---

## 5. Feasibility assessment

**Is it viable?** Demonstrated — the full study ran end to end on real data, not a toy. Every dependency
that could have blocked it was tested: the BVL API is programmatically accessible; Norwegian data is
obtainable (manually); the graph builds and answers deterministically; the evaluation produces gradeable,
discriminating results.

**Is it worthwhile?** The result is non-trivial and defensible: a measured, blind-graded, multi-run
comparison with a nuanced correctness-vs-faithfulness trade-off — more credible than a clean sweep, and
directly tied to a gap no prior single-jurisdiction system addresses.

**Reproducibility:** frozen baseline (tagged), scripted extraction, pre-registered benchmark, blind grading
with a published key, all committed to version control.

---

## 6. What a full thesis would add

- Extend the KG beyond late blight to apple scab and powdery mildew (data already collected).
- Instantiate the open **hierarchy-traversal** category (BVL crop taxonomy).
- Address the **corpus-imbalance confound** (28:1 German docs) with balanced or country-aware retrieval.
- Larger model and/or a **hybrid** arm (KG precision + explicit abstention discipline) to recover
  faithfulness.
- Multiple graders / inter-rater agreement; more questions per category for tighter estimates.

---

## 7. Limitations

_(carried verbatim in spirit from Stage 7)_

Absolute performance is low (KG 41%) — this is a *relative* comparison under a small local model and strict
grading, not a deployable system. The German-dominated corpus partly confounds document-RAG's
region-specific failures. Single disease built into the graph; single blind grader; small per-category
counts. One honest document-RAG win (product mixtures, c03) was retained rather than engineered away.

---

## Conclusion

The study is feasible, was executed in full, and yields a publishable-shaped finding: representing identical
agricultural regulatory knowledge as a curated cross-jurisdiction knowledge graph improves correctness and
consistency over document-based RAG on relational, negative, and cross-border queries, while document-RAG
remains competitive on simple lookup and more faithful by abstaining. This is a sound basis for a thesis,
with clear, bounded extensions to strengthen it further.