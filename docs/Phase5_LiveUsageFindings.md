# Phase 5 — Live Usage Findings (to address next session)

Found during a real end-to-end test of the deployed local assistant (not a constructed eval case).

## Finding 1 — severe hallucination, correctly caught

Query: *"There's white powdery coating on my cucumber leaves in Norway, what can I use?"*
Answer fabricated generic IPM advice and cited a non-existent authority, **"Nordic Council of Ministers
(FHC)"** — not BVL, not Mattilsynet, invented outright. A more severe version of the `r2` pattern from
Phase 4 (even short, clean facts_text doesn't guarantee no fabrication). **The verifier correctly flagged
it** — a real, live confirmation of Work Package B, not just the constructed 93-case eval set.

## Finding 2 — a real, structural blind spot in the verifier (the one to fix)

Image-identified powdery mildew, Norway: answer correctly named the real product (**Talius**) but
fabricated its active substance as *"pyraclostrobin and azoxystrobin"* — the real substance is
**proquinazid**. The verifier flagged the answer, but only for citation phrasing, never for the wrong
chemical names.

**Root cause, confirmed**: `verification_layer.py`'s entity extractor (`_extract_entities`) only matches
capitalised words (`[A-Z][A-Za-z]{2,}`). Chemical substance names are correctly written in lowercase
(matching the KG's own facts_text style — "proquinazid," not "Proquinazid"), so they're structurally
invisible to the current check. This is the exact category of fact where an error matters most in this
domain, and it's the one category the verifier currently cannot see at all.

## Next session: proposed fix

Extend `verification_layer.py` to also check lowercase domain-vocabulary terms (chemical substance names)
against the KG's actual known substance list — likely a small addition alongside the existing entity
extraction, checking recognised substance-name tokens case-insensitively rather than only capitalised
ones. Should be evaluated the same way Step 2's method was: test against this exact case (must flag) plus
the existing 93-case known-good set (must not regress false-positive rate).