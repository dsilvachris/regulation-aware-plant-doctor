"""
phase3_step1_diagnose_conflicts.py — Phase 3, Step 1: do real KG/RAG conflicts exist in this data?

Per Phase3_Design.md: before building a conflict-handling evaluation (Step 4), verify conflicts actually
occur — the same discipline that caught Phase 1's hierarchy-traversal category (pre-registered but not
instantiable in the data). No LLM calls in this step: both arms already retrieve deterministically
(kg_arm's SPARQL, rag_arm's embedding similarity), so this is a pure comparison of their outputs.

Method (heuristic, approximate by design — flagged results are for MANUAL review, not a final verdict):
  1. Build an authoritative entity vocabulary directly from the KG (all product names, all substance
     names) — using the graph itself as ground truth for what counts as an entity, rather than generic
     NLP extraction.
  2. For each benchmark question, get the KG arm's verbalised facts_text (same text the LLM would see,
     computed WITHOUT calling explain()/Ollama) and the RAG arm's top-8 retrieved docs (joined).
  3. Extract which vocabulary entities appear in each text. Classify the question by entity overlap:
       - REDUNDANT   : most/all KG-stated entities also appear in the RAG text (sources agree/overlap)
       - ONE_SIDED_GAP: KG states entities the RAG text doesn't mention at all (RAG silent on what KG
                        knows) — expected to be the common case, since RAG's top-8 retrieval is a fixed-k
                        semantic search, not a guarantee of complete coverage
       - NO_KG_ENTITIES: KG facts contain no vocabulary entities to compare (e.g. count-only or
                        yes/no-only answers) — overlap comparison doesn't apply, flagged separately
  4. A simple negation heuristic additionally flags NEGATION_MISMATCH candidates: cases where the KG
     facts_text explicitly negates something (e.g. "NOT authorised") but the RAG text discusses the same
     entity without an obvious negation nearby — a candidate for genuine conflict, but heuristic and
     REQUIRES manual verification per the pre-registered plan (this script does not claim these are
     confirmed conflicts).

Run: python src/phase3_step1_diagnose_conflicts.py
"""
import json, re, sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
import kg_arm as _kg
import rag_arm

EX_PREFIX = 'PREFIX ex: <http://plant-regkg.org/ontology#>\n'
NEGATION_WORDS = ["not authorised", "not authorized", "no such", " not ", "banned", "prohibited"]


def kg_facts_text(qid):
    """Same text the LLM would see from the KG arm — WITHOUT calling explain()/Ollama."""
    query_fn, params, vcat = ep.route(qid)
    facts = query_fn(**params)
    facts_text = ep.verbalise3(vcat, facts) or ep.verbalise2(vcat, facts)
    if facts_text is None:
        facts_text = ep.verbalise(vcat, facts)
    return facts_text or ""


def build_vocab():
    """Authoritative entity vocabulary pulled directly from the KG (not inferred/guessed)."""
    g = _kg._g()
    products = {str(r[0]) for r in g.query(
        EX_PREFIX + "SELECT DISTINCT ?name WHERE { ?a ex:hasProduct ?p . ?p rdfs:label ?name . }")}
    substances = {str(r[0]) for r in g.query(
        EX_PREFIX + "SELECT DISTINCT ?name WHERE { ?p ex:containsSubstance ?s . ?s rdfs:label ?name . }")}
    vocab = products | substances
    # longest-first so multi-word entities aren't partially shadowed by shorter substrings
    return sorted(vocab, key=len, reverse=True)


def find_entities(text, vocab):
    tl = text.lower()
    return {e for e in vocab if e.lower() in tl}


def has_negation_near(text, entity):
    tl = text.lower()
    idx = tl.find(entity.lower())
    if idx == -1:
        return False
    window = tl[max(0, idx - 60):idx + 60]
    return any(neg in window for neg in NEGATION_WORDS)


if __name__ == "__main__":
    print("Building entity vocabulary from the KG...")
    vocab = build_vocab()
    print(f"  {len(vocab)} distinct product/substance entities\n")

    items = [it for it in ep.load_benchmark() if it[2] != "hierarchy"]
    results = {}
    counts = {"REDUNDANT": 0, "ONE_SIDED_GAP": 0, "NO_KG_ENTITIES": 0}
    negation_candidates = []

    for qid, q, cat in items:
        ftext = kg_facts_text(qid)
        rag_docs = rag_arm.rag_retrieve(q, k=8)
        rtext = "\n".join(rag_docs)

        kg_entities = find_entities(ftext, vocab)
        rag_entities = find_entities(rtext, vocab)

        if not kg_entities:
            classification = "NO_KG_ENTITIES"
        else:
            missing = kg_entities - rag_entities
            overlap_ratio = 1 - (len(missing) / len(kg_entities))
            classification = "REDUNDANT" if overlap_ratio >= 0.5 else "ONE_SIDED_GAP"

        counts[classification] += 1

        neg_flag = False
        if "not" in ftext.lower() or "NOT" in ftext:
            for e in kg_entities:
                if has_negation_near(ftext, e) and e in rag_entities and not has_negation_near(rtext, e):
                    neg_flag = True
                    negation_candidates.append({"qid": qid, "question": q, "entity": e,
                                                  "kg_facts_text": ftext, "rag_snippet": rtext[:400]})

        results[qid] = {
            "question": q, "category": cat, "classification": classification,
            "kg_entities": sorted(kg_entities), "rag_entities_found": sorted(rag_entities & kg_entities),
            "kg_entities_missing_from_rag": sorted(kg_entities - rag_entities),
            "negation_mismatch_candidate": neg_flag,
            "kg_facts_text": ftext,
        }
        print(f"  {qid:8} {cat:16} {classification:16} "
              f"kg_entities={len(kg_entities):2} missing_from_rag={len(kg_entities - rag_entities):2}"
              f"{'  <-- NEGATION CANDIDATE' if neg_flag else ''}")

    print("\n" + "=" * 60)
    print("Summary:")
    for k, v in counts.items():
        print(f"  {k:20} {v:3} / {len(items)}")
    print(f"  NEGATION_MISMATCH candidates: {len(negation_candidates)} (heuristic — needs manual review)")

    if negation_candidates:
        print("\n-- Negation-mismatch candidates (READ THESE MANUALLY before treating as real conflicts) --")
        for c in negation_candidates:
            print(f"\n  {c['qid']}: {c['question']}")
            print(f"    entity: {c['entity']}")
            print(f"    KG facts_text: {c['kg_facts_text']}")
            print(f"    RAG snippet: {c['rag_snippet'][:200]}...")

    json.dump({
        "_meta": {"method": "entity-overlap heuristic against KG-derived vocabulary; "
                             "negation candidates are unverified, for manual review only"},
        "counts": counts,
        "negation_candidates": negation_candidates,
        "results": results,
    }, open(DATA / "phase3_conflict_diagnosis.json", "w"), ensure_ascii=False, indent=2)
    print("\nWrote data/phase3_conflict_diagnosis.json")