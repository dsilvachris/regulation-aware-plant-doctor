"""probe_awg_kultur.py — is there an awg->crop link table, and do OUR crops sit in meaningful groups?"""
import json, urllib.request, urllib.parse
BASE = "https://psm-api.bvl.bund.de/ords/psm/api-v1"
def fetch(table, q=None, limit=5):
    url = f"{BASE}/{table}/?limit={limit}"
    if q: url += "&q=" + urllib.parse.quote(json.dumps(q))
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r).get("items", []), True
    except Exception:
        return [], False

print("=== probe for the awg->crop link table ===")
for t in ["awg_kultur", "awg_kultur_zul", "kultur", "awgkultur", "anwendung_kultur"]:
    rows, ok = fetch(t, limit=2)
    print(f"  {t}/: {'EXISTS keys='+str(list(rows[0].keys())) if ok and rows else ('EXISTS empty' if ok else '404')}")

print("\n=== find the crop code for potato + which group(s) it belongs to ===")
# potato in German = Kartoffel; find its crop code via kode table
rows, ok = fetch("kode", {"kodetext": {"$instr": "Kartoffel"}}, limit=10)
potato_codes = sorted({r["kode"] for r in rows if r.get("sprache") in ("DE","GB","VA")})
print(f"  potato (Kartoffel) codes: {potato_codes}")
for pc in potato_codes[:3]:
    grp, ok = fetch("kultur_gruppe", {"kultur": pc}, limit=10)
    as_parent, ok2 = fetch("kultur_gruppe", {"kultur_gruppe": pc}, limit=10)
    print(f"  {pc}: appears as CHILD in groups {[g['kultur_gruppe'] for g in grp]}; "
          f"as PARENT of {len(as_parent)} children")