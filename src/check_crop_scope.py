"""check_crop_scope.py — are the awg_ids in our files disease-specific, or all uses of the products?"""
import json
from pathlib import Path
DATA = Path(__file__).resolve().parent.parent / "data"

for fname, code in [("bvl_apple_scab_DE.json","VENTIN"), ("bvl_powdery_mildew_DE.json","PODOXA")]:
    de = json.load(open(DATA/fname, encoding="utf-8"))
    uses = de.get("uses", [])
    awg_ids = {u.get("awg_id") for u in uses if u.get("awg_id")}
    crops = de.get("_crops", {})
    print(f"=== {fname} (pest {code}) ===")
    print(f"  uses: {len(uses)}, distinct awg_ids: {len(awg_ids)}")
    # how many crops per awg_id? if each awg_id has 1-2 crops, they're use-specific (good).
    # if some awg_id has 10+ crops, that awg_id spans many crops (still could be right).
    sizes = sorted((len(v) for v in crops.values()), reverse=True)
    print(f"  crops-per-awg_id (top): {sizes[:10]}")
    # show a couple awg_id -> crops
    for awg_id in list(awg_ids)[:4]:
        print(f"    {awg_id}: {crops.get(awg_id, [])}")