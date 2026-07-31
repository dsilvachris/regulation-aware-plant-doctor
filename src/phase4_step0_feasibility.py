"""
phase4_step0_feasibility.py — Phase 4, Step 0: candidate-set feasibility check.

Confirms, at the actual scale Phase 4 will use (not just via one anecdote), that:
  1. openFDA returns real records for a candidate set of active substances.
  2. Each substance's ATC code can be obtained (natively from EMA, via RxClass for the FDA side).
  3. Genuine cross-region divergence exists in this candidate set (some substance/product
     approved in one region, not the other) — same "checked, not assumed" discipline as Phase 1.
  4. The candidate set spans enough ATC classes to support real hierarchy-traversal questions
     (Category 7) — i.e. some substances share a parent ATC class with others in the set.

This script needs open internet access to api.fda.gov, rxnav.nlm.nih.gov, and ema.europa.eu — none of
which are reachable from a sandboxed environment with a domain allowlist. Run it locally.

Run: python src/phase4_step0_feasibility.py
"""
import json, time
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"

# A small, deliberately mixed candidate set: some likely-divergent (aducanumab: FDA yes, EMA refused),
# some likely-convergent (common generics), spanning a few ATC classes to test hierarchy richness.
CANDIDATES = [
    "aducanumab", "lecanemab",              # Alzheimer's — known FDA/EMA divergence candidates
    "morphine", "oxycodone", "fentanyl",     # opioids — same ATC class (N02A), tests hierarchy
    "metformin", "sitagliptin",              # diabetes — common, likely convergent
    "ibuprofen", "aspirin",                  # common OTC — likely convergent, factual-category control
]

FDA_URL = "https://api.fda.gov/drug/drugsfda.json"
RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
RXNORM_FINDRXCUI = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
EMA_MEDICINES_URL = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines_json-report_en.json"


def fda_lookup(substance):
    """Returns whether the substance has an ACTUALLY APPROVED FDA application (submission_status "AP"
    on at least one submission), not just any record matching the search — a 'Discontinued' marketing
    status still means it WAS approved, so we check submission history, not current marketing status."""
    r = requests.get(FDA_URL, params={"search": f'products.active_ingredients.name:"{substance.upper()}"',
                                       "limit": 20}, timeout=20)
    if r.status_code != 200:
        return {"found": False, "approved": False, "status": r.status_code}
    data = r.json()
    results = data["results"]
    approved = any(sub.get("submission_status") == "AP"
                   for app in results for sub in app.get("submissions", []))
    return {"found": True, "approved": approved, "n": data["meta"]["results"]["total"], "sample": results[:2]}


def word_boundary_match(substance, text):
    """Exact-word match, not substring — prevents 'morphine' matching inside 'apomorphine'."""
    import re
    if not text:
        return False
    return re.search(r'\b' + re.escape(substance.lower()) + r'\b', text.lower()) is not None


def rxcui_lookup(substance):
    r = requests.get(RXNORM_FINDRXCUI, params={"name": substance}, timeout=20)
    if r.status_code != 200:
        return None
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None


def atc_via_rxclass(rxcui):
    if not rxcui:
        return []
    r = requests.get(f"{RXCLASS_BASE}/class/byRxcui.json", params={"rxcui": rxcui, "relaSource": "ATC"},
                      timeout=20)
    if r.status_code != 200:
        return []
    items = r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    return sorted({i["rxclassMinConceptItem"]["classId"] for i in items
                   if i["rxclassMinConceptItem"]["classType"] in ("ATC1-4",)})


def load_ema_data():
    r = requests.get(EMA_MEDICINES_URL, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def ema_lookup(substance, ema_data):
    hits = [m for m in ema_data
            if word_boundary_match(substance, m.get("active_substance"))
            or word_boundary_match(substance, m.get("international_non_proprietary_name_common_name"))]
    return hits


if __name__ == "__main__":
    print("Loading EMA medicines dataset (this is a single bulk file, ~2700 records)...")
    ema_data = load_ema_data()
    print(f"  loaded {len(ema_data)} EMA records\n")

    results = {}
    for sub in CANDIDATES:
        print(f"--- {sub} ---")
        fda = fda_lookup(sub)
        time.sleep(0.3)
        rxcui = rxcui_lookup(sub)
        time.sleep(0.3)
        atc_codes = atc_via_rxclass(rxcui)
        ema_hits = ema_lookup(sub, ema_data)
        ema_atc = sorted({m["atc_code_human"] for m in ema_hits if m.get("atc_code_human")})
        ema_statuses = sorted({m.get("medicine_status", "") for m in ema_hits})
        ema_approved = any(m.get("medicine_status") == "Authorised" for m in ema_hits)

        fda_approved = fda.get("approved", False)
        divergent = fda_approved != ema_approved  # authorised in one region's regulator, not the other

        print(f"  FDA: found={fda.get('found')}, APPROVED={fda_approved} "
              f"({fda.get('n', 0)} matching records)")
        print(f"  EMA: found={len(ema_hits) > 0}, AUTHORISED={ema_approved} "
              f"(statuses seen: {ema_statuses})")
        print(f"  ATC (via RxClass, FDA-side): {atc_codes}")
        print(f"  ATC (native, EMA-side): {ema_atc}")
        print(f"  DIVERGENT (authorised by one regulator, not the other): {divergent}")

        results[sub] = {
            "fda_found": fda.get("found", False), "fda_approved": fda_approved, "fda_n": fda.get("n", 0),
            "ema_found": len(ema_hits) > 0, "ema_approved": ema_approved, "ema_n": len(ema_hits),
            "ema_statuses_seen": ema_statuses,
            "atc_fda_side": atc_codes, "atc_ema_side": ema_atc,
            "divergent": divergent,
        }
        print()

    # --- Summary checks ---
    n_divergent = sum(1 for r in results.values() if r["divergent"])
    all_atc_prefixes = set()
    for r in results.values():
        for code in r["atc_fda_side"] + r["atc_ema_side"]:
            if len(code) >= 3:
                all_atc_prefixes.add(code[:3])  # anatomical+therapeutic subgroup, e.g. "N02"
    shared_classes = {p for p in all_atc_prefixes
                       if sum(1 for r in results.values()
                              if any(c.startswith(p) for c in r["atc_fda_side"] + r["atc_ema_side"])) >= 2}

    print("=" * 60)
    print(f"Candidates with real cross-region divergence: {n_divergent} / {len(CANDIDATES)}")
    print(f"ATC subgroups shared by 2+ candidates (hierarchy richness): {sorted(shared_classes)}")

    go = n_divergent >= 2 and len(shared_classes) >= 1
    print(f"\nGO/NO-GO: {'GO' if go else 'NO-GO - widen candidate set before proceeding to Step 1'}")

    json.dump({"candidates": results, "n_divergent": n_divergent,
               "shared_atc_subgroups": sorted(shared_classes), "go": go},
              open(DATA / "phase4_step0_feasibility.json", "w"), indent=2)
    print("\nWrote data/phase4_step0_feasibility.json")