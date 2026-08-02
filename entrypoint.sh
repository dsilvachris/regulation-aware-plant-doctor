#!/bin/bash
# entrypoint.sh — Phase 5, Step 4. Starts Ollama as an internal-only background process (not exposed
# publicly, see Dockerfile's note on port constraints), waits for it to actually be ready to serve
# requests (not just "process started"), then launches the Streamlit app on the public port.
set -e

echo "Starting Ollama server (internal, localhost:11434 only)..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to actually respond, not just assume a fixed sleep is long enough
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Ollama did not become ready in time." >&2
        exit 1
    fi
    sleep 1
done

echo "Starting the Streamlit app on port 7860..."
exec streamlit run src/streamlit_app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false