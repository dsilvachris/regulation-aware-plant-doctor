"""
interrater_agreement.py — compute inter-rater agreement between two blind graders.

Inputs (in data/): grading_sheet_BLIND.json (grader 1 = you), grading_sheet_BLIND_2.json (grader 2).
Matches items by 'item' id; compares only items BOTH graded. Reports:
  - percent agreement per metric (correct, faithful) for each system slot
  - Cohen's kappa (chance-corrected agreement)
  - disagreement list (so you can inspect where graders differ)

Run:  python src/interrater_agreement.py
"""
import json
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"

def load(fn):
    d = json.load(open(DATA / fn, encoding="utf-8"))
    items = d.get("items", d if isinstance(d, list) else [])
    return {it["item"]: it for it in items}

g1 = load("grading_sheet_BLIND.json")     # you
g2 = load("grading_sheet_BLIND_2.json")   # second grader

def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None

FIELDS = ["grade_A_correct", "grade_B_correct", "grade_A_faithful", "grade_B_faithful"]

both = [i for i in g1 if i in g2]
print(f"Items graded by both: {len(both)}\n")

def kappa(pairs):
    # Cohen's kappa for binary labels
    n = len(pairs)
    if n == 0: return None
    po = sum(1 for a, b in pairs if a == b) / n
    # marginals
    a1 = sum(a for a, b in pairs) / n; a0 = 1 - a1
    b1 = sum(b for a, b in pairs) / n; b0 = 1 - b1
    pe = a1 * b1 + a0 * b0
    return (po - pe) / (1 - pe) if pe != 1 else 1.0, po

# overall per-metric agreement (pooling A and B slots into correctness / faithfulness)
for metric, flds in [("CORRECT", ["grade_A_correct", "grade_B_correct"]),
                     ("FAITHFUL", ["grade_A_faithful", "grade_B_faithful"])]:
    pairs = []
    for i in both:
        for f in flds:
            a, b = val(g1[i].get(f)), val(g2[i].get(f))
            if a is not None and b is not None:
                pairs.append((a, b))
    if pairs:
        k, po = kappa(pairs)
        print(f"{metric}: {len(pairs)} judgements | agreement {po:.1%} | Cohen's kappa {k:.2f}")

# disagreements to inspect
print("\n--- Disagreements (first 25) ---")
shown = 0
for i in both:
    for f in FIELDS:
        a, b = val(g1[i].get(f)), val(g2[i].get(f))
        if a is not None and b is not None and a != b:
            print(f"  {i} {f}: you={a} grader2={b}")
            shown += 1
            if shown >= 25: break
    if shown >= 25: break

def interpret(k):
    if k is None: return ""
    if k < 0.2: return "slight"
    if k < 0.4: return "fair"
    if k < 0.6: return "moderate"
    if k < 0.8: return "substantial"
    return "almost perfect"
print("\n(kappa guide: <0.2 slight, 0.2-0.4 fair, 0.4-0.6 moderate, 0.6-0.8 substantial, >0.8 almost perfect)")