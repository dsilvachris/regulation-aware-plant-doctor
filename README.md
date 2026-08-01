# Regulation-Aware Plant Doctor 🌱

A research program on **grounding language models for regulated, high-stakes advice** — built around one
question, tested from four different angles: *when does giving an LLM verified structure actually make it
more trustworthy, and when does that trust break down?*

This repo now holds two connected pieces of work:

- **Programme A** — a working, local, multimodal plant-disease assistant (vision → grounded advice → a
  region-aware conversational layer), and the evaluation that shows grounding roughly triples useful advice
  over an ungrounded baseline. This was the original prototype and the source of the project's guiding
  principle: **faithfulness over confidence.**
- **Programme B** — a four-phase, rigorously pre-registered research program that takes that principle and
  stress-tests it properly: does a knowledge graph actually beat document-RAG for regulatory reasoning
  (Phase 1)? Can an LLM be trusted to *route* between retrieval strategies (Phase 2)? Can it be trusted to
  *reconcile* two evidence sources into one answer (Phase 3)? Does any of this generalise beyond the
  original domain (Phase 4)?

> **The through-line across both programmes:** a fluent wrong answer is worse than an honest "I don't
> know." Programme A built a system around that principle. Programme B spent four phases finding out
> exactly where that principle holds, where it's harder to guarantee than it looks, and where — as Phase 4
> discovered — even the "safe" arm turns out to fabricate sometimes.

---

## Quick navigation

- [Programme A: the grounded assistant](#programme-a--the-grounded-plant-disease-assistant)
- [Programme B: does structure actually help?](#programme-b--does-structure-actually-help-an-llm-get-regulation-right)
  - [Phase 1 — Retrieval isolation (KG vs RAG)](#phase-1--retrieval-isolation-kg-vs-rag)
  - [Phase 2 — Adaptive retrieval (can an LLM route safely?)](#phase-2--adaptive-retrieval-can-an-llm-route-safely)
  - [Phase 3 — Hybrid retrieval & evidence fusion](#phase-3--hybrid-retrieval--evidence-fusion)
  - [Phase 4 — Generalisation to healthcare](#phase-4--generalisation-to-healthcare-fda-vs-ema)
  - [What four phases of this add up to](#what-four-phases-of-this-add-up-to)
- [Repo structure](#repo-structure)
- [Honest limitations](#honest-limitations)
- [Run it](#run-it)

---

## Programme A — the grounded plant-disease assistant

Upload a photo of a diseased leaf → it identifies the disease → and returns treatment advice that is
*grounded in authoritative sources* and *correct for German regulation* (only BVL-authorised products).
When it isn't sure, or the disease is outside its knowledge, it **abstains instead of guessing.**

### The headline finding

A 25-question evaluation set, ungrounded LLM vs grounded (RAG) LLM, on a verified 12-disease corpus:

| Metric (21 in-corpus questions) | Ungrounded | Grounded (RAG) |
|---|---|---|
| Gave *useful* advice (correct **and** safe) | **19%** | **57%** |
| Knew when to abstain (out-of-corpus) | 0 / 4 | **4 / 4** |

Grounding roughly triples useful advice — and only the grounded model refuses to answer questions it has
no source for. Pushing further: **a bigger model (8B vs 3B) gives more useful advice but fabricates more**
on adversarial out-of-corpus questions (faithful refusal dropped 92% → 52%, confirmed across 10 repeated
runs). You don't get safety for free by scaling up — a finding Programme B would end up re-confirming from
a completely different angle in Phase 2.

### How it works

```
        ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
 image  │  MobileNetV2 │     │    bridge    │     │   RAG retrieval  │     │  local LLM (RAG) │
 ─────► │  (TFLite)    │ ──► │ label→corpus │ ──► │  12-disease KB   │ ──► │ grounded, BVL-   │ ──► advice
        │  28 classes  │     │ /healthy/    │     │  (EPPO + BVL)    │     │ aware answer     │
        └─────────────┘     │  abstain     │     └─────────────────┘     └──────────────────┘
              │             └──────────────┘
              ▼ low confidence → abstain
```

- **Vision:** MobileNetV2 transfer-learned on PlantDoc (field images), exported to TFLite, confidence-gated.
- **Bridge:** maps 28 vision classes to *ground* (14 → corpus entry), *healthy* (10), or *abstain* (4,
  deliberately outside the corpus). The vision abstention boundary lines up exactly with the corpus
  boundary.
- **Corpus:** 12 diseases across 5 pathogen types, each with a verified EPPO code, source, and
  BVL-authorisation note. (Verifying the EPPO codes caught two real taxonomy errors — the "don't trust the
  clean-looking number" lesson that recurs throughout Programme B too.)
- **Grounding:** sentence-transformers retrieval (cosine, k=3) + a local LLM via Ollama, prompted to answer
  only from retrieved context.

Everything local, €0 — no paid APIs, no cloud.

### Multi-region extension and the conversational layer

Because the system is *regulation-aware*, the sharpest test is whether the same disease gets correctly
*different* advice across a regulatory border. A Norwegian corpus slice (Mattilsynet instead of BVL) for
three shared diseases probed exactly this — and found the project's signature failure reappearing on a new
axis: with no region stated, the system silently defaulted to the majority region instead of asking. Fixed
with a deterministic **region gate** (explicit rule, not an LLM judgment) that asks when the region can't be
determined. A **Streamlit chat layer** then made that gate usable in multi-turn dialogue: region persists
across turns, pending questions are remembered while the region is requested, and photo uploads fill the
"disease" slot the same way text does.

Full write-up: [`docs/Results_Note_Regulation-RAG_Eval-v1.md`](docs/Results_Note_Regulation-RAG_Eval-v1.md).
Reflection: [`docs/Stage7_Interpretation.md`](docs/Stage7_Interpretation.md).

---

## Programme B — does structure actually help an LLM get regulation right?

Programme A showed grounding helps *in general*. Programme B asks the harder, more specific questions a
supervisor-split thesis chapter needs answered: **which kind of grounding, delegated how much, and does
any of it hold up outside the one domain it was built in?**

Every phase follows the same discipline, carried consistently across all four: **design and pre-register
predictions before running anything → build → verify against the real, live data (not synthetic
placeholders) → run multi-run, never trust a single pass → grade blind → report confirmations and
disconfirmations honestly, including the ones that complicate the story.** Real bugs were found in nearly
every phase — a hardcoded disease-name bug, an ambiguous KG template, a data-parity gap between two arms —
and every one is documented in full rather than quietly fixed and forgotten, because how those bugs were
found is as much a part of the contribution as the headline numbers.

### Phase 1 — Retrieval isolation (KG vs RAG)

**Question:** for a plant-protection regulation domain (Germany vs Norway authorisation data), does a
curated knowledge graph produce more correct, more faithful answers than document-RAG — and if so, on
which *kinds* of questions?

**Finding:** KG outperforms RAG, and the advantage is concentrated exactly where you'd expect structure to
matter — relational, absence ("is X *not* authorised"), and cross-border questions — while a simple factual
lookup shows no advantage either way (a clean bias-check). A pre-registered hierarchy-traversal category
turned out not to be instantiable in this 3-disease dataset — reported honestly as a real limitation, not
forced. Corrected mid-project after a downstream diagnostic (Phase 3) found a bug that had been silently
depressing KG's own scores: KG **62.0%** / RAG **39.5%** correctness, final.

📄 [`docs/Phase1_Results.md`](docs/Phase1_Results.md)

### Phase 2 — Adaptive retrieval: can an LLM route safely?

**Question:** if you could always route a question to whichever arm (KG or RAG) handles it better, could an
LLM do that routing — and is it worth the cost of asking one to?

**Finding:** a deterministic rule (four lines of regex) matches the achievable ceiling exactly, with
perfect run-to-run stability and zero risky-category misroutes. No LLM-router variant tested clearly beats
it once measured honestly under repetition — the prompt variant that looked *best* on proxy metrics
actually underperformed a naive always-KG baseline on real correctness, and the variant with the largest
real gain was also the least stable (55% self-consistency across runs). **The core conclusion: for this
task and this model class, a transparent rule beats LLM-based routing.**

📄 [`docs/Phase2_Results.md`](docs/Phase2_Results.md) · full step-by-step trail in
[`docs/Phase2_Design.md`](docs/Phase2_Design.md), [`Phase2_Plan.md`](docs/Phase2_Plan.md), and four
intermediate results docs.

### Phase 3 — Hybrid retrieval & evidence fusion

**Question:** routing only ever picks *one* arm's evidence. What if the system combined both — does that
close more of the gap to the theoretical ceiling, and can the LLM be trusted to reconcile two sources
without fabricating or silently resolving disagreement?

**Finding:** genuinely mixed. A minimal ("naive") fusion prompt gives a small, real edge over the
deterministic router. A more carefully structured fusion prompt gives a much larger apparent edge — but
that headline result could not be independently validated (a self-regrade came back with suspiciously
perfect agreement, meaning it confirmed internal consistency, not correctness) and is reported as
provisional, not confirmed. The phase's most important result wasn't in the win/loss column at all: both
fusion variants were caught fabricating a specific, wrong detail and **explicitly misattributing it to the
verified knowledge-graph source** — and a prompt instruction telling the model not to invent things did
**not** fix it. The real fix required rewriting the ambiguous *source* text the model was reading, not the
prompt. That's a generalisable methodological finding in its own right: some faithfulness failures live in
the data, not the instructions.

📄 [`docs/Phase3_Results.md`](docs/Phase3_Results.md) · design, plan, and four step docs alongside it.

### Phase 4 — Generalisation to healthcare (FDA vs EMA)

**Question:** does the Phase 1 finding — structure helps on relational/absence/cross-border/hierarchical
questions, not on simple lookups — replicate in a second regulated domain, built completely independently?

**Method:** live-sourced data from `openFDA`, the EU's EMA, and NLM's RxClass — 8 real
pharmaceutical substances (Alzheimer's and oncology drugs, chosen after a feasibility check ruled out
common generics as unsuitable), a 14-question benchmark spanning all 7 original categories. This finally
made **hierarchy-traversal testable for the first time in the whole project**, via ATC drug classification
— the oldest open thread in this thesis, closed here.

**Finding:** yes, directionally, at a comparable-or-larger magnitude (KG 88%/86% vs RAG 45%/76%) — but the
clean version of that story is wrong. The KG arm itself **hallucinated on a short, unambiguous,
single-fact question in 2 of 3 runs**, fabricating a detail nowhere in its own source data — caught only
because of multi-run testing; a single-run demo earlier in the phase would have reported KG as flawless.
Separately, both arms failed equally at a "list all N matching items" hierarchy question even when the
KG's facts were complete and correct — a shared small-model limitation, not a knowledge-representation
difference. A real data-parity bug (one arm's prose was missing a fact the other stated) was found and
fixed mid-phase rather than left in. **The honest conclusion, four phases in: structure reduces
fabrication risk and enables real relational/hierarchical reasoning — it does not eliminate fabrication,
even in the "gold-standard" arm, and some limitations are about the model, not the retrieval strategy.**

📄 [`docs/Phase4_Results.md`](docs/Phase4_Results.md) · feasibility, design, plan, and step docs alongside it.

### What four phases of this add up to

- **Tiered trust, tested rung by rung.** Phase 1 kept the LLM out of retrieval entirely. Phase 2 let it (or
  a rule) *select* between two verified sources — the rule won. Phase 3 asked it to *reconcile* two
  sources — genuinely mixed, with one clear new risk found. Phase 4 asked whether any of this holds outside
  the original domain — mostly yes, with the sharpest caveat of the whole project (the KG hallucination)
  showing up exactly there.
- **Multi-run testing repeatedly overturned single-run impressions** — the LLM router's apparent
  reliability in Phase 2, and the KG arm's apparent flawlessness on `r2` in Phase 4, both looked clean on
  one pass and were not, once repeated.
- **Every phase found and fixed a real bug**, documented rather than smoothed over: a hardcoded disease
  name that had been silently depressing scores since Phase 1 (caught in Phase 3), an ambiguous KG template
  that caused a confirmed fabrication (Phase 3), and a data-parity gap between two arms (Phase 4). How these
  were found — mostly by refusing to trust a good-looking number without checking it against source data —
  is as much the contribution as the headline results.

---

## Repo structure

```
data/       Programme A: DE+NO corpus, eval sets, vision bridge, class labels
            Programme B: kg_all.ttl / rag_docs_all.json (Phase 1), benchmark files (all phases),
                          kg_phase4.ttl / rag_docs_phase4.json + sourced FDA/EMA data (Phase 4),
                          grading sheets + keys (blind, per phase)
models/     agro_vision.tflite (Programme A vision model)

src/        Programme A:
              plant_doctor_app.py       image -> grounded advice (Gradio)
              streamlit_app.py          multimodal chat UI (text + image)
              conversational_doctor.py  multi-turn dialogue engine
              vision.py                 TFLite leaf-image identifier
              region_gate.py            deterministic region resolver
              run_eval.py / finetune_embedder.py / strengthen.py / region_eval.py / region_probe.py

            Programme B, Phase 1: build_kg.py, kg_arm.py, kg_verbalise.py, rag_arm.py, eval_pipeline.py,
                                   stage6_eval.py, verify_*.py (ground-truth verification)
            Programme B, Phase 2: phase2_step*.py (oracle ceiling, deterministic router, LLM router,
                                   prompt-sensitivity, multi-run robustness, cost-of-misrouting)
            Programme B, Phase 3: fusion_arm.py, phase3_step*.py (conflict diagnosis, fusion generation,
                                   scoring, second-grading agreement check)
            Programme B, Phase 4: phase4_step0_feasibility.py, phase4_step2_source_data.py,
                                   build_kg_phase4.py, kg_arm_phase4.py, kg_verbalise_phase4.py,
                                   rag_arm_phase4.py, eval_pipeline_phase4.py, phase4_step5_generate.py,
                                   phase4_step6_scoring.py
            Programme B, corrections: correction_regenerate_kg_answers.py,
                                   correction_merge_and_recompute.py

results/    Programme A: graded eval scores, strengthen + region results

docs/       Programme A: BASELINE.md, Feasibility_Report.md, Literature_Review.md,
                          Results_Note_Regulation-RAG_Eval-v1.md, Stage7_Interpretation.md,
                          RESEARCH_README.md, Benchmark_Design_Stage2.md, Thesis_Chapter_Map.md
            Programme B: Phase1_Results.md
                          Phase2_Design.md / Plan.md / Results.md + 4 step docs
                          Phase3_Design.md / Plan.md / Results.md + 4 step docs
                          Phase4_Design.md / Plan.md / Results.md + 2 step docs
                          Correction_KG_Disease_Name_Bug.md (the mid-project data-quality correction)
```

---

## Honest limitations

**Programme A:** small scale (25 eval questions, 12-disease corpus, hand-graded by one person); the vision
model is ~50% on real field images (a documented lab→field generalisation gap, which is why the confidence
gate matters); a research prototype, not a deployable agricultural advisory tool.

**Programme B:** a single grader across Phases 3 and 4, with an attempted independent-validation check in
Phase 3 that came back uninformative rather than confirmatory — stated as an open limitation, not
resolved; Phase 4's 14-question benchmark is smaller than Phase 1's 51, producing ceiling effects on some
categories that couldn't discriminate between arms; every phase's local LLM is a 3B model, and Phase 2's
own finding (a larger model changes reliability) has not been re-tested against Phases 3 or 4.

**Both programmes:** research and portfolio work, not deployable products, and nothing here is medical,
agricultural, or regulatory advice.

---

## Tech stack

`Python` · `Ollama` (Llama 3.2 3B / 3.1 8B) · `sentence-transformers` (MiniLM, fine-tuned) · `rdflib` (KG
construction and SPARQL) · `TensorFlow Lite` (`ai-edge-litert`) · `MobileNetV2` · `Gradio` (vision app) ·
`Streamlit` (chat) · live data from `openFDA`, EMA, RxClass, BVL, and Mattilsynet · all local, zero-budget.

## Run it

```bash
# 1. Local LLM
ollama serve            # in one terminal
ollama pull llama3.2:3b

# 2. Environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3a. Programme A — image-based plant doctor (Gradio)
python src/plant_doctor_app.py

# 3b. Programme A — conversational plant doctor (Streamlit chat)
streamlit run src/streamlit_app.py

# 3c. Programme B — any phase's evaluation pipeline, e.g. Phase 1:
python src/stage6_eval.py --runs 3
python src/stage6_eval.py --gradesheet
```

---

*Built as a portfolio project and a thesis research program in regulation-aware, multimodal AI assistants
— and in figuring out, empirically, exactly how far you can trust a language model with a decision before
you shouldn't.*