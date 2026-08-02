# Phase 5, Step 4 — Deployment Feasibility & Deployment (Work Package D)

## CORRECTION, found during actual Space creation (see `docs/Phase5_Step0b_HostingFeasibility.md`)

Everything below (Dockerfile, entrypoint.sh, file manifest) was built correctly and remains valid, but
**Hugging Face Spaces' current free tier cannot actually run it**: Docker SDK is paid-gated for new free
accounts, and the only free hardware option (ZeroGPU) is a burst-access GPU model incompatible with a
persistent background process like `ollama serve`. Render and Koyeb's genuinely free tiers were checked as
alternatives and are also disqualified (512MB RAM, far below what's needed). Full detail in
`Phase5_Step0b_HostingFeasibility.md`'s correction section.

**This does not waste the work done below** — the artifacts are platform-agnostic and would work
unchanged the moment a Docker-capable tier is available (HF PRO, most likely, or any VPS/PaaS with
sufficient RAM). The three real paths forward, decided with the researcher rather than assumed, are
recorded in the "Decision" section at the end of this document.

## Target platform (as originally planned, artifacts below built against this)

Hugging Face Spaces, Docker SDK, CPU Basic tier — confirmed GO in
`docs/Phase5_Step0b_HostingFeasibility.md` (16GB RAM, genuinely free, real-world Ollama precedent found).
Streamlit Community Cloud was ruled out there (1GB RAM ceiling, no background-process support).

## What was built

- **`Dockerfile`** — installs Ollama, bakes `llama3.2:3b` into the image **at build time** (Step 0b found
  HF Spaces' disk is not persistent by default, so pulling the model at container start would mean
  re-downloading it on every restart), installs only the deployment-specific Python dependencies, copies
  only the files actually needed at runtime, and runs `entrypoint.sh`.
- **`entrypoint.sh`** — starts Ollama as an internal-only background process (never exposed publicly —
  Step 0b found only ports 80/443/8080 are public on HF Spaces, and Ollama's own port, 11434, isn't one of
  them; the app reaches it over localhost inside the same container), **waits for it to actually respond**
  (polls `/api/tags` rather than a fixed `sleep`, so the app never starts before Ollama can serve
  requests), then launches the Streamlit app on the public port (7860, HF's Docker SDK default).
- **`HF_SPACE_README.md`** — the Space's own README with the required YAML frontmatter
  (`sdk: docker`, `app_port: 7860`) — separate from this repo's main `README.md`, since it needs to become
  `README.md` inside the actual Space, not overwrite this repo's.
- **`requirements-deploy.txt`** — a minimal dependency list for the container, trimmed from the full
  `requirements.txt` (which also covers `gradio`, `datasets`, `accelerate` — needed elsewhere in this
  project, not by the deployed conversational app). Reduces build time and image size, itself one of Work
  Package D's stated evaluation criteria.

## A real finding from tracing the deployment's actual dependencies

Building the file manifest by tracing real imports (not guessing) found that
`phase2_step2b_deterministic_router.py` — needed only for its `classify_deterministic()` function, which
uses nothing but `re` — was importing the entire Phase 2 evaluation harness at module level
(`eval_pipeline.py`, which itself re-imports `kg_arm`/`rag_arm`, plus `phase2_step3b_prompt_sensitivity.py`)
purely to support that file's own self-test code. Fixed by moving those imports to be local to `score()`
and the `__main__` block. Verified: the lightweight import now takes 23ms and pulls in zero unnecessary
modules, with `classify_deterministic()`'s behaviour unchanged. This is exactly the kind of technical debt
that attempting a real deployment surfaces and a documentation-only "integration" would not have caught.

## File manifest, traced not guessed

| File | Why it's needed |
|---|---|
| `conversational_doctor.py`, `streamlit_app.py` | the app itself |
| `vision.py` | image-turn disease identification |
| `region_gate.py` | region detection, RAG retrieval, corpus |
| `kg_retrieval_bridge.py` | Step 1's KG-primary integration |
| `kg_arm.py`, `kg_verbalise.py` | Phase 1's validated KG query/verbalisation |
| `verification_layer.py` | Step 2's trustworthiness layer |
| `phase2_step2b_deterministic_router.py` | Phase 2's validated routing rule (now lightweight) |
| `kg_all.ttl` | the validated 3-disease KG |
| `corpus.json` | the 12-disease RAG corpus (out-of-scope diseases fall back here) |
| `agro_vision_classes.json`, `vision_to_corpus.json` | vision → corpus mapping |
| `agro_vision.tflite` | the vision model |

`corpus_no_entries.json` was checked and confirmed **not** needed — it's used only by one-off
data-preparation scripts (`fix_paths.py`, `merge_corpus.py`), not the runtime conversational path.

## What I could verify myself, and what needs your machine

I confirmed every file in the manifest exists at its stated path, and that the import-chain trace is
accurate (checked by grep, not assumed). I could **not** build or run the actual Docker image in this
environment — no Docker daemon, and `ollama.com` isn't reachable from this sandbox's network allowlist,
so the `curl -fsSL https://ollama.com/install.sh` step can't be tested here. **The build itself needs to
happen on your machine or HF's own build infrastructure.**

## What you need to do — superseded, see Decision below

~~1. Create a free Hugging Face account... 2. Create a new Space: Docker/CPU Basic (free)...~~
**Step 2 is no longer possible on a free account** (confirmed via the actual Space-creation UI). The rest
of the file-push steps remain accurate for whichever platform is chosen below.

## Decision

Given the corrected finding, three real paths forward — this is a real decision, not made unilaterally:

1. **HF PRO ($9/month)** — likely unlocks Docker + CPU Basic Space creation (based on current
   documentation patterns, not 100% confirmed without subscribing). Cheapest path to an actual public URL;
   every artifact built in this step (Dockerfile, entrypoint.sh, file manifest) works unchanged.
2. **A hybrid architecture** — keep KG/RAG/verification fully local, swap only LLM generation for a
   free-tier hosted inference API over the network. Would fit Render/Koyeb's small memory budgets, since
   the model would no longer need to live in the container's own memory. A real architectural change, not
   a small tweak — would need its own design pass, not assumed to be a drop-in swap.
3. **Report this as the honest Work Package D finding and stop here.** The assistant is fully built,
   integrated, and validated (Steps 1–3 complete, all real measurements and real evaluations). No
   genuinely free, always-on hosting for this architecture was found among the platforms checked. The
   system remains fully demonstrable locally, exactly as it has run throughout this entire project.

## Status

Build artifacts complete and locally verified as far as this sandbox allows (file existence, import-chain
accuracy, one real bug found and fixed along the way — see above). Hosting platform decision above is
open, pending the researcher's choice among the three paths, rather than assumed.