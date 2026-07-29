# Phase 1 — Three-Disease Evaluation Results

## What changed from the Stage 0–7 study

The original study evaluated **late blight only**. Phase 1 (the agreed Master's-thesis scope) extends the
knowledge graph and benchmark to **three diseases** — late blight, apple scab, cucurbit powdery mildew —
across the same two jurisdictions (Germany, Norway), and re-runs the full blind, multi-run evaluation. It
also adds a **new query category — cross-disease** — that the combined graph makes possible and that the
single-disease study could not test.

Benchmark: ~51 questions × 3 runs = 153 blind-graded items. Same pipeline, same model (Llama 3.2 3B), same
blind-grading protocol as Stage 6.

## Results

### Correctness (answer matches verified ground truth)

| category | KG | RAG |
|---|---|---|
| factual (control) | 27% | 33% |
| region-specific | 89% | 89% |
| multi-hop | 31% | 19% |
| constraint | 50% | 31% |
| negative / absence | 71% | 36% |
| cross-border divergence | 27% | 32% |
| **cross-disease (new)** | **100%** | **25%** |
| **overall** | **50%** | **43%** |

### Faithfulness (asserts only supported facts; abstains honestly)

| category | KG | RAG |
|---|---|---|
| factual | 100% | 97% |
| region-specific | 100% | 100% |
| multi-hop | 75% | 75% |
| constraint | 100% | 75% |
| negative / absence | 100% | 64% |
| cross-border | 95% | 95% |
| cross-disease | 100% | 75% |
| **overall** | **96%** | **88%** |

### Consistency (overall correctness across 3 runs)

- KG: mean 50%, range 48–53% (stable)
- RAG: mean 42%, range 37–47% (variable)

## Interpretation

**1. The cross-disease category is the headline result — KG 100% vs RAG 25%.** This is the largest gap in
the study and the clearest demonstration of structural advantage. "Which active substance is authorised
against more than one of these diseases?" (answer: azoxystrobin, potassium phosphonate) is a single graph
traversal but requires document-RAG to retrieve across all three diseases and join by substance in the
model's context — which semantic retrieval does not reliably do. This capability did not exist in the
single-disease study; it is a genuine new contribution of the combined graph.

**2. The KG advantage is real but more concentrated than the single-disease run suggested.** Overall
correctness is KG 50% vs RAG 43% — a narrower margin than the late-blight-only 41% vs 26%. The KG dominates
where structure matters (cross-disease, negative/absence 71% vs 36%, constraint 50% vs 31%, multi-hop 31%
vs 19%), ties on region-specific lookup (89% vs 89%), and slightly trails on simple factual lookup. This is
a *more credible* picture than a broad sweep: the single-disease run was partly inflated by the 28:1
German-corpus imbalance, which is diluted across three diseases. The KG's advantage now sits exactly where
the pre-registered predictions expected it, and not elsewhere.

**3. Faithfulness — the change from Stage 6, now explained.** In the single-disease study, document-RAG was
*more* faithful (92% vs 82%), because it abstained rather than fabricate. In this three-disease run the
ordering **reverses**: KG 96% vs RAG 88%. This change was investigated rather than assumed, using the
recovered Stage 6 grades: on the **identical late-blight questions** across both evaluations, KG faithfulness
rose from **82.0% to 95.0% (+13.1 pts)** while RAG's fell slightly (91.9% to 87.1%). Because the question set
is held constant, the change is isolated to the **pipeline refinement** made between the two runs — cleaner
fact-verbalisation and disease-filtered queries reduced the KG's tendency to overclaim. The negative/absence
category shows the effect starkly: KG 100% faithful vs RAG 64%, because RAG hallucinates on absence questions
while the KG correctly denies.

The improvement was strong but **not uniform**: of the late-blight questions graded in both runs, 12 improved
in KG faithfulness, 3 regressed, and 22 were unchanged. Notably, the 3 regressions (m02, m03, d04) are
cross-country/divergence questions whose routing was rewired to fetch *more* facts — and supplying the model
more precise facts made it more likely to overclaim on them. This is a small in-vivo instance of the
correctness-versus-faithfulness tension this study documents: the very facts that raise correctness can tempt
the model to assert beyond them. (It also confirms the earlier "faithfully unhelpful RAG" finding was
specific to the earlier, rougher KG arm.)

**4. Consistency advantage holds.** The KG remains markedly more stable across runs (48–53%) than
document-RAG (37–47%) — the reliability property carries over to the multi-disease setting.

## A note on a subtler divergence finding

Cucurbit powdery mildew shows **count parity but substance divergence**: Germany and Norway each authorise
exactly one product, but Germany's uses azoxystrobin and Norway's uses proquinazid. Cross-border divergence
is therefore not only about *how many* products a country authorises but *which chemistry* — a distinction a
structured representation surfaces cleanly and a count-based view misses.

## Limitations (unchanged in spirit from Stage 7, plus new)

- Absolute performance remains low — a *relative* comparison under a small local model and strict grading,
  not a deployable system.
- **Grading validated.** A second independent blind grader scored 125 of the 153 items; inter-rater
  agreement was near-perfect (Cohen's kappa 0.99 for correctness, 1.00 for faithfulness). The grading is
  reproducible — the result no longer rests on a single assessor.
- The corpus imbalance is reduced but not eliminated; powdery mildew and apple scab contribute few
  questions each, so their per-category rates rest on small counts.
- The faithfulness change between the two evaluations was traced to pipeline refinement (confirmed on the
  identical late-blight question set), but the two runs were not a single controlled ablation — the pipeline
  and the disease set both changed between Stage 6 and Phase 1, so the isolation, while strong, is not a
  formal A/B test.

## Status

Phase 1 core complete: three-disease KG, expanded verified benchmark, repeated blind evaluation, new
cross-disease capability demonstrated, grading validated by a second blind grader (kappa 0.99/1.00), and the
faithfulness change between evaluations traced to pipeline refinement. Remaining optional items: instantiate
the open hierarchy-traversal category (requires wiring real German crop codes), and verify the AGROVOC crop
URIs and remaining Norwegian registration numbers.