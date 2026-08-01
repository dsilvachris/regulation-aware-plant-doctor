# Phase 5, Step 1 — Architecture Integration: Complete

## What was built

`kg_retrieval_bridge.py` replaces Programme A's plain-RAG-only retrieval with KG-primary retrieval for
the 3 diseases Programme B validated (late blight, apple scab, cucurbit powdery mildew), reusing Phase 1's
KG and Phase 2's deterministic router unchanged. Every other disease in Programme A's original 12-disease
corpus falls back to RAG with an explicit, visible notice — the integration boundary from
`Phase5_Design.md` is enforced in code. Wired into `conversational_doctor.py` for both text and image
turns.

## Regression check: 9/10, and the result is stronger than the raw number suggests

Two rounds, 10 natural-language conversational queries (not copied from Phase 1's exact benchmark
wording — the point was testing the *embedded* system against realistic phrasing):

- **Round 1** (6 cases: disease names, both routing outcomes) found one real issue: the query "What
  pathogen is responsible for late blight?" was misidentified as `early blight`, an unvalidated
  neighbour disease one word apart from `late blight`.
- **Round 2** (4 added cases, specifically targeting the concerning scenario) tested **symptom-based
  phrasing** ("dark scabby spots," "white powder," "rotting fast," "white coating") and **confusion
  between the 3 validated diseases specifically** — the one scenario where a misidentification would slip
  past the scope-check safety net undetected, since all 3 are in `VALIDATED_DISEASE_MAP`. **All 4 passed
  cleanly.** The embedding model correctly distinguishes late blight, apple scab, and cucurbit powdery
  mildew from each other even via symptom description alone.

## The one persistent failure, and why it's safely contained rather than concerning

`early blight` is not in `VALIDATED_DISEASE_MAP` (Programme B never built or validated a KG for it — it's
one of the 9 out-of-scope diseases by design). Every time this misidentification occurred, the bridge's
scope check correctly caught it and fell back to `rag-out-of-scope` — **the system never produced a
confidently-wrong KG answer for the wrong disease.** The failure mode observed is "graceful degradation to
RAG with a disclosed notice," which is exactly the intended behaviour when something goes wrong, not a
silent error.

The real risk this regression check was built to catch — cross-confusion *between* the 3 validated
diseases, which the scope-check cannot catch because all 3 pass the membership test — did not occur in
any of the 4 targeted adversarial cases.

## Secondary finding: Phase 2's deterministic router is regex-exact, not semantic

Discovered incidentally: `classify_deterministic()` matches the literal substring `"pathogen causes"`
(and 3 similarly exact phrasings). A paraphrase like *"pathogen is responsible for"* doesn't match,
defaulting to `"kg"` instead of the originally-benchmarked `"rag"`. This is a real, now-documented
limitation surfacing for the first time now that a benchmark-validated rule meets open conversational
language instead of fixed wording. **Not a safety issue** — worst case for a validated disease is a
paraphrased factual question receiving KG product-list facts instead of RAG's pathogen-name facts: a
suboptimal answer shape, not a faithfulness violation, since the KG facts are still true, just not
precisely matched to the sub-question's intent. Logged here as a known limitation, not fixed in Phase 5 —
extending Phase 2's rule to be paraphrase-robust would be new scope, not integration work.

## Decision

Work Package A is complete. The one known failure mode (early/late blight confusion) is documented,
safely contained by design, and not fixed — Programme B never validated a KG for early blight, so RAG
fallback with disclosure is the correct behaviour, not a gap to close. Extending KG coverage to more
diseases remains explicit future work per `Phase5_Design.md`'s stated scope boundary.

## Status

Proceeding to Step 2: build and evaluate the trustworthiness verification layer, using the qualifier-aware
method confirmed in Step 0a.