# Stage 1 — Literature Review

**Status:** closed for Stage 1. Citations are tracked in `Literature_Verification_Register_v3.md`; each was
confirmed against the official publication before inclusion. Two peripheral benchmark entries (MetaQA,
Self-RAG) remain marked *Partial* in the register pending DOI/BibTeX collection and are cited lightly.

This review positions the Knowledge-Graph vs document-RAG study; it is not itself an experiment.

---

## 1. Scope and questions

The review covers: agricultural knowledge graphs; domain-specific KG design; knowledge representation for
regulatory systems; retrieval-augmented generation (RAG); KG-augmented retrieval; evaluation of KGQA and
RAG; trustworthy and explainable AI and selective prediction (abstention); and reusable agricultural
vocabularies.

GraphRAG is reviewed to position the work, not as an implementation target: this project uses a **curated**
regulatory graph queried by **deterministic** logic, not an LLM-constructed graph.

---

## 2. Related work

**Agricultural and regulatory knowledge graphs.** Several systems represent crop-protection and regulatory
knowledge as ontologies or knowledge graphs. E-PHY (ANSES, France) is an open catalogue of authorised and
withdrawn plant-protection products, with an ontology representing product, active-substance and use data.
C3PO (Darnala et al.) is a crop planning and production ontology and knowledge graph that integrates
chemical-product data via the E-PHY model. The GMRDF crop-pest ontology (Damos et al., 2017) represents the
Greek Ministry of Rural Development and Food's crop-protection data as a semantic knowledge graph. These
establish that curating national crop-protection regulatory data as a graph is feasible and useful.

**Graph-augmented retrieval and reasoning.** PullNet, GraphRAG, and Crop GraphRAG demonstrate that
structured knowledge can improve retrieval and multi-hop reasoning for domain-specific question answering,
generally using large language models and, in the GraphRAG lineage, LLM-constructed graphs.

**Evaluation.** RAG faithfulness frameworks (e.g. RAGAS, ARES, TruLens) and multi-hop KGQA benchmarks
(e.g. MetaQA, ComplexWebQuestions, PullNet) provide established metrics — faithfulness and context/answer
relevance on the RAG side; Hits@1, F1 and exact match on the KGQA side. Selective-prediction work
(e.g. Self-RAG, SelfCheckGPT) connects to this project's abstention behaviour.

---

## 3. The gap this study addresses

Existing research has demonstrated that agricultural regulations can be represented using ontologies and
Knowledge Graphs, including systems such as E-PHY (ANSES, France), C3PO (Darnala et al.), and the GMRDF
crop-pest ontology (Damos et al., 2017, Greece). Likewise, graph-enhanced retrieval approaches, including
PullNet and Crop GraphRAG, have shown that structured knowledge can improve retrieval and reasoning for
domain-specific question answering.

However, these regulatory Knowledge Graphs each model a single national jurisdiction. No existing work
represents *cross-border regulatory divergence* — the situation in which the same crop and disease require
different authorised treatments depending on the country. This divergence is a direct consequence of the
EU's dual authorisation structure, in which the Commission approves active substances centrally while each
Member State authorises products on its own territory (Regulation (EC) No 1107/2009), with non-EU EEA
states such as Norway diverging further.

Furthermore, no study has systematically compared two alternative representations of identical agricultural
regulatory knowledge — a curated Knowledge Graph and an unstructured document collection — within an
otherwise identical Retrieval-Augmented Generation pipeline. Consequently, there is limited evidence on
whether a curated Knowledge Graph improves retrieval quality, provenance, explainability, and regulatory
correctness relative to document-based RAG.

This thesis addresses both gaps: it constructs a curated, cross-jurisdiction agricultural regulatory
Knowledge Graph, and uses it to run a controlled comparison in which identical regulatory content is
expressed as a graph and as documents — isolating the effect of the knowledge representation itself.

---

## 4. Evaluation approaches worth borrowing

| purpose | precedents | metric convention to mirror |
|---|---|---|
| RAG faithfulness | RAGAS, ARES, TruLens | faithfulness, context/answer relevance |
| multi-hop KGQA | MetaQA, ComplexWebQuestions, PullNet | Hits@1, F1, exact match |
| hallucination detection | HaluEval, SelfCheckGPT, TruthfulQA | hallucination rate, factual consistency |
| abstention / selective prediction | Self-RAG, SelfCheckGPT | (connects to this project's faithfulness work) |

**Design note.** Several RAG frameworks (RAGAS, ARES, TruLens) use reference-free LLM-as-judge scoring.
This study instead uses **deterministic, blind, manual** grading, justified by (a) known LLM-judge biases
and (b) the safety-critical framing, where a graded human judgment is more defensible than an automated
one. Mirroring the multi-hop metric convention (Hits@1 / F1 / EM) keeps the relationship-query results
comparable to prior KGQA work.

---

## 5. Vocabularies / ontologies to reuse (Stage 3 input)

- **AGROVOC (FAO).** Multilingual agricultural thesaurus published as linked data (SKOS, dereferenceable
  URIs), aligned to ~10 other agricultural knowledge-organisation systems, queryable via a Skosmos REST API
  and a public SPARQL endpoint. Reuse for crop and general agricultural-concept URIs; multilingual coverage
  is relevant given German and Norwegian sources.
- **Crop Ontology + Planteome (Plant Ontology, Trait Ontology).** FAIR reference ontologies with public
  URIs, hosted on AgroPortal / OLS. These are plant-biology / genomics / trait ontologies, not
  disease-treatment or regulatory — use for crop and plant-part identifiers only; build the disease and
  regulatory layer separately.
- **EPPO ontology / EPPO codes.** Pathogens are already identified by EPPO codes in the baseline; an EPPO
  ontology exists (Frontiers, 2023). Reuse EPPO identifiers for pathogens rather than minting new ones.
- **AgroPortal.** Hosts ~150 agricultural ontologies (including FoodOn and the Agronomy Ontology). Consult
  before introducing any new identifier — reuse-first is the defensible choice.

**Schema reuse (Stage 3).** Reuse E-PHY's validated model (Product → Active substance → Use → Crop) and the
EU active-substance-vs-product distinction rather than inventing entities.

---

## 6. Data obtainability (feasibility, informing Stage 4)

- **Germany (BVL):** public PSM REST API (`psm-api.bvl.bund.de`), JSON queries, monthly updates, open
  licence, mandated by Article 57 of Regulation (EC) No 1107/2009. Crops are hierarchical
  (cereals → wheat → winter wheat) — a native graph-traversal case for the benchmark.
- **France (E-PHY):** open XML/CSV catalogue (ANSES).
- **Greece (GMRDF):** open-licensed data underlying the crop-pest ontology.
- **Norway (Mattilsynet):** primary source `plantevernmidler.mattilsynet.no` (web UI, Norwegian, manual
  extraction; no API). Plantevernguiden is under redevelopment. Norway (EEA, non-EU) is the key divergence
  partner precisely because it sits outside the EU authorisation system.

Because the EU-side data is API-accessible while Norway's requires manual extraction, coverage is matched
deliberately across countries rather than driven by data availability.

---

## 7. Benchmark table (raw survey — appendix)

_Paste the AI_Evaluation_Benchmarks_Table here as an appendix. Every row is tracked and verified in
`Literature_Verification_Register_v3.md`; entries still marked Partial there are cited lightly._