# Phase 4, Step 6 — Results (final, post data-parity fix)

## Headline

| condition | correct | faithful | n | stability |
|---|---|---|---|---|
| KG | 88% | 86% | 42 | 86%-93% across 3 runs |
| RAG | 45% | 76% | 42 | 43%-50% across 3 runs |

These numbers supersede the earlier pre-fix run. That run showed KG at a suspiciously perfect 93%/93%
with zero variance — a single-question data-parity bug (below) inflated it. With the bug fixed, KG's real
reliability is lower and shows genuine run-to-run variance, including a confirmed hallucination (below).
This is exactly why every prior phase in this project insisted on multi-run testing before trusting a
result: the first, cleaner-looking number was the less honest one.

## The most important finding: KG hallucinated on `r2`, in 2 of 3 runs

`r2`'s KG facts_text states exactly one fact: *"Niraparib is authorised via the EU's centralised
procedure (EMA)."* Nothing else. Yet in `run1` and `run3`, the KG arm answered: *"Niraparib is authorised
via **both** the EU's centralised procedure (EMA) **and at the national level**"* — a fabricated addition,
correctly graded incorrect and unfaithful both times. `run2` answered correctly and faithfully.

This is a genuine, repeated fabrication from the "gold-standard" arm, on a question with short,
unambiguous, complete facts — not a hard multi-hop case, not a borderline judgment call. It directly
tempers any narrative of "KG is reliable, RAG is the one that hallucinates." Both arms can fabricate;
this benchmark just hadn't caught the KG arm doing it before this run, because the earlier single-run
demo and the first 3-run pass (with the parity bug still in place) both happened to land on `r2`'s one
faithful phrasing by chance.

## Data-parity fix confirmed working, with a nuanced result

RAG's `r2` answers now sometimes correctly extract and state the centralised-procedure fact (`run2`:
*"...which was granted via the EMA's centralised procedure"* — correct). `run1` and `run3` still miss it
despite the fact being genuinely present in the retrieved text. This is a **different and more legitimate
finding than before**: previously RAG couldn't answer at all because the fact was missing (a parity bug,
not a real result); now the fact is present and RAG extracts it unreliably (1/3) — a real, if modest,
extraction-reliability limitation, fair to report.

## Per-category, updated

| category | KG | RAG | verdict |
|---|---|---|---|
| factual | 100% | 78% | both strong (control category) |
| negative | 100% | 100% | tie |
| constraint | 100% | 100% | tie |
| region_specific | 67% | 0% | KG's `r2` hallucination pulls this down from the earlier (bugged) 100% |
| cross_border | 100% | 0% | real: RAG's K=3 retrieval can't see enough of the 8-candidate pool |
| multi_hop | 100% | 0% | real: same retrieval-breadth issue + a genuine ATC-prefix confusion |
| hierarchy | 67% | 33% | real but not uniform — see the h1/h2/h3 breakdown below (unchanged by the fix) |

### `hierarchy` — unchanged by the parity fix, still the clearest real finding

| item | KG | RAG | what it actually tests |
|---|---|---|---|
| `h1` (list all 4 substances sharing niraparib's L01 group) | 0/3 | 0/3 | **enumerate-all-N** — both arms fail equally (3B model limitation, not KG vs RAG) |
| `h2` (which substance shares lecanemab's N06D subgroup) | **3/3** | 0/3 | **pairwise filter** — clean, repeatable KG win, the cleanest result in this phase |
| `h3` (does aducanumab share N06D — yes/no) | 3/3 correct, 1/3 faithful | 3/3 correct, 3/3 faithful | both correct; KG's own phrasing occasionally reads as self-contradictory |

`h1` remains a shared 3B-model limitation, not a KG-vs-RAG difference — verified in Step 4 that the KG's
facts_text lists all 4 correct substances; the model still only echoes 1–2 across all 3 runs, same as RAG.

### `cross_border` / `multi_hop` — unchanged, still a real retrieval-breadth finding

RAG's K=3 retrieval cannot see enough of the 8-candidate pool to answer questions requiring a full-corpus
comparison. Distinct from the `r2` parity bug: the underlying facts ARE present in the RAG prose here,
RAG just can't retrieve enough of it at once. `m1` additionally shows a genuine ATC-prefix reasoning
error (RAG wrongly includes isatuximab, `L01XC38`, under an `L01F` filter in one run).

## Revised interpretation

The core finding survives the correction and the hallucination discovery: KG substantially outperforms
RAG on this pharma benchmark (88% vs 45%), replicating Phase 1's directional finding in a domain built
completely independently. But the magnitude is smaller and the KG arm is shown to be genuinely fallible
too, not a clean baseline — the honest version of this result is **"structured retrieval reduces but does
not eliminate fabrication risk,"** not **"structured retrieval solves faithfulness."** The `h1` finding
(both arms fail at full enumeration) and the `r2` hallucination (KG fabricates even from clean, complete,
unambiguous facts) are the two findings most worth foregrounding in the write-up — both cut against a
simple "KG wins, case closed" narrative in favour of a more precise, defensible one.