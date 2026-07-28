"""
query_kg.py — sanity-check the late-blight KG by running real benchmark questions against it
with DETERMINISTIC SPARQL (the LLM never writes these queries — Stage 5 architectural principle).
Run:  python src/query_kg.py
"""
from pathlib import Path
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EX = Namespace("http://plant-regkg.org/ontology#")

g = Graph(); g.parse(str(DATA / "kg_all.ttl"), format="turtle")
print(f"Loaded {len(g)} triples\n")

def q(title, sparql):
    print(f"--- {title} ---")
    for row in g.query(sparql, initNs={"ex": EX}):
        print("   " + " | ".join(str(x) for x in row))
    print()

# category 6 (d01): how many late-blight products per country?
q("Products per country (d01: DE vs NO)", """
  SELECT ?cc (COUNT(DISTINCT ?prod) AS ?n) WHERE {
    ?a a ex:Authorisation ; ex:hasProduct ?prod ; ex:inCountry ?c .
    ?c rdfs:label ?cc .
  } GROUP BY ?cc ORDER BY DESC(?n)
""")

# category 3 (m01): active substances in Norway's late-blight products
q("Active substances authorised in Norway (m01)", """
  SELECT DISTINCT ?sub WHERE {
    ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?p .
    ?c rdfs:label "NO" .
    ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
  } ORDER BY ?sub
""")

# category 5 (n02): is fluazinam authorised in Norway? (should be empty = definitive NO)
q("Is fluazinam authorised in NO? (n02 — expect EMPTY = 'no')", """
  SELECT ?p WHERE {
    ?a a ex:Authorisation ; ex:inCountry ?c ; ex:hasProduct ?p .
    ?c rdfs:label "NO" .
    ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
    FILTER(CONTAINS(LCASE(?sub), "fluazinam"))
  }
""")

# category 6 (d06): active substances in DE but NOT in NO
q("Substances authorised in DE but NOT in NO (d06)", """
  SELECT DISTINCT ?sub WHERE {
    ?a a ex:Authorisation ; ex:inCountry ?cde ; ex:hasProduct ?p .
    ?cde rdfs:label "DE" .
    ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
    FILTER NOT EXISTS {
      ?a2 a ex:Authorisation ; ex:inCountry ?cno ; ex:hasProduct ?p2 .
      ?cno rdfs:label "NO" .
      ?p2 ex:containsSubstance ?s2 . ?s2 rdfs:label ?sub2 .
      FILTER(?sub2 = ?sub)
    }
  } ORDER BY ?sub
""")