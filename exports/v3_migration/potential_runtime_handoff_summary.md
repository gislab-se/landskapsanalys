# V3 Potential Runtime Handoff Summary

Date: 2026-06-10

## Scope

This handoff is only for the first real V3 runtime result layer:

`Potentiell etableringsyta`

V3 should build this layer from actual V2 base potential frames for wind and solar. Do not require energy scenario, scenario allocation, proposed GWh, area demand, or outside-LP for this first step.

The layer answers one question:

Where is wind and/or solar suitable after the active base filters?

## V2 Sources That Govern This Layer

### Main V2 files

- `potential_app.py`
  - `9346` `_potential_establishment_source_frame(...)`
  - `9441` `_combined_establishment_class(...)`
  - `9463` `_apply_establishment_style_columns(...)`
  - `9676` `_combined_potential_establishment_frame(...)`
  - `10486` `_combined_establishment_feature_collection(...)`
  - `10583` `_combined_establishment_layer(...)`
  - `10652` `_combined_potential_establishment_family_layers(...)`
- `apps/potential_model/geometry.py`
  - `31` `load_h3_display_geometries(...)`
- `apps/potential_model/manifests/regions/bornholm.json`
- `apps/potential_model/manifests/regions/trondelag.json`
- `apps/potential_model/manifests/regions/vara.json`
- `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json`
- `apps/potential_model/manifests/landscape/trondelag_landscape_placeholder.json`

### Supporting V2 runtime logic

- Solar base potential:
  - `potential_app.py:5820` `_solar_large_scale_frame(...)`
  - `potential_app.py:5983` `_combined_solar_hex_frame(...)`
- Wind base potential:
  - `potential_app.py:8620` `_build_wind_runtime_hex_layer_data(...)`
  - `potential_app.py:8956` `_finalize_fast_wind_share_frame(...)`
  - `potential_app.py:8988` `_wind_fast_distance_runtime_result(...)`
- Display/geometries:
  - `potential_app.py:3531` `_h3_display_geometry_path(...)`
  - `potential_app.py:4621` `_hex_family_layers(...)`
  - `apps/potential_model/geometry.py:31` `load_h3_display_geometries(...)`

### V2 tests and validation scripts

- `scripts/validate_potential_region_contract.py`
  - checks Trondelag native CRS `EPSG:25832`
  - checks Trondelag exposes exactly R7/R6/R5
  - checks Trondelag does not expose R8/R9
  - checks Trondelag feature counts: R7 `13735`, R6 `2163`, R5 `365`
  - checks zoom-family layer contract builds R7/R6/R5
- `scripts/validate_potential_region_parity.py`
  - checks active wind and solar potential rows
  - checks Trondelag establishment parity runs in R7 light mode
  - checks R6/R5 rollup follows dominant R7 child classes
  - checks manual R6/R5 and zoom-family R6/R5 use the same classes
- `scripts/test_potential_interactions_smoke.py`
  - applies controls and checks the app does not throw severe browser errors
- `scripts/test_potential_tutorial_ui.py`
  - checks user-facing result layer names and guide steps
- `scripts/test_potential_language_switch.py`
  - checks result/tutorial copy survives language switch

### Commits that matter

- `48e6ebb` Add V3 potential runtime handoff
- `c530c02` Stabilize potential app H3 analysis
- `891d6bd` Stabilize potential app establishment UX
- `b30aa9d` Fix Trondelag establishment rollup
- `8562890` Fix Trondelag zoom adaptive layers
- `cc48d7f` Refine area demand and scenario allocation
- `fbeb8c6` Suppress tiny outside-potential markers
- `27e3a4b` Add potential app interaction smoke tests
- `93b7b9f` Fix social acceptance capacity metrics
- `2c3dfd3`, `bdd4b79`, `999b7c3` Tutorial/UI stabilization

For this first V3 layer, use `cc48d7f` and `fbeb8c6` mainly as evidence that scenario allocation and outside-LP were fragile and should stay out of the first runtime port.

## How V2 Builds `wind_suitable`

V2 normalizes the wind frame in `_potential_establishment_source_frame(...)`.

Input can be either a selected/runtime wind frame or a base potential wind frame. Required source key is `hex_id`.

Wind score/area rules:

- Preferred score field: `potential_area_share_pct`
- Fallback score field: `wind_score`
- If `potential_area_km2` exists:
  - use it as wind potential area
  - use `potential_area_share_pct` or `wind_score` as score if present
  - otherwise derive score from area divided by source H3 cell area
- If `potential_area_km2` is missing:
  - derive area as `potential_score_pct / 100 * source_h3_cell_area_km2`
- Clamp score to `0..100`
- Clamp area to `0..target_h3_cell_area_km2`

If `target_resolution < source_resolution`, V2 maps each source hex to `h3.cell_to_parent(hex_id, target_resolution)`, sums `potential_area_km2`, clamps to target cell area, and recomputes score from area.

Final rule:

```text
wind_suitable = wind_potential_area_km2 > 1e-9
```

For V3 `technology_potential_frame`, this maps to:

```text
technology_id = "wind"
suitable = potential_area_km2 > 1e-9
potential_score_pct = potential_area_share_pct or wind_score or derived score
potential_area_km2 = potential_area_km2 or derived area
```

## How V2 Builds `solar_suitable`

V2 normalizes solar in the same `_potential_establishment_source_frame(...)`.

Solar area/score rules:

- Preferred area field: `potential_area_km2`
- Fallback area field: `potential_area_m2 / 1_000_000`
- If no area exists, area is `0`
- Preferred score field: `potential_area_share_pct`
- Fallback score field: `solar_score`
- If no score exists, derive score from area divided by source H3 cell area
- Clamp score to `0..100`
- Clamp area to `0..target_h3_cell_area_km2`

V2 also reads optional filter-intersection fields:

- `large_filter_buffer_share_pct`
- `filter_buffer_share_pct`
- `protected_buffer_share_pct`

and optional small-scale area:

- `small_area_m2`

Default final rule:

```text
solar_suitable = solar_potential_area_km2 > 1e-9
```

Trondelag special rule:

When `region_id == "trondelag"` and the target display is coarse app-level R7 or a rollup from R7, V2 applies `coarse_filter_intersection_blocks`.

```text
if filter_intersection_share_pct > 0 and small_area_km2 <= 1e-9:
    solar_suitable = false
```

Reason from V2 comment: Trondelag uses R7 as app level. Any selected land-exclusion overlap must be visible at cell level so the coarse map mirrors Bornholm's finer-grid establishment behavior.

For V3 `technology_potential_frame`, this maps to:

```text
technology_id = "solar"
suitable = potential_area_km2 > 1e-9
potential_score_pct = potential_area_share_pct or solar_score or derived score
potential_area_km2 = potential_area_km2 or potential_area_m2 / 1e6
```

plus the Trondelag coarse-filter blocking rule.

## Combined Establishment Classes

V2 maps booleans to one class in `_combined_establishment_class(...)`:

```text
wind_suitable=true,  solar_suitable=true  -> wind_and_solar
wind_suitable=true,  solar_suitable=false -> wind_only
wind_suitable=false, solar_suitable=true  -> solar_only
wind_suitable=false, solar_suitable=false -> not_suitable
```

V3 should keep this mapping exactly.

## Geometry And H3 Cells

V2 does not invent geometry inside the result builder. It uses region display geometry manifests.

Geometry loader:

- `apps/potential_model/geometry.py:31` `load_h3_display_geometries(path_str)`
- reads GeoJSON features
- uses `properties.hex_id` or `properties.h3_address`
- prefers full H3 polygon from `h3.cell_to_boundary(hex_id)`
- falls back to feature geometry
- returns EPSG:4326 polygon geometry for Leaflet

V3 should do the same:

1. Load display geometries for the requested region and display H3 resolution.
2. Build a base frame from all display `hex_id`s.
3. Left-join normalized wind and solar `technology_potential_frame` rows.
4. Missing technology rows mean `suitable=false`, score/area `0`.
5. Emit GeoJSON FeatureCollection in EPSG:4326.

### Bornholm geometry

From `apps/potential_model/manifests/regions/bornholm.json`:

- native CRS: `EPSG:25833`
- web/render CRS: `EPSG:4326`
- available H3 display resolutions: R6/R7/R8/R9/R10
- source/default analysis: R10
- default display: R8
- display geometries:
  - R10: `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/map/bornholm_v10_landscape_types_map_data.geojson`
  - R9: `docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_h3_res_9_land_clipped.geojson`
  - R8: `docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_h3_res_8_land_clipped.geojson`
  - R7: `docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_h3_res_7_land_clipped.geojson`
  - R6: `docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_h3_res_6_land_clipped.geojson`

### Trondelag geometry

From `apps/potential_model/manifests/regions/trondelag.json`:

- native CRS: `EPSG:25832`
- web/render CRS: `EPSG:4326`
- available H3 display resolutions: R7/R6/R5 only
- source/default analysis: R7
- default display: R7
- feature counts:
  - R7: `13735`
  - R6: `2163`
  - R5: `365`
- display geometries:
  - R7: `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson`
  - R6: `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r6_rollup.geojson`
  - R5: `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r5_rollup.geojson`

V3 must not expose Trondelag R8 or R9 in the interactive app unless a later data/product decision explicitly changes the contract.

### Vara/Skaraborg geometry

From `apps/potential_model/manifests/regions/vara.json`:

- status: `planned`
- available H3 resolutions: `[]`
- default H3 resolution: `null`
- potential manifest: `null`

V3 must return `missing` and must not render a synthetic `Potentiell etableringsyta` as if it were analysis.

## Region Data Status

| Region | Base geometry | Base wind | Base solar | Scenario/allocation | V3 first-layer status |
|---|---|---|---|---|---|
| Bornholm | ok, R10/R8 etc | ok/prototype from V2 runtime | ok/prototype from V2 runtime | placeholder/scenario separate | `ok` for base layer |
| Trondelag | ok, R7 app bundle with R6/R5 rollups | ok/proxy, fast-distance/runtime controller flow | ok/proxy, R7 solar filters; population uses 250 m grid/centroid proxy | placeholder/proxy, keep separate | `ok_with_proxy_notes` for base layer |
| Vara/Skaraborg | missing | missing | missing | missing | `missing` |

Important Trondelag notes:

- Population/settlement currently uses a 250 m grid/centroid proxy.
- User-facing population and settlement buffers should be dissolved polygon buffers, not H3 buffer overlays.
- PDF/LABLAB landscape-type layers are experimental and not the base potential layer.
- Energy scenario/TIMES/AreaDemand placeholders must not be required for `Potentiell etableringsyta`.

## Minimal V3 Runtime Contract

V3 should normalize V2 wind and solar rows into:

```text
technology_potential_frame
  hex_id: string
  technology_id: "wind" | "solar"
  suitable: boolean
  potential_score_pct: number
  potential_area_km2: number
  source_h3_resolution: integer
  display_h3_resolution: integer
  data_status: "ok" | "proxy" | "empty" | "placeholder" | "missing"
  source_ref: string
  notes: string optional
```

Then materialize:

```text
potential_establishment_frame
  hex_id
  wind_suitable
  solar_suitable
  wind_potential_score
  solar_potential_score
  wind_potential_area_km2
  solar_potential_area_km2
  establishment_class
  establishment_label
  fill
  stroke
  fill_opacity
```

Do not include scenario-only fields in the first implementation unless they are explicitly `null` and ignored by the UI:

- `wind_allocated_area_km2`
- `solar_allocated_area_km2`
- `wind_allocated_gwh`
- `solar_allocated_gwh`
- `outside_lp_shortage`
- `outside_lp_reason`
- `wind_outside_lp_area_km2`
- `solar_outside_lp_area_km2`

## V2 Tests V3 Should Recreate First

1. `test_normalize_wind_uses_potential_area_share_pct`
2. `test_normalize_wind_falls_back_to_wind_score`
3. `test_normalize_solar_uses_potential_area_km2`
4. `test_normalize_solar_falls_back_to_potential_area_m2`
5. `test_wind_suitable_is_area_greater_than_epsilon`
6. `test_solar_suitable_is_area_greater_than_epsilon`
7. `test_trondelag_solar_filter_intersection_blocks_coarse_suitability`
8. `test_establishment_class_wind_and_solar`
9. `test_establishment_class_wind_only`
10. `test_establishment_class_solar_only`
11. `test_establishment_class_not_suitable`
12. `test_bornholm_materializes_potential_establishment_without_energy_scenario`
13. `test_trondelag_materializes_r7_potential_establishment_without_energy_scenario`
14. `test_trondelag_available_display_resolutions_are_exactly_r7_r6_r5`
15. `test_trondelag_r8_r9_are_not_exposed`
16. `test_trondelag_r6_r5_rollup_uses_dominant_r7_child_class`
17. `test_skaraborg_vara_missing_does_not_render_placeholder`
18. `test_geojson_features_use_display_geometry_epsg4326`
19. `test_draft_change_does_not_rebuild_rendered_snapshot_before_apply`
20. `test_layer_toggle_does_not_change_view_or_recompute_analysis`

## V3 Implementation Order

1. Implement region source registry and status resolution.
2. Implement `load_technology_potential_frame(region_id, technology_id, applied_state)`.
3. Normalize V2-shaped wind and solar inputs to `technology_potential_frame`.
4. Load display geometry by region and display H3 resolution.
5. Join frames on display `hex_id`.
6. Classify with the V2 four-class mapping.
7. Emit `rendered_snapshot.layers[result.potential_establishment_area]`.
8. Make the layer default visible only when a non-empty FeatureCollection exists.
9. Add the tests above before adding scenario allocation or outside-LP.

