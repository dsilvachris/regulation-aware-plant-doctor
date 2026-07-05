# Regulation-Aware Plant Doctor 🌱

A multimodal, regulation-aware plant-disease assistant that runs entirely on a laptop, for free —
and, more importantly, **knows when *not* to answer.**

Upload a photo of a diseased leaf → it identifies the disease → and returns treatment advice that is
*grounded in authoritative sources* and *correct for German regulation* (only BVL-authorised products).
When it isn't sure, or the disease is outside its knowledge, it **abstains instead of guessing.**

> **The through-line of this project is faithfulness over confidence** — a fluent wrong answer is worse
> than an honest "I don't know," especially when the wrong answer tells a grower to spray an
> illegal or useless chemical. I built the system, then ran an evaluation to measure exactly when
> grounding delivers that faithfulness and when it breaks.

---

## The headline finding

I built a 25-question evaluation set and compared an **ungrounded** LLM against a **grounded** (RAG) one
on a verified 12-disease corpus:

| Metric (21 in-corpus questions) | Ungrounded | Grounded (RAG) |
|---|---|---|
| Gave *useful* advice (correct **and** safe) | **19%** | **57%** |
| Knew when to abstain (out-of-corpus) | 0 / 4 | **4 / 4** |

Grounding roughly triples useful advice — and only the grounded model refuses to answer questions it
has no source for (the ungrounded model confidently fabricated all four).

But the more interesting result came from pushing further:

> **There is a usefulness ↔ faithfulness trade-off that scaling the model *shifts* but does not *eliminate*.**
> A bigger model (Llama 3.1 8B vs 3.2 3B) gives more useful advice — but, being more confident, it
> *fabricates more* on adversarial out-of-corpus questions (faithful refusal dropped from **92% → 52%**,
> confirmed across 10 repeated runs). You don't get safety for free by scaling up.

That trade-off — measured, repeatable, and honestly reported — is the core contribution.

---

## Demo

The same faithfulness principle runs through the vision front-end. The app abstains in **two** ways:

1. **Low vision confidence** → it shows the top possibilities and declines to advise.
2. **Disease outside the authorised corpus** (e.g. a disease I deliberately excluded) → it recognises
   it but refuses to give treatment advice.

| Grounded advice (confident, in-corpus) | Faithful abstention (unsure or out-of-scope) |
|---|---|
| ![advice](docs/screenshot_advice.png) | ![abstain](docs/screenshot_abstain.png) |

*(replace with your screenshots)*

---

## How it works

```
        ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
 image  │  MobileNetV2 │     │    bridge    │     │   RAG retrieval  │     │  local LLM (RAG) │
 ─────► │  (TFLite)    │ ──► │ label→corpus │ ──► │  12-disease KB   │ ──► │ grounded, BVL-   │ ──► advice
        │  28 classes  │     │ /healthy/    │     │  (EPPO + BVL)    │     │ aware answer     │
        └─────────────┘     │  abstain     │     └─────────────────┘     └──────────────────┘
              │             └──────────────┘
              ▼ low confidence → abstain
```

- **Vision:** a MobileNetV2 transfer-learned on the PlantDoc (field) dataset, exported to **TFLite** for
  portable, dependency-light inference. Confidence-gated.
- **Bridge:** maps the 28 vision classes to one of three actions — **ground** (14 classes → a corpus
  entry), **healthy** (10 classes), or **abstain** (4 classes deliberately outside the corpus). All 12
  corpus diseases are reachable from vision. *The vision abstention boundary lines up exactly with the
  corpus boundary* — the system knows the edge of its knowledge in both modalities.
- **Corpus:** 12 diseases across **5 pathogen types** (fungus, oomycete, bacterium, virus, pest), each
  with a verified **EPPO code**, the source, and a **BVL-authorisation** note. (Verifying the EPPO codes
  caught two real taxonomy errors and one missing code — *don't trust the clean-looking number.*)
- **Grounding:** sentence-transformers retrieval (cosine, k=3) + a local LLM via **Ollama**, prompted to
  answer only from the retrieved context and to surface the German regulatory rule.

Everything is **local and €0** — no paid APIs, no cloud.

---

## What I measured (and what broke)

A four-condition experiment plus a retrieval fine-tuning study, all on the held-out 25-question set:

| Experiment | Result |
|---|---|
| Grounded vs ungrounded | Useful advice 19% → **57%**; abstention 0/4 → **4/4** |
| Strict prompt | **Over-refuses ~1/3 of answerable questions**, systematically on the hardest (trap) cases |
| Prompt fix attempt | **Failed** — a sound fix couldn't beat the 3B model's capability limit |
| Bigger model (8B) | More useful, but **less faithful** on adversarial out-of-corpus (92%→52%) |
| Retrieval threshold | Restores faithful refusal (2/4 → 4/4) at a small, characterised cost |
| Fine-tuned domain embedder | Retrieval top-1 **76% → 86%** (zero regressions)… |
| …but | …it **recalibrated the score scale**, breaking the fixed threshold — the two fixes don't compose |
| Repeated runs (×10) | Confirmed the trade-off with error bars; revealed an apparent single-run gain was noise |
| **Multi-region (Germany→Norway)** | Region-faithful when the region is known or inferable — **but silently defaults to the majority region when none is given** (fixed by a region gate; see below) |
| **Conversational layer** | Multi-turn chat that tracks region across turns, asks when it's missing, and grounds each answer — the region gate becomes the first dialogue slot |

The recurring theme: most "wins" hid a catch one layer down, and the eval set is what surfaced them.
Full write-up with all numbers and caveats in [`docs/Results_Note_Regulation-RAG_Eval-v1.md`](docs/Results_Note_Regulation-RAG_Eval-v1.md).

---

## Multi-region extension: Germany → Norway

Because the system is *regulation-aware*, the sharpest test is whether the **same disease** gets correctly
**different** advice across a regulatory border. I added a Norwegian corpus slice (authority
**Mattilsynet** instead of Germany's BVL; products checked against Norway's **Plantevernguiden** database)
for three shared diseases, and probed the boundary.

**What holds:** given a stated or *inferable* region, the system is region-faithful — it cites the right
national authority, refuses to transfer a German product recommendation across the border ("check
Plantevernguiden — a German authorisation doesn't carry over"), and even infers region from a place name
("near Hardanger" → Norway).

**What breaks (the finding):** when **no region is given at all**, behaviour is unsafe — the system
*silently assumes* a region rather than asking, defaulting to whichever region dominates the corpus
(Germany). The mechanism is corpus imbalance leaking through retrieval into generation. It's the project's
signature failure — *confident where it should be uncertain* — reappearing on the geographic axis.

**The fix (built):** a **region gate** that determines the region by an explicit, auditable rule —
explicit country words, then a curated place gazetteer — and *asks* the grower which country they're in
when the region can't be determined, instead of guessing. The region decision is deliberately kept out of
the LLM (its geography is uneven and unverifiable); the model only writes the advice. On the probe set the
gate asks exactly on the true no-region cases and never guesses a region wrongly — the geographic analogue
of the retrieval threshold above.

---

## Conversational layer

The region gate created a need for multi-turn dialogue: it *asks* which country you're in, so the system
has to receive the answer and continue. The conversational layer (a **Streamlit chat UI** over the same
grounded engine) makes that work, tracking dialogue state across turns:

- **region slot** — set once, then *persists*; ask about several crops in a row without repeating your
  country, and switch region mid-conversation ("actually I'm in Germany") and later answers follow.
- **pending question** — ask about a disease before giving a region, and the assistant remembers the
  question, asks for the region, then answers the *original* question.
- **answer-only-if-asked** — a turn is answered only if it actually contains a question (judged by
  retrieval relevance); a bare region change is acknowledged, not answered with a fabricated response.
- **multimodal turns** — you can *upload a leaf photo inside the chat*: the vision model identifies the
  disease, the region gate still applies, and the answer is grounded and region-correct. An image simply
  fills the "disease" slot the way a text description does. This unites the two halves of the project —
  the vision app and the chatbot — into one assistant. Vision-side abstention carries over: low-confidence
  or out-of-corpus photos are declined rather than guessed, and a disease with no region-specific entry
  (e.g. a German-only disease asked about in Norway) is flagged honestly.

The region decision stays deterministic (gate + gazetteer); the LLM writes the grounded advice. It's a
task-oriented, multimodal dialogue agent, not a stateless Q&A wrapper.

---

## Honest limitations

- Small scale: 25 eval questions, a 12-disease corpus, hand-graded by one person. Directions are clear;
  exact percentages would firm up with more questions, more graders, and more repeated runs.
- The vision model is ~50% on real field images (a documented lab→field generalisation gap) — which is
  *why* the confidence gate matters, and the app abstains often on genuine field photos.
- This is a research prototype and portfolio project, **not** a deployable agricultural advisory tool.

---

## Tech stack

`Python` · `Ollama` (Llama 3.2 3B / 3.1 8B) · `sentence-transformers` (MiniLM, fine-tuned) ·
`TensorFlow Lite` (`ai-edge-litert`) · `MobileNetV2` · `Gradio` (vision app) · `Streamlit` (chat) ·
all local, zero-budget.

## Run it

```bash
# 1. Local LLM
ollama serve            # in one terminal
ollama pull llama3.2:3b

# 2. Environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3a. Image-based plant doctor (Gradio)
python src/plant_doctor_app.py

# 3b. Conversational plant doctor (Streamlit chat)
streamlit run src/streamlit_app.py
```

## Repo structure

```
data/       corpus (DE + NO), eval sets, vision bridge, class labels
models/     agro_vision.tflite (vision model)
src/        all code:
              plant_doctor_app.py     image -> grounded advice (Gradio)
              streamlit_app.py        multimodal chat UI (text + image)
              conversational_doctor.py multi-turn dialogue engine (text + image turns)
              vision.py               TFLite leaf-image identifier (shared by the chat)
              region_gate.py          deterministic region resolver
              run_eval.py             grounded-vs-ungrounded evaluation
              finetune_embedder.py    domain embedder fine-tuning
              strengthen.py           repeated-run rigor pass
              region_eval.py / region_probe.py  multi-region experiments
results/    graded eval scores, strengthen + region results
docs/       results note, reflection, plan
```

---

*Built as a portfolio project and a research starting point in regulation-aware, multimodal AI assistants.*
