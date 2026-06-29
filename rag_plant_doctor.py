"""
rag_plant_doctor.py — regulation-aware plant-disease RAG (Phase 2)
Runs locally on the Mac via Ollama. Data lives in corpus.json (separate from code).

Prereqs:
  - Ollama running (the `ollama serve` tab) with a model pulled: `ollama pull llama3.2:3b`
  - pip install ollama sentence-transformers numpy
  - corpus.json in the same folder as this file
"""
import json
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

MODEL   = "llama3.2:3b"
EMB_MOD = "all-MiniLM-L6-v2"

# --- Load corpus (data separate from code: growing the corpus = editing JSON only) ---
records   = json.load(open("corpus.json", encoding="utf-8"))
doc_ids   = [r["id"]   for r in records]
doc_texts = [r["text"] for r in records]
doc_meta  = {r["id"]: r for r in records}     # id -> full record (crop, eppo, source, ...)
print(f"{len(records)} corpus records loaded: " + ", ".join(doc_ids))

# --- Embed the corpus once ---
embedder = SentenceTransformer(EMB_MOD)
doc_emb  = embedder.encode(doc_texts, normalize_embeddings=True)

# --- Retrieval: embed query, cosine-similarity against every doc ---
def retrieve(query, k=3):
    q = embedder.encode([query], normalize_embeddings=True)[0]
    scores = doc_emb @ q
    order  = np.argsort(scores)[::-1][:k]
    return [(doc_ids[i], doc_texts[i], float(scores[i])) for i in order]

# --- Retrieval sanity check: plain-language symptoms -> expected disease ---
# Watch closely: the leaf-spot/blight diseases share vocabulary and may confuse the retriever.
probes = {
    "olive mould on the underside of greenhouse tomato leaves":              "tomato_leaf_mould",
    "dark target-like concentric rings on older potato leaves":              "tomato_potato_early_blight",
    "small grey spots with tiny black dots on lower tomato leaves":          "tomato_septoria_leaf_spot",
    "olive-green velvety scabby spots on apple fruit and leaves":            "apple_scab",
    "water-soaked grey-green patches spreading fast in cool wet weather":    "tomato_potato_late_blight",
}
print("\n=== Retrieval sanity check (expected vs. top-1) ===")
for q, expected in probes.items():
    top = retrieve(q, k=3)
    flag = "OK  " if top[0][0] == expected else "MISS"
    print(f"[{flag}] {q[:54]:54s} -> {top[0][0]:28s} ({top[0][2]:.3f})")

# --- LLM via local Ollama ---
def ask_llm(prompt):
    return ollama.generate(model=MODEL, prompt=prompt)["response"].strip()

# --- Three-condition experiment on a real question ---
question = "My tomato plants have a mosaic pattern on the leaves. What is it and how do I treat it?"

# (a) COLD — no retrieval
cold = ask_llm(question)

# (b) RAG — top-3 real corpus chunks as grounding
top     = retrieve(question, k=3)
context = "\n\n".join(f"[{cid}] {txt}" for cid, txt, _ in top)
rag_prompt = f"""If the context does not contain ANY relevant information about the disease in the question, reply exactly: "I don't have that in my sources." Otherwise, answer using the context.
Do NOT add information that is not in the context, even if you believe you know it.

Context:
{context}

Question: {question}
Answer:"""
rag = ask_llm(rag_prompt)

# (c) RAG with WRONG context — give it apple scab, same strict instructions
wrong = ask_llm(rag_prompt.replace(context, doc_meta["apple_scab"]["text"]))

print("\n=== Retrieved for the question (with sources) ===")
for cid, _, s in top:
    print(f"  {s:.3f}  {cid}  (source: {doc_meta[cid]['source']})")

print("\n=== (a) COLD — no retrieval ===\n", cold)
print("\n=== (b) RAG — grounded on real corpus ===\n", rag)
print("\n=== (c) RAG — WRONG context (apple scab) ===\n", wrong)