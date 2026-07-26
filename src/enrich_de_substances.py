"""
enrich_de_substances.py — one-time: translate BVL substance codes (wirknr) to names and cache
them into bvl_late_blight_DE.json under _wirkstoff_names, so downstream (KG, RAG docs) have
real active-substance names instead of codes.
Run:  python src/enrich_de_substances.py
"""
import json, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"

def fetch(table, limit=5000):
    url = f"{BASE}/{table}/?limit={limit}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r).get("items", [])

for fname in ["bvl_late_blight_DE.json"]:   # extend to scab/mildew later
    path = DATA / fname
    if not path.exists():
        print(f"skip {fname} (not found)"); continue
    de = json.load(open(path, encoding="utf-8"))
    # collect the wirknr codes actually used
    used = set()
    for rows in de.get("substances", {}).values():
        for r in rows:
            if r.get("wirknr"): used.add(str(r["wirknr"]))
    # build code->name from the wirkstoff table
    wk = fetch("wirkstoff")
    code2name = {str(w.get("wirknr")): w.get("wirkstoffname") for w in wk if w.get("wirknr")}
    resolved = {c: code2name.get(c, None) for c in used}
    missing = [c for c, n in resolved.items() if not n]
    de["_wirkstoff_names"] = {c: n for c, n in resolved.items() if n}
    json.dump(de, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{fname}: cached {len(de['_wirkstoff_names'])}/{len(used)} substance names"
          + (f"  (missing codes: {missing})" if missing else ""))