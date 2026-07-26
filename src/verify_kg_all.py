"""verify_kg_all.py — sanity-check the combined 3-disease KG and show the cross-disease capability."""
from pathlib import Path
from rdflib import Graph, Namespace
EX = Namespace("http://plant-regkg.org/ontology#")
DATA = Path(__file__).resolve().parent.parent / "data"
g = Graph(); g.parse(str(DATA / "kg_all.ttl"), format="turtle")
print(f"Total triples: {len(g)}\n")

print("=== products per disease x country ===")
for r in g.query("""SELECT ?dl ?cc (COUNT(DISTINCT ?prod) AS ?n) WHERE {
  ?a a ex:Authorisation ; ex:forDisease ?d ; ex:inCountry ?c ; ex:hasProduct ?prod .
  ?d rdfs:label ?dl . ?c rdfs:label ?cc . } GROUP BY ?dl ?cc ORDER BY ?dl ?cc""", initNs={"ex": EX}):
    print(f"  {str(r[0]):28} {r[1]}  {r[2]}")

print("\n=== substances used against MORE THAN ONE disease (only visible in a combined graph) ===")
found = False
for r in g.query("""SELECT ?sub (COUNT(DISTINCT ?d) AS ?nd) WHERE {
  ?a a ex:Authorisation ; ex:forDisease ?d ; ex:hasProduct ?p .
  ?p ex:containsSubstance ?s . ?s rdfs:label ?sub .
} GROUP BY ?sub HAVING (COUNT(DISTINCT ?d) > 1) ORDER BY DESC(?nd) ?sub""", initNs={"ex": EX}):
    print(f"  {str(r[0]):28} used against {r[1]} diseases"); found = True
if not found:
    print("  (none — the three diseases share no active substance)")