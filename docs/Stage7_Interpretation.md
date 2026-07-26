# Stage 7 — Results and Interpretation

## Summary of findings

A curated cross-jurisdiction knowledge graph (KG) was compared against document-based RAG over
**identical** late-blight regulatory data (Germany + Norway), through an otherwise-identical pipeline
(same LLM, same prompt; only the knowledge representation differs). Both arms were run three times and
graded **blind** against ground truth from official sources, on two separate axes — *correctness* and
*faithfulness*.

### Correctness (answer matches verified ground truth)

| category | KG | RAG |
|---|---|---|
| factual (control) | 30% | 17% |
| region-specific | 44% | 48% |
| multi-hop | **67%** | 25% |
| constraint | 42% | 25% |
| negative / absence | **33%** | 8% |
| cross-border divergence | 39% | 22% |
| **overall** | **41%** | **26%** |

### Faithfulness (asserts only supported facts; abstains honestly)

| category | KG | RAG |
|---|---|---|
| factual | 87% | 97% |
| region-specific | 81% | 93% |
| multi-hop | 100% | 92% |
| constraint | 67% | 75% |
| negative / absence | 92% | 100% |
| cross-border | 67% | 89% |
| **overall** | **82%** | **92%** |

### Consistency (overall correctness across the 3 runs)

- KG: mean 41%, range 38–46% (stable)
- RAG: mean 26%, range 16–38% (high variance)

## Interpretation

**1. Structured representation substantially improves correctness on relational and absence queries.**
The KG roughly doubles overall correctness (41% vs 26%) and wins in five of six categories. The largest
gaps are exactly where the pre-registered predictions expected them: **multi-hop (67% vs 25%)** and
**negative/absence (33% vs 8%)**. These are the categories that require traversing relationships or
asserting that something is *not* present — operations a graph performs by construction and that flat
document retrieval handles poorly. The hypothesis is supported where it was predicted to hold.

**2. The control behaved as a control should.** On factual lookup the KG does not dramatically dominate,
and on region-specific lookup document-RAG actually matches/slightly beats the KG (48% vs 44%). This is a
healthy result: the KG does not win everything, which is evidence the comparison is not biased toward it.
Simple single-fact lookup is a task document retrieval does well, and the data reflects that.

**3. The faithfulness axis inverts — and this is the study's most important finding.** Document-RAG is
*more* faithful overall (92% vs 82%). The reason is instructive rather than flattering to either system:
- Document-RAG, when its retrieval fails, tends to **abstain** ("no information about Norway is provided")
  rather than fabricate. Abstention scores as faithful even though the answer is wrong — it is
  *faithfully unhelpful*.
- The KG supplies the LLM with precise verified facts, which raises correctness but occasionally **tempts
  the LLM to assert beyond them**, lowering faithfulness (most visibly in cross-border, 67% vs 89%).

So the two representations trade off along a **correctness ↔ faithfulness** axis: the KG buys correctness
at some cost to faithfulness; document-RAG preserves faithfulness largely by declining to answer.

**4. The KG is markedly more consistent.** Across three runs the KG's correctness is stable (38–46%) while
document-RAG's swings widely (16–38%). Beyond mean accuracy, the KG offers **reliability** — its behaviour
depends on deterministic queries over structured facts, not on which documents semantic retrieval happens
to surface on a given run. For a safety-critical domain, run-to-run stability is itself a meaningful property.

## Practical implication

Structured representation is most valuable **exactly where document retrieval is weakest** — relationships,
absence, and cross-jurisdictional comparison — and least necessary for simple lookup. The faithfulness
result suggests the strongest system is neither arm alone but a **hybrid**: the KG's deterministic
retrieval for precision and consistency, paired with an explicit abstention discipline (answer only from
verified facts; refuse when the graph returns nothing) to recover the faithfulness that document-RAG gets
"for free" by abstaining. This matches the project's standing principle that safety-critical reasoning
should be deterministic and the LLM confined to phrasing verified facts.

## Limitations (stated plainly)

- **Absolute performance is low** (KG 41% correct). This is a *relative* comparison of two representations
  under a small local model (Llama 3.2 3B), terse verbalised facts, and strict grading — not an evaluation
  of a deployable system. The claim is "the KG roughly doubles correctness over document-RAG on relational
  regulatory queries," not "the KG is accurate in absolute terms."
- **Corpus imbalance (28:1 German documents).** Document-RAG's region-specific failures are partly an
  artifact of the German-dominated corpus swamping semantic retrieval, not purely a representational
  weakness. The KG faces the same imbalance and is robust to it — which is itself part of the point — but
  the confound should temper any strong claim about RAG's region-correctness specifically.
- **Single disease, single grader.** The comparison covers late blight only; apple scab and powdery mildew
  were collected but not yet built into the graph. Grading was by one assessor (blind), not multiple.
- **Small benchmark, low counts per category.** Category rates rest on few questions each; the direction of
  effects is clearer than their precise magnitudes.
- **One honest RAG win (c03, mixtures)** was retained deliberately: document prose carried per-product
  substance detail that the KG query template discarded. This is a genuine case where document retrieval
  sufficed, and it is reported rather than engineered away.

## Conclusion

Representing identical agricultural regulatory knowledge as a curated cross-jurisdiction knowledge graph
**improves correctness and consistency** over document-based RAG on relational, negative, and cross-border
regulatory queries, while **document-RAG remains competitive on simple lookup and more faithful overall by
abstaining**. The contribution is not "the KG is better" but a characterisation of *when and why* structured
representation helps: it converts questions about relationships and absence — which document retrieval can
only answer by luck or decline — into deterministic, verifiable lookups, at a manageable and addressable
cost to faithfulness. Both the positive result (structure helps) and the qualification (it does not
dominate, and trades against faithfulness) are treated as findings, per the pre-registered design.