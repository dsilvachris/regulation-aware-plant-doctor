"""
gen_train_queries.py — Step 5, Phase 1.
Generate synthetic symptom-style queries per disease (training data for fine-tuning the embedder).

IMPORTANT: these are TRAINING queries. They must stay separate from the 25 eval questions.
Never let an eval question into this file.

Prereqs: Ollama running + llama3.1:8b; corpus.json present; pip install ollama
"""
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent
DATA, MODELS, RESULTS = _ROOT/'data', _ROOT/'models', _ROOT/'results'
import json, re, random
import ollama

MODEL = "llama3.1:8b"
N_PER_DISEASE = 10

corpus = json.load(open(str(DATA / "corpus.json"), encoding="utf-8"))

def gen_queries(rec, n=N_PER_DISEASE):
    prompt = f"""A grower notices a plant problem and asks an online assistant about it.
Based ONLY on the disease description below, write {n} short, varied questions a grower might type.
Rules:
- Describe the symptoms, or ask what it is / how to treat or manage it.
- Do NOT name the disease or the pathogen anywhere.
- Vary the wording, length, and angle so the {n} questions are clearly different from each other.
- Make them sound like real, casual user questions.
- Output ONE question per line. No numbering, no extra text.

Disease description:
{rec['text']}

Questions:"""
    out = ollama.generate(model=MODEL, prompt=prompt)["response"]
    lines = [re.sub(r'^[\-\d\.\)\s]+', '', l).strip() for l in out.splitlines()]
    qs = [l for l in lines if len(l) > 10 and l.endswith(('?', '.')) or (len(l) > 15)]
    # de-dup, keep order
    seen, clean = set(), []
    for q in qs:
        k = q.lower()
        if k not in seen:
            seen.add(k); clean.append(q)
    return clean[:n]

pairs = []
for rec in corpus:
    qs = gen_queries(rec)
    for q in qs:
        pairs.append({"query": q, "disease_id": rec["id"]})
    print(f"  {rec['id']:34s} {len(qs)} queries")

json.dump(pairs, open(str(DATA / "train_queries.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\nTotal: {len(pairs)} training pairs -> train_queries.json")

print("\n--- random sample to INSPECT (do these look like real, varied, unnamed queries?) ---")
for p in random.sample(pairs, min(10, len(pairs))):
    print(f"  [{p['disease_id']:30s}] {p['query']}")

# quick leakage guard: warn if any disease NAME leaked into its own queries
print("\n--- leakage check (queries should NOT contain the disease/pathogen name) ---")
flags = 0
for rec in corpus:
    name_bits = re.findall(r"[A-Za-z]{5,}", rec["disease"] + " " + rec["pathogen"])
    for p in pairs:
        if p["disease_id"] == rec["id"]:
            if any(b.lower() in p["query"].lower() for b in name_bits):
                print(f"  WARN {rec['id']}: '{p['query']}'"); flags += 1
if not flags:
    print("  clean - no obvious disease-name leakage")