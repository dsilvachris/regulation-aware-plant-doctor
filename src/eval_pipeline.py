"""
eval_pipeline.py — Stage 5/6: the shared explanation wrapper + comparison runner.

BOTH arms use the SAME LLM and the SAME prompt; only the retrieved {facts} differ:
  - KG arm  : verified facts from deterministic category-based SPARQL (kg_arm)
  - RAG arm : top-k retrieved prose documents (rag_arm)

This isolation (same model, same prompt, only representation differs) is the whole experiment.
Answers are written to a JSON for BLIND grading (arm labels hidden at grading time).

Run:  python src/eval_pipeline.py            # runs both arms over the benchmark, writes answers
      python src/eval_pipeline.py --demo     # just show a few side-by-side, no file
"""
import json, sys
from pathlib import Path
import ollama
import kg_arm, rag_arm
from kg_verbalise import verbalise, verbalise2, verbalise3

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LLM = "llama3.2:3b"

SHARED_PROMPT = """You are a plant-protection regulatory assistant. Answer the question using ONLY the
facts provided below. If the facts do not support an answer, say so plainly — do not guess and do not add
information that is not in the facts. Be concise and precise.

FACTS:
{facts}

QUESTION: {question}
ANSWER:"""

def explain(question, facts_text):
    prompt = SHARED_PROMPT.format(facts=facts_text, question=question)
    return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

def kg_answer_by_id(qid, question):
    query_fn, params, vcat = route(qid)
    facts = query_fn(**params)
    facts_text = verbalise3(vcat, facts) or verbalise2(vcat, facts)
    if facts_text is None:
        facts_text = verbalise(vcat, facts)
    return explain(question, facts_text), facts

def rag_answer(question):
    docs = rag_arm.rag_retrieve(question)
    facts_text = "\n".join(f"- {d}" for d in docs)
    return explain(question, facts_text), docs

# Explicit, deterministic per-question routing: (kg_query_fn_name, params).
# This replaces text-guessing — each benchmark question maps to exactly one KG query + params.
# Written by hand from the benchmark files so routing is auditable, not inferred by an LLM.
import kg_arm as _kg

ROUTING = {
    # factual (control) — disease facts
    "f01": ("q_factual", {}), "f02": ("q_factual", {}), "f03": ("q_factual", {}),
    "f04": ("q_factual", {}), "f05": ("q_factual", {}), "f06": ("q_factual", {}),
    "f07": ("q_factual", {}), "f08": ("q_factual", {}), "f09": ("q_factual", {}), "f10": ("q_factual", {}),
    # region-specific — authority + where-to-check
    "r01": ("q_authority", {"country": "DE"}), "r02": ("q_authority", {"country": "NO"}),
    "r03": ("q_authority", {"country": "NO"}), "r04": ("q_authority", {"country": "DE"}),
    "r05": ("q_products_in_country", {"country": "NO"}), "r06": ("q_products_in_country", {"country": "DE"}),
    "r07": ("q_products_in_country", {"country": "NO"}), "r08": ("q_substance_in_both", {"substance": "cyazofamid"}),
    "r09": ("q_authority", {"country": "NO"}),
    # multi-hop
    "m01": ("q_substances_in_country", {"country": "NO"}),
    "m02": ("q_substances_in_country", {"country": "NO"}),   # "which DE substance also in NO" -> list NO's, all are in DE
    "m03": ("q_substances_de_only", {}),
    "m04": ("q_products_in_country", {"country": "NO"}),
    # constraint
    "c01": ("q_products_with_substance", {"country": "NO", "substance": "mandipropamid"}),
    "c02": ("q_products_single_substance", {"country": "NO"}),
    "c03": ("q_products_with_substance", {"country": "NO", "substance": "mandipropamid"}),
    "c04": ("q_products_with_substance", {"country": "NO", "substance": "copper"}),
    # negative/absence
    "n01": ("q_products_in_country", {"country": "DE"}),   # (cucurbit mildew not in late-blight KG — expect honest 'no data')
    "n02": ("q_is_substance_authorised", {"country": "NO", "substance": "fluazinam"}),
    "n03": ("q_is_substance_authorised", {"country": "NO", "substance": "copper"}),
    "n04": ("q_products_in_country", {"country": "NO"}),
    # cross-border divergence
    "d01": ("q_divergence_counts", {}),
    "d02": ("q_divergence_counts", {}),   # apple scab not in late-blight KG — expect honest 'no data'
    "d03": ("q_substance_in_both", {"substance": "cyazofamid"}),
    "d04": ("q_divergence_counts", {}),
    "d05": ("q_divergence_counts", {}),   # cucurbit mildew not in late-blight KG
    "d06": ("q_substances_de_only", {}),
}

# category label per query fn, so we pick the right verbaliser
FN_CATEGORY = {
    "q_factual": "factual", "q_authority": "authority",
    "q_products_in_country": "region_specific", "q_substances_in_country": "multi_hop",
    "q_substances_de_only": "de_only", "q_products_with_substance": "products_with_substance",
    "q_products_single_substance": "single_substance", "q_is_substance_authorised": "negative",
    "q_divergence_counts": "cross_border", "q_substance_in_both": "substance_in_both",
    "q_substance_multi_disease": "multi_disease",
}

# Routing for the Phase-1 expansion questions (apple scab, powdery mildew, cross-disease).
ROUTING_EXPANSION = {
    # apple scab
    "as_m01": ("q_substances_in_country", {"country": "NO", "disease": "apple_scab"}),
    "as_m02": ("q_substances_in_country", {"country": "DE", "disease": "apple_scab"}),
    "as_c01": ("q_products_with_substance", {"country": "NO", "substance": "dithianon", "disease": "apple_scab"}),
    "as_c02": ("q_products_with_substance", {"country": "DE", "substance": "sulfur", "disease": "apple_scab"}),
    "as_n01": ("q_is_substance_authorised", {"country": "NO", "substance": "captan", "disease": "apple_scab"}),
    "as_d01": ("q_divergence_counts", {"disease": "apple_scab"}),
    "as_d02": ("q_substance_in_both", {"substance": "dithianon", "disease": "apple_scab"}),
    # powdery mildew
    "pm_n01": ("q_products_in_country", {"country": "DE", "disease": "powdery_mildew"}),
    "pm_n02": ("q_is_substance_authorised", {"country": "NO", "substance": "sulfur", "disease": "powdery_mildew"}),
    "pm_d01": ("q_divergence_counts", {"disease": "powdery_mildew"}),
    "pm_d02": ("q_substance_in_both", {"substance": "proquinazid", "disease": "powdery_mildew"}),
    "pm_d03": ("q_substances_in_country", {"country": "DE", "disease": "powdery_mildew"}),
    # cross-disease (the new capability — no single disease)
    "xd_01": ("q_substance_multi_disease", {}),
    "xd_02": ("q_substance_multi_disease", {}),
}
ROUTING.update(ROUTING_EXPANSION)

def route(qid):
    """Return (query_fn, params, verbalise_category) for a benchmark question id.
    For the original late-blight questions (no disease in params), inject disease='late_blight'
    so they filter correctly in the combined 3-disease graph."""
    fn_name, params = ROUTING.get(qid, ("q_factual", {}))
    params = dict(params)
    # original late-blight ids: f*, r*, m*, c0*, n*, d0* — add the disease filter if absent
    if "disease" not in params and not qid.startswith(("as_", "pm_", "xd_")):
        params["disease"] = "late_blight"
    return getattr(_kg, fn_name), params, FN_CATEGORY[fn_name]

DEMO = [
    ("m01", "Which active substances are authorised against late blight in Norway?"),
    ("n02", "Is fluazinam authorised for late blight in Norway?"),
    ("d01", "How does the number of authorised late-blight products differ between Germany and Norway?"),
]

def load_benchmark():
    """Load all benchmark questions with their category + id from the two files."""
    items = []
    b12 = json.load(open(DATA / "benchmark_cat1_2.json", encoding="utf-8"))
    for q in b12.get("category_1_factual", []):
        items.append((q["id"], q["q"], "factual"))
    for q in b12.get("category_2_region_specific", []):
        items.append((q["id"], q["q"], "region_specific"))
    b37 = json.load(open(DATA / "benchmark_cat3_7.json", encoding="utf-8"))
    catmap = {"category_3_multi_hop": "multi_hop", "category_4_constraint": "constraint",
              "category_5_negative_absence": "negative", "category_6_cross_border_divergence": "cross_border",
              "category_7_hierarchy_traversal": "hierarchy"}
    for key, cat in catmap.items():
        for q in b37.get(key, []):
            items.append((q["id"], q["q"], cat))
    # Phase 1 expansion: apple scab + powdery mildew + cross-disease
    try:
        bmd = json.load(open(DATA / "benchmark_multidisease.json", encoding="utf-8"))
        for disease_block in ("apple_scab", "powdery_mildew"):
            for cat, qs in bmd.get(disease_block, {}).items():
                if isinstance(qs, list):
                    for q in qs:
                        items.append((q["id"], q["q"], cat))
        for q in bmd.get("cross_disease", {}).get("questions", []):
            items.append((q["id"], q["q"], "cross_disease"))
    except FileNotFoundError:
        pass
    return items

def run_full():
    items = load_benchmark()
    results = []
    for qid, q, cat in items:
        if cat == "hierarchy":
            continue   # category 7 open — skip
        try:
            kg_a, kg_f = kg_answer_by_id(qid, q)
        except Exception as e:
            kg_a, kg_f = f"[error: {e}]", {}
        rag_a, rag_d = rag_answer(q)
        results.append({"id": qid, "category": cat, "question": q,
                        "kg_answer": kg_a, "rag_answer": rag_a})
        print(f"  {qid} ({cat}) done")
    out = {"_meta": {"model": LLM, "note": "For blind grading, anonymise kg_answer/rag_answer as System A/B, shuffled per question."},
           "results": results}
    json.dump(out, open(DATA / "comparison_answers.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nWrote data/comparison_answers.json  ({len(results)} questions x 2 arms)")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        for qid, q in DEMO:
            kg_a, _ = kg_answer_by_id(qid, q)
            rag_a, _ = rag_answer(q)
            print("=" * 78)
            print(f"[{qid}] {q}\n")
            print(f"KG answer : {kg_a}")
            print(f"RAG answer: {rag_a}\n")
    else:
        run_full()