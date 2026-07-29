"""
kg_verbalise.py — turn the KG arm's structured facts into declarative sentences before the LLM sees them.

Why: handing the LLM raw JSON ({"substances":[...]}) makes it say "no information provided" — the JSON
isn't a claim. Both arms must hand the LLM PROSE facts; the only difference the experiment tests is WHICH
facts (KG's verified/precise vs RAG's retrieved/approximate), not their format. This equalises format.
"""
def verbalise(category, facts):
    c = facts.get("country", "")
    cname = {"NO": "Norway", "DE": "Germany"}.get(c, c)
    # Kept in sync with build_kg.py's DISEASES[...]["label"] — duplicated here (not imported) because
    # build_kg.py runs its full KG-build pipeline at import time (side effects), same reason
    # phase2_step1_oracle.py is not imported elsewhere in this project.
    DISEASE_LABEL = {"late_blight": "late blight", "apple_scab": "apple scab",
                      "powdery_mildew": "cucurbit powdery mildew"}
    dname = DISEASE_LABEL.get(facts.get("disease"), "late blight")  # default preserves old behaviour
                                                                      # when disease is genuinely unset

    if category == "factual":
        return (f"Late blight is caused by the pathogen {facts.get('pathogen','?')} "
                f"(EPPO code {facts.get('eppo','?')}).")

    if category == "region_specific":
        prods = facts.get("products", [])
        if not prods:
            return f"No products are authorised against {dname} in {cname}."
        return (f"{len(prods)} products are authorised against {dname} in {cname}: "
                + ", ".join(prods) + ".")

    if category in ("multi_hop", "constraint"):
        subs = facts.get("substances", [])
        if not subs:
            return f"No active substances are authorised against {dname} in {cname}."
        return (f"The active substances authorised against {dname} in {cname} are: "
                + ", ".join(subs) + ".")

    if category == "negative":
        sub = facts.get("substance", "the substance")
        if facts.get("authorised"):
            return (f"{sub} IS authorised against {dname} in {cname} "
                    f"(in: {', '.join(facts.get('products', []))}).")
        return f"{sub} is NOT authorised against {dname} in {cname}. There are no such authorised products."

    if category == "cross_border":
        return (f"The number of products authorised against {dname} is "
                f"{facts.get('DE_count','?')} in Germany and {facts.get('NO_count','?')} in Norway.")

    # fallback: dump as readable key: value lines
    return "; ".join(f"{k}: {v}" for k, v in facts.items())

if __name__ == "__main__":
    print(verbalise("multi_hop", {"country":"NO","substances":["cyazofamid","difenoconazole","mandipropamid","oxathiapiprolin"]}))
    print(verbalise("negative", {"country":"NO","substance":"fluazinam","authorised":False,"products":[]}))
    print(verbalise("cross_border", {"DE_count":112,"NO_count":4}))
    print(verbalise("region_specific", {"country":"NO","products":["Ranman TOP","Revus","Revus Pro","Revus Top"]}))


def verbalise2(category, facts):
    """Verbaliser cases for the templates added after the first full run."""
    c = facts.get("country", ""); cname = {"NO":"Norway","DE":"Germany"}.get(c, c)
    # Same fix and same rationale as verbalise() above — kept duplicated rather than shared to avoid
    # coupling these two independently-evolving verbaliser functions.
    DISEASE_LABEL = {"late_blight": "late blight", "apple_scab": "apple scab",
                      "powdery_mildew": "cucurbit powdery mildew"}
    dname = DISEASE_LABEL.get(facts.get("disease"), "late blight")

    if category == "authority":
        a = facts.get("authority")
        return (f"The national authority regulating plant-protection products in {cname} is {a}."
                if a else f"No authority information is available for {cname}.")

    if category == "de_only":
        subs = facts.get("de_only_substances", [])
        return (f"{len(subs)} active substances are authorised against {dname} in Germany but not in Norway: "
                + ", ".join(subs) + ".") if subs else "No Germany-only substances found."

    if category == "products_with_substance":
        prods = facts.get("products", [])
        sub = facts.get("substance","")
        return (f"In {cname}, the {dname} products containing {sub} are: " + ", ".join(prods) + "."
                if prods else f"In {cname}, no authorised {dname} product contains {sub}.")

    if category == "single_substance":
        s = facts.get("single_substance", []); m = facts.get("mixtures", [])
        return (f"In {cname}, the {dname} products with a single active substance are: {', '.join(s) or 'none'}. "
                f"Mixtures (two or more substances): {', '.join(m) or 'none'}.")

    if category == "substance_in_both":
        sub = facts.get("substance",""); de = facts.get("in_DE"); no = facts.get("in_NO")
        return (f"{sub} is authorised against {dname} in Germany: {'yes' if de else 'no'}; "
                f"in Norway: {'yes' if no else 'no'}. "
                f"{'It is authorised in both countries.' if facts.get('in_both') else ''}")

    return None   # not handled here -> fall back to verbalise()


def verbalise3(category, facts):
    """Verbaliser for the cross-disease query added in Phase 1."""
    if category == "multi_disease":
        subs = facts.get("multi_disease_substances", [])
        # Note: this template used to read "...more than one of the three diseases (late blight, apple
        # scab, cucurbit powdery mildew) are: X, Y." — the parenthetical (naming what "the three diseases"
        # ARE, as a category label) sat directly next to the substance list, and was found (via Phase 3's
        # Step 2 fusion demo, cross-checked against Phase 1's original grading data) to be reliably
        # misread by the LLM as a per-substance disease breakdown — i.e. "azoxystrobin covers late blight,
        # apple scab, and cucurbit powdery mildew," which is not stated and is not fully true (azoxystrobin
        # actually covers late blight + powdery mildew, not apple scab). This already caused one confirmed
        # mis-graded answer in Phase 1's original data (run2_xd_02). Fixed by structurally separating the
        # category-label sentence from the substance-list sentence, so the disease names never sit
        # adjacent to "are: X, Y" and cannot be read as describing X and Y specifically.
        if not subs:
            return ("Considering the three diseases studied (late blight, apple scab, cucurbit powdery "
                    "mildew): no active substance is authorised against more than one of them.")
        return ("Considering the three diseases studied (late blight, apple scab, cucurbit powdery "
                "mildew), the following active substances are each authorised against more than one of "
                "them (this statement does not specify which particular diseases each substance covers): "
                + ", ".join(subs) + ".")
    return None