"""
kg_verbalise_phase4.py — Phase 4, Step 4: turn kg_arm_phase4.py's structured query results into the
facts_text the LLM sees.

Two lessons already paid for in this project, applied here from the start rather than discovered later:
  1. Every fact names its actual substance/region/code explicitly, derived from the query result — never
     a hardcoded placeholder (the exact bug class in Correction_KG_Disease_Name_Bug.md, which affected
     12 Phase-1 questions before being caught downstream in Phase 3).
  2. Category-label / candidate-list text is kept structurally separate from the actual answer list — a
     "considering candidates X, Y, Z" framing sentence is never immediately followed by "are: A, B" in a
     way that could be misread as "X, Y, Z are A, B" (the exact ambiguity in the multi_disease template
     fixed in Phase3_Step2_FusionArm.md, which caused a confirmed fabrication).

Run: python src/kg_verbalise_phase4.py   -> self-test against kg_arm_phase4.py's live query results
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kg_arm_phase4 as kg


def verbalise(category, facts):
    if category == "atc_code":
        sub, code = facts["substance"], facts["atc_code"]
        return f"The ATC (Anatomical Therapeutic Chemical) code for {sub} is {code}." if code \
            else f"No ATC code is recorded for {sub}."

    if category == "regulator":
        sub, region, reg = facts["substance"], facts["region"], facts["regulator"]
        return f"In {region}, {sub} is regulated by {reg}." if reg \
            else f"No {region} regulatory record was found for {sub}."

    if category == "centralised":
        sub, c = facts["substance"], facts["centralised"]
        return (f"{sub} is authorised via the EU's centralised procedure (EMA)." if c
                else f"{sub} is not currently authorised via the EU's centralised procedure.")

    if category == "atc_subclass_filter":
        candidates, prefix, matches = facts["candidates"], facts["atc_prefix"], facts["matches"]
        # Lesson 2: the candidate list and the result list are two separate sentences, not one blended
        # "candidates are: matches" construction.
        cand_sentence = f"The candidate substances considered are: {', '.join(candidates)}."
        if matches:
            result_sentence = (f"Of these, the ones classified under ATC prefix {prefix} are: "
                                f"{', '.join(matches)}.")
        else:
            result_sentence = f"None of these candidates are classified under ATC prefix {prefix}."
        return cand_sentence + " " + result_sentence

    if category == "orphan_filter":
        candidates, matches = facts["candidates"], facts["matches"]
        cand_sentence = f"The candidate substances considered are: {', '.join(candidates)}."
        if matches:
            result_sentence = f"Of these, the ones holding EMA orphan-medicine designation are: {', '.join(matches)}."
        else:
            result_sentence = "None of these candidates hold EMA orphan-medicine designation."
        return cand_sentence + " " + result_sentence

    if category == "current_status":
        sub, region, status = facts["substance"], facts["region"], facts["status"]
        return f"{sub}'s current authorisation status in {region} is: {status}." if status \
            else f"No {region} authorisation record was found for {sub}."

    if category == "divergent":
        candidates, fav, matches = facts["candidates"], facts["favoured_region"], facts["matches"]
        other = "EU" if fav == "US" else "US"
        cand_sentence = f"The candidate substances considered are: {', '.join(candidates)}."
        if matches:
            result_sentence = (f"Of these, the ones currently authorised in {fav} but NOT in {other} are: "
                                f"{', '.join(matches)}.")
        else:
            result_sentence = f"None of these candidates are authorised in {fav} but not in {other}."
        return cand_sentence + " " + result_sentence

    if category == "shares_atc_ancestor":
        sub, ancestor, matches = facts["substance"], facts["ancestor_code"], facts.get("matches", [])
        if facts.get("error"):
            return facts["error"] + "."
        if matches:
            return (f"Other substances that share {sub}'s ATC classification at the {ancestor} level are: "
                    f"{', '.join(matches)}.")
        return f"No other substance in this benchmark shares {sub}'s ATC classification at the {ancestor} level."

    if category == "shares_atc_ancestor_bool":
        a, b, ancestor, reaches = (facts["substance_a"], facts["substance_b"], facts["ancestor_code"],
                                    facts["substance_a_reaches_level"])
        verdict = "does" if reaches else "does NOT"
        return (f"{a}'s own ATC classification {verdict} reach the {ancestor} level. "
                f"(This determines whether {a} shares that specific ATC subgroup with {b}.)")

    return None


if __name__ == "__main__":
    print("--- Self-test: verbalise every query type against real kg_arm_phase4.py output ---\n")
    tests = [
        ("atc_code", kg.q_atc_code("lecanemab")),
        ("regulator", kg.q_regulator("dostarlimab", "US")),
        ("centralised", kg.q_is_centralised("niraparib")),
        ("atc_subclass_filter", kg.q_substances_in_atc_subclass(
            ["niraparib", "isatuximab", "epcoritamab", "dostarlimab", "melphalan flufenamide"], "L01F")),
        ("orphan_filter", kg.q_orphan_substances(
            ["niraparib", "isatuximab", "epcoritamab", "dostarlimab", "melphalan flufenamide"])),
        ("current_status", kg.q_current_status("aducanumab", "EU")),
        ("current_status", kg.q_current_status("melphalan flufenamide", "US")),
        ("divergent", kg.q_divergent(
            ["aducanumab", "lecanemab", "donanemab", "niraparib", "isatuximab", "epcoritamab",
             "dostarlimab", "melphalan flufenamide"], "US")),
        ("shares_atc_ancestor", kg.q_shares_atc_ancestor("niraparib", "L01")),
        ("shares_atc_ancestor", kg.q_shares_atc_ancestor("lecanemab", "N06D")),
        ("shares_atc_ancestor_bool", kg.q_shares_atc_ancestor_bool("aducanumab", "lecanemab", "N06D")),
    ]
    for cat, facts in tests:
        print(f"[{cat}]")
        print(" ", verbalise(cat, facts))
        print()