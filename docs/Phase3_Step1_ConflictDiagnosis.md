# Phase 3, Step 1 — Results: Do Real KG/RAG Conflicts Exist in This Data?

Re-run after the disease-name bug fix (`docs/Correction_KG_Disease_Name_Bug.md`) with clean facts_text.
Method: `src/phase3_step1_diagnose_conflicts.py` (entity-overlap classification + negation heuristic
against a KG-derived vocabulary, no LLM calls). Full per-question detail: `data/phase3_conflict_diagnosis.json`.

## Summary

| classification | count | meaning |
|---|---|---|
| REDUNDANT | 19 / 51 | KG-stated entities also appear in RAG's retrieved text — sources overlap/agree |
| ONE_SIDED_GAP | 9 / 51 | RAG is silent on entities KG states (or occasionally the reverse) — incompleteness, not disagreement |
| NO_KG_ENTITIES | 23 / 51 | KG's answer is count/yes-no only, nothing to compare (e.g. "9 vs 1 products") |
| NEGATION_MISMATCH candidates | 8 (heuristic) | flagged by a crude negation-window heuristic; **all 8 manually reviewed below** |

## Manual review of all 8 negation candidates: none are real conflicts

**5 candidates (`m03` x2, `d06` x3) — heuristic false positive, list-scope vs item-scope negation.**
KG's facts_text reads "18 active substances are authorised against late blight in Germany **but not** in
Norway: ametoctradin, azoxystrobin, amisulbrom, ...". The "not" negates the *category description of the
whole list* (these are the DE-only substances), not any individual substance's existence. My heuristic's
60-character negation window doesn't distinguish list-level from item-level scope, so it flagged every
entity in a long comma-separated list as "negated" simply because "not" appears nearby in the sentence.
The RAG snippet in each case describes a *different German product* (Presidium K-Plus) that happens to
contain one of these substances — entirely consistent with "authorised in Germany," which is exactly what
the KG list already asserts. **Not a conflict; a heuristic artifact, now understood and documented.**

**2 candidates (`as_n01`: captan, `pm_n02`: sulfur) — RAG cross-contamination from a different
country/disease, confirmed by checking the benchmark's own ground truth.** KG correctly states captan/
sulfur are NOT authorised in Norway for the specific disease asked about. RAG's top-8 semantic retrieval,
searching for "captan"/"sulfur" + "apple scab"/"cucurbit powdery mildew", pulled in documents from a
*different country* that happen to share the substance name: `as_m02`'s own ground-truth answer confirms
captan **is** authorised in Germany for apple scab, and sulfur is a German apple-scab substance too
(`as_c02`) — not a Norway or powdery-mildew fact at all. RAG's retrieval isn't wrong about what it
retrieved; it's simply not filtering by the country/disease boundary the question cares about, and my
entity-presence check can't tell "mentioned in an on-topic assertion" from "mentioned in an unrelated
country's product list." **Not a conflict; RAG surfacing a same-entity-different-context document.**

**1 candidate (`n02`: fluazinam) — same pattern, most instructive case.** KG: "fluazinam is NOT
authorised against late blight in Norway." RAG's retrieved doc: "In BVL (Germany), the product BANJO...
is authorised against late blight... It contains fluazinam." Both statements are true simultaneously —
KG is about Norway, RAG's doc is about Germany (signalled only by "In BVL," not by any explicit "Germany"
label the retrieval guarantees a fusion-reading model will parse correctly). **Not a conflict — but the
one case worth carrying forward as a concrete design risk** (see below), because unlike the other 7, this
is the cleanest example of two genuinely true, non-conflicting statements that a fusion-reading model could
still misread as agreement ("fluazinam is authorised... in BANJO") if it doesn't carefully track which
country each source's claim belongs to.

## Verdict: no real KG/RAG conflicts found in this dataset

This is the same honest outcome as Phase 1's Category 7 (hierarchy-traversal, pre-registered but not
instantiable) — checked, not assumed, and reported plainly rather than force-fit. **Per
`Phase3_Design.md`'s pre-registered scope discipline, the Step 4 conflict-handling grading dimension
(correctly-reflects-reliable-source / surfaces-disagreement / silently-picks-a-source /
fabricates-synthesis) is scoped down:** there is no confirmed real-conflict subset in this data to grade
that dimension against, so it will not be built as originally planned.

## What Phase 3 should actually test, given this finding

Two things ARE real and supported by this diagnostic, and become the revised focus for Steps 2–4:

1. **Gap-filling (9/51 ONE_SIDED_GAP cases).** RAG is genuinely silent on facts KG states about a third of
   the time entities are comparable at all. Does fusion correctly use KG's evidence to fill what RAG
   lacks, without RAG's silence causing unwarranted hedging on facts that ARE well-supported by KG alone?
2. **Cross-context entity attribution (the `n02`/`as_n01`/`pm_n02` pattern).** RAG's top-8 retrieval
   regularly surfaces same-substance-different-country (or different-disease) documents. This isn't a
   data conflict, but it's a real risk for fusion specifically: a model combining KG's country-scoped
   claim with RAG's country-ambiguous-on-the-surface claim could misattribute RAG's fact to the wrong
   country if the fusion prompt doesn't force explicit source-by-source country/disease matching. This is
   now a concrete, evidence-grounded design requirement for Step 2's fusion prompts (both naive and
   structured variants should be checked against a `n02`-style question specifically), not a hypothetical
   risk.

## Status vs Phase3_Plan.md

Step 1 is complete. The conflict-handling metric from `Phase3_Design.md` is formally scoped down (documented
here, not silently dropped). Step 2 (build the fusion arm + pre-register prompts) is next, informed by the
gap-filling and cross-context-attribution findings above rather than a conflict-resolution framing.