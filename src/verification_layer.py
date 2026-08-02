"""
verification_layer.py — Phase 5, Step 2 (Work Package B): the trustworthiness verification layer.

Deterministic, post-generation detection (never correction) of unsupported claims. Method confirmed via
Step 0a's feasibility check (docs/Phase5_Step0a_VerifierFeasibility.md): qualifier/coordination-aware
matching catches the one confirmed real hallucination this project has produced (Phase 4's `r2`), with
zero false positives on 35 real known-good cases. This module is the productionised version of that
script — same logic, refactored into an importable library with a pluggable domain-synonym table (Step
0a's `EMA<->EU`/`FDA<->US` table was pharma-specific; the deployed plant-protection assistant needs its
own).

Pipeline (detection only):

    generated answer -> extract claims -> compare against facts_text ->
      supported? -> YES: return unmodified
                 -> NO: flag, name the unsupported part, disclose - never silently correct or retry

Run: python src/verification_layer.py   -> self-test against a few inline examples
"""
import re

BASE_STOPWORDS = {
    "the", "a", "an", "is", "in", "of", "to", "and", "or", "at", "via", "for", "with", "on",
    "as", "by", "this", "that", "it", "its", "was", "were", "be", "been", "are", "no", "not",
    # discourse markers - real entities never appear ONLY as these, but they're commonly capitalised
    # at sentence-start and were the majority cause of false positives in Step 0a's first round
    "according", "based", "both", "also", "additionally", "however", "therefore", "furthermore",
    "considering", "given", "since", "while", "although", "similarly", "overall", "finally",
    "thus", "hence", "moreover", "there", "can", "there's", "here",
}

# Per-domain regulator/region synonym tables. Justified in each case by the domain's own KG schema
# stating the correspondence explicitly for every fact (not external knowledge smuggled in) - see
# Phase5_Step0a_VerifierFeasibility.md for the pharma table's original justification.
DOMAIN_SYNONYMS = {
    "pharma": {"ema": "eu", "eu": "ema", "fda": "us", "us": "fda"},
    "plant_protection": {"bvl": "germany", "germany": "bvl", "de": "germany",
                          "mattilsynet": "norway", "norway": "mattilsynet", "no": "norway"},
}

COORD_PATTERNS = [
    re.compile(r"\bboth\s+(.+?)\s+and\s+(.+?)([.;,]|$)", re.IGNORECASE),
    re.compile(r"(.+?)\s+as well as\s+(.+?)([.;,]|$)", re.IGNORECASE),
    re.compile(r"(.+?),?\s+in addition to\s+(.+?)([.;,]|$)", re.IGNORECASE),
]


def _entity_in_facts(entity, facts_lower, synonyms):
    if entity.lower() in facts_lower:
        return True
    synonym = synonyms.get(entity.lower())
    return synonym is not None and synonym in facts_lower


def _extract_entities(text, stopwords):
    caps = re.findall(r"\b[A-Z][A-Za-z]{2,}\b", text)
    codes = re.findall(r"\b[A-Z0-9]{4,}\b", text)
    return {e for e in (caps + codes) if e.lower() not in stopwords and e not in ("The", "This", "It")}


def _keywords(phrase, stopwords):
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", phrase.lower())
    return {t for t in tokens if t not in stopwords}


def verify(answer, facts_text, domain=None, extra_stopwords=None, question=None):
    """
    Main entry point. Returns:
      {"flagged": bool, "reason": str or None, "branches": [...] or None}

    domain: key into DOMAIN_SYNONYMS (e.g. "plant_protection", "pharma"), or None for no synonym table.
    extra_stopwords: optional additional domain-specific stopwords.
    question: optional original question text. Entities the model echoes back from the user's OWN
      question (e.g. "I don't have information about Germany" when Germany was named in the question)
      are not fabrications - they're references to what was asked, not invented claims. Checked as
      additional legitimate context alongside facts_text.
    """
    stopwords = BASE_STOPWORDS | (extra_stopwords or set())
    synonyms = DOMAIN_SYNONYMS.get(domain, {})
    facts_lower = facts_text.lower()
    question_lower = (question or "").lower()

    def supported_anywhere(entity):
        return (_entity_in_facts(entity, facts_lower, synonyms)
                or (question_lower and entity.lower() in question_lower))

    branches_checked = []
    any_flag = False
    found_coordination = False

    for pattern in COORD_PATTERNS:
        for m in pattern.finditer(answer):
            found_coordination = True
            branch1, branch2 = m.group(1), m.group(2)
            for branch in (branch1, branch2):
                kws = _keywords(branch, stopwords)
                supported = any(supported_anywhere(kw) for kw in kws) if kws else True
                branches_checked.append({"branch": branch.strip(), "supported": supported})
                if not supported:
                    any_flag = True

    if found_coordination:
        reason = None
        if any_flag:
            unsupported = [b["branch"] for b in branches_checked if not b["supported"]]
            reason = f"Unsupported claim(s): {'; '.join(unsupported)}"
        return {"flagged": any_flag, "reason": reason, "branches": branches_checked}

    # No compound claim detected - fall back to entity-presence check
    entities = _extract_entities(answer, stopwords)
    missing = [e for e in entities if not supported_anywhere(e)]
    reason = f"Unsupported entity/entities: {', '.join(missing)}" if missing else None
    return {"flagged": len(missing) > 0, "reason": reason, "branches": None}


def disclose(answer, verify_result):
    """Given a flagged verify() result, produce the user-facing disclosure to append. Detection and
    disclosure only - never rewrites or corrects the answer itself."""
    if not verify_result["flagged"]:
        return answer
    return (f"{answer}\n\n*(Note: part of this answer could not be verified against the retrieved "
            f"facts and may be inaccurate - {verify_result['reason']}. Please confirm against the "
            f"original source before relying on it.)*")


if __name__ == "__main__":
    # The confirmed r2 case
    r2_facts = "niraparib is authorised via the EU's centralised procedure (EMA)."
    r2_answer = ("Niraparib is authorised via both the EU's centralised procedure (EMA) and "
                 "at the national level.")
    r = verify(r2_answer, r2_facts, domain="pharma")
    print("r2 (should flag):", r)
    print("disclosed:", disclose(r2_answer, r))
    print()

    # A genuine, fully-supported compound claim (should NOT flag)
    facts2 = "Aducanumab is not authorised in the EU. Aducanumab is approved in the US."
    answer2 = "Aducanumab is authorised in both the US and not in the EU."
    r2 = verify(answer2, facts2, domain="pharma")
    print("genuine compound claim (should not flag):", r2)