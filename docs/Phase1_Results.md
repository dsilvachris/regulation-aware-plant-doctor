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

Wiring real crops improves the graph's accuracy and completeness. It does **not** change the KG-vs-RAG
results, because no benchmark question turns on the specific crop — the comparison is unaffected, and this is
stated rather than implied.

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