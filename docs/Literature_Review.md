# Stage 1 — findings to merge into Literature_Review.md (Sections 3, 5)
# (Claude-run searches #2 vocabularies and #3 legal/regulatory KGs. VERIFY each source before citing.)

## Section 5 — Vocabularies / ontologies to reuse (Stage 3 input)

**AGROVOC (FAO).** Multilingual agricultural thesaurus published as linked data: SKOS, dereferenceable
URIs, aligned to ~10 other agricultural KOS (exact/close match). Queryable via a Skosmos REST API and a
public SPARQL endpoint; >4.8M resources; mappings to Eurovoc, GEMET, NALT, DBpedia. Multilingual matters
here (German/Norwegian). → reuse for CROP and general agricultural-concept URIs.

**Crop Ontology (CO) + Planteome (PO/TO).** Reference plant-biology ontologies (Plant Ontology, Trait
Ontology) with crop-specific vocabularies mapped in; FAIR, public URIs, hosted on AgroPortal / OLS.
BUT these are genomics/phenomics/trait ontologies — NOT disease-treatment or regulatory. Use for crop /
plant-part identifiers only; build the disease + regulatory layer yourself.

**AgroPortal.** Hosts ~150 agricultural ontologies (incl. Agronomy Ontology, FoodOn). Check here before
minting any new identifier — reuse-first is the defensible choice.

Open Stage-3 decision: adopt external URIs directly vs. map local ids → external URIs.

## Section 3 — Prior art and the (revised, narrower, TRUE) gap

**Plant-protection regulatory KGs already exist — do NOT claim novelty for the idea itself:**
- **E-PHY / ANSES (France):** open catalogue of ~15,000 authorised/withdrawn products (MA number, trade
  name, product type, active substances, uses); the E-PHY *ontology* (Bouazzouni & Jonquet, ~2021)
  represents it. Single-jurisdiction (France). Also integrated by the C3PO crop KG (Frontiers, 2023).
- **GMRDF (Greece):** crop-pest ontology from the Greek Ministry of Rural Development DB; concepts crop,
  disease, dose, pesticide treatment, arthropod pest, as a semantic KG. Single-jurisdiction (Greece).
- **C3PO (Frontiers, 2023):** crop planning/production ontology + KG; integrates chemical-product data
  (Basagri) via E-PHY. Closest full-system prior work — read it and position against it.

**Why the gap survives (and is sharper now).** Every prior system is SINGLE-JURISDICTION (models one
country). None represents CROSS-BORDER DIVERGENCE — the same disease requiring different *authorised*
products across a regulatory boundary. The EU "dual" system explains why this matters and is underexplored:
the Commission approves ACTIVE SUBSTANCES centrally, but each Member State authorises PRODUCTS on its own
territory (Reg. (EC) 1107/2009); Norway (EEA, non-EU) diverges further. That structure is inherently a
multi-jurisdiction relation that single-country ontologies cannot express.

**Revised positioning (true, narrow, defensible):** national plant-protection KGs exist (E-PHY, GMRDF);
what is missing is (a) an explicit representation of cross-jurisdictional regulatory divergence and (b) a
benchmark for region-correct comparative queries across a boundary. NOT "first agricultural regulatory KG."

**Stage-3 schema gift.** Reuse E-PHY's validated model (Product → Active substance → Use → Crop) and the
EU active-substance-vs-product distinction rather than inventing entities. Data obtainability: DE (BVL API)
+ FR (E-PHY open data) + GR (GMRDF) show EU-side data is reachable; Norway stays manual extraction and is
the key divergence partner precisely because it is outside the EU authorisation system.

## Must-read before closing Stage 1
- E-PHY ontology paper (Bouazzouni & Jonquet) — nearest regulatory-ontology prior work.
- C3PO (Frontiers, 2023) — nearest full crop-KG-with-chemicals system.
- GMRDF crop-pest ontology paper — second single-jurisdiction precedent.
- Confirm no cross-jurisdictional-divergence KG exists (pharma / food-safety framings too) before writing the gap as settled.