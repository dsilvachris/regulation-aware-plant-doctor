"""
substance_norm.py — canonicalise active-substance names across languages/spellings so that
cross-border comparison matches on chemistry, not on string.

The same substance appears as different strings across sources:
  DE (BVL, German spelling) vs NO (Mattilsynet, English/Norwegian) vs element-vs-compound (copper).
canonical() maps any known variant to one lowercase English canonical name.

Extend ALIASES as new substances appear (apple scab / powdery mildew data later).
"""
import re

# canonical (lowercase English) -> list of variant spellings seen in the data
ALIASES = {
    "difenoconazole":        ["difenoconazol", "difenoconazole"],
    "copper hydroxide":      ["kupferhydroxid", "copper hydroxide"],
    "copper oxychloride":    ["kupferoxychlorid", "copper oxychloride"],
    "potassium phosphonate": ["kaliumphosphonat", "kaliumphosphit", "kaliumphosphonat (kaliumphosphit)",
                               "potassium phosphonate", "potassium phosphite", "kalium fosfonat"],
    "cyazofamid":            ["cyazofamid"],
    "mandipropamid":         ["mandipropamid"],
    "oxathiapiprolin":       ["oxathiapiprolin"],
    "fluazinam":             ["fluazinam"],
    "cymoxanil":             ["cymoxanil"],
    "ametoctradin":          ["ametoctradin", "ametoctradine"],
    "amisulbrom":            ["amisulbrom"],
    "azoxystrobin":          ["azoxystrobin"],
    "benalaxyl-m":           ["benalaxyl-m", "benalaxyl m"],
    "fluopicolide":          ["fluopicolide"],
    "propamocarb":           ["propamocarb"],
    "valifenalate":          ["valifenalate", "valifenalat"],
    "zoxamide":              ["zoxamide", "zoxamid"],
    "cos-oga":               ["cos-oga"],
    "cerevisane":            ["cerevisane", "cerevisan"],
    "orange oil":            ["orangenöl", "orangenoel", "orange oil"],
    "bacillus amyloliquefaciens": ["bacillus amyloliquefaciens stamm fzb24",
                                   "bacillus amyloliquefaciens strain fzb24",
                                   "bacillus amyloliquefaciens"],
    "pythium oligandrum":    ["pythium oligandrum m1", "pythium oligandrum"],
    "dithianon":             ["dithianon"],
    "proquinazid":           ["proquinazid"],
    "captan":                ["captan"],
    "sulfur":                ["schwefel", "sulfur", "sulphur", "svovel"],
    "lime sulfur":           ["schwefelkalkbrühe", "schwefelkalkbruehe", "lime sulfur", "lime sulphur",
                              "calcium polysulfide", "svovelkalk"],
    "trifloxystrobin":       ["trifloxystrobin"],
    "laminarin":             ["laminarin"],
    "aureobasidium pullulans": ["aureobasidium pullulans dsm 14940", "aureobasidium pullulans dsm 14941",
                                "aureobasidium pullulans"],
    "bupirimate":            ["bupirimate"],
}

# build reverse lookup: variant (normalised) -> canonical
_VAR2CANON = {}
def _norm(s):
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s
for canon, variants in ALIASES.items():
    for v in variants:
        _VAR2CANON[_norm(v)] = canon
    _VAR2CANON[_norm(canon)] = canon

def canonical(name):
    """Return the canonical substance name, or the cleaned original if unknown (flagged upstream)."""
    n = _norm(name)
    if n in _VAR2CANON:
        return _VAR2CANON[n]
    # tolerant fallback: strip a trailing parenthetical, e.g. 'kaliumphosphonat (kaliumphosphit)'
    base = _norm(re.sub(r"\(.*?\)", "", name))
    return _VAR2CANON.get(base, n)   # returns normalised original if still unknown

def is_known(name):
    return _norm(name) in _VAR2CANON or _norm(re.sub(r"\(.*?\)", "", name)) in _VAR2CANON

if __name__ == "__main__":
    tests = ["Difenoconazol", "difenoconazole", "Kupferhydroxid", "copper hydroxide",
             "Kaliumphosphonat (Kaliumphosphit)", "potassium phosphonate", "Cyazofamid", "SomethingNew"]
    for t in tests:
        print(f"  {t:38} -> {canonical(t):24} {'(known)' if is_known(t) else '(UNKNOWN)'}")