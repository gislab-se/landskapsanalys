# GC4 RUNBOOK

## Short Answer

Latest verified GC4 run found locally:

- workspace: `C:\gislab\speedlocal_bornholm`
- notebook execution: `2026-02-20`
- exported context and factor CSVs: `2026-02-20 13:47`
- rendered report snapshot: `2026-02-20 15:22`

The app in `speedlocal` consumes the same exported outputs, but the original working run appears to have been carried out in `speedlocal_bornholm`.

## Core Artifacts

Notebook and exported files:

- `C:\gislab\speedlocal_bornholm\jyp_note_book_geocontext\bornholm.ipynb`
- `C:\gislab\speedlocal_bornholm\jyp_note_book_geocontext\bornholm.executed.ipynb`
- `C:\gislab\speedlocal_bornholm\jyp_note_book_geocontext\bornholm_points_with_context_gc4.csv`
- `C:\gislab\speedlocal_bornholm\jyp_note_book_geocontext\bornholm_r8_factor_scores_gc4.csv`
- `C:\gislab\speedlocal_bornholm\jyp_note_book_geocontext\bornholm_r8_factor_loadings_gc4.csv`

Rendered review pages:

- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_report.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_index.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_F1.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_F2.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_F3.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_F4.html`
- `C:\gislab\speedlocal_bornholm\docs\geocontext\bornholm_gc4_F5.html`

Consumer copies also exist in:

- `C:\gislab\speedlocal\jyp_note_book_geocontext\`
- `C:\gislab\landskapsanalys\data\gc4\`

## The Four Core Input Layers

The shipped GC4 export reflects four raw indicators:

1. `fastboendebefolkningmapinfo`
2. `roads_simplified_gd_v_vej_road_merged_bol_33`
3. `ecology_connectivity_pdk_oekologiskforbindelse_bor_32`
4. `cultural_and_historical_conservation_values_kulturhistoriske_bevaringsvardier_pdk_kulturhistoriskebevaringsvardier_bor_32`

Short names used in the exported GC4 context table:

- `gc_fastboendebefolkningmapinfo_cnt_00ea14`
- `gc_roads_simplified_gd_v_vej_road_merged__len_0231cb`
- `gc_ecology_connectivity_pdk_oekologiskfor_shr_032534`
- `gc_cultural_and_historical_conservation_v_shr_034ee6`

## Important Clarification

The legacy GC4 files do not contain only four columns. They contain four raw indicators expanded into contextual variables across several neighbourhood sizes.

The notebook builds `mean_` and `std_` context variables for each indicator at:

- `k = 10`
- `k = 50`
- `k = 100`
- `k = 250`
- `k = 1000`

That gives `4 indicators x 2 summary stats x 5 k-values = 40 contextual feature columns`.

## Pipeline Chain

### Step 1: Build geocontext base features in PostGIS

Referenced workflow:

- `C:\gislab\speedlocal_bornholm\START_TOMORROW.md`

Relevant scripts:

- `C:\gislab\databas\script\04_build_bornholm_r8_geocontext_from_selection.R`
- `C:\gislab\speedlocal_bornholm\script\05_finalize_bornholm_r8_geocontext_features.R`
- `C:\gislab\speedlocal_bornholm\script\07_create_bornholm_r8_qgis_views.R`

Outputs include:

- `h3.bornholm_r8_geocontext_features`
- `h3.bornholm_r8_geocontext_zscores`
- QGIS views for those tables

### Step 2: Notebook reads base features

The notebook reads selected columns from:

- `h3.bornholm_r8_geocontext_features`

It also joins geometry-centroid coordinates from:

- `h3.bornholm_r8`

### Step 3: Notebook generates contextual variables

Notebook function call:

- `pointsWithContext = geocontext(...)`

Inputs are the four raw indicators and the configured `k` values.

### Step 4: Notebook performs factor analysis

The notebook:

- standardizes the contextual matrix
- removes empty or degenerate columns
- runs `FactorAnalyzer`
- uses `n_factors = 5`
- uses `varimax` rotation

Outputs:

- factor scores `F1..F5`
- factor loadings table

### Step 5: Notebook clusters hexagons on factor scores

The notebook:

- collects `F1..F5`
- tests `K = 5..10`
- ranks candidates by silhouette score
- chooses `K_BEST = 8`
- writes cluster labels to `class_km`

### Step 6: Notebook writes factors back to PostGIS and CSV

Database table refreshed by the notebook:

- `h3.bornholm_r8_factors_gc4`

CSV outputs written from notebook working directory:

- `bornholm_r8_factor_loadings_gc4.csv`
- `bornholm_r8_factor_scores_gc4.csv`
- `bornholm_points_with_context_gc4.csv`

### Step 7: Report rendering

Report script:

- `C:\gislab\speedlocal_bornholm\script\09_render_bornholm_gc4_reports.ps1`

Rendered pages:

- factor pages `F1..F5`
- main snapshot report
- index page

## What Is Not The GC4 Factor Pipeline

This script is not the notebook-based GC4 factor analysis:

- `C:\gislab\speedlocal_bornholm\script\06_build_bornholm_r8_geocontext_score.R`

That script builds a weighted composite score table from configured feature weights. It is useful, but it is a different method than the notebook's factor-analysis workflow.

## Related Audit In This Repo

A later audit of the shipped 4-indicator GC4 export exists here:

- `C:\gislab\landskapsanalys\docs\geocontext\GEOCONTEXT_AGGREGATION_AUDIT_2026-03-04.md`

That audit confirms that the shipped GC4 context export reflects four indicators, not the first four layers in the broader 37-layer configuration.
