"""
phase3_step4b_second_grading_sample.py — build a stratified sample for an independent second-grading pass,
before trusting Step 4's headline number (structured fusion nominally beating the oracle-per-question
ceiling, 76.5% vs 74%).

Unlike Phase 2 (where Step 5 was legitimately skipped — routing only ever reused Phase-1's already-graded
answers), fusion generates genuinely NEW answers that only one person has ever graded, once, blind. That's
a real gap specifically for this phase's data, not a general requirement reapplied out of caution.

Sampling is stratified TOWARD the categories most worth doubting, not a flat random draw:
  - cross_disease: ALL items (n=6) — smallest category, most surprising reversal (structured < naive),
    any single flip swings the percentage by ~17 points.
  - negative, constraint: oversampled — both showed the largest swings in structured's favor and are
    plausible targets for grading-leniency drift on longer, more hedged structured answers.
  - factual: oversampled — the one category where structured did WORSE, and where the original grading
    notes already document a concrete mechanism (over-hedging), worth confirming an independent grader
    sees the same pattern.
  - cross_border, multi_hop, region_specific: lighter sampling — less surprising results, still worth a
    baseline check.

Produces:
  - data/phase3_second_grading_sample.json — the sample to grade, SAME System A/B text and slot
    assignment as the original (so grades are directly comparable), grade_* fields blanked.
  - data/phase3_original_grades_for_sample.json — the ORIGINAL grades for exactly these items, held out
    (not shown to whoever grades the sample) — used later to compute agreement.

Run: python src/phase3_step4b_second_grading_sample.py
"""
import json, random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Per-category target sample size (None = take all)
TARGETS = {
    "cross_disease": None,   # all 6
    "negative": 12,
    "constraint": 8,
    "factual": 10,
    "cross_border": 8,
    "multi_hop": 5,
    "region_specific": 5,
}

if __name__ == "__main__":
    sheet = json.load(open(DATA / "phase3_grading_sheet_BLIND.json", encoding="utf-8"))["items"]

    by_cat = {}
    for it in sheet:
        by_cat.setdefault(it["category"], []).append(it)

    random.seed(2024)  # independent of every other seed used in this project
    sample = []
    for cat, target in TARGETS.items():
        pool = by_cat.get(cat, [])
        if target is None or target >= len(pool):
            chosen = pool
        else:
            chosen = random.sample(pool, target)
        sample.extend(chosen)
        print(f"  {cat:<18} {len(chosen)}/{len(pool)} sampled")

    print(f"\nTotal sample: {len(sample)} / {len(sheet)} items ({len(sample)/len(sheet):.0%})")

    original_grades = {}
    blanked = []
    for it in sample:
        original_grades[it["item"]] = {
            "grade_A_correct": it["grade_A_correct"], "grade_B_correct": it["grade_B_correct"],
            "grade_A_faithful": it["grade_A_faithful"], "grade_B_faithful": it["grade_B_faithful"],
            "notes": it.get("notes", ""),
        }
        blanked.append({
            "item": it["item"], "category": it["category"], "question": it["question"],
            "System A": it["System A"], "System B": it["System B"],
            "grade_A_correct": "", "grade_B_correct": "",
            "grade_A_faithful": "", "grade_B_faithful": "", "notes": "",
        })

    json.dump({
        "_instructions": "Independent second-grading sample (stratified toward the categories most worth "
                          "double-checking — see script docstring for why). Grade exactly as before: "
                          "1=correct/faithful, 0=not, against each question's ground-truth 'answer' field "
                          "in the benchmark files. Ideally graded by someone who has NOT seen the original "
                          "grades for these items, or by the original grader after enough time has passed "
                          "to not recall specific answers. Do not consult the original grading sheet while "
                          "grading this one.",
        "items": blanked,
    }, open(DATA / "phase3_second_grading_sample.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    json.dump({"original_grades": original_grades},
              open(DATA / "phase3_original_grades_for_sample.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\nWrote data/phase3_second_grading_sample.json ({len(blanked)} items to grade)")
    print("Wrote data/phase3_original_grades_for_sample.json (held out — do not look at this while grading)")