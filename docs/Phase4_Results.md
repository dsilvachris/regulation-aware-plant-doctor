# Phase 4 Results — Generalisation to Healthcare: Does the KG-vs-RAG Advantage Replicate?

*Synthesis chapter (Step 7 of `docs/Phase4_Plan.md`). Draws on the feasibility gate
(`Phase4_Step0_Feasibility.md`), the benchmark and KG build (Steps 1–4), and the final multi-run results
(`Phase4_Step6_Results.md`). This chapter answers the pre-registered RQ against that evidence; it does
not introduce new results.*

## The research question

> **RQ (Phase 4): Does the KG-vs-RAG advantage found in Phase 1 — and the category-level pattern behind
> it (relational/absence/cross-border/hierarchy favour structure; simple factual lookup does not) —
> replicate in a second regulated domain (pharmaceutical drug authorisation, US FDA vs EU EMA), sourced
> and built independently of the plant-protection corpus?**

(`docs/Phase4_Design.md`)

## Answer

**Yes, directionally and at a comparable-or-larger magnitude — but the clean version of this story is
wrong, and the more precise version is more interesting: structure reduces fabrication risk and enables
real hierarchy reasoning, but does not eliminate fabrication even in the KG arm, and both arms share a
common small-model ceiling on some task shapes regardless of representation.**

| condition | correct | faithful | stability (3-run range) |
|---|---|---|---|
| KG | 88% | 86% | 86%-93% |
| RAG | 45% | 76% | 43%-50% |

This replicates Phase 1's directional finding (KG substantially outperforms RAG) in a domain built
entirely independently — different regulators (FDA/EMA vs BVL/Mattilsynet), different data shape,
different subject matter, sourced and verified live rather than reused from Phase 1's pipeline. The
~43-point correctness gap is comparable to or larger than Phase 1's corrected ~22-point gap
(`Phase2_Results.md`'s addendum), which is itself informative: the magnitude was explicitly left open in
the pre-registered prediction, and the evidence did not converge toward a smaller gap in the new domain.

## Against the pre-registered prediction

`Phase4_Plan.md` recorded this prediction before Step 5 ran:

> *"Category 1 (factual): KG and RAG should tie or RAG should slightly lead... Categories 3–6: expected to
> favour the KG... Category 7 (hierarchy): expected to favour the KG strongly, and expected to be
> instantiable at all... Magnitude... treated as a genuinely open empirical question."*

- **Category 1 (factual, bias-check) — partially disconfirmed.** KG scored 100%, RAG 78%, a real gap where
  none was predicted. In Phase 1, this category was a clean control precisely because simple lookups gave
  neither arm an edge. Here, RAG's misses were extraction/recitation slips on a much smaller corpus (8
  documents vs Phase 1's 128), not retrieval failures — but the prediction that this category would show no
  KG advantage did not hold cleanly, and that's worth stating rather than smoothing over. It suggests the
  "factual = no advantage" pattern from Phase 1 is not automatically portable to a new domain's benchmark
  design; it needs to be re-verified per domain, not assumed.
- **Categories 3–6 — confirmed where discriminating, uninformative where not.** `multi_hop` (100% vs 0%)
  and `cross_border` (100% vs 0%) confirm the prediction strongly, and for a real, identified mechanism
  (RAG's K=3 retrieval cannot see enough of an 8-candidate pool for full-corpus comparison questions).
  `constraint` and `negative` both hit 100%/100% — a ceiling effect from only 1–2 questions per category
  at this benchmark's size, not a genuine "RAG matched KG" finding. This is a real limitation of a
  14-question starter benchmark, stated plainly rather than claimed as evidence either way.
- **Category 7 (hierarchy) — confirmed as instantiable (the oldest open thread in this thesis, closed);
  confirmed to favour KG, but not uniformly, which the prediction did not anticipate.** `h2` (a pairwise
  hierarchy filter) is the cleanest result in the entire phase: KG 3/3, RAG 0/3, repeatable and mechanistically
  clear (RAG conflates a subgroup code with the full specific code). `h1` (enumerate all N matches) fails for
  **both** arms equally, 0/3 each — verified in Step 4 that the KG's facts_text lists all 4 correct answers,
  yet the 3B model still only echoes 1–2 across every run. The pre-registered prediction ("favour the KG
  strongly") was right in kind but too broad in scope: KG's real advantage is on filtered/pairwise hierarchy
  questions, not full-enumeration ones, and that boundary would not have been visible without item-level
  analysis rather than trusting the category aggregate.
- **Magnitude — correctly left open, and the answer is "larger, not smaller."** The ~43-point gap here
  exceeds Phase 1's corrected ~22-point gap. Whether this reflects a genuinely stronger structure advantage
  in denser, more technical pharma data, or an artifact of this benchmark's small size and category
  imbalance, is not resolved by this phase alone — flagged as an open question below, not answered here.

## The finding that wasn't predicted: the KG arm hallucinates too

The single most important result in this phase was not in the pre-registered prediction at all.
`r2`'s KG facts_text states exactly one fact — *"Niraparib is authorised via the EU's centralised
procedure (EMA)"* — with no ambiguity and nothing else asserted. In 2 of 3 runs, the KG arm answered that
niraparib is authorised *"via both the EU's centralised procedure (EMA) and at the national level"* — a
fabricated addition, present in neither the facts nor any plausible inference from them. This was caught
only because of the multi-run discipline: the single-run demo earlier in this phase happened to land on
the one faithful phrasing, and would have reported KG as flawless on this question if trusted alone.

This is a real methodological result, not a footnote: it directly tempers the thesis's broader KG-vs-RAG
narrative. The honest claim, across all four phases now, is **"structured retrieval reduces the frequency
and severity of fabrication, especially on relational/absence/cross-border/hierarchical questions where
document retrieval structurally struggles — it does not make fabrication impossible, even on short,
unambiguous, single-fact questions."** A thesis chapter that presented KG as immune to hallucination would
be overclaiming against this project's own evidence.

## A genuine bug caught and fixed mid-phase, not hidden

An earlier run of this benchmark showed `region_specific` at 100%/17% — driven entirely by `r2`. On
inspection, RAG's prose documents never stated the word "centralised" anywhere, a data-parity violation
(the KG's fact existed; the equivalent RAG sentence was simply never written) rather than a genuine
capability gap. This was fixed in `build_kg_phase4.py`, the benchmark was regenerated and re-graded, and
the corrected run is what's reported above. Documented in full in `Phase4_Step6_Results.md` and in the
commit history rather than silently overwritten — the same standard applied to the disease-name bug in
Phase 2 and the ambiguous-template bug in Phase 3.

## Limitations, stated plainly

- **14 questions is a starter benchmark**, not Phase 1's 51. Several categories have only 1–2 questions,
  producing ceiling effects (`constraint`, `negative`) that cannot discriminate between arms at this
  sample size. The directional findings that DO discriminate (`h2`, `cross_border`, `multi_hop`,
  and the `r2` hallucination) are trustworthy because they're either repeatable across runs or mechanistically
  explained, not because the benchmark is large.
- **Single grader, no independent validation** — the same limitation Phase 3 identified and could not fully
  resolve. Carried forward here rather than re-litigated; the same caveat applies to any single-grader
  result across both phases.
- **The `h1` mechanism (LLM enumeration failure) was inferred from the facts_text/answer mismatch, not
  independently stress-tested** — a controlled follow-up (e.g. varying list length to find where enumeration
  starts failing) would strengthen this finding beyond this phase's scope.

## What would change this conclusion

- **A larger benchmark** (more substances, more questions per category) to remove the ceiling effects on
  `constraint`/`negative` and get real discriminating power there.
- **A dedicated `r2`-style fabrication stress test**: deliberately construct several more short,
  single-fact, unambiguous questions to see whether the 2/3 hallucination rate observed here is
  representative or a small-sample fluke.
- **A larger model**, to test whether the `h1` enumeration failure and the `r2` fabrication are 3B-specific
  limitations (as Phase 2 found for routing instability) or persist at larger scale — this phase does not
  test model size at all, and Phase 2's finding that scale matters for LLM reliability has not been checked
  against Phase 4's domain.

## Deliverables checklist (Phase4_Plan.md), final status

- [x] `phase4_step0_feasibility.json` + go/no-go, corrected after catching a false-positive divergence count
      (Step 0)
- [x] `data/benchmark_phase4.json`, 14 questions, pre-registered ground truth, corrected once after
      verifying against the built KG (`h2`) (Step 1)
- [x] `data/fda_drugs_US.json`, `data/ema_medicines_EU.json`, sourced and verified live (Step 2)
- [x] `kg_phase4.ttl` (184 triples), `rag_docs_phase4.json`, data-parity bug found and fixed (Step 3)
- [x] Deterministic query layer + verbalisers, self-tested end-to-end against the real KG before any LLM
      call (Step 4)
- [x] Multi-run comparison (3 runs), single grader (Step 5)
- [x] Core analysis, with the pre-fix vs post-fix numbers both preserved for the audit trail (Step 6)
- [x] this document (Step 7)