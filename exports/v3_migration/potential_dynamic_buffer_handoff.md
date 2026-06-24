# V2 -> V3 Handoff: Dynamic Buffers For Potential Establishment

Date: 2026-06-10

Scope: how V2 updates `wind_suitable`, `solar_suitable`, and `establishment_class` when applied distance/buffer parameters change. Scenario allocation and outside-LP remain out of scope.

## Short Answer

V2 does not treat `Potentiell etableringsyta` as a static layer. It rebuilds wind and solar potential frames from the currently applied parameter state, then rebuilds the establishment frame from those two technology frames.

For road changes, V2 has two relevant applied inputs:

- Wind: `road_distance_m`, registry group `transport`, semantic `distance_conflict`.
- Solar: `road_buffer_m`, solar filter group `transport`, semantic `exclusion` in the solar filter pipeline.

The app start/reference default is 300 m for both. The raw wind fallback default is 100 m, but `_ensure_default_start_state(...)` applies the 300 m reference default in the app.

## Files And Functions

Core files:

- `potential_app.py`
- `apps/potential_model/wind_acceptance.py`
- `apps/acceptance_model/layers.py`
- `apps/acceptance_model/runtime_geometry.py`
- `script/acceptance/render_wind_acceptance_geometry_runtime.R`
- `script/acceptance/render_trondelag_population_buffer.R`
- `apps/acceptance_model/registry.json`
- `apps/acceptance_model/registry_trondelag.json`
- `docs/geocontext/acceptance_framework/data/*/asset_manifest.csv`

Important V2 functions:

- `potential_app.py:260` solar road filter spec: group `transport`, config key `road_buffer_m`, default 100 in control metadata.
- `potential_app.py:394` `DEFAULT_SOLAR_APPLIED_CONFIG`: applied start has `road_buffer_m = 300.0`.
- `potential_app.py:4230` `_solar_active_filter_configs(...)`: converts applied solar config into active filter configs with `group_id`, `layer_ids`, `buffer_m`, and `effect`.
- `potential_app.py:5394` `_solar_filter_runtime_result(...)`: sends `{active_layer_ids, analysis_value_m}` to geometry runtime.
- `potential_app.py:5478` `_distance_table_filter_share_frame(...)`: fallback path from precomputed distance tables to H3 filter shares.
- `potential_app.py:5600` `_solar_filter_union_buffer_frame(...)`: unions solar filter geometries/shares per H3 and returns `filter_buffer_share_pct`.
- `potential_app.py:5813` `_solar_large_scale_frame(...)`: subtracts exclusion shares, applies feasibility shares, and outputs solar potential area.
- `potential_app.py:5969` `_combined_solar_hex_frame(...)`: turns large/small solar frames into combined solar potential.
- `potential_app.py:7221` `_default_wind_params(...)`: raw fallback has `road_distance_m = 100.0`.
- `potential_app.py:7237` `_reference_default_wind_params(...)`: app start/reference has `road_distance_m = 300.0`.
- `potential_app.py:7252` `_reference_default_wind_layer_selection(...)`: app start/reference selects transport roads.
- `potential_app.py:8989` `_wind_fast_distance_runtime_result(...)`: Trondelag wind fast path from distance tables.
- `potential_app.py:9036` min distance and intersection are merged across selected road layers.
- `potential_app.py:9040` group acceptance is computed from `analysis_kind` and applied threshold.
- `potential_app.py:9041` wind potential share is updated by taking the minimum across active groups.
- `potential_app.py:9346` `_potential_establishment_source_frame(...)`: `*_suitable` is based on positive potential area.
- `potential_app.py:9429` Trondelag solar coarse display can block suitability when filter overlap exists.
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`: combines wind/solar suitability into establishment class.
- `potential_app.py:10831` `_wind_polygon_preview_state(...)`: chooses Trondelag fast distance path or geometry runtime path.
- `potential_app.py:10998` `_wind_polygon_summary_frame(...)`: converts wind runtime result into the potential frame.
- `potential_app.py:11120` `_wind_runtime_config_json(...)`: sends selected wind groups and `analysis_value_m` to geometry runtime.

Supporting logic:

- `apps/potential_model/wind_acceptance.py:20` `WIND_GROUP_LAYER_DEFAULTS`
- `apps/potential_model/wind_acceptance.py:59` `GROUP_PARAM_MAP`, including `transport -> road_distance_m`
- `apps/potential_model/wind_acceptance.py:85` `HARD_EXCLUSION_GROUPS`
- `apps/potential_model/wind_acceptance.py:194` distance-conflict acceptance
- `apps/potential_model/wind_acceptance.py:210` proximity-feasibility acceptance
- `apps/potential_model/wind_acceptance.py:223` hard-exclusion acceptance
- `apps/acceptance_model/layers.py:247` `source_geojson_for_layer(...)`
- `apps/acceptance_model/layers.py:271` `distance_table_for_layer(...)`
- `apps/acceptance_model/runtime_geometry.py:45` `run_geometry_runtime(...)`
- `script/acceptance/render_wind_acceptance_geometry_runtime.R:301` `prepare_layer_geometry(...)`
- `script/acceptance/render_wind_acceptance_geometry_runtime.R:431` combined runtime geometry: feasible intersection minus conflict union, or landmask minus conflict union.

## How Road Buffer Changes Affect H3

### Wind, Bornholm

Bornholm wind normally goes through the geometry runtime path:

1. V2 sends selected groups/layers and applied meters to `_wind_runtime_config_json(...)`.
2. `run_geometry_runtime(...)` calls `render_wind_acceptance_geometry_runtime.R`.
3. The R runtime unions source geometries, buffers them in native CRS, clips to landmass, and combines groups.
4. Conflict groups, including roads, are subtracted from the landmask.
5. `_wind_runtime_hex_layer_frame(...)` converts the resulting geometry to H3 coverage/share.
6. `_wind_polygon_summary_frame(...)` emits `potential_area_share_pct`, `potential_area_km2`, and `wind_score`.
7. `_potential_establishment_source_frame(...)` sets `wind_suitable = wind_potential_area_km2 > 1e-9`.

So a larger `road_distance_m` changes H3 cells by changing the buffered conflict geometry, then re-H3-covering the resulting land area.

### Wind, Trondelag

Trondelag wind uses the fast distance-table path:

1. `_wind_fast_distance_runtime_result(...)` loads per-layer distance tables from `asset_manifest.csv`.
2. Each table has `hex_id`, `distance_m`, `intersects`.
3. `_target_resolution_distance_frame(...)` rolls distance tables to the target display/analysis resolution.
4. Selected road layers are merged; min distance and any intersection are computed.
5. `transport` is `distance_conflict`.
6. Acceptance is `0` when a cell intersects or is within the threshold, ramps from `0` to `1` between threshold and `2 * threshold`, and is `1` beyond that.
7. Wind potential share becomes the minimum acceptance share across active groups.

So a larger `road_distance_m` changes H3 cells by re-evaluating distance columns against a new threshold, not by recomputing geometry.

### Solar

Solar uses the filter pipeline:

1. `_solar_active_filter_configs(...)` reads applied config and emits active filters.
2. Exclusion filters subtract area share; feasibility filters multiply area share.
3. Roads are an exclusion filter in solar, using `road_buffer_m`.
4. `_solar_filter_union_buffer_frame(...)` first tries runtime geometry and H3 overlay.
5. If runtime geometry is unavailable, `_distance_table_filter_share_frame(...)` falls back to precomputed distance tables and approximates line/point/polygon share.
6. `_solar_large_scale_frame(...)` starts from `100%` candidate land, subtracts exclusion share, applies feasibility share, then computes `potential_area_m2/km2`.
7. `_combined_solar_hex_frame(...)` emits the solar potential frame.
8. `_potential_establishment_source_frame(...)` sets `solar_suitable = solar_potential_area_km2 > 1e-9`.

Trondelag has one extra coarse-R7 rule for solar: if a selected land-exclusion filter overlaps a coarse cell and there is no small-scale solar area, `solar_suitable` can be false even when the aggregated area remains positive. This is in `potential_app.py:9429`.

## Rule Semantics

Wind registry semantics:

- `distance_conflict`: `settlement`, `transport`, `aviation_bird`
- `proximity_feasibility`: `electrical`
- `hard_exclusion`: `protected`, `culture`, `coastal`, `aviation_approach`, `military`
- Trondelag-only hard exclusions: `land_use`, `reindeer`

Solar filter semantics:

- `exclusion`: population, protected nature, land use/forest, roads, culture, reindeer, coastal
- `feasibility`: electrical/grid proximity

Important: solar roads use the same `transport` source layers as wind, but solar treats them as exclusion area, not as wind-style distance-conflict ramp.

## Does V2 Recompute Geometry Or Select Precomputed Frames?

Both, depending on region and technology:

- Bornholm wind: recomputes/caches runtime geometry for the applied config, then H3-overlays it.
- Trondelag wind: does not recompute geometry for analysis; it re-evaluates precomputed distance tables.
- Solar: tries runtime geometry and H3 overlay; falls back to distance-table share approximation where needed.
- Trondelag population visual buffers are dissolved polygon buffers from the 250 m population-grid proxy, but analysis currently uses distance-table/share logic.

There is no static list of ready frames for each possible slider value. V3 must either evaluate the rule against geometry/distance tables on apply, or precompute an explicit finite set of applied states.

## Inputs V3 Must Send From `applied_analysis_input`

Minimum wind input:

- `region_id`
- `analysis_h3_resolution`
- `display_h3_resolution`
- `wind.selected_layers_by_group`
- `wind.params.settlement_distance_m`
- `wind.params.road_distance_m`
- `wind.params.grid_max_distance_m`
- `wind.params.protected_buffer_m`
- `wind.params.coastal_buffer_m`
- `wind.params.culture_buffer_m`
- `wind.params.reindeer_buffer_m`
- `wind.params.aviation_approach_buffer_m`
- `wind.params.aviation_bird_distance_m`
- `wind.params.military_buffer_m`
- `wind.empty_selection_active`, if V3 supports the V2 unfiltered-land mode

Minimum solar input:

- `solar.large_scale_active`
- `solar.large_unfiltered_land_active`
- `solar.large_population_active`
- `solar.population_buffer_m`
- `solar.large_protected_layer_ids`
- `solar.protected_buffer_m`
- `solar.large_road_layer_ids`
- `solar.road_buffer_m`
- `solar.large_electrical_layer_ids`
- `solar.solar_grid_max_distance_m`
- `solar.large_culture_layer_ids`
- `solar.culture_buffer_m`
- `solar.large_reindeer_layer_ids`
- `solar.reindeer_buffer_m`
- `solar.large_land_use_layer_ids`
- `solar.forest_buffer_m`
- `solar.large_coastal_layer_ids`
- `solar.coastal_buffer_m`

If V3 exposes one shared road slider, map it to both:

- `wind.params.road_distance_m`
- `solar.road_buffer_m`

If V3 exposes technology-specific controls, keep them separate.

## Minimal V3 Contract

Recommended contract:

1. `draft` changes only UI state.
2. `applied_analysis_input` is created on Apply and includes all active layer ids and meter values.
3. V3 computes a stable `applied_fingerprint` over normalized applied input.
4. Potential runtime uses `applied_fingerprint` as cache key.
5. V3 builds or refreshes:
   - `wind_potential_frame`
   - `solar_potential_frame`
   - `potential_establishment_frame`
   - `potential_establishment_area_geojson`
6. `rendered_snapshot` points to the newly built establishment layer.
7. A visible source/buffer toggle must not change analysis unless the applied source/layer ids or meters changed.

Minimum establishment logic:

```text
wind_suitable  = wind_potential_area_km2 > 1e-9
solar_suitable = solar_potential_area_km2 > 1e-9

if region == trondelag and display/source resolution is coarse R7:
  solar_suitable = solar_suitable AND NOT(selected_exclusion_overlap AND no_small_solar_area)

establishment_class =
  wind_and_solar if wind_suitable and solar_suitable
  wind_only      if wind_suitable
  solar_only     if solar_suitable
  not_suitable   otherwise
```

## Example Output For V3 Tests

Generated files:

- `exports/v3_migration/potential_dynamic_buffer_examples.csv`
- `exports/v3_migration/potential_dynamic_buffer_examples.json`
- Script: `scripts/export_potential_dynamic_buffer_examples.py`

Comparison: both wind `road_distance_m` and solar `road_buffer_m` changed from 300 m to 400 m.

Bornholm, R10 analysis -> R8 display:

- Class changes: 26 hexes
- Wind suitability changes: 24 hexes
- Solar suitability changes: 23 hexes
- Example: `881f0c9b01fffff` changes `wind_and_solar -> not_suitable`

Trondelag, R7 analysis/display:

- Class changes: 38 hexes
- Wind suitability changes: 0 hexes in this comparison
- Solar suitability changes: 38 hexes
- Example: `870800474ffffff` changes `wind_and_solar -> wind_only`

## Tests V3 Should Create

1. `test_potential_establishment_recomputes_after_applied_road_buffer`
   - Load Bornholm.
   - Apply road 300 m.
   - Apply road 400 m.
   - Assert `881f0c9b01fffff` changes from `wind_and_solar` to `not_suitable`.

2. `test_trondelag_solar_coarse_filter_blocks_suitability`
   - Load Trondelag R7.
   - Apply road 300 m and 400 m.
   - Assert `870800474ffffff` changes from `wind_and_solar` to `wind_only`.
   - Assert this happens even though solar area can remain positive, because `solar_suitable` is false.

3. `test_draft_does_not_change_rendered_snapshot_until_apply`
   - Change draft road buffer.
   - Assert the existing rendered establishment layer is unchanged.
   - Apply.
   - Assert `applied_fingerprint` and establishment output change.

4. `test_source_buffer_visibility_does_not_change_analysis`
   - Toggle source/buffer visibility only.
   - Assert potential frame and establishment class counts do not change.

5. `test_trondelag_rejects_r8_r9_dynamic_establishment`
   - Assert Trondelag dynamic potential only uses R7/R6/R5.

## V2 Tests That Already Guard This

- `scripts/validate_potential_region_parity.py`
  - `ROAD_TEST_LAYER_ID = "roads_large"` and road buffers are explicitly set.
  - Asserts solar road filter reduces candidate area.
  - Asserts solar road filter changes shared establishment classes.
  - Asserts separate solar/wind source and buffer layers remain visible.
  - Asserts Trondelag establishment parity runs in R7 and R6/R5 rollups follow dominant R7 child classes.
- `scripts/validate_potential_region_contract.py`
  - Asserts Trondelag CRS, H3 R7/R6/R5 policy, and display geometry counts.
- `scripts/test_potential_interactions_smoke.py`
  - Smoke coverage for draft/apply/interaction state behavior.

## Relevant Commits

- `ae9dee1` Extend solar filters and remove Markblokke base
- `1d3ab26` Make solar filter effects visible and robust
- `dcb265d` Add Trondelag road parity layers
- `2038a9f` Activate Trondelag R7 potential parity
- `b30aa9d` Fix Trondelag establishment rollup
- `fde565a` Update Trondelag potential app population buffers
- `17ae32d` Add electrical grid feasibility for solar
- `27e3a4b` Add potential app interaction smoke tests
- `8562890` Fix Trondelag zoom adaptive layers

Most important for this gap: `1d3ab26`, `dcb265d`, `2038a9f`, and `b30aa9d`.

## Recommendation

Recommendation: adapt now.

Do not port the whole Streamlit file. Port the small analysis contract:

- rule registry and group/layer ids
- applied parameter normalization
- distance-table evaluator for Trondelag wind
- solar filter share/effect semantics
- establishment-frame classification
- Trondelag R7 coarse solar blocking rule
- regression tests using the exported H3 examples

Do not wait for scenario allocation or outside-LP. They are downstream layers and should not block making `Potentiell etableringsyta` apply-driven.
