"""
eval_pipeline_phase4.py — Phase 4, Step 4: the shared explanation wrapper + routing table.

BOTH arms use the SAME LLM and the SAME prompt; only the retrieved {facts} differ — same isolation
principle as eval_pipeline.py:
  - KG arm  : verified facts from deterministic SPARQL (kg_arm_phase4) + verbaliser (kg_verbalise_phase4)
  - RAG arm : top-k retrieved prose documents (rag_arm_phase4)

ROUTING is explicit and hand-written from the benchmark file (data/benchmark_phase4.json), same
"auditable, not LLM-guessed" principle as Phase 1's eval_pipeline.py.

Run: python src/eval_pipeline_phase4.py --demo   -> a few questions, both arms, side by side
"""
import json, sys
from pathlib import Path
import ollama
import kg_arm_phase4 as kg
import rag_arm_phase4 as rag
from kg_verbalise_phase4 import verbalise

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LLM = "llama3.2:3b"

SHARED_PROMPT = """You are a pharmaceutical regulatory assistant. Answer the question using ONLY the
facts provided below. If the facts do not support an answer, say so plainly — do not guess and do not add
information that is not in the facts. Be concise and precise.

FACTS:
{facts}

QUESTION: {question}
ANSWER:"""

ONCOLOGY = ["niraparib", "isatuximab", "epcoritamab", "dostarlimab", "melphalan flufenamide"]
ROSTER = ["aducanumab", "lecanemab", "donanemab"] + ONCOLOGY

# Explicit, deterministic per-question routing: (query_fn, params, verbalise_category).
# Written by hand from data/benchmark_phase4.json - not inferred by an LLM.
ROUTING = {
    "f1": (kg.q_atc_code, {"substance": "lecanemab"}, "atc_code"),
    "f2": (kg.q_atc_code, {"substance": "niraparib"}, "atc_code"),
    "f3": (kg.q_atc_code, {"substance": "isatuximab"}, "atc_code"),
    "r1": (kg.q_regulator, {"substance": "dostarlimab", "region": "US"}, "regulator"),
    "r2": (kg.q_is_centralised, {"substance": "niraparib"}, "centralised"),
    "m1": (kg.q_substances_in_atc_subclass, {"candidates": ONCOLOGY, "prefix": "L01F"}, "atc_subclass_filter"),
    "c1": (kg.q_orphan_substances, {"candidates": ONCOLOGY}, "orphan_filter"),
    "n1": (kg.q_current_status, {"substance": "aducanumab", "region": "EU"}, "current_status"),
    "n2": (kg.q_current_status, {"substance": "melphalan flufenamide", "region": "US"}, "current_status"),
    "d1": (kg.q_divergent, {"candidates": ROSTER, "favoured_region": "US"}, "divergent"),
    "d2": (kg.q_divergent, {"candidates": ROSTER, "favoured_region": "EU"}, "divergent"),
    "h1": (kg.q_shares_atc_ancestor, {"substance": "niraparib", "ancestor_code": "L01"}, "shares_atc_ancestor"),
    "h2": (kg.q_shares_atc_ancestor, {"substance": "lecanemab", "ancestor_code": "N06D"}, "shares_atc_ancestor"),
    "h3": (kg.q_shares_atc_ancestor_bool,
           {"substance_a": "aducanumab", "substance_b": "lecanemab", "ancestor_code": "N06D"},
           "shares_atc_ancestor_bool"),
}


def route(qid):
    return ROUTING[qid]


def load_benchmark():
    """Returns [(id, question_text, category), ...] flattened from benchmark_phase4.json."""
    data = json.load(open(DATA / "benchmark_phase4.json", encoding="utf-8"))
    items = []
    for key, qs in data.items():
        if key == "_meta":
            continue
        cat = key.split("_", 2)[-1] if key.startswith("category_") else key
        for q in qs:
            items.append((q["id"], q["q"], cat))
    return items


def explain(question, facts_text):
    prompt = SHARED_PROMPT.format(facts=facts_text, question=question)
    return ollama.generate(model=LLM, prompt=prompt)["response"].strip()


def kg_answer_by_id(qid, question):
    query_fn, params, vcat = route(qid)
    facts = query_fn(**params)
    facts_text = verbalise(vcat, facts)
    return explain(question, facts_text), facts


def rag_answer(question):
    docs = rag.rag_retrieve(question)
    facts_text = "\n".join(f"- {d}" for d in docs)
    return explain(question, facts_text), docs


if __name__ == "__main__":
    items = load_benchmark()
    demo_ids = ["f1", "n1", "h2", "h3"] if "--demo" in sys.argv else [i for i, _, _ in items]
    for qid, q, cat in items:
        if qid not in demo_ids:
            continue
        print(f"\n=== {qid} ({cat}): {q} ===")
        kg_ans, facts = kg_answer_by_id(qid, q)
        print(f"  [KG]  {kg_ans}")
        rag_ans, docs = rag_answer(q)
        print(f"  [RAG] {rag_ans}")