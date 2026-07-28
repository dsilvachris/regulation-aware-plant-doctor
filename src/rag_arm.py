"""
rag_arm.py — Stage 5: the document-RAG arm.

Same job as the KG arm (retrieve facts for a benchmark question), but via semantic document
retrieval over the SAME data rendered as prose (data-parity). No category templates — it just
retrieves the top-k most similar prose docs, exactly as a normal RAG system would.

Workflow:  question -> embed -> retrieve top-k prose docs -> (LLM answers from them)
"""
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
K = 8   # retrieve more docs than the KG returns, to give RAG a fair shot at multi-fact answers

_emb = None
_docs = None
_doc_emb = None

def _load():
    global _emb, _docs, _doc_emb
    if _emb is None:
        _emb = SentenceTransformer("all-MiniLM-L6-v2")
        _docs = json.load(open(DATA / "rag_docs_all.json", encoding="utf-8"))["documents"]
        _doc_emb = _emb.encode([d["text"] for d in _docs], normalize_embeddings=True)
    return _emb, _docs, _doc_emb

def rag_retrieve(question, k=K):
    """Return the top-k prose docs most similar to the question."""
    emb, docs, doc_emb = _load()
    qe = emb.encode([question], normalize_embeddings=True)[0]
    order = np.argsort(doc_emb @ qe)[::-1][:k]
    return [docs[i]["text"] for i in order]

if __name__ == "__main__":
    for q in ["Which products are authorised for late blight in Norway?",
              "Is fluazinam authorised for late blight in Norway?",
              "How many late blight products are authorised in Germany?"]:
        print(f"\nQ: {q}")
        for t in rag_retrieve(q, k=3):
            print("   -", t[:90])