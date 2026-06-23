# Bornholm Next-Day Handoff

Date for follow-up: 2026-06-24

## Current Status

Bornholm has been moved from the old Prekvart-derived landmask to the DAGI Landsdel landmask for the active app extent and acceptance/source assets.

The app is running locally at:

- `http://localhost:8501`

The active Bornholm acceptance registry is:

- `apps/acceptance_model/registry_bornholm.json`

The active Bornholm acceptance asset package is:

- `docs/geocontext/acceptance_framework/data/prototype_assets_dagi_landsdel/`

This package now includes:

- source GeoJSON
- distance tables
- landmask RDS
- per-layer analysis RDS

## QGIS Review First Thing

Open:

- `exports/qgis_review/bornholm_dagi_acceptance_coastal_qa/qgis_review_index.csv`

Review especially:

- `strand_protection_raw_source_wgs84.geojson`
- `strand_protection_exact_dagi_clip_wgs84.geojson`
- `strand_protection_new_dagi_clip_display.geojson`
- `coastal_zone_3km_exact_dagi_clip_wgs84.geojson`
- `coastal_zone_3km_new_dagi_clip_display.geojson`
- `bornholm_dagi_landsdel_landmask_wgs84.geojson`

Main QA question:

- Do `strand_protection` and `coastal_zone_3km` now behave acceptably against the DAGI Landsdel landmask and XYZ/satellite basemaps?

## Known Numbers

Active Bornholm R9 app hexes:

- 6852

Distance-table rows:

- `strand_protection`: 6852
- `coastal_zone_3km`: 6852

Old vs new coastal comparison over the active app hexes:

| Layer | Changed intersections | New intersecting hexes |
| --- | ---: | ---: |
| `strand_protection` | 4 | 664 |
| `coastal_zone_3km` | 15 | 3486 |

## Validation Already Done

- Region contract: 71 checks, 0 blockers.
- 26 DAGI analysis RDS files read successfully.
- 0 RDS files with missing CRS.
- `roads_small` remains the only empty layer after filtering, as expected.

## Recommended Next Move

If the QGIS coastal review looks good, commit/keep this as the Bornholm R9 DAGI acceptance baseline. Then move to the visible Bornholm `strandskydd` issue in the app by comparing:

- the map source overlay,
- the dynamic coastal filter result,
- and the wind/solar suitability impact.

If anything looks wrong in QGIS, do not tune scores first. Fix the source/mask clipping before changing acceptance parameters.
