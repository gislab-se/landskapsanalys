# GC4 TO R9 FACTOR MIGRATION

## Current Situation

Legacy GC4 used four raw layers, transformed into contextual variables, then into five factors and eight clusters.

Current R9 work in `landskapsanalys` now has a much broader layer universe:

- 44 configured layers in `script/semi_manual_r9/config/bornholm_r9_geocontext_layers.csv`
- 40 visible parent steps in the current review report
- child layers already introduced under parent layers for selected themes such as roads, rivers, and nature types

This is enough to rebuild geocontext for R9, but it is not a good idea to throw all parent and child variables into the first factor model without a selection policy.

## Legacy Four-Layer Continuity

The four legacy GC4 themes are already represented in the R9 configuration:

1. `fastboendebefolkningmapinfo`
2. `roads_simplified_gd_v_vej_road_merged_bol_33`
3. `ecology_connectivity_pdk_oekologiskforbindelse_bor_32`
4. `cultural_and_historical_conservation_values_kulturhistoriske_bevaringsvardier_pdk_kulturhistoriskebevaringsvardier_bor_32`

That gives us a strong migration path:

- first reproduce a legacy-like GC4 run on the new R9 workflow
- then expand carefully to a richer model

## Recommended Migration Strategy

### Phase 1: Legacy-Compatible R9 Check

Build an R9 geocontext run using only the four legacy GC4 themes.

Goal:

- verify the new engine and reporting chain
- confirm that factor scores and clusters behave sensibly on the new workflow
- create a bridge from the historical GC4 work to the new pipeline

### Phase 2: Curated R9 v1 Factor Universe

Do not jump straight from 4 layers to every available parent and child layer.

Instead, create a curated first factor-analysis universe of roughly 15 to 25 features that represent distinct themes with low-to-moderate redundancy.

Suggested theme groups:

- settlement and access
- blue-green structure
- protected landscapes and nature
- cultural landscape
- energy infrastructure
- topography
- agriculture

### Phase 3: Expanded R9 Model

After a stable v1 model exists, test a broader model that includes more layers, additional splits, or alternative transforms.

## Most Important Rule For Parent/Child Layers

For factor analysis, do not include both the parent total and all of its child splits in the same model by default.

Why:

- the child layers often sum to, or strongly approximate, the parent
- that creates structural collinearity
- factor solutions become harder to interpret
- the model starts rewarding bookkeeping rather than real variation

Recommended policy:

- keep both parent and child layers in the QA/reporting system
- but define one explicit `analysis_role` for factor analysis

Suggested `analysis_role` values:

- `parent_only`
- `children_only`
- `exclude_from_factor`
- `candidate_experiment`

Examples:

- roads: likely `children_only` or a carefully reduced set of child groups
- river: likely `children_only` for width classes if those prove more informative
- BES naturtyper: likely `children_only` for selected subtype shares
- broad protected-area layers: often `parent_only`

## Recommended Data Rules Before Factor Analysis

### 1. Keep aggregation QA strict

Before factor modeling, the R9 pipeline should enforce:

- geometry-type validation
- explicit aggregation type handling
- polygon-share caps or QC for values above `1.0`
- a run manifest of selected layers and outputs

### 2. Use metric-aware transforms

A practical first-pass policy is:

- counts: `log1p`
- lengths: `asinh` or `log1p` after zero handling
- shares: keep as bounded proportions, optionally winsorized
- relief / elevation metrics: start with no transform, then inspect tails

### 3. Remove degenerate columns

As in the old notebook, remove:

- all-NA columns
- zero-variance columns
- duplicated or near-duplicated columns

## Candidate R9 v1 Themes

A good first curated factor model might include variables from these groups:

### Settlement and Access

- fastboende population
- roads, simplified or road child groups
- built centre
- built low / buildings low

### Blue-Green Structure

- river or river width classes
- lake
- wetland
- moor / hede
- forest
- ecology connectivity

### Protected and Cultural Landscape

- valuable cultural environment
- cultural and historical conservation values
- landscapes worthy of preservation
- one or two major Natura / protected-area layers

### Special Case: `landscapes_worthy_of_preservation`

Treat `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32` as a special candidate in the first R9 factor-analysis work.

Reason:

- the source layer already looks like a landscape-character interpretation
- it is close to the kind of synthetic landscape reading we ultimately want to produce
- if included naively, it may either improve the cultural-landscape signal or partially pre-encode the answer we are trying to derive from the data

Recommended handling in the first serious R9 analysis:

- keep it as a single parent layer, not a split layer
- test the full landscape-analysis workflow in two variants:
  - without this layer
  - with this layer
- compare factor loadings, factor stability, and cluster geography between the two runs

The practical question is not only whether the layer is predictive, but whether it helps the model surface richer cultural-geographic structure instead of simply reinforcing an already interpreted planning layer.

### Topography and Land Use

- contour-based relief
- highest contour value per hex
- markblokke share

### Energy Infrastructure

Use sparingly in the first factor model unless the analytical goal is explicitly energy-landscape coupling.

Candidates include:

- substations
- high-voltage lines
- underground cable
- wind
- solar
- biogas

## Recommended First Implementation Order

1. Freeze an `R9_factor_v1` feature list.
2. Tag each parent/child variable with an `analysis_role`.
3. Mark `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32` as a special `with/without` test variable.
4. Build an R9 feature matrix from the selected parent or child variables only.
5. Run geocontext context generation at the legacy `k` values: `10, 50, 100, 250, 1000`.
6. Build at least two candidate factor models, e.g. `4`, `5`, and `6` factors.
7. For the preferred model, run two variants:
   - without `landscapes_worthy_of_preservation`
   - with `landscapes_worthy_of_preservation`
8. Compare interpretability, loading stability, and cluster coherence.
9. Cluster on factor scores and test a reasonable `K` range, e.g. `5..10`.
10. Add the factor outputs to the review report and app.

## Suggested Deliverables For The Next Step

### `R9_factor_v1_feature_roles.csv`

A new config file that states, for each selected feature:

- `include`
- `feature_name`
- `source_layer`
- `analysis_role`
- `metric_type`
- `transform`
- `notes`

### `R9_factor_v1_run_manifest.json`

A machine-readable record of what exactly went into the run.

### `R9_factor_v1_report.html`

A dedicated review artifact for:

- selected features
- transforms
- factor loadings
- cluster profiles
- comparison against legacy GC4

## Bottom-Line Recommendation

Yes, the project is ready to start rebuilding geocontext for R9.

But the first serious R9 factor run should be:

- curated, not maximal
- explicit about parent vs child policy
- reproducible from config
- compared against the legacy four-layer GC4 baseline





