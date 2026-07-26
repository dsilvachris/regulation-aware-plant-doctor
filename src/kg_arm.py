"""
kg_arm.py — Stage 5: the Knowledge Graph arm.

Deterministic, category-based query selection (the LLM NEVER writes SPARQL). Each benchmark
category maps to a parameterised SPARQL template. The graph returns verified facts; the LLM's
only job (in eval_pipeline.py) is to phrase those facts in natural language.

Workflow:  question(+category) -> template -> SPARQL -> verified facts -> (LLM phrases them)
"""
from pathlib import Path
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EX = Namespace("http://plant-regkg.org/ontology#")

_graph = None
def _g():
    global _graph
    if _graph is None:
        _graph = Graph()
        _graph.parse(str(DATA / "kg_late_blight.ttl"), format="turtle")
    return _graph

def _run(sparql, **params):
    rows = _g().query(sparql, initNs={"ex": EX})
    return [tuple(str(x) for x in row) for row in rows]

# --- parameterised query templates, keyed by benchmark category ---
# Params available: country ('DE'/'NO'), substance, product. Disease is fixed (late blight) in this KG.

def q_factual(**p):
    # cat 1 — disease facts (pathogen, EPPO). Control category.
    rows = _run("""SELECT ?plabel ?eppo WHERE {
        ?d a ex:Disease ; ex:causedBy ?path . ?path rdfs:label ?plabel ; ex:eppoCode ?eppo . }""")
    return {"pathogen": rows[0][0], "eppo": rows[0][1]} if rows else {}

def q_products_in_country(country, **p):
    # cats 2/6 — products (and count) authorised in a country
    rows = _run(f"""SELECT DISTINCT ?name WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod .
        ?c rdfs:label "{country}" . ?prod rdfs:label ?name . }} ORDER BY ?name""")
    return {"country": country, "count": len(rows), "products": [r[0] for r in rows]}

def q_substances_in_country(country, **p):
    # cat 3 — active substances authorised in a country
    rows = _run(f"""SELECT DISTINCT ?sub WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod .
        ?c rdfs:label "{country}" . ?prod ex:containsSubstance ?s . ?s rdfs:label ?sub . }} ORDER BY ?sub""")
    return {"country": country, "substances": [r[0] for r in rows]}

def q_is_substance_authorised(country, substance, **p):
    # cat 5 — negative/absence: is a substance authorised in a country? (empty = definitive NO)
    rows = _run(f"""SELECT ?prod WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?pr .
        ?c rdfs:label "{country}" . ?pr ex:containsSubstance ?s . ?s rdfs:label ?sub . ?pr rdfs:label ?prod .
        FILTER(CONTAINS(LCASE(?sub), LCASE("{substance}"))) }}""")
    return {"country": country, "substance": substance,
            "authorised": len(rows) > 0, "products": [r[0] for r in rows]}

def q_substances_de_only(**p):
    # cat 6 — divergence: substances in DE but not NO
    rows = _run("""SELECT DISTINCT ?sub WHERE {
        ?a a ex:Authorisation ; ex:inCountry ?cde ; ex:hasProduct ?p . ?cde rdfs:label "DE" .
        ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
        FILTER NOT EXISTS {
          ?a2 a ex:Authorisation ; ex:inCountry ?cno ; ex:hasProduct ?p2 . ?cno rdfs:label "NO" .
          ?p2 ex:containsSubstance ?s2 . ?s2 rdfs:label ?sub2 . FILTER(?sub2 = ?sub) } } ORDER BY ?sub""")
    return {"de_only_substances": [r[0] for r in rows], "count": len(rows)}

def q_divergence_counts(**p):
    # cat 6 — product counts per country side by side
    de = q_products_in_country("DE"); no = q_products_in_country("NO")
    return {"DE_count": de["count"], "NO_count": no["count"]}

# map benchmark category -> the query function(s) it uses
CATEGORY_QUERY = {
    "factual":          q_factual,
    "region_specific":  q_products_in_country,
    "multi_hop":        q_substances_in_country,
    "constraint":       q_substances_in_country,
    "negative":         q_is_substance_authorised,
    "cross_border":     q_divergence_counts,
}

def kg_facts(category, **params):
    """Return verified facts for a benchmark question, chosen deterministically by category."""
    fn = CATEGORY_QUERY.get(category)
    if fn is None:
        return {"error": f"no query template for category '{category}'"}
    return fn(**params)

if __name__ == "__main__":
    print("factual:", q_factual())
    print("NO products:", q_products_in_country("NO"))
    print("NO substances:", q_substances_in_country("NO"))
    print("fluazinam in NO?:", q_is_substance_authorised("NO", "fluazinam"))
    print("DE-only count:", q_substances_de_only()["count"])
    print("divergence counts:", q_divergence_counts())


# ---- additional templates for categories that lost to RAG in the first full run ----

def q_authority(country, **p):
    # region_specific — which authority regulates a country (was hallucinated when missing)
    rows = _run(f"""SELECT ?alabel WHERE {{
        ?auth a ex:Authority ; ex:inCountry ?c ; rdfs:label ?alabel . ?c rdfs:label "{country}" . }}""")
    return {"country": country, "authority": rows[0][0] if rows else None}

def q_products_with_substance(country, substance, **p):
    # constraint — which products in a country contain a given substance
    rows = _run(f"""SELECT DISTINCT ?name WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . ?c rdfs:label "{country}" .
        ?prod rdfs:label ?name ; ex:containsSubstance ?s . ?s rdfs:label ?sub .
        FILTER(CONTAINS(LCASE(?sub), LCASE("{substance}"))) }} ORDER BY ?name""")
    return {"country": country, "substance": substance, "products": [r[0] for r in rows]}

def q_products_single_substance(country, **p):
    # constraint — products in a country with exactly ONE active substance
    rows = _run(f"""SELECT ?name (COUNT(DISTINCT ?s) AS ?n) WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . ?c rdfs:label "{country}" .
        ?prod rdfs:label ?name ; ex:containsSubstance ?s .
    }} GROUP BY ?name""")
    singles = [r[0] for r in rows if r[1] == "1"]
    mixtures = [r[0] for r in rows if r[1] != "1"]
    return {"country": country, "single_substance": singles, "mixtures": mixtures}

def q_substance_in_both(substance, **p):
    # cross_border — is a substance authorised in BOTH countries?
    de = q_is_substance_authorised("DE", substance)["authorised"]
    no = q_is_substance_authorised("NO", substance)["authorised"]
    return {"substance": substance, "in_DE": de, "in_NO": no, "in_both": de and no}