# V2 Leaflet Layer Control Inventory For V3

Date: 2026-06-09

This is a handoff only. No V2 app behavior has been changed.

## Executive Recommendation

V3 should port V2's custom Leaflet renderer pattern, not folium and not streamlit-folium. The best migration path is:

1. Keep V3's draft/applied/rendered snapshot model.
2. Build `rendered_snapshot.layers` from applied state only.
3. Feed those layers into a small custom Leaflet HTML/JS renderer modelled on V2's `build_layered_hex_map_html()`.
4. Let Leaflet's `L.control.layers` control map visibility only.

This gives V3 the exact UX we want: collapsed layer button inside the map, OSM/Satellite radio buttons, overlay checkboxes, no Streamlit rerun when a user toggles an already-rendered overlay, and no technical data status inside the map control.

Avoid making PyDeck emulate this control. PyDeck can render data, but V2's layer UX is native Leaflet behavior and would be more expensive to recreate correctly in deck.gl/PyDeck.

## 1. V2 Map Techstack

V2's Landskapspotential map is custom Leaflet HTML/JS embedded in Streamlit.

| Question | Answer |
| --- | --- |
| Leaflet directly? | Yes. V2 includes Leaflet CSS/JS from `unpkg.com/leaflet@1.9.4` and calls `L.map`, `L.tileLayer`, `L.geoJSON`, `L.control.layers`. |
| folium? | No evidence in the potential app. No `folium` imports or dependency. |
| streamlit-folium? | No evidence. No `streamlit_folium` or `st_folium`. |
| custom Leaflet HTML/JS? | Yes. `apps/potential_model/map_rendering.py` returns full HTML strings. |
| PyDeck/deck.gl? | Present in older/other app paths, not the V2 potential map rendered by `streamlit_app.py`. |
| Streamlit render path | `potential_app.py` imports `streamlit.components.v1` and renders the HTML with `components.html()` or `st.iframe()` fallback. |

Code references:

- Entry point: `streamlit_app.py:13` runs `potential_app.py`.
- Potential app imports Streamlit components and the Leaflet renderer: `potential_app.py:18-23`, `potential_app.py:44`.
- The main app calls `main()` in `potential_app.py:13585-13604`.
- Leaflet CSS/JS are embedded in `apps/potential_model/map_rendering.py:158-174`.
- The primary V2 layered map is created by `build_layered_hex_map_html()` in `apps/potential_model/map_rendering.py:133`.
- The map instance is created with `L.map(...).setView(...)` in `apps/potential_model/map_rendering.py:281`.
- The map is rendered to Streamlit by `_render_html_map()` and `_render_layers()` in `potential_app.py:7433-7476`.
- Layer control is Leaflet's native `L.control.layers`, not folium `LayerControl`: `apps/potential_model/map_rendering.py:619`.
- Legacy/other PyDeck references exist in `app.py:5`, `app.py:254-274`, and `apps/acceptance_model/map_rendering.py:16-145`; do not use those as the V3 layer-control model.
- `requirements.txt` includes `pydeck>=0.9` but not folium or streamlit-folium.

## 2. Kartinstans And Base Layers

The layered potential map starts with:

- `L.map('map', { preferCanvas: true })` at `apps/potential_model/map_rendering.py:281`.
- OSM tile layer is created and immediately added to the map at `apps/potential_model/map_rendering.py:283-286`.
- Satellite tile layer is created but not initially added at `apps/potential_model/map_rendering.py:288-291`.
- Base layers are passed to Leaflet as radio-button choices through `L.control.layers({ 'OSM': osm, 'Satellite': satellite }, overlays, { collapsed: true })` at `apps/potential_model/map_rendering.py:619`.

Default base layer:

- OSM is default because `.addTo(map)` is called on the OSM tile layer.
- Satellite is available in the control but off by default.

UI labels:

- V2 uses literal labels `"OSM"` and `"Satellite"`.

Simplified V2 model:

```js
const map = L.map('map', { preferCanvas: true }).setView(mapStartCenter, mapStartZoom);

const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 20,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  maxZoom: 20,
  attribution: 'Tiles &copy; Esri'
});

L.control.layers({ 'OSM': osm, 'Satellite': satellite }, overlays, { collapsed: true }).addTo(map);
```

## 3. Overlay Layers And Layer Control

V2 overlays are ordinary Leaflet GeoJSON layers created from layer spec dicts.

Renderer flow:

- `layerSpecs` is serialized from Python into JS at `apps/potential_model/map_rendering.py:176`.
- Each spec is passed to `buildGeoJsonLayer(spec, index)` at `apps/potential_model/map_rendering.py:409-465`.
- Each non-auto layer is registered as `overlays[spec.name] = layer` at `apps/potential_model/map_rendering.py:504`.
- Initial visibility is `savedOverlayVisibility[spec.name]` if present, otherwise `spec.default_visible !== false` at `apps/potential_model/map_rendering.py:506-508`.
- Auto-resolution layer families are exposed as one control row via `spec.control_name || spec.name` at `apps/potential_model/map_rendering.py:481-501` and `607-615`.

Important result overlays:

- `Potentiell etableringsyta` label is defined as `COMBINED_ESTABLISHMENT_LAYER_LABEL` in `potential_app.py:188`.
- Its spec is created in `_combined_establishment_layer()` at `potential_app.py:10583-10609`.
- It is default visible: `default_visible: True` at `potential_app.py:10600`.
- It uses `z_index: 476` and `layer_kind: "hex"` at `potential_app.py:10605-10606`.

- `Scenariofördelning i etableringshex` label is defined in `potential_app.py:189`.
- Its spec is created in `_scenario_allocation_marker_layer()` at `potential_app.py:10418-10451`.
- Its default visibility is conditional; for Trøndelag family layers it is forced off at `potential_app.py:10465`.
- It uses `z_index: 540` and `layer_kind: "hex"` at `potential_app.py:10447-10448`.

Source overlays:

- Solar population source is created by `_solar_population_source_layer()` at `potential_app.py:5028-5056`.
- Solar filter sources are built by `_solar_filter_source_layers()` at `potential_app.py:5284-5338`.
- Wind polygon/source layers are built in `_wind_polygon_source_layers()` around `potential_app.py:8231-8263` and `potential_app.py:8332-8393`.
- Source layers use names such as `Sol källa: Befolkningsunderlag`, `Sol källa: Skyddad natur`, and `Vind källa: ...`.
- They carry `source_layer_id` for dedupe and identity, e.g. `potential_app.py:5041`, `potential_app.py:5322`, `potential_app.py:8259`, `potential_app.py:8389`.

Buffer overlays:

- Population polygon buffer layer is created around `potential_app.py:5175-5197`.
- Solar population H3/polygon buffer layer is created around `potential_app.py:5263-5281`.
- Solar filter buffers are created in `_solar_filter_buffer_layer()` at `potential_app.py:5705-5725`.
- Wind filter buffers are created in `_wind_filter_buffer_layer()` at `potential_app.py:5783-5803`.
- Runtime wind buffer overlays are created in `_wind_polygon_group_layers()` at `potential_app.py:8396-8443`.
- Buffer layers use names such as `Solbuffert: ...` and `Vindbuffert: ...`.
- They carry `buffer_layer_id` for dedupe and identity, e.g. `potential_app.py:5177`, `potential_app.py:5265`, `potential_app.py:5706-5709`, `potential_app.py:5784-5787`, `potential_app.py:8426`.

Layer order and z-index:

- The renderer creates one custom Leaflet pane per spec and sets pane z-index from `spec.z_index`, falling back to `400 + index`: `apps/potential_model/map_rendering.py:409-413`.
- Result layers use higher z-indexes for overlays that must sit above broad hex layers, e.g. scenario markers at `540`, establishment at `476`, vector source/buffer layers around `455-459`.

Tooltip/popup behavior:

- Fill/stroke style can come from feature properties or spec defaults: `apps/potential_model/map_rendering.py:311-363`.
- Polygon/line layers use `L.geoJSON(... style ...)`; point layers become `L.circleMarker` at `apps/potential_model/map_rendering.py:415-446`.
- Tooltip is bound when a feature has `tooltip_title` or `tooltip_body`: `apps/potential_model/map_rendering.py:455-461`.
- Popup uses `props.popup`, then falls back to `tooltip_title`, `layer_label`, `spec.name`, or `hex_id`: `apps/potential_model/map_rendering.py:392-399`, `apps/potential_model/map_rendering.py:463`.

If a layer is selected for analysis but hidden in the map:

- The analysis selection remains in applied state.
- Source/buffer overlays are only materialized into `layers` when the separate "Visa källa i kartan" or "Visa buffert i kartan" control has been applied.
- Once the overlay exists in the map HTML, Leaflet's own checkbox can hide/show it without changing analysis state.

## 4. V2 Layer-Spec Contract

There is no strict dataclass for potential map layers. The contract is a Python dict consumed directly by `build_layered_hex_map_html()`.

Fields used by V2 renderer:

| Field | Meaning |
| --- | --- |
| `name` | User-facing overlay label in Leaflet layer control. |
| `control_name` | Optional user-facing name for auto-resolution layer families. |
| `feature_collection` | GeoJSON FeatureCollection embedded in the HTML. |
| `default_visible` | Initial overlay visibility if no localStorage override exists. |
| `source_layer_id` | Identity/dedupe key for source overlays. |
| `buffer_layer_id` | Identity/dedupe key for buffer overlays. |
| `layer_kind` | V2 renderer geometry/render type, usually `hex` or `vector`. This is not the semantic V3 kind. |
| `fill_property` | Feature property containing fill color. |
| `fill_color` | Fallback fill color. |
| `fill_opacity` | Fallback opacity. |
| `fill_opacity_property` | Feature property containing fill opacity. |
| `stroke_property` | Feature property containing stroke color. |
| `stroke_color` | Fallback stroke color. |
| `stroke_opacity` | Fallback stroke opacity. |
| `stroke_weight_property` | Feature property containing stroke width. |
| `stroke` | Explicit stroke enabled/disabled. |
| `weight` | Fallback stroke width. |
| `dash_array` | Leaflet dash array string. |
| `point_radius` | Fallback point radius for circle markers. |
| `point_radius_m_at_scale` | Optional meter-based point radius converted to pixels by zoom. |
| `point_min_radius`, `point_max_radius` | Bounds for scaled point radius. |
| `use_global_opacity` | Whether vector opacity slider should apply. |
| `z_index` | Leaflet pane z-index. |
| `legend_items` | Legend rows with label/color and optional shape. |
| `legend_id` | Dedupe/group id for legends. |
| `legend_title` | Legend section title. |
| `auto_resolution_group` | Groups several H3 resolution layers behind one Leaflet overlay. |
| `auto_resolution` | Resolution for an auto-family layer. |
| `selected_resolution` | Preferred/selected display resolution. |
| `lock_selected_resolution` | Disables automatic resolution switching. |
| `opacity_family`, `opacity_label` | Used by the advanced opacity controls outside the map. |

Examples are saved in:

- `exports/v3_migration/leaflet_layer_spec_examples.json`

## 5. Source/Buffer/Result Separation

V2 separates these concepts operationally, but not with one uniform semantic `layer_kind`.

| Concept | V2 representation | V3 recommendation |
| --- | --- | --- |
| Base layer | Hard-coded Leaflet tile layers `OSM` and `Satellite`. | Include as `layer_kind: "base"` or separate `base_layers`. |
| Result layer | Dict with `name`, GeoJSON, legend, `layer_kind: "hex"` or `vector`. | `layer_kind: "result"` plus `geometry_kind: "hex"` or `vector`. |
| Source layer | Dict with `source_layer_id`, name prefix `Sol källa:` or `Vind källa:`, usually `layer_kind: "vector"`. | `layer_kind: "source"`, keep `source_layer_id`. |
| Buffer layer | Dict with `buffer_layer_id`, name prefix `Solbuffert:` or `Vindbuffert:`, usually `layer_kind: "vector"`. | `layer_kind: "buffer"`, keep `source_layer_id`, `buffer_layer_id`, `distance_m`. |
| Overlay in layer control | Any non-base Leaflet layer added to `overlays`. | `is_overlay: true`. |
| Analysis layer not shown | Applied analysis inputs exist, but no source/buffer overlay is materialized unless visual controls are applied. | Build rendered layers only from applied visual/rendered snapshot. |

Important V3 principle:

- A selected analysis layer may be hidden in the map.
- "Visa källa i kartan" and "Visa buffert i kartan" should create separate overlays in `rendered_snapshot.layers`.
- Leaflet layer-control checkboxes should only change map visibility.
- The map must read applied/rendered state, not draft widget keys.

## 6. State Model And Interaction

V2 has two different visibility mechanisms:

1. Side-panel "show source/buffer" controls decide whether source/buffer overlays exist in the rendered map.
2. Leaflet layer-control checkboxes decide whether an existing overlay is visible.

Side-panel controls:

- Solar stores applied config in `SOLAR_APPLIED_CONFIG_KEY` (`potential_app.py:178`).
- Solar visual groups are stored as `visible_source_groups` and `visible_buffer_groups` (`potential_app.py:390-435`).
- Draft visual checkboxes use `_solar_visual_control_key()` and are copied into config only through `_solar_draft_config_from_session()` (`potential_app.py:4160-4188`, `potential_app.py:4385-4425`).
- The solar apply button copies draft into `SOLAR_APPLIED_CONFIG_KEY` and invalidates the render cache at `potential_app.py:12533-12552`.
- Wind visual controls are form checkboxes at `potential_app.py:8138-8148`.
- Wind visual groups are read by `_wind_visual_options_from_state()` at `potential_app.py:7910-7924`.
- Wind apply invalidates the workspace cache at `potential_app.py:8157-8165`.

Leaflet controls:

- Overlay visibility is held inside the iframe/Leaflet map and persisted in `window.localStorage`: `apps/potential_model/map_rendering.py:185-199`, `244-278`.
- `overlayadd` and `overlayremove` call `storeOverlayVisibility()` and update the legend; they do not call Streamlit: `apps/potential_model/map_rendering.py:622-648`.
- Pan/zoom are also UI-only map state stored on `moveend`/`zoomend`: `apps/potential_model/map_rendering.py:650-655`.
- V2 stores the last computed workspace payload in `WORKSPACE_RENDER_CACHE_KEY` and can reuse it for UI-only reruns: `potential_app.py:166-168`, `potential_app.py:11683-11705`, `potential_app.py:13457-13470`.

Comparison to V3 draft/applied/rendered_snapshot:

- V2's solar model already resembles V3: draft controls become applied config only on "Använd ändringar".
- V2's wind controls are inside a form and invalidate cache only when applied.
- V2's Leaflet layer toggles are even lighter than V3 state: they stay client-side and do not alter draft or applied.
- V3 should port this separation exactly.

## 7. UI/UX And CSS

Layer control:

- Position: Leaflet default `topright` because `L.control.layers(...)` is added with no custom position option.
- Collapsed by default: `{ collapsed: true }` at `apps/potential_model/map_rendering.py:619`.
- Icon/button: Leaflet's built-in layer-control toggle icon from the Leaflet CSS, not a custom icon.
- Open/close behavior: native Leaflet layer-control hover/click behavior depending on browser/device.
- Base layers: radio buttons from Leaflet.
- Overlays: checkboxes from Leaflet.
- Width/styling: V2 only sets basic font for `.leaflet-control-layers`; Leaflet supplies most panel layout. Custom CSS is at `apps/potential_model/map_rendering.py:159-168`.
- Notes and legends are separate Leaflet controls: map note top-right at `apps/potential_model/map_rendering.py:714-721`; legend bottom-right at `apps/potential_model/map_rendering.py:747-765`.

Labels:

- Result labels: `Potentiell etableringsyta`, `Scenariofördelning i etableringshex`, `Ytbehov utanför landskapets potential`.
- Source labels: `Sol källa: ...`, `Vind källa: ...`.
- Buffer labels: `Solbuffert: ...`, `Vindbuffert: ...`.

Technical fields:

- Leaflet layer control shows only the layer label.
- V2 can create debug rows with `typ`, `features`, `default`, `z` at `potential_app.py:3892-3905` and display them around `potential_app.py:13539-13543`.
- That debug table is outside the map and should not be part of V3's normal public UI.

For V3 politicians/tjänstepersoner:

- Do not show CRS, operation, cache key, feature count, native/render CRS, or data status in the map layer control.
- If debug is needed, keep it behind an explicit developer/debug mode.

## 8. Recommendation To V3

Recommended option: embed/port V2's custom Leaflet renderer as the V3 map component, then make it the main V3 map once stable.

Why:

- V2 already has the desired UX natively through `L.control.layers`.
- Leaflet supports base-layer radio buttons and overlay checkboxes without extra state plumbing.
- Overlay toggling does not trigger Streamlit rerun or analysis recomputation.
- GeoJSON result/source/buffer layers map cleanly to V2's renderer.
- The custom renderer is small and easier to reason about than folium-generated HTML.
- It fits V3's applied/rendered snapshot model: V3 can pass a frozen list of layers, and the map can keep visibility UI-only.

What to port directly:

- `build_layered_hex_map_html()` structure from `apps/potential_model/map_rendering.py:133-833`.
- Base-layer setup from `apps/potential_model/map_rendering.py:281-291`.
- `buildGeoJsonLayer()` style/tooltip/popup logic from `apps/potential_model/map_rendering.py:409-465`.
- `L.control.layers(..., { collapsed: true })` from `apps/potential_model/map_rendering.py:619`.
- localStorage view/overlay persistence if V3 wants map view continuity: `apps/potential_model/map_rendering.py:185-278`, `622-656`.
- Legend updating tied to overlay visibility: `apps/potential_model/map_rendering.py:723-804`.

What to avoid:

- Do not port V2's debug dataframes as end-user UI.
- Do not make the Leaflet layer-control write to V3 draft or applied state.
- Do not use V2's `layer_kind: "hex" | "vector"` as V3's semantic layer kind; rename it to `geometry_kind` or adapt it at the renderer boundary.
- Do not introduce folium/streamlit-folium unless V3 specifically wants to trade control over HTML/JS for a Python wrapper.
- Do not keep PyDeck as the primary V3 map if the required UX is V2 parity.

## 9. Minimum V3 Contract

V3 `rendered_snapshot.layers` should contain both user-facing display metadata and internal renderer metadata, but the layer-control UI should only use `label`.

Recommended fields:

| Field | Required | User-visible? | Notes |
| --- | --- | --- | --- |
| `layer_id` | yes | no | Stable identity. |
| `label` | yes | yes | Leaflet control label. |
| `layer_kind` | yes | no | Semantic: `base`, `result`, `source`, `buffer`. |
| `geometry_kind` | yes for overlays | no | Renderer hint: `hex`, `vector`, `tile`. |
| `default_visible` | yes | no | Initial checkbox/radio state. |
| `is_base_layer` | yes | no | True for OSM/Satellite. |
| `is_overlay` | yes | no | True for GeoJSON overlays. |
| `feature_collection` | yes if embedded | no | V2-compatible inline GeoJSON. |
| `geojson_path` | optional | no | Alternative for V3 if renderer can fetch/load. |
| `tile_url` | base only | no | Base-layer URL template. |
| `style` | yes for overlays | no | Contains V2 style fields. |
| `tooltip_fields` | optional | no | Usually `tooltip_title`, `tooltip_body`. |
| `popup_fields` | optional | no | Usually `popup`. |
| `z_index` | recommended | no | Leaflet pane order. |
| `group` | recommended | no | `result`, `source`, `buffer`, or domain grouping. |
| `technology_id` | recommended | no | `wind`, `solar`, `combined`. |
| `parameter_id` | recommended | no | E.g. `protected_buffer_m`. |
| `source_layer_id` | source/buffer | no | Source identity/provenance. |
| `buffer_layer_id` | buffer | no | Buffer identity/provenance. |
| `distance_m` | buffer | no | Buffer/proximity distance. |
| `legend_id` | optional | no | Legend grouping. |
| `legend_title` | optional | yes in legend | Human legend title. |
| `legend_items` | optional | yes in legend | Human legend rows. |
| `data_status` | optional internal | no | Never in standard layer control. |
| `native_crs`, `render_crs` | optional internal | no | Debug/provenance only. |
| `operation`, `cache_key`, `feature_count` | optional internal | no | Debug/provenance only. |

Minimal V3 shape:

```json
{
  "layer_id": "buffer:solar:protected:250",
  "label": "Solbuffert: Skyddad natur",
  "layer_kind": "buffer",
  "geometry_kind": "vector",
  "default_visible": true,
  "is_base_layer": false,
  "is_overlay": true,
  "source_layer_id": "solar:protected:protected_areas",
  "buffer_layer_id": "solar:protected:buffer:250:protected_areas",
  "distance_m": 250,
  "feature_collection": {"type": "FeatureCollection", "features": []},
  "style": {
    "fill_property": "fill",
    "fill_color": "#16a34a",
    "fill_opacity": 0.18,
    "stroke_color": "#16a34a",
    "stroke_opacity": 0.56,
    "weight": 0.75
  },
  "tooltip_fields": ["tooltip_title", "tooltip_body"],
  "popup_fields": ["popup"],
  "z_index": 458,
  "group": "buffer",
  "technology_id": "solar",
  "parameter_id": "protected_buffer_m"
}
```

## 10. V3 Test Cases

Suggested AppTest/block tests:

1. Render smoke: Bornholm, Trøndelag, and Skaraborg maps render without Streamlit exceptions.
2. Layer control exists inside the map iframe in the upper-right area with `.leaflet-control-layers`.
3. Layer control starts collapsed.
4. `OSM` and `Satellite` appear as base-layer radio options.
5. Only one base layer can be active at a time.
6. Result layers appear as overlay checkbox rows.
7. Applied source layers appear as separate overlay checkbox rows.
8. Applied buffer layers appear as separate overlay checkbox rows.
9. Leaflet overlay checkbox toggles change map visibility but do not change V3 draft state.
10. Leaflet overlay checkbox toggles do not change V3 applied state.
11. Draft side-panel changes do not alter `rendered_snapshot.layers` before `Använd ändringar`.
12. After `Använd ändringar`, `rendered_snapshot.layers` is rebuilt from applied state and the layer control updates.
13. A selected analysis source with source visibility off still affects analysis but does not create a source overlay row.
14. `Visa källa i kartan` creates a source overlay after apply.
15. `Visa buffert i kartan` creates a buffer overlay after apply.
16. Source and buffer overlays can be independently hidden/shown in Leaflet.
17. Technical fields such as CRS, operation, cache key, feature count, and data status do not appear in the layer-control text.
18. Legend content updates when overlay visibility changes.
19. Map pan/zoom and overlay visibility are UI-only and persist only under the map state key.
20. A new rendered snapshot can reset saved map view/overlay visibility through a reset token if V3 implements that part of V2.

## Migration Risks

- V2 embeds GeoJSON directly in the HTML. For very large V3 layers this can become heavy; V3 may need a `geojson_path` or tile strategy later.
- V2's `layer_kind` means geometry/render kind, while V3 needs semantic kind. Add an adapter instead of reusing the name blindly.
- Leaflet CDN use is simple but production V3 may prefer vendored/static assets for offline/stable deployment.
- V2 localStorage persistence is useful, but keys must include region/snapshot version so Bornholm, Trøndelag, and Skaraborg do not leak overlay visibility into each other.
- V2's debug layer rows are useful during development but should not be visible in V3's public workflow.
