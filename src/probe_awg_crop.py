"""probe_awg_crop.py — find where the crop lives in awg, and inspect the kultur_gruppe hierarchy."""
import json, urllib.request, urllib.parse
BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"
def fetch(table, q=None, limit=5):
    url = f"{BASE}/{table}/?limit={limit}"
    if q: url += "&q=" + urllib.parse.quote(json.dumps(q))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r).get("items", [])

print("=== awg table: full field list of one record ===")
rows = fetch("awg", limit=1)
if rows:
    print("  keys:", list(rows[0].keys()))
    print("  sample:", json.dumps(rows[0], ensure_ascii=False)[:500])

print("\n=== kultur_gruppe: sample records (the hierarchy) ===")
rows = fetch("kultur_gruppe", limit=8)
for r in rows:
    print(" ", json.dumps(r, ensure_ascii=False))

print("\n=== does awg have a 'kultur' field? check a late-blight product's awg by kennr ===")
# pick a known late-blight product kennr from the data
import pathlib, json as J
de = J.load(open(pathlib.Path(__file__).resolve().parent.parent/"data"/"bvl_late_blight_DE.json"))
kennr = next(iter(de.get("products", {})), None)
print(f"  sample kennr: {kennr}")
if kennr:
    rows = fetch("awg", {"kennr": kennr}, limit=3)
    for r in rows:
        # show only crop-relevant fields
        crop_fields = {k:v for k,v in r.items() if "kultur" in k.lower() or "anwend" in k.lower()}
        print(f"  awg crop-related fields: {crop_fields}")