# Phase 5 — Operationalising a Trustworthy Regulation-Aware Plant Protection Assistant: Design

*Programme A/B convergence point. Same discipline as every prior phase: design → build → verify against
real conditions → evaluate → interpret, committing after each step. Chapter vision and structure
originally drafted by the researcher; this version folds in four open questions identified in review
before treating it as buildable.*

## Chapter vision

Phases 1–4 established **what works and why** (KG-primary retrieval, deterministic routing over LLM
delegation, fusion's unresolved status, generalisation with a caveat about residual fabrication risk).
Phase 5 does not ask another retrieval question. It asks how those findings become a system a person can
actually use, while keeping the project's central principle — **faithfulness over confidence** — intact
through the transition from experiment to product.

## Central research question

> **How can the experimentally validated retrieval architecture be operationalised into a trustworthy,
> deployable conversational AI assistant for plant protection, while preserving deterministic
> decision-making, transparent evidence, and calibrated abstention?**

## Why Phase 5 exists

| Phase | Question |
|---|---|
| 1 | Does KG retrieval outperform document-RAG? |
| 2 | Can an LLM route between retrieval strategies safely? |
| 3 | Can retrieval strategies be combined? |
| 4 | Does the architecture generalise to a second regulated domain? |
| **5** | **How do these findings become an assistant people can actually use?** |

## Programme convergence

Programme A and Programme B independently arrived at the same principle from opposite directions:
**critical routing decisions should be deterministic, not delegated to the LLM.** Programme A's
`region_gate.py` embodies this — built before Phase 2 existed, for a different decision (which country's
regulations apply), arrived at the same design by instinct that Phase 2 later confirmed by evidence. Phase
5 is not introducing this principle to Programme A; it's recognising Programme A already believed it, and
formally merging the two streams that had been proving it independently:

- **Programme A** provides the user-facing capabilities: vision, region gate, conversation memory, chat
  interface.
- **Programme B** provides the validated reasoning architecture: KG-primary retrieval, deterministic
  routing, the evaluation evidence behind both.

## Integration boundary

**Integrated:**
- KG-primary retrieval, replacing Programme A's original plain-RAG backend
- Deterministic routing — **reusing `phase2_step2b_deterministic_router.py`'s actual logic, not a
  reimplementation**, so the deployed system runs the exact rule Phase 2 validated, not a new one built to
  resemble it
- The existing region gate and conversation memory, unchanged
- Explainable evidence (the answer can point to the specific KG fact or retrieved document behind it)
- Confidence-aware abstention, extended by the new verification layer (Work Package B)

**Not integrated:** experimental hybrid evidence fusion (Phase 3). Its headline result was never
independently validated (`Phase3_Step4_FusionResults.md`), and shipping it would mean deploying the one
component across four phases that is explicitly still an open question. Remains future work.

**Scope decision, made explicit rather than assumed:** Programme A's original corpus covers 12 diseases;
Programme B's validated KG covers 3 (late blight, apple scab, cucurbit powdery mildew — the ones Phase 1
built, tested, and corrected). The deployed assistant's KG-backed answers are scoped to these 3 diseases
only. For the other 9, the assistant either (a) falls back to Programme A's original RAG pipeline with
that boundary disclosed to the user, or (b) states plainly that the disease is outside the KG's validated
scope. Which of these is the right default is a Work Package A decision, not assumed here — but the
boundary itself must be explicit and visible, not silently blurred. Extending the KG to the remaining 9
diseases is out of scope for Phase 5 and named as future work.

## Work Package A — Architecture integration

Replace Programme A's RAG-only backend with the validated KG-primary + deterministic-router pipeline,
inside the existing conversational wrapper (`conversational_doctor.py`).

**Includes a regression check**, not just a swap: once the backend is embedded in multi-turn conversation
state, verify on a sample of questions that answers still match Phase 1's validated quality standalone.
Embedding a validated pipeline into a stateful wrapper is not guaranteed to preserve its behaviour —
this needs checking, not assuming, same as everything else in this project.

**Deliverable:** one unified regulation-aware assistant, with the 3-vs-12-disease boundary explicit in
both the code and the user-facing output.

## Work Package B — Trustworthiness verification

### Research question

Can a deterministic, post-generation check detect unsupported claims in a generated answer, cheaply
enough to run on every response, without becoming a second reasoning pass?

### The method needs to be specified, not assumed — and checked against the one confirmed failure it exists to catch

A naive approach (check whether every named entity in the answer appears in the facts_text) will likely
**miss** the only confirmed hallucination this project has actually produced: `r2`'s KG answer
(`Phase4_Step6_Results.md`) fabricated *"authorised via both the centralised procedure **and at the
national level**"* — no new entity was invented; an unsupported **relationship/qualifier** was added to
real entities that were both genuinely present in the facts. Entity-presence matching would pass this
answer as fully supported.

The verification method therefore needs a specific design, decided in Step 0 (below) via a feasibility
check against real cases, not assumed to be simple string matching:
- **Candidate 1 — claim-level decomposition**: split the answer into atomic claims (subject–predicate–
  object triples, roughly), check each against the facts_text/KG directly rather than just checking that
  the words appear somewhere.
- **Candidate 2 — qualifier/negation-aware matching**: extend simple entity matching with a check for
  added qualifiers (e.g. "both X and Y", "also", "in addition to") that introduce information beyond what
  a single matched fact states.
- Both are still deterministic, cheap, and explainable — no second LLM call, no fusion-style reconciliation
  step. The point of Step 0 is finding out which (if either) actually catches the `r2` case before
  committing to a design.

**Pipeline (detection only, never correction):**

```
Generated answer → extract claims → compare against retrieved facts_text/KG →
  supported? → YES: return as-is
             → NO: flag → explain what's unsupported → abstain rather than silently correct
```

Correction (having the model retry or reconcile) would reopen Phase 3's fusion-risk problem. Detection and
disclosure keeps this a deterministic, auditable step, consistent with every other design choice in this
project.

### This needs its own evaluation, not just a working pipeline

A verifier that has never been measured isn't a finding, it's a claim. Test set: the confirmed `r2`
fabrication (replayed, must be flagged), a set of known-good answers from Phases 1/4's graded data (must
NOT be flagged — false positives make the assistant unusably cautious), and a handful of newly-constructed
borderline cases. Report precision and recall against this set before calling the verifier validated.

## Work Package C — Deployability evaluation (local-first)

Measure, on the actual local hardware this project has run on throughout: response latency, CPU/memory
usage, KG load time, retrieval performance, conversational responsiveness, and how easy it is to refresh
the KG when source data changes. Consistent with the project's standing "everything local, €0" constraint
— this is a measurement exercise, not a redesign.

## Work Package D — Deployment feasibility (free-tier hosting)

### A feasibility gate is needed before this is designed, not after

Most candidate free platforms (Streamlit Community Cloud, Hugging Face Spaces' free tier) do not support a
persistent local Ollama server running a 3B model — no guaranteed heavy compute, spin-down behaviour on
idle, tight memory ceilings. This needs a real, live check (same discipline as Phase 4 Step 0) before any
comparison table of "candidate platforms" is written as though local-Ollama-on-free-hosting is a given.
The honest answer might be "no free tier supports this configuration as-is; a hosted-inference-API
alternative (keeping the retrieval/verification logic local and free, swapping only the LLM call) is the
only zero-cost path" — that is itself a legitimate, reportable finding, not a failure to design around.

**Deliverable, once the gate is passed or the constraint is confirmed:** a hosting comparison, a
recommended deployment architecture, and a public demonstration strategy — scoped to what's actually
feasible, not to an assumed ideal.

## Expected contributions

1. Integrate Programme A and Programme B into one coherent system, with the KG-coverage boundary explicit.
2. Deploy only experimentally validated components — fusion explicitly excluded.
3. Introduce and *validate* a deterministic verification layer, specifically checked against the one
   confirmed real fabrication this project has produced.
4. Evaluate local deployability with real measurements.
5. Evaluate free-tier cloud deployment, feasibility-checked before designed around.
6. Demonstrate a complete, honest research-to-deployment workflow — including stating plainly where the
   deployed system's scope is narrower than Programme A's original corpus, and why.

## Final outcome

One deployed, trustworthy, regulation-aware plant-protection assistant, combining Programme A's
user-facing capabilities with Programme B's validated retrieval architecture and a checked (not assumed)
verification layer — remaining faithful to the project's guiding principle throughout: when uncertainty
cannot be justified, the assistant explains its limitations and abstains rather than guessing.