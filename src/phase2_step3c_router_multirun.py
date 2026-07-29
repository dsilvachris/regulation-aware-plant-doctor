"""
phase2_step3c_router_multirun.py — Phase 2, Step 3c: is the prompt-variant comparison (step 3b) a real
effect, or noise from running each prompt once?

Motivation (see docs/Phase2_Step3b_PromptSensitivity.md): PROMPT_A scored 1/12 systematic RAG-wins in the
original llm_router.py run and 2/12 when re-run once here with the identical prompt. Same model, same
prompt, different result — meaning single-run comparisons between A/B/C cannot be trusted at face value.
Before treating PROMPT_B's apparent improvement (6/12 vs A's 2/12) as real, or PROMPT_C's cross-disease
misroute as a property of that prompt rather than one unlucky sample, each variant needs to be run multiple
times and checked for two things:

  1. STABILITY — does each variant route the SAME question to the SAME arm across repeated runs, or does
     the decision flip? A variant whose decisions flip run-to-run cannot be trusted regardless of its
     single-run accuracy number — an unstable router is not usable even if its average looks good.
  2. ROBUSTNESS OF THE STEP-3B FINDING — averaged over N runs, does B still beat A on systematic-RAG-win
     capture, and does C still misroute cross-disease questions more than A/B? If yes across N runs, the
     step-3b conclusion is confirmed. If the gaps shrink to within run-to-run noise, they should be
     reported as inconclusive rather than as a "DOCS-first is safer" finding.

This does NOT re-derive the prompts or scoring logic — it imports them from phase2_step3b_prompt_sensitivity
so there is exactly one definition of each prompt, one parser, one scorer, and one oracle mapping.

Run: python src/phase2_step3c_router_multirun.py            # N_RUNS=3 per variant (default)
     python src/phase2_step3c_router_multirun.py 5           # override N_RUNS
"""
import json, sys, statistics
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
from phase2_step3b_prompt_sensitivity import (
    VARIANTS, EXCLUDE, CATEGORY_OPTIMAL, SYSTEMATIC_RAG_WINS, route_with, score,
)

N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
RISKY_CATS = {"negative", "cross_border", "cross_disease"}


def run_all(items):
    """runs[variant][run_idx] = {qid: {'routed_to':..., 'category':..., 'ambiguous_parse':...}}"""
    runs = {name: [] for name in VARIANTS}
    for run_idx in range(N_RUNS):
        for name, template in VARIANTS.items():
            decisions = {}
            for qid, q, cat in items:
                arm, ambiguous = route_with(template, q)
                decisions[qid] = {"routed_to": arm, "category": cat, "ambiguous_parse": ambiguous}
                print(f"  run{run_idx+1} [{name:14}] {qid:8} {cat:16} -> {arm}")
            runs[name].append(decisions)
        print()
    return runs


def per_run_scores(variant_runs):
    """List of the step-3b score() dict for each run of one variant."""
    return [score(decisions) for decisions in variant_runs]


def mean_range(values):
    if not values:
        return (0, 0, 0)
    return (statistics.mean(values), min(values), max(values))


def stability_analysis(variant_runs, items):
    """For each question, does routed_to stay the same across all N runs?
    Returns (n_stable, n_flip, flip_detail: {qid: [decisions across runs]})."""
    by_qid = {qid: [] for qid, _, _ in items}
    for run_decisions in variant_runs:
        for qid, d in run_decisions.items():
            by_qid[qid].append(d["routed_to"])
    stable, flips = 0, {}
    for qid, arms in by_qid.items():
        if len(set(arms)) == 1:
            stable += 1
        else:
            flips[qid] = arms
    return stable, flips


def summarize(name, variant_runs, items):
    scores = per_run_scores(variant_runs)
    acc = mean_range([s["routing_accuracy_vs_oracle"] for s in scores])
    rag_caught = [int(s["systematic_rag_wins_caught"].split("/")[0]) for s in scores]
    fact = [int(s["factual_routed_to_docs"].split("/")[0]) for s in scores]
    stable, flips = stability_analysis(variant_runs, items)

    risky_flip_or_hit = []
    for qid, arms in flips.items():
        cat = next(it[2] for it in items if it[0] == qid)
        if cat in RISKY_CATS:
            risky_flip_or_hit.append((qid, cat, arms))
    # also catch risky misroutes that are CONSISTENT (every run sends a risky-category question to rag)
    consistent_risky_misroutes = []
    for run_decisions in variant_runs:
        for qid, d in run_decisions.items():
            if d["category"] in RISKY_CATS and d["routed_to"] == "rag":
                cat = d["category"]
                if qid not in flips:  # consistent, not a flip
                    consistent_risky_misroutes.append(qid)
    consistent_risky_misroutes = sorted(set(consistent_risky_misroutes))

    return {
        "variant": name,
        "n_runs": N_RUNS,
        "acc_vs_oracle_mean_min_max": acc,
        "rag_wins_caught_per_run": rag_caught,
        "rag_wins_caught_mean": statistics.mean(rag_caught),
        "factual_to_docs_per_run": fact,
        "factual_to_docs_mean": statistics.mean(fact),
        "stable_questions": stable,
        "total_questions": len(items),
        "flipping_questions": len(flips),
        "flip_detail": flips,
        "risky_category_flips": risky_flip_or_hit,
        "consistent_risky_misroutes": consistent_risky_misroutes,
    }


if __name__ == "__main__":
    items = [it for it in ep.load_benchmark() if it[2] not in EXCLUDE]
    print(f"Routing {len(items)} questions x {N_RUNS} runs x {len(VARIANTS)} variants "
          f"= {len(items) * N_RUNS * len(VARIANTS)} LLM calls.\n")

    runs = run_all(items)

    summaries = {name: summarize(name, runs[name], items) for name in VARIANTS}

    print("=" * 90)
    print(f"{'variant':<14}{'acc(mean,min,max)':<22}{'rag_wins/run':<18}{'factual/run':<16}{'stable_q':<10}")
    print("-" * 90)
    for name, s in summaries.items():
        acc_m, acc_lo, acc_hi = s["acc_vs_oracle_mean_min_max"]
        acc_str = f"{acc_m:.0%} ({acc_lo:.0%}-{acc_hi:.0%})"
        stable_str = f"{s['stable_questions']}/{s['total_questions']}"
        print(f"{name:<14}{acc_str:<22}{str(s['rag_wins_caught_per_run']):<18}"
              f"{str(s['factual_to_docs_per_run']):<16}{stable_str:<10}")

    print("\n--- Stability detail: questions whose routing FLIPPED across runs ---")
    for name, s in summaries.items():
        print(f"\n{name}: {s['flipping_questions']} flipping questions")
        for qid, arms in s["flip_detail"].items():
            tag = " <-- SYSTEMATIC RAG-WIN" if qid in SYSTEMATIC_RAG_WINS else ""
            print(f"    {qid:8} {arms}{tag}")

    print("\n--- Risky-category (negative/cross_border/cross_disease) misroutes to RAG ---")
    for name, s in summaries.items():
        if s["consistent_risky_misroutes"]:
            print(f"  {name}: CONSISTENT misroute every run: {s['consistent_risky_misroutes']}")
        if s["risky_category_flips"]:
            print(f"  {name}: INTERMITTENT (flips run-to-run): "
                  f"{[(q, c) for q, c, _ in s['risky_category_flips']]}")
        if not s["consistent_risky_misroutes"] and not s["risky_category_flips"]:
            print(f"  {name}: none.")

    out = {
        "_meta": {"n_runs": N_RUNS, "purpose": "multi-run stability + robustness check on step-3b variants"},
        "summaries": {name: {k: v for k, v in s.items() if k != "flip_detail"} | {"flip_detail": s["flip_detail"]}
                      for name, s in summaries.items()},
        "raw_runs": runs,
    }
    json.dump(out, open(DATA / "phase2_router_multirun.json", "w"), ensure_ascii=False, indent=2)
    print(f"\nWrote data/phase2_router_multirun.json")