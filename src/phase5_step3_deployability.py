"""
phase5_step3_deployability.py — Phase 5, Step 3 (Work Package C): local deployability evaluation.

Measures, on the actual hardware this project has run on throughout: KG load time, embedding model load
time, retrieval latency (both KG and RAG paths), LLM generation latency, verification-layer overhead, and
peak memory at each stage. Uses only the standard library (`resource`, `time`) for portability - no new
dependency added just for benchmarking, consistent with this project's zero-cost, minimal-dependency
approach throughout.

Run: python src/phase5_step3_deployability.py
"""
import sys, time, resource, platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

N_REPEATS = 3  # for latency measurements sensitive to LLM sampling variance


def peak_rss_mb():
    """Peak resident set size in MB. macOS reports bytes; Linux reports KB - handled here."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return raw / (1024 * 1024)
    return raw / 1024


def timed(label, fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    print(f"  {label:<45} {elapsed:>8.3f}s   (peak RSS so far: {peak_rss_mb():.0f} MB)")
    return result, elapsed


def timed_repeated(label, fn, *args, n=N_REPEATS, **kwargs):
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    print(f"  {label:<45} mean={sum(times)/n:.3f}s  min={min(times):.3f}s  max={max(times):.3f}s  (n={n})")
    return times


if __name__ == "__main__":
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Baseline peak RSS at start: {peak_rss_mb():.0f} MB\n")

    print("=" * 70)
    print("1. KNOWLEDGE GRAPH LOAD")
    print("-" * 70)
    from rdflib import Graph
    def load_kg():
        g = Graph()
        g.parse("data/kg_all.ttl", format="turtle")
        return g
    g, kg_load_time = timed("Parse kg_all.ttl (RDFLib)", load_kg)
    print(f"  -> {len(g)} triples loaded")

    print("\n" + "=" * 70)
    print("2. EMBEDDING MODEL LOAD (sentence-transformers)")
    print("-" * 70)
    t0 = time.perf_counter()
    import region_gate  # triggers SentenceTransformer + doc embedding load at import time
    import_elapsed = time.perf_counter() - t0
    print(f"  import region_gate (model load + doc embeddings)  {import_elapsed:>8.3f}s   "
          f"(peak RSS so far: {peak_rss_mb():.0f} MB)")

    print("\n" + "=" * 70)
    print("3. RETRIEVAL LATENCY")
    print("-" * 70)
    import kg_arm
    import kg_retrieval_bridge as bridge

    timed_repeated("RAG retrieval (region_gate.retrieve, k=3)",
                   region_gate.retrieve, "What pathogen causes late blight?", "DE")
    timed_repeated("KG query (kg_arm.q_products_in_country)",
                   kg_arm.q_products_in_country, country="DE", disease="late_blight")
    timed_repeated("Disease identification (bridge.identify_disease)",
                   bridge.identify_disease, "Which products are authorised against late blight in Germany?", "DE")

    print("\n" + "=" * 70)
    print("4. VERIFICATION LAYER OVERHEAD")
    print("-" * 70)
    import verification_layer as vl
    sample_answer = "Niraparib is authorised via both the EU's centralised procedure and at the national level."
    sample_facts = "niraparib is authorised via the EU's centralised procedure (EMA)."
    timed_repeated("verification_layer.verify() (regex-based, no model call)",
                   vl.verify, sample_answer, sample_facts, domain="pharma", n=10)

    print("\n" + "=" * 70)
    print("5. LLM GENERATION LATENCY (Ollama, llama3.2:3b)")
    print("-" * 70)
    import conversational_doctor as cd
    convo = cd.Conversation()
    convo.region = "DE"

    print("  KG-path question:")
    timed_repeated("  _grounded_answer (KG path)",
                   convo._grounded_answer, "Which products are authorised against late blight in Germany?")

    print("  RAG-path question:")
    timed_repeated("  _grounded_answer (RAG path)",
                   convo._grounded_answer, "What pathogen causes late blight?")

    print("\n" + "=" * 70)
    print("6. MEMORY SUMMARY")
    print("-" * 70)
    print(f"  Final peak RSS: {peak_rss_mb():.0f} MB")

    print("\n" + "=" * 70)
    print("7. KG REFRESH PROCEDURE (documented, not measured)")
    print("-" * 70)
    print("  Manual: python src/build_kg.py  (re-parses source BVL/Mattilsynet data, rebuilds kg_all.ttl)")
    print("  No automatic refresh trigger exists - source data changes require a manual re-run.")
    print("  Flagged as a known limitation for Phase 5's scope, not automated here (Work Package D may")
    print("  revisit this if a scheduled rebuild becomes part of the deployment design).")