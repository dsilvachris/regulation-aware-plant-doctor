"""
phase3_step4_fusion_scoring.py — Phase 3, Step 4: does fusion beat the best single-arm baseline
(Phase 2's deterministic router) and close any of the gap to the oracle-per-question ceiling?

Self-contained: scores directly from data/phase3_grading_sheet_BLIND.json + data/phase3_grading_key.json.
Deliberately does NOT re-derive anything from data/phase3_fusion_runs.json, since 16 of the 153 graded
items have a known reproducibility gap against that raw file (see docs/Phase3_Step3_FusionGeneration.md) —
the grading sheet itself is the authoritative, self-contained record of what was graded.

Baselines it compares against are the CORRECTED Phase 2 numbers (post disease-name-bug fix, see
docs/Phase2_Results.md's addendum): always-KG 62%, always-RAG 40%, oracle(category)/deterministic router
64%/94%, oracle(per-question) 74%/97%. These are hardcoded here (not re-read from a Phase 2 output file)
since Phase 2's scoring already lives in its own committed docs and this script's job is the NEW Phase 3
numbers, not to re-run Phase 2.

Reports: overall correctness/faithfulness for naive and structured (mean + per-run range across the 3
runs, same discipline as Phase 2's step 3c multi-run check — a single-run number is not trusted anywhere
in this project); per-category breakdown with risky categories flagged; and how much of the 64%->74% gap
(if any) each variant closes.

Run: python src/phase3_step4_fusion_scoring.py
"""
import json, statistics
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
RISKY_CATS = {"negative", "cross_border", "cross_disease"}

# Corrected Phase 2 baselines (post disease-name-bug fix) — see docs/Phase2_Results.md addendum.
PHASE2_BASELINES = {
    "always_kg": 0.620, "always_rag": 0.395,
    "oracle_category_/_deterministic_router": 0.640,
    "oracle_per_question": 0.740,
}


def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None


if __name__ == "__main__":
    sheet = json.load(open(DATA / "phase3_grading_sheet_BLIND.json", encoding="utf-8"))["items"]
    key = {k["item"]: k for k in json.load(open(DATA / "phase3_grading_key.json", encoding="utf-8"))["key"]}

    # rows[(item, variant)] = {"correct":, "faithful":, "category":}
    rows = {}
    for it in sheet:
        item = it["item"]
        mp = key.get(item)
        if not mp:
            continue
        for slot in ("A", "B"):
            variant = mp[slot]
            rows[(item, variant)] = {
                "correct": val(it.get(f"grade_{slot}_correct")),
                "faithful": val(it.get(f"grade_{slot}_faithful")),
                "category": it.get("category"),
            }

    run_items = sorted({i for (i, _) in rows})
    n_runs = len({i.split("_", 1)[0] for i in run_items})

    def score(variant, run_filter=None):
        c, f = [], []
        per_cat = {}
        for item in run_items:
            if run_filter and not item.startswith(run_filter + "_"):
                continue
            r = rows.get((item, variant))
            if not r:
                continue
            if r["correct"] is not None:
                c.append(r["correct"])
                per_cat.setdefault(r["category"], []).append(r["correct"])
            if r["faithful"] is not None:
                f.append(r["faithful"])
        return {
            "correct": sum(c) / len(c) if c else 0,
            "faithful": sum(f) / len(f) if f else 0,
            "n": len(c),
            "per_category": {k: sum(v) / len(v) for k, v in per_cat.items()},
        }

    print("=" * 78)
    print(f"{'condition':<24}{'correct':>10}{'faithful':>10}{'n':>6}")
    print("-" * 78)
    for name, val_ in PHASE2_BASELINES.items():
        print(f"{name:<24}{val_:>9.0%} {'':>10}{'':>6}   (Phase 2, corrected)")

    overall = {}
    per_run = {}
    for variant in ("naive", "structured"):
        overall[variant] = score(variant)
        per_run[variant] = [score(variant, run_filter=f"run{i+1}") for i in range(n_runs)]
        corrs = [r["correct"] for r in per_run[variant]]
        c_mean, c_lo, c_hi = statistics.mean(corrs), min(corrs), max(corrs)
        o = overall[variant]
        print(f"{variant:<24}{o['correct']:>9.0%} {o['faithful']:>9.0%} {o['n']:>6}   "
              f"(range {c_lo:.0%}-{c_hi:.0%} across {n_runs} runs)")

    print("\n" + "=" * 78)
    print("Per-category correctness (risky categories marked *)")
    print("-" * 78)
    all_cats = sorted(set(c for v in overall.values() for c in v["per_category"]))
    print(f"{'category':<18}{'naive':>10}{'structured':>12}")
    for cat in all_cats:
        n_c = overall["naive"]["per_category"].get(cat, 0)
        s_c = overall["structured"]["per_category"].get(cat, 0)
        tag = " *RISKY*" if cat in RISKY_CATS else ""
        print(f"{cat:<18}{n_c:>10.0%}{s_c:>12.0%}{tag}")

    print("\n" + "=" * 78)
    print("Gap closure vs Phase 2 baselines")
    print("-" * 78)
    det = PHASE2_BASELINES["oracle_category_/_deterministic_router"]
    oracle_pq = PHASE2_BASELINES["oracle_per_question"]
    gap = oracle_pq - det
    for variant in ("naive", "structured"):
        c = overall[variant]["correct"]
        closed = (c - det) / gap if gap else 0
        beats_det = "beats" if c > det else ("ties" if abs(c - det) < 0.005 else "below")
        print(f"{variant:<12} correctness {c:.1%} vs deterministic-router {det:.1%}: {beats_det}. "
              f"Fraction of the {det:.0%}->{oracle_pq:.0%} gap closed: {closed:+.1%}")

    out = {
        "phase2_baselines": PHASE2_BASELINES,
        "overall": overall,
        "per_run": per_run,
        "n_runs": n_runs,
    }
    json.dump(out, open(DATA / "phase3_step4_results.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase3_step4_results.json")