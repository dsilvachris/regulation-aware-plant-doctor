"""
phase4_step6_scoring.py — Phase 4, Step 6: core analysis.

Scores the graded data/phase4_grading_sheet_BLIND.json against data/phase4_grading_key.json: overall
always-KG / always-RAG correctness and faithfulness, per-category breakdown (the real test — does the
hierarchy-traversal pattern from the demo hold up under multi-run scrutiny?), and multi-run stability.

Self-contained: reads only local JSON, no Ollama/embeddings needed.

Run: python src/phase4_step6_scoring.py
"""
import json, statistics
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None


if __name__ == "__main__":
    sheet = json.load(open(DATA / "phase4_grading_sheet_BLIND.json", encoding="utf-8"))["items"]
    key = {k["item"]: k for k in json.load(open(DATA / "phase4_grading_key.json", encoding="utf-8"))["key"]}

    rows = {}  # (item, arm) -> {correct, faithful, category}
    for it in sheet:
        item = it["item"]
        mp = key.get(item)
        if not mp:
            continue
        for slot in ("A", "B"):
            arm = mp[slot]
            rows[(item, arm)] = {
                "correct": val(it.get(f"grade_{slot}_correct")),
                "faithful": val(it.get(f"grade_{slot}_faithful")),
                "category": it.get("category"),
            }

    run_items = sorted({i for (i, _) in rows})
    n_runs = len({i.split("_", 1)[0] for i in run_items})

    def score(arm, run_filter=None):
        c, f = [], []
        per_cat = {}
        for item in run_items:
            if run_filter and not item.startswith(run_filter + "_"):
                continue
            r = rows.get((item, arm))
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

    print("=" * 70)
    print(f"{'condition':<14}{'correct':>10}{'faithful':>10}{'n':>6}")
    print("-" * 70)
    overall = {}
    for arm in ("kg", "rag"):
        overall[arm] = score(arm)
        per_run = [score(arm, run_filter=f"run{i+1}") for i in range(n_runs)]
        corrs = [r["correct"] for r in per_run]
        c_mean, c_lo, c_hi = statistics.mean(corrs), min(corrs), max(corrs)
        o = overall[arm]
        print(f"{arm:<14}{o['correct']:>9.0%} {o['faithful']:>9.0%} {o['n']:>6}   "
              f"(range {c_lo:.0%}-{c_hi:.0%} across {n_runs} runs)")

    print("\n" + "=" * 70)
    print("Per-category correctness")
    print("-" * 70)
    all_cats = sorted(set(c for v in overall.values() for c in v["per_category"]))
    print(f"{'category':<18}{'kg':>10}{'rag':>10}")
    for cat in all_cats:
        kg_c = overall["kg"]["per_category"].get(cat, 0)
        rag_c = overall["rag"]["per_category"].get(cat, 0)
        tag = " <-- hierarchy" if cat == "hierarchy" else ""
        print(f"{cat:<18}{kg_c:>10.0%}{rag_c:>10.0%}{tag}")

    out = {"overall": overall, "n_runs": n_runs}
    json.dump(out, open(DATA / "phase4_step6_results.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase4_step6_results.json")