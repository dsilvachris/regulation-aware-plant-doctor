"""
rag_arm_phase4.py — Phase 4, Step 4: the document-RAG arm.

Same job as kg_arm_phase4.py (retrieve facts for a benchmark question), but via semantic document
retrieval over the SAME data rendered as prose (data-parity, rag_docs_phase4.json). No category
templates — retrieves the top-k most similar prose docs, exactly as a normal RAG system would. Mirrors
rag_arm.py's structure exactly.

With only 8 documents in this corpus (vs Phase 1's 128), K defaults lower — retrieving 8 would just
return the whole corpus every time, giving RAG an unrealistic advantage no real deployment would have.

Run: python src/rag_arm_phase4.py   -> demo retrieval on a few benchmark-style questions
"""
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
K = 3  # corpus is only 8 docs; retrieving too many defeats the purpose of a retrieval comparison

_emb = None
_docs = None
_doc_emb = None


def _load():
    global _emb, _docs, _doc_emb
    if _emb is None:
        _emb = SentenceTransformer("all-MiniLM-L6-v2")
        _docs = json.load(open(DATA / "rag_docs_phase4.json", encoding="utf-8"))["documents"]
        _doc_emb = _emb.encode([d["text"] for d in _docs], normalize_embeddings=True)
    return _emb, _docs, _doc_emb


def rag_retrieve(question, k=K):
    """Return the top-k prose docs most similar to the question."""
    emb, docs, doc_emb = _load()
    qe = emb.encode([question], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb @ qe)[::-1][:k]
    return [docs[i]["text"] for i in order]


if __name__ == "__main__":
    for q in ["Is aducanumab authorised in the EU?",
              "What is the ATC code for niraparib?",
              "Which substances are approved by the FDA but not the EMA?"]:
        print(f"\nQ: {q}")
        for t in rag_retrieve(q, k=3):
            print("   -", t[:100])