"""
phase4_step5_generate.py — Phase 4, Step 5: multiple runs + blind grading sheet.

Mirrors stage6_eval.py exactly, adapted for the pharma domain (eval_pipeline_phase4.py, 14 questions,
both arms - no category exclusion needed here since Category 7/hierarchy IS instantiable in this domain,
unlike Phase 1 where it had to be excluded).

Two commands:
  python src/phase4_step5_generate.py --runs 3      -> run the full benchmark N times, save
                                                        data/phase4_comparison_runs.json
  python src/phase4_step5_generate.py --gradesheet  -> from that file, emit a BLIND grading sheet
                                                        (System A/B anonymised + shuffled) + key

Rationale (same as every prior phase): the 3B model varies run to run - report mean + spread, never a
single run. Blind grading: grader has a stake in the KG, so arm labels are anonymised until scoring.

Ground truth for grading: each question's pre-registered "answer" field in data/benchmark_phase4.json.
Do not open data/phase4_grading_key.json until grading is complete.
"""
import json, sys, random
from pathlib import Path
import eval_pipeline_phase4 as ep

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def run_n(n):
    items = ep.load_benchmark()
    runs = []
    for run_i in range(n):
        print(f"--- run {run_i + 1}/{n} ({len(items)} questions x 2 arms = {len(items) * 2} LLM calls) ---")
        answers = {}
        for qid, q, cat in items:
            try:
                kg_a, _ = ep.kg_answer_by_id(qid, q)
            except Exception as e:
                kg_a = f"[error: {e}]"
            try:
                rag_a, _ = ep.rag_answer(q)
            except Exception as e:
                rag_a = f"[error: {e}]"
            answers[qid] = {"question": q, "category": cat, "kg": kg_a, "rag": rag_a}
            print(f"  {qid} done")
        runs.append(answers)
    json.dump({"n_runs": n, "runs": runs},
              open(DATA / "phase4_comparison_runs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nWrote data/phase4_comparison_runs.json ({n} runs)")


def make_gradesheet():
    data = json.load(open(DATA / "phase4_comparison_runs.json", encoding="utf-8"))
    runs = data["runs"]
    random.seed(2726)  # distinct from every other seed used in this project (42, 4297, 917, 2024)
    sheet, key = [], []
    for run_i, answers in enumerate(runs):
        for qid, a in answers.items():
            if random.random() < 0.5:
                A, B, mapping = a["kg"], a["rag"], {"A": "kg", "B": "rag"}
            else:
                A, B, mapping = a["rag"], a["kg"], {"A": "rag", "B": "kg"}
            item_id = f"run{run_i + 1}_{qid}"
            sheet.append({"item": item_id, "category": a["category"], "question": a["question"],
                          "System A": A, "System B": B,
                          "grade_A_correct": "", "grade_B_correct": "",
                          "grade_A_faithful": "", "grade_B_faithful": "", "notes": ""})
            key.append({"item": item_id, **mapping})
    json.dump({"_instructions": "Fill grade_* fields: 1=correct/faithful, 0=not, against each question's "
                                 "pre-registered 'answer' field in data/benchmark_phase4.json. Do NOT open "
                                 "phase4_grading_key.json until all grading is done.",
               "items": sheet},
              open(DATA / "phase4_grading_sheet_BLIND.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"key": key}, open(DATA / "phase4_grading_key.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Wrote data/phase4_grading_sheet_BLIND.json ({len(sheet)} items) and data/phase4_grading_key.json")
    print("Grade the BLIND sheet WITHOUT opening the key. Then run scoring to un-blind.")


if __name__ == "__main__":
    if "--gradesheet" in sys.argv:
        make_gradesheet()
    else:
        n = 3
        if "--runs" in sys.argv:
            n = int(sys.argv[sys.argv.index("--runs") + 1])
        run_n(n)