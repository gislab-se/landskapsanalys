# Potential Result Layers Inventory For V3

Datum: 2026-06-09

Syfte: inventera hur V2 bygger, uppdaterar och renderar resultatlager i potentialkartan, utan att ändra V2-appens beteende.

## Kort slutsats

V2:s resultatkarta är en egen Leaflet-renderer byggd som HTML/JS och monterad i Streamlit via `st.iframe` eller `streamlit.components.v1.html`. Den använder inte Folium, pydeck eller Streamlits native mapkomponent för resultatkartan.

De användarnära resultatlagren i gemensam potentialvy är:

- `Potentiell etableringsyta`
- `Scenariofördelning i etableringshex`
- `Ytbehov utanför landskapets potential`

V2 skiljer inte strikt på `source | buffer | result` i layer-kontraktet. Resultatlager är i praktiken lager med användarnära labels, `layer_kind: "hex"`, computed GeoJSON och legend. Source/buffer-lager är oftare `layer_kind: "vector"` och namnges som källa eller buffert. V3 bör göra denna skillnad explicit i kontraktet.

## Teknik i V2

Primär karta:

- `potential_app.py:44` importerar `build_layered_hex_map_html`
- `potential_app.py:7433` `_render_html_map(...)`
- `potential_app.py:7447` `_render_layers(...)`
- `apps/potential_model/map_rendering.py:133` `build_layered_hex_map_html(...)`

Rendering:

- V2 bygger en HTML-sträng med Leaflet 1.9.4.
- HTML renderas med `st.iframe` om tillgängligt, annars `components.html`.
- Leaflet-lager byggs från Python-genererade layer specs och `feature_collection`.

Kodreferenser:

- `potential_app.py:7433` väljer `st.iframe` eller `components.html`
- `potential_app.py:7462` anropar `build_layered_hex_map_html(...)`
- `apps/potential_model/map_rendering.py:174` laddar Leaflet JS
- `apps/potential_model/map_rendering.py:415` bygger `L.geoJSON(...)`
- `apps/potential_model/map_rendering.py:619` skapar `L.control.layers(...)`

Gamla helpers som V3 bör undvika:

- `apps/potential_model/map_rendering.py:7` `build_landscape_map_html(...)`
- `apps/potential_model/map_rendering.py:836` `build_potential_map_html(...)`

De är single-layer helpers med egen `fitInitialBounds()` och utan samma view-persistensmodell som den gemensamma layered potentialkartan. De är inte rätt portningskälla för V3:s resultatlager.

## Resultatlagerlabels

Labels definieras centralt:

- `potential_app.py:188` `COMBINED_ESTABLISHMENT_LAYER_LABEL = "Potentiell etableringsyta"`
- `potential_app.py:189` `SCENARIO_ALLOCATION_LAYER_LABEL = "Scenariofördelning i etableringshex"`
- `potential_app.py:196` `OUTSIDE_LP_NEED_LAYER_LABEL = "Ytbehov utanför landskapets potential"`

Tutorial/guide använder samma labels för att hitta legendsektioner:

- `potential_app.py:994`
- `potential_app.py:1004`
- `potential_app.py:1015`

## Hur resultat byggs

### Energimodell och ytbehov

Energimodellen läser scenario och AreaDemand:

- `potential_app.py:3151` `_render_energy_modeling_panel(...)`
- `potential_app.py:3165` `_cached_energy_inputs(...)`
- `potential_app.py:3166` `_cached_area_demand(...)`
- `potential_app.py:3186` state key `energy_model_planning_scenario_<region_id>`
- `potential_app.py:3214` state key `energy_model_area_scenario_<region_id>`
- `potential_app.py:3268` `calculate_area_demand(...)`

V2:s energiwidgets skriver direkt till Streamlit session state. Det är användarbeteende i V2, inte en V3-princip att porta. V3 bör låta widgets skriva till draft och bara låta kartan läsa applied/rendered snapshot.

### Solens scenarioyta

Solens etableringsförslag byggs i:

- `potential_app.py:6175` `_solar_establishment_frame(...)`
- `potential_app.py:6259` prioriterar kandidater med `_apply_landscape_priority_to_allocation_frame(...)`
- `potential_app.py:6415` `_expand_solar_area_outside_lp(...)`
- `potential_app.py:12946` skapar `solar_proposal_frame`
- `potential_app.py:12965` expanderar utanför landskapspotential vid brist
- `potential_app.py:12975` sparar `energy_model_state["solar_proposal_frame"]`
- `potential_app.py:12976` sparar `energy_model_state["solar_proposal_stats"]`

Resultatet är en DataFrame med bland annat:

- `hex_id`
- `potential_area_km2`
- `allocated_area_km2`
- `allocated_twh`
- `allocated_hex_share_pct`
- prioriteringsfält
- eventuell `outside_et`

### Vindens scenarioyta

Vindens etableringsförslag byggs i:

- `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)`
- `potential_app.py:13066` `_apply_landscape_priority_to_allocation_frame(...)`
- `potential_app.py:13072` `_apply_social_acceptance_priority_to_wind_allocation_frame(...)`
- `potential_app.py:13079` `allocate_wind_area_from_core_hexes(...)`
- `potential_app.py:13086` `_expand_wind_area_outside_et(...)`
- `potential_app.py:13106` sparar `energy_model_state["proposal_frame"]`
- `potential_app.py:13107` sparar `energy_model_state["proposal_stats"]`

### Gemensam potentiell etableringsyta

Den gemensamma potentialytan kombinerar vindpotential, solpotential och scenarioallokering:

- `potential_app.py:9441` `_combined_establishment_class(...)`
- `potential_app.py:9463` `_apply_establishment_style_columns(...)`
- `potential_app.py:9478` `_combined_establishment_frame(...)`
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`
- `potential_app.py:10486` `_combined_establishment_feature_collection(...)`
- `potential_app.py:10583` `_combined_establishment_layer(...)`
- `potential_app.py:10652` `_combined_potential_establishment_family_layers(...)`

Klassningen är:

- `wind_and_solar`
- `wind_only`
- `solar_only`
- `not_suitable`

Färger:

- `potential_app.py:2308` `ESTABLISHMENT_CLASS_SPECS`
- `potential_app.py:9246` `_combined_establishment_legend_items()`

Layer spec för själva lagret:

- `potential_app.py:10591` `name`
- `potential_app.py:10592` `feature_collection`
- `potential_app.py:10593` `fill_property = "fill"`
- `potential_app.py:10594` `fill_opacity_property = "fill_opacity"`
- `potential_app.py:10595` `stroke_property = "stroke"`
- `potential_app.py:10596` `stroke_weight_property = "stroke_weight"`
- `potential_app.py:10597` legend items
- `potential_app.py:10598` `legend_id = "combined_establishment"`
- `potential_app.py:10600` `default_visible = True`
- `potential_app.py:10605` `z_index = 476`
- `potential_app.py:10606` `layer_kind = "hex"`

Kartan lägger till lagret här:

- `potential_app.py:13186` bygger `combined_establishment_layers`
- `potential_app.py:13199` testar om lager finns
- `potential_app.py:13201` `layers.extend(combined_establishment_layers)`

### Scenariofördelning / etableringshex

Scenariofördelningen visar scenariots placering som mindre child-hex.

Byggfunktioner:

- `potential_app.py:10269` `SCENARIO_ALLOCATION_SPECS`
- `potential_app.py:10291` `_scenario_allocation_class(...)`
- `potential_app.py:10309` `_scenario_allocation_child_cell(...)`
- `potential_app.py:10325` `_scenario_allocation_marker_feature_collection(...)`
- `potential_app.py:10418` `_scenario_allocation_marker_layer(...)`
- `potential_app.py:10454` `_scenario_allocation_marker_family_layers(...)`

V2 väljer child cell med target resolution + 1 där det går. Färgen visar:

- vind
- sol
- vind och sol, om båda tekniker faktiskt behöver samma scenariohex

Layer spec:

- `potential_app.py:10430` `name`
- `potential_app.py:10431` `feature_collection`
- `potential_app.py:10432` `fill_property = "fill"`
- `potential_app.py:10433` `fill_opacity_property = "fill_opacity"`
- `potential_app.py:10436` legend items
- `potential_app.py:10440` `legend_id = "scenario_allocation"`
- `potential_app.py:10441` `legend_title`
- `potential_app.py:10442` default visible-regel
- `potential_app.py:10447` `z_index = 540`
- `potential_app.py:10448` `layer_kind = "hex"`

Default visibility:

- Trøndelag sätts explicit till av från start: `potential_app.py:10465`
- Annars är lagret synligt bara om `target_resolution <= 9` och `feature_count <= 12000`: `potential_app.py:10442`

Kartan lägger till lagret här:

- `potential_app.py:13213` bygger `allocation_marker_layers`
- `potential_app.py:13221` testar om lager finns
- `potential_app.py:13222` `layers.extend(allocation_marker_layers)`

### Ytbehov utanför landskapets potential

Detta är ett schematiskt resultatlager. Det visar mängd ytbehov utanför landskapets potential, inte verklig placering.

Byggfunktioner:

- `potential_app.py:10069` `_outside_lp_need_feature_collection(...)`
- `potential_app.py:10188` `_outside_lp_need_layer(...)`
- `potential_app.py:10225` `_outside_lp_need_family_layers(...)`

Layer spec:

- `potential_app.py:10201` `name`
- `potential_app.py:10202` `feature_collection`
- `potential_app.py:10203` `fill_property = "fill"`
- `potential_app.py:10204` `fill_opacity_property = "fill_opacity"`
- `potential_app.py:10207` legend items
- `potential_app.py:10211` `legend_id = "outside_lp_need"`
- `potential_app.py:10213` `default_visible = True`
- `potential_app.py:10218` `z_index = 486`
- `potential_app.py:10219` `layer_kind = "hex"`

Kartan lägger till lagret här:

- `potential_app.py:13231` bygger `outside_lp_need_layers`
- `potential_app.py:13241` testar om lager finns
- `potential_app.py:13242` `layers.extend(outside_lp_need_layers)`

## Zoomfamiljer och layer control

V2 bygger resultatlagren som zoomfamiljer när zoomanpassad visning är aktiv:

- `potential_app.py:4621` `_hex_family_layers(...)`
- `potential_app.py:4645` sätter tekniskt namn `"<control_name> R<resolution>"`
- `potential_app.py:4646` sätter `control_name`
- `potential_app.py:4647` sätter `auto_resolution_group`
- `potential_app.py:4648` sätter `auto_resolution`
- `potential_app.py:4649` sätter `selected_resolution`
- `potential_app.py:4650` sätter `lock_selected_resolution`

I Leaflet visas bara `control_name` i layer control:

- `apps/potential_model/map_rendering.py:481` läser `auto_resolution_group`
- `apps/potential_model/map_rendering.py:483` skapar `autoFamilies`
- `apps/potential_model/map_rendering.py:607` lägger familjens controller i overlays
- `apps/potential_model/map_rendering.py:608` `overlays[family.controlName] = family.controller`

Vid zoom väljer V2 rätt upplösning i samma familj:

- `apps/potential_model/map_rendering.py:544` `autoResolutionFromScale(...)`
- `apps/potential_model/map_rendering.py:583` `syncAutoFamily(...)`
- `apps/potential_model/map_rendering.py:651` `zoomend`
- `apps/potential_model/map_rendering.py:652` syncar auto-familjer

Detta är en V2-optimering. V3 kan porta iden "ett användarlager kan ha flera render-varianter", men bör göra det explicit i `rendered_snapshot.layers[].render_variants` eller liknande i stället för att exponera flera tekniska lager.

## Leaflet-rendering

Alla specs blir `L.geoJSON`:

- `apps/potential_model/map_rendering.py:409` `buildGeoJsonLayer(...)`
- `apps/potential_model/map_rendering.py:415` `L.geoJSON(spec.feature_collection, ...)`
- `apps/potential_model/map_rendering.py:417` stylefunktion
- `apps/potential_model/map_rendering.py:428` `fillColor`
- `apps/potential_model/map_rendering.py:429` `fillOpacity`
- `apps/potential_model/map_rendering.py:453` tooltips och popups

Style läses från properties eller fallback i spec:

- `apps/potential_model/map_rendering.py:311` `layerFillOpacity(...)`
- `apps/potential_model/map_rendering.py:324` `layerFillColor(...)`
- `apps/potential_model/map_rendering.py:332` `layerStrokeColor(...)`
- `apps/potential_model/map_rendering.py:340` `layerStrokeWeight(...)`

## Legend och kartlagerkontroll

Layer control:

- `apps/potential_model/map_rendering.py:619` `L.control.layers({ 'OSM': osm, 'Satellite': satellite }, overlays, { collapsed: true })`

Legend:

- `apps/potential_model/map_rendering.py:477` samlar lager med `legend_items`
- `apps/potential_model/map_rendering.py:723` legend state
- `apps/potential_model/map_rendering.py:746` skapar Leaflet legend control
- `apps/potential_model/map_rendering.py:768` `updateLegendContent()`
- `apps/potential_model/map_rendering.py:779` visar bara legendsektioner för synliga overlays

Layer control visar användarnära namn (`control_name`) för zoomfamiljer. Teknisk datastatus visas inte i layer control.

Teknisk debug finns i V2, men i avancerade ytor:

- `potential_app.py:3892` `_map_layer_debug_rows(...)`
- `potential_app.py:13365` sparar `energy_model_state["map_layer_debug_rows"]`
- `potential_app.py:13539` visar debug rows i avancerad panel

V3 bör hålla detta utanför huvud-UI enligt principen: teknisk status hör hemma i kontrakt, test och debug.

## Skillnad mot source layers och buffer layers

V2:s source/buffer-lager byggs i separata funktioner, till exempel:

- `potential_app.py:5028` `_solar_population_source_layer(...)`
- `potential_app.py:5284` `_solar_filter_source_layers(...)`
- `potential_app.py:5665` `_solar_filter_buffer_layer(...)`
- `potential_app.py:5728` `_wind_filter_buffer_layer(...)`
- `potential_app.py:8224` `_wind_source_vector_layers(...)`

De renderas tekniskt i samma Leaflet-renderer, men de har andra labels och ofta `layer_kind: "vector"`.

Resultatlager är däremot computed outputs från potential-/scenarioflödet och använder `layer_kind: "hex"` i V2:

- `potential_app.py:10219` outside LP
- `potential_app.py:10448` scenario allocation
- `potential_app.py:10606` combined establishment

V3 bör inte gissa layer roll från `layer_kind`. V3 bör ha explicit:

- `layer_kind: "source" | "buffer" | "result"`
- `result_type`, exempelvis `potential_establishment_area` eller `scenario_allocation`

## State, cache och localStorage

### Streamlit state och cache

V2 har en workspace-cache:

- `potential_app.py:168` `WORKSPACE_RENDER_CACHE_KEY = "potential_workspace_render_cache_v2"`
- `potential_app.py:2220` `_workspace_calculation_fingerprint(...)`
- `potential_app.py:2246` docstring: UI language exkluderas
- `potential_app.py:2280` `_cached_workspace_payload(...)`
- `potential_app.py:2289` `_invalidate_workspace_cache(...)`
- `potential_app.py:13457` sparar workspace-cache

Cache-payload innehåller:

- `fingerprint`
- `layers`
- `note_body`
- `performance_log`
- `energy_model_state`
- `map_state`

Se:

- `potential_app.py:13457`
- `potential_app.py:13459`
- `potential_app.py:13462`
- `potential_app.py:13463`

UI-only rerun:

- `potential_app.py:166` `UI_ONLY_RERUN_KEY`
- `potential_app.py:2202` `_request_ui_only_rerun(...)`
- `potential_app.py:2207` `_ui_only_rerun_requested()`
- `potential_app.py:11674` `_render_reused_workspace_outputs(...)`
- `potential_app.py:11694` caption: återanvänder beräknad karta och potential
- `potential_app.py:11695` renderar cached layers

Opacity:

- `potential_app.py:3557` `_opacity_key(...)`
- `potential_app.py:3569` `_hex_opacity_key(...)`
- `potential_app.py:3598` `_hex_opacity_controls(...)`
- `potential_app.py:3634` `_apply_layer_opacity_state(...)`

Opacityändring är UI-only och ska inte köra ny potentialberäkning.

### Browser localStorage

Leaflet-renderern sparar view och overlay visibility i browsern:

- `apps/potential_model/map_rendering.py:185` `browserStorage()`
- `apps/potential_model/map_rendering.py:199` `storageKey(kind)`
- `apps/potential_model/map_rendering.py:200` `regional-energy-potential:<mapStateKey>:<kind>`
- `apps/potential_model/map_rendering.py:220` `readSavedView()`
- `apps/potential_model/map_rendering.py:244` `readSavedOverlayVisibility()`
- `apps/potential_model/map_rendering.py:262` `storeMapView()`
- `apps/potential_model/map_rendering.py:622` `storeOverlayVisibility()`

`map_state_key` skickas från V2 så här:

- `potential_app.py:157` `MAP_STATE_VERSION = "establishment-start-v6"`
- `potential_app.py:13431` `map_state_key=f"{region_id}:workspace:{MAP_STATE_VERSION}"`
- `potential_app.py:13432` `map_reset_token=map_reset_token`

Normal key blir:

```text
regional-energy-potential:<region_id>:workspace:establishment-start-v6:view
regional-energy-potential:<region_id>:workspace:establishment-start-v6:overlays
regional-energy-potential:<region_id>:workspace:establishment-start-v6:reset-token
```

Viktigt: view-key är inte scopad per resultatlager eller snapshot. Den är region/workspace-scopad.

## Kartvy och fitBounds

View init:

- `apps/potential_model/map_rendering.py:277` `savedView`
- `apps/potential_model/map_rendering.py:279` `mapStartCenter`
- `apps/potential_model/map_rendering.py:280` `mapStartZoom`
- `apps/potential_model/map_rendering.py:281` `setView(...)`

`fitBounds`:

- `apps/potential_model/map_rendering.py:808` `fitInitialBounds()`
- `apps/potential_model/map_rendering.py:810` returnerar direkt om `savedView` finns
- `apps/potential_model/map_rendering.py:815` fit till `defaultBounds`
- `apps/potential_model/map_rendering.py:819` fallback till alla `renderedLayers`
- `apps/potential_model/map_rendering.py:826` körs en gång via timeout

Det betyder:

- Resultatlager får bytas eller uppdateras utan att view nollställs, om saved view finns.
- Overlay toggle kör inte `fitBounds`.
- Baslagerbyte kör inte `fitBounds`.
- Ny applied/beräknad karta i samma region bevarar view via samma localStorage-key.

## overlayadd / overlayremove

Overlay-events:

- `apps/potential_model/map_rendering.py:632` `overlayadd`
- `apps/potential_model/map_rendering.py:641` `overlayremove`

De gör:

- syncar auto-resolution family
- sparar overlay visibility
- uppdaterar legend

De gör inte:

- ny Python-analys
- Streamlit state update
- `fitBounds`
- `setView`

Kod:

- `apps/potential_model/map_rendering.py:638` `storeOverlayVisibility()`
- `apps/potential_model/map_rendering.py:639` `updateLegendContent()`
- `apps/potential_model/map_rendering.py:647` `storeOverlayVisibility()`
- `apps/potential_model/map_rendering.py:648` `updateLegendContent()`

V2 har också en JS-helper för tutorial/guide:

- `apps/potential_model/map_rendering.py:674` `setOverlayVisibilityByName(...)`
- `apps/potential_model/map_rendering.py:698` `window.__potentialMapSetOverlayVisibility`

Även den är klient-side och triggar inte ny analys.

## Vad V3 bör ta med

Portera beteende:

- Resultatlager ska komma från applied/rendered snapshot.
- Layer control visar användarnära resultatlager.
- Overlay toggle är UI-only.
- Legend följer synliga användarlager.
- Kartvy är separat UI-state.
- `fitBounds` körs bara initialt när ingen sparad view finns.

Ersätt implementation:

- V2:s blandning av widget state, cache och karta ska ersättas av V3:s draft/applied/rendered snapshot.
- V2:s implicit result/source/buffer-skillnad ska ersättas av explicit `layer_kind`.
- V2:s auto-resolution fields kan ersättas av ett tydligare `render_variants`-kontrakt om V3 behöver zoomfamiljer.
