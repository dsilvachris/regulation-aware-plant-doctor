"""
kg_arm_phase4.py — Phase 4, Step 4: deterministic query layer for the pharma KG (kg_phase4.ttl).

Same principle as Phase 1's kg_arm.py: the LLM never writes queries. Every benchmark question maps to
exactly one of these Python functions, called with parameters derived directly from the question's own
wording (never from any answer). All queries operate on real, verified data (docs/Phase4_Step0_Feasibility.md).

Run: python src/kg_arm_phase4.py   -> self-test against the pre-registered benchmark ground truth
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EX = Namespace("http://pharma-regkg.org/ontology#")

_graph = None


def _g():
    global _graph
    if _graph is None:
        _graph = Graph()
        _graph.parse(str(DATA / "kg_phase4.ttl"), format="turtle")
    return _graph


def _node_for(substance):
    g = _g()
    for s, p, o in g.triples((None, EX.hasAtcCode, None)):
        if s.split("/")[-1] == substance.replace(" ", "_"):
            return s
    return None


def _atc_chain(substance):
    g = _g()
    node = _node_for(substance)
    if node is None:
        return []
    cls = list(g.objects(node, EX.inAtcClass))
    if not cls:
        return []
    chain = [cls[0]]
    cur = cls[0]
    while True:
        nxt = list(g.objects(cur, EX.broader))
        if not nxt:
            break
        chain.append(nxt[0])
        cur = nxt[0]
    return [c.split("/")[-1] for c in chain]  # most specific first, e.g. atc_L01FF07 ... atc_L


def q_atc_code(substance, **p):
    """f1-f3: What is the ATC code for X?"""
    g = _g()
    node = _node_for(substance)
    code = list(g.objects(node, EX.hasAtcCode))[0] if node else None
    return {"substance": substance, "atc_code": str(code) if code else None}


def q_regulator(substance, region, **p):
    """r1: Which agency approved/authorised X in region Y?"""
    g = _g()
    node = _node_for(substance)
    for auth, _, sub in g.triples((None, EX.forSubstance, node)):
        if str(list(g.objects(auth, EX.inRegion))[0]) == region:
            reg = list(g.objects(auth, EX.regulatedBy))[0]
            return {"substance": substance, "region": region, "regulator": str(reg)}
    return {"substance": substance, "region": region, "regulator": None}


def q_is_centralised(substance, **p):
    """r2: Is X authorised via EMA's centralised procedure (vs national only)?
    True for every substance in this roster BY CONSTRUCTION (Step 0 required centralised-eligible
    candidates only) - this question type is deterministic but not very discriminating on this roster;
    flagged in docs/Phase4_Step0_Feasibility.md's scope note, not hidden."""
    g = _g()
    node = _node_for(substance)
    for auth, _, sub in g.triples((None, EX.forSubstance, node)):
        if str(list(g.objects(auth, EX.inRegion))[0]) == "EU":
            reg = list(g.objects(auth, EX.regulatedBy))[0]
            return {"substance": substance, "centralised": "EMA" in str(reg)}
    return {"substance": substance, "centralised": False}


def q_substances_in_atc_subclass(candidates, prefix, **p):
    """m1: Which of [candidates] fall under ATC prefix X (e.g. 'L01F')?"""
    matches = []
    for sub in candidates:
        g = _g()
        node = _node_for(sub)
        code = list(g.objects(node, EX.hasAtcCode))[0] if node else None
        if code and str(code).startswith(prefix):
            matches.append(sub)
    return {"candidates": candidates, "atc_prefix": prefix, "matches": matches}


def q_orphan_substances(candidates, **p):
    """c1: Which of [candidates] hold EMA orphan-medicine designation?"""
    g = _g()
    matches = []
    for sub in candidates:
        node = _node_for(sub)
        orphan = list(g.objects(node, EX.hasOrphanDesignation))
        if orphan and str(orphan[0]).lower() == "true":
            matches.append(sub)
    return {"candidates": candidates, "matches": matches}


def q_current_status(substance, region, **p):
    """n1, n2: What is X's current authorisation status in region Y?"""
    g = _g()
    node = _node_for(substance)
    for auth, _, sub in g.triples((None, EX.forSubstance, node)):
        if str(list(g.objects(auth, EX.inRegion))[0]) == region:
            status = list(g.objects(auth, EX.hasStatus))[0]
            return {"substance": substance, "region": region, "status": str(status)}
    return {"substance": substance, "region": region, "status": None}


def q_divergent(candidates, favoured_region, **p):
    """d1, d2: Which of [candidates] is authorised in favoured_region but not the other?
    'Authorised' here means status is exactly 'Approved' (US) or 'Authorised' (EU) - any other status
    (withdrawn, application withdrawn, not approved) counts as not-currently-authorised."""
    g = _g()
    other_region = "EU" if favoured_region == "US" else "US"
    positive_status = {"US": "Approved", "EU": "Authorised"}
    results = []
    for sub in candidates:
        node = _node_for(sub)
        fav_status, other_status = None, None
        for auth, _, s in g.triples((None, EX.forSubstance, node)):
            region = str(list(g.objects(auth, EX.inRegion))[0])
            status = str(list(g.objects(auth, EX.hasStatus))[0])
            if region == favoured_region:
                fav_status = status
            elif region == other_region:
                other_status = status
        if fav_status == positive_status[favoured_region] and other_status != positive_status[other_region]:
            results.append(sub)
    return {"candidates": candidates, "favoured_region": favoured_region, "matches": results}


def q_shares_atc_ancestor(substance, ancestor_code, **p):
    """h1, h2: Which OTHER roster substances share this substance's ATC ancestor at a given level?"""
    g = _g()
    target_node = RES_atc(ancestor_code)
    ref_chain = _atc_chain(substance)
    if f"atc_{ancestor_code}" not in ref_chain:
        return {"substance": substance, "ancestor_code": ancestor_code,
                "error": f"{substance} does not itself reach ATC level {ancestor_code}", "matches": []}
    all_substances = [s.split("/")[-1] for s, _, _ in g.triples((None, EX.hasAtcCode, None))]
    matches = []
    for other in all_substances:
        if other == substance.replace(" ", "_"):
            continue
        other_chain = _atc_chain(other.replace("_", " "))
        if f"atc_{ancestor_code}" in other_chain:
            matches.append(other.replace("_", " "))
    return {"substance": substance, "ancestor_code": ancestor_code, "matches": sorted(matches)}


def q_shares_atc_ancestor_bool(substance_a, comparators, ancestor_code, **p):
    """h3: Does substance_a belong to the same ATC ancestor level as ALL of [comparators]?
    Checks substance_a's own chain AND verifies each comparator genuinely reaches that level too
    (rather than assuming it) - a fact that only names some of the comparators a compound question
    asks about is an incomplete answer to that question, not a correct one."""
    chain_a = _atc_chain(substance_a)
    in_a = f"atc_{ancestor_code}" in chain_a
    comparator_status = {}
    for comp in comparators:
        chain_c = _atc_chain(comp)
        comparator_status[comp] = f"atc_{ancestor_code}" in chain_c
    return {"substance_a": substance_a, "comparators": comparators, "ancestor_code": ancestor_code,
            "substance_a_reaches_level": in_a, "comparator_status": comparator_status}


def RES_atc(code):
    from rdflib import Namespace
    RES = Namespace("http://pharma-regkg.org/resource/")
    return RES[f"atc_{code}"]


if __name__ == "__main__":
    print("--- Self-test against pre-registered benchmark ground truth ---\n")

    print("f1 (lecanemab ATC):", q_atc_code("lecanemab"))
    print("f2 (niraparib ATC):", q_atc_code("niraparib"))
    print("f3 (isatuximab ATC):", q_atc_code("isatuximab"))
    print()
    print("r1 (dostarlimab US regulator):", q_regulator("dostarlimab", "US"))
    print("r2 (niraparib centralised?):", q_is_centralised("niraparib"))
    print()
    onco = ["niraparib", "isatuximab", "epcoritamab", "dostarlimab", "melphalan flufenamide"]
    print("m1 (L01F subclass filter):", q_substances_in_atc_subclass(onco, "L01F"))
    print()
    print("c1 (orphan designation):", q_orphan_substances(onco))
    print()
    print("n1 (aducanumab EU status):", q_current_status("aducanumab", "EU"))
    print("n2 (melphalan flufenamide US status):", q_current_status("melphalan flufenamide", "US"))
    print()
    roster = ["aducanumab", "lecanemab", "donanemab", "niraparib", "isatuximab", "epcoritamab",
              "dostarlimab", "melphalan flufenamide"]
    print("d1 (US-only divergence):", q_divergent(roster, "US"))
    print("d2 (EU-only divergence):", q_divergent(roster, "EU"))
    print()
    print("h1 (niraparib's L01 sharers):", q_shares_atc_ancestor("niraparib", "L01"))
    print("h2 (lecanemab's N06D sharers):", q_shares_atc_ancestor("lecanemab", "N06D"))
    print("h3 (aducanumab in N06D?):", q_shares_atc_ancestor_bool("aducanumab", ["lecanemab", "donanemab"], "N06D"))