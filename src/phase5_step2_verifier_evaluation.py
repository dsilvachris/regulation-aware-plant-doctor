"""
phase5_step2_verifier_evaluation.py — Phase 5, Step 2 (Work Package B): full evaluation of the
verification layer before treating it as validated, per Phase5_Plan.md's requirement.

Expands Step 0a's 35-case, pharma-only test set (a caveat explicitly flagged there) with:
  - the confirmed r2 fabrication (must flag) - unchanged
  - 54 real, correct-and-faithful KG answers from Phase 1's PLANT-PROTECTION domain (the domain this
    verifier will actually be deployed against in Step 1's integrated assistant), pulled from the real
    grading data, excluding the 12 disease-name-bug-affected questions to keep the known-good set clean
  - the original 35 pharma known-good cases, kept for cross-domain comparison
  - new borderline cases: genuine, fully-supported compound claims ("authorised in both Germany and
    Norway") specifically constructed to stress-test whether coordination-splitting over-flags legitimate
    claims, in the plant-protection domain the verifier will actually run against

Run: python src/phase5_step2_verifier_evaluation.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import verification_layer as vl
import eval_pipeline as ep_p1
import eval_pipeline_phase4 as ep_p4
from kg_verbalise import verbalise as verbalise_p1_base, verbalise2 as verbalise2_p1, verbalise3 as verbalise3_p1
from kg_verbalise_phase4 import verbalise as verbalise_p4


def verbalise_p1(vcat, facts):
    """Same fallback chain as eval_pipeline.py's kg_answer_by_id() - verbalise3 -> verbalise2 ->
    verbalise. Using only the base verbalise() (as an earlier draft of this script did) silently
    returns a raw dict-string fallback for categories it doesn't handle (products_with_substance,
    substance_in_both, de_only, etc.), which is NOT what the LLM actually saw - a bug in the harness,
    not the verifier, caught by an unexpectedly high false-positive rate on first run."""
    return verbalise3_p1(vcat, facts) or verbalise2_p1(vcat, facts) or verbalise_p1_base(vcat, facts)


def val(x):
    s = str(x).strip()
    return int(s) if s in ("0", "1") else None


def load_phase1_known_good():
    sheet = {it["item"]: it for it in json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
    key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}
    cases = []
    for item, it in sorted(sheet.items()):
        qid = item.split("_", 1)[1] if "_" in item else item
        if qid.startswith(("as_", "pm_", "xd_")):
            continue  # exclude disease-name-bug-affected questions, keep the known-good set clean
        mp = key.get(item)
        if not mp:
            continue
        for slot in ("A", "B"):
            if mp[slot] != "kg":
                continue
            if val(it.get(f"grade_{slot}_correct")) == 1 and val(it.get(f"grade_{slot}_faithful")) == 1:
                query_fn, params, vcat = ep_p1.route(qid)
                facts_text = verbalise_p1(vcat, query_fn(**params))
                cases.append({"label": f"phase1_{item}", "answer": it[f"System {slot}"],
                               "facts": facts_text, "domain": "plant_protection", "should_flag": False,
                               "question": it.get("question", "")})
    return cases


def load_phase4_known_good():
    sheet = {it["item"]: it for it in json.load(open(DATA / "phase4_grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
    key = {k["item"]: k for k in json.load(open(DATA / "phase4_grading_key.json", encoding="utf-8"))["key"]}
    cases = []
    for item, it in sorted(sheet.items()):
        qid = item.split("_", 1)[1]
        mp = key.get(item)
        if not mp:
            continue
        for slot in ("A", "B"):
            if mp[slot] != "kg":
                continue
            if val(it.get(f"grade_{slot}_correct")) == 1 and val(it.get(f"grade_{slot}_faithful")) == 1:
                query_fn, params, vcat = ep_p4.route(qid)
                facts_text = verbalise_p4(vcat, query_fn(**params))
                cases.append({"label": f"phase4_{item}", "answer": it[f"System {slot}"],
                               "facts": facts_text, "domain": "pharma", "should_flag": False,
                               "question": it.get("question", "")})
    return cases


TRUE_POSITIVE = [
    {"label": "r2_confirmed_fabrication",
     "answer": "Niraparib is authorised via both the EU's centralised procedure (EMA) and at the national level.",
     "facts": "niraparib is authorised via the EU's centralised procedure (EMA).",
     "domain": "pharma", "should_flag": True, "question": "Is niraparib authorised via EMA's centralised procedure?"},
]

BORDERLINE_GENUINE_COMPOUND = [
    {"label": "borderline_both_countries_true",
     "answer": "Cyazofamid is authorised against late blight in both Germany and Norway.",
     "facts": "Germany: 112 products authorised against late blight, including those containing cyazofamid. "
              "Norway: cyazofamid is authorised against late blight.",
     "domain": "plant_protection", "should_flag": False, "question": ""},
    {"label": "borderline_negation_and_true",
     "answer": "Fluazinam is authorised in Germany and not authorised in Norway.",
     "facts": "fluazinam is authorised against late blight in Germany. fluazinam is NOT authorised "
              "against late blight in Norway.",
     "domain": "plant_protection", "should_flag": False, "question": ""},
    {"label": "borderline_both_true_fabricated_addition",
     "answer": "Fluazinam is authorised in both Germany and at the regional level within Bavaria.",
     "facts": "fluazinam is authorised against late blight in Germany.",
     "domain": "plant_protection", "should_flag": True, "question": ""},  # "Bavaria" is a genuine fabrication
]

if __name__ == "__main__":
    print("Loading real known-good cases from both domains...")
    cases = TRUE_POSITIVE + load_phase1_known_good() + load_phase4_known_good() + BORDERLINE_GENUINE_COMPOUND
    n_should_flag = sum(1 for c in cases if c["should_flag"])
    print(f"  {len(cases)} total cases ({n_should_flag} should flag, {len(cases) - n_should_flag} should not)\n")

    tp, fp, tn, fn = 0, 0, 0, 0
    failures = []

    for c in cases:
        result = vl.verify(c["answer"], c["facts"], domain=c["domain"], question=c.get("question"))
        flagged = result["flagged"]
        if c["should_flag"] and flagged:
            tp += 1
        elif c["should_flag"] and not flagged:
            fn += 1
            failures.append(("FALSE NEGATIVE", c["label"], c["answer"], c["facts"]))
        elif not c["should_flag"] and flagged:
            fp += 1
            failures.append(("FALSE POSITIVE", c["label"], c["answer"], result["reason"]))
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")

    print("=" * 70)
    print(f"TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    print(f"Precision: {precision:.1%}  (of flagged answers, how many were truly unsupported)")
    print(f"Recall:    {recall:.1%}  (of truly unsupported answers, how many were caught)")
    if (tn + fp):
        print(f"False-positive rate on known-good: {fp}/{tn + fp} = {fp / (tn + fp):.1%}")

    if failures:
        print(f"\n{len(failures)} failures:")
        for kind, label, answer, extra in failures:
            print(f"  [{kind}] {label}")
            print(f"    answer: {answer}")
            print(f"    {extra}")
    else:
        print("\nNo failures. Verifier confirmed across both domains, real known-good data, and "
              "borderline compound-claim stress tests.")