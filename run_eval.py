"""
run_eval.py — run the eval set through COLD vs RAG, for hand-grading.

Outputs two files in the same folder:
  - eval_results.md   : human-readable transcript (read this to grade)
  - eval_scores.csv   : structured sheet (fill in your Y/N judgments)

Prereqs: Ollama running + `ollama pull llama3.2:3b`; corpus.json and eval_set.json present;
         pip install ollama sentence-transformers numpy
Note: this makes ~50 model calls (25 questions x 2 conditions). Expect a few minutes.
"""
import json, csv
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

THRESHOLD = 0.48   # retrieval gate: if even the best match is weaker than this, refuse

MODEL = "llama3.1:8b" 
EMB_MOD = "all-MiniLM-L6-v2"
K       = 3

# --- Load corpus + eval set ---
corpus    = json.load(open("corpus.json", encoding="utf-8"))
doc_ids   = [r["id"] for r in corpus]
doc_texts = [r["text"] for r in corpus]
evalset   = json.load(open("eval_set.json", encoding="utf-8"))
print(f"{len(corpus)} corpus records, {len(evalset)} eval questions")

# --- Embed corpus + retrieval ---
embedder = SentenceTransformer(EMB_MOD)
doc_emb  = embedder.encode(doc_texts, normalize_embeddings=True)

def retrieve(query, k=K):
    q = embedder.encode([query], normalize_embeddings=True)[0]
    scores = doc_emb @ q
    order  = np.argsort(scores)[::-1][:k]
    return [(doc_ids[i], doc_texts[i], float(scores[i])) for i in order]

def ask(prompt):
    try:
        return ollama.generate(model=MODEL, prompt=prompt)["response"].strip()
    except Exception as e:
        return f"[ERROR: {e}]"

# The tuned RAG prompt (the sweet-spot version: answers when grounded, refuses on a true gap, no leaking)
RAG_TMPL = '''You are a plant-disease assistant for growers in Germany.
Use ONLY the facts in the context below.

Step 1 - decide if the context covers the disease or problem in the question:
- If NO disease in the context matches the question, reply exactly: "I don't have that in my sources." and nothing else.
- If a disease in the context DOES match, you MUST give an answer from the context. Do this even if the specific treatment the user asked about (a spray, fungicide, cure, etc.) is not available: in that case, say what the context states - for example that there is no chemical cure, or that fungicides are not effective - and give the management steps the context does provide.

Do NOT add any information that is not in the context, even if you believe you know it.
If the context mentions BVL-authorised products, include that point.


Context:
{context}

Question: {question}
Answer:'''

rows, md = [], []
for i, q in enumerate(evalset, 1):
    print(f"[{i:>2}/{len(evalset)}] {q['id']} ({q['type']}) ...", flush=True)
    question = q["question"]
    target   = q.get("target_id")

    # COLD
    cold = ask(question)

    # RAG
    top     = retrieve(question, K)
    ret_ids = [c for c, _, _ in top]
    best    = top[0][2]                      # cosine score of the top hit
    if best < THRESHOLD:
         rag = "I don't have that in my sources."   # too weak to trust — don't even ask the model
    else:
        context = "\n\n".join(f"[{cid}] {txt}" for cid, txt, _ in top)
        rag     = ask(RAG_TMPL.format(context=context, question=question))
        
    # Auto (objective) retrieval metrics
    top1      = ret_ids[0]
    hit_top1  = (target == top1) if target else ""
    hit_top3  = (target in ret_ids) if target else ""

    rows.append({
        "id": q["id"], "type": q["type"], "target_id": target or "",
        "retrieved_top1": top1, "retrieved_top3": "|".join(ret_ids),
        "retrieval_hit_top1": hit_top1, "retrieval_hit_top3": hit_top3,
        # --- fill these by hand (Y / N / leave blank if N/A) ---
        "cold_correct_disease": "", "cold_safe_advice": "", "cold_cited_BVL": "", "cold_refused_ok": "",
        "rag_correct_disease": "",  "rag_safe_advice": "",  "rag_cited_BVL": "",  "rag_refused_ok": "",
        "notes": "",
    })

    md.append(f"## {q['id']}  [{q['type']}]   target: {target or '— out of corpus —'}")
    md.append(f"**Question:** {question}\n")
    md.append("**Retrieved top-3:** " + ", ".join(f"{c} ({s:.2f})" for c, _, s in top) + "  ")
    if target:
        md.append(f"**Target in top-3:** {'YES' if hit_top3 else 'NO'}  |  **Top-1 correct:** {'YES' if hit_top1 else 'NO'}\n")
    if q.get("must_include"):
        md.append("**Must include:** " + "; ".join(q["must_include"]))
    if q.get("correct_behavior"):
        md.append("**Correct behaviour:** " + q["correct_behavior"])
    if q.get("unsafe_if"):
        md.append("**Unsafe if:** " + q["unsafe_if"])
    md.append(f"\n**— COLD —**\n\n{cold}\n")
    md.append(f"**— RAG —**\n\n{rag}\n")
    md.append("\n---\n")

# --- Write CSV scoring sheet ---
cols = list(rows[0].keys())
with open("eval_scores.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

# --- Write readable transcript ---
legend = (
    "# Evaluation run — COLD vs RAG\n\n"
    "Grade each answer in `eval_scores.csv` (Y / N, leave blank if not applicable):\n"
    "- **correct_disease** — named the right disease/pathogen\n"
    "- **safe_advice** — no wrong/harmful treatment (the key one; e.g. no fungicide for a virus)\n"
    "- **cited_BVL** — mentioned BVL / authorised-products rule where relevant\n"
    "- **refused_ok** — (out-of-corpus only) correctly said 'not in my sources' instead of fabricating\n\n"
    "Retrieval columns (top-1 / top-3 hit) are filled automatically.\n\n---\n\n"
)
with open("eval_results.md", "w", encoding="utf-8") as f:
    f.write(legend + "\n".join(md))

# --- Quick auto-summary of retrieval (the objective half) ---
with_target = [r for r in rows if r["target_id"]]
t1 = sum(1 for r in with_target if r["retrieval_hit_top1"] is True)
t3 = sum(1 for r in with_target if r["retrieval_hit_top3"] is True)
n  = len(with_target)
print(f"\nDone. Wrote eval_results.md (read) and eval_scores.csv (grade).")
print(f"Retrieval (auto, {n} in-corpus questions): top-1 correct {t1}/{n}, target in top-3 {t3}/{n}")