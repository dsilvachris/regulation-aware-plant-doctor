"""
region_inspect.py — print the ACTUAL grounded answers (not just flags) so we can see
whether the authority problem is real LLM leakage or just the auto-scorer miscounting paraphrases.
Prints, per question: retrieved region, what authority we EXPECTED, and the full answer text.
"""
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent
DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'
import json
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

LLM = "llama3.2:3b"
K = 3
emb = SentenceTransformer("all-MiniLM-L6-v2")
corpus  = json.load(open(str(DATA / "corpus.json"), encoding="utf-8"))
evalset = json.load(open(str(DATA / "region_eval_set.json"), encoding="utf-8"))
doc_emb = emb.encode([r["text"] for r in corpus], normalize_embeddings=True)

def retrieve(question, country, k=K):
    idx = [i for i, r in enumerate(corpus) if r["country"] == country]   # region-AWARE
    qe = emb.encode([question], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb[idx] @ qe)[::-1][:k]
    return [corpus[idx[j]] for j in order]

def answer(question, ctx):
    prompt = f"""You are a plant-disease assistant. Use ONLY the context below.
Name the disease and how to manage it, and state which national authority's authorised
products must be used. Do not add facts that are not in the context.

Context:
{ctx}

Question: {question}
Answer:"""
    return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

for q in evalset:
    top = retrieve(q["question"], q["country"])
    ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
    ans = answer(q["question"], ctx)
    print("="*70)
    print(f"{q['id']} | region={q['country']} | retrieved top1={top[0]['country']} | EXPECT authority: {q['expect_authority']} (avoid {q['avoid_authority']})")
    print(f"Q: {q['question']}")
    print(f"A: {ans}")
    print()