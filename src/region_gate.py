"""
region_gate.py — region-gate fix (deterministic version).

Phase 3 failure: with no region given, the system silently defaulted to the majority region.
Fix: determine the region with an EXPLICIT, AUDITABLE rule (not the LLM's uneven geography),
and if the region can't be determined, ASK instead of guessing.

Region is decided by, in order:
  1) explicit country words           -> DE / NO
  2) a curated place gazetteer         -> DE / NO   (Hamburg and Hardanger treated identically:
                                                      both are in the list, regardless of fame)
  3) nothing recognised                -> gate (ask the user)

The LLM is used ONLY to write the advice, never to decide the region. This removes the
famous-city-vs-obscure-town inconsistency: a place either is in the known list or it isn't.
"""
import json, re
from pathlib import Path
import numpy as np
import ollama
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LLM = "llama3.2:3b"; K = 3

emb = SentenceTransformer("all-MiniLM-L6-v2")
corpus = json.load(open(DATA / "corpus.json", encoding="utf-8"))
probes = json.load(open(DATA / "region_probe_set.json", encoding="utf-8"))
doc_emb = emb.encode([r["text"] for r in corpus], normalize_embeddings=True)

# --- explicit country signals ---
COUNTRY_WORDS = {
    "NO": ("norway", "norwegian", "norge"),
    "DE": ("germany", "german", "deutschland"),
}

# --- curated place gazetteer (extensible; the auditable coverage list) ---
# Both well-known and lesser-known places are listed explicitly, so behaviour is uniform.
GAZETTEER = {"DE": [
    # cities
    "hamburg","munich","münchen","munchen","berlin","cologne","köln","koln","frankfurt",
    "stuttgart","düsseldorf","dusseldorf","dortmund","essen","leipzig","dresden","hannover",
    "hanover","nuremberg","nürnberg","nurnberg","bremen","bonn","mannheim","karlsruhe","freiburg",
    "kiel","mainz","wiesbaden","münster","munster",
    # states / regions
    "bavaria","bayern","saxony","sachsen","thuringia","thüringen","hesse","hessen",
    "lower saxony","niedersachsen","baden-württemberg","baden-wurttemberg","rhineland","rheinland",
    "palatinate","pfalz","brandenburg","mecklenburg","schleswig-holstein","saarland","westphalia",
    "westfalen",
    # agricultural areas
    "altes land","bodensee","lake constance","spreewald",
], "NO": [
    # cities
    "oslo","bergen","trondheim","stavanger","kristiansand","drammen","tromsø","tromso",
    "ålesund","alesund","bodø","bodo","sandnes","sarpsborg","skien","molde","lillehammer",
    "hamar","gjøvik","gjovik","fredrikstad","tønsberg","tonsberg",
    # counties / regions
    "hardanger","sogn","sunnfjord","nordfjord","telemark","vestland","rogaland","viken",
    "innlandet","trøndelag","trondelag","agder","vestfold","østfold","ostfold","nordland",
    "troms","finnmark","lofoten",
    # agricultural areas
    "gvarv","lier",
]}
# invert to place -> country, longest-first so multi-word names match before their parts
PLACE_TO_COUNTRY = []
for country, places in GAZETTEER.items():
    for p in places:
        PLACE_TO_COUNTRY.append((p, country))
PLACE_TO_COUNTRY.sort(key=lambda x: -len(x[0]))

GATE_MESSAGE = (
    "I can help with that - but the authorised plant-protection products differ by country, "
    "so I need to know where you're growing before I advise. Which country are you in: "
    "Germany or Norway? (Those are the two regions I currently cover.)"
)

def detect_region(query):
    q = query.lower()
    for country, words in COUNTRY_WORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", q) for w in words):
            return country, "explicit-country"
    for place, country in PLACE_TO_COUNTRY:
        if re.search(rf"\b{re.escape(place)}\b", q):
            return country, f"gazetteer:{place}"
    return "UNKNOWN", "no-region"

def retrieve(query, country, k=K):
    idx = [i for i, r in enumerate(corpus) if r["country"] == country]
    qe = emb.encode([query], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb[idx] @ qe)[::-1][:k]
    return [corpus[idx[j]] for j in order]

def answer(query, ctx):
    prompt = f"""You are a plant-disease assistant. Use ONLY the context below.
Name the disease and how to manage it, and state which national authority's authorised
products must be used. Do not add facts that are not in the context.

Context:
{ctx}

Question: {query}
Answer:"""
    return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

def gated_diagnose(query):
    region, how = detect_region(query)
    if region == "UNKNOWN":
        return "GATE", how, GATE_MESSAGE
    top = retrieve(query, region)
    ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
    return region, how, answer(query, ctx)

if __name__ == "__main__":
    fired = 0
    for q in probes:
        region, how, resp = gated_diagnose(q["question"])
        if region == "GATE":
            tag = "GATE FIRED -> asked for region"; fired += 1
        else:
            tag = f"proceeded as {region} ({how})"
        print("=" * 72)
        print(f"{q['id']} | {q['category']} | {tag}")
        print(f"Q: {q['question']}")
        print(f"A: {resp}")
        print()
    print(f"\nGate fired on {fired}/{len(probes)} (expected: only the true no-location cases).")