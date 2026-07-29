"""
phase2_step0_freeze.py — Phase 2, Step 0: verify all Phase-1 inputs Phase 2 stands on are present,
loadable, and mutually consistent. Produces a 'frozen inputs' manifest recording exactly what Phase 2
builds upon (git commit + file hashes), so the baseline is pinned and reproducible.
Run: python src/phase2_step0_freeze.py
"""
import json, hashlib, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "src"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12] if Path(path).exists() else None

def git_commit():
    try:
        return subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"

print("=== Phase 2 Step 0: freeze Phase-1 inputs ===\n")

# 1) required data artifacts
data_files = ["kg_all.ttl", "rag_docs_all.json",
              "benchmark_cat1_2.json", "benchmark_cat3_7.json", "benchmark_multidisease.json",
              "comparison_runs.json", "results_summary.json",
              "grading_sheet_BLIND.json", "grading_key.json"]
# 2) required code artifacts
code_files = ["kg_arm.py", "rag_arm.py", "kg_verbalise.py", "eval_pipeline.py",
              "stage6_eval.py", "score_results.py", "build_kg.py"]

manifest = {"git_commit": git_commit(), "data": {}, "code": {}, "checks": {}}

print("-- data artifacts --")
all_ok = True
for f in data_files:
    h = sha(DATA / f)
    manifest["data"][f] = h
    status = "OK" if h else "MISSING"
    if not h: all_ok = False
    print(f"  {f:32} {status:8} {h or ''}")

print("\n-- code artifacts --")
for f in code_files:
    h = sha(SRC / f)
    manifest["code"][f] = h
    status = "OK" if h else "MISSING"
    if not h: all_ok = False
    print(f"  {f:32} {status:8} {h or ''}")

# 3) consistency checks
print("\n-- consistency checks --")
def check(name, cond, detail=""):
    manifest["checks"][name] = bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    return cond

# benchmark question count
try:
    import sys; sys.path.insert(0, str(SRC))
    import eval_pipeline as ep
    items = ep.load_benchmark()
    n_q = len(items)
    check("benchmark loads", n_q > 0, f"({n_q} questions)")
    # category coverage
    cats = sorted({c for _,_,c in items})
    check("all categories present", len(cats) >= 7, f"({cats})")
except Exception as e:
    check("benchmark loads", False, f"(error: {e})")

# KG loads and has the 3 diseases
try:
    from rdflib import Graph, Namespace
    EX = Namespace("http://plant-regkg.org/ontology#")
    g = Graph(); g.parse(str(DATA/"kg_all.ttl"), format="turtle")
    diseases = list(g.query("SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE {?d a ex:Disease}", initNs={"ex":EX}))
    nd = int(diseases[0][0])
    check("KG loads with 3 diseases", nd == 3, f"({nd} diseases, {len(g)} triples)")
except Exception as e:
    check("KG loads", False, f"(error: {e})")

# RAG docs load
try:
    docs = json.load(open(DATA/"rag_docs_all.json", encoding="utf-8"))["documents"]
    check("RAG docs load", len(docs) > 0, f"({len(docs)} docs)")
except Exception as e:
    check("RAG docs load", False, f"(error: {e})")

# Phase-1 results present (the comparison baseline)
try:
    runs = json.load(open(DATA/"comparison_runs.json", encoding="utf-8"))
    check("Phase-1 runs present", runs.get("n_runs",0) >= 1, f"({runs.get('n_runs')} runs)")
except Exception as e:
    check("Phase-1 runs present", False, f"(error: {e})")

manifest["all_inputs_present"] = all_ok
json.dump(manifest, open(DATA/"phase2_frozen_inputs.json","w"), indent=2)
print(f"\nWrote data/phase2_frozen_inputs.json (git {manifest['git_commit']})")
print("FROZEN OK — safe to build Phase 2 on these inputs." if all_ok and all(manifest["checks"].values())
      else "ISSUES FOUND — resolve before building Phase 2.")