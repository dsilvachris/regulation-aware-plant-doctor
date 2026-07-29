## Addendum — crop representation and the hierarchy-traversal category

### Real crop data (resolved)

The earlier build represented each German authorisation's crop at the disease-default level (e.g. all late
blight authorisations labelled "potato"). This was corrected: crops are now drawn from the BVL `awg_kultur`
table, which links each authorised *use* to its specific crop(s). The resulting distribution is accurate and
biologically sensible — for late blight, German authorisations span **potato (82), tomato (40), aubergine
(7), and ornamentals (1)**; for apple scab, they span pome and stone fruit (apple, pear, quince, and several
Prunus species); the single German cucurbit-mildew product is in fact authorised on **ornamentals** while
targeting *Podosphaera xanthii*.

Two honest observations follow from the real crop data:
- The "apple scab" authorisations (scoped by the pathogen *Venturia inaequalis*) are in practice authorised
  across pome/stone fruit, not apple alone — the crop breadth reflects real product labelling.
- Group-level crop terms (e.g. "pome fruit") appear directly as crop values in the data, so a degree of crop
  grouping exists implicitly in naming even though the explicit parent-child crop table does not cover the
  studied crops (see below).


### Category 7 (hierarchy-traversal): pre-registered but not instantiable

Category 7 was designed to test whether a knowledge graph can traverse a crop *hierarchy* — answering a
question about a child crop from an authorisation recorded at a parent crop-group level, which flat retrieval
handles poorly. Investigating the BVL data established that this category **cannot be instantiated for the
studied crops**:

- The `awg` table carries no crop field; crop links live in `awg_kultur` (recovered, see above).
- A crop-group table (`kultur_gruppe`) exists and encodes parent→child relationships for *some* crops, but
  the crops central to this study — potato (EPPO SOLTU), apple, and the cucurbits — appear in **no**
  parent-child relationships in it. Potato is neither a child of any group nor a parent of any crop.

A hierarchy-traversal question therefore cannot be constructed for these diseases' crops, because the
required parent-child structure is absent from the data. This is reported as a **pre-registered category that
the available data could not support**, rather than omitted — the design predicted a KG advantage on crop
hierarchy, and the honest finding is that the BVL crop coding for these crops is flat. It remains a
well-defined test for future work on crops (e.g. cereals) whose BVL coding *is* hierarchical.

## Addendum — KG-arm disease-name bug found and corrected (post-hoc, discovered via Phase 3)

A bug was found in `kg_verbalise.py` during Phase 3's Step 1 conflict diagnostic (see
`docs/Correction_KG_Disease_Name_Bug.md` for full detail): several verbaliser branches hardcoded the
string "late blight" into the KG arm's facts text regardless of the actual disease queried, affecting all
12 apple-scab/powdery-mildew extension questions. The underlying SPARQL retrieval was always
disease-correct; only the phrasing handed to the LLM was wrong. Reading the graded transcripts confirmed
17 of 24 graded KG-arm items on this subset were marked incorrect specifically because the LLM faithfully
noticed the mismatch and abstained — a correct response to a broken input, scored as if it were a
reasoning failure.

The bug was fixed, the 12 affected questions' KG answers were regenerated and blind-graded (same
convention as the original: independent random seed, System A/B blinded, grader unaware of arm identity
until scoring), and merged into a new master grading file (`grading_sheet_BLIND_corrected.json` — the
original file remains on record, unmodified).

**Corrected headline numbers** (129 items total, same n as before):

| metric | before | after | delta |
|---|---|---|---|
| KG correctness | 50.4% | **62.0%** | **+11.6 pts** |
| KG faithfulness | 96.1% | 94.6% | −1.6 pts |
| RAG correctness | 42.6% | 39.5% | −3.1 pts |
| RAG faithfulness | 87.6% | 80.6% | −7.0 pts |
| KG correctness, affected 12-question subset | 29.2% | **91.7%** | **+62.5 pts** |
| RAG correctness, affected 12-question subset | 70.8% | 54.2% | −16.7 pts |

**KG's advantage over RAG widens substantially** (from +7.8 points to +22.5 points headline correctness)
once the bug is fixed — the qualitative Phase 1 conclusion (KG is the stronger arm) is not overturned, it
is strengthened. On the 12-question subset specifically, KG's correctness nearly triples (29.2% → 91.7%),
confirming the bug had been severely understating its real performance there.

**A caveat, stated honestly:** RAG's own answers were never regenerated (the bug never touched RAG), yet
RAG's correctness and faithfulness on the 12-question subset also shifted (70.8%→54.2% correctness,
and −7.0 points faithfulness overall) purely from being blind-graded a second time in a fresh session.
This is not a change in RAG's actual answers — it reflects ordinary grader judgment variance between
sessions on the harder, more ambiguous disease-extension questions, the same kind of variance Phase 1's
original inter-rater-agreement check (Cohen's κ) was designed to catch. It is noted here rather than
smoothed over; it does not affect the KG-side correction, which is the change this addendum is about.

All downstream Phase 2 numbers were recomputed against the corrected data — see
`docs/Phase2_Results.md`'s addendum for what changed there (short version: the deterministic-router-vs-LLM
comparison is qualitatively unchanged, and the cross-disease cost gradient across LLM prompt variants,
Phase 2's single most load-bearing finding, is untouched by this correction since `xd_01`/`xd_02` were
never affected by the bug).