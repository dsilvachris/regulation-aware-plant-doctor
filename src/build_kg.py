"""
build_kg.py — Phase 1: build the COMBINED 3-disease Knowledge Graph (RDFLib) AND the parallel
prose documents for the RAG arm, from the SAME Stage-4 data (data-parity).

Diseases: late blight (PHYTIN), apple scab (VENTIN), cucurbit powdery mildew (PODOXA).
Shared nodes (countries, authorities, and any active substance used across diseases) are single
nodes that link multiple diseases — the cross-disease structure a graph is for.

Schema (n-ary authorisation node, mirroring E-PHY's "Use"):
  Authorisation --hasProduct--> Product --containsSubstance--> ActiveSubstance
  Authorisation --targetsPathogen--> Pathogen (EPPO code) ; --forDisease--> Disease
  Authorisation --onCrop--> Crop ; --inCountry--> Country ; --regulatedBy--> Authority

Run:  python src/build_kg.py     Outputs: data/kg_all.ttl  and  data/rag_docs_all.json
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from substance_norm import canonical, is_known

EX   = Namespace("http://plant-regkg.org/ontology#")
RES  = Namespace("http://plant-regkg.org/resource/")
EPPO = Namespace("https://gd.eppo.int/taxon/")
AGRO = Namespace("http://aims.fao.org/aos/agrovoc/")

AUTHORITY = {"DE": "BVL (Federal Office of Consumer Protection and Food Safety)",
             "NO": "Mattilsynet (Norwegian Food Safety Authority)"}
AGROVOC = {"potato": "c_6377", "tomato": "c_7758"}   # illustrative; verify before citing

# --- disease config: EPPO code, pathogen, human label, DE file, NO key, default crop ---
DISEASES = {
    "late_blight":    {"eppo": "PHYTIN", "pathogen": "Phytophthora infestans", "label": "late blight",
                       "de_file": "bvl_late_blight_DE.json", "no_key": "late_blight_NO", "crop": "potato"},
    "apple_scab":     {"eppo": "VENTIN", "pathogen": "Venturia inaequalis", "label": "apple scab",
                       "de_file": "bvl_apple_scab_DE.json", "no_key": "apple_scab_NO", "crop": "apple"},
    "powdery_mildew": {"eppo": "PODOXA", "pathogen": "Podosphaera xanthii", "label": "cucurbit powdery mildew",
                       "de_file": "bvl_powdery_mildew_DE.json", "no_key": "powdery_mildew_NO", "crop": "cucurbit"},
}

def clean(s):
    return "".join(ch if ch.isalnum() else "_" for ch in str(s)).strip("_")

g = Graph()
for pfx, ns in [("ex",EX),("res",RES),("eppo",EPPO),("agrovoc",AGRO),("rdfs",RDFS)]:
    g.bind(pfx, ns)

# shared country + authority nodes (built once)
for cc, name in AUTHORITY.items():
    g.add((RES[cc], RDF.type, EX.Country)); g.add((RES[cc], RDFS.label, Literal(cc)))
    g.add((RES["authority_"+cc], RDF.type, EX.Authority))
    g.add((RES["authority_"+cc], RDFS.label, Literal(name)))
    g.add((RES["authority_"+cc], EX.inCountry, RES[cc]))

rag_docs = []
auth_counter = 0
warnings = []

def add_authorisation(dkey, dcfg, country, product_name, reg_id, substances, crop):
    global auth_counter
    auth_counter += 1
    patho = EPPO[dcfg["eppo"]]
    prod = RES["product_" + clean(reg_id or product_name)]
    g.add((prod, RDF.type, EX.Product)); g.add((prod, RDFS.label, Literal(product_name)))
    if reg_id: g.add((prod, EX.registrationId, Literal(str(reg_id))))
    for sub in substances:
        canon = canonical(sub)
        s_node = RES["substance_" + clean(canon)]     # canonical -> shared across diseases/countries
        g.add((s_node, RDF.type, EX.ActiveSubstance)); g.add((s_node, RDFS.label, Literal(canon)))
        if canonical(sub) != sub.lower().strip():
            g.add((s_node, EX.altLabel, Literal(sub)))
        if not is_known(sub):
            warnings.append(f"{dkey}/{country}: unknown substance {sub!r}")
        g.add((prod, EX.containsSubstance, s_node))
    a = RES[f"authorisation_{dkey}_{country}_{auth_counter}"]
    g.add((a, RDF.type, EX.Authorisation))
    g.add((a, EX.hasProduct, prod))
    g.add((a, EX.targetsPathogen, patho))
    g.add((a, EX.forDisease, RES[dkey]))
    g.add((a, EX.inCountry, RES[country]))
    g.add((a, EX.regulatedBy, RES["authority_"+country]))
    if crop:
        c_node = RES["crop_" + clean(crop)]
        g.add((c_node, RDF.type, EX.Crop)); g.add((c_node, RDFS.label, Literal(crop)))
        if crop.lower() in AGROVOC:
            g.add((c_node, EX.agrovocConcept, AGRO[AGROVOC[crop.lower()]]))
        g.add((a, EX.onCrop, c_node))
    subs = ", ".join(canonical(s) for s in substances) if substances else "unspecified active substance"
    crop_txt = f" on {crop}" if crop else ""
    rag_docs.append({
        "id": f"{dkey}_{country}_{auth_counter}", "country": country, "disease": dcfg["label"],
        "text": f"In {AUTHORITY[country]}, the product {product_name}"
                + (f" (registration {reg_id})" if reg_id else "")
                + f" is authorised against {dcfg['label']} ({dcfg['pathogen']}){crop_txt}. "
                + f"It contains {subs}."
    })

for dkey, dcfg in DISEASES.items():
    # disease + pathogen nodes
    patho = EPPO[dcfg["eppo"]]
    g.add((patho, RDF.type, EX.Pathogen)); g.add((patho, RDFS.label, Literal(dcfg["pathogen"])))
    g.add((patho, EX.eppoCode, Literal(dcfg["eppo"])))
    g.add((RES[dkey], RDF.type, EX.Disease)); g.add((RES[dkey], RDFS.label, Literal(dcfg["label"])))
    g.add((RES[dkey], EX.causedBy, patho))

    # Norway (manual data) — single file no_products.json with per-disease keys
    no = json.load(open(DATA / "no_products.json", encoding="utf-8"))
    n_no = 0
    for row in no.get(dcfg["no_key"], []):
        subs = [s.strip() for s in str(row.get("active_substance","")).replace("+",",").split(",") if s.strip()]
        add_authorisation(dkey, dcfg, "NO", row.get("product","?"), row.get("reg_nr"), subs,
                          row.get("crop", dcfg["crop"]))
        n_no += 1

    # Germany (BVL extract)
    de_path = DATA / dcfg["de_file"]
    n_de = 0
    if de_path.exists():
        de = json.load(open(de_path, encoding="utf-8"))
        names = de.get("_wirkstoff_names", {})
        for kennr, prod in de.get("products", {}).items():
            subs = [names.get(str(r.get("wirknr")), f"wirknr:{r.get('wirknr')}")
                    for r in de.get("substances", {}).get(kennr, [])]
            add_authorisation(dkey, dcfg, "DE", prod.get("mittelname", kennr), kennr, subs, dcfg["crop"])
            n_de += 1
    else:
        print(f"  [warn] {dcfg['de_file']} not found — run enrich for {dkey} first")
    print(f"{dcfg['label']}: DE {n_de}, NO {n_no}")

g.serialize(destination=str(DATA / "kg_all.ttl"), format="turtle")
json.dump({"_meta": {"diseases": [d["label"] for d in DISEASES.values()],
                     "source": "Stage-4 data (BVL + Mattilsynet)", "note": "combined 3-disease KG + parallel RAG docs (data-parity)"},
           "documents": rag_docs},
          open(DATA / "rag_docs_all.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\nKG triples: {len(g)}")
print(f"RAG docs:   {len(rag_docs)}")
print(f"Wrote data/kg_all.ttl and data/rag_docs_all.json")
if warnings:
    print(f"\n{len(warnings)} substance warnings:")
    for w in warnings[:20]: print("  " + w)
if any("wirknr:" in d["text"] for d in rag_docs):
    print("\nWARNING: some German substances are unresolved codes — run enrich_de_substances.py for all diseases first.")