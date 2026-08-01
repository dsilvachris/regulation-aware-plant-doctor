"""
build_kg_phase4.py — Phase 4, Step 3: build the pharma Knowledge Graph (RDFLib) AND the parallel prose
documents for the RAG arm, from the SAME Step-2 sourced data (data-parity, same principle as Phase 1's
build_kg.py).

Domain: FDA (US) vs EMA (EU) drug authorisation, 8-substance verified roster
(docs/Phase4_Step0_Feasibility.md): aducanumab, lecanemab, donanemab (Alzheimer's, ATC N06D);
niraparib, isatuximab, epcoritamab, dostarlimab, melphalan flufenamide (oncology, ATC L01).

Schema (n-ary authorisation node, mirroring Phase 1's Authorisation pattern):
  Authorisation --forSubstance--> Substance ; --inRegion--> Region ; --regulatedBy--> Authority
  Authorisation --hasStatus--> literal ; --hasDecisionDate--> literal (where known)
  Substance --hasAtcCode--> literal (EMA's atc_code_human — authoritative; RxClass ATC is NOT used for
    hierarchy edges, since it showed drift on 2/8 substances vs EMA's own classification, see Step 2 notes)
  Substance --inAtcClass--> AtcClass (most specific class matching its own code)
  AtcClass --broader--> AtcClass (chain up through ATC's levels: anatomical -> therapeutic ->
    pharmacological -> chemical -> substance, derived by systematic prefix-slicing of the ATC code string)

Applies the two lessons already paid for in this project, from day one:
  1. Every verbalised fact names its actual substance/region explicitly — never a hardcoded placeholder
     (the exact bug class in Correction_KG_Disease_Name_Bug.md).
  2. Category-label text is kept structurally separate from entity/substance lists in the RAG prose
     (the exact ambiguity fixed in Phase3_Step2_FusionArm.md's multi_disease template).

Run: python src/build_kg_phase4.py   Outputs: data/kg_phase4.ttl and data/rag_docs_phase4.json
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

EX = Namespace("http://pharma-regkg.org/ontology#")
RES = Namespace("http://pharma-regkg.org/resource/")

AUTHORITY = {"US": "FDA (U.S. Food and Drug Administration)", "EU": "EMA (European Medicines Agency)"}

# ATC level boundaries by character position (WHO ATC 5-level structure): anatomical(1) / therapeutic(3)
# / pharmacological(4) / chemical(5) / substance(7). A code shorter than a boundary simply has no node at
# that level yet — this is real (e.g. aducanumab's EMA code is only "N07", 3 chars: therapeutic level
# only, reflecting its incomplete/withdrawn review, not a data error — see Phase4 Step 2 notes).
ATC_LEVEL_LENGTHS = [1, 3, 4, 5, 7]


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s).strip("_")


def atc_chain(code):
    """Returns the ATC codes present in this code's chain, most specific to least, e.g. 'L01FF07' ->
    ['L01FF07','L01FF','L01F','L01','L']. Stops at whatever length the actual code has."""
    if not code:
        return []
    chain = [code[:length] for length in ATC_LEVEL_LENGTHS if len(code) >= length]
    return sorted(set(chain), key=len, reverse=True)


if __name__ == "__main__":
    fda_data = json.load(open(DATA / "fda_drugs_US.json", encoding="utf-8"))
    ema_data = json.load(open(DATA / "ema_medicines_EU.json", encoding="utf-8"))

    g = Graph()
    g.bind("ex", EX)
    g.bind("res", RES)

    rag_docs = []
    auth_counter = 0

    for sub_name in fda_data:
        sub_node = RES[slug(sub_name)]
        g.add((sub_node, RDF.type, EX.Substance))
        g.add((sub_node, RDFS.label, Literal(sub_name)))

        # --- ATC classification: EMA's native atc_code_human is authoritative (see module docstring) ---
        ema_records = ema_data[sub_name]["records"]
        atc_codes = sorted({m["atc_code_human"] for m in ema_records if m.get("atc_code_human")})
        primary_atc = max(atc_codes, key=len) if atc_codes else None  # most specific available
        if primary_atc:
            g.add((sub_node, EX.hasAtcCode, Literal(primary_atc)))
            chain = sorted({c for code in atc_codes for c in atc_chain(code)}, key=len, reverse=True)
            prev = None
            for code in chain:
                class_node = RES[f"atc_{slug(code)}"]
                g.add((class_node, RDF.type, EX.AtcClass))
                g.add((class_node, RDFS.label, Literal(code)))
                if prev is not None:
                    g.add((prev, EX.broader, class_node))
                prev = class_node
            most_specific = RES[f"atc_{slug(chain[0])}"]
            g.add((sub_node, EX.inAtcClass, most_specific))

        # --- US (FDA) authorisation ---
        fda_records = fda_data[sub_name]["records"]
        auth_counter += 1
        us_auth = RES[f"auth_{auth_counter}"]
        g.add((us_auth, RDF.type, EX.Authorisation))
        g.add((us_auth, EX.forSubstance, sub_node))
        g.add((us_auth, EX.inRegion, Literal("US")))
        g.add((us_auth, EX.regulatedBy, Literal(AUTHORITY["US"])))
        if fda_records:
            approved = any(sub.get("submission_status") == "AP"
                            for app in fda_records for sub in app.get("submissions", []))
            status = "Approved" if approved else "Not approved"
            # melphalan flufenamide: FDA formally withdrew approval Feb 2024; absent from current openFDA
            # index (see docs/Phase4_Step0_Feasibility.md's manual-override note) - encoded explicitly here
            # since openFDA's own data cannot express "was approved, later withdrawn" cleanly.
            if sub_name == "melphalan flufenamide":
                status = "Approved, then withdrawn (February 2024)"
            g.add((us_auth, EX.hasStatus, Literal(status)))
        else:
            status = "No current FDA record" if sub_name != "melphalan flufenamide" \
                else "Approved (2021), then withdrawn (February 2024) — no longer in the current FDA index"
            g.add((us_auth, EX.hasStatus, Literal(status)))

        # --- EU (EMA) authorisation ---
        auth_counter += 1
        eu_auth = RES[f"auth_{auth_counter}"]
        g.add((eu_auth, RDF.type, EX.Authorisation))
        g.add((eu_auth, EX.forSubstance, sub_node))
        g.add((eu_auth, EX.inRegion, Literal("EU")))
        g.add((eu_auth, EX.regulatedBy, Literal(AUTHORITY["EU"])))
        eu_statuses = sorted({m.get("medicine_status", "") for m in ema_records if m.get("medicine_status")})
        eu_status = eu_statuses[0] if eu_statuses else "No EMA centralised-procedure record"
        g.add((eu_auth, EX.hasStatus, Literal(eu_status)))
        orphan = any(m.get("orphan_medicine") == "Yes" for m in ema_records)
        g.add((sub_node, EX.hasOrphanDesignation, Literal(orphan)))

        # --- Parallel RAG prose (data parity: same facts, prose form; entity/region names always
        # explicit, category labels never adjacent to entity lists - lessons from Correction_KG_Disease_
        # Name_Bug.md and Phase3_Step2_FusionArm.md applied from the start) ---
        atc_prose = f" Its ATC classification is {primary_atc}." if primary_atc else ""
        orphan_prose = f" It holds an EMA orphan-medicine designation." if orphan else ""
        # Data-parity fix: the KG states explicitly whether EU authorisation went through EMA's
        # centralised procedure (q_is_centralised in kg_arm_phase4.py) - the RAG prose must state the
        # same fact in words, or RAG can never possibly answer a question about it (not a reasoning
        # gap, a missing-fact gap - confirmed via r2's graded results: RAG correctly declined every run
        # because the word "centralised" never appeared anywhere in its documents).
        centralised_prose = (f" This EU authorisation was granted via the EMA's centralised procedure."
                              if eu_status not in ("No EMA centralised-procedure record", "") else "")
        rag_docs.append({
            "id": slug(sub_name),
            "substance": sub_name,
            "text": (f"{sub_name.capitalize()}: US status ({AUTHORITY['US']}) is '{status}'. "
                     f"EU status ({AUTHORITY['EU']}) is '{eu_status}'.{centralised_prose}"
                     f"{atc_prose}{orphan_prose}"),
        })

    g.serialize(destination=str(DATA / "kg_phase4.ttl"), format="turtle")
    json.dump({"documents": rag_docs}, open(DATA / "rag_docs_phase4.json", "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

    print(f"Wrote data/kg_phase4.ttl ({len(g)} triples)")
    print(f"Wrote data/rag_docs_phase4.json ({len(rag_docs)} documents)")
    print("\nSample RAG docs:")
    for doc in rag_docs[:3]:
        print(f"  - {doc['text']}")