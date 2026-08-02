# Phase 5, Step 4 (Work Package D): deployment to Hugging Face Spaces (Docker SDK, CPU Basic).
# Target platform confirmed in docs/Phase5_Step0b_HostingFeasibility.md: 16GB RAM, genuinely free,
# Docker SDK supported. Two constraints from that check are addressed explicitly below:
#   1. Disk is NOT persistent by default -> the model is pulled at BUILD time, baked into the image,
#      not pulled at container start (which would fail/re-download on every restart).
#   2. Only ports 80/443/8080 are publicly exposed -> Ollama's own port (11434) is never exposed
#      publicly; the app talks to it over localhost inside the same container.

FROM python:3.11-slim

# --- Install Ollama ---
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (separate layer for caching - only rebuilds if requirements change) ---
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements-deploy.txt

# --- Bake the model into the image at BUILD time (see constraint 1 above) ---
RUN (ollama serve &) && sleep 5 && ollama pull llama3.2:3b && pkill ollama || true

# --- Only the files actually needed at runtime, not the full research repo (grading sheets,
# benchmark files, hundreds of phase-N evaluation scripts) - traced via the real import chain,
# not guessed, see docs/Phase5_Step4_Deployment.md ---
COPY src/conversational_doctor.py src/streamlit_app.py src/vision.py src/region_gate.py \
     src/kg_retrieval_bridge.py src/kg_arm.py src/kg_verbalise.py src/verification_layer.py \
     src/phase2_step2b_deterministic_router.py ./src/
COPY data/kg_all.ttl data/corpus.json data/agro_vision_classes.json data/vision_to_corpus.json ./data/
COPY models/agro_vision.tflite ./models/

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# HF Spaces' Docker SDK default app port
EXPOSE 7860

ENTRYPOINT ["./entrypoint.sh"]