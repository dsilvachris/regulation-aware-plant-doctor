"""
phase4_step2_source_data.py — Phase 4, Step 2: source the data.

Pulls and PERSISTS the full, real records for the 8-substance roster confirmed in Step 0
(docs/Phase4_Step0_Feasibility.md) from openFDA and EMA, plus each substance's ATC classification.
Unlike Step 0 (which only checked booleans - found/approved/divergent), this saves the full structured
records so Step 3 (KG build) has real source data to build from, not re-fetched ad hoc.

Self-contained (does not import phase4_step0_feasibility.py, which has its own __main__ entrypoint) -
minimal duplication of the fetch logic, same convention used elsewhere in this project (e.g.
phase2_step4_cost_of_misrouting.py's CATEGORY_OPTIMAL, kept in sync by comment rather than cross-import).

Every record is written with its retrieval timestamp and source URL, so later verification (spot-checking
against the live source, same discipline as Phase 1's BVL/Mattilsynet extraction) is always possible.

Run: python src/phase4_step2_source_data.py
"""
import json, time, re
from datetime import datetime, timezone
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"

FDA_URL = "https://api.fda.gov/drug/drugsfda.json"
RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
RXNORM_FINDRXCUI = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
EMA_MEDICINES_URL = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines_json-report_en.json"

# The verified 8-substance roster from Step 0 (docs/Phase4_Step0_Feasibility.md) - do not add substances
# here without re-running Step 0's feasibility check on them first.
ROSTER = ["aducanumab", "lecanemab", "donanemab",
          "niraparib", "isatuximab", "epcoritamab", "dostarlimab", "melphalan flufenamide"]


def word_boundary_match(substance, text):
    if not text:
        return False
    return re.search(r'\b' + re.escape(substance.lower()) + r'\b', text.lower()) is not None


def fetch_fda_records(substance):
    r = requests.get(FDA_URL, params={"search": f'products.active_ingredients.name:"{substance.upper()}"',
                                       "limit": 20}, timeout=20)
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def fetch_rxcui(substance):
    r = requests.get(RXNORM_FINDRXCUI, params={"name": substance}, timeout=20)
    if r.status_code != 200:
        return None
    ids = r.json().get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None


def fetch_atc_via_rxclass(rxcui):
    if not rxcui:
        return []
    r = requests.get(f"{RXCLASS_BASE}/class/byRxcui.json", params={"rxcui": rxcui, "relaSource": "ATC"},
                      timeout=20)
    if r.status_code != 200:
        return []
    items = r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    return sorted({i["rxclassMinConceptItem"]["classId"] for i in items
                   if i["rxclassMinConceptItem"]["classType"] == "ATC1-4"})


def fetch_ema_records(substance, ema_data):
    return [m for m in ema_data
            if word_boundary_match(substance, m.get("active_substance"))
            or word_boundary_match(substance, m.get("international_non_proprietary_name_common_name"))]


if __name__ == "__main__":
    ts = datetime.now(timezone.utc).isoformat()
    print("Loading EMA medicines dataset...")
    ema_all = requests.get(EMA_MEDICINES_URL, timeout=60).json()["data"]
    print(f"  loaded {len(ema_all)} EMA records\n")

    fda_out, ema_out = {}, {}
    for sub in ROSTER:
        print(f"--- {sub} ---")
        fda_records = fetch_fda_records(sub)
        time.sleep(0.3)
        rxcui = fetch_rxcui(sub)
        time.sleep(0.3)
        atc_rxclass = fetch_atc_via_rxclass(rxcui)
        ema_records = fetch_ema_records(sub, ema_all)

        print(f"  FDA: {len(fda_records)} records, rxcui={rxcui}, ATC(RxClass)={atc_rxclass}")
        print(f"  EMA: {len(ema_records)} records, "
              f"ATC(native)={sorted({m.get('atc_code_human') for m in ema_records if m.get('atc_code_human')})}")

        fda_out[sub] = {
            "retrieved_at": ts, "source_url": FDA_URL, "rxcui": rxcui, "atc_via_rxclass": atc_rxclass,
            "records": fda_records,
        }
        ema_out[sub] = {
            "retrieved_at": ts, "source_url": EMA_MEDICINES_URL, "records": ema_records,
        }
        print()

    json.dump(fda_out, open(DATA / "fda_drugs_US.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(ema_out, open(DATA / "ema_medicines_EU.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Wrote data/fda_drugs_US.json and data/ema_medicines_EU.json")
    print("\nNEXT: spot-check a few records against the live source pages (same discipline as Phase 1's "
          "BVL/Mattilsynet extraction) before building the KG in Step 3.")