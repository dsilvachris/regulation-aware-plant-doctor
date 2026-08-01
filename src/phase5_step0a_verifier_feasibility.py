"""
phase5_step0a_verifier_feasibility.py — Phase 5, Step 0a: does a deterministic verifier catch the one
confirmed hallucination this project has actually produced (r2), without flagging genuinely correct
answers?

Test set:
  - r2's real facts_text + the real fabricated KG answer from Phase 4 grading (MUST be flagged)
  - All correct+faithful KG answers from Phase 4's graded sheet, paired with their real facts_text
    (re-derived from kg_arm_phase4.py/kg_verbalise_phase4.py, not retyped) — MUST NOT be flagged

Two candidates tested honestly, per the pre-registered prediction in Phase5_Plan.md:
  A. Naive entity-presence matching (predicted to MISS r2, since no new entity was invented — only an
     unsupported relationship between two already-present entities was added)
  B. Qualifier/coordination-aware matching (predicted to CATCH r2, by splitting compound claims like
     "both X and Y" into branches and verifying each independently)

Run: python src/phase5_step0a_verifier_feasibility.py
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline_phase4 as ep
from kg_verbalise_phase4 import verbalise

STOPWORDS = {"the", "a", "an", "is", "in", "of", "to", "and", "or", "at", "via", "for", "with", "on",
             "as", "by", "this", "that", "it", "its", "was", "were", "be", "been", "are", "no", "not",
             # discourse markers - real entities never appear ONLY as these, but these are commonly
             # capitalised at sentence-start and were the majority cause of false positives (Step 0a v1)
             "according", "based", "both", "also", "additionally", "however", "therefore", "furthermore",
             "considering", "given", "since", "while", "although", "similarly", "overall", "finally",
             "thus", "hence", "moreover"}

# Regulator <-> region synonym table. Not external knowledge: this correspondence is stated explicitly
# in build_kg_phase4.py's own AUTHORITY dict (EMA regulates EU, FDA regulates US) and is consistent
# across every fact in this KG - a model substituting the regulator name for the region it's stated to
# oversee is restating the same fact, not inventing one. Diagnosed as a real false-positive cause in
# Step 0a v1 (n1's "EMA" missing when facts_text said only "EU").
DOMAIN_SYNONYMS = {"ema": "eu", "eu": "ema", "fda": "us", "us": "fda"}


def entity_in_facts(entity, facts_lower):
    if entity.lower() in facts_lower:
        return True
    synonym = DOMAIN_SYNONYMS.get(entity.lower())
    return synonym is not None and synonym in facts_lower


def extract_entities(text):
    """Candidate A's entity extractor: capitalized words/phrases and alphanumeric codes."""
    caps = re.findall(r"\b[A-Z][A-Za-z]{2,}\b", text)
    codes = re.findall(r"\b[A-Z0-9]{4,}\b", text)
    return {e for e in (caps + codes) if e.lower() not in STOPWORDS and e not in ("The", "This", "It")}


def verify_naive_entity(answer, facts_text):
    """Candidate A."""
    entities = extract_entities(answer)
    facts_lower = facts_text.lower()
    missing = [e for e in entities if not entity_in_facts(e, facts_lower)]
    return {"flagged": len(missing) > 0, "missing_entities": missing}


COORD_PATTERNS = [
    re.compile(r"\bboth\s+(.+?)\s+and\s+(.+?)([.;,]|$)", re.IGNORECASE),
    re.compile(r"(.+?)\s+as well as\s+(.+?)([.;,]|$)", re.IGNORECASE),
    re.compile(r"(.+?),?\s+in addition to\s+(.+?)([.;,]|$)", re.IGNORECASE),
]


def keywords(phrase):
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", phrase.lower())
    return {t for t in tokens if t not in STOPWORDS}


def verify_qualifier_aware(answer, facts_text):
    """Candidate B. Falls back to Candidate A's check if no coordination pattern is found."""
    facts_lower = facts_text.lower()
    branches_checked = []
    any_flag = False
    found_coordination = False

    for pattern in COORD_PATTERNS:
        for m in pattern.finditer(answer):
            found_coordination = True
            branch1, branch2 = m.group(1), m.group(2)
            for branch in (branch1, branch2):
                kws = keywords(branch)
                supported = any(entity_in_facts(kw, facts_lower) for kw in kws) if kws else True
                branches_checked.append({"branch": branch.strip(), "supported": supported})
                if not supported:
                    any_flag = True

    if found_coordination:
        return {"flagged": any_flag, "branches": branches_checked, "method": "coordination-split"}

    # No compound claim detected - fall back to entity-presence check
    base = verify_naive_entity(answer, facts_text)
    base["method"] = "fallback-entity"
    return base


if __name__ == "__main__":
    # --- The confirmed fabrication case ---
    r2_query_fn, r2_params, r2_vcat = ep.route("r2")
    r2_facts = verbalise(r2_vcat, r2_query_fn(**r2_params))
    r2_fabricated_answer = ("Niraparib is authorised via both the EU's centralised procedure (EMA) and "
                             "at the national level.")

    print("=" * 70)
    print("CONFIRMED FABRICATION CASE (r2) — must be flagged by a working verifier")
    print(f"  facts_text: {r2_facts}")
    print(f"  answer:     {r2_fabricated_answer}")
    a_result = verify_naive_entity(r2_fabricated_answer, r2_facts)
    b_result = verify_qualifier_aware(r2_fabricated_answer, r2_facts)
    print(f"  Candidate A (naive entity):        flagged={a_result['flagged']}  "
          f"{'CORRECTLY CAUGHT' if a_result['flagged'] else 'MISSED (as predicted)'}")
    print(f"  Candidate B (qualifier-aware):      flagged={b_result['flagged']}  "
          f"{'CORRECTLY CAUGHT' if b_result['flagged'] else 'MISSED'}")
    if b_result.get("branches"):
        for br in b_result["branches"]:
            print(f"      branch: '{br['branch']}'  supported={br['supported']}")

    # --- Known-good KG answers (correct + faithful) from Phase 4's real graded data ---
    sheet = {it["item"]: it for it in json.load(open(DATA / "phase4_grading_sheet_BLIND.json", encoding="utf-8"))["items"]}
    key = {k["item"]: k for k in json.load(open(DATA / "phase4_grading_key.json", encoding="utf-8"))["key"]}

    def val(x):
        s = str(x).strip()
        return int(s) if s in ("0", "1") else None

    good_cases = []
    for item, it in sorted(sheet.items()):
        mp = key[item]
        for slot in ("A", "B"):
            if mp[slot] != "kg":
                continue
            if val(it.get(f"grade_{slot}_correct")) == 1 and val(it.get(f"grade_{slot}_faithful")) == 1:
                qid = item.split("_", 1)[1]
                good_cases.append((item, qid, it[f"System {slot}"]))

    print("\n" + "=" * 70)
    print(f"KNOWN-GOOD KG ANSWERS (n={len(good_cases)}) — must NOT be flagged (false-positive check)")
    print("-" * 70)
    a_fp, b_fp = 0, 0
    for item, qid, answer in good_cases:
        query_fn, params, vcat = ep.route(qid)
        facts_text = verbalise(vcat, query_fn(**params))
        a_r = verify_naive_entity(answer, facts_text)
        b_r = verify_qualifier_aware(answer, facts_text)
        if a_r["flagged"]:
            a_fp += 1
        if b_r["flagged"]:
            b_fp += 1
        flag_str = f"A={'FLAG' if a_r['flagged'] else 'ok'} B={'FLAG' if b_r['flagged'] else 'ok'}"
        print(f"  {item:10} {flag_str}  {answer[:70]}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"Candidate A (naive entity):   r2 caught={a_result['flagged']}  "
          f"false positives={a_fp}/{len(good_cases)}")
    print(f"Candidate B (qualifier-aware): r2 caught={b_result['flagged']}  "
          f"false positives={b_fp}/{len(good_cases)}")

    winner = None
    if b_result["flagged"] and b_fp == 0:
        winner = "B (qualifier-aware)"
    elif a_result["flagged"] and a_fp == 0:
        winner = "A (naive entity)"
    print(f"\nGO/NO-GO: {'GO - ' + winner + ' selected' if winner else 'NO-GO - neither candidate works cleanly, report as negative finding'}")