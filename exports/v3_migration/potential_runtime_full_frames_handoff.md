# V2 -> V3 Handoff: Full Potential Establishment Runtime Frames

Date: 2026-06-10

Scope: full region runtime data for `Potentiell etableringsyta`, built from V2 wind/solar ground potential. Scenario allocation and outside-LP are intentionally omitted.

## 1. Where The Full Frames Are

The full V2 runtime export is now materialized under:

- `exports/v3_migration/potential_runtime_full_frames/index.json`
- `exports/v3_migration/potential_runtime_full_frames/bornholm/`
- `exports/v3_migration/potential_runtime_full_frames/trondelag/`

Bornholm files:

- `wind_potential_source_r10.csv` - full V2 wind source/analysis frame, 47,117 rows.
- `solar_potential_source_r10.csv` - full V2 solar source/analysis frame, 47,117 rows.
- `wind_technology_potential_frame_r8.csv` - V3-ready wind frame at display R8, 1,041 rows.
- `solar_technology_potential_frame_r8.csv` - V3-ready solar frame at display R8, 1,041 rows.
- `potential_establishment_frame_r8.csv` - combined establishment frame, 1,029 rows.
- `potential_establishment_area_r8.geojson` - ready display FeatureCollection, 1,029 features.

Trondelag files:

- `wind_potential_source_r7.csv` - full V2 wind source/display frame, 13,735 rows.
- `solar_potential_source_r7.csv` - full V2 solar source/display frame, 13,735 rows.
- `wind_technology_potential_frame_r7.csv` - V3-ready wind frame at display R7, 13,735 rows.
- `solar_technology_potential_frame_r7.csv` - V3-ready solar frame at display R7, 13,735 rows.
- `potential_establishment_frame_r7.csv` - combined establishment frame, 13,735 rows.
- `potential_establishment_area_r7.geojson` - ready display FeatureCollection, 13,735 features.

## 2. What Builds Them

The export script is:

- `scripts/export_potential_establishment_runtime_frames.py`

Core V2 runtime functions in `potential_app.py`:

- `5813` `_solar_large_scale_frame(...)`
- `5969` `_combined_solar_hex_frame(...)`
- `8989` `_wind_fast_distance_runtime_result(...)`
- `9075` `_wind_runtime_hex_layer_frame(...)`
- `9346` `_potential_establishment_source_frame(...)`
- `9676` `_combined_potential_establishment_frame(...)`
- `10486` `_combined_establishment_feature_collection(...)`
- `10652` `_combined_potential_establishment_family_layers(...)`
- `10831` `_wind_polygon_preview_state(...)`
- `10998` `_wind_polygon_summary_frame(...)`

Important behavior: `suitable` is derived from positive potential area, not from scenario allocation. Allocation/outside-LP columns are zero/false in this export by design.

## 3. Recommended Display H3

Bornholm:

- Source/analysis: R10.
- Recommended V3 web display: R8.
- Reason: R10 is correct as analysis basis but too small/dense for an immediately visible web layer. R8 gives 1,029 visible features and keeps the map lightweight.
- R7/R6 can be added later as overview rollups, but R8 should be the first real display layer.

Trondelag:

- Source/display: R7.
- Recommended V3 web display: R7.
- Allowed app resolutions: R7/R6/R5 only.
- Do not expose R8/R9 for Trondelag.

## 4. Ready GeoJSON

V2 did not previously keep this full layer as a static exported file. The app built it in memory via `_combined_establishment_feature_collection(...)`.

This handoff now exports ready FeatureCollections:

- Bornholm: `exports/v3_migration/potential_runtime_full_frames/bornholm/potential_establishment_area_r8.geojson`
- Trondelag: `exports/v3_migration/potential_runtime_full_frames/trondelag/potential_establishment_area_r7.geojson`

V3 can consume these directly for the first full runtime layer.

## 5. Join Path If V3 Builds The Layer

Join key: `hex_id`.

Bornholm:

- Potential frames:
  - `exports/v3_migration/potential_runtime_full_frames/bornholm/wind_technology_potential_frame_r8.csv`
  - `exports/v3_migration/potential_runtime_full_frames/bornholm/solar_technology_potential_frame_r8.csv`
  - or combined `potential_establishment_frame_r8.csv`
- Display geometry:
  - `docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_h3_res_8_land_clipped.geojson`

Trondelag:

- Potential frames:
  - `exports/v3_migration/potential_runtime_full_frames/trondelag/wind_technology_potential_frame_r7.csv`
  - `exports/v3_migration/potential_runtime_full_frames/trondelag/solar_technology_potential_frame_r7.csv`
  - or combined `potential_establishment_frame_r7.csv`
- Display geometry:
  - `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson`

If V3 wants only the map layer, use the ready GeoJSON. If V3 wants the normalized runtime contract, import wind/solar technology frames and materialize establishment classes from them.

## 6. Data Status

- Bornholm: `ok`
- Trondelag: `proxy`
- Vara/Skaraborg: `missing`
- Scenario allocation: `hold` or `pending_analysis`
- Outside-LP: `hold` or `pending_analysis`

Do not mark scenario allocation or outside-LP as part of `Potentiell etableringsyta`. They are downstream analysis layers.

## 7. Counts And Classes

Bornholm R8 establishment layer:

- Features: 1,029
- `wind_only`: 627
- `wind_and_solar`: 326
- `solar_only`: 21
- `not_suitable`: 55

Trondelag R7 establishment layer:

- Features: 13,735
- `wind_and_solar`: 1,002
- `wind_only`: 404
- `solar_only`: 126
- `not_suitable`: 12,203

## 8. Tests V3 Should Recreate First

V2 test/validation entry points:

- `scripts/validate_potential_region_parity.py`
  - Builds Bornholm then Trondelag.
  - Verifies wind/solar potential rows are non-empty.
  - Verifies shared establishment behavior.
  - Verifies Trondelag runs in R7 light mode and R6/R5 rollups follow dominant R7 child classes.
- `scripts/validate_potential_region_contract.py`
  - Verifies Trondelag CRS `EPSG:25832`.
  - Verifies Trondelag exposes exactly R7/R6/R5.
  - Verifies stale R10 state is sanitized to R7.
  - Verifies display geometry counts and paths for Trondelag R7/R6/R5.
- `scripts/test_potential_interactions_smoke.py`
  - UI smoke coverage for interaction/state behavior around potential layers.

Recommended V3 tests:

- Load each region manifest and assert `data_status`.
- Load wind/solar technology frames and assert required columns: `hex_id`, `technology`, `suitable`, `potential_score`, `potential_area_km2`, `display_h3_resolution`, `source_h3_resolution`, `data_status`.
- Join/consume display geometry by `hex_id` and assert feature count equals manifest count.
- Assert Bornholm display resolution is R8 and source resolution is R10.
- Assert Trondelag display/source resolution is R7 and R8/R9 are rejected.
- Assert `suitable == potential_area_km2 > 0` for both technologies.
- Assert no non-zero allocation or outside-LP values are required to render `Potentiell etableringsyta`.

## 9. Commits That Explain The Behavior

Useful commits to inspect:

- `c530c02` Stabilize potential app H3 analysis
- `891d6bd` Stabilize potential app establishment UX
- `9974f7e` Wind builder: show geometry-based potential establishment area by default
- `7f8bcf2` Wind builder: add polygon-first hex share preview
- `ae9dee1` Extend solar filters and remove Markblokke base
- `2038a9f` Activate Trondelag R7 potential parity
- `b30aa9d` Fix Trondelag establishment rollup
- `8562890` Fix Trondelag zoom adaptive layers
- `cc48d7f` Refine area demand and scenario allocation
- `fbeb8c6` Suppress tiny outside-potential markers

The first eight matter for ground potential and establishment display. The last two explain why scenario allocation/outside-LP should stay separate from this V3 runtime layer.

## 10. Rebuild Command

From the V2 repo root:

```powershell
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\export_potential_establishment_runtime_frames.py
```

The script writes CSV, GeoJSON, per-region manifests, and the shared `index.json`.
