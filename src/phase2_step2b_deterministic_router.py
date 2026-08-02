"""
phase2_step2b_deterministic_router.py — Phase 2, Step 2: the no-LLM routing baseline.

This was always Step 2 of the original plan (docs/Phase2_Plan.md) but was deferred while the LLM router
was investigated first (steps 1, 2a, 3, 3b, 3c). It is built now with full knowledge of that investigation,
which is exactly why it is worth being explicit about what "principled, not tuned to grades" means here:

  - The rule below is derived from the CATEGORY DEFINITIONS themselves (factual questions are a "tie;
    both retrieve single facts" per phase2_step1_oracle.py's own comment — i.e. the category-level oracle
    already says the only questions where RAG is the pre-registered-optimal arm are simple biology-fact
    lookups: what pathogen, what type, what EPPO code, what crops). It is NOT fit by inspecting which of
    the 51 questions individually favour RAG in the grading data (that would be training on the test set,
    same discipline as llm_router.py's pre-registered prompt).
  - It was verified against the FULL 51-question set before being committed (see commit message / dev
    notes) to confirm zero false positives — i.e. no non-factual question accidentally matches the
    biology-jargon pattern. This is checked, not assumed.

WHY THIS MATTERS GIVEN STEP 3C: the LLM router (best variant, B) caught up to 6/12 systematic RAG-wins per
run but was only self-consistent on 55% of questions across 5 runs. A rule-based classifier is, by
construction, perfectly deterministic (100% stable) and cannot introduce a NEW risky-category misroute that
isn't already baked into the rule — so this baseline directly tests whether the LLM added anything beyond
what "detect simple biology lookups, default the rest to KG" already gives you for free, with none of the
instability.

Run: python src/phase2_step2b_deterministic_router.py
"""
import json, re, sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
# NOTE: eval_pipeline / phase2_step3b_prompt_sensitivity imports moved to be LOCAL (inside score() and
# the __main__ block below) rather than module-level. classify_deterministic() - the only thing this
# module needs to provide for Phase 5's deployed assistant (kg_retrieval_bridge.py) - only needs `re`.
# Found while tracing the Docker image's dependency chain for Phase 5 Step 4: importing this module for
# deployment was unnecessarily dragging in the entire Phase 2 evaluation harness (eval_pipeline.py, which
# itself pulls in kg_arm/rag_arm/kg_verbalise again, plus phase2_step3b_prompt_sensitivity.py). No
# behaviour change for classify_deterministic() or for running this script standalone.

# --- PRE-REGISTERED RULE (principled: derived from category definitions, not from grades) ---
# A question is routed to DOCS only if it is a simple single-disease biology-attribute lookup —
# the ONLY case the category-level oracle marks as RAG-optimal. Everything else defaults to KG,
# matching Phase-1's finding that KG is the stronger arm overall and the safer default.
FACTUAL_PATTERNS = [
    r"pathogen causes",
    r"type of pathogen",
    r"eppo code",
    r"crops does .* affect",
]


def classify_deterministic(question: str) -> str:
    ql = question.lower()
    for pat in FACTUAL_PATTERNS:
        if re.search(pat, ql):
            return "rag"
    return "kg"


def score(decisions):
    """Same metric definitions as phase2_step3b_prompt_sensitivity.score(), reproduced here rather than
    imported because that version expects an 'ambiguous_parse' key that doesn't apply to a deterministic
    rule (there is no parsing step to fail)."""
    from phase2_step3b_prompt_sensitivity import CATEGORY_OPTIMAL, SYSTEMATIC_RAG_WINS  # local: see note above
    n = len(decisions)
    correct_vs_oracle = sum(1 for d in decisions.values()
                             if d["routed_to"] == CATEGORY_OPTIMAL.get(d["category"], "kg"))
    rag_wins_caught = sum(1 for qid, d in decisions.items()
                           if qid in SYSTEMATIC_RAG_WINS and d["routed_to"] == "rag")
    factual_to_docs = sum(1 for d in decisions.values()
                           if d["category"] == "factual" and d["routed_to"] == "rag")
    factual_total = sum(1 for d in decisions.values() if d["category"] == "factual")
    risky_cats = {"negative", "cross_border", "cross_disease"}
    risky_misroutes = [(qid, d["category"]) for qid, d in decisions.items()
                        if d["category"] in risky_cats and d["routed_to"] == "rag"]
    return {
        "n": n,
        "routing_accuracy_vs_oracle": correct_vs_oracle / n if n else 0,
        "systematic_rag_wins_caught": f"{rag_wins_caught}/{len(SYSTEMATIC_RAG_WINS)}",
        "factual_routed_to_docs": f"{factual_to_docs}/{factual_total}",
        "risky_category_misroutes_to_rag": risky_misroutes,
    }


if __name__ == "__main__":
    import eval_pipeline as ep
    from phase2_step3b_prompt_sensitivity import EXCLUDE
    items = [it for it in ep.load_benchmark() if it[2] not in EXCLUDE]

    decisions = {}
    for qid, q, cat in items:
        arm = classify_deterministic(q)
        decisions[qid] = {"question": q, "category": cat, "routed_to": arm}
        print(f"  {qid:8} {cat:16} -> {arm}")

    s = score(decisions)

    # Determinism check: re-run and confirm identical output (should be trivially true, but verify
    # rather than assume, matching project convention).
    decisions2 = {qid: classify_deterministic(q) for qid, q, cat in items}
    is_stable = all(decisions[qid]["routed_to"] == decisions2[qid] for qid in decisions)

    print("\n" + "=" * 70)
    print(f"Routing accuracy vs category oracle: {s['routing_accuracy_vs_oracle']:.0%}")
    print(f"Systematic RAG-wins caught:          {s['systematic_rag_wins_caught']}")
    print(f"Factual questions routed to DOCS:    {s['factual_routed_to_docs']}")
    print(f"Risky-category misroutes to RAG:     {s['risky_category_misroutes_to_rag'] or 'none'}")
    print(f"Deterministic (identical on re-run):  {is_stable}  (stability = 100% by construction)")

    out = {
        "_meta": {
            "method": "deterministic rule (regex over biology-jargon terms), no LLM calls",
            "rule_source": "derived from category-level oracle definition (factual -> rag, tie); "
                            "verified against full 51-question set for zero false positives before commit",
        },
        "score": s,
        "decisions": decisions,
    }
    json.dump(out, open(DATA / "phase2_deterministic_router.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase2_deterministic_router.json")