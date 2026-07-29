# Phase 2, Step 3b — LLM Router Prompt-Sensitivity Check

## Why this step exists

The pre-registered LLM router (`src/llm_router.py`) was run first with a single, principled prompt
(**PROMPT A**, described in that file's docstring: KG criteria stated first, DOCS second, explicit "default
to KG on anything ambiguous" fallback). The result was a near-total collapse to the KG arm: of the 12
questions where Phase 1 established RAG as the *systematic* winner (see
`src/phase2_step2a_diagnose.py`), the router caught only **1/12** (f05). It also misrouted the three
simplest factual-lookup questions (f03, f08, f09) to KG, despite its own prompt stating "simple fact
lookup → DOCS" — meaning the model did not reliably apply a criterion it was explicitly given.

Two explanations are consistent with that result and lead to different conclusions:

- **Conclusion A — a 3B model genuinely cannot do this routing.** A real, thesis-relevant finding: this
  decision cannot safely be delegated to a small LLM.
- **Conclusion B — the prompt was biased**, not the task. PROMPT A leads with the KG description and states
  a KG-favoring fallback; either could anchor the model toward KG regardless of the question.

Reporting "LLM routing fails" from a single prompt would not distinguish these, and would be a weak,
easily-challenged claim. This step tests prompt-sensitivity directly before scoring anything as a Phase-2
result. Method, rationale, and the pre-registered interpretation tree are documented in the script's
docstring: `src/phase2_step3b_prompt_sensitivity.py`.

## Method

All three prompts route the same 51 non-hierarchy benchmark questions, once each, using the same model
(`llama3.2:3b` via Ollama):

- **A — baseline.** Imported verbatim from `llm_router.py` (not retyped), so behaviour here is directly
  comparable to the original run.
- **B — DOCS-first.** Identical criteria to A, but DOCS is described before KG, and "default" language is
  removed in favour of symmetric framing. Isolates whether the KG-bias is an ordering/anchoring artifact.
- **C — few-shot.** A's ordering and criteria, plus 5 synthetic worked examples (different diseases, crops,
  and countries than the benchmark, to preserve the "not tuned to the test set" property of PROMPT A) —
  including one explicit example mapping a cross-disease question to KG, since that was baseline's costliest
  error type.

Each variant is scored against: (1) the pre-registered category-level oracle from
`phase2_step1_oracle.py`; (2) how many of the 12 *systematic* RAG-win questions it actually catches — the
harder, more meaningful test than the category-level number; (3) whether it violates its own "simple
lookup → DOCS" rule on the factual category; (4) whether it misroutes any of the three risk-critical
categories (negative, cross_border, cross_disease) to RAG, since Phase 1 showed RAG fails worst on exactly
these.

## Results

| variant | acc. vs. category oracle | systematic RAG-wins caught | factual → DOCS | risky misroutes to RAG |
|---|---|---|---|---|
| A — baseline | 80% | 2/12 | 4/10 | none |
| B — DOCS-first | 82% | **6/12** | 8/10 | none |
| C — few-shot | 90% | 2/12 | 7/10 | **xd_02 (cross-disease)** |

Per-question detail on the 12 systematic RAG-wins (the honest test — this is where the category-level
"accuracy vs oracle" number can mislead):

| qid | category | A | B | C |
|---|---|---|---|---|
| f03 | factual | rag ✓ | rag ✓ | kg |
| f05 | factual | rag ✓ | rag ✓ | rag ✓ |
| f08 | factual | kg | kg | rag ✓ |
| f09 | factual | kg | rag ✓ | kg |
| r04 | region_specific | kg | rag ✓ | kg |
| m04 | multi_hop | kg | kg | kg |
| c03 | constraint | kg | rag ✓ | kg |
| as_m02 | multi_hop | kg | kg | kg |
| as_c02 | constraint | kg | rag ✓ | kg |
| as_d02 | cross_border | kg | kg | kg |
| pm_d02 | cross_border | kg | kg | kg |
| pm_d03 | cross_border | kg | kg | kg |

## Interpretation

**B (DOCS-first) is the standout result, and the mechanism is informative.** Simply reordering the same
criteria — no new content, no examples — roughly tripled the systematic-RAG-win capture rate (2/12 → 6/12)
and fixed most of the factual-lookup violations (4/10 → 8/10), with zero new risky misroutes. This is strong
evidence that baseline's KG-collapse was substantially an ordering/anchoring artifact of PROMPT A, not
solely a ceiling on the 3B model's routing ability.

**C (few-shot) is a cautionary result, not a win.** Its category-level "90% accuracy" is inflated by the
factual category (10 of 51 questions) and does not reflect improvement on the harder cases: on the 12
systematic RAG-wins outside easy lookups, C performs no better than baseline (2/12, and a *different* 2
than baseline's). More importantly, C is the only variant that misrouted a cross-disease question (xd_02)
to RAG — the single costliest error type in the Phase-2 risk framework — **despite the prompt containing an
explicit worked example teaching exactly that mapping** ("joins facts across diseases → KG"). The example
did not transfer to the held-out cross-disease question. With only 2 cross-disease questions in the
benchmark, this single misroute is a 50%-of-category event and should not be over-read as "few-shot
prompting causes cross-disease failures" — but it is strong enough to treat few-shot content as unproven,
and not to prefer C over B on current evidence.

**A confound that limits how far any of this can be trusted yet: run-to-run instability.** PROMPT A here
caught 2/12 systematic wins (f03, f05); the *original* router run, using the identical prompt, caught only
1/12 (f05 alone). Same model, same prompt, different result. This means every number in this table carries
real sampling noise, and a gap of 1 (e.g., C vs A on systematic wins) is not distinguishable from noise on
current evidence. A gap of 4 (B vs A) is more likely to be a real effect, but has not yet been confirmed
under repetition.

## Conclusion (provisional)

None of the four pre-registered interpretation branches (see script docstring) fit cleanly, and that is
itself the finding: routing quality is highly and non-intuitively prompt-sensitive; the effective fix found
so far is structural (reordering), not content-based (examples); and the intuitive "teach it with examples"
fix introduced a new instance of the costliest error type on exactly the category one of its examples
targeted. Before this becomes a scored Phase-2 result or a stated thesis conclusion, it requires a
multi-run check (repeat A and B — and plausibly C — 3× each, as already anticipated for the router in
`Phase2_Plan.md` Step 3) to establish whether B's improvement and C's misroute are robust effects or
artifacts of one sampling run each.

## Artifacts

- Script: `src/phase2_step3b_prompt_sensitivity.py`
- Raw decisions + scores: `data/phase2_prompt_sensitivity.json` (generated locally, not committed —
  regenerable by rerunning the script; see `.gitignore` conventions for regenerable outputs)
- Systematic RAG-win list source of truth: `src/phase2_step2a_diagnose.py`
- Category-level oracle mapping source of truth: `src/phase2_step1_oracle.py`

## Next step

Multi-run consistency check on variants A and B (minimum) before selecting a router prompt or drawing a
final Phase-2 conclusion about LLM-router feasibility. Not yet started.