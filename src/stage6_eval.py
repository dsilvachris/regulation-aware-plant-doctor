"""
stage6_eval.py — Stage 6: multiple runs + blind grading sheet.

Two commands:
  python src/stage6_eval.py --runs 3      -> run the full benchmark N times, save comparison_runs.json
  python src/stage6_eval.py --gradesheet  -> from comparison_runs.json, emit a BLIND grading sheet
                                             (System A/B anonymised + shuffled per question) + a key file

Rationale:
  - Multiple runs: the 3B varies; report mean + spread, not a single run (per methodology).
  - Blind grading: grader has a stake in the KG; anonymise arm labels so scoring can't favour it.
"""
import json, sys, random
from pathlib import Path
import eval_pipeline as ep

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def run_n(n):
    items = ep.load_benchmark()
    runs = []
    for run_i in range(n):
        print(f"--- run {run_i+1}/{n} ---")
        answers = {}
        for qid, q, cat in items:
            if cat == "hierarchy":
                continue
            try:
                kg_a, _ = ep.kg_answer_by_id(qid, q)
            except Exception as e:
                kg_a = f"[error: {e}]"
            rag_a, _ = ep.rag_answer(q)
            answers[qid] = {"question": q, "category": cat, "kg": kg_a, "rag": rag_a}
            print(f"  {qid} done")
        runs.append(answers)
    json.dump({"n_runs": n, "runs": runs},
              open(DATA / "comparison_runs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nWrote data/comparison_runs.json ({n} runs)")

def make_gradesheet():
    data = json.load(open(DATA / "comparison_runs.json", encoding="utf-8"))
    runs = data["runs"]
    random.seed(42)
    sheet, key = [], []
    for run_i, answers in enumerate(runs):
        for qid, a in answers.items():
            # randomly assign which arm is A vs B, per question per run
            if random.random() < 0.5:
                A, B, mapping = a["kg"], a["rag"], {"A": "kg", "B": "rag"}
            else:
                A, B, mapping = a["rag"], a["kg"], {"A": "rag", "B": "kg"}
            item_id = f"run{run_i+1}_{qid}"
            sheet.append({"item": item_id, "category": a["category"], "question": a["question"],
                          "System A": A, "System B": B,
                          "grade_A_correct": "", "grade_B_correct": "",
                          "grade_A_faithful": "", "grade_B_faithful": "", "notes": ""})
            key.append({"item": item_id, **mapping})
    json.dump({"_instructions": "Fill grade_* fields: 1=correct/faithful, 0=not, per the ground truth. "
                                 "Do NOT look at the key file until all grading is done.",
               "items": sheet},
              open(DATA / "grading_sheet_BLIND.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"key": key}, open(DATA / "grading_key.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Wrote data/grading_sheet_BLIND.json ({len(sheet)} items) and data/grading_key.json")
    print("Grade the BLIND sheet WITHOUT opening the key. Then run scoring to un-blind.")

if __name__ == "__main__":
    if "--gradesheet" in sys.argv:
        make_gradesheet()
    else:
        n = 3
        if "--runs" in sys.argv:
            n = int(sys.argv[sys.argv.index("--runs")+1])
        run_n(n)