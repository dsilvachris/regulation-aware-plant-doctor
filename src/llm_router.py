"""
llm_router.py — Phase 2, Step 3: LLM-based per-question router.

The LLM predicts which retrieval strategy (KG or documents) will better answer a question, based on
the QUESTION ALONE. The routing PROMPT is written from GENERAL principles about when structured vs
textual retrieval helps — NOT from the Phase-1 grades (that would be training on the test set).
Pre-registering this prompt (committing it before running) is the audit trail that it wasn't tuned
to the known answers.

The LLM classifies only; downstream retrieval + answering stay deterministic/grounded (Phase-1 principle).

Run: python src/llm_router.py            # route the benchmark, save routing decisions
"""
import json, sys
from pathlib import Path
import ollama
DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
LLM = "llama3.2:3b"

# --- PRE-REGISTERED ROUTING PROMPT (principles only; no reference to which questions RAG won) ---
ROUTER_PROMPT = """You are a retrieval router for a plant-protection regulation assistant. Two retrieval
strategies are available:

KG (knowledge graph): best when the question requires REASONING OVER RELATIONSHIPS — connecting products,
substances, crops, pathogens, or countries; counting or comparing across categories; determining whether
something is NOT authorised (absence); or joining facts across diseases or jurisdictions.

DOCS (document retrieval): best when the question is a SIMPLE FACT LOOKUP answerable from a single passage
(e.g. what pathogen causes a disease), or needs FINE-GRAINED TEXTUAL DETAIL about a specific product that
would be spelled out in its description (e.g. the exact combination of substances in one named product).

Decide which single strategy will better answer the question below. Consider only the question itself.
Answer with exactly one word: KG or DOCS.

QUESTION: {question}
ANSWER:"""

def route_question(question):
    resp = ollama.generate(model=LLM, prompt=ROUTER_PROMPT.format(question=question))["response"].strip().upper()
    # parse first token
    if "DOCS" in resp or "DOC" in resp or "RAG" in resp:
        return "rag"
    return "kg"   # default to kg on anything ambiguous (safer per Phase-1: KG stronger overall)

if __name__ == "__main__":
    items = ep.load_benchmark()
    decisions = {}
    for qid, q, cat in items:
        if cat == "hierarchy":
            continue
        arm = route_question(q)
        decisions[qid] = {"question": q, "category": cat, "routed_to": arm}
        print(f"  {qid:8} {cat:16} -> {arm}")
    out = {"_meta": {"model": LLM, "prompt_note": "principled prompt, pre-registered; not tuned to grades"},
           "decisions": decisions}
    json.dump(out, open(DATA/"llm_router_decisions.json","w"), ensure_ascii=False, indent=2)
    print(f"\nRouted {len(decisions)} questions. Wrote data/llm_router_decisions.json")