"""
phase2_step3b_prompt_sensitivity.py — Phase 2, Step 3b: is the LLM router's KG-collapse a property of
ONE prompt, or of the routing task itself for a 3B model?

Context (pre-registered before this script was written): the baseline router (llm_router.py, PROMPT A
below) caught only 1 of 12 systematic RAG-win questions, misrouted all three simple-factual questions
(f03/f08/f09) to KG despite the prompt explicitly saying "simple fact lookup -> DOCS", and misrouted one
cross-disease question to RAG (the costliest error class per Phase2_Design.md's risk asymmetry).

Before scoring that as a Phase-2 result, this script tests three prompt variants on the SAME benchmark:

  PROMPT_A  baseline        — KG described first, DOCS second, explicit "default to KG" fallback text.
                              (imported verbatim from llm_router.ROUTER_PROMPT — not retyped, so a diff
                              between A's behaviour here and the original run would itself be a bug flag.)
  PROMPT_B  docs-first       — same criteria as A, but DOCS is described first and the framing is made
                              symmetric (no language implying either strategy is the "default").
  PROMPT_C  few-shot         — A's ordering + criteria, plus 5 worked examples covering exactly the
                              failure categories seen in the baseline run (factual->DOCS, absence->KG,
                              cross_border->KG, cross_disease->KG, multi_hop->KG). Examples are SYNTHETIC
                              (different disease/crop/country than anything in the 53-question benchmark)
                              to preserve the same "not tuned to the test set" audit-trail property that
                              PROMPT A was written under.

Interpretation is pre-registered here, before running:
  - If B and C both still collapse to KG and still misroute the cross-disease question -> Conclusion A
    (a 3B model can't reliably do this routing) is strong, and specifically localized to instruction-
    following weakness rather than one bad prompt.
  - If B alone fixes it -> the KG-bias was a simple ordering/anchoring artifact.
  - If only C fixes it -> the model needs concrete worked examples, not just a restated rule; it can't
    apply an abstract criterion zero-shot even when the criterion is stated correctly.
  - If none fix it uniformly (e.g. C fixes factual but not cross-disease) -> routing quality depends on
    the failure mode's nature, not on a single global "can/can't route" answer — report per-category.

Run: python src/phase2_step3b_prompt_sensitivity.py
"""
import json, sys
from pathlib import Path
import ollama

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
from llm_router import ROUTER_PROMPT as PROMPT_A   # baseline, imported verbatim — not retyped

LLM = "llama3.2:3b"

# Kept in sync with phase2_step1_oracle.py's CATEGORY_OPTIMAL. Duplicated (not imported) because that
# file is a run-and-print script, not a module; if you change one, change both.
CATEGORY_OPTIMAL = {
    "factual": "rag", "region_specific": "kg", "multi_hop": "kg", "constraint": "kg",
    "negative": "kg", "cross_border": "kg", "cross_disease": "kg",
}
EXCLUDE = {"hierarchy"}

# The 12 questions where Phase-1 established RAG as the SYSTEMATIC winner (verified via
# phase2_step2a_diagnose.py, not re-typed from memory).
SYSTEMATIC_RAG_WINS = {"f03", "f05", "f08", "f09", "r04", "m04", "c03",
                        "as_m02", "as_c02", "as_d02", "pm_d02", "pm_d03"}

# --- PROMPT B: DOCS-first, symmetric framing, no "default" language ---
PROMPT_B = """You are a retrieval router for a plant-protection regulation assistant. Two retrieval
strategies are available:

DOCS (document retrieval): best when the question is a SIMPLE FACT LOOKUP answerable from a single passage
(e.g. what pathogen causes a disease), or needs FINE-GRAINED TEXTUAL DETAIL about a specific product that
would be spelled out in its description (e.g. the exact combination of substances in one named product).

KG (knowledge graph): best when the question requires REASONING OVER RELATIONSHIPS — connecting products,
substances, crops, pathogens, or countries; counting or comparing across categories; determining whether
something is NOT authorised (absence); or joining facts across diseases or jurisdictions.

Decide which single strategy will better answer the question below. Consider only the question itself.
Answer with exactly one word: KG or DOCS.

QUESTION: {question}
ANSWER:"""

# --- PROMPT C: A's ordering + criteria, plus synthetic few-shot examples (not from the benchmark) ---
PROMPT_C = """You are a retrieval router for a plant-protection regulation assistant. Two retrieval
strategies are available:

KG (knowledge graph): best when the question requires REASONING OVER RELATIONSHIPS — connecting products,
substances, crops, pathogens, or countries; counting or comparing across categories; determining whether
something is NOT authorised (absence); or joining facts across diseases or jurisdictions.

DOCS (document retrieval): best when the question is a SIMPLE FACT LOOKUP answerable from a single passage
(e.g. what pathogen causes a disease), or needs FINE-GRAINED TEXTUAL DETAIL about a specific product that
would be spelled out in its description (e.g. the exact combination of substances in one named product).

Examples:
QUESTION: What pathogen causes downy mildew in grapevine?
ANSWER: DOCS

QUESTION: Which active substances are combined in the product Fantic M?
ANSWER: DOCS

QUESTION: Is imidacloprid authorised for use on lettuce in France?
ANSWER: KG

QUESTION: Do Spain and Portugal differ in which fungicides are authorised for citrus greening?
ANSWER: KG

QUESTION: Which substances are authorised for both grapevine downy mildew and wheat rust?
ANSWER: KG

Decide which single strategy will better answer the question below. Consider only the question itself.
Answer with exactly one word: KG or DOCS.

QUESTION: {question}
ANSWER:"""

VARIANTS = {"A_baseline": PROMPT_A, "B_docs_first": PROMPT_B, "C_few_shot": PROMPT_C}


def parse_decision(resp: str):
    """Returns ('kg'|'rag', ambiguous:bool). Ambiguous parses still default to 'kg' (same convention as
    llm_router.py) but are flagged separately so we can tell 'model chose KG' from 'parsing broke'."""
    resp_u = resp.strip().upper()
    lines = [l.strip() for l in resp_u.splitlines() if l.strip()]
    tail = lines[-1] if lines else resp_u
    if "DOCS" in tail or "DOC" in tail or "RAG" in tail:
        return "rag", False
    if "KG" in tail:
        return "kg", False
    # fallback: scan the full response in case the one-word answer wasn't on the last line
    if "DOCS" in resp_u or "DOC" in resp_u or "RAG" in resp_u:
        return "rag", False
    if "KG" in resp_u:
        return "kg", False
    return "kg", True  # genuinely ambiguous — defaulted, not chosen


def route_with(prompt_template, question):
    resp = ollama.generate(model=LLM, prompt=prompt_template.format(question=question))["response"]
    return parse_decision(resp)


def run_variant(name, prompt_template, items):
    decisions = {}
    for qid, q, cat in items:
        arm, ambiguous = route_with(prompt_template, q)
        decisions[qid] = {"question": q, "category": cat, "routed_to": arm, "ambiguous_parse": ambiguous}
        flag = " (ambiguous->defaulted)" if ambiguous else ""
        print(f"  [{name}] {qid:8} {cat:16} -> {arm}{flag}")
    return decisions


def score(decisions):
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
    ambiguous_n = sum(1 for d in decisions.values() if d["ambiguous_parse"])
    return {
        "n": n,
        "routing_accuracy_vs_oracle": correct_vs_oracle / n if n else 0,
        "systematic_rag_wins_caught": f"{rag_wins_caught}/{len(SYSTEMATIC_RAG_WINS)}",
        "factual_routed_to_docs": f"{factual_to_docs}/{factual_total}",
        "risky_category_misroutes_to_rag": risky_misroutes,
        "ambiguous_parses": ambiguous_n,
    }


if __name__ == "__main__":
    items = [it for it in ep.load_benchmark() if it[2] not in EXCLUDE]
    print(f"Routing {len(items)} questions (hierarchy excluded) through {len(VARIANTS)} prompt variants.\n")

    all_decisions = {}
    all_scores = {}
    for name, template in VARIANTS.items():
        print(f"--- Variant {name} ---")
        decisions = run_variant(name, template, items)
        all_decisions[name] = decisions
        all_scores[name] = score(decisions)
        print()

    print("=" * 78)
    print(f"{'variant':<14} {'acc_vs_oracle':>14} {'rag_wins_caught':>16} {'factual->docs':>14} {'ambiguous':>10}")
    print("-" * 78)
    for name, s in all_scores.items():
        print(f"{name:<14} {s['routing_accuracy_vs_oracle']:>13.0%} "
              f"{s['systematic_rag_wins_caught']:>16} {s['factual_routed_to_docs']:>14} "
              f"{s['ambiguous_parses']:>10}")
    print()
    for name, s in all_scores.items():
        if s["risky_category_misroutes_to_rag"]:
            print(f"{name}: RISKY misroutes to RAG (negative/cross_border/cross_disease): "
                  f"{s['risky_category_misroutes_to_rag']}")
        else:
            print(f"{name}: no risky-category misroutes to RAG.")

    out = {
        "_meta": {
            "model": LLM,
            "purpose": "prompt-sensitivity check before concluding LLM routing fails (see docstring)",
        },
        "scores": all_scores,
        "decisions": all_decisions,
    }
    json.dump(out, open(DATA / "phase2_prompt_sensitivity.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase2_prompt_sensitivity.json")