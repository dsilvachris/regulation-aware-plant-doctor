# Phase 2 — Adaptive Retrieval: Design

*Programme B, Phase 2. Post-thesis research (may also strengthen the thesis if the supervisor deems it in scope). Documented to thesis/publication standard.*

## Motivation

Phase 1 established that neither retrieval strategy dominates: the knowledge graph wins on relational,
absence, cross-border, and cross-disease queries; document-RAG matches it on simple lookup and is more
faithful by abstaining. The natural next question — and the pre-registered Phase-1→Phase-2 decision gate —
is:

> **How should a system decide, per question, which retrieval strategy to use?**

This is *adaptive retrieval*: routing each query to the strategy best suited to it, rather than committing
to one representation for all queries.

## The core research tension

Phase 1's architecture rests on a deliberate principle: **the LLM never sits in the control path.**
Retrieval is deterministic; the LLM only phrases verified facts. An LLM-based router reintroduces the LLM
into a decision that governs *what knowledge is retrieved* — precisely the thing Phase 1 excluded.

Phase 2 does not assume this is safe. It **measures** it. The research question is therefore not "can we
build a router" but:

> **RQ (Phase 2): How closely can an LLM-based router approach optimal routing, and what is the cost of its
> misrouting — particularly on the safety-critical query types (absence, cross-border) where the wrong
> strategy fails worst?**

This directly extends the thesis's central theme: not whether to use an LLM, but *which decisions* an LLM
can be trusted with, and at what risk. A key sub-claim to test: **routing (classifying a question's type) is
a lower-stakes LLM decision than answering** — a misroute yields a suboptimal-but-still-grounded answer, not
a fabricated fact. Phase 2 tests whether that claim holds empirically.

## Design

### Conditions compared

1. **Oracle routing (ceiling).** Each benchmark question carries a known category (from the pre-registered
   Phase-1 design), and Phase-1 results tell us which strategy is optimal per category. Oracle routing sends
   each question to its optimal arm. This is the upper bound — the best any router could do.
2. **LLM router (the system under test).** An LLM classifies each question (into a retrieval strategy or
   query type) using a fixed prompt; the question is then routed accordingly. The LLM classifies; it does
   **not** write queries or generate the final answer from unverified text — those remain deterministic /
   grounded as in Phase 1.
3. **Deterministic router (baseline).** A rules/feature-based classifier (keyword and structural cues) that
   uses no LLM. Establishes what non-LLM routing achieves, and isolates the LLM's contribution.
4. **(Reference) single-arm baselines.** Always-KG and always-RAG, i.e. the Phase-1 arms with no routing,
   for context.

### What "optimal per category" means (from Phase 1 evidence)

| category | optimal arm (from Phase 1) | rationale |
|---|---|---|
| factual (lookup) | either / RAG | tie; both retrieve single facts |
| region-specific | KG (marginal) | KG respects country boundary |
| multi-hop | KG | traversal |
| constraint | KG | filtered/relational |
| negative / absence | KG | definitive "no"; RAG hallucinates here |
| cross-border | KG | joins two jurisdictions |
| cross-disease | KG | joins across diseases (RAG structurally can't) |

*Note the asymmetry of risk: misrouting a lookup to the KG costs little; misrouting an absence or
cross-border question to RAG costs a lot (Phase 1: RAG faithfulness collapses on absence). The evaluation
must weight these, not just count routing accuracy.*

### Metrics

- **Routing accuracy** — % of questions the router sends to the optimal arm (vs oracle).
- **End-to-end correctness & faithfulness** — the Phase-1 metrics, but on the *routed* system, so the
  cost of misrouting shows up in the actual answer quality (blind-graded, multi-run, as in Phase 1).
- **Cost-of-misrouting analysis** — for each misrouted question, the drop vs oracle; broken down by
  category, with special attention to the safety-critical ones (absence, cross-border).
- **Router consistency** — does the LLM router make the same decision across runs? (It may not — a new
  failure mode the deterministic router doesn't have.)

### Protocol (mirrors Phase 1 for comparability)

- Same 3-disease benchmark (~51 questions), same model, same blind multi-run grading, same second grader
  where feasible.
- The router condition is evaluated end-to-end; oracle and deterministic conditions give the ceiling and
  the no-LLM baseline.
- Pre-register the prediction: *the LLM router will approach oracle on clearly-typed questions but lose
  ground on ambiguous ones; its worst misroutes will be the costliest categories.* Report where this holds
  and where it doesn't.

## Expected contribution

Whether the LLM router does well or badly, Phase 2 yields a publishable claim:
- If it approaches oracle **and** its misroutes are cheap → evidence that LLMs can be trusted with the
  *routing* decision even in regulated domains, supporting a tiered-trust architecture.
- If it misroutes the costly categories → evidence that even "low-stakes" LLM decisions carry hidden risk
  in safety-critical retrieval, strengthening the case for deterministic control.

Either result advances the thesis's core question: **which decisions can we safely delegate to the model?**

## Open design choices (to resolve during build)

- Router granularity: classify into {KG, RAG} (binary) vs into the 7 query categories then map to an arm.
- Router prompt design: zero-shot vs few-shot with category examples.
- Whether a "confidence/abstain" option for the router itself is worth testing (router says "unsure" →
  default to the safer arm).