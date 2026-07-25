"""
bvl_extract.py — Stage 4 (Germany): pull authorised-product data for late blight from the BVL PSM API.

Walks the schema chain mapped manually:
  kode (pest code) -> awg_schadorg (uses targeting the pest) -> awg (use: product + crop)
  -> mittel (product name + validity) -> wirkstoff_gehalt -> wirkstoff (active substances)

Writes bvl_late_blight_DE.json for inspection. This is the extraction method-of-record for the thesis.
Run:  python bvl_extract.py   (needs: pip install requests)
"""
import requests, json, time
from urllib.parse import quote

import sys
from datetime import date

BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"

# --- GROUND-TRUTH SCOPE DECISIONS (documented, not silent) ---
# Each disease's pest-code scope is chosen to match the benchmark disease exactly.
# Late blight: severity/crop VARIANTS of one species -> include general + tomato + potato, EXCLUDE brown rot.
# Apple scab:  VENTIN only -> exclude pear (VENTPI), cherry (VENTCE), genus-level (VENTSP/VENTUR).
# Powdery mildew: PODOXA only (cucurbits) -> exclude other-crop Podosphaera species and genus-level PODOSP.
DISEASES = {
    "late_blight":    {"label": "late blight (tomato/potato)", "codes": ["PHYTIN", "PHYTIN_1", "PHYTIN_2"],
                       "excluded": ["PHYTIN_3", "PHYTIN_4 (brown rot)"]},
    "apple_scab":     {"label": "apple scab", "codes": ["VENTIN"],
                       "excluded": ["VENTPI (pear)", "VENTCE (cherry)", "VENTSP/VENTUR (genus)"]},
    "powdery_mildew": {"label": "cucurbit powdery mildew", "codes": ["PODOXA"],
                       "excluded": ["PODOLE/PODOTR/PODOCL/PODOAP (other crops)", "PODOSP (genus)"]},
}

# choose disease from the command line: python src/bvl_extract.py apple_scab
KEY = sys.argv[1] if len(sys.argv) > 1 else "late_blight"
if KEY not in DISEASES:
    sys.exit(f"Unknown disease '{KEY}'. Choose one of: {', '.join(DISEASES)}")
PEST_CODES = DISEASES[KEY]["codes"]
DISEASE_LABEL = DISEASES[KEY]["label"]
EXCLUDED = DISEASES[KEY]["excluded"]
OUTFILE = f"bvl_{KEY}_DE.json"

# keep only products whose authorisation has NOT expired (zul_ende in the future or empty)
VALID_ONLY = True
TODAY = date.today().isoformat()

def is_valid(product):
    """True if the product's authorisation end date is empty or today-or-later."""
    end = (product.get("zul_ende") or "").strip()
    if not end:
        return True                 # no end date recorded = treat as valid
    return end[:10] >= TODAY        # ISO dates compare correctly as strings

def get(table, q=None, limit=1000):
    """GET a table, optionally with a JSON filter q (dict). Handles pagination."""
    url = f"{BASE}/{table}/"
    params = {"limit": limit}
    if q is not None:
        params["q"] = json.dumps(q)
    items, offset = [], 0
    while True:
        params["offset"] = offset
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("items", []))
        if not data.get("hasMore"):
            break
        offset += data.get("limit", limit)
        time.sleep(0.2)   # be polite to the server
    return items

print(f"Extracting: {DISEASE_LABEL}  codes={PEST_CODES}\n")

# 1) uses (awg_id) that target our pest codes
awg_ids = set()
for code in PEST_CODES:
    rows = get("awg_schadorg", {"schadorg": code})   # exact match on the code
    print(f"  awg_schadorg schadorg={code}: {len(rows)} use-links")
    for row in rows:
        awg_ids.add(row["awg_id"])
print(f"  -> {len(awg_ids)} distinct authorised uses (awg_id)\n")

# 2) for each use, pull the awg record (product kennr + crop) — filter awg by awg_id
uses = []
for i, awg_id in enumerate(sorted(awg_ids), 1):
    rows = get("awg", {"awg_id": awg_id})
    for row in rows:
        uses.append(row)
    if i % 25 == 0:
        print(f"  awg lookups: {i}/{len(awg_ids)}")
print(f"  -> {len(uses)} awg use records\n")

# collect the distinct product ids (kennr) these uses point to
kennrs = sorted({u["kennr"] for u in uses if u.get("kennr")})
print(f"  -> {len(kennrs)} distinct products (kennr)\n")

# 3) product details (name, validity) from mittel
products = {}
for i, kennr in enumerate(kennrs, 1):
    rows = get("mittel", {"kennr": kennr})
    if rows:
        products[kennr] = rows[0]
    if i % 25 == 0:
        print(f"  mittel lookups: {i}/{len(kennrs)}")

# 3b) optionally drop products whose authorisation has expired
n_before = len(products)
if VALID_ONLY:
    products = {k: p for k, p in products.items() if is_valid(p)}
    kennrs = [k for k in kennrs if k in products]
    uses = [u for u in uses if u.get("kennr") in products]
    print(f"  valid-only filter: kept {len(products)}/{n_before} currently-authorised products\n")

# 4) active substances per product: wirkstoff_gehalt (kennr -> wirkstoff) then wirkstoff names
substances = {}
for i, kennr in enumerate(kennrs, 1):
    gehalt = get("wirkstoff_gehalt", {"kennr": kennr})
    substances[kennr] = gehalt
    if i % 25 == 0:
        print(f"  wirkstoff_gehalt lookups: {i}/{len(kennrs)}")

# data provenance: the STAND (update date) table
try:
    stand = get("stand")
except Exception:
    stand = []

out = {
    "_meta": {
        "disease": DISEASE_LABEL,
        "pest_codes": PEST_CODES,
        "excluded_codes": EXCLUDED,
        "valid_only": VALID_ONLY,
        "extracted_on": TODAY,
        "source": "BVL PSM API (psm-api.bvl.bund.de)",
        "note": "Authorisation currency taken from the API zul_ende field; not re-confirmed against the human BVL portal.",
        "stand": stand,
        "n_uses": len(uses), "n_products": len(products),
    },
    "uses": uses,
    "products": products,
    "substances": substances,
}
json.dump(out, open(OUTFILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\nSaved {OUTFILE}  ({len(products)} products, {len(uses)} uses)")
print("Inspect it, then spot-check a few products before trusting it.")