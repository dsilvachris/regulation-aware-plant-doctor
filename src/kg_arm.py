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
        _graph.parse(str(DATA / "kg_all.ttl"), format="turtle")
    return _graph

def _run(sparql, **params):
    rows = _g().query(sparql, initNs={"ex": EX})
    return [tuple(str(x) for x in row) for row in rows]

# --- parameterised query templates, keyed by benchmark category ---
# Params available: country ('DE'/'NO'), substance, product, disease (resource key or None=all diseases).
# With the combined 3-disease graph, most queries take a `disease` filter (e.g. 'late_blight',
# 'apple_scab', 'powdery_mildew'); omitting it queries across all diseases (used by cross-disease Qs).

def _disease_clause(disease, auth_var="?a"):
    return f"{auth_var} ex:forDisease res:{disease} ." if disease else ""

RES_PREFIX = 'PREFIX res: <http://plant-regkg.org/resource/>\n'

def q_factual(disease=None, **p):
    # cat 1 — disease facts (pathogen, EPPO). If disease given, return that disease's pathogen.
    filt = f'res:{disease} ex:causedBy ?path .' if disease else '?d a ex:Disease ; ex:causedBy ?path .'
    rows = _run(RES_PREFIX + f"""SELECT ?plabel ?eppo WHERE {{
        {filt} ?path rdfs:label ?plabel ; ex:eppoCode ?eppo . }}""")
    return {"disease": disease, "pathogen": rows[0][0], "eppo": rows[0][1]} if rows else {"disease": disease}

def q_products_in_country(country, disease=None, **p):
    rows = _run(RES_PREFIX + f"""SELECT DISTINCT ?name WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . {_disease_clause(disease)}
        ?c rdfs:label "{country}" . ?prod rdfs:label ?name . }} ORDER BY ?name""")
    return {"country": country, "disease": disease, "count": len(rows), "products": [r[0] for r in rows]}

def q_substances_in_country(country, disease=None, **p):
    rows = _run(RES_PREFIX + f"""SELECT DISTINCT ?sub WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . {_disease_clause(disease)}
        ?c rdfs:label "{country}" . ?prod ex:containsSubstance ?s . ?s rdfs:label ?sub . }} ORDER BY ?sub""")
    return {"country": country, "disease": disease, "substances": [r[0] for r in rows]}

def q_is_substance_authorised(country, substance, disease=None, **p):
    rows = _run(RES_PREFIX + f"""SELECT ?prod WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?pr . {_disease_clause(disease)}
        ?c rdfs:label "{country}" . ?pr ex:containsSubstance ?s . ?s rdfs:label ?sub . ?pr rdfs:label ?prod .
        FILTER(CONTAINS(LCASE(?sub), LCASE("{substance}"))) }}""")
    return {"country": country, "substance": substance, "disease": disease,
            "authorised": len(rows) > 0, "products": [r[0] for r in rows]}

def q_substances_de_only(disease=None, **p):
    dcl = _disease_clause(disease); dcl2 = _disease_clause(disease, "?a2")
    rows = _run(RES_PREFIX + f"""SELECT DISTINCT ?sub WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?cde ; ex:hasProduct ?p . ?cde rdfs:label "DE" . {dcl}
        ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
        FILTER NOT EXISTS {{
          ?a2 a ex:Authorisation ; ex:inCountry ?cno ; ex:hasProduct ?p2 . ?cno rdfs:label "NO" . {dcl2}
          ?p2 ex:containsSubstance ?s2 . ?s2 rdfs:label ?sub2 . FILTER(?sub2 = ?sub) }} }} ORDER BY ?sub""")
    return {"disease": disease, "de_only_substances": [r[0] for r in rows], "count": len(rows)}

def q_divergence_counts(disease=None, **p):
    de = q_products_in_country("DE", disease); no = q_products_in_country("NO", disease)
    return {"disease": disease, "DE_count": de["count"], "NO_count": no["count"]}

def q_substance_multi_disease(**p):
    # NEW cross-disease query (only possible in the combined graph): substances used vs >1 disease
    rows = _run(RES_PREFIX + """SELECT ?sub (COUNT(DISTINCT ?d) AS ?nd) WHERE {
        ?a a ex:Authorisation ; ex:forDisease ?d ; ex:hasProduct ?p .
        ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
    } GROUP BY ?sub HAVING (COUNT(DISTINCT ?d) > 1) ORDER BY ?sub""")
    return {"multi_disease_substances": [r[0] for r in rows]}

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
    print("factual (late blight):", q_factual(disease="late_blight"))
    print("NO late-blight products:", q_products_in_country("NO", disease="late_blight"))
    print("NO apple-scab products:", q_products_in_country("NO", disease="apple_scab"))
    print("NO late-blight substances:", q_substances_in_country("NO", disease="late_blight"))
    print("fluazinam in NO late blight?:", q_is_substance_authorised("NO", "fluazinam", disease="late_blight"))
    print("DE-only late blight count:", q_substances_de_only(disease="late_blight")["count"])
    print("late-blight divergence:", q_divergence_counts(disease="late_blight"))
    print("apple-scab divergence:", q_divergence_counts(disease="apple_scab"))
    print("multi-disease substances:", q_substance_multi_disease())


# ---- additional templates for categories that lost to RAG in the first full run ----

def q_authority(country, **p):
    # region_specific — which authority regulates a country (was hallucinated when missing)
    rows = _run(f"""SELECT ?alabel WHERE {{
        ?auth a ex:Authority ; ex:inCountry ?c ; rdfs:label ?alabel . ?c rdfs:label "{country}" . }}""")
    return {"country": country, "authority": rows[0][0] if rows else None}

def q_products_with_substance(country, substance, disease=None, **p):
    # constraint — which products in a country contain a given substance
    rows = _run(RES_PREFIX + f"""SELECT DISTINCT ?name WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . {_disease_clause(disease)} ?c rdfs:label "{country}" .
        ?prod rdfs:label ?name ; ex:containsSubstance ?s . ?s rdfs:label ?sub .
        FILTER(CONTAINS(LCASE(?sub), LCASE("{substance}"))) }} ORDER BY ?name""")
    return {"country": country, "substance": substance, "disease": disease, "products": [r[0] for r in rows]}

def q_products_single_substance(country, disease=None, **p):
    # constraint — products in a country with exactly ONE active substance
    rows = _run(RES_PREFIX + f"""SELECT ?name (COUNT(DISTINCT ?s) AS ?n) WHERE {{
        ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?prod . {_disease_clause(disease)} ?c rdfs:label "{country}" .
        ?prod rdfs:label ?name ; ex:containsSubstance ?s .
    }} GROUP BY ?name""")
    singles = [r[0] for r in rows if r[1] == "1"]
    mixtures = [r[0] for r in rows if r[1] != "1"]
    return {"country": country, "disease": disease, "single_substance": singles, "mixtures": mixtures}

def q_substance_in_both(substance, disease=None, **p):
    # cross_border — is a substance authorised in BOTH countries (optionally for a disease)?
    de = q_is_substance_authorised("DE", substance, disease)["authorised"]
    no = q_is_substance_authorised("NO", substance, disease)["authorised"]
    return {"substance": substance, "disease": disease, "in_DE": de, "in_NO": no, "in_both": de and no}