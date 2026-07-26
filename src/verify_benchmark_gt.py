"""
verify_benchmark_gt.py — resolve the VERIFY flags in benchmark categories 3-7.

Reads the German late-blight extract and checks which active substances / products are present,
so cross-border and absence answers become confirmed rather than assumed.
Run from the Agro root:  python src/verify_benchmark_gt.py
"""
import json, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- load German late blight ---
de = json.load(open(DATA / "bvl_late_blight_DE.json", encoding="utf-8"))
products = de.get("products", {})
substances = de.get("substances", {})   # kennr -> list of wirkstoff_gehalt rows (has wirknr = substance CODE)

# The substance is stored as a code (wirknr). We must translate wirknr -> name via the wirkstoff table.
# Pull the wirkstoff table live and build a code->name map.
import urllib.request, urllib.parse
BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"

def fetch(table, q=None, limit=5000):
    url = f"{BASE}/{table}/?limit={limit}"
    if q:
        url += "&q=" + urllib.parse.quote(json.dumps(q))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r).get("items", [])

print("Fetching wirkstoff table to translate substance codes -> names ...")
wirkstoff = fetch("wirkstoff")
# find the code field and the name field from a sample
if wirkstoff:
    print(f"  sample wirkstoff row: {json.dumps(wirkstoff[0], ensure_ascii=False)}")
# build map: try common field names
CODE_FIELD = "wirknr" if wirkstoff and "wirknr" in wirkstoff[0] else None
NAME_FIELD = None
if wirkstoff:
    for cand in ("wirkstoffname", "name", "bezeichnung", "wirkstoff"):
        if cand in wirkstoff[0]:
            NAME_FIELD = cand
            break
print(f"  code field = {CODE_FIELD}, name field = {NAME_FIELD}\n")

code2name = {}
if CODE_FIELD and NAME_FIELD:
    for w in wirkstoff:
        code2name[str(w.get(CODE_FIELD))] = w.get(NAME_FIELD)

# translate the substances present in our German late-blight products
de_sub_names = set()
for kennr, rows in substances.items():
    for r in rows:
        name = code2name.get(str(r.get("wirknr")))
        if name:
            de_sub_names.add(name.lower())

print(f"=== {len(de_sub_names)} distinct active substances in German late-blight products ===")
for s in sorted(de_sub_names):
    print(f"  {s}")
print()

def present(term):
    t = term.lower()
    return [v for v in de_sub_names if t in v]

NO_LATE_BLIGHT_SUBS = ["cyazofamid", "mandipropamid", "difenoconazole", "oxathiapiprolin"]
print("=== Cross-border: are Norway's late-blight substances present in the German data? ===")
for s in NO_LATE_BLIGHT_SUBS:
    hits = present(s)
    print(f"  {s:16} -> {'FOUND in DE' if hits else 'NOT in DE'}  {hits[:2]}")
print()

print("=== Absence: German substances NOT among Norway's 4 (divergence evidence) ===")
for s in ["fluazinam", "kupfer", "copper", "mancozeb", "cymoxanil"]:
    hits = present(s)
    in_no = s in [x.lower() for x in NO_LATE_BLIGHT_SUBS]
    if hits and not in_no:
        print(f"  {s:12} in DE ({hits[0]}) but NOT in NO -> DIVERGENCE")
    elif hits:
        print(f"  {s:12} in DE and NO")
    else:
        print(f"  {s:12} not found in DE data")
print()

# (product-name listing kept below for eyeballing)
print("=== German late-blight product names (first 20) ===")
for i, (kennr, p) in enumerate(products.items()):
    if i >= 20:
        print(f"  ... and {len(products)-20} more")
        break
    print(f"  {kennr}  {p.get('mittelname','?')}")