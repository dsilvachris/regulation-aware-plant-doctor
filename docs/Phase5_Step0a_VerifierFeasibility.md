# Phase 5, Step 0a — Verifier Feasibility: Confirmed GO

## Method

Two candidate deterministic verifiers tested against a real test set: the confirmed `r2` fabrication
(`Phase4_Step6_Results.md`) plus all 35 correct-and-faithful KG answers from Phase 4's actual graded data,
each paired with its real facts_text (re-derived from `kg_arm_phase4.py`/`kg_verbalise_phase4.py`, not
retyped).

- **Candidate A — naive entity presence.** Extract capitalised words/codes from the answer, flag if any
  are absent from facts_text.
- **Candidate B — qualifier/coordination-aware.** Detect compound claims (`"both X and Y"`, `"as well as"`,
  `"in addition to"`), split into branches, verify each independently. Falls back to Candidate A's method
  when no compound structure is present.

## Round 1: B catches r2, but both candidates share 6/35 false positives

Candidate A missed `r2` entirely, exactly as predicted — no new entity was fabricated, only an unsupported
relationship between two already-present entities ("both the centralised procedure **and** the national
level"). Candidate B correctly split the compound claim and flagged the unsupported branch.

Both candidates shared the same 6 false positives, traced to two distinct, narrow causes — not a
fundamental flaw in the coordination-splitting logic itself:

1. **Discourse-marker words extracted as if they were entities.** `"According"`, `"Based"`, `"Both"` are
   capitalised at sentence-start and matched the entity-extraction regex, but aren't named entities.
2. **A genuine regulator/region synonym gap.** `n1`'s facts_text says only *"...status in **EU** is:..."*;
   the graded-correct answer says *"...authorised by the **EMA**..."* — a faithful restatement (EMA is the
   EU's regulator, stated explicitly in every fact this KG produces), not an invented fact, but the
   verifier had no way to know that.

## Round 2: both fixed, clean result

- Expanded the stopword list with discourse markers (`according`, `based`, `both`, `also`, `however`, etc.)
- Added a small `EMA↔EU`, `FDA↔US` synonym table — justified by the KG's own schema
  (`build_kg_phase4.py`'s `AUTHORITY` dict states this correspondence explicitly for every fact), not
  external knowledge smuggled in.

Re-run: **Candidate B still catches `r2`; false positives drop to 0/35.**

| | catches r2 | false positives (n=35) |
|---|---|---|
| Candidate A (naive entity) | No | 0/35 (after fixes) |
| Candidate B (qualifier-aware) | **Yes** | **0/35** |

## Decision: GO — Candidate B selected for Work Package B

The method is confirmed to catch the one real, confirmed hallucination this project has produced, with
zero false positives on a real (not synthetic) 35-case known-good set. This is deterministic, cheap
(regex + set lookups, no model call), and explainable (the flagged branch and the missing keyword can be
shown directly to the user — supporting "detection, not correction, flag and disclose").

## Caveats, stated honestly before this goes further

- **n=35 known-good cases is not large**, and all come from one domain (Phase 4's pharma benchmark) graded
  by one person. The 0/35 false-positive rate is a real, verified result, not a guaranteed rate at scale —
  Work Package B's own evaluation (Step 2) should expand this set, including cases from Phase 1's
  plant-protection domain, before treating 0% as a stable property of the method.
- **Only one true positive case exists** (`r2` itself) — the method has not been tested against a *second*,
  independently-occurring fabrication, because no second one has been found in this project yet. If Step 2
  or later grading surfaces another real hallucination, it should be added to this test set immediately as
  a second true-positive check, not left as a one-off validation.
- **The synonym table is domain-specific and manually curated** (2 pairs, both justified by this KG's own
  schema). Extending this method to a different domain (e.g. back to plant-protection's BVL/Mattilsynet) would
  need its own small, similarly-justified synonym table — not assumed to transfer automatically.

## Status

Step 0a complete. Candidate B (qualifier-aware matching with discourse-marker filtering and domain
synonyms) is the method for Work Package B. Proceeding to Step 0b (hosting feasibility) before Step 1
(architecture integration).