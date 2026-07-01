"""
region_eval.py — does region-blind grounding give region-INCORRECT regulatory advice,
and does region-aware retrieval fix it?

Two conditions on the same 15-entry corpus (12 DE + 3 NO):
  - region-BLIND  : pure cosine over ALL entries (no country filter)
  - region-AWARE  : filter corpus to the grower's country, THEN cosine

Because DE and NO twins share near-identical disease text, blind retrieval can't tell them
apart and often cites the wrong authority. Aware retrieval conditions on country first.

Metric (auto, no grading): did the GROUNDED answer cite the correct authority for the
grower's region (BVL for DE, Mattilsynet for NO) and NOT the wrong one?
Prereqs: Ollama running; corpus.json + region_eval_set.json present.
"""
import json, re
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

LLM = "llama3.2:3b"
K = 3
emb = SentenceTransformer("all-MiniLM-L6-v2")

corpus  = json.load(open("corpus.json", encoding="utf-8"))
evalset = json.load(open("region_eval_set.json", encoding="utf-8"))
texts   = [r["text"] for r in corpus]
doc_emb = emb.encode(texts, normalize_embeddings=True)

def retrieve(question, country=None, k=K):
    idx = [i for i, r in enumerate(corpus) if (country is None or r["country"] == country)]
    qe = emb.encode([question], normalize_embeddings=True)[0]
    sims = doc_emb[idx] @ qe
    order = np.argsort(sims)[::-1][:k]
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

def authority_score(text, expect, avoid):
    t = text.lower()
    said_expect = expect.lower() in t or ("food safety" in t if expect=="Mattilsynet" else False) \
                  or ("federal office" in t if expect=="BVL" else False)
    said_avoid  = avoid.lower() in t or ("food safety" in t if avoid=="Mattilsynet" else False) \
                  or ("federal office" in t if avoid=="BVL" else False)
    return said_expect, said_avoid

def run(condition):
    aware = condition == "aware"
    correct = wrong = 0
    rows = []
    for q in evalset:
        country = q["country"] if aware else None
        top = retrieve(q["question"], country=country)
        ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
        ans = answer(q["question"], ctx)
        top1_country = top[0]["country"]
        said_e, said_a = authority_score(ans, q["expect_authority"], q["avoid_authority"])
        ok = said_e and not said_a
        correct += ok; wrong += said_a
        rows.append((q["id"], q["country"], top1_country, q["expect_authority"], said_e, said_a, ok))
    return correct, wrong, rows

print("=== REGION-BLIND (no country filter) ===")
cb, wb, rows_b = run("blind")
print(f"correct authority: {cb}/{len(evalset)}   wrong authority cited: {wb}")
print("=== REGION-AWARE (filter to grower's country) ===")
ca, wa, rows_a = run("aware")
print(f"correct authority: {ca}/{len(evalset)}   wrong authority cited: {wa}")

print(f"\nHEAD-TO-HEAD: correct authority  blind {cb}/{len(evalset)}  ->  aware {ca}/{len(evalset)}")
print(f"             wrong authority   blind {wb}        ->  aware {wa}")

print("\nPer-question (Q | region | top1-retrieved-region | gave-right | gave-wrong):")
print("  BLIND:")
for r in rows_b:
    flag = "OK " if r[6] else "XX "
    print(f"    {flag}{r[0]} {r[1]} | top1={r[2]} | right_auth={r[4]} wrong_auth={r[5]}")
print("  AWARE:")
for r in rows_a:
    flag = "OK " if r[6] else "XX "
    print(f"    {flag}{r[0]} {r[1]} | top1={r[2]} | right_auth={r[4]} wrong_auth={r[5]}")

json.dump({"blind": {"correct": cb, "wrong": wb}, "aware": {"correct": ca, "wrong": wa}},
          open("region_eval_results.json", "w"), indent=2)
print("\nSaved region_eval_results.json")