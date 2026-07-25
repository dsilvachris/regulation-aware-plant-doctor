# Stage 2 — Evaluation Benchmark Design

**Scope:** 3 overlap diseases (late blight, apple scab, powdery mildew) × 2 jurisdictions (Germany, Norway).
7 categories, ~8–10 questions each, target ~65 questions.

**Design discipline (frozen before any graph or product data exists):**
- Question *structure* and per-category *predictions* are committed now (Option A).
- Ground-truth answers are instantiated after Stage 4, sourced from the AUTHORITATIVE databases
  (BVL PSM API, Mattilsynet), never from the KG or the RAG system being compared.
- Both systems (document-RAG and KG-RAG) receive identical knowledge; they differ only in representation.
- Grading is blind (condition anonymised) and each condition is run multiple times (report mean + spread).

**Prediction key:** `=` no difference expected · `KG+` KG advantage expected · `?` genuinely uncertain.
Record the prediction BEFORE running. Report where predictions were right AND wrong.

---

## Categories, predictions, and ground-truth source

| # | Category | Prediction | Why | Ground-truth source | Needs Stage 4 data? |
|---|---|---|---|---|---|
| 1 | Factual lookup | `=` | control category; single-fact, both retrieve it | existing corpus | No |
| 2 | Region-specific info | `=`/`?` | one country, one disease; tests region-correctness | corpus + authority | Partly |
| 3 | Multi-hop | `KG+` | requires traversal across relations | authority (products) | Yes |
| 4 | Constraint | `KG+` | filtered/negated attribute queries | authority (products) | Yes |
| 5 | Negative / absence | `KG+` | KG answers "no" definitively; RAG can only fail to find | authority (products) | Yes |
| 6 | Cross-border divergence | `KG+` | THE novel category — same disease, different authorised treatment by country | both authorities | Yes |
| 7 | Hierarchy-traversal | `KG+` | authorisation recorded at parent crop level, asked at child level | BVL crop taxonomy | Yes |

Category 1 is the bias check: if the KG "wins" here, the setup is flawed.

---

## Question templates by category

Placeholders: `{disease}` ∈ {late blight, apple scab, powdery mildew}; `{country}` ∈ {Germany, Norway};
`{crop}`, `{pathogen_type}`, `{product}`, `{active_substance}`, `{parent_crop}`, `{child_crop}`.

### 1 — Factual lookup  (control, `=`)
- What pathogen causes {disease}?
- What type of pathogen is responsible for {disease} (fungus / oomycete / bacterium)?
- Which crops does {disease} affect?
- What is the EPPO code for the pathogen causing {disease}?
- Describe the typical symptoms of {disease}.
_Ground truth: existing corpus. Answers identical across jurisdictions._

### 2 — Region-specific info  (`=`/`?`)
- Which national authority regulates plant-protection products in {country}?
- For {disease} in {country}, what management practices are recommended?
- Is {disease} economically significant in {country}?
- Where should a grower in {country} check which products are authorised?
_Ground truth: corpus + authority identity (BVL / Mattilsynet). No product records needed for most._

### 3 — Multi-hop  (`KG+`)
- Which authorised products in {country} act against the pathogen type that causes {disease}?
  (disease → pathogen_type → products)
- {disease} and {other_disease} share a pathogen type — which authorised products in {country} treat both?
- What active substances are used in {country}-authorised products against {disease}?
  (disease → products → active_substances)
- Which crops can be treated for {disease} using products authorised in {country}?
_Ground truth: authority product records + relations. REQUIRES Stage 4._

### 4 — Constraint  (`KG+`)
- What products authorised in {country} for {disease} are NOT of product-type fungicide?
- Which {country}-authorised products for {disease} on {crop} contain active substance {active_substance}?
- List {country}-authorised products for {disease} approved after {date} / still valid today.
- Which authorised products treat {disease} on {crop} but exclude {excluded_active_substance}?
_Ground truth: filtered authority records. REQUIRES Stage 4._

### 5 — Negative / absence  (`KG+`, sharpest)
- Is {product} authorised for {disease} on {crop} in {country}?  (where it is NOT)
- Is active substance {active_substance} permitted in {country} for {disease}?  (where it is NOT)
- Can a product authorised in Germany for {disease} be used in Norway?  (correct answer: not without separate NO authorisation)
- Are there any authorised products for {disease} on {crop} in {country}?  (where none exist)
_Ground truth: verified ABSENCE from the authority list. REQUIRES Stage 4. A "not found" is a real answer here._

### 6 — Cross-border divergence  (`KG+`, novel/headline)
- For {disease}, how do the authorised products differ between Germany and Norway?
- Is {product}, authorised for {disease} in Germany, also authorised in Norway?
- Which active substances are authorised against {disease} in Germany but NOT in Norway (or vice versa)?
- A grower moves a {crop} operation from Germany to Norway — what changes about {disease} treatment authorisation?
_Ground truth: BOTH authority lists, compared. REQUIRES Stage 4 for both countries. This category = the contribution._

### 7 — Hierarchy-traversal  (`KG+`)
- Is {product} authorised for {child_crop} when its authorisation is registered at the {parent_crop} level? (Germany/BVL taxonomy)
- Which products authorised at the {parent_crop} level apply to {child_crop} for {disease}?
- Does an authorisation for {parent_crop} against {disease} cover {child_crop}?
_Ground truth: BVL crop taxonomy + product records. REQUIRES Stage 4 (BVL hierarchy)._

---

## What this hands Stage 4 (the precise data shopping list)

To instantiate ground truth, Stage 4 must collect, for each of the 3 diseases in BOTH countries:
- authorised **products** (name, MA/registration number, product type, validity dates);
- each product's **active substance(s)**;
- the **crop(s) / uses** each product is authorised for;
- the **pathogen / target** each addresses (to link disease → product);
- for Germany: the **crop hierarchy** (parent→child) as recorded by BVL;
- confirmed **absences** (for negative queries — a product/substance verified NOT on the list).

Coverage is matched across countries deliberately (same diseases, comparable depth), not driven by
whichever database is easier to query.

---

## Metrics (per question; mirrors Stage-1 literature conventions)

- **Region correctness** — right jurisdiction's authority/products cited.
- **Recommendation correctness** — answer matches authoritative ground truth.
- **Faithfulness** — claims traceable to provided evidence (no fabrication).
- **Negative-query handling** — correctly says "no / not authorised" vs guessing or failing silently.
- **Relationship reasoning** — multi-hop / constraint / hierarchy answered correctly.
- **Response completeness** — all parts of a multi-part answer covered (define per-question rubric before grading).

Grading: blind to condition; multiple runs; report mean and observed variation.