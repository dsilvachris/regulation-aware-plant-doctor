"""
phase2_step1_oracle.py — Phase 2, Step 1: establish the ROUTING CEILING from existing Phase-1 data.

No new LLM calls. Uses the Phase-1 blind grades (grading_sheet_BLIND.json + grading_key.json) to compute:
  - always-KG        : correctness/faithfulness if every question goes to the KG arm
  - always-RAG       : ... to the RAG arm
  - oracle (category): route each question to the PRE-REGISTERED optimal arm for its category (the honest ceiling)
  - oracle (question): route each question to whichever arm actually scored better on it (optimistic upper bound)

Hierarchy stubs (category 7, not instantiable) are excluded.
Run: python src/phase2_step1_oracle.py
"""
import json
from collections import defaultdict
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"

sheet = {it["item"]: it for it in json.load(open(DATA/"grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
key   = {k["item"]: k for k in json.load(open(DATA/"grading_key.json", encoding="utf-8"))["key"]}

def val(x):
    s=str(x).strip(); return int(s) if s in ("0","1") else None

# PRE-REGISTERED optimal arm per category (from Phase2_Design.md). factual -> rag (tie, pick the simpler/cheaper).
CATEGORY_OPTIMAL = {
    "factual": "rag", "region_specific": "kg", "multi_hop": "kg", "constraint": "kg",
    "negative": "kg", "cross_border": "kg", "cross_disease": "kg",
}
EXCLUDE = {"hierarchy"}   # category 7 not instantiable

# gather per (item, arm) -> (correct, faithful), plus category
rows = {}
for item, it in sheet.items():
    mp = key.get(item)
    if not mp: continue
    cat = it.get("category")
    if cat in EXCLUDE: continue
    for slot in ("A","B"):
        arm = mp[slot]
        rows[(item, arm)] = {
            "category": cat,
            "correct": val(it.get(f"grade_{slot}_correct")),
            "faithful": val(it.get(f"grade_{slot}_faithful")),
        }

items = sorted({i for (i,_) in rows})
def get(item, arm, metric):
    r = rows.get((item, arm)); return r[metric] if r else None

def score(selector):
    """selector(item, category) -> 'kg'|'rag'. Returns (correct_rate, faithful_rate, n)."""
    corr, faith = [], []
    for item in items:
        cat = rows.get((item,"kg"), rows.get((item,"rag")))["category"]
        arm = selector(item, cat)
        c = get(item, arm, "correct"); f = get(item, arm, "faithful")
        if c is not None: corr.append(c)
        if f is not None: faith.append(f)
    return (sum(corr)/len(corr) if corr else 0, sum(faith)/len(faith) if faith else 0, len(corr))

always_kg  = score(lambda i,c: "kg")
always_rag = score(lambda i,c: "rag")
oracle_cat = score(lambda i,c: CATEGORY_OPTIMAL.get(c, "kg"))
def per_q(item, cat):
    # pick the arm with higher correctness on this item (tie -> the more faithful; tie -> kg)
    ck, cr = get(item,"kg","correct") or 0, get(item,"rag","correct") or 0
    if ck != cr: return "kg" if ck>cr else "rag"
    fk, fr = get(item,"kg","faithful") or 0, get(item,"rag","faithful") or 0
    return "kg" if fk>=fr else "rag"
oracle_q = score(per_q)

print(f"Questions (hierarchy excluded): {len(items)}\n")
print(f"{'condition':<22} {'correct':>9} {'faithful':>9}")
print("-"*42)
for name,(c,f,n) in [("always-KG",always_kg),("always-RAG",always_rag),
                     ("oracle (category)",oracle_cat),("oracle (per-question)",oracle_q)]:
    print(f"{name:<22} {c:>8.0%} {f:>9.0%}")

print("\nInterpretation:")
best_single = max(always_kg[0], always_rag[0])
gain = oracle_cat[0] - best_single
print(f"  Best single-arm correctness: {best_single:.0%}")
print(f"  Oracle (category) correctness: {oracle_cat[0]:.0%}  -> adaptivity ceiling gain: +{gain*100:.1f} pts")
print(f"  Oracle (per-question) is an optimistic bound (uses the grades to pick): {oracle_q[0]:.0%}")

json.dump({
    "n_questions": len(items),
    "always_kg": {"correct": always_kg[0], "faithful": always_kg[1]},
    "always_rag": {"correct": always_rag[0], "faithful": always_rag[1]},
    "oracle_category": {"correct": oracle_cat[0], "faithful": oracle_cat[1]},
    "oracle_perquestion": {"correct": oracle_q[0], "faithful": oracle_q[1]},
    "category_optimal": CATEGORY_OPTIMAL,
}, open(DATA/"oracle_results.json","w"), indent=2)
print("\nWrote data/oracle_results.json")