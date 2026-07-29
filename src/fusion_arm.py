"""
fusion_arm.py — Phase 3, Step 2: the evidence-fusion arm.

Retrieves via BOTH existing arms (kg_arm's deterministic SPARQL, rag_arm's semantic top-k) — no new
retrieval logic — and answers using one of two pre-registered fusion prompts, written from general
principles BEFORE any fusion answer has ever been generated, same audit-trail discipline as
llm_router.py's ROUTER_PROMPT (pre-registered, not tuned to a known outcome — there is no outcome to tune
to yet, since Step 3 hasn't run).

  NAIVE_FUSION_PROMPT      : both fact sets concatenated, one added instruction (say so if sources
                             conflict, don't silently pick one). Tests whether simply giving the model
                             both verified fact sets helps or dilutes/confuses it.
  STRUCTURED_FUSION_PROMPT : facts explicitly labeled by provenance and reliability, an explicit priority
                             rule (prefer KG for authorisation/relational facts, RAG only fills gaps), and
                             — grounded directly in Phase 3 Step 1's finding, not generic boilerplate — an
                             explicit instruction to verify that each source's claim concerns the SAME
                             country and disease as the question before using it. Step 1
                             (docs/Phase3_Step1_ConflictDiagnosis.md) found zero real KG/RAG factual
                             conflicts in this data, but did find RAG's top-k retrieval regularly surfaces
                             same-substance-different-country/-disease documents (e.g. n02: KG says
                             fluazinam is NOT authorised in Norway; RAG's retrieved doc describes BANJO's
                             GERMAN authorisation — both true, no conflict, but a fusion model that doesn't
                             track which country each claim belongs to could misread this as agreement).
                             That is the concrete risk this variant is designed to test against.

Both variants reuse exactly the retrieval eval_pipeline.py's kg_answer_by_id()/rag_answer() already use:
kg_arm's category-routed SPARQL (ep.route) and rag_arm's top-k semantic retrieval (k=8, matching
rag_arm.py's own default K). facts_text is computed WITHOUT calling explain()/Ollama for the KG side
(same helper pattern as phase3_step1_diagnose_conflicts.py), then both fact sets are handed to Ollama
together via the fusion prompt.

--- Amendment (before Step 3, before any grading has happened) ---
The Step 2 demo (3 questions, both variants) surfaced a real fabrication: on xd_02, BOTH naive and
structured fusion stated azoxystrobin is "authorised against late blight, apple scab, and cucurbit powdery
mildew" and explicitly attributed this to "the KG facts" — but the KG facts_text for this question only
says azoxystrobin covers "more than one" of the three diseases, naming none, and none of the 8 retrieved
RAG documents mention apple scab or powdery mildew at all (all 8 are late-blight-only). Two of the three
named diseases happen to be correct (verified directly against kg_arm); apple scab is not. This is a
genuine, confirmed fabrication misattributed to a verified source, not a retrieval-attribution error (the
retrieved documents don't contain the fabricated content either). STRUCTURED_FUSION_PROMPT's rule 4 below
was added in direct response to this finding, before any Step 3 generation or grading — the same
demo-then-refine practice used to develop Phase 2's prompt variants. NAIVE_FUSION_PROMPT is intentionally
left unchanged (it stays the fixed, deliberately-minimal baseline for the whole phase, same discipline as
Phase 2's PROMPT_A).

Run: python src/fusion_arm.py   -> demo on a few benchmark questions, both prompt variants
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pipeline as ep
import rag_arm
import ollama

LLM = "llama3.2:3b"


def kg_facts_text(qid):
    """Same KG facts text eval_pipeline.kg_answer_by_id() would show the LLM — computed without calling
    explain()/Ollama, so it can be reused freely (e.g. for both fusion prompt variants) without extra
    generation cost."""
    query_fn, params, vcat = ep.route(qid)
    facts = query_fn(**params)
    facts_text = ep.verbalise3(vcat, facts) or ep.verbalise2(vcat, facts)
    if facts_text is None:
        facts_text = ep.verbalise(vcat, facts)
    return facts_text or ""


def rag_facts_text(question, k=8):
    docs = rag_arm.rag_retrieve(question, k=k)
    return "\n".join(f"- {d}" for d in docs)


# --- PRE-REGISTERED FUSION PROMPTS (written before Step 3 has generated a single fusion answer) ---

NAIVE_FUSION_PROMPT = """You are a plant-protection regulatory assistant. Answer the question using ONLY
the facts provided below. If the facts do not support an answer, say so plainly — do not guess and do not
add information that is not in the facts. If the two fact sources below disagree, say so explicitly rather
than silently picking one. Be concise and precise.

KG FACTS:
{kg_facts}

RETRIEVED DOCUMENTS:
{rag_facts}

QUESTION: {question}
ANSWER:"""

STRUCTURED_FUSION_PROMPT = """You are a plant-protection regulatory assistant. Answer the question using
ONLY the facts provided below.

KG FACTS (verified, authoritative — precisely filtered for the country and disease in the question):
{kg_facts}

RETRIEVED DOCUMENTS (may be incomplete, and may describe a DIFFERENT country or disease than the one
asked about — check this before using a document's claim):
{rag_facts}

Rules:
1. Before using any fact from either source, check it actually concerns the SAME country and disease as
   the question. A document mentioning the right substance but a different country or disease does not
   support an answer.
2. If the KG facts and a genuinely on-topic retrieved document disagree, prefer the KG facts for
   authorisation, counts, and any relationship between products, substances, or countries — the KG is
   verified and precisely filtered; retrieved documents are similarity-matched and may include off-topic
   material.
3. Use a retrieved document only to fill a gap the KG facts do not cover, and only if it is genuinely
   on-topic per rule 1.
4. If a source makes only an AGGREGATE claim (e.g. "authorised against more than one disease") without
   naming specifics, do not supply the specifics yourself unless another provided fact states them
   explicitly. Do not fill in plausible-sounding detail that isn't actually written in the facts, and
   never attribute an invented detail to a source that didn't state it.
5. If neither source supports an answer, say so plainly — do not guess.
Be concise and precise.

QUESTION: {question}
ANSWER:"""

FUSION_PROMPTS = {"naive": NAIVE_FUSION_PROMPT, "structured": STRUCTURED_FUSION_PROMPT}


def fusion_answer(qid, question, variant="naive"):
    """Returns (answer_text, kg_facts, rag_facts). One Ollama call."""
    kg_facts = kg_facts_text(qid)
    rag_facts = rag_facts_text(question)
    prompt = FUSION_PROMPTS[variant].format(kg_facts=kg_facts, rag_facts=rag_facts, question=question)
    answer = ollama.generate(model=LLM, prompt=prompt)["response"].strip()
    return answer, kg_facts, rag_facts


if __name__ == "__main__":
    demo = [
        ("m01", "Which active substances are authorised against late blight in Norway?"),
        ("n02", "Is the German late blight product BANJO (fluazinam) authorised in Norway?"),
        ("xd_02", "Is azoxystrobin used against only a single disease among the three studied?"),
    ]
    for qid, q in demo:
        print(f"\n=== {qid}: {q} ===")
        kg_f = kg_facts_text(qid)
        rag_f = rag_facts_text(q)
        print(f"\n  KG FACTS:\n    {kg_f}")
        print(f"\n  RAG FACTS (top-8 retrieved docs):")
        for line in rag_f.split("\n"):
            print(f"    {line}")
        for variant in FUSION_PROMPTS:
            prompt = FUSION_PROMPTS[variant].format(kg_facts=kg_f, rag_facts=rag_f, question=q)
            answer = ollama.generate(model=LLM, prompt=prompt)["response"].strip()
            print(f"\n  [{variant}] {answer}")