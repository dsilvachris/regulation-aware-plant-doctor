# Cross-Jurisdictional Regulatory Knowledge: Knowledge Graph vs Document-RAG

A controlled study asking whether representing identical agricultural plant-protection regulatory
knowledge as a **curated knowledge graph** improves retrieval, provenance, and regulatory correctness
compared with **document-based RAG** — evaluated across two jurisdictions (Germany and Norway).

Built on the frozen baseline of the regulation-aware plant-disease assistant (tag `baseline-v1.0`).

## Research question and gap

National plant-protection regulatory knowledge graphs already exist (E-PHY / ANSES France; C3PO;
the GMRDF crop-pest ontology, Greece) — so this work does **not** claim the first agricultural
regulatory KG. Each of those models a **single jurisdiction**. What is missing, and what this study
addresses, is twofold:

1. an explicit representation of **cross-border regulatory divergence** — the same crop and disease
   requiring different *authorised* products depending on the country (a consequence of the EU's dual
   system: central active-substance approval, national product authorisation, Reg. (EC) No 1107/2009;
   with non-EU EEA Norway diverging further); and
2. a **controlled comparison** of two representations of the *same* knowledge — a curated KG vs an
   unstructured document collection — within an otherwise identical pipeline, isolating the effect of
   representation itself.

## Methodology (7 stages)

| Stage | What | Status |
|---|---|---|
| 0 | Freeze the baseline as experimental control (pipeline, code, eval framework, repo; tag `baseline-v1.0`) | Done |
| 1 | Literature review + positioning; reuse EPPO/AGROVOC vocabularies | Done |
| 2 | Design the evaluation benchmark **before** implementation (7 categories, pre-registered predictions) | Done |
| 4 | Curated regulatory data from official sources (BVL API + Mattilsynet) | Done |
| 3 | Build the KG (RDFLib) **and** parallel prose docs from the same data | Done (late blight) |
| 5 | Query layer (deterministic KG queries + document retrieval) → LLM explanation | Next |
| 6 | Blind comparative evaluation, multiple runs | Pending |
| 7 | Interpretation (KG helps / KG doesn't — both valid findings) | Pending |

Stage 4 precedes Stage 3 in practice: the data must exist before the graph can be built. Stage-4 data
is given to **both** arms — as a graph for the KG arm, as prose for the RAG arm — so the two differ only
in representation (data parity).

## Design principles

- **Ground truth comes from authoritative sources**, never from either system being compared.
- **Predictions are pre-registered** per benchmark category (before running), so wins *and* misses are
  reported honestly. Category 1 (factual lookup) is a bias-check control: the KG must **not** win there.
- **Safety-critical reasoning stays deterministic.** KG queries are written as code (SPARQL); the LLM
  never generates graph queries. Workflow: query → deterministic logic → verified facts → LLM phrases them.
- **Reuse published identifiers** — EPPO codes for pathogens, AGROVOC concepts for crops — rather than
  minting local ones.
- **Verify, don't trust** — every extracted record, citation, and derived fact is checked against the
  source before use.

## Data (Stage 4)

Authorised plant-protection products for three overlap diseases, from official regulators:

- **Germany — BVL PSM REST API** (`psm-api.bvl.bund.de`): programmatic, monthly-updated, open licence,
  mandated by Art. 57 of Reg. (EC) No 1107/2009. Pest identifiers are EPPO codes (PHYTIN, VENTIN, PODOXA).
- **Norway — Mattilsynet** (`plantevernmidler.mattilsynet.no`): no search API; manual extraction, each
  product verified against its official label.

**Authorised-product counts (late blight, apple scab, cucurbit powdery mildew):**

| disease | Germany | Norway |
|---|---|---|
| late blight | 112 | 4 |
| apple scab | 9 | 1 |
| cucurbit powdery mildew | 1 | 1 |

The asymmetry is the finding, not a data gap: coverage is matched deliberately (same diseases), and the
divergence reflects real regulatory difference — Norway actively restricts late-blight products.

## The benchmark (Stage 2)

38 questions across 7 categories, each with a pre-registered prediction and ground truth from official
sources:

1. factual lookup (control, `=`), 2. region-specific, 3. multi-hop (`KG+`), 4. constraint (`KG+`),
5. negative/absence (`KG+`, sharpest), 6. cross-border divergence (`KG+`, the novel category),
7. hierarchy-traversal (`KG+`, currently open pending crop-hierarchy inspection).

Categories 1–2 are answerable from the baseline corpus; 3–7 required the Stage-4 product data and are
verified against it. Grading (Stage 6) will be blind to condition, over multiple runs, reporting mean and
variation.

## The knowledge graph (Stage 3, late blight)

Built with RDFLib. Authorisation is modelled as an **n-ary node** (mirroring E-PHY's "Use") because it is
a four-way relationship — a product authorised *against a pathogen*, *on a crop*, *in a country*:

```
Authorisation --hasProduct--> Product --containsSubstance--> ActiveSubstance
Authorisation --targetsPathogen--> Pathogen  (EPPO: PHYTIN)
Authorisation --onCrop--> Crop
Authorisation --inCountry--> Country
Product --regulatedBy--> Authority
```

Late-blight graph: **1,266 triples, 116 authorisations (112 DE + 4 NO)**. The same facts are also written
as prose documents for the RAG arm (data parity). Active-substance names are normalised across
German/English/Norwegian spellings (e.g. *Kupferhydroxid* → *copper hydroxide*) so cross-border comparison
matches on chemistry, not on string.

Verified against ground truth with deterministic SPARQL — including the category-5 showcase: asking "is
fluazinam authorised in Norway?" returns a structurally empty result, i.e. a definitive *no*, where
document retrieval could only fail to find it.

## Repository layout (research artifacts)

```
docs/   BASELINE.md, Literature_Review.md, Literature_Verification_Register_v3.md,
        Benchmark_Design_Stage2.md
data/   bvl_*_DE.json (BVL extracts), no_products.json (Norway),
        benchmark_cat1_2.json, benchmark_cat3_7.json,
        kg_late_blight.ttl, rag_docs_late_blight.json
src/    bvl_extract.py, enrich_de_substances.py, verify_benchmark_gt.py,
        build_kg.py, substance_norm.py, query_kg.py
```

## Status

Stages 0–4 complete; Stage 3 built and verified for late blight. Next: Stage 5 (query + explanation
pipeline for both arms), then the blind comparative evaluation. Both outcomes — the KG helps, or it does
not and document RAG suffices — are treated as valid contributions.