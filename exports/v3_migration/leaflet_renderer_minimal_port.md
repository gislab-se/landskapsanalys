# Minimal V3 Port Of V2 Leaflet Renderer

Date: 2026-06-09

## Goal

Give V3 the same map-layer UX as V2 with the smallest practical port:

- collapsed layer button inside the map, upper right
- OSM/Satellite base-layer radio buttons
- result/source/buffer overlay checkboxes
- overlay toggles that do not change analysis state
- no technical CRS/cache/status rows in the map UI

## Port These V2 Pieces

1. `apps/potential_model/map_rendering.py::build_layered_hex_map_html`
   - HTML shell
   - Leaflet CSS/JS includes
   - `L.map(..., { preferCanvas: true })`
   - OSM and Satellite `L.tileLayer`
   - `buildGeoJsonLayer(spec, index)`
   - `L.control.layers(..., { collapsed: true })`
   - scale control
   - optional note and legend controls

2. `potential_app.py::_render_html_map`
   - Prefer V3's component wrapper if it exists.
   - Keep the same fallback idea: iframe/component HTML, no folium dependency.

3. A V3 adapter from `rendered_snapshot.layers` to V2 renderer specs
   - `label` -> V2 `name`
   - semantic `layer_kind` -> keep for metadata, but map to V2 `geometry_kind`/renderer kind
   - `geometry_kind` -> V2 renderer `layer_kind` (`hex` or `vector`)
   - `style.fill_property` -> V2 `fill_property`
   - `style.stroke_color` -> V2 `stroke_color`
   - `style.fill_color` -> V2 `fill_color`
   - `style.stroke_opacity` -> V2 `stroke_opacity`
   - `style.fill_opacity` -> V2 `fill_opacity`
   - `style.weight` -> V2 `weight`
   - preserve `source_layer_id`, `buffer_layer_id`, `legend_*`, `z_index`, `default_visible`

4. Optional localStorage behavior
   - Port if V3 wants map view and overlay visibility to survive reruns.
   - Scope keys by region and rendered snapshot version.
   - Keep this UI-only; never write to draft/applied state.

## Do Not Port

- V2's old/root PyDeck `app.py` map.
- `apps/acceptance_model/map_rendering.py` PyDeck renderer.
- folium or streamlit-folium wrappers.
- V2 debug layer tables as standard end-user UI.
- Any direct reads from draft widget keys inside the map renderer.

## V3 Renderer Boundary

The renderer should receive a frozen object like:

```json
{
  "map_id": "skaraborg:applied:2026-06-09T12:00:00Z",
  "center": [58.39, 13.44],
  "zoom": 9,
  "bounds": [[57.8, 12.4], [59.0, 14.8]],
  "layers": []
}
```

The renderer may keep UI-only visibility in browser localStorage, but it must treat `layers` as read-only.

## Acceptance Criteria

- Opening the map shows OSM and result overlays according to `default_visible`.
- The Leaflet layer icon is in the upper-right map corner and collapsed by default.
- Switching OSM/Satellite does not rerun V3 analysis.
- Toggling result/source/buffer overlays does not rerun V3 analysis.
- Applying side-panel changes rebuilds `rendered_snapshot.layers`.
- Draft side-panel edits do not alter the layer control until apply.
- Layer-control text contains only user labels, never `native_crs`, `render_crs`, `operation`, `cache_key`, `feature_count`, or `data_status`.
