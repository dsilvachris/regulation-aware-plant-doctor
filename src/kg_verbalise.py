"""
kg_verbalise.py — turn the KG arm's structured facts into declarative sentences before the LLM sees them.

Why: handing the LLM raw JSON ({"substances":[...]}) makes it say "no information provided" — the JSON
isn't a claim. Both arms must hand the LLM PROSE facts; the only difference the experiment tests is WHICH
facts (KG's verified/precise vs RAG's retrieved/approximate), not their format. This equalises format.
"""
def verbalise(category, facts):
    c = facts.get("country", "")
    cname = {"NO": "Norway", "DE": "Germany"}.get(c, c)

    if category == "factual":
        return (f"Late blight is caused by the pathogen {facts.get('pathogen','?')} "
                f"(EPPO code {facts.get('eppo','?')}).")

    if category == "region_specific":
        prods = facts.get("products", [])
        if not prods:
            return f"No products are authorised against late blight in {cname}."
        return (f"{len(prods)} products are authorised against late blight in {cname}: "
                + ", ".join(prods) + ".")

    if category in ("multi_hop", "constraint"):
        subs = facts.get("substances", [])
        if not subs:
            return f"No active substances are authorised against late blight in {cname}."
        return (f"The active substances authorised against late blight in {cname} are: "
                + ", ".join(subs) + ".")

    if category == "negative":
        sub = facts.get("substance", "the substance")
        if facts.get("authorised"):
            return (f"{sub} IS authorised against late blight in {cname} "
                    f"(in: {', '.join(facts.get('products', []))}).")
        return f"{sub} is NOT authorised against late blight in {cname}. There are no such authorised products."

    if category == "cross_border":
        return (f"The number of products authorised against late blight is "
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

    if category == "authority":
        a = facts.get("authority")
        return (f"The national authority regulating plant-protection products in {cname} is {a}."
                if a else f"No authority information is available for {cname}.")

    if category == "de_only":
        subs = facts.get("de_only_substances", [])
        return (f"{len(subs)} active substances are authorised against late blight in Germany but not in Norway: "
                + ", ".join(subs) + ".") if subs else "No Germany-only substances found."

    if category == "products_with_substance":
        prods = facts.get("products", [])
        sub = facts.get("substance","")
        return (f"In {cname}, the late-blight products containing {sub} are: " + ", ".join(prods) + "."
                if prods else f"In {cname}, no authorised late-blight product contains {sub}.")

    if category == "single_substance":
        s = facts.get("single_substance", []); m = facts.get("mixtures", [])
        return (f"In {cname}, the late-blight products with a single active substance are: {', '.join(s) or 'none'}. "
                f"Mixtures (two or more substances): {', '.join(m) or 'none'}.")

    if category == "substance_in_both":
        sub = facts.get("substance",""); de = facts.get("in_DE"); no = facts.get("in_NO")
        return (f"{sub} is authorised against late blight in Germany: {'yes' if de else 'no'}; "
                f"in Norway: {'yes' if no else 'no'}. "
                f"{'It is authorised in both countries.' if facts.get('in_both') else ''}")

    return None   # not handled here -> fall back to verbalise()


def verbalise3(category, facts):
    """Verbaliser for the cross-disease query added in Phase 1."""
    if category == "multi_disease":
        subs = facts.get("multi_disease_substances", [])
        if not subs:
            return "No active substance is authorised against more than one of the three diseases."
        return ("The active substances authorised against more than one of the three diseases "
                "(late blight, apple scab, cucurbit powdery mildew) are: " + ", ".join(subs) + ".")
    return None