"""
phase3_step4d_agreement.py — Phase 3: inter-rater agreement between the original grading and the
stratified second-grading sample (data/phase3_step4b_second_grading_sample.py), plus the decisive check:
does the qualitative finding (structured fusion beats naive) REPLICATE under the second, independent
grading pass on this same 54-item subsample?

Run: python src/phase3_step4d_agreement.py
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def cohens_kappa(pairs):
    """pairs: list of (rating1, rating2), each 0/1. Returns (kappa, po, pe, n)."""
    n = len(pairs)
    if n == 0:
        return None, None, None, 0
    po = sum(1 for a, b in pairs if a == b) / n
    p1_a = sum(1 for a, _ in pairs if a == 1) / n
    p1_b = sum(1 for _, b in pairs if b == 1) / n
    pe = p1_a * p1_b + (1 - p1_a) * (1 - p1_b)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return kappa, po, pe, n


if __name__ == "__main__":
    second = {it["item"]: it for it in json.load(open(DATA / "phase3_second_grading_sample.json", encoding="utf-8"))["items"]}
    original = json.load(open(DATA / "phase3_original_grades_for_sample.json", encoding="utf-8"))["original_grades"]
    key = {k["item"]: k for k in json.load(open(DATA / "phase3_grading_key.json", encoding="utf-8"))["key"]}

    items = sorted(second.keys())
    assert set(items) == set(original.keys()), "sample/original mismatch"

    # --- 1. Inter-rater agreement, overall and by dimension ---
    for dim in ("correct", "faithful"):
        pairs = []
        for item in items:
            for slot in ("A", "B"):
                o = original[item][f"grade_{slot}_{dim}"]
                s = second[item][f"grade_{slot}_{dim}"]
                pairs.append((o, s))
        kappa, po, pe, n = cohens_kappa(pairs)
        print(f"{dim:<10} agreement: {po:.1%} raw, kappa={kappa:.3f} (n={n})")

    # --- 2. Agreement by category ---
    print("\nAgreement by category (correct dimension):")
    by_cat = {}
    for item in items:
        cat = second[item]["category"]
        for slot in ("A", "B"):
            o = original[item][f"grade_{slot}_correct"]
            s = second[item][f"grade_{slot}_correct"]
            by_cat.setdefault(cat, []).append((o, s))
    for cat, pairs in sorted(by_cat.items()):
        kappa, po, pe, n = cohens_kappa(pairs)
        print(f"  {cat:<18} {po:.1%} raw, kappa={kappa:.3f} (n={n})")

    # --- 3. Agreement by variant (naive vs structured), via the key ---
    print("\nAgreement by variant (correct dimension):")
    by_variant = {"naive": [], "structured": []}
    for item in items:
        mp = key[item]
        for slot in ("A", "B"):
            variant = mp[slot]
            o = original[item][f"grade_{slot}_correct"]
            s = second[item][f"grade_{slot}_correct"]
            by_variant[variant].append((o, s))
    for variant, pairs in by_variant.items():
        kappa, po, pe, n = cohens_kappa(pairs)
        print(f"  {variant:<12} {po:.1%} raw, kappa={kappa:.3f} (n={n})")

    # --- 4. THE DECISIVE CHECK: does "structured > naive" replicate under the second grading? ---
    print("\n" + "=" * 60)
    print("Does structured beat naive on THIS 54-item subsample, under each grading pass?")
    for label, grades in [("original grading", original), ("second grading", second)]:
        variant_correct = {"naive": [], "structured": []}
        for item in items:
            mp = key[item]
            for slot in ("A", "B"):
                variant = mp[slot]
                variant_correct[variant].append(grades[item][f"grade_{slot}_correct"])
        n_c = sum(variant_correct["naive"]) / len(variant_correct["naive"])
        s_c = sum(variant_correct["structured"]) / len(variant_correct["structured"])
        print(f"  [{label}] naive: {n_c:.1%}  structured: {s_c:.1%}  "
              f"(structured {'beats' if s_c > n_c else 'does not beat'} naive)")

    out = {"items_compared": len(items)}
    json.dump(out, open(DATA / "phase3_agreement_results.json", "w"), indent=2)
    print("\nWrote data/phase3_agreement_results.json")