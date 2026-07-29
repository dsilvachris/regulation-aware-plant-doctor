"""
phase3_step0_freeze.py — Phase 3, Step 0: verify all inputs Phase 3 stands on are present, loadable, and
mutually consistent. Produces a 'frozen inputs' manifest recording exactly what Phase 3 builds upon (git
commit + file hashes), mirroring phase2_step0_freeze.py's convention.

Phase 3 stands on TWO things Phase 2 did not need to touch:
  1. Phase 1's arms (kg_arm.py, rag_arm.py) — fusion calls these directly, unchanged, so their actual
     retrieval FUNCTIONS (not just the underlying data files) are smoke-tested here, not just parsed.
  2. Phase 2's deterministic-router result (52% correct / 95% faithful, zero risky-category cost) — the
     fixed single-arm baseline fusion must beat to justify itself. This script re-derives that number from
     the committed rule + existing grades (not from a possibly-stale cached JSON) to confirm it hasn't
     drifted before Phase 3 builds on top of it.

Run: python src/phase3_step0_freeze.py
"""
import json, hashlib, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12] if Path(path).exists() else None


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


print("=== Phase 3 Step 0: freeze Phase-1 + Phase-2 inputs ===\n")

data_files = ["kg_all.ttl", "rag_docs_all.json",
              "benchmark_cat1_2.json", "benchmark_cat3_7.json", "benchmark_multidisease.json",
              "comparison_runs.json", "grading_sheet_BLIND.json", "grading_key.json"]
code_files = ["kg_arm.py", "rag_arm.py", "kg_verbalise.py", "eval_pipeline.py",
              "phase2_step1_oracle.py", "phase2_step2b_deterministic_router.py",
              "phase2_step4_cost_of_misrouting.py"]

manifest = {"git_commit": git_commit(), "data": {}, "code": {}, "checks": {}}

print("-- data artifacts --")
all_ok = True
for f in data_files:
    h = sha(DATA / f)
    manifest["data"][f] = h
    status = "OK" if h else "MISSING"
    if not h:
        all_ok = False
    print(f"  {f:32} {status:8} {h or ''}")

print("\n-- code artifacts --")
for f in code_files:
    h = sha(SRC / f)
    manifest["code"][f] = h
    status = "OK" if h else "MISSING"
    if not h:
        all_ok = False
    print(f"  {f:32} {status:8} {h or ''}")


def check(name, cond, detail=""):
    manifest["checks"][name] = bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    return cond


print("\n-- consistency checks (inherited from Phase 2's freeze) --")
try:
    import eval_pipeline as ep
    items = ep.load_benchmark()
    n_q = len(items)
    check("benchmark loads", n_q > 0, f"({n_q} questions)")
    cats = sorted({c for _, _, c in items})
    check("all categories present", len(cats) >= 7, f"({cats})")
except Exception as e:
    check("benchmark loads", False, f"(error: {e})")
    items = []

try:
    from rdflib import Graph, Namespace
    EX = Namespace("http://plant-regkg.org/ontology#")
    g = Graph()
    g.parse(str(DATA / "kg_all.ttl"), format="turtle")
    diseases = list(g.query("SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE {?d a ex:Disease}", initNs={"ex": EX}))
    nd = int(diseases[0][0])
    check("KG loads with 3 diseases", nd == 3, f"({nd} diseases, {len(g)} triples)")
except Exception as e:
    check("KG loads", False, f"(error: {e})")

try:
    docs = json.load(open(DATA / "rag_docs_all.json", encoding="utf-8"))["documents"]
    check("RAG docs load", len(docs) > 0, f"({len(docs)} docs)")
except Exception as e:
    check("RAG docs load", False, f"(error: {e})")

print("\n-- Phase-3-specific checks (new) --")

# Smoke-test that the actual arm FUNCTIONS fusion_arm.py will call are callable end-to-end,
# not just that the underlying data files parse.
try:
    sample_qid, sample_q, _ = next((it for it in items if it[0] == "f01"), items[0])
    answer, kg_raw_facts = ep.kg_answer_by_id(sample_qid, sample_q)
    check("kg_answer_by_id() callable end-to-end", bool(answer), f"(qid={sample_qid}, len(answer)={len(answer)})")
except Exception as e:
    check("kg_answer_by_id() callable end-to-end", False, f"(error: {e})")

try:
    answer, rag_docs_used = ep.rag_answer(sample_q)
    check("rag_answer() callable end-to-end", bool(answer),
          f"(qid={sample_qid}, {len(rag_docs_used)} docs retrieved)")
except Exception as e:
    check("rag_answer() callable end-to-end", False, f"(error: {e})")

# Re-derive Phase 2's deterministic-router headline number from the committed rule + existing grades,
# rather than trusting a possibly-stale cached data/phase2_deterministic_router.json — confirms the
# Phase-2 baseline hasn't drifted before Phase 3 is built on top of it.
try:
    from phase2_step2b_deterministic_router import classify_deterministic

    sheet = {it["item"]: it for it in json.load(open(DATA / "grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
    key = {k["item"]: k for k in json.load(open(DATA / "grading_key.json", encoding="utf-8"))["key"]}

    def val(x):
        s = str(x).strip()
        return int(s) if s in ("0", "1") else None

    qtext = {qid: q for qid, q, cat in items}
    corr, faith = [], []
    for item, it in sheet.items():
        mp = key.get(item)
        if not mp or it.get("category") == "hierarchy":
            continue
        qid = item.split("_", 1)[1] if "_" in item else item
        q = qtext.get(qid)
        if q is None:
            continue
        arm = classify_deterministic(q)
        slot = "A" if mp["A"] == arm else ("B" if mp["B"] == arm else None)
        if slot is None:
            continue
        c, f = val(it.get(f"grade_{slot}_correct")), val(it.get(f"grade_{slot}_faithful"))
        if c is not None:
            corr.append(c)
        if f is not None:
            faith.append(f)
    det_correct = sum(corr) / len(corr) if corr else 0
    det_faithful = sum(faith) / len(faith) if faith else 0
    check("Phase-2 deterministic router reproduces 52%/95%",
          abs(det_correct - 0.52) < 0.01 and abs(det_faithful - 0.95) < 0.01,
          f"(recomputed: {det_correct:.0%} correct, {det_faithful:.0%} faithful)")
except Exception as e:
    check("Phase-2 deterministic router reproduces 52%/95%", False, f"(error: {e})")

# Confirm Phase 3 build hasn't started yet (sanity: this really is Step 0)
fusion_exists = (SRC / "fusion_arm.py").exists()
check("fusion_arm.py does not yet exist (Step 0 sanity)", not fusion_exists,
      "(exists already — Step 0 is being run out of order)" if fusion_exists else "")

manifest["all_inputs_present"] = all_ok
json.dump(manifest, open(DATA / "phase3_frozen_inputs.json", "w"), indent=2)
print(f"\nWrote data/phase3_frozen_inputs.json (git {manifest['git_commit']})")
print("FROZEN OK — safe to build Phase 3 on these inputs." if all_ok and all(manifest["checks"].values())
      else "ISSUES FOUND — resolve before building Phase 3.")