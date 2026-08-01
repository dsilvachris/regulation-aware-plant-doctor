# Phase 5, Step 0b — Hosting Feasibility: Confirmed, With a Clear Winner

## Method

Live-checked against official documentation and confirmed real-world precedent (not just theoretical
specs), per the same discipline as Phase 4 Step 0: verify before designing around an assumption.

## Streamlit Community Cloud — NO-GO

- **~1GB RAM hard limit** (confirmed via Streamlit's own docs and multiple current sources). `llama3.2:3b`
  needs roughly 2–4GB just for inference at typical quantization — this alone exceeds the ceiling before
  the app (KG, embedding model, conversation state) is even loaded.
- **Not a general container** — Streamlit Cloud runs your Python script directly from a GitHub repo; it
  does not support installing and running a separate background daemon (an actual Ollama binary + model
  weights + a persistent server process) alongside the app the way local development does.
- **Apps sleep after 12 hours idle** — a real UX characteristic regardless, but moot given the RAM ceiling
  already disqualifies this platform.

**Confirmed exactly as predicted in `Phase5_Plan.md`**: no free tier of this type supports the intended
architecture as-is.

## Hugging Face Spaces (Docker SDK, CPU Basic) — GO

Checked directly against HF's own current official documentation
(`huggingface.co/docs/hub/en/spaces-overview`), not a third-party summary:

- **CPU Basic: 2 vCPU, 16GB RAM, genuinely free** — confirmed in HF's own hardware table. Comfortably
  covers `llama3.2:3b` (2–4GB) plus the KG (a few hundred KB), the sentence-transformers embedding model
  (~80MB), and the conversational app itself.
- **Docker SDK is a first-class, supported option** — full container control, meaning Ollama can actually
  be installed and run as a real background process, not worked around.
- **Real-world precedent exists**, not just theoretical feasibility: documented working deployments of
  Ollama-served models (Llama 3, Gemma) on this exact free tier via Docker.

### Two real constraints, both addressable, both worth designing around explicitly

1. **50GB disk, NOT persistent by default.** Model weights pulled at container runtime would be lost on
   every rebuild/restart. Fix: bake the model into the Docker image at *build* time
   (`ollama pull llama3.2:3b` as a build step, not a runtime step) so weights persist across restarts as
   part of the image itself, at the cost of a larger image (~2GB+).
2. **Only ports 80, 443, 8080 are publicly exposed.** Ollama's default port (11434) is not one of them —
   but this doesn't block anything, since Ollama only needs to be reachable *inside* the same container by
   the app itself (localhost), not from the public internet. The app's own public-facing port (e.g. 7860
   for Gradio, or 8080) is what needs to be exposed, not Ollama's.
3. **Free-tier Spaces sleep on idle**, same as Streamlit — expect a cold-start delay (KG + model reload)
   after a quiet period. A real, reportable UX property for Work Package C/D's write-up, not a blocker.

## Decision

**GO for Hugging Face Spaces, Docker SDK, CPU Basic tier.** This is the target platform for Work Package
D's actual deployment attempt. Streamlit Community Cloud is ruled out for the full backend, though
Programme A's existing Streamlit chat UI could still call a separately-hosted HF Space as its backend if a
Streamlit front-end is preferred — an architecture option worth keeping in mind for Step 4, not decided
here.

## Status

Step 0b complete via live documentation and precedent verification — no local testing was needed for this
determination, since HF's own current specs and confirmed working examples were sufficient evidence.
Proceeding to Step 1 (architecture integration).