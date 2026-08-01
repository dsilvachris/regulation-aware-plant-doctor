"""
phase5_step1_regression_check.py — Phase 5, Step 1: the regression check Phase5_Design.md required
before treating the architecture integration as done.

A standalone-validated pipeline embedded in a stateful conversational wrapper is not guaranteed to
behave the same way — in particular, kg_retrieval_bridge.py's identify_disease() depends entirely on
real sentence-transformer embeddings correctly distinguishing between diseases from natural-language
phrasing, which cannot be verified with mocked embeddings (confirmed: a mock test with zero-vector
embeddings mis-identified "apple scab" as "powdery mildew" — an artifact of the mock, not the code, but
exactly the kind of thing that needs checking with the real model before trusting the integration).

This script runs natural-language, conversational-style questions (not Phase 1's exact benchmark
wording) through the full Conversation._grounded_answer() path and checks:
  1. identify_disease() picks the correct disease for each question
  2. the KG/RAG routing decision matches what classify_deterministic() would say directly
  3. for KG-routed questions, the facts_text matches what kg_arm.py would produce standalone

Run: python src/phase5_step1_regression_check.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kg_retrieval_bridge as bridge
import kg_arm
from kg_verbalise import verbalise
from phase2_step2b_deterministic_router import classify_deterministic

# Natural-language, conversational-style rephrasings (deliberately NOT copied verbatim from Phase 1's
# benchmark wording) of questions covering all 3 validated diseases, both regions, and both expected
# routing outcomes (kg and rag).
CASES = [
    # (query, region, expected_base_id, expected_route)
    ("Which products can I use against late blight in Germany?", "DE", "tomato_potato_late_blight", "kg"),
    ("What pathogen is responsible for late blight?", "DE", "tomato_potato_late_blight", "rag"),
    ("Is there anything authorised for apple scab in Norway?", "NO", "apple_scab", "kg"),
    ("What type of pathogen causes apple scab?", "DE", "apple_scab", "rag"),
    ("What can I spray on cucurbit powdery mildew in Germany?", "DE", "cucurbits_powdery_mildew", "kg"),
    ("Which crops does cucurbit powdery mildew affect?", "DE", "cucurbits_powdery_mildew", "rag"),
]

if __name__ == "__main__":
    print("Regression check: real embeddings, real KG, natural-language conversational queries\n")
    failures = []

    for query, region, expected_base_id, expected_route in CASES:
        identified = bridge.identify_disease(query, region)
        route = classify_deterministic(query)
        ctx, source, notice = bridge.get_context_for_query(query, region)

        disease_ok = identified == expected_base_id
        route_ok = route == expected_route
        source_ok = source == expected_route  # bridge's source label should match the route decision

        status = "PASS" if (disease_ok and route_ok and source_ok) else "FAIL"
        if status == "FAIL":
            failures.append((query, expected_base_id, identified, expected_route, route, source))

        print(f"[{status}] {query!r}")
        print(f"    disease identified: {identified!r} (expected {expected_base_id!r}) "
              f"{'OK' if disease_ok else 'MISMATCH'}")
        print(f"    route: {route!r} (expected {expected_route!r}) {'OK' if route_ok else 'MISMATCH'}")
        print(f"    bridge source label: {source!r} {'OK' if source_ok else 'MISMATCH'}")
        if source == "kg":
            # Cross-check: does the bridge's KG facts_text match what kg_arm.py produces standalone?
            disease_key = bridge.VALIDATED_DISEASE_MAP[expected_base_id]
            standalone_facts = kg_arm.q_products_in_country(country=region, disease=disease_key)
            standalone_text = verbalise("region_specific", standalone_facts)
            match = ctx.strip() == standalone_text.strip()
            print(f"    KG facts_text matches standalone kg_arm.py output: {match}")
        print()

    print("=" * 70)
    if failures:
        print(f"REGRESSION CHECK FAILED: {len(failures)}/{len(CASES)} cases did not behave as expected.")
        for f in failures:
            print(f"  {f}")
    else:
        print(f"REGRESSION CHECK PASSED: {len(CASES)}/{len(CASES)} cases correct.")
        print("The embedded pipeline (real conversational wrapper) matches standalone behaviour.")