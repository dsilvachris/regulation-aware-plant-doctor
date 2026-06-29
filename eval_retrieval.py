"""
eval_retrieval.py — Step 5, Phase 3.
Compare retrieval BEFORE (baseline all-MiniLM-L6-v2) vs AFTER (fine-tuned) on the
held-out 25 eval questions. No LLM, no Ollama — pure retrieval, runs in seconds.

This is the real test: the eval questions were NEVER in training.

Prereqs: corpus.json, eval_set.json, and the ./finetuned-agri-embedder folder present.
"""
import json
import numpy as np
from sentence_transformers import SentenceTransformer

corpus  = json.load(open("corpus.json", encoding="utf-8"))
evalset = json.load(open("eval_set.json", encoding="utf-8"))
doc_ids   = [r["id"] for r in corpus]
doc_texts = [r["text"] for r in corpus]
incorpus  = [q for q in evalset if q.get("target_id")]   # only questions with a known answer

def evaluate(model_name_or_path, label):
    m = SentenceTransformer(model_name_or_path)
    doc_emb = m.encode(doc_texts, normalize_embeddings=True)
    rows, t1, t3 = [], 0, 0
    for q in incorpus:
        qe = m.encode([q["question"]], normalize_embeddings=True)[0]
        scores = doc_emb @ qe
        order = np.argsort(scores)[::-1]
        ids = [doc_ids[i] for i in order]
        top1_ok = ids[0] == q["target_id"]
        top3_ok = q["target_id"] in ids[:3]
        t1 += top1_ok; t3 += top3_ok
        rank = ids.index(q["target_id"]) + 1
        rows.append((q["id"], q["target_id"], ids[0], float(scores[order[0]]), rank, top1_ok))
    n = len(incorpus)
    print(f"\n=== {label} ===")
    print(f"top-1 correct: {t1}/{n} ({t1/n*100:.0f}%)   top-3: {t3}/{n} ({t3/n*100:.0f}%)")
    return {r[0]: r for r in rows}, t1, t3, n

base, b1, b3, n = evaluate("all-MiniLM-L6-v2", "BASELINE (general MiniLM)")
ft,   f1, f3, _ = evaluate("finetuned-agri-embedder", "FINE-TUNED (domain)")

print("\n=== HEAD-TO-HEAD ===")
print(f"top-1: baseline {b1}/{n}  ->  fine-tuned {f1}/{n}   ({f1-b1:+d})")
print(f"top-3: baseline {b3}/{n}  ->  fine-tuned {f3}/{n}   ({f3-b3:+d})")

print("\nPer-question changes (only where top-1 changed):")
print(f"  {'Q':4} {'target':30} {'base top1':30} {'ft top1':30}")
for qid in base:
    b = base[qid]; f = ft[qid]
    if b[5] != f[5]:                      # top-1 correctness flipped
        arrow = "FIXED " if f[5] else "BROKE "
        print(f"  {arrow}{qid:4} {b[1]:30} base:{b[2][:24]:26} ft:{f[2][:24]}")

# focus: the late/early blight queries and the terse retrieval-stress ones
print("\nKey cases (target -> rank under each model):")
focus = ["q04","q10","q24","q21","q23","q02","q17"]
for qid in focus:
    if qid in base:
        print(f"  {qid}: target {base[qid][1]:30}  baseline rank {base[qid][4]}  ->  fine-tuned rank {ft[qid][4]}")