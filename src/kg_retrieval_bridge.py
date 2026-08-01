"""
kg_retrieval_bridge.py — Phase 5, Step 1: Work Package A, architecture integration.

Replaces Programme A's plain-RAG-only retrieval with KG-primary retrieval + Phase 2's validated
deterministic router, for exactly the 3 diseases Programme B actually validated (late blight, apple
scab, cucurbit powdery mildew — docs/Phase1_Results.md). For every other disease in Programme A's
original 12-disease corpus, falls back to the original RAG pipeline with an explicit, visible scope
notice — the integration boundary from Phase5_Design.md is enforced here in code, not left as
documentation the running system can silently ignore.

Reuses, unmodified, not reimplemented:
  - phase2_step2b_deterministic_router.py's classify_deterministic() — the actual validated rule.
  - kg_arm.py's q_products_in_country() — Phase 1's validated deterministic query.
  - kg_verbalise.py's verbalise() — the corrected verbaliser (post disease-name-bug fix,
    Correction_KG_Disease_Name_Bug.md).
  - region_gate.py's retrieve() — the original RAG path, used whenever the router says "rag" or the
    disease is out of the KG's validated scope.

Disease identification for free-text queries is deliberately cheap and reuses the SAME embedding
retrieval already used for RAG: the top-1 semantic match's underlying disease is treated as "what this
query is about," formalising a step the RAG path was already doing implicitly. This does not change RAG
behaviour when RAG is actually used — the top-k retrieval for the answer itself is unchanged.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kg_arm
from kg_verbalise import verbalise
from phase2_step2b_deterministic_router import classify_deterministic
import region_gate

# Maps Programme A's corpus base id -> Phase 1 KG's disease key. ONLY the 3 diseases Programme B
# actually validated. Every other corpus disease is intentionally absent — falls through to RAG with
# an explicit notice, per Phase5_Design.md's stated integration boundary.
VALIDATED_DISEASE_MAP = {
    "tomato_potato_late_blight": "late_blight",
    "apple_scab": "apple_scab",
    "cucurbits_powdery_mildew": "powdery_mildew",
}

OUT_OF_SCOPE_NOTICE = (
    " *(This disease is outside the knowledge-graph-validated scope of this assistant — the answer "
    "above is generated from retrieved documents only, not verified structured data. Currently "
    "KG-validated: late blight, apple scab, cucurbit powdery mildew.)*"
)


def _strip_region_suffix(corpus_id):
    return corpus_id[:-3] if corpus_id.endswith("_no") else corpus_id


def identify_disease(query, region):
    """Cheap disease identification for free-text queries: the top-1 embedding match's base corpus id.
    Formalises what the RAG path was already doing implicitly via top-k retrieval; does not change
    RAG's own answer-context retrieval, which still runs its own top-k when RAG is selected."""
    top1 = region_gate.retrieve(query, region, k=1)
    if not top1:
        return None
    return _strip_region_suffix(top1[0]["id"])


def get_context(query, region, base_id):
    """
    Returns (context_text, source_label, notice):
      source_label in {"kg", "rag", "rag-out-of-scope"}
      notice is None, or a user-facing disclosure string to append to the reply.
    """
    if base_id in VALIDATED_DISEASE_MAP:
        disease_key = VALIDATED_DISEASE_MAP[base_id]
        decision = classify_deterministic(query)
        if decision == "kg":
            facts = kg_arm.q_products_in_country(country=region, disease=disease_key)
            facts_text = verbalise("region_specific", facts)
            return facts_text, "kg", None
        # decision == "rag": still validated-scope, use the original RAG retrieval unchanged
        top = region_gate.retrieve(query, region)
        ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
        return ctx, "rag", None

    # Out-of-scope disease: original RAG pipeline, with an explicit, visible notice
    top = region_gate.retrieve(query, region)
    ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
    return ctx, "rag-out-of-scope", OUT_OF_SCOPE_NOTICE


def get_context_for_query(query, region):
    """For text turns: identify the disease first, then get_context()."""
    base_id = identify_disease(query, region)
    return get_context(query, region, base_id)


if __name__ == "__main__":
    demo = [
        ("Which products are authorised against late blight in Germany?", "DE"),
        ("What pathogen causes late blight?", "DE"),
        ("Is my apple scab treatable in Norway?", "NO"),
        ("How do I deal with tomato mosaic virus?", "DE"),  # out-of-scope disease
    ]
    for q, region in demo:
        ctx, source, notice = get_context_for_query(q, region)
        print(f"\nQ: {q}  [{region}]")
        print(f"  source={source}")
        print(f"  context: {ctx[:150]}")
        if notice:
            print(f"  notice: {notice}")