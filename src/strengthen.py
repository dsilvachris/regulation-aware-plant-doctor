"""
strengthen.py — repeated-run rigor pass.
Runs each condition N times and AUTO-measures the refusal metrics (no grading):
  - over_refusal      : in-corpus questions the model wrongly REFUSED (should have answered)
  - ooc_refused       : out-of-corpus questions the model CORRECTLY refused
Reports mean +/- range across runs, turning single-run point estimates into intervals.

Why no grading: a refusal is detectable from the answer text ("I don't have that...").
correct_disease / safe_advice still need a human, so they stay single-run (in the results note).

Conditions: v1 = 3B + strict prompt; v3 = 8B + revised prompt (the two key contrast points).
Prereqs: Ollama running; corpus.json + eval_set.json present. Writes strengthen_results.json + .md.
Runtime: N x 25 x 2 conditions model calls. ~1-3 h unattended (8B is the slow half).
"""
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent
DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'
import json, time, statistics, re
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

N_RUNS  = 10
EMB_MOD = "all-MiniLM-L6-v2"
K       = 3

corpus    = json.load(open(str(DATA / "corpus.json"), encoding="utf-8"))
evalset   = json.load(open(str(DATA / "eval_set.json"), encoding="utf-8"))
doc_ids   = [r["id"] for r in corpus]
doc_texts = [r["text"] for r in corpus]

embedder = SentenceTransformer(EMB_MOD)
doc_emb  = embedder.encode(doc_texts, normalize_embeddings=True)

def retrieve(q, k=K):
    qe = embedder.encode([q], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb @ qe)[::-1][:k]
    return [(doc_ids[i], doc_texts[i]) for i in order]

def is_refusal(txt):
    return txt.strip().lower().startswith("i don't have")

def ask(model, prompt):
    try:
        return ollama.generate(model=model, prompt=prompt)["response"].strip()
    except Exception as e:
        return f"[ERROR: {e}]"

# --- the two prompts (v1 strict, v3 revised) ---
STRICT = '''You are a plant-disease assistant. Answer using ONLY the context below.
If the context does not cover the question, reply exactly: "I don't have that in my sources." and nothing more.

Context:
{context}

Question: {question}
Answer:'''

REVISED = '''You are a plant-disease assistant for growers in Germany.
Use ONLY the facts in the context below.
Step 1 - if NO disease in the context matches the question, reply exactly: "I don't have that in my sources." and nothing else.
Step 2 - if a disease in the context DOES match, you MUST answer from the context, even if the specific treatment asked about does not exist (then say so and give what the context provides).
Do NOT add information that is not in the context, even if you believe you know it.
If the context mentions BVL-authorised products, include that point.

Context:
{context}

Question: {question}
Answer:'''

CONDITIONS = [
    {"label": "v1_3B_strict",  "model": "llama3.2:3b", "tmpl": STRICT},
    {"label": "v3_8B_revised", "model": "llama3.1:8b", "tmpl": REVISED},
]

incorpus = [q for q in evalset if q.get("target_id")]
ooc      = [q for q in evalset if not q.get("target_id")]
print(f"{len(incorpus)} in-corpus, {len(ooc)} out-of-corpus | {N_RUNS} runs x {len(CONDITIONS)} conditions\n")

def one_run(cond):
    """One full pass over the eval set; returns (over_refusal_count, ooc_refused_count)."""
    over = 0
    for q in incorpus:
        top = retrieve(q["question"])
        ctx = "\n\n".join(f"[{cid}] {txt}" for cid, txt in top)
        ans = ask(cond["model"], cond["tmpl"].format(context=ctx, question=q["question"]))
        if is_refusal(ans):
            over += 1                       # in-corpus refusal = over-refusal
    ref = 0
    for q in ooc:
        top = retrieve(q["question"])
        ctx = "\n\n".join(f"[{cid}] {txt}" for cid, txt in top)
        ans = ask(cond["model"], cond["tmpl"].format(context=ctx, question=q["question"]))
        if is_refusal(ans):
            ref += 1                        # out-of-corpus refusal = correct
    return over, ref

results = {}
for cond in CONDITIONS:
    print(f"=== {cond['label']} ({cond['model']}) ===")
    overs, refs = [], []
    for r in range(1, N_RUNS + 1):
        t0 = time.time()
        over, ref = one_run(cond)
        overs.append(over); refs.append(ref)
        print(f"  run {r:>2}/{N_RUNS}: over-refusal {over}/{len(incorpus)}  ooc-refused {ref}/{len(ooc)}  ({time.time()-t0:.0f}s)", flush=True)
    results[cond["label"]] = {"over_refusal": overs, "ooc_refused": refs}
    # save after each condition so nothing is lost
    json.dump(results, open(str(RESULTS / "strengthen_results.json"), "w"), indent=2)

# --- summary ---
def fmt(vals, n):
    pct = [v / n * 100 for v in vals]
    return f"{statistics.mean(pct):.0f}% (range {min(pct):.0f}-{max(pct):.0f}%, raw {min(vals)}-{max(vals)}/{n})"

lines = ["# Strengthen — repeated-run refusal metrics\n",
         f"{N_RUNS} runs per condition. Auto-measured from answer text (no grading).\n"]
print("\n================ SUMMARY ================")
for cond in CONDITIONS:
    lab = cond["label"]; r = results[lab]
    o = fmt(r["over_refusal"], len(incorpus))
    f = fmt(r["ooc_refused"], len(ooc))
    block = f"\n**{lab}** ({cond['model']})\n- over-refusal (in-corpus wrongly refused): {o}\n- ooc-refused (correctly refused): {f}\n- raw over-refusal counts: {r['over_refusal']}"
    print(block); lines.append(block)
open(str(RESULTS / "strengthen_results.md"), "w").write("\n".join(lines))
print("\nSaved strengthen_results.json and strengthen_results.md")