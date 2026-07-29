"""
correction_regenerate_kg_answers.py — Remediation for the kg_verbalise.py disease-name bug found via
Phase 3's Step 1 conflict diagnostic (see docs/Correction_KG_Disease_Name_Bug.md).

Scope: exactly the 12 apple-scab/powdery-mildew extension questions whose KG facts_text incorrectly said
"late blight" regardless of actual disease, at the SAME run count as the original grading data (run1,
run2 — these questions were only graded for 2 runs in grading_sheet_BLIND.json, not the full 3).

RAG's answers for these 12 questions are NOT regenerated — the bug was entirely in kg_verbalise.py's
KG-facts phrasing; RAG never touches that code and its existing graded answers remain valid. This script
only regenerates the KG side and re-uses RAG's existing graded answer for each (run, question), to avoid
unnecessary Ollama calls and unnecessary re-grading of unaffected answers.

Output: a NEW, separate blind grading sheet (grading_sheet_BLIND_correction.json + a key file) covering
just these 24 items (12 questions x 2 runs), same schema and same blind-grading convention as
stage6_eval.py's make_gradesheet() (fresh random seed, independent of the original sheet's shuffle).
Grade this the same way as the original: fill grade_*_correct / grade_*_faithful WITHOUT opening the key.

After grading, run correction_merge_and_recompute.py to merge these corrected+graded items into a new
master grading sheet and recompute every downstream Phase 1/2 number against it.

Run: python src/correction_regenerate_kg_answers.py
"""
import json, random, sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep

AFFECTED_QIDS = ["as_m01", "as_m02", "as_c01", "as_c02", "as_n01", "as_d01", "as_d02",
                 "pm_n01", "pm_n02", "pm_d01", "pm_d02", "pm_d03"]
RUNS = ["run1", "run2"]  # matches the original grading data's coverage for these questions exactly

if __name__ == "__main__":
    sheet = json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]
    key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}
    sheet_by_item = {it["item"]: it for it in sheet}
    qtext = {qid: (q, cat) for qid, q, cat in ep.load_benchmark()}

    new_answers = {}  # (run, qid) -> {"question", "category", "kg", "rag"}
    for run in RUNS:
        for qid in AFFECTED_QIDS:
            item = f"{run}_{qid}"
            orig = sheet_by_item.get(item)
            mp = key.get(item)
            if orig is None or mp is None:
                print(f"  WARNING: {item} not found in original sheet/key — skipping")
                continue
            q, cat = qtext[qid]
            rag_slot = "A" if mp["A"] == "rag" else "B"
            rag_answer_unchanged = orig[f"System {rag_slot}"]  # reuse, do NOT regenerate

            print(f"  Regenerating KG answer for {item} ({q[:60]}...)")
            kg_answer_new, _ = ep.kg_answer_by_id(qid, q)

            new_answers[(run, qid)] = {
                "question": q, "category": cat, "kg": kg_answer_new, "rag": rag_answer_unchanged,
            }

    # Build the correction blind sheet, same convention as stage6_eval.py's make_gradesheet(),
    # but an independent seed so this shuffle has no relationship to the original sheet's.
    random.seed(4297)  # distinct from stage6_eval.py's seed=42, deliberately
    corr_sheet, corr_key = [], []
    for (run, qid), a in sorted(new_answers.items()):
        if random.random() < 0.5:
            A, B, mapping = a["kg"], a["rag"], {"A": "kg", "B": "rag"}
        else:
            A, B, mapping = a["rag"], a["kg"], {"A": "rag", "B": "kg"}
        item_id = f"{run}_{qid}"
        corr_sheet.append({"item": item_id, "category": a["category"], "question": a["question"],
                            "System A": A, "System B": B,
                            "grade_A_correct": "", "grade_B_correct": "",
                            "grade_A_faithful": "", "grade_B_faithful": "", "notes": ""})
        corr_key.append({"item": item_id, **mapping})

    json.dump({"_instructions": "CORRECTION BATCH (12 questions x 2 runs = 24 items). Only the KG side "
                                 "is new (RAG answers are reused from the original grading, unaffected by "
                                 "the bug). Fill grade_* fields: 1=correct/faithful, 0=not. Do NOT open "
                                 "the key file until grading is done. See "
                                 "docs/Correction_KG_Disease_Name_Bug.md for context.",
               "items": corr_sheet},
              open(DATA / "grading_sheet_BLIND_correction.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"key": corr_key},
              open(DATA / "grading_key_correction.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nWrote data/grading_sheet_BLIND_correction.json ({len(corr_sheet)} items) "
          f"and data/grading_key_correction.json")
    print("Grade the correction sheet the same way as the original (blind, System A vs B), then run "
          "src/correction_merge_and_recompute.py")