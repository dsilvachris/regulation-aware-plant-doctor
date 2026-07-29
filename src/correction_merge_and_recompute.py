"""
correction_merge_and_recompute.py — after grading data/grading_sheet_BLIND_correction.json, merge the
12 corrected questions (24 items) into a NEW master grading sheet (the original 105 items are untouched)
and recompute every number that depends on it: Phase 1's headline always-KG/always-RAG, and Phase 2's
oracle/deterministic-router/LLM-router cost-of-misrouting tables.

Produces grading_sheet_BLIND_corrected.json (105 original + 24 corrected = 129 items, same as before) —
a new file, NOT an overwrite of the original grading_sheet_BLIND.json, so the pre-correction data remains
on record for the audit trail.

Run: python src/correction_merge_and_recompute.py
"""
import json, statistics
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None


if __name__ == "__main__":
    orig_sheet = json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]
    orig_key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}
    corr_sheet = json.load(open(DATA / "grading_sheet_BLIND_correction.json", encoding="utf-8"))["items"]
    corr_key = {k["item"]: k for k in json.load(open(DATA / "grading_key_correction.json", encoding="utf-8"))["key"]}

    # sanity: correction items must actually be graded before merging
    ungraded = [it["item"] for it in corr_sheet
                if val(it.get("grade_A_correct")) is None or val(it.get("grade_B_correct")) is None]
    if ungraded:
        print(f"STOP: {len(ungraded)} correction items are not yet graded: {ungraded}")
        print("Grade data/grading_sheet_BLIND_correction.json completely before running this script.")
        raise SystemExit(1)

    corr_items = {it["item"] for it in corr_sheet}
    merged_sheet = [it for it in orig_sheet if it["item"] not in corr_items] + corr_sheet
    merged_key_map = dict(orig_key)
    merged_key_map.update(corr_key)
    merged_key = list(merged_key_map.values())

    json.dump({"_instructions": "Merged master sheet: original grading + the 12-question disease-name-bug "
                                 "correction (see docs/Correction_KG_Disease_Name_Bug.md).",
               "items": merged_sheet},
              open(DATA / "grading_sheet_BLIND_corrected.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"key": merged_key},
              open(DATA / "grading_key_corrected.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Wrote merged grading_sheet_BLIND_corrected.json ({len(merged_sheet)} items) "
          f"and grading_key_corrected.json\n")

    # --- Recompute always-KG / always-RAG on OLD vs NEW sheets for a direct before/after comparison ---
    def score(sheet, keymap):
        rows = {}
        for it in sheet:
            item = it["item"]
            mp = keymap.get(item)
            if not mp:
                continue
            for slot in ("A", "B"):
                arm = mp[slot]
                rows[(item, arm)] = {"correct": val(it.get(f"grade_{slot}_correct")),
                                      "faithful": val(it.get(f"grade_{slot}_faithful")),
                                      "category": it.get("category")}
        out = {}
        for arm in ("kg", "rag"):
            c = [v["correct"] for (i, a), v in rows.items() if a == arm and v["correct"] is not None]
            f = [v["faithful"] for (i, a), v in rows.items() if a == arm and v["faithful"] is not None]
            out[arm] = {"correct": sum(c) / len(c) if c else 0, "faithful": sum(f) / len(f) if f else 0,
                        "n": len(c)}
        # also just on the 12-question correction subset, old vs new
        affected_qids = {"as_m01", "as_m02", "as_c01", "as_c02", "as_n01", "as_d01", "as_d02",
                          "pm_n01", "pm_n02", "pm_d01", "pm_d02", "pm_d03"}
        for arm in ("kg", "rag"):
            c = [v["correct"] for (i, a), v in rows.items()
                 if a == arm and v["correct"] is not None and i.split("_", 1)[1] in affected_qids]
            out[f"{arm}_on_affected_subset"] = {"correct": sum(c) / len(c) if c else 0, "n": len(c)}
        return out

    print("=" * 70)
    print("BEFORE (original grading_sheet_BLIND.json):")
    before = score(orig_sheet, orig_key)
    for k, v in before.items():
        print(f"  {k:24} {v}")

    print("\nAFTER (corrected grading_sheet_BLIND_corrected.json):")
    after = score(merged_sheet, merged_key_map)
    for k, v in after.items():
        print(f"  {k:24} {v}")

    json.dump({"before": before, "after": after},
              open(DATA / "correction_before_after.json", "w"), indent=2)
    print("\nWrote data/correction_before_after.json")

    # --- Re-derive Phase 2's numbers against the corrected sheet, WITHOUT modifying the existing
    # Phase 2 scripts (they hardcode "grading_sheet_BLIND.json"/"grading_key.json" by filename): back up
    # the originals, swap the corrected files into place, run each script, rename its output with a
    # "_corrected" suffix, then restore the originals. Originals are never left overwritten.
    import shutil, subprocess, sys as _sys

    print("\n" + "=" * 70)
    print("Re-deriving Phase 2 numbers against the corrected sheet...")
    orig_sheet_path = DATA / "grading_sheet_BLIND.json"
    orig_key_path = DATA / "grading_key.json"
    backup_sheet = DATA / "grading_sheet_BLIND.json.bak"
    backup_key = DATA / "grading_key.json.bak"

    shutil.copy(orig_sheet_path, backup_sheet)
    shutil.copy(orig_key_path, backup_key)
    try:
        shutil.copy(DATA / "grading_sheet_BLIND_corrected.json", orig_sheet_path)
        shutil.copy(DATA / "grading_key_corrected.json", orig_key_path)

        for script, out_file in [
            ("phase2_step1_oracle.py", "oracle_results.json"),
            ("phase2_step2b_deterministic_router.py", "phase2_deterministic_router.json"),
            ("phase2_step4_cost_of_misrouting.py", "phase2_step4_results.json"),
        ]:
            print(f"\n--- running {script} against corrected data ---")
            subprocess.run([_sys.executable, str(Path(__file__).resolve().parent / script)], check=True)
            out_path = DATA / out_file
            corrected_out_path = DATA / out_file.replace(".json", "_corrected.json")
            if out_path.exists():
                shutil.copy(out_path, corrected_out_path)
                print(f"    saved -> {corrected_out_path.name}")
    finally:
        shutil.copy(backup_sheet, orig_sheet_path)
        shutil.copy(backup_key, orig_key_path)
        backup_sheet.unlink()
        backup_key.unlink()
        print("\nOriginal grading_sheet_BLIND.json / grading_key.json restored (never overwritten).")

    print("\nDone. Compare data/oracle_results.json vs oracle_results_corrected.json (and the "
          "deterministic-router / step4 pairs) for the before/after Phase 2 numbers.")