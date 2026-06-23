# Bornholm R9 Runtime QA Handoff - 2026-06-23

## Status

Trondelag LABLAB landscape default was committed in `66c3f7b`.

Bornholm app behavior has not been changed in this step. This handoff records the first R9 runtime QA package for QGIS review before changing strandskydd/coastal behavior or promoting a stricter Bornholm runtime contract.

QA builder:

- `scripts/build_bornholm_r9_runtime_qa_package.py`

QGIS package:

- `exports/qgis_review/bornholm_r9_runtime_qa/README.md`
- `exports/qgis_review/bornholm_r9_runtime_qa/qgis_review_index.csv`
- `exports/qgis_review/bornholm_r9_runtime_qa/runtime_contract_summary.json`

## Inputs

Active Bornholm region manifest:

- `regions/bornholm/region.json`

Core R9 runtime inputs:

- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_9_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_app.geojson`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.csv`
- `exports/v2_multiregion/bornholm/bornholm_establishment_placement_score_r9.csv`
- `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9.csv`

Coastal/strandskydd review inputs:

- `docs/geocontext/acceptance_framework/data/prototype_assets/source_geojson/strand_protection.geojson`
- `docs/geocontext/acceptance_framework/data/prototype_assets/source_geojson/coastal_zone_3km.geojson`

## Findings

R9 ID coverage:

- Display cells: 6855
- Landscape app GeoJSON cells: 6853
- Landscape CSV rows: 6877
- Establishment score rows: 6878
- Social acceptance rows: 6878

Display gaps:

- `891f2a63347ffff` is in the display geometry and has score/social rows, but no landscape app or landscape CSV row.
- `891f2a741cfffff` is in the display geometry, but has no landscape, score, or social rows. Its display area is about 5.9 m2.

Source rows outside display:

- 24 R9 rows exist in landscape CSV, score CSV, and social CSV outside the active clipped display geometry.
- These are source/runtime alignment artifacts, not automatically app candidates under the current display-clipped contract.

Rollup behavior:

- At R8, score/social cover all display parents but add 12 extra source parents.
- At R8, landscape app/CSV miss one display parent and add extra source parents.
- At R7/R6, source rollups add extra parents but do not miss display parents.

## QGIS Review

Use the package index as the load checklist:

- `exports/qgis_review/bornholm_r9_runtime_qa/qgis_review_index.csv`

Recommended order:

1. Load the active R9 display geometry.
2. Load the current LABLAB R9 landscape app layer.
3. Overlay `bornholm_r9_display_without_landscape_app.geojson`.
4. Overlay `bornholm_r9_display_without_score_social.geojson`.
5. Overlay `bornholm_r9_any_source_rows_without_display.geojson`.
6. Add `strand_protection.geojson`.
7. Add `coastal_zone_3km.geojson`.

Check whether the display gaps and outside-display source rows are shore slivers, offshore trim artifacts, or a true CRS/source geometry issue. The known v1 Bornholm strandskydd issue should be evaluated against these layers before changing hard-stop logic.

## Recommendation

Keep the current display-clipped app extent for Bornholm while reviewing the strandskydd issue.

Do not add the 24 outside-display source rows to the app just to make CSV counts line up. If QGIS confirms they are outside the app display contract, treat them as provenance/source rows and keep them out of candidate rendering.

After QGIS review, promote a Bornholm-specific runtime contract:

- app candidate geometry is the active land-clipped display set;
- landscape, score, and social tables are joined to that display set;
- missing tiny slivers are either explicitly dropped or shown as no-data, with counts documented;
- strandskydd/coastal hard-stop behavior is fixed only if the source layer, distance table, or runtime filter semantics are proven to be wrong.
