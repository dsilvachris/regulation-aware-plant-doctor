# Phase 5 — Execution Plan

*Companion to Phase5_Design.md. Two feasibility gates up front (verification method, hosting platform),
matching the discipline that caught real problems early in Phase 4 — check before designing around an
assumption, not after.*

---

## Step 0a — Feasibility gate: does a deterministic verifier catch the one confirmed hallucination?

Before designing Work Package B properly, test both candidate methods (claim-decomposition,
qualifier-aware matching) against:
- The real, confirmed `r2` fabrication text (must be flagged)
- A handful of genuinely correct answers from Phase 1/4's graded data (must NOT be flagged)

**Go/no-go:** if neither candidate catches `r2` without an unacceptable false-positive rate on known-good
answers, that is reported honestly as a negative finding about how far cheap deterministic verification
can go — not forced into a design that doesn't actually work. If one candidate works, it becomes Work
Package B's method, chosen on evidence rather than picked first and hoped to work.

**Produces:** `docs/Phase5_Step0a_VerifierFeasibility.md` + the winning method, or an honest "neither
worked" finding with implications for scope.

## Step 0b — Feasibility gate: can free-tier hosting actually run this?

Live-check (not documentation-check) whether a real free-tier account on the leading candidates
(Streamlit Community Cloud, Hugging Face Spaces) can run a persistent Ollama process with `llama3.2:3b`
loaded, under realistic memory/compute limits, for long enough to serve a conversation.

**Go/no-go:** if no free tier supports local Ollama, the honest deliverable becomes: retrieval and
verification stay local/free, and the only place cost enters is an LLM API call — reported as a real
constraint, not designed around silently. If some platform does work, proceed with it as the target.

**Produces:** `docs/Phase5_Step0b_HostingFeasibility.md` — a real comparison grounded in what was actually
tested, not what's documented as theoretically possible.

## Step 1 — Architecture integration (Work Package A)

- Swap Programme A's plain-RAG backend in `conversational_doctor.py` for KG-primary retrieval +
  `phase2_step2b_deterministic_router.py`'s actual routing logic (imported, not reimplemented).
- Implement the explicit 3-vs-12-disease boundary: KG-backed answers for late blight/apple scab/powdery
  mildew; a clearly disclosed fallback or scope statement for the other 9.
- **Regression check**: run a sample of Phase 1's validated benchmark questions through the newly-embedded
  pipeline (inside the conversational wrapper, multi-turn context included) and confirm answers still
  match the standalone pipeline's quality — do not assume embedding preserves behaviour.

**Produces:** the integrated assistant; a regression-check report.

## Step 2 — Trustworthiness verification, built and evaluated (Work Package B)

- Implement the method chosen in Step 0a.
- Build the evaluation set: `r2` (must flag), known-good answers from Phase 1/4 grading data (must not
  flag), plus new borderline cases constructed specifically to stress-test the qualifier/relationship
  issue that motivated this work package.
- Report precision/recall against this set before treating the verifier as validated.

**Produces:** the verification layer, wired into the integrated assistant's response pipeline; a
precision/recall report against the evaluation set.

## Step 3 — Local deployability evaluation (Work Package C)

- Measure response latency, CPU/memory, KG load time, retrieval performance, and conversational
  responsiveness on the actual hardware used throughout this project.
- Document how the KG gets refreshed when source data changes (manual re-run of the build script, at
  minimum — note whether this is acceptable for Phase 5's scope or flagged as future automation work).

**Produces:** `docs/Phase5_Step3_LocalDeployability.md` with real measurements.

## Step 4 — Deployment feasibility and (if feasible) actual deployment (Work Package D)

- Using Step 0b's confirmed-feasible platform (or the fallback API-based architecture if no free tier
  supports local Ollama), attempt an actual deployment.
- Evaluate: cost, deployment complexity, latency, memory limits, maintenance burden, public accessibility.

**Produces:** a hosting comparison; a recommended architecture; if feasible, a real public URL demonstrating
the assistant.

## Step 5 — Interpretation and write-up

- Answer the Phase-5 RQ against what was actually built and measured, not against the original vision.
- State plainly where the deployed system's scope is narrower than the full research programme (3 diseases,
  not 12; fusion excluded; verification method's real precision/recall, not an assumed one).
- Close the loop explicitly: what Phases 1–4 found, and what Phase 5 shipped because of it.

**Produces:** `docs/Phase5_Results.md`.

---

## Deliverables checklist

- [ ] `docs/Phase5_Step0a_VerifierFeasibility.md` — verification method chosen on evidence (Step 0a)
- [ ] `docs/Phase5_Step0b_HostingFeasibility.md` — real, live-tested hosting constraints (Step 0b)
- [ ] Integrated assistant + regression-check report (Step 1)
- [ ] Verification layer + precision/recall report (Step 2)
- [ ] `docs/Phase5_Step3_LocalDeployability.md` (Step 3)
- [ ] Hosting comparison + (if feasible) live deployment (Step 4)
- [ ] `docs/Phase5_Results.md` (Step 5)

## Pre-registered prediction (record before Step 0a runs)

The qualifier/relationship-aware matching candidate is expected to catch the `r2`-style fabrication where
naive entity-presence matching would not, since the failure mode specifically involves an added
relationship between two already-present entities, not a new entity. Some false-positive rate is expected
on genuinely correct but loosely-phrased answers (e.g. an answer that restates a fact with added
context that IS supported but phrased unusually) — the acceptable threshold for this is not yet fixed and
should be decided based on what Step 0a actually finds, not assumed in advance. On hosting: it is expected,
based on general knowledge of free-tier constraints, that no fully free platform supports a persistent
local Ollama process at the scale this project needs — expected to be confirmed, not assumed, in Step 0b.

## Scope discipline

- Fusion stays excluded — this is not revisited in Phase 5 regardless of how integration goes.
- The 3-disease KG boundary is not silently expanded to cover all 12 of Programme A's original diseases;
  doing so is explicitly out-of-scope future work, stated as such in the final write-up.
- If Step 0a finds no deterministic method catches the confirmed hallucination, that is reported as a real
  negative finding, not hidden by narrowing the evaluation set until something passes.
- If Step 0b finds free hosting cannot run the intended architecture, the deliverable becomes an honest
  architecture recommendation (e.g. hosted LLM API + local everything else), not a forced fit onto an
  infeasible platform.
  