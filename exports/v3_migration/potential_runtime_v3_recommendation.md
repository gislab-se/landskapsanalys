# Potential Runtime V3 Recommendation

Date: 2026-06-10

## Recommendation In One Sentence

Port V2's `Potentiell etableringsyta` behavior as a small typed runtime contract: two `technology_potential_frame`s in, one result layer out, no scenario allocation and no outside-LP.

## What To Port Directly

Port these V2 behaviors:

- Wind and solar are normalized separately.
- `suitable` is based on positive potential area after active base filters.
- Wind and solar booleans map to exactly four establishment classes.
- Geometry comes from region H3 display geometry manifests.
- GeoJSON for Leaflet is EPSG:4326.
- Native CRS remains region-specific for distance, buffer and area logic.
- Trondelag exposes only R7/R6/R5.
- Trondelag R6/R5 rollups follow dominant R7 child establishment classes.
- Layer toggle is UI-only and does not recompute analysis or change map view.

## What Not To Port Yet

Do not port these into the first runtime layer:

- energy scenario requirement
- TIMES/AreaDemand coupling
- scenario allocation
- `outside_lp_shortage`
- outside-LP markers
- GWh allocation fields
- popup HTML as the data contract
- V2's broad Streamlit session-state shape
- V2's large `potential_app.py` structure

Scenario and outside-LP can be added later as separate result layers/properties once the base layer is stable.

## Proposed V3 Functions

```python
def load_technology_potential_frame(
    region_id: str,
    technology_id: Literal["wind", "solar"],
    applied_state: AppliedState,
) -> TechnologyPotentialFrame:
    ...


def materialize_potential_establishment_layer(
    region: RegionManifest,
    wind_frame: TechnologyPotentialFrame,
    solar_frame: TechnologyPotentialFrame,
    display_h3_resolution: int,
) -> ResultLayerSpec:
    ...
```

The loader should never read draft/widget keys. It should consume normalized `applied_state`.

## Technology Frame Normalization

### Required V3 fields

```text
hex_id
technology_id
suitable
potential_score_pct
potential_area_km2
source_h3_resolution
display_h3_resolution
data_status
source_ref
```

### Wind mapping from V2

V2 source fields:

- `hex_id`
- `potential_area_share_pct` preferred
- `wind_score` fallback
- `potential_area_km2` optional

V3 mapping:

```text
potential_score_pct = potential_area_share_pct ?? wind_score ?? derived_from_area
potential_area_km2 = potential_area_km2 ?? potential_score_pct / 100 * source_h3_area_km2
suitable = potential_area_km2 > 1e-9
```

If rolling from source to display resolution:

```text
display_hex_id = h3.cell_to_parent(source_hex_id, display_h3_resolution)
potential_area_km2 = sum(child potential_area_km2)
potential_area_km2 = min(potential_area_km2, display_h3_area_km2)
potential_score_pct = potential_area_km2 / display_h3_area_km2 * 100
```

### Solar mapping from V2

V2 source fields:

- `hex_id`
- `potential_area_km2` preferred
- `potential_area_m2` fallback
- `potential_area_share_pct` preferred score
- `solar_score` fallback score
- optional filter fields:
  - `large_filter_buffer_share_pct`
  - `filter_buffer_share_pct`
  - `protected_buffer_share_pct`
  - `small_area_m2`

V3 mapping:

```text
potential_area_km2 = potential_area_km2 ?? potential_area_m2 / 1e6 ?? 0
potential_score_pct = potential_area_share_pct ?? solar_score ?? derived_from_area
suitable = potential_area_km2 > 1e-9
```

Trondelag coarse-display rule:

```text
if region_id == "trondelag" and display_h3_resolution <= 7:
    filter_share = max(
        large_filter_buffer_share_pct,
        filter_buffer_share_pct,
        protected_buffer_share_pct,
    )
    if filter_share > 0 and small_area_m2 <= 0:
        suitable = False
```

## Result Layer Contract

V3 should publish one result layer:

```json
{
  "id": "result:potential_establishment_area:{region_id}:r{display_h3_resolution}",
  "label": "Potentiell etableringsyta",
  "layer_kind": "result",
  "result_type": "potential_establishment_area",
  "default_visible": true,
  "visible": true,
  "data_status": "ok",
  "feature_collection": {
    "type": "FeatureCollection",
    "features": []
  }
}
```

Recommended feature properties:

```text
hex_id
establishment_class
establishment_label
wind_suitable
solar_suitable
wind_potential_score
solar_potential_score
wind_potential_area_km2
solar_potential_area_km2
data_status
fill
stroke
fill_opacity
tooltip_title
tooltip_body
```

Keep popup text derived from structured properties, not the other way around.

## Region Policy

### Bornholm

V3 status: `ok`

- Native CRS: `EPSG:25833`
- Render CRS: `EPSG:4326`
- Source/default analysis H3: R10
- Default display H3: R8
- Available display H3: R10/R9/R8/R7/R6
- Scenario manifests are placeholder and should not be required for base potential rendering.

### Trondelag

V3 status: `ok_with_proxy_notes`

- Native CRS: `EPSG:25832`
- Render CRS: `EPSG:4326`
- Source/default analysis H3: R7
- Available display H3: R7/R6/R5 only
- Feature counts must remain R7 `13735`, R6 `2163`, R5 `365`
- R8/R9 must not be exposed in the interactive app.
- Wind/solar runtime is usable for base potential, but some source semantics are proxy/modelled.
- Population/settlement uses a 250 m grid/centroid proxy.
- Energy scenario/TIMES/AreaDemand is placeholder/proxy and separate from the base layer.
- LABLAB/PDF landscape is experimental and should not be used as the base potential source.

### Vara/Skaraborg

V3 status: `missing`

- No available H3 resolutions in V2 region manifest.
- No potential manifest.
- No display geometry.
- Return missing status and render no synthetic establishment layer.

## Trondelag R7/R6/R5 Rule

V3 should enforce this in both configuration and tests:

```text
available_h3_resolutions == [7, 6, 5]
default_h3_resolution == 7
default_display_h3_resolution == 7
8 not in available_h3_resolutions
9 not in available_h3_resolutions
```

Rollup rule:

- Build R7 establishment classes first.
- For R6/R5, map R7 children to parent cells.
- Sum area by establishment class.
- Parent class is the class with dominant child area.
- Manual R6/R5 and zoom-family R6/R5 must match.

## V3 Test Backlog For This Layer

Port these V2 test intentions directly:

- `test_normalize_wind_uses_potential_area_share_pct`
- `test_normalize_wind_falls_back_to_wind_score`
- `test_normalize_wind_derives_area_from_score`
- `test_normalize_solar_uses_potential_area_km2`
- `test_normalize_solar_falls_back_to_potential_area_m2`
- `test_normalize_solar_derives_score_from_area`
- `test_wind_suitable_threshold`
- `test_solar_suitable_threshold`
- `test_trondelag_solar_filter_intersection_blocks_coarse_suitability`
- `test_establishment_class_wind_and_solar`
- `test_establishment_class_wind_only`
- `test_establishment_class_solar_only`
- `test_establishment_class_not_suitable`
- `test_geojson_uses_display_geometry_for_hex_id`
- `test_bornholm_potential_establishment_without_energy_scenario`
- `test_trondelag_potential_establishment_r7_without_energy_scenario`
- `test_trondelag_display_resolutions_are_r7_r6_r5_only`
- `test_trondelag_r8_r9_not_exposed`
- `test_trondelag_rollup_r6_r5_dominant_child_class`
- `test_skaraborg_missing_does_not_render_placeholder`
- `test_draft_change_does_not_rebuild_rendered_snapshot_before_apply`
- `test_layer_toggle_does_not_recompute_analysis`
- `test_layer_toggle_does_not_call_fitbounds`

## First Implementation Path

1. Add typed region runtime status.
2. Add `TechnologyPotentialFrame` normalizer.
3. Add wind and solar loaders that return normalized frames from V2-shaped sources.
4. Add display-geometry loader keyed by region and display H3 resolution.
5. Add establishment materializer using the exact four V2 classes.
6. Add `rendered_snapshot.layers` entry.
7. Add tests for Bornholm, Trondelag and Vara/Skaraborg.
8. Only after this passes, start a separate migration for scenario allocation.

