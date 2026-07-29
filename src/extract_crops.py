"""
extract_crops.py — Option A: pull REAL crops for each authorisation via awg_kultur, translate the
codes, and cache them into the three bvl_{disease}_DE.json files under _crops (awg_id -> [crop names]).
This fixes the hardcoded-crop limitation. Run: python src/extract_crops.py
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

# build a crop-code -> readable-name map from the kode table (kodeliste for crops).
# We resolve lazily/cache per code to avoid pulling the whole kode table blindly.
_crop_name_cache = {}
def crop_name(code):
    code = str(code)
    if code in _crop_name_cache:
        return _crop_name_cache[code]
    rows = fetch("kode", {"kode": code}, limit=20)
    # prefer English then German readable label
    name = None
    for lang in ("GB", "DE"):
        for r in rows:
            if r.get("sprache") == lang and r.get("kodetext"):
                name = r["kodetext"]; break
        if name: break
    if not name and rows:
        name = rows[0].get("kodetext")
    _crop_name_cache[code] = name or f"crop:{code}"
    return _crop_name_cache[code]

FILES = ["bvl_late_blight_DE.json", "bvl_apple_scab_DE.json", "bvl_powdery_mildew_DE.json"]
for fname in FILES:
    path = DATA / fname
    if not path.exists():
        print(f"skip {fname}"); continue
    de = json.load(open(path, encoding="utf-8"))
    uses = de.get("uses", [])
    awg_ids = sorted({u.get("awg_id") for u in uses if u.get("awg_id")})
    crops_by_awg = {}
    all_codes = set()
    for awg_id in awg_ids:
        rows = fetch("awg_kultur", {"awg_id": awg_id}, limit=50)
        codes = [str(r.get("kultur")) for r in rows if r.get("kultur")]
        crops_by_awg[awg_id] = codes
        all_codes.update(codes)
    # translate codes -> names (dedup lookups)
    code2name = {c: crop_name(c) for c in sorted(all_codes)}
    crops_named = {awg_id: sorted({code2name[c] for c in codes}) for awg_id, codes in crops_by_awg.items()}
    de["_crops"] = crops_named
    de["_crop_codes"] = code2name
    json.dump(de, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # summary: distinct crops across this disease
    distinct = sorted({n for names in crops_named.values() for n in names})
    print(f"{fname}: {len(awg_ids)} uses, {len(all_codes)} distinct crop codes")
    print(f"  crops: {distinct[:15]}{' ...' if len(distinct)>15 else ''}")