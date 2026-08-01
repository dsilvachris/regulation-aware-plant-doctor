# Phase 4, Step 6 — Results (with corrections)

## Headline

| condition | correct | faithful | n | stability |
|---|---|---|---|---|
| KG | 93% | 93% | 42 | 93%-93% (zero variance across 3 runs) |
| RAG | 50% | 67% | 42 | 50%-50% (zero variance across 3 runs) |

Both arms show zero run-to-run variance in correctness. This is expected, not suspicious: both arms
retrieve deterministically (SPARQL and embedding top-k are both deterministic), so the *facts* shown to
the LLM are identical every run — only phrasing varies, and phrasing variation never flipped a
correctness verdict on this benchmark. Worth stating as a real, structural property of this comparison.

## Per-category, with the nuance the aggregate hides

| category | KG | RAG | verdict |
|---|---|---|---|
| factual | 100% | 89% | both strong (control category, as designed) |
| negative | 100% | 100% | tie |
| constraint | 100% | 100% | tie |
| region_specific | 100% | 17% | **`r2` was a data-parity bug — see below, not a fair result** |
| cross_border | 100% | 0% | real: RAG's K=3 retrieval can't see enough of the 8-candidate pool |
| multi_hop | 100% | 0% | real: same retrieval-breadth issue + a genuine ATC-prefix confusion |
| hierarchy | 67% | 33% | **real but not uniform — see the h1/h2/h3 breakdown below** |

### `region_specific` (`r2`) — a real bug, now fixed, not a genuine finding

RAG answered every run: *"cannot be answered based on the provided facts, as they do not indicate
whether..."* — and it was right that it couldn't. `build_kg_phase4.py`'s RAG prose never stated the word
"centralised" anywhere, while the KG's `q_is_centralised()` fact was verbalised explicitly. This is a
data-parity violation (the same principle Phase 1 was built around: both arms must see the same
underlying information, differing only in representation) — `r2`'s ~100%-vs-0% gap measured "was this
fact written into the prose," not "can RAG reason about centralisation." **Fixed**: the RAG prose
template now states the centralised-procedure fact explicitly wherever the KG does. This benchmark run
predates the fix — `r2`'s numbers here should not be cited as a finding; a re-run is needed for a fair
reading of this category.

### `hierarchy` — the real story is per-question, not the aggregate

| item | KG | RAG | what it actually tests |
|---|---|---|---|
| `h1` (list all 4 substances sharing niraparib's L01 group) | 0/3 | 0/3 | **enumerate-all-N** — both arms fail equally |
| `h2` (which substance shares lecanemab's N06D subgroup) | **3/3** | 0/3 | **pairwise filter** — clean, repeatable KG win |
| `h3` (does aducanumab share N06D — yes/no) | 3/3 correct, 1/3 faithful | 3/3 correct, 3/3 faithful | both correct; KG's own phrasing occasionally reads as self-contradictory |

`h1` is not a KG-vs-RAG difference — it's a 3B-model limitation. Verified directly in Step 4 that the KG's
facts_text lists all 4 correct substances; across 3 runs the model still only echoed 1–2 of them, same
failure as RAG. The category's 67%/33% aggregate is real but should not be reported as "KG solves
hierarchy" — the accurate claim is narrower: **KG solves pairwise/filtered hierarchy checks reliably;
neither arm reliably enumerates a full match set from this 3B model.**

`h3` surfaces a smaller, separate issue: the KG's verbalised fact for this question
(`"...shares the N06D subgroup only with those comparators for which both conditions are true"`) is
logically correct but somewhat convoluted, and the model sometimes restates it in a way that reads as
self-contradictory ("No... [but] shares the subgroup with lecanemab and donanemab") even though the
bottom-line answer stays correct. Correctness survives; faithfulness takes the hit. Worth simplifying
that verbaliser sentence in a future iteration, though not blocking any conclusion here.

### `cross_border` / `multi_hop` — real, and worth being precise about the mechanism

RAG consistently answers *"no information provided"* on `d1`/`d2`, because these ask it to compare across
all 8 candidates while it only retrieves K=3 — a genuine retrieval-breadth limitation, and unlike `r2`,
**not** a parity bug: the underlying facts ARE present in the RAG prose, RAG simply can't see enough of
the corpus in one retrieval to use them. `m1` compounds this with a second, independent error: RAG's
run2 answer wrongly includes isatuximab (ATC `L01XC38`) under the `L01F` filter — a real ATC-prefix
confusion, not just a coverage gap.

## Status

Headline numbers are directionally real but the `region_specific` category needs a re-run with the
corrected RAG prose before being cited. The `hierarchy` category's true finding is narrower and more
specific than the aggregate suggests. Recommend: regenerate + re-grade before writing final Phase 4
conclusions, now that the parity bug is fixed.