"""
score_results.py — Stage 6 scoring: un-blind the graded sheet and compute KG-vs-RAG results.

Inputs (in data/):
  grading_sheet_BLIND.json  — with grade_A_correct/grade_B_correct/grade_A_faithful/grade_B_faithful filled (1/0)
  grading_key.json          — the A/B -> kg/rag mapping per item

Outputs: prints a results table (per-category correct & faithful rates for KG vs RAG,
with mean and spread across runs) and writes data/results_summary.json.

Run:  python src/score_results.py
"""
import json, statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

sheet = json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]
key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}

def g(v):
    """Parse a grade cell to 1/0; blank or non-numeric -> None (ungraded)."""
    s = str(v).strip()
    return int(s) if s in ("0", "1") else None

# collect per (arm, category, metric) the list of 1/0, and track run for spread
# item id looks like 'run1_f01' -> run='run1', qid='f01'
records = []   # (run, category, arm, correct, faithful)
ungraded = 0
for it in sheet:
    item = it["item"]
    run = item.split("_")[0]
    cat = it["category"]
    mp = key.get(item)
    if not mp:
        continue
    for slot in ("A", "B"):
        arm = mp[slot]                      # 'kg' or 'rag'
        corr = g(it.get(f"grade_{slot}_correct"))
        faith = g(it.get(f"grade_{slot}_faithful"))
        if corr is None and faith is None:
            ungraded += 1
            continue
        records.append((run, cat, arm, corr, faith))

if ungraded:
    print(f"WARNING: {ungraded} answer-slots have no grades yet — results are partial.\n")

def rate(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None

# overall per arm
for metric_i, metric in enumerate(["correct", "faithful"]):
    print(f"===== {metric.upper()} =====")
    # per category
    cats = sorted(set(r[1] for r in records))
    header = f"{'category':<16} {'KG':>8} {'RAG':>8}"
    print(header); print("-"*len(header))
    for cat in cats:
        kg = rate([r[3 if metric=='correct' else 4] for r in records if r[1]==cat and r[2]=='kg'])
        rg = rate([r[3 if metric=='correct' else 4] for r in records if r[1]==cat and r[2]=='rag'])
        kg_s = f"{kg:.0%}" if kg is not None else "-"
        rg_s = f"{rg:.0%}" if rg is not None else "-"
        print(f"{cat:<16} {kg_s:>8} {rg_s:>8}")
    # overall
    kg_all = rate([r[3 if metric=='correct' else 4] for r in records if r[2]=='kg'])
    rg_all = rate([r[3 if metric=='correct' else 4] for r in records if r[2]=='rag'])
    print("-"*len(header))
    print(f"{'OVERALL':<16} {kg_all:.0%} {rg_all:>7.0%}\n" if kg_all is not None and rg_all is not None else "")

# spread across runs (overall correct rate per run per arm)
print("===== SPREAD ACROSS RUNS (overall correct rate) =====")
runs = sorted(set(r[0] for r in records))
for arm in ("kg", "rag"):
    per_run = []
    for run in runs:
        rr = rate([r[3] for r in records if r[0]==run and r[2]==arm])
        if rr is not None: per_run.append(rr)
    if per_run:
        mean = statistics.mean(per_run)
        spread = f"{min(per_run):.0%}–{max(per_run):.0%}"
        print(f"  {arm.upper():<4} mean {mean:.0%}  range {spread}  (per-run: {[f'{x:.0%}' for x in per_run]})")

# save machine-readable summary
summary = {"per_record_count": len(records), "ungraded_slots": ungraded,
           "note": "correct/faithful rates per arm per category; see console for table"}
json.dump(summary, open(DATA / "results_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\nWrote data/results_summary.json")