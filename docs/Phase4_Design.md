# Phase 4 — Generalisation to a Second Regulated Domain (Healthcare): Design

*Program B, Phase 4, per the original roadmap (Phase 1: KG vs RAG · Phase 2: Adaptive Retrieval ·
Phase 3: Hybrid Retrieval & Fusion · Phase 4: Generalisation · Phase 5: Deployment). Same discipline as
every prior phase: design → build → verify → evaluate → interpret, committing after each step.*

## Motivation

Phases 1–3 established a rigorous methodology and a specific set of findings in **one** regulated domain:
plant-protection product authorisation, Germany vs Norway. The core finding — a curated KG improves
correctness on relational, absence, and cross-border questions, while a transparent rule beats LLM-based
adaptive strategies — is only as strong as its generality. A result that holds in exactly one
hand-built domain is a weaker thesis contribution than one shown to hold (or not) in a second, independently
sourced domain with a different regulator, different data shape, and different subject matter.

> **RQ (Phase 4): Does the KG-vs-RAG advantage found in Phase 1 — and the category-level pattern behind
> it (relational/absence/cross-border/hierarchy favour structure; simple factual lookup does not) —
> replicate in a second regulated domain (pharmaceutical drug authorisation, US FDA vs EU EMA), sourced
> and built independently of the plant-protection corpus?**

This also closes the single oldest open thread in the thesis: Category 7 (hierarchy-traversal) was
pre-registered in the original Stage 2 benchmark design but found not instantiable in the three-disease
plant-protection data (`Phase1_Results.md`'s addendum). Pharmaceutical drugs have a genuine, well-established
multi-level classification (ATC — Anatomical Therapeutic Chemical) that plant-protection products do not.
If Category 7 can finally be tested anywhere in this thesis, it is here.

## Domain and data sources (feasibility-checked before committing)

| | Germany/Norway (Phase 1) | US/EU (Phase 4) |
|---|---|---|
| Regulator A | BVL (DE) | FDA — `openFDA` Drugs@FDA API |
| Regulator B | Mattilsynet (NO) | EMA — public medicines data export (JSON/table, updated twice daily) |
| Access | API (DE), manual (NO) | Both free, structured, no-auth-required for basic access |
| Product/substance link | Product → Substance | Product (NDA/ANDA/BLA) → Active ingredient |
| Cross-jurisdiction divergence | Same disease, different authorised products by country | Same active substance/drug, different approval status by region |
| Hierarchy | None found (Category 7 not instantiable) | **ATC classification** — drug → chemical subgroup → pharmacological subgroup → therapeutic subgroup → anatomical group |

Both sources were checked for basic reachability before this design was finalised (see chat record: openFDA's
`drugsfda.json` endpoint and EMA's JSON/table exports are both live, free, and structured). A proper Step 0
feasibility gate (below) verifies this programmatically, at the scale actually needed, before any KG is built
— the same discipline that caught Category 7's non-instantiability in Phase 1 rather than assuming it away.

## Scope decision: replicate Phase 1's core comparison, not the full three-phase arc

Phase 4's primary deliverable is **a Phase-1-shaped KG-vs-RAG comparison in the new domain** — same
7-category benchmark structure, same deterministic-query principle, same blind multi-run grading discipline.
Re-running Phase 2 (routing) and Phase 3 (fusion) in this new domain is **explicitly optional, stretch-goal
future work**, not part of Phase 4's core scope: Phases 2 and 3 already produced domain-general
methodological findings (a transparent rule beats LLM routing; fusion shows promise but needs independent
validation) that are about *how LLMs handle retrieval-control decisions*, not about plant-protection data
specifically — re-verifying them in a second domain would be valuable but is not required to test this
phase's actual RQ (does the KG-vs-RAG advantage generalise). Keeping scope disciplined here avoids the
trap Phase 2/3 explicitly warned against: don't balloon a phase past what its RQ requires.

## Benchmark category mapping (adapted from Phase 1's 7 categories)

| # | category | Phase 1 (plant-protection) | Phase 4 (pharma) |
|---|---|---|---|
| 1 | Factual (control, bias-check — KG must NOT win) | "What pathogen causes late blight?" | "What is the ATC code for ibuprofen?" |
| 2 | Region-specific | "Which products are authorised against late blight in Norway?" | "Which formulations of [drug] are FDA-approved?" |
| 3 | Multi-hop (`KG+`) | "Which substances are authorised in Germany but not Norway?" | "Which active substances in [ATC class] are EMA-authorised but administered via [route]?" |
| 4 | Constraint (`KG+`) | "Which German apple-scab products contain sulfur?" | "Which US-approved products contain both substance A and B?" |
| 5 | Negative/absence (`KG+`, sharpest) | "Is fluazinam authorised in Norway?" | "Is [drug] EMA-authorised?" |
| 6 | Cross-border divergence (`KG+`, the novel category) | "Name a substance authorised in DE but not NO" | "Name a substance FDA-approved but not EMA-authorised (or vice versa)" |
| 7 | Hierarchy-traversal (`KG+`, previously not instantiable) | — (not instantiable) | "Which drugs share [drug]'s ATC therapeutic subgroup?" / "List substances under ATC class [X] approved in both regions" |

Predictions are pre-registered per category, same bias-control principle as Phase 1: Category 1 is a
control and the KG **must not** win there, or the benchmark itself is suspect.

## Pre-registered predictions (recorded before any data collection)

- **Category 1 (factual):** KG and RAG should tie or RAG should slightly lead — same as Phase 1's finding
  that structure offers no advantage on simple lookups. If the KG wins here, that is a benchmark-design
  flaw to investigate, not a result to report.
- **Categories 3–6 (multi-hop, constraint, negative, cross-border):** expected to favour the KG, replicating
  Phase 1's core finding, since these require relational/structured reasoning across the same underlying
  data document retrieval was never well-suited to.
- **Category 7 (hierarchy):** expected to favour the KG strongly, and — unlike Phase 1 — expected to be
  *instantiable at all*, since ATC provides genuine multi-level structure the plant-protection domain lacked.
- **Magnitude:** whether the KG's overall correctness advantage is of similar size to Phase 1's (a ~12–22
  point gap depending on which Phase-2-corrected number is used) or different is treated as a genuinely
  open empirical question, not assumed to replicate exactly. Pharma data is likely larger and more complex
  per-entry than the plant-protection data, which could shift the RAG arm's retrieval difficulty in either
  direction.

## Risk framing and disclosure

This domain involves real medical/regulatory claims about real drugs. Every output in this phase must
carry the same disclosure Phase 1 gave the plant-protection work — a research/methodology testbed, not a
deployable medical information source, and never a substitute for consulting a regulator's own database or
a healthcare professional. Ground truth still comes only from the authoritative sources (`openFDA`, EMA's
own data), never from either system under test — same principle as every prior phase.

## Scope discipline

- Do not attempt full FDA/EMA coverage. Phase 1 scoped to 3 diseases; Phase 4 should scope to a small,
  bounded set of ATC classes or a handful of active substances with clear cross-region divergence, checked
  for real divergence before committing (same "the asymmetry is the finding, not assumed" principle).
- **Candidate substances must be drawn from EMA's centralised-eligible categories** (oncology, HIV,
  diabetes, neurodegenerative, autoimmune, viral diseases, orphan designation, biotech/ATMP) — confirmed
  necessary during Step 0's feasibility check (`Phase4_Step0_Feasibility.md`): EMA's medicines dataset only
  covers the centralised procedure, so common/old generics (which use national authorisation routes) show
  false "divergence" that reflects dataset scope, not real regulatory difference.
- Do not reopen Phase 1–3's plant-protection findings; this phase tests generalisation, not correctness of
  what came before.
- If Step 0's feasibility gate shows the two data sources cannot be matched cleanly (e.g. genuinely
  incompatible schemas, no real divergence in a reasonably-sized sample), that is reported as an honest
  negative finding about domain transferability, not forced into a benchmark that doesn't reflect real data
  — the same standard Category 7's original non-instantiability was held to.