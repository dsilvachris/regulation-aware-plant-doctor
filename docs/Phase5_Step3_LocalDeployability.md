# Phase 5, Step 3 — Local Deployability (Work Package C): Results

Measured on real hardware (MacBook Air, Apple Silicon/arm64) — the actual machine this entire project has
run on. Stdlib-only measurement (`resource` + `time`), no new dependency.

## Results

| Component | Latency | Peak RSS |
|---|---|---|
| KG load (`kg_all.ttl`, 1,601 triples) | 22ms | 35MB |
| Embedding model load (sentence-transformers + corpus embeddings) | **8.47s (one-time)** | 553MB |
| RAG retrieval (k=3) | 8–41ms | — |
| KG query (SPARQL) | 6–87ms | — |
| Disease identification | 6–22ms | — |
| Verification layer (`verify()`) | <1ms | — |
| **LLM generation, KG-path question** | **mean 3.807s (2.259–6.063s)** | — |
| **LLM generation, RAG-path question** | **mean 1.332s (0.743–2.303s)** | — |
| Final peak RSS | — | **553MB** |

## The headline finding: KG-path answers are ~3x slower than RAG-path, and it's not the retrieval

Every retrieval step (RAG, KG query, disease ID) is fast either way — under 100ms in all cases. The
latency gap is entirely downstream, in LLM generation. The KG-path test question ("which products are
authorised against late blight in Germany") pulls a **112-product list** as facts_text — the same number
verified repeatedly across Phases 1, 2, and 4. That's a much longer prompt for the LLM to process, and
typically a longer answer enumerating or summarising that list. The RAG-path question hits a single short
fact and generates a short answer.

**This is a genuine, real deployability tradeoff, not a flaw**: the KG-primary architecture this project
validated as more reliable (Phases 1–4) can cost real latency specifically on large-result-set questions.
Worth stating plainly rather than only reporting the favourable retrieval-speed numbers. A future
optimisation (out of Phase 5's scope, noted for later) would be truncating or summarising very large
product lists before they reach the LLM on the largest-result-set question types, trading some
completeness for latency on exactly those questions.

## Memory: comfortably within the confirmed hosting budget

553MB peak RSS is well within Hugging Face Spaces' CPU Basic tier (16GB RAM, confirmed free in
`Phase5_Step0b_HostingFeasibility.md`) — plenty of headroom for the KG, embeddings, conversation state, and
the LLM process itself.

## Cold start is real and worth designing around

The 8.47s embedding-model load is a one-time cost per process start, not per-request — but combined with
Step 0b's finding that free-tier hosting sleeps on idle, **every wake-up after an idle period pays this
cost again**. First request after a cold start: ~0.02s (KG) + 8.47s (embeddings) + 1.3–3.8s (generation) ≈
**10–12 seconds** before the first reply. Subsequent requests in the same session only pay the generation
cost. This is a real UX property Work Package D's deployment should account for explicitly — e.g. a
"warming up" indicator on first load, rather than a bare loading spinner that looks broken.

## KG refresh: manual, documented as a known limitation

No automatic refresh trigger exists. Updating the KG when BVL/Mattilsynet source data changes requires a
manual `python src/build_kg.py` re-run. Not automated in Phase 5 — flagged for Work Package D to revisit
if a scheduled rebuild becomes part of the actual deployment design, not assumed to be solved here.

## Status

Work Package C complete: local deployability characterised with real measurements, one genuine
architectural tradeoff surfaced and explained (KG-path latency on large result sets), memory footprint
confirmed compatible with the hosting platform selected in Step 0b, and cold-start behaviour quantified
for Work Package D's UX design.

Proceeding to Step 4: deployment feasibility and (if feasible) actual deployment to Hugging Face Spaces.