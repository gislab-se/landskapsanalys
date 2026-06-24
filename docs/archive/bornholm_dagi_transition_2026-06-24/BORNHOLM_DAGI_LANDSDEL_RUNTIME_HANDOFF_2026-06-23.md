# Bornholm DAGI Landsdel Runtime Handoff - 2026-06-23

## Decision

Use `DAGI_Landsdel_Scale10000_BOL_33.shp` as the selected Bornholm app landmask candidate.

Reason:

- The previous Prekvart-derived mask aligned poorly against satellite/XYZ tiles.
- The previous mask had 99 interior rings/residual line artifacts.
- DAGI Landsdel reports `EPSG:25833`, matching the Bornholm regional CRS.
- QGIS comparison showed no practical app-scale difference from the filtered DAGI municipality candidate.

## Generated Runtime Package

Builder:

- `scripts/build_bornholm_dagi_landsdel_runtime_package.py`

Selected landmask:

- `exports/v2_multiregion/bornholm/landmask/bornholm_dagi_landsdel_landmask_wgs84.geojson`
- `exports/v2_multiregion/bornholm/landmask/bornholm_dagi_landsdel_landmask_outline_wgs84.geojson`

Active display geometries:

- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_6_dagi_landsdel_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_7_dagi_landsdel_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_8_dagi_landsdel_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_9_dagi_landsdel_land_clipped.geojson`

Active landscape app GeoJSON:

- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_dagi_landsdel_app.geojson`

Runtime summary:

- `exports/v2_multiregion/bornholm/bornholm_dagi_landsdel_runtime_summary.json`

## Counts

Display geometry counts:

- R6: 32
- R7: 166
- R8: 1035
- R9: 6852

R9 app contract:

- R9 display cells: 6852
- R9 landscape app features: 6852
- Display cells missing landscape CSV: 0
- Display cells missing score CSV: 0
- Display cells missing social CSV: 0

Source rows outside display:

- Landscape CSV rows outside display: 25
- Score CSV rows outside display: 26
- Social CSV rows outside display: 26

These source rows remain provenance/source rows outside the active candidate geometry. They should not be shown as app candidate cells.

## Updated Manifests

Updated:

- `regions/bornholm/region.json`
- `exports/v2_multiregion/bornholm/bornholm_region_v2_manifest.json`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.json`
- `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9_manifest.json`
- `exports/v2_multiregion/bornholm/build_summary.json`

## QA

QA builder:

- `scripts/build_bornholm_r9_runtime_qa_package.py`

QA package:

- `exports/qgis_review/bornholm_r9_runtime_qa/runtime_contract_summary.json`
- `exports/qgis_review/bornholm_r9_runtime_qa/qgis_review_index.csv`

QA result after DAGI Landsdel:

- Display without landscape app: 0
- Display without score/social: 0
- Any source rows outside display: 26

## Remaining Work

The acceptance/source GeoJSON folder is still from the older export flow unless explicitly rebuilt. Those layers were clipped to the old landmask before export, and their distance tables were computed from those clipped geometries.

Next controlled rebuild:

1. Update the acceptance export flow to use the DAGI Landsdel landmask.
2. Point raw source paths to the available `D:/LABLAB_Energiforsk/...` source tree.
3. Re-export source GeoJSON, analysis RDS, and distance tables.
4. Rebuild establishment placement score if distance-table inputs change.
5. Re-run Bornholm QA, with special attention to `strand_protection`.

This refresh made the app display/landscape contract consistent. It does not yet prove that the Bornholm strandskydd distance behavior is fixed.
