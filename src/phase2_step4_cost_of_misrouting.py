"""
phase2_step4_cost_of_misrouting.py — Phase 2, Step 4: end-to-end quality + cost-of-misrouting.

This is the step Phase2_Plan.md calls "the heart of the contribution." Everything computed in steps 1-3c
was a PROXY: did a router pick the arm the pre-registered category-oracle says is optimal? This step
replaces the proxy with the real thing: actual correctness/faithfulness of the answers the routed system
would have produced, using Phase-1's existing blind grades — because Phase 1 already generated and graded
BOTH arms' answers for every benchmark question, routing never needs a NEW answer or a NEW grade. It only
needs to select, per question, which of the two already-graded answers a given router would have chosen.
This is why Step 5 (new blind grading) is skipped: there is nothing new to grade.

Conditions scored, all using the identical scoring machinery so every number is directly comparable:
  - always-KG, always-RAG            (Phase-1 single-arm baselines, reproduced here for a self-contained
                                       report; source of truth is phase2_step1_oracle.py)
  - oracle (category)                the pre-registered ceiling — reproduced from phase2_step1_oracle.py
  - oracle (per-question)            optimistic upper bound (uses the grades to pick) — ditto
  - deterministic router             from data/phase2_deterministic_router.json (single, stable decision)
  - LLM router A / B / C             from data/phase2_router_multirun.json, EACH OF THE 5 RUNS SCORED
                                       SEPARATELY (mean + range), since step 3c established these routers
                                       are not self-consistent — a single aggregate number would hide that.

Cost-of-misrouting: for every condition, the per-question correctness gap vs oracle(category), broken down
by category, with the three risk-critical categories (negative, cross_border, cross_disease) reported
separately, per the pre-registered risk asymmetry in Phase2_Design.md.

Run: python src/phase2_step4_cost_of_misrouting.py
Requires data/phase2_deterministic_router.json and data/phase2_router_multirun.json to already exist
(from src/phase2_step2b_deterministic_router.py and src/phase2_step3c_router_multirun.py).
"""
import json, statistics
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
RISKY_CATS = {"negative", "cross_border", "cross_disease"}

# --- Load Phase-1 grades (same source as phase2_step1_oracle.py) ---
sheet = {it["item"]: it for it in json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}


def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None


EXCLUDE = {"hierarchy"}
rows = {}  # (item, arm) -> {category, correct, faithful}
for item, it in sheet.items():
    mp = key.get(item)
    if not mp:
        continue
    cat = it.get("category")
    if cat in EXCLUDE:
        continue
    for slot in ("A", "B"):
        arm = mp[slot]
        rows[(item, arm)] = {
            "category": cat,
            "correct": val(it.get(f"grade_{slot}_correct")),
            "faithful": val(it.get(f"grade_{slot}_faithful")),
        }

run_items = sorted({i for (i, _) in rows})  # e.g. "run1_f01", "run2_f01", ...
CATEGORY_OPTIMAL = {
    "factual": "rag", "region_specific": "kg", "multi_hop": "kg", "constraint": "kg",
    "negative": "kg", "cross_border": "kg", "cross_disease": "kg",
}


def get(item, arm, metric):
    r = rows.get((item, arm))
    return r[metric] if r else None


def base_qid(item):
    return item.split("_", 1)[1] if "_" in item else item


def category_of(item):
    r = rows.get((item, "kg")) or rows.get((item, "rag"))
    return r["category"] if r else None


def score_selector(selector):
    """selector(item, qid, category) -> 'kg'|'rag'. Returns dict with aggregate + per-category + per-item."""
    corr, faith = [], []
    per_cat_corr = {}
    per_item_correct = {}
    for item in run_items:
        cat = category_of(item)
        qid = base_qid(item)
        arm = selector(item, qid, cat)
        c = get(item, arm, "correct")
        f = get(item, arm, "faithful")
        if c is not None:
            corr.append(c)
            per_cat_corr.setdefault(cat, []).append(c)
            per_item_correct[item] = c
        if f is not None:
            faith.append(f)
    return {
        "correct": sum(corr) / len(corr) if corr else 0,
        "faithful": sum(faith) / len(faith) if faith else 0,
        "n": len(corr),
        "per_category_correct": {c: sum(v) / len(v) for c, v in per_cat_corr.items()},
        "per_item_correct": per_item_correct,
    }


def selector_fixed_arm(arm_name):
    return lambda item, qid, cat: arm_name


def selector_category_oracle(item, qid, cat):
    return CATEGORY_OPTIMAL.get(cat, "kg")


def selector_per_question_oracle(item, qid, cat):
    ck, cr = get(item, "kg", "correct") or 0, get(item, "rag", "correct") or 0
    if ck != cr:
        return "kg" if ck > cr else "rag"
    fk, fr = get(item, "kg", "faithful") or 0, get(item, "rag", "faithful") or 0
    return "kg" if fk >= fr else "rag"


def selector_from_decisions(decisions):
    """decisions: {qid: arm}. Applies the SAME fixed per-question decision across all Phase-1 runs for
    that question (consistent with how oracle_category / always-arm apply a fixed policy across runs)."""
    return lambda item, qid, cat: decisions.get(qid, "kg")


def cost_of_misrouting(condition_result, oracle_cat_result):
    """Per-category mean correctness gap: oracle(category) minus this condition, using items both cover."""
    oracle_items = oracle_cat_result["per_item_correct"]
    cond_items = condition_result["per_item_correct"]
    by_cat_gap = {}
    for item in oracle_items:
        if item not in cond_items:
            continue
        cat = category_of(item)
        gap = oracle_items[item] - cond_items[item]
        by_cat_gap.setdefault(cat, []).append(gap)
    return {cat: sum(g) / len(g) for cat, g in by_cat_gap.items()}


if __name__ == "__main__":
    results = {}
    results["always_kg"] = score_selector(selector_fixed_arm("kg"))
    results["always_rag"] = score_selector(selector_fixed_arm("rag"))
    results["oracle_category"] = score_selector(selector_category_oracle)
    results["oracle_per_question"] = score_selector(selector_per_question_oracle)

    # --- Deterministic router ---
    det_path = DATA / "phase2_deterministic_router.json"
    if det_path.exists():
        det = json.load(open(det_path, encoding="utf-8"))
        det_decisions = {qid: d["routed_to"] for qid, d in det["decisions"].items()}
        results["deterministic"] = score_selector(selector_from_decisions(det_decisions))
    else:
        print(f"WARNING: {det_path} not found, skipping deterministic router.")

    # --- LLM router variants, multi-run ---
    multirun_path = DATA / "phase2_router_multirun.json"
    llm_run_results = {}  # variant -> list of per-run score dicts
    if multirun_path.exists():
        mr = json.load(open(multirun_path, encoding="utf-8"))
        for variant, runs in mr["raw_runs"].items():
            per_run = []
            for run_decisions in runs:
                decisions = {qid: d["routed_to"] for qid, d in run_decisions.items()}
                per_run.append(score_selector(selector_from_decisions(decisions)))
            llm_run_results[variant] = per_run
    else:
        print(f"WARNING: {multirun_path} not found. Run src/phase2_step3c_router_multirun.py first, "
              f"or copy that file here, to include LLM router quality numbers.")

    # --- Print summary ---
    print("=" * 78)
    print(f"{'condition':<24}{'correct':>10}{'faithful':>10}{'n':>6}")
    print("-" * 78)
    for name in ("always_kg", "always_rag", "oracle_category", "oracle_per_question", "deterministic"):
        if name in results:
            r = results[name]
            print(f"{name:<24}{r['correct']:>9.0%} {r['faithful']:>9.0%} {r['n']:>6}")
    for variant, per_run in llm_run_results.items():
        corrs = [r["correct"] for r in per_run]
        faiths = [r["faithful"] for r in per_run]
        c_mean, c_lo, c_hi = statistics.mean(corrs), min(corrs), max(corrs)
        f_mean = statistics.mean(faiths)
        label = f"LLM_{variant}"
        print(f"{label:<24}{c_mean:>8.0%}* {f_mean:>9.0%} {per_run[0]['n']:>6}   "
              f"(range {c_lo:.0%}-{c_hi:.0%} across {len(per_run)} runs)")

    # --- Cost of misrouting vs oracle(category), by category ---
    print("\n" + "=" * 78)
    print("Cost of misrouting: mean correctness gap vs oracle(category), by category")
    print("(positive = oracle better; RISKY categories marked *)")
    print("-" * 78)
    oracle_cat_result = results["oracle_category"]
    for name in ("always_kg", "always_rag", "deterministic"):
        if name not in results:
            continue
        gaps = cost_of_misrouting(results[name], oracle_cat_result)
        print(f"\n{name}:")
        for cat, gap in sorted(gaps.items(), key=lambda x: -x[1]):
            tag = " *RISKY*" if cat in RISKY_CATS else ""
            print(f"    {cat:<18} {gap:+.1%}{tag}")
    for variant, per_run in llm_run_results.items():
        print(f"\nLLM_{variant} (mean gap across {len(per_run)} runs):")
        all_gaps = [cost_of_misrouting(r, oracle_cat_result) for r in per_run]
        cats = set(c for g in all_gaps for c in g)
        for cat in sorted(cats, key=lambda c: -statistics.mean([g.get(c, 0) for g in all_gaps])):
            vals = [g.get(cat, 0) for g in all_gaps if cat in g]
            if not vals:
                continue
            tag = " *RISKY*" if cat in RISKY_CATS else ""
            print(f"    {cat:<18} {statistics.mean(vals):+.1%}{tag}")

    # --- Save ---
    out = {
        "_meta": {"purpose": "Step 4: end-to-end quality + cost-of-misrouting, no new LLM calls/grading"},
        "results": {k: {kk: vv for kk, vv in v.items() if kk != "per_item_correct"} for k, v in results.items()},
        "llm_router_per_run": {
            variant: [{kk: vv for kk, vv in r.items() if kk != "per_item_correct"} for r in per_run]
            for variant, per_run in llm_run_results.items()
        },
    }
    json.dump(out, open(DATA / "phase2_step4_results.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase2_step4_results.json")