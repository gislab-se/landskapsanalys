# Geocontext Aggregation Audit (2026-03-04)

## Scope
- Source pipeline copied into this repo from `C:\gislab\databas\script` to `script/upstream_databas/`.
- Reviewed aggregation logic for the first 4 layers and compared with shipped GC4 outputs in `data/gc4/`.

## Verdict
- The **core aggregation logic is correct in principle**:
  - points -> count per hex
  - lines -> intersected length per hex (meters)
  - polygons -> intersected area share per hex
- The statement "first four layers are analyzed" is **not consistent with the shipped GC4 export** in this repo.

## Evidence
- Aggregation entry point: `script/upstream_databas/04_build_bornholm_r8_geocontext_from_selection.R`
- Core function: `script/upstream_databas/lib/geocontext_qgis_layers.R` (`aggregate_layer_to_hex`)
- First four configured layers:
  - `fastboendebefolkningmapinfo` (point/count)
  - `industry_business...` (polygon/share)
  - `built_low...` (polygon/share)
  - `built_centre...` (polygon/share)
- Shipped GC4 context file currently contains only 4 indicators, but they are:
  - `gc_fastboendebefolkningmapinfo_cnt_00ea14`
  - `gc_roads_simplified_gd_v_vej_road_merged__len_0231cb`
  - `gc_ecology_connectivity_pdk_oekologiskfor_shr_032534`
  - `gc_cultural_and_historical_conservation_v_shr_034ee6`

## Findings (ordered by severity)

### 1) High: `aggregation_type` is collected but not used
- Selection CSV has `aggregation_type`, but `aggregate_layer_to_hex` does not branch on it.
- Current behavior is purely geometry-driven.
- Risk: manual intent in selection config can be silently ignored.

### 2) High: Polygon `area_share` can exceed 1.0
- For polygons, intersected areas are summed; overlapping polygons can produce `area_m2 > hex_area_m2`.
- Current code does not cap to `[0, 1]`.
- Risk: "share" semantics break and downstream scoring may be biased.

### 3) Medium: Mixed geometry layers are handled by first match priority
- Logic checks `is_point` first, then line, then polygon.
- If a layer contains mixed geometries, it may be aggregated as point-count only.
- Risk: wrong metric for mixed/dirty layers.

### 4) Medium: Export/provenance mismatch in this repo
- This repo includes full 37-layer config files, but shipped `data/gc4/bornholm_points_with_context_gc4.csv` only reflects 4 context indicators.
- Risk: users infer wrong progress/status and may tune weights against unavailable features.

### 5) Low: Limited automated tests for geocontext pipeline
- Existing test file focuses on a small matrix-join helper path, not geocontext aggregation correctness.
- Risk: regressions in spatial aggregation go undetected.

## Recommended Improvements
1. Enforce `aggregation_type` in `aggregate_layer_to_hex` with explicit allowed values and fail-fast on unknown values.
2. Add optional strict cap for polygon shares (`pmin(area_share, 1)`) plus a QC report of any pre-cap exceedances.
3. Validate each selected layer geometry type before aggregation and block mixed types unless explicitly allowed.
4. Add a generated run manifest (timestamp, selected layers, output columns, row counts) and store with exported CSVs.
5. Add tests for:
   - point count correctness
   - line length correctness
   - polygon share correctness and overlap behavior
   - first-4 layer smoke test against expected columns.

## Copied Pipeline Location
- `script/upstream_databas/`

