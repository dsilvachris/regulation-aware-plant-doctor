"""
build_kg.py — Stage 3: build the late-blight Knowledge Graph (RDFLib) AND the parallel
prose documents for the RAG arm, from the SAME Stage-4 data (data-parity).

Schema (n-ary authorisation via an intermediate node, mirroring E-PHY's "Use"):
  Authorisation --hasProduct--> Product --containsSubstance--> ActiveSubstance
  Authorisation --targetsPathogen--> Pathogen (EPPO code)
  Authorisation --onCrop--> Crop (AGROVOC where known)
  Authorisation --inCountry--> Country
  Product --regulatedBy--> Authority ; Authority --inCountry--> Country

Identifier reuse: Pathogen uses EPPO codes (e.g. PHYTIN); Crop maps to AGROVOC URIs where known.
Run:  python src/build_kg.py     Outputs: data/kg_late_blight.ttl  and  data/rag_docs_late_blight.json
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

EX    = Namespace("http://plant-regkg.org/ontology#")   # local ontology terms
RES   = Namespace("http://plant-regkg.org/resource/")   # local resources
EPPO  = Namespace("https://gd.eppo.int/taxon/")          # EPPO codes as identifiers
AGRO  = Namespace("http://aims.fao.org/aos/agrovoc/")    # AGROVOC concept URIs

# --- known identifier reuse (verify/extend as needed) ---
EPPO_CODES = {"late blight": "PHYTIN"}          # pathogen Phytophthora infestans
AGROVOC = {                                       # crop -> AGROVOC concept id (illustrative; verify URIs)
    "potato": "c_6377", "tomato": "c_7758",
}
AUTHORITY = {"DE": "BVL (Federal Office of Consumer Protection and Food Safety)",
             "NO": "Mattilsynet (Norwegian Food Safety Authority)"}

def clean(s):
    return "".join(ch if ch.isalnum() else "_" for ch in str(s)).strip("_")

g = Graph()
g.bind("ex", EX); g.bind("res", RES); g.bind("eppo", EPPO); g.bind("agrovoc", AGRO)
g.bind("rdfs", RDFS)

# shared nodes: pathogen + countries + authorities
patho = EPPO["PHYTIN"]
g.add((patho, RDF.type, EX.Pathogen)); g.add((patho, RDFS.label, Literal("Phytophthora infestans")))
g.add((patho, EX.eppoCode, Literal("PHYTIN")))
disease = RES["late_blight"]
g.add((disease, RDF.type, EX.Disease)); g.add((disease, RDFS.label, Literal("late blight")))
g.add((disease, EX.causedBy, patho))

for cc, name in AUTHORITY.items():
    country = RES[cc]; auth = RES["authority_"+cc]
    g.add((country, RDF.type, EX.Country)); g.add((country, RDFS.label, Literal(cc)))
    g.add((auth, RDF.type, EX.Authority)); g.add((auth, RDFS.label, Literal(name)))
    g.add((auth, EX.inCountry, country))

rag_docs = []   # parallel prose for the RAG arm (SAME facts, different representation)
auth_counter = 0

def add_authorisation(country, product_name, reg_id, substances, crop):
    """Add one authorisation (n-ary node) + product + substances to the graph, and a prose doc."""
    global auth_counter
    auth_counter += 1
    prod = RES["product_"+clean(reg_id or product_name)]
    g.add((prod, RDF.type, EX.Product)); g.add((prod, RDFS.label, Literal(product_name)))
    if reg_id: g.add((prod, EX.registrationId, Literal(str(reg_id))))
    for sub in substances:
        s_node = RES["substance_"+clean(sub)]
        g.add((s_node, RDF.type, EX.ActiveSubstance)); g.add((s_node, RDFS.label, Literal(sub)))
        g.add((prod, EX.containsSubstance, s_node))
    a = RES[f"authorisation_{country}_{auth_counter}"]
    g.add((a, RDF.type, EX.Authorisation))
    g.add((a, EX.hasProduct, prod))
    g.add((a, EX.targetsPathogen, patho))
    g.add((a, EX.inCountry, RES[country]))
    g.add((a, EX.regulatedBy, RES["authority_"+country]))
    if crop:
        c_node = RES["crop_"+clean(crop)]
        g.add((c_node, RDF.type, EX.Crop)); g.add((c_node, RDFS.label, Literal(crop)))
        if crop.lower() in AGROVOC:
            g.add((c_node, EX.agrovocConcept, AGRO[AGROVOC[crop.lower()]]))
        g.add((a, EX.onCrop, c_node))
    # parallel prose doc (identical facts)
    subs = ", ".join(substances) if substances else "unspecified active substance"
    crop_txt = f" on {crop}" if crop else ""
    rag_docs.append({
        "id": f"auth_{country}_{auth_counter}",
        "country": country,
        "text": f"In {AUTHORITY[country]}, the product {product_name}"
                + (f" (registration {reg_id})" if reg_id else "")
                + f" is authorised against late blight (Phytophthora infestans){crop_txt}. "
                + f"It contains {subs}."
    })

# --- load NORWAY (from the manual template) ---
no = json.load(open(DATA / "no_products.json", encoding="utf-8"))
for row in no.get("late_blight_NO", []):
    subs = [s.strip() for s in str(row.get("active_substance","")).replace("+",",").split(",") if s.strip()]
    add_authorisation("NO", row.get("product","?"), row.get("reg_nr"), subs, row.get("crop","potato"))

print(f"Norway: {len(no.get('late_blight_NO', []))} authorisations added")

# --- load GERMANY (from the BVL extract) : product -> substances via the substance code map ---
de = json.load(open(DATA / "bvl_late_blight_DE.json", encoding="utf-8"))
products = de.get("products", {})
substances_by_kennr = de.get("substances", {})
# NOTE: German substances are stored as codes (wirknr). For a faithful KG we need names.
# This script expects a translated map; if not present, it records the code and flags it.
code2name = de.get("_wirkstoff_names", {})   # optional: {wirknr: name} if you cached it
n_de = 0
for kennr, prod in products.items():
    name = prod.get("mittelname", kennr)
    subs = []
    for row in substances_by_kennr.get(kennr, []):
        wirknr = str(row.get("wirknr",""))
        subs.append(code2name.get(wirknr, f"wirknr:{wirknr}"))
    add_authorisation("DE", name, kennr, subs, "potato")   # crop simplified; refine from awg kultur later
    n_de += 1
print(f"Germany: {n_de} authorisations added")

# --- write outputs ---
g.serialize(destination=str(DATA / "kg_late_blight.ttl"), format="turtle")
json.dump({"_meta": {"disease": "late blight", "source": "Stage-4 data (BVL + Mattilsynet)",
                      "note": "prose rendering of the SAME facts as the KG, for the RAG arm (data-parity)"},
           "documents": rag_docs},
          open(DATA / "rag_docs_late_blight.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\nKG triples: {len(g)}")
print(f"RAG docs:   {len(rag_docs)}")
print(f"Wrote data/kg_late_blight.ttl and data/rag_docs_late_blight.json")
if any('wirknr:' in d['text'] for d in rag_docs):
    print("\nWARNING: German substances are unresolved codes (wirknr:...). Cache a {wirknr:name} map")
    print("into bvl_late_blight_DE.json['_wirkstoff_names'] (from verify_benchmark_gt.py) and rerun.")