# Phase 4 — Generalisation to Healthcare: Execution Plan

*Companion to Phase4_Design.md. Mirrors the original 7-stage methodology (`RESEARCH_README.md`) that
produced Phase 1, adapted for a second domain, plus the design/build/verify/evaluate/interpret discipline
used throughout Phases 2–3.*

---

## Step 0 — Feasibility gate (prerequisite, go/no-go)

- Query `openFDA`'s `drugsfda.json` endpoint programmatically for a small candidate set of active
  substances/ATC classes; confirm structured, parseable records (sponsor, approval status, dosage form,
  active ingredient) are actually returned, not just documented as available.
- Pull EMA's medicines data export (JSON/table) for the same candidate substances; confirm ATC codes,
  authorisation status, and active substance names are present and machine-readable.
- Check for **real cross-region divergence** in this candidate set (some substance/drug approved in one
  region, not the other) — if the candidate set is too clean (full overlap), widen it before concluding
  divergence doesn't exist; do not force a benchmark category onto data that doesn't support it.
- Check ATC data is rich enough to support genuine multi-level hierarchy questions (does the candidate set
  span multiple ATC classes with siblings/parents in common?).
- **Produces:** `phase4_step0_feasibility.json` + go/no-go decision. If any of the above fails at
  reasonable candidate-set size, stop and report why — an honest negative result about domain
  transferability is a valid outcome (per `Phase4_Design.md`'s scope discipline), not a failure to fix at
  all costs.

## Step 1 — Benchmark design (before any data collection, same bias-control discipline as Stage 2)

- Adapt the 7 categories (table in `Phase4_Design.md`) into concrete, answerable questions, written
  against a bounded candidate set of ATC classes/substances chosen in Step 0.
- Pre-register a ground-truth answer and a predicted winning arm for every question, **before** the KG or
  RAG corpus is built — the same discipline that made Category 1 a real bias check in Phase 1, not a
  post-hoc rationalisation.
- **Produces:** `data/benchmark_phase4.json` (mirrors `benchmark_cat1_2.json`'s schema: id, question,
  category, pre-registered answer, predicted arm).

## Step 2 — Source the data

- Pull the actual records for the chosen candidate set from `openFDA` and EMA's export, at the scope
  decided in Step 0 (a bounded set of ATC classes, not full FDA/EMA coverage).
- Verify every extracted record against its source before use (same "verify, don't trust" principle as
  Phase 1's BVL/Mattilsynet extraction) — spot-check a sample against the live EMA/FDA product pages.
- **Produces:** `data/fda_drugs_US.json`, `data/ema_medicines_EU.json` (raw, verified extracts).

## Step 3 — Build the KG and the parallel RAG corpus (data parity)

- RDFLib graph, schema mirroring Phase 1's n-ary Authorisation node
  (`Authorisation --hasProduct--> Product --containsSubstance--> ActiveSubstance`,
  `--inRegion--> Region`, `--regulatedBy--> Authority`), plus a new `ActiveSubstance --inAtcClass--> AtcClass`
  hierarchy component (`AtcClass --broaderThan--> AtcClass`, multi-level) to support Category 7.
- Write the same underlying facts as prose documents for the RAG arm — same data-parity principle as Phase
  1: the two arms differ only in representation, never in underlying information.
- **Produces:** `src/build_kg_phase4.py`, `data/kg_phase4.ttl`, `data/rag_docs_phase4.json`.

## Step 4 — Query layer (deterministic, LLM never writes queries)

- SPARQL query functions per category, mirroring `kg_arm.py`'s `ROUTING`-table pattern — one deterministic
  function per question category, parameterised by substance/ATC-class/region as appropriate.
- Verbalisation functions mirroring `kg_verbalise.py` — **apply the lessons already paid for in this
  project**: parametrise every disease/region/class name from the actual query result, never hardcode a
  placeholder (the exact bug class found and fixed in `Correction_KG_Disease_Name_Bug.md` and
  `Phase3_Step2_FusionArm.md`); keep category-label parentheticals structurally separate from any
  substance/entity list (the exact ambiguity fixed in the `multi_disease` template fix).
- **Produces:** `src/kg_arm_phase4.py`, `src/kg_verbalise_phase4.py`, `src/rag_arm_phase4.py`,
  `src/eval_pipeline_phase4.py` (shared prompt + explain, same as `eval_pipeline.py`).

## Step 5 — Blind comparative evaluation, multi-run

- Run both arms over the full benchmark, multiple runs (3, matching Phase 1's convention).
- Blind grading sheet, same format/shuffling convention as `stage6_eval.py`/`phase3_step3_fusion_generate.py`.
- Grade against the Step-1 pre-registered ground truth. If a second grader is available, use one — Phase
  3's self-regrade limitation (`Phase3_Step4_FusionResults.md`) is worth actively avoiding here if at all
  possible, given it's already a known, documented weak point of this project's methodology.
- **Produces:** `data/phase4_comparison_runs.json`, `data/phase4_grading_sheet_BLIND.json` + key.

## Step 6 — Core analysis

- Correctness/faithfulness for always-KG, always-RAG, per category — direct comparison against Phase 1's
  numbers (correctness gap, faithfulness gap, which categories favour which arm).
- Specifically: does Category 7 (hierarchy) finally produce a result, and does it favour the KG as
  predicted?
- **Produces:** comparison tables, same format as `Phase1_Results.md`.

## Step 7 — Interpretation and write-up

- Answer the Phase-4 RQ: does the KG-vs-RAG advantage replicate, and at what magnitude, in a domain sourced
  and built independently of Phase 1's?
- Report against the pre-registered predictions, itemized confirm/disconfirm, same discipline as every
  prior phase.
- State what this means for the thesis's central claim: is "structure helps for
  relational/absence/cross-border/hierarchical regulatory questions" a domain-general finding, or
  specific to the plant-protection case that happened to be studied first?
- **Produces:** `docs/Phase4_Results.md`.

---

## Deliverables checklist

- [ ] `phase4_step0_feasibility.json` + go/no-go (Step 0)
- [ ] `data/benchmark_phase4.json`, pre-registered before data collection (Step 1)
- [ ] `data/fda_drugs_US.json`, `data/ema_medicines_EU.json`, verified (Step 2)
- [ ] `kg_phase4.ttl`, `rag_docs_phase4.json`, data-parity checked (Step 3)
- [ ] Deterministic query layer + verbalisers, applying prior bug lessons up front (Step 4)
- [ ] Blind multi-run comparison, second grader if possible (Step 5)
- [ ] Core analysis tables (Step 6)
- [ ] `Phase4_Results.md` (Step 7)
- [ ] (optional, stretch) revisit Phase 2 routing and/or Phase 3 fusion in this domain — explicitly not
      required for Phase 4's core RQ

## Pre-registered prediction (record before Step 5 runs)

The KG-vs-RAG advantage found in Phase 1 is expected to replicate on Categories 3–6 (relational, absence,
cross-border), for the same underlying reason: document retrieval struggles with precise relational/negative
queries regardless of domain. Category 7 is expected to become instantiable for the first time in this
thesis and to favour the KG strongly, given ATC's genuine hierarchy. Category 1 is expected to show no KG
advantage (bias check). The magnitude of the overall gap is not predicted to match Phase 1's exactly —
pharma records are likely denser and more complex per entry, which could make either arm's task harder in
ways that shift the gap in either direction. Report confirmation and disconfirmation honestly, as in every
prior phase.

## Scope discipline (see also Design doc)

- This phase is a replication of Phase 1's core comparison in a new domain — it is not a re-run of Phase
  2's routing investigation or Phase 3's fusion investigation, which are explicitly out of scope here
  (optional future work only).
- If Step 0 shows the two data sources cannot be feasibly matched, report that honestly and stop — do not
  force a mismatched benchmark to get a result.
- Do not scale beyond a bounded candidate set of ATC classes/substances; matching Phase 1's corpus scale
  (a handful of categories, tens of benchmark questions) keeps this phase comparable and completable.
  