# Potential Result Layers V3 Recommendation

Datum: 2026-06-09

Detta är rekommendationen baserad på V2-inventeringen i `potential_result_layers_inventory.md`.

## Portera direkt

Portera dessa beteenden:

- Leaflet layer control ska visa användarnära resultatlager: `Potentiell etableringsyta`, `Scenariofördelning i etableringshex`, och vid behov `Ytbehov utanför landskapets potential`.
- Legend ska baseras på synliga användarlager och uppdateras vid `overlayadd` / `overlayremove`.
- Overlay-toggle ska vara UI-only och får inte trigga ny analys.
- Baslagerbyte ska inte ändra zoom eller center.
- Kartvy ska vara separat browser/UI-state, inte en egenskap på resultatlagret.
- `fitBounds` får bara köras som initial fallback när ingen sparad view finns, eller efter explicit reset.
- Ett användarlager får ha flera render-varianter per upplösning, men layer control ska fortfarande visa ett enda användarnamn.

## Förenkla i V3

Förenkla V2:s interna modell:

- Gör `layer_kind` explicit: `source`, `buffer`, `result`.
- Lägg resultatspecar i `rendered_snapshot.layers`, inte i blandad Streamlit state.
- Låt widgets skriva till draft och låt `Använd ändringar` skapa en ny applied/rendered snapshot.
- Låt kartan läsa endast `rendered_snapshot`.
- Ersätt V2:s `auto_resolution_group`-fält med ett tydligare `render_variants`-kontrakt om zoomfamiljer behövs.
- Håll teknisk lagerstatus utanför huvud-UI. Lägg den i kontrakt, test eller debug-expander.

## Undvik

Undvik dessa V2-detaljer:

- Porta inte `build_potential_map_html()` eller `build_landscape_map_html()` som V3-resultatkarta. De är äldre single-layer helpers.
- Låt inte layer control visa source/buffer/result-teknikstatus, missing/empty/proxy-flaggor eller cache-detaljer.
- Lägg inte `rendered_snapshot_id`, layer-id eller visible overlay-set i map view key.
- Kör inte `fitBounds` efter varje render eller efter att visible overlays ändras.
- Låt inte draft/widgetkeys påverka kartan före apply.
- Låt inte opacity- eller overlay-toggle invalidiera resultatberäkningen.

## Föreslagen V3-modell

`rendered_snapshot.layers` bör ha resultatlager med dessa roller:

- `result.potential_establishment_area`: huvudresultat, default synligt.
- `result.scenario_allocation_hex`: scenariofördelning, togglebart och gärna släckt från start om många features.
- `result.outside_landscape_potential_need`: schematiskt bristlager, bara med när det finns brist.

Varje layer spec bör bära:

- `id`
- `label`
- `layer_kind: "result"`
- `result_type`
- `visible`
- `default_visible`
- `feature_collection` eller `data_ref`
- `cache_key`
- `style`
- `legend_group`
- `source` med härledning från applied snapshot

Kartvyn bör bära:

- `center`
- `zoom`
- `view_key`
- `reset_token`

Den ska inte bära:

- result layer cache key
- layer visibility set
- draft keys
- rendered snapshot id

## Rekommenderad eventmodell

Använd:

- `moveend`: spara center/zoom
- `zoomend`: spara center/zoom och synca eventuella zoomvarianter
- `overlayadd`: spara overlay visibility och uppdatera legend
- `overlayremove`: spara overlay visibility och uppdatera legend
- `baselayerchange`: endast spara baslagerval om V3 vill ha det

Använd inte dessa events för view:

- `overlayadd`
- `overlayremove`
- `baselayerchange`

## Rekommenderad fitBounds-regel

V3 bör följa denna ordning:

1. Om sparad view finns för regionens map key: `setView(saved.center, saved.zoom)`, ingen `fitBounds`.
2. Annars: `setView(defaultCenter, defaultZoom)`.
3. Om regionen har default bounds: initial `fitBounds(defaultBounds)`.
4. Annars: initial fit till stabila snapshot-bounds, inte till just synliga overlays.
5. Efter initial fit: spara view.

Vid apply i samma region:

- bygg ny `rendered_snapshot`
- byt lagerdata
- bevara view
- kör inte ny fit om saved view finns

Vid regionbyte:

- använd ny region-scopad view key
- använd sparad view för regionen om den finns
- annars default center/zoom och initial fit

## Föreslagna AppTest/blocktest

1. `test_result_overlay_toggle_does_not_change_view`
   - Rendera `result.potential_establishment_area`.
   - Sätt karta till känd center/zoom.
   - Toggle result layer av/på.
   - Assert: center/zoom oförändrade.

2. `test_scenario_allocation_toggle_does_not_change_view`
   - Rendera etableringsyta plus scenariofördelning.
   - Toggle `result.scenario_allocation_hex`.
   - Assert: ingen `fitBounds`, `setView`, `flyTo` eller `panTo`.

3. `test_base_layer_toggle_does_not_change_view`
   - Byt OSM/Satellite.
   - Assert: center/zoom oförändrade.

4. `test_apply_same_region_updates_result_layers_but_preserves_view`
   - Spara view för Skaraborg.
   - Ändra draft och tryck `Använd ändringar`.
   - Assert: `rendered_snapshot.layers` får ny cache_key/applied_hash.
   - Assert: view-key är oförändrad och saved view används.

5. `test_draft_change_does_not_update_result_map`
   - Ändra en draft-widget.
   - Assert: `rendered_snapshot` och kartlager är oförändrade före apply.

6. `test_result_cache_key_does_not_reset_map_view`
   - Byt result layer cache key inom samma region.
   - Assert: localStorage view key ändras inte.

7. `test_overlay_visibility_is_separate_from_view`
   - Toggle scenariofördelning av.
   - Panorera kartan.
   - Rendera om samma snapshot.
   - Assert: overlay visibility och view återställs från separata keys.

8. `test_initial_fit_only_when_no_saved_view`
   - Tom localStorage: initial fit får köras.
   - Sparad view: initial fit returnerar utan att ändra view.

9. `test_large_scenario_allocation_defaults_hidden`
   - Rendera scenariofördelning med feature_count över tröskel.
   - Assert: lagret finns i layer control men är släckt från start.

10. `test_debug_status_not_in_main_layer_control`
    - Rendera source, buffer och result layers.
    - Assert: layer control visar användarnära labels.
    - Assert: missing/proxy/cache/data_status inte visas som egna huvudrader.

## Portningsregel i en mening

V3 bör porta V2:s användarbeteende för resultatlager, men ersätta V2:s interna widget/cache/layer-dict-blandning med ett tydligt `rendered_snapshot.layers`-kontrakt där resultatlager och kartvy är separata saker.
