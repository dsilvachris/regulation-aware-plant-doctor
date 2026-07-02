"""
conversational_doctor.py — Phase 4 (start): the conversational layer.

Multi-turn chat over the regulation-aware RAG. Dialogue state:
  - region slot: PERSISTS once set; can be changed mid-conversation.
  - pending question: if you ask before giving a region, it's remembered and answered
    once you supply the region.
  - history: recent turns passed to the model so follow-ups have context.

A turn is only ANSWERED if it actually contains an answerable question, judged by retrieval
relevance (top-1 similarity >= RELEVANCE). A bare region change ("actually I'm in Germany")
scores low, so the assistant acknowledges and waits instead of fabricating an answer
(the Phase-2 retrieval-threshold idea, reused to decide "is this turn even a question?").

Composes region_gate.py (deterministic region detection + region-aware retrieval).
"""
from region_gate import detect_region, retrieve, corpus, GATE_MESSAGE, LLM, emb, doc_emb
import numpy as np
import ollama

RELEVANCE = 0.35   # top-1 cosine below this = the turn isn't an answerable question
DEBUG = False      # set True to print retrieval traces to the terminal

class Conversation:
    def __init__(self):
        self.region = None
        self.pending = None
        self.history = []

    def _best_relevance(self, text, region=None):
        idx = [i for i, r in enumerate(corpus) if (region is None or r["country"] == region)]
        qe = emb.encode([text], normalize_embeddings=True)[0]
        return float((doc_emb[idx] @ qe).max())

    def _has_question(self, text, region=None):
        return self._best_relevance(text, region) >= RELEVANCE

    def _grounded_answer(self, query):
        top = retrieve(query, self.region)
        if DEBUG:
            print(f"   [trace] query={query!r} -> retrieved: {[r['id'] for r in top]}")
        ctx = "\n\n".join(f"[{r['id']} | {r['country']}] {r['text']}" for r in top)
        country = "Germany" if self.region == "DE" else "Norway"
        recent = self.history[-3:]
        hist = "\n".join(f"User: {u}\nAssistant: {a}" for u, a in recent)
        prompt = f"""You are a plant-disease assistant helping a grower in {country}.
Answer ONLY the specific disease or crop the user asks about in their latest message. The context
may list several diseases - use only the one that matches the question and ignore the rest.
Use ONLY facts from the context; do not add anything that is not in it.
Write the authority name and any database names EXACTLY as they appear in the context - do not rename or re-expand them.
Keep it concise: a short paragraph on management, then the required national authority.

Context:
{ctx}
""" + (f"\nConversation so far:\n{hist}\n" if hist else "") + f"""
User: {query}
Assistant:"""
        return ollama.generate(model=LLM, prompt=prompt)["response"].strip()

    def turn(self, message):
        old_region = self.region
        region, _ = detect_region(message)
        if region != "UNKNOWN":
            self.region = region

        # no region yet -> ask; remember the question only if it IS one
        if self.region is None:
            if self._has_question(message):
                self.pending = message
            return GATE_MESSAGE

        # region known -> resolve which text is the actual question
        query = self.pending or message
        self.pending = None

        # turn carries no answerable question -> acknowledge / prompt, don't fabricate
        if not self._has_question(query, self.region):
            country = "Germany" if self.region == "DE" else "Norway"
            if self.region != old_region:
                return f"Got it - you're in {country}. What would you like to know? Tell me the crop and the problem."
            return "What would you like to know? Tell me the crop and the symptoms (e.g. 'late blight on my potatoes')."

        reply = self._grounded_answer(query)
        self.history.append((query, reply))
        return reply

if __name__ == "__main__":
    print("Regulation-Aware Plant Doctor - chat (type 'quit' to exit)\n")
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
        reply = convo.turn(msg)
        print(f"\nDoctor [region={convo.region or 'unknown'}]: {reply}\n")