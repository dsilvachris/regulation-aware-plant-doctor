"""
check_scores.py — does fine-tuning raise the top-1 SCORES of the threshold casualties?
The 0.48 retrieval threshold wrongly refused q21 and q23 (scores too low, not wrong rank).
Question: does the fine-tuned embedder lift them above 0.48?
"""
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent
DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'
import json
import numpy as np
from sentence_transformers import SentenceTransformer

corpus  = json.load(open(str(DATA / "corpus.json"), encoding="utf-8"))
evalset = {q["id"]: q for q in json.load(open(str(DATA / "eval_set.json"), encoding="utf-8"))}
doc_ids   = [r["id"] for r in corpus]
doc_texts = [r["text"] for r in corpus]
THRESHOLD = 0.48

def top1_score(m, doc_emb, question):
    qe = m.encode([question], normalize_embeddings=True)[0]
    s = doc_emb @ qe
    return float(s.max())

def run(path, label):
    m = SentenceTransformer(path)
    doc_emb = m.encode(doc_texts, normalize_embeddings=True)
    print(f"\n{label}")
    for qid in ["q21","q23","q06","q02","q07"]:   # low-scoring in-corpus cases near the threshold
        q = evalset[qid]
        sc = top1_score(m, doc_emb, q["question"])
        gate = "PASS" if sc >= THRESHOLD else "refused"
        print(f"  {qid}: top-1 score {sc:.3f}  [{gate} @ {THRESHOLD}]   ({q['question'][:50]})")

run("all-MiniLM-L6-v2", "BASELINE")
run(str(MODELS / "finetuned-agri-embedder"), "FINE-TUNED")