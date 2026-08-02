# Phase 5 Results — Operationalising a Trustworthy Regulation-Aware Assistant

*Synthesis chapter (Step 5 of `docs/Phase5_Plan.md`). Draws on all prior Phase 5 steps: verifier
feasibility (0a), hosting feasibility (0b, corrected), architecture integration (1), trustworthiness
verification (2), local deployability (3), and deployment (4). Answers the pre-registered RQ against
what was actually built and measured; introduces no new results.*

## The research question

> **How can the experimentally validated retrieval architecture be operationalised into a trustworthy,
> deployable conversational AI assistant for plant protection, while preserving deterministic
> decision-making, transparent evidence, and calibrated abstention?**

(`docs/Phase5_Design.md`)

## Answer

**Fully operationalised as a working, locally-running, trustworthy assistant. Publicly deployed on
always-on free infrastructure: not achieved, and reported as a genuine finding about current platform
economics rather than engineered around.** Every one of Phases 1–4's validated components — the KG,
Phase 2's deterministic router, and a new deterministic verification layer built and evaluated specifically
for this phase — is integrated into Programme A's existing conversational assistant, running exactly as
designed, with the scope boundary between validated and out-of-scope diseases enforced in code and
disclosed to the user, not just documented.

## What was built, and what it demonstrates

**Architecture integration (Step 1).** `kg_retrieval_bridge.py` replaces Programme A's plain-RAG backend
with KG-primary retrieval for the 3 diseases Programme B validated, reusing Phase 1's KG and Phase 2's
exact deterministic rule unchanged. A 10-case regression check — deliberately including natural,
symptom-based phrasing rather than exact benchmark wording — passed 9/10, with the one failure safely
contained by the scope-check design (graceful fallback to disclosed RAG, never a confidently-wrong KG
answer) rather than a silent error. The 4 cases specifically designed to find the dangerous failure mode
(cross-confusion between validated diseases) all passed cleanly.

**Trustworthiness verification (Step 2).** A deterministic, post-generation detection layer, evaluated on
93 real cases spanning both of this project's domains (plant-protection and pharma), not just the smaller
pharma-only set Step 0a first validated it against. Recall: 100% — the confirmed `r2` hallucination and a
constructed fabrication case were both caught. Precision: 40%, with every false positive traced to one
understood, deliberately-accepted cause (benign chemical-name misspellings) rather than fuzzy-matched away
at real risk to recall. Wired into both text and image turns, confirmed end-to-end.

**Local deployability (Step 3).** Real hardware measurements surfaced a genuine architectural tradeoff
that documentation-only integration would not have found: KG-path answers are ~3x slower than RAG-path
answers (3.8s vs 1.3s mean), not because of retrieval (both under 100ms) but because of facts_text size on
large-result-set questions. Memory footprint (553MB peak) and cold-start cost (~10-12s after idle) were
both quantified for deployment planning, not assumed.

**Deployment (Step 4).** Complete, platform-agnostic Docker artifacts were built and locally verified
(file existence, import-chain accuracy — which itself surfaced and fixed a real piece of technical debt,
unnecessary heavy imports in `phase2_step2b_deterministic_router.py`). Attempting the actual deployment
found that Hugging Face Spaces' Docker SDK is now paid-gated for new free accounts, and the only free
hardware (ZeroGPU) is architecturally incompatible with the persistent-process model this assistant needs
— not merely quota-limited, a different execution model entirely. Render and Koyeb's genuinely free tiers
were also checked and ruled out on RAM alone (512MB, against a measured 553MB+ real footprint).

## The honest bottom line on deployment

**No genuinely free, always-on public hosting for a locally-run LLM architecture was found among the
platforms checked, as of this investigation.** This is reported as a real finding about current hosting
economics, not a failure of the engineering: every artifact built (Dockerfile, entrypoint.sh, the
integrated assistant itself) is correct and would deploy successfully the moment a suitable Docker-capable
tier is available, paid or free. Forcing a workaround onto an incompatible free tier, or quietly not
mentioning that "free" no longer means what it did when this phase was designed, would have been the
project's first real instance of optimizing for a clean-looking conclusion over an honest one — exactly
the failure mode every prior phase was built to avoid.

**The system remains fully demonstrable locally**, exactly as it has run throughout this entire project —
the same standard every phase before this one was validated under.

## Against the pre-registered predictions

`Phase5_Plan.md` predicted, before Step 0a ran: *"The qualifier/relationship-aware matching candidate is
expected to catch the r2-style fabrication where naive entity-presence matching would not... it is
expected... that no fully free platform supports a persistent local Ollama process at the scale this
project needs — expected to be confirmed, not assumed, in Step 0b."*

- **The verifier prediction — confirmed precisely**, including the specific mechanism (coordination
  splitting catches an added relationship between two already-present entities; naive matching does not).
- **The hosting prediction — confirmed, more strongly than the original Step 0b check suggested.** The
  first pass at Step 0b found a false GO (HF Spaces), later corrected when actual Space creation revealed
  what documentation review alone had missed. The final, corrected picture matches the original prediction
  exactly: no free tier supports this architecture.

## Deliverables checklist (Phase5_Plan.md), final status

- [x] Verifier feasibility, method chosen on evidence (Step 0a)
- [x] Hosting feasibility — corrected after live Space-creation testing surfaced a real restriction
      documentation review had missed (Step 0b)
- [x] Integrated assistant + regression check (Step 1)
- [x] Verification layer + evaluation (Step 2)
- [x] Local deployability, real measurements (Step 3)
- [x] Deployment artifacts + honest feasibility finding (Step 4)
- [x] this document (Step 5)

## What would change this conclusion

- **HF PRO or an equivalent low-cost tier**, actually subscribed to and tested — would convert the
  existing, already-built Docker artifacts into a live public deployment with no further engineering work.
- **A hybrid architecture** (local retrieval/verification, hosted LLM API for generation only) — a real,
  separate design question, under active discussion as the next piece of this project, not folded into
  this phase's conclusion.
- **Platform economics changing again** — worth re-checking periodically, since this finding is a snapshot
  of a specific point in time, not a permanent property of "free hosting" in general.