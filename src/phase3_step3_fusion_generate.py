"""
phase3_step3_fusion_generate.py — Phase 3, Step 3: generate fusion answers over the full benchmark,
multi-run from the start (per Phase3_Plan.md and the lesson already learned in Phase 2's step 3c — no
single-run LLM-involved result should be trusted).

Mirrors stage6_eval.py's structure exactly (run_n() + make_gradesheet()), but generates NAIVE and
STRUCTURED fusion answers instead of KG and RAG — and blinds them the SAME way: naive/structured shuffled
into System A/B per (run, question), one blind item per question per run, identical grading effort per
item to what Phase 1's original sheet already required. This is a deliberate design choice: it keeps the
human grading burden the same order of magnitude as Phase 1's, rather than doubling it by presenting each
variant as a separate item.

Two commands:
  python src/phase3_step3_fusion_generate.py --runs 3       -> generate, save data/phase3_fusion_runs.json
  python src/phase3_step3_fusion_generate.py --gradesheet    -> from that file, emit a BLIND grading sheet
                                                                 (System A/B anonymised + shuffled) + key

Ground truth for grading: every benchmark question already carries a pre-registered "answer" field
(data/benchmark_cat1_2.json, benchmark_cat3_7.json, benchmark_multidisease.json) — same reference used for
the correction batch grading. Do not open phase3_grading_key.json until grading is complete.

Run: python src/phase3_step3_fusion_generate.py --runs 3
     python src/phase3_step3_fusion_generate.py --gradesheet
"""
import json, sys, random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
import fusion_arm as fa

EXCLUDE = {"hierarchy"}


def run_n(n):
    items = [it for it in ep.load_benchmark() if it[2] not in EXCLUDE]
    runs = []
    for run_i in range(n):
        print(f"--- run {run_i + 1}/{n} ({len(items)} questions x 2 variants = "
              f"{len(items) * 2} LLM calls) ---")
        answers = {}
        for qid, q, cat in items:
            try:
                naive_a, _, _ = fa.fusion_answer(qid, q, "naive")
            except Exception as e:
                naive_a = f"[error: {e}]"
            try:
                structured_a, _, _ = fa.fusion_answer(qid, q, "structured")
            except Exception as e:
                structured_a = f"[error: {e}]"
            answers[qid] = {"question": q, "category": cat, "naive": naive_a, "structured": structured_a}
            print(f"  {qid} done")
        runs.append(answers)
    json.dump({"n_runs": n, "runs": runs},
              open(DATA / "phase3_fusion_runs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nWrote data/phase3_fusion_runs.json ({n} runs)")


def make_gradesheet():
    data = json.load(open(DATA / "phase3_fusion_runs.json", encoding="utf-8"))
    runs = data["runs"]
    random.seed(917)  # distinct from stage6_eval.py's 42 and the correction batch's 4297
    sheet, key = [], []
    for run_i, answers in enumerate(runs):
        for qid, a in answers.items():
            if random.random() < 0.5:
                A, B, mapping = a["naive"], a["structured"], {"A": "naive", "B": "structured"}
            else:
                A, B, mapping = a["structured"], a["naive"], {"A": "structured", "B": "naive"}
            item_id = f"run{run_i + 1}_{qid}"
            sheet.append({"item": item_id, "category": a["category"], "question": a["question"],
                          "System A": A, "System B": B,
                          "grade_A_correct": "", "grade_B_correct": "",
                          "grade_A_faithful": "", "grade_B_faithful": "", "notes": ""})
            key.append({"item": item_id, **mapping})
    json.dump({"_instructions": "Fill grade_* fields: 1=correct/faithful, 0=not, against each question's "
                                 "pre-registered 'answer' field in the benchmark files "
                                 "(data/benchmark_cat1_2.json, benchmark_cat3_7.json, "
                                 "benchmark_multidisease.json). Do NOT look at the key file until all "
                                 "grading is done. See docs/Phase3_Step2_FusionArm.md for context on the "
                                 "two variants being compared (naive vs structured fusion, not KG vs RAG).",
               "items": sheet},
              open(DATA / "phase3_grading_sheet_BLIND.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"key": key}, open(DATA / "phase3_grading_key.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Wrote data/phase3_grading_sheet_BLIND.json ({len(sheet)} items) and data/phase3_grading_key.json")
    print("Grade the BLIND sheet WITHOUT opening the key. Then run the Step 4 scoring (once written).")


if __name__ == "__main__":
    if "--gradesheet" in sys.argv:
        make_gradesheet()
    else:
        n = 3
        if "--runs" in sys.argv:
            n = int(sys.argv[sys.argv.index("--runs") + 1])
        run_n(n)