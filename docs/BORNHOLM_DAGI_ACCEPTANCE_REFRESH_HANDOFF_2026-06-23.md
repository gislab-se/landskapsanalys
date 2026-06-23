# Bornholm DAGI Acceptance Refresh Handoff

Date: 2026-06-23

## Status

Bornholm acceptance/source assets have been rebuilt against the DAGI Landsdel landmask after the old Prekvart-derived landmask was found to align poorly with XYZ/satellite basemaps and contain internal residual lines.

The app now selects `apps/acceptance_model/registry_bornholm.json` for Bornholm. Trondelag remains on `apps/acceptance_model/registry_trondelag.json`.

## Active Files

- Registry: `apps/acceptance_model/registry_bornholm.json`
- Resolved source config: `script/acceptance/generated/bornholm_r9_geocontext_layers_dagi_landsdel.csv`
- Asset directory: `docs/geocontext/acceptance_framework/data/prototype_assets_dagi_landsdel/`
- QGIS QA package: `exports/qgis_review/bornholm_dagi_acceptance_coastal_qa/`

## Source And Mask

- Landmask source: `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Bornholm_SL01/Basmap_BOR/DAGI_Landsdel_Scale10000_BOL_33.shp`
- Working CRS: `EPSG:25833`
- App distance-table hex universe: `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_dagi_landsdel_app.geojson`
- Active hex count: 6852

## Export Result

`scripts/export_bornholm_dagi_acceptance_assets.py` rebuilt:

- `source_geojson/*.geojson`
- `distance_tables/*.csv`
- `asset_manifest.csv`

`script/acceptance/export_bornholm_dagi_analysis_rds.R` then rebuilt:

- `analysis_rds/*.rds`
- `analysis_rds_export_report.csv`
- `asset_manifest.csv` RDS path/base-buffer columns

Manifest summary:

- `ok`: 26 layers
- `empty_after_filter`: 1 layer (`roads_small`, same practical behavior as before)
- `analysis_rds_path`: populated for all 26 `ok` layers
- `strand_protection` distance rows: 6852
- `coastal_zone_3km` distance rows: 6852

## Coastal QA Summary

`scripts/build_bornholm_dagi_acceptance_coastal_qa.py` produced exact and display QA layers for:

- `strand_protection`
- `coastal_zone_3km`

Old vs new distance/intersection comparison over the active 6852 app hexes:

| Layer | Old intersecting hexes | New intersecting hexes | Changed intersections | Old zero-distance hexes | New zero-distance hexes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `strand_protection` | 660 | 664 | 4 | 257 | 412 |
| `coastal_zone_3km` | 3471 | 3486 | 15 | 3091 | 3342 |

## Remaining Risk

The refreshed package now has the same asset classes expected by the app: source GeoJSON, distance tables, landmask RDS, and per-layer analysis RDS. The main remaining risk is semantic QA, not missing runtime assets: review the coastal QA package in QGIS and confirm that the DAGI-clipped `strand_protection` and `coastal_zone_3km` behavior is acceptable before treating the package as final.

The RDS export keeps `population_points` as a dissolved 100 m buffer with `analysis_base_buffer_m = 100`, matching the earlier Bornholm prototype behavior. All other non-empty layers use `analysis_base_buffer_m = 0`.
