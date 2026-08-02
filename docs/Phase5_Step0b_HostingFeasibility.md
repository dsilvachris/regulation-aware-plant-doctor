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

## CORRECTION (post-Step 4): Hugging Face Spaces is no longer a valid GO

**This reverses the GO verdict above.** Confirmed live, via the actual HF Space-creation UI and current
(2026) documentation/community reports, not assumed:

- **Docker SDK is fully paid-gated** for new free accounts — shown as locked ("Paid") directly in the
  creation UI, not just documented.
- **CPU Basic hardware is also greyed out for new free accounts.** The only selectable free hardware is
  **ZeroGPU**.
- **ZeroGPU is architecturally incompatible with this deployment, not just quota-limited.** It's a
  burst-access model — code briefly claims a shared GPU for one function call and releases it, with a
  daily time quota (a few minutes for free accounts). This assistant needs a **persistent background
  process** (`ollama serve`, kept alive and ready across an entire conversation) — a fundamentally
  different execution model ZeroGPU was never built for. This is not a limitation that can be worked
  around with a smaller quota or a leaner image; it's the wrong kind of platform for this architecture.
- Confirmed (HF community forum, cross-checked): this is a real, recent restriction — "Hugging Face has
  restricted standard CPU Basic space creation for new free accounts, shifting the free focus toward the
  ZeroGPU ecosystem."
- **HF PRO ($9/month)** likely restores Docker + CPU Basic Space creation, based on the pattern in current
  documentation, but this is not 100% confirmed without actually subscribing — stated as probable, not
  verified, since confirming it would require spending real money to test.

Render and Koyeb's free tiers were also checked as alternatives (both offer genuine no-credit-card free
tiers for Docker services) and are **also disqualified**: both cap free-tier RAM at 512MB, far below what's
needed to hold `llama3.2:3b` in memory alongside the app itself (which alone uses 553MB per
`Phase5_Step3_LocalDeployability.md`'s real measurement).

**Revised conclusion: no genuinely free, always-on hosting platform checked supports this architecture
(persistent local LLM inference) as of this check.** This is reported as an honest finding, not
engineered around — see `docs/Phase5_Step4_Deployment.md` for the three paths forward this leaves open.

## Status

Original Step 0b determination (HF Spaces GO) was superseded during Step 4 when actual Space creation
revealed a real, current platform restriction that documentation alone hadn't fully surfaced. Corrected
above rather than left stale. See `docs/Phase5_Step4_Deployment.md` for how the project proceeded given
this — the build artifacts (Dockerfile, entrypoint.sh) remain valid and reusable the moment a working
Docker-capable free (or low-cost) tier is available, since nothing about the architecture itself was
wrong, only the platform's current access policy.