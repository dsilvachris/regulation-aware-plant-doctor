"""
probe_crop_hierarchy.py — does a crop HIERARCHY exist for our diseases' crops in BVL data?
Category 7 (hierarchy-traversal) is only instantiable if authorisations are recorded at a parent
crop level that implies child crops. This probe checks the real awg 'kultur' codes and whether
the kode table encodes any parent/child crop structure.
Run: python src/probe_crop_hierarchy.py
"""
import json, urllib.request, urllib.parse
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"
BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"

def fetch(table, q=None, limit=5000):
    url = f"{BASE}/{table}/?limit={limit}"
    if q: url += "&q=" + urllib.parse.quote(json.dumps(q))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r).get("items", [])

# 1) what kultur codes appear in our late-blight awg uses?
de = json.load(open(DATA / "bvl_late_blight_DE.json", encoding="utf-8"))
uses = de.get("uses", [])
kultur_codes = {}
for u in uses:
    k = u.get("kultur")
    if k: kultur_codes[str(k)] = kultur_codes.get(str(k), 0) + 1
print(f"Distinct kultur codes in late-blight uses: {len(kultur_codes)}")
print(f"  codes + frequency: {dict(sorted(kultur_codes.items(), key=lambda x:-x[1]))}\n")

# 2) translate them via the kode table (which kodeliste are crops?)
# find crop code list — try to resolve a few codes across kodelists
sample = list(kultur_codes)[:8]
print("Resolving sample kultur codes via kode table:")
for code in sample:
    rows = fetch("kode", {"kode": code})
    labels = [(r.get("kodeliste"), r.get("sprache"), r.get("kodetext")) for r in rows]
    # prefer German/English readable labels
    readable = [l for l in labels if l[1] in ("DE","GB")]
    print(f"  {code}: {readable[:3] if readable else labels[:3]}")

# 3) does the kode table expose hierarchy? look for a parent/level field on crop codes
print("\nInspecting a crop code record's full fields for any hierarchy/parent pointer:")
if sample:
    rows = fetch("kode", {"kode": sample[0]})
    if rows:
        print(f"  fields present: {list(rows[0].keys())}")
        print(f"  full record: {json.dumps(rows[0], ensure_ascii=False)}")

# 4) is there a dedicated crop-hierarchy table? probe likely names
print("\nProbing for a crop-hierarchy table:")
for t in ["kultur", "kultur_gruppe", "kulturgruppe", "kode_hierarchie", "kultur_hierarchie"]:
    try:
        rows = fetch(t, limit=1)
        print(f"  {t}/: EXISTS — sample keys {list(rows[0].keys()) if rows else '(empty)'}")
    except Exception as e:
        print(f"  {t}/: 404 / not found")