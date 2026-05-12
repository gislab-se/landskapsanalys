# Trondelag Potential App Minimal Package - potential_app_minimal_2026-05-12

## Status

This package is a first stable data handoff for activating Trondelag in the Potential App. It is suitable for map/H3 display QA, but it is not a final landscape analysis.

## Created Files

- R6: `outputs/trondelag/potential_app_minimal_2026-05-12/h3/trondelag_h3_r6_land_clipped.geojson` (1822 clipped geometries)
- R7: `outputs/trondelag/potential_app_minimal_2026-05-12/h3/trondelag_h3_r7_land_clipped.geojson` (12777 clipped geometries)
- R8: `outputs/trondelag/potential_app_minimal_2026-05-12/h3/trondelag_h3_r8_land_clipped.geojson` (89312 clipped geometries)
- R9: `outputs/trondelag/potential_app_minimal_2026-05-12/h3/trondelag_h3_r9_land_clipped.geojson` (625387 land-selected full H3 geometries)
- Mask GPKG EPSG:25832: `outputs/trondelag/potential_app_minimal_2026-05-12/mask/trondelag_land_region_mask_25832.gpkg`
- Mask GeoJSON EPSG:4326: `outputs/trondelag/potential_app_minimal_2026-05-12/mask/trondelag_land_region_mask_wgs84.geojson`
- Preliminary R8 landscape GeoJSON: `outputs/trondelag/potential_app_minimal_2026-05-12/landscape/trondelag_landscape_h3_r8.geojson`
- Cluster profile: `outputs/trondelag/potential_app_minimal_2026-05-12/landscape/trondelag_cluster_profile.csv`
- Cluster sizes: `outputs/trondelag/potential_app_minimal_2026-05-12/landscape/trondelag_cluster_sizes.csv`
- Run summary: `outputs/trondelag/potential_app_minimal_2026-05-12/landscape/trondelag_run_summary.csv`

## CRS

- Native processing CRS: EPSG:25832.
- Boundary source CRS: EPSG:25833, transformed to EPSG:25832.
- App GeoJSON CRS: EPSG:4326 / OGC CRS84 coordinates.

## Data Sources

- Boundary: `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 33/ADM_FY_TRL_33.gpkg`
- Land/non-sea mask: `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/N500_AD_Merged_TRL_32.gpkg`
- Landscape attributes: `C:/gislab/regional-landscape-pipeline/outputs/trondelag/landscape_first_pass_res7_no_energy_grouped_cover_2026-04-28/landscape/map/trondelag_landscape_first_pass_res7_map.geojson`

No new official data was downloaded for this package. Provider/license fields in `projects/trondelag/config/source_registry.csv` still include several `TBD verify` notes and need cleanup before publication.

## Column Status

- `hex_id`, geometry and `display_area_m2`: real R8 H3 display geometry clipped to the preliminary non-sea mask.
- H3 display files through R8 are geometrically clipped to the mask. Higher resolutions are land-selected by H3 cell membership and written with full H3 polygon geometry to keep the app handoff tractable.
- `class_km`, `landscape_type`, `landscape_type_id`, `F1`-`F5`: inherited from the existing R7 first-pass model by parent H3 cell.
- Rows with `value_status = placeholder_no_matching_r7_model` have no matching R7 model value and use neutral placeholders (`class_km = 0`, `F1`-`F5 = 0`).

## Gaps

- The mask is a pragmatic N500 non-sea region surface, not a final maintained coastline/land polygon.
- The R8 landscape layer is not recomputed at R8; it inherits R7 first-pass factors and clusters.
- Surficial geology/jordart and final interpreted landscape types are still missing.
- Source licenses/provenance should be verified before external publication.
