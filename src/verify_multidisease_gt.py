"""verify_multidisease_gt.py — resolve the VERIFY flags in the expanded benchmark against kg_all.ttl."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kg_arm as kg

def show(label, val):
    print(f"  {label}: {val}")

print("=== APPLE SCAB ===")
show("DE substances", kg.q_substances_in_country("DE", disease="apple_scab")["substances"])
show("NO substances", kg.q_substances_in_country("NO", disease="apple_scab")["substances"])
show("as_c02 German products with sulfur", kg.q_products_with_substance("DE","sulfur",disease="apple_scab")["products"])
show("as_d02 dithianon in both?", kg.q_substance_in_both("dithianon", disease="apple_scab"))
print()

print("=== POWDERY MILDEW ===")
show("DE substances", kg.q_substances_in_country("DE", disease="powdery_mildew")["substances"])
show("NO substances", kg.q_substances_in_country("NO", disease="powdery_mildew")["substances"])
show("pm_n02 sulfur in NO mildew?", kg.q_is_substance_authorised("NO","sulfur",disease="powdery_mildew")["authorised"])
show("pm_d02 proquinazid in both?", kg.q_substance_in_both("proquinazid", disease="powdery_mildew"))
print()

print("=== CROSS-DISEASE ===")
show("xd_01 multi-disease substances", kg.q_substance_multi_disease()["multi_disease_substances"])