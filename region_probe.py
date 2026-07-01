"""
region_probe.py — probe the HARD cases and print answers for HAND-grading (no auto-scorer;
they've proven unreliable). For each question: if a region is given, retrieve region-aware
(filter to that country); if not, retrieve blind (over all 15) — which is the realistic
behaviour when the country is unknown or only implied.
"""
import json
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

LLM = "llama3.2:3b"; K = 3
emb = SentenceTransformer("all-MiniLM-L6-v2")
corpus = json.load(open("corpus.json", encoding="utf-8"))
probes = json.load(open("region_probe_set.json", encoding="utf-8"))
doc_emb = emb.encode([r["text"] for r in corpus], normalize_embeddings=True)

def retrieve(question, region, k=K):
    idx = [i for i, r in enumerate(corpus) if (region is None or r["country"] == region)]
    qe = emb.encode([question], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb[idx] @ qe)[::-1][:k]
    return [corpus[idx[j]] for j in order]

def answer(question, ctx):
    prompt = f"""You are a plant-disease assistant. Use ONLY the context below.
Name the disease and how to manage it, and state which national authority's authorised
products must be used. If the country is unclear, say so rather than guessing.
Do not add facts that are not in the context.

Context:
{ctx}

Question: {question}
Answer:"""
    return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

for q in probes:
    top = retrieve(q["question"], q["region"])
    ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
    ans = answer(q["question"], ctx)
    retr = "AWARE(" + q["region"] + ")" if q["region"] else "BLIND(all)"
    print("="*72)
    print(f"{q['id']} | {q['category']} | retrieval={retr} | top1={top[0]['id']} ({top[0]['country']})")
    print(f"Q: {q['question']}")
    print(f"PASS IF: {q['pass_criteria']}")
    print(f"A: {ans}")
    print()