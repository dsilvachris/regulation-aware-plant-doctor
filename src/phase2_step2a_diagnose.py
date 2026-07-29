"""
phase2_step2a_diagnose.py — Phase 2 (pivot), Step 2a: is per-question arm-advantage SYSTEMATIC or NOISE?

The 70% per-question oracle is only a real target if the arm that wins a given question does so
CONSISTENTLY across runs. If the winning arm flips run-to-run, the 'advantage' is model noise and
cannot be routed. This script uses the 3-run Phase-1 data to classify each question.

Run: python src/phase2_step2a_diagnose.py
"""
import json
from collections import defaultdict
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"

sheet = {it["item"]: it for it in json.load(open(DATA/"grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
key   = {k["item"]: k for k in json.load(open(DATA/"grading_key.json", encoding="utf-8"))["key"]}

def val(x):
    s=str(x).strip(); return int(s) if s in ("0","1") else None
def base(item): return item.split("_",1)[1] if "_" in item else item   # run2_m01 -> m01
def run_of(item): return item.split("_",1)[0]

EXCLUDE = {"hierarchy"}

# for each (base question, run) record correctness of kg and rag
byq = defaultdict(dict)   # base_qid -> run -> {'kg':c,'rag':c,'category':cat}
for item, it in sheet.items():
    mp = key.get(item)
    if not mp: continue
    cat = it.get("category")
    if cat in EXCLUDE: continue
    q = base(item); r = run_of(item)
    rec = byq[q].setdefault(r, {"category": cat})
    for slot in ("A","B"):
        arm = mp[slot]
        rec[arm] = val(it.get(f"grade_{slot}_correct"))

# classify each question: does an arm CONSISTENTLY win, or does the winner flip across runs?
systematic_rag_wins = []   # RAG consistently >= KG and strictly > in at least one run
systematic_kg_wins  = []
flips = []                 # winner changes across runs (noise)
ties = []                  # arms equal every run

for q, runs in byq.items():
    cat = next(iter(runs.values()))["category"]
    kg_scores = [runs[r].get("kg") for r in runs if runs[r].get("kg") is not None]
    rag_scores= [runs[r].get("rag") for r in runs if runs[r].get("rag") is not None]
    if not kg_scores or not rag_scores: continue
    # per-run winner: +1 kg, -1 rag, 0 tie
    winners = []
    for r in runs:
        kg, rag = runs[r].get("kg"), runs[r].get("rag")
        if kg is None or rag is None: continue
        winners.append(0 if kg==rag else (1 if kg>rag else -1))
    kg_ever = any(w==1 for w in winners); rag_ever = any(w==-1 for w in winners)
    if kg_ever and rag_ever:
        flips.append((q, cat, winners))
    elif rag_ever:
        systematic_rag_wins.append((q, cat, winners))
    elif kg_ever:
        systematic_kg_wins.append((q, cat, winners))
    else:
        ties.append((q, cat))

print(f"Distinct questions analysed: {len(byq)}\n")
print(f"Systematic KG-wins:  {len(systematic_kg_wins)}")
print(f"Systematic RAG-wins: {len(systematic_rag_wins)}  <- these are the routable RAG opportunities")
print(f"Flips (noise):       {len(flips)}  <- winner changes across runs = NOT routable")
print(f"Ties every run:      {len(ties)}\n")

print("--- Systematic RAG-wins (question, category, per-run winners [1=kg,-1=rag,0=tie]) ---")
for q,cat,w in systematic_rag_wins:
    print(f"  {q:8} {cat:16} {w}")
print("\n--- Flips / noise (these inflate the per-question oracle but can't be routed) ---")
for q,cat,w in flips[:20]:
    print(f"  {q:8} {cat:16} {w}")

# the key number: how much of the per-question oracle's gain is systematic vs noise?
print(f"\nKEY: of the questions where RAG ever beats KG, {len(systematic_rag_wins)} are systematic "
      f"and {len(flips)} flip. If flips dominate, the 70% ceiling is largely noise and per-question "
      f"routing has little REAL headroom over always-KG.")