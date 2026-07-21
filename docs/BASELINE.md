# Frozen Baseline — Experimental Control

**Purpose.** This document records the exact configuration of the system frozen at Stage 0 of the
Knowledge Graph vs document-RAG study. The baseline serves as the experimental control and is not
modified during the comparison.

**Git tag:** `baseline-v1.0`
**Commit:** `33eb3de0cb81da3aca3b674734964c7e1e3a2892`
**Date frozen:** 21 July 2026

> **Verify before tagging.** Every value below should be checked against the code as it stands, not
> assumed. A frozen baseline is only useful if the record is accurate.

---

## What is frozen

The **pipeline, code, evaluation framework, benchmark, and repository state** are frozen.

The **knowledge** is deliberately *not* frozen: regulatory data collected in Stage 4 will be supplied to
both experimental conditions — as structured documents for the document-RAG arm and as graph entities and
relationships for the Knowledge Graph arm — so that the two conditions differ only in representation.

---

## Language models

| role | model | source |
|---|---|---|
| primary generation | `llama3.2:3b` | Ollama, local |
| larger-model condition | `llama3.1:8b` | Ollama, local |

All inference is local. No paid APIs.

## Retrieval

| parameter | value |
|---|---|
| embedder (baseline) | `sentence-transformers/all-MiniLM-L6-v2` |
| embedder (fine-tuned variant) | `finetuned-agri-embedder` — regenerable via `src/finetune_embedder.py`, not committed |
| similarity | cosine over normalised embeddings |
| k (documents retrieved) | 3 |
| retrieval similarity threshold (v4 condition) | 0.48 |

**Note on the fine-tuned embedder:** MNR-loss fine-tuning recalibrates the cosine score scale, so the
fixed 0.48 threshold is *not* valid for the fine-tuned model. The baseline comparison uses the general
embedder unless stated otherwise.

## Vision

| parameter | value |
|---|---|
| architecture | MobileNetV2, transfer learning (frozen base) |
| input size | 128 × 128 × 3 |
| classes | 28 (PlantDoc) |
| runtime format | TFLite (`models/agro_vision.tflite`) via `ai-edge-litert` |
| confidence threshold | 0.50 (below → abstain) |
| label order | `data/agro_vision_classes.json` |
| label → action bridge | `data/vision_to_corpus.json` (14 ground / 10 healthy / 4 abstain) |

## Region routing

Deterministic, in order: explicit country words → curated place gazetteer → gate (ask the user).
The LLM never decides the region.

## Conversation

| parameter | value |
|---|---|
| answerable-question relevance threshold | 0.35 (top-1 cosine) |
| history window passed to the model | last 3 turns |

---

## Data

| file | contents |
|---|---|
| `data/corpus.json` | 15 entries — 12 Germany, 3 Norway (late blight, apple scab, powdery mildew) |
| `data/eval_set.json` | 25 held-out questions (6 trap, 11 normal, 4 out-of-corpus, 4 retrieval-stress) |
| `data/region_eval_set.json` | 8 paired region questions (4 DE, 4 NO) |
| `data/region_probe_set.json` | 8 hard probes (adversarial cross-border, implicit location, no location, anchors) |

The eval sets are held out and were never used in embedder training.

---

## Baseline results (reference points for the comparison)

| measure | value |
|---|---|
| useful advice, in-corpus (ungrounded → grounded) | 19% → 57% |
| out-of-corpus refusal (ungrounded → grounded) | 0/4 → 4/4 |
| retrieval top-1, held-out (baseline → fine-tuned) | 76% → 86% |
| over-refusal, 10 runs (3B-strict / 8B-revised) | 34% (29–38%) / 33% (24–38%) |
| out-of-corpus refusal, 10 runs (3B-strict / 8B-revised) | 92% (75–100%) / 52% (50–75%) |
| region probes, hand-graded | 7/8 before the region gate; no incorrect region guesses after it |

Full detail and caveats: `docs/Results_Note_Regulation-RAG_Eval-v1.md`.

---

## Reproducing the baseline

```bash
git checkout baseline-v1.0
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ollama serve            # separate terminal
ollama pull llama3.2:3b
ollama pull llama3.1:8b
```

Grading of the comparison is manual and **blind** — responses are anonymised with respect to condition
before scoring. Each condition is run multiple times; means and observed variation are reported rather
than single-run values.