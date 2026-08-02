"""
conversational_doctor.py — Phase 4/5: conversational engine (text + image turns).

Multi-turn chat over the regulation-aware retrieval backend. Dialogue state:
  - region slot: persists once set; can change mid-conversation.
  - pending text question / pending image-identified disease: remembered until a region is given.
  - history: recent turns for follow-up context.

Text turns retrieve the disease from the query. Image turns receive a disease already identified
by vision.py and ground the region-appropriate corpus entry directly. The LLM writes the advice;
the region is decided deterministically (region_gate). This module has no vision dependency.

Phase 5, Step 1 (Work Package A): retrieval is now KG-primary for the 3 diseases Programme B
validated (late blight, apple scab, cucurbit powdery mildew), via kg_retrieval_bridge.py, which
reuses Phase 1's KG and Phase 2's validated deterministic router unchanged. Every other disease
falls back to the original RAG pipeline, with an explicit notice surfaced in the reply — the
integration boundary from docs/Phase5_Design.md is enforced here, not just documented.
"""
from region_gate import detect_region, retrieve, corpus, GATE_MESSAGE, LLM, emb, doc_emb
import kg_retrieval_bridge as bridge
import verification_layer as vl
import numpy as np
import ollama

RELEVANCE = 0.35   # top-1 cosine below this = the turn isn't an answerable question
DEBUG = False      # set True to print retrieval traces (including kg/rag source) to the terminal
CORPUS_BY_ID = {r["id"]: r for r in corpus}

class Conversation:
    def __init__(self):
        self.region = None
        self.pending = None            # a text question waiting for a region
        self.pending_disease = None    # an image-identified disease (base corpus id) waiting for a region
        self.history = []

    # ---------- shared helpers ----------
    def _best_relevance(self, text, region=None):
        idx = [i for i, r in enumerate(corpus) if (region is None or r["country"] == region)]
        qe = emb.encode([text], normalize_embeddings=True)[0]
        return float((doc_emb[idx] @ qe).max())

    def _has_question(self, text, region=None):
        return self._best_relevance(text, region) >= RELEVANCE

    def _country_name(self):
        return "Germany" if self.region == "DE" else "Norway"

    def _generate(self, topic, ctx):
        recent = self.history[-3:]
        hist = "\n".join(f"User: {u}\nAssistant: {a}" for u, a in recent)
        prompt = f"""You are a plant-disease assistant helping a grower in {self._country_name()}.
Answer ONLY the specific disease or crop in question. The context may list several diseases -
use only the one that matches and ignore the rest.
Use ONLY facts from the context; do not add anything that is not in it.
Write the authority name and any database names EXACTLY as they appear in the context.
Keep it concise: a short paragraph on management, then the required national authority.

Context:
{ctx}
""" + (f"\nConversation so far:\n{hist}\n" if hist else "") + f"""
User: {topic}
Assistant:"""
        return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

    def _region_entry(self, base_id):
        """The corpus entry for a disease in the current region (NO twins are base_id + '_no')."""
        if self.region == "DE":
            return CORPUS_BY_ID.get(base_id)
        if self.region == "NO":
            return CORPUS_BY_ID.get(base_id + "_no")
        return None

    # ---------- text turns ----------
    def _grounded_answer(self, query):
        ctx, source, notice = bridge.get_context_for_query(query, self.region)
        if DEBUG:
            print(f"   [trace] query={query!r} -> source={source}")
        reply = self._generate(query, ctx)
        check = vl.verify(reply, ctx, domain="plant_protection", question=query)
        if check["flagged"]:
            if DEBUG:
                print(f"   [trace] verifier flagged: {check['reason']}")
            reply = vl.disclose(reply, check)
        if notice:
            reply += notice
        return reply

    def turn(self, message):
        old_region = self.region
        region, _ = detect_region(message)
        if region != "UNKNOWN":
            self.region = region

        # no region yet -> ask; remember the question only if it is one
        if self.region is None:
            if self._has_question(message):
                self.pending = message
            return GATE_MESSAGE

        # a photo was waiting for a region -> answer it now
        if self.pending_disease:
            did = self.pending_disease
            self.pending_disease = None
            return self._answer_for_disease(did)

        # otherwise answer the pending text question, or this message
        query = self.pending or message
        self.pending = None
        if not self._has_question(query, self.region):
            if self.region != old_region:
                return f"Got it - you're in {self._country_name()}. What would you like to know? Tell me the crop and the problem."
            return "What would you like to know? Tell me the crop and the symptoms (e.g. 'late blight on my potatoes')."
        reply = self._grounded_answer(query)
        self.history.append((query, reply))
        return reply

    # ---------- image turns ----------
    def _answer_for_disease(self, base_id):
        rec = self._region_entry(base_id)
        if rec is None:   # region is NO but this disease has no Norwegian entry
            dname = CORPUS_BY_ID.get(base_id, {}).get("disease", base_id)
            return (f"I identified **{dname}**, but I only have Norway-specific authorised guidance for "
                    f"late blight, apple scab, and powdery mildew. For this disease I can't give "
                    f"Norway-correct product advice - please consult Mattilsynet / Plantevernguiden.")
        ctx, source, notice = bridge.get_context(rec["disease"], self.region, base_id)
        if DEBUG:
            print(f"   [trace] image disease={rec['disease']!r} base_id={base_id!r} -> source={source}")
        reply = self._generate(rec["disease"], ctx)
        check = vl.verify(reply, ctx, domain="plant_protection", question=rec["disease"])
        if check["flagged"]:
            if DEBUG:
                print(f"   [trace] verifier flagged: {check['reason']}")
            reply = vl.disclose(reply, check)
        if notice:
            reply += notice
        self.history.append((f"[photo identified as {rec['disease']}]", reply))
        return reply

    def image_turn(self, vr):
        """vr = structured result from vision.identify()."""
        act = vr["action"]
        if act == "lowconf":
            lines = [f"I'm not confident about that photo (top guess **{vr['label']}**, {vr['conf']:.0%}).",
                     "Field photos are hard. It might be:"]
            lines += [f"- {n} ({p:.0%})" for n, p in vr["top3"]]
            lines.append("Could you send a clearer, single-leaf photo, or just describe the symptoms?")
            return "\n".join(lines)
        if act == "healthy":
            return f"That looks like a healthy {vr.get('crop','plant')} leaf ({vr['conf']:.0%} confidence) - no disease detected."
        if act == "abstain":
            return (f"I can identify this as **{vr['label']}** ({vr['conf']:.0%}), but it's outside my "
                    f"authorised knowledge base ({vr.get('reason','out of scope')}), so I won't give treatment advice.")
        # action == "ground": a disease we can advise on
        base_id = vr["corpus_id"]
        dname = CORPUS_BY_ID.get(base_id, {}).get("disease", vr["label"])
        if self.region is None:
            self.pending_disease = base_id
            return f"I've identified this as **{dname}** ({vr['conf']:.0%}). " + GATE_MESSAGE
        return self._answer_for_disease(base_id)

# text-only CLI for quick testing (image turns go through the Streamlit app)
if __name__ == "__main__":
    print("Plant Doctor chat - text CLI ('quit' to exit)\n")
    convo = Conversation()
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if msg.lower() in ("quit", "exit", "q"):
            break
        if not msg:
            continue
        print(f"\nDoctor [region={convo.region or 'unknown'}]: {convo.turn(msg)}\n")