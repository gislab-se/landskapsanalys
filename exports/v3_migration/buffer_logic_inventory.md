# V2 -> V3 inventory: buffertlogik och första analyskoppling

Inventering utförd i V2-repot 2026-06-09. Syftet är att hitta metodlogik som V3 kan porta till en explicit `draft -> applied -> rendered_snapshot`-modell, inte att kopiera V2:s Streamlit-implementation rakt av.

## Kort Slutsats

V2 har en användbar metodmodell:

- Parametergrupper har en analyssemantik: `hard_exclusion`, `distance_conflict` eller `proximity_feasibility`.
- Source layers och buffer/group layers hålls separata i både UI och kartlager.
- Buffertgeometri skapas i meter-CRS, dissolvas till gruppgeometrier och exporteras till GeoJSON/EPSG:4326 för karta.
- Analysen använder antingen verklig runtime-geometri eller distanstabeller/H3-share frames som fallback/snabbväg.

V3 bör porta semantiken och cache-/runtime-idén, men göra state-kontraktet explicit: draft ändrar inte buffert, karta eller analys förrän `Använd ändringar` skapar en ny applied state och rendered snapshot.

## 1. Buffertskapande

### Generisk geometri-runtime

Den generiska buffertvägen körs via Python-wrapper och R-script:

- `run_geometry_runtime(config_json)` i `apps/acceptance_model/runtime_geometry.py:45-87`.
- Cache/revision token bygger på config, R-scriptets mtime och aktivt registry i `apps/acceptance_model/runtime_geometry.py:32-42`.
- Runtime-katalogen ligger under `docs/geocontext/acceptance_framework/data/prototype_runtime` i `apps/acceptance_model/runtime_geometry.py:16-22`.
- R-scriptet är `script/acceptance/render_wind_acceptance_geometry_runtime.R`.

R-runtimen:

- läser registry, layer config och assetmanifest i `script/acceptance/render_wind_acceptance_geometry_runtime.R:23-28`;
- väljer `working_epsg` från `registry$native_crs_epsg`, annars fallback `32633`, i `script/acceptance/render_wind_acceptance_geometry_runtime.R:28`;
- läser landmask och dissolvar den med `st_union` i `script/acceptance/render_wind_acceptance_geometry_runtime.R:120-146`;
- läser lager antingen från `analysis_rds_path` i assetmanifest eller från source path i registry/lagerconfig i `script/acceptance/render_wind_acceptance_geometry_runtime.R:215-249`;
- transformerar lager till `working_epsg` före buffer i `script/acceptance/render_wind_acceptance_geometry_runtime.R:222-244`;
- applicerar eventuella registryfilter innan buffert/clip i `script/acceptance/render_wind_acceptance_geometry_runtime.R:245-248`;
- förenklar och exporterar till EPSG:4326 i `script/acceptance/render_wind_acceptance_geometry_runtime.R:252-258`.

### CRS

V2-kontraktet är regionstyrt:

- Trøndelag acceptance registry sätter `"native_crs_epsg": 25832` i `apps/acceptance_model/registry_trondelag.json:7`.
- Trøndelag region/landscape-manifest har `native_crs: EPSG:25832` i `apps/potential_model/manifests/regions/trondelag.json:6` och `apps/potential_model/manifests/landscape/trondelag_landscape_placeholder.json:6`.
- Bornholm region/landscape-manifest har `native_crs: EPSG:25833` i `apps/potential_model/manifests/regions/bornholm.json:6`, `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json:5` och `apps/potential_model/manifests/landscape/bornholm_landscape_v4.json:5`.

Viktig V3-not: R-runtimens generiska fallback är `32633` om registry saknar `native_crs_epsg`. V3 ska inte kopiera den fallbacken som produktregel. V3 bör kräva explicit native CRS per region: Bornholm `EPSG:25833`, Trøndelag `EPSG:25832`, och endast export/render i `EPSG:4326`.

### Dissolve och kombination

R-runtimen gör dissolve på flera nivåer:

- `single_feature_polygonal()` extraherar polygoner och `st_union`-dissolvar dem i `script/acceptance/render_wind_acceptance_geometry_runtime.R:112-118`.
- `prepare_layer_geometry()` unionerar source-lagrets geometrier med `st_union(st_geometry(layer_sf))`, klipper till landmask och buffrar i `script/acceptance/render_wind_acceptance_geometry_runtime.R:301-329`.
- Flera valda lager i samma grupp kombineras med `combine_geometries()` och sedan `single_feature_polygonal()` i `script/acceptance/render_wind_acceptance_geometry_runtime.R:357-386`.
- Gruppens `role` sätts till `feasible` för `proximity_feasibility`, annars `conflict`, i `script/acceptance/render_wind_acceptance_geometry_runtime.R:386-394`.
- Kombinerad acceptansyta blir feasibility-intersection minus conflict-union, eller landmask minus conflict-union om inga feasibility-grupper finns, i `script/acceptance/render_wind_acceptance_geometry_runtime.R:431-455`.

Detta är direkt portabelt som V3-metod:

```text
combined = intersection(feasible_groups) - union(conflict_groups)
if no feasible groups:
    combined = landmask - union(conflict_groups)
```

### Trøndelag population proxy

Trøndelag har en specialväg för population/settlement eftersom datan är en 250 m grid/centroid-proxy, inte individuella befolkningspunkter.

- RDS-källa pekas ut i `_trondelag_population_proxy_rds_path()` i `potential_app.py:5083-5084`.
- Cachefilen skrivs per bufferavstånd i `_trondelag_population_buffer_cache_path()` i `potential_app.py:5091-5097`.
- R-scriptet körs via `_load_trondelag_population_buffer_geojson()` i `potential_app.py:5101-5127`.
- Layer buildern `_trondelag_population_buffer_polygon_layer()` skapar ett kartlager med explicit proxy-not i `potential_app.py:5147-5188`.

R-scriptet:

- transformerar population proxy till EPSG:25832 före buffer i `script/acceptance/render_trondelag_population_buffer.R:28`;
- dissolvar geometrier med `st_union` i `script/acceptance/render_trondelag_population_buffer.R:36`;
- kör `st_buffer(..., dist = buffer_m)` i `script/acceptance/render_trondelag_population_buffer.R:39`;
- förenklar med `st_simplify(..., dTolerance = 10)` i `script/acceptance/render_trondelag_population_buffer.R:45`;
- exporterar till EPSG:4326 i `script/acceptance/render_trondelag_population_buffer.R:57`.

V3 bör porta detta som region-specific buffer adapter för Trøndelag settlement/population. Visa det som upplöst polygonbuffer från 250 m proxy, inte H3-buffer.

### Multi-layer och proxy-lager

Multi-layer hanteras genom att varje grupp har flera `active_layer_ids`.

- Registry datamodellerna `GroupSpec` och `SourceLayerSpec` finns i `apps/acceptance_model/layers.py:21-45`.
- Validering/normalisering av valda lager sker i `normalize_group_layer_map()` i `apps/potential_model/wind_acceptance.py:113-121`.
- Vinds runtime-config skriver `active_layer_ids` och `analysis_value_m` per grupp i `_wind_runtime_config_json()` i `potential_app.py:11119-11134`.
- Solens aktiva filterconfigs byggs med `group_id`, `layer_ids`, `buffer_m` och `effect` i `_solar_active_filter_configs()` i `potential_app.py:4230-4247`.
- Solens runtime-config för filtergrupper skickar samma form till geometri-runtimen i `_solar_filter_runtime_result()` i `potential_app.py:5394-5413`.

Proxyer är inte dolda i V2; de dokumenteras i registry och assetmanifest. Exempel:

- Trøndelag `population_points` är `polygon_proxy_from_250m_centroids` i assetmanifestet med meddelandet att det är en 250 m occupied grid-cell polygon derived from centroids.
- `built_low_selection` är fritidshus/holiday-house centroid proxy.
- Reindrift är Trøndelag-specifik och har ingen Bornholm-motsvarighet.

V3 bör bära vidare `data_status`/`proxy_type` till lagerkatalogen och UI-status.

### Tomma eller osäkra lager

V2 är defensivt:

- `load_asset_manifest()` returnerar en tom tabell med statuskolumner om manifest saknas i `apps/acceptance_model/layers.py:166-185`.
- `source_geojson_for_layer()` returnerar `None` om manifest, rad eller `geojson_path` saknas i `apps/acceptance_model/layers.py:247-257`.
- `distance_table_for_layer()` returnerar tom distanstabell om path saknas i `apps/acceptance_model/layers.py:271-280`.
- `_wind_layer_is_ready()` kräver `geojson_ready`, `source_exists`, `feature_count > 0` och `status == "ok"` i `potential_app.py:7974-7981`.
- `_solar_filter_layer_options()` för vidare `ready` och `message` till UI i `potential_app.py:5368-5387`.
- `_wind_group_controls()` disablar grupper/lager utan ready assets och visar captions i `potential_app.py:8053-8057` samt `potential_app.py:8110-8118`.
- Missing-region-kontroller visas disabled i `potential_app.py:12153-12177`.

V3 bör porta statuskontraktet men göra det datadrivet i lagerkatalogen: tomt lager ska ge `status: empty|missing|experimental`, inte en trasig karta.

## 2. Source Layers vs Buffer Layers

### Namngivning

V2 skiljer source och buffer med både displaynamn och interna id:n.

Sol:

- Source: `Sol källa: ...`, t.ex. `_solar_population_source_layer()` i `potential_app.py:5028-5056` och `_solar_filter_source_layers()` i `potential_app.py:5284-5340`.
- Buffer: `Solbuffert: ...` eller `Sol nära nät: ...`, byggt i `_solar_filter_buffer_layer()` i `potential_app.py:5665-5725`.
- Intern source-id: `source_layer_id = "solar:{...}"`, se `potential_app.py:5041` och `potential_app.py:5322`.
- Intern buffer-id: `buffer_layer_id = "solar:{group_id}:buffer:{buffer_m}:{layer_ids}"` i `potential_app.py:5705-5709`.

Vind:

- Source: `Vind källa: ...`, byggt i `_wind_polygon_source_layers()` i `potential_app.py:8299-8393`.
- Buffer/group: `Vindbuffert: ...` eller `Vind nära nät: ...`, byggt i `_wind_filter_buffer_layer()` i `potential_app.py:5728-5805` och `_wind_polygon_group_layers()` i `potential_app.py:8396-8443`.
- Intern source-id: `source_layer_id = "wind:{layer_id}"` i `potential_app.py:8389`.
- Intern buffer-id: `buffer_layer_id = "wind:{group_id}:buffer:{analysis_value}"` i `potential_app.py:8412-8416`, eller mer detaljerat i `_wind_filter_buffer_layer()` i `potential_app.py:5782-5787`.

### Styling

Source layers:

- använder source-färg från `SourceLayerSpec.source_color` eller solens `source_color`;
- har typiskt högre stroke och lägre fill-opacitet;
- är `layer_kind: "vector"`;
- är normalt `default_visible: False`, utom Trøndelag population source för vind som kan vara default-visible i `potential_app.py:8372-8381`.

Exempel:

- Sol population source: stroke opacity `0.85`, fill opacity `0.28`, point radius från layer spec i `potential_app.py:5037-5055`.
- Sol filter source: stroke opacity `0.82`, fill opacity `0.22`, z-index `456` i `potential_app.py:5319-5338`.
- Vind source: stroke opacity från `_wind_source_opacity()`, fill opacity `opacity * 0.28`, weight `2.0` i `potential_app.py:8373-8390`.

Buffer layers:

- använder grupp-/bufferfärg;
- har låg fill opacity och egen legend;
- `use_global_opacity: False`;
- `default_visible: False` i de generiska bufferlagren.

Exempel:

- Sol buffer: stroke opacity `0.56`, fill opacity `0.18`, z-index `458` i `potential_app.py:5704-5725`.
- Vind buffer: stroke opacity `0.56`, fill opacity `0.18`, z-index `459` i `potential_app.py:5782-5803`.
- Vind polygon group layer: stroke opacity `opacity * 0.95`, fill opacity `opacity * 0.32`, weight `2.2` i `potential_app.py:8417-8441`.
- Trøndelag population polygon buffer har egen styling och proxy-not i `potential_app.py:5162-5188`.

### Synlighet och session/applied keys

Sol:

- `visible_source_groups` och `visible_buffer_groups` är applied config-fält (`SOLAR_VISUAL_SOURCE_GROUPS_KEY`, `SOLAR_VISUAL_BUFFER_GROUPS_KEY`) i `potential_app.py:390-391`.
- Draft-widgetkeys skapas som `solar_draft_visual_{source|buffer}__{group_id}` i `potential_app.py:4160-4165`.
- Draft kopieras till applied vid `Använd ändringar` enligt interaktionsinventeringen.
- Kartbygget läser applied via `_solar_visual_enabled(applied_solar_config, kind, group_id)` i `potential_app.py:12797-12813`.

Vind:

- Widgetkeys är `wind_control__visual_source__{group_id}` och `wind_control__visual_buffer__{group_id}` via `_wind_control_key()` i `potential_app.py:7906-7907`.
- `_wind_visual_options_from_state()` samlar aktiva source/buffer groups i `potential_app.py:7910-7924`.
- Kontrollerna finns i vindformuläret i `potential_app.py:8138-8148`.
- `_wind_polygon_preview_state()` lägger bara till source/buffer layers när gruppen finns i `source_group_ids`/`buffer_group_ids` i `potential_app.py:10886-10939`.

V3 bör göra vindens visibility lika explicit som solens: draft visibility -> apply -> applied `layer_visibility` -> rendered snapshot.

## 3. Valda lager + avstånd till analys

### Wind/acceptance semantik

Registry anger gruppens `analysis_kind`, defaultavstånd och färg. Se `apps/acceptance_model/registry_trondelag.json:8-151` och Bornholm registry i `apps/acceptance_model/registry.json`.

V2:s H3/distanstabellsanalys:

- `_group_distance_frame()` tar minsta avstånd och `any_intersection` över alla valda lager i gruppen i `apps/potential_model/wind_acceptance.py:147-191`.
- `distance_conflict`: för nära är dåligt; acceptance rampas från 0 vid threshold till 1 vid ca 2x threshold i `apps/potential_model/wind_acceptance.py:194-207`.
- `proximity_feasibility`: nära är bra; utanför maxavstånd blockeras i `apps/potential_model/wind_acceptance.py:210-220`.
- `hard_exclusion`: intersection eller avstånd <= buffer blockerar helt i `apps/potential_model/wind_acceptance.py:223-233`.
- `_acceptance_for_kind()` dispatchar dessa tre i `apps/potential_model/wind_acceptance.py:236-246`.
- Gruppacceptance kombineras med min över aktiva grupper; hard-blocking sätter wind_score till 0 i `apps/potential_model/wind_acceptance.py:330-348`.

V2:s Trøndelag fast-distance path gör samma semantik direkt i `potential_app.py`:

- `_acceptance_series_for_group()` i `potential_app.py:8931-8953`.
- `_wind_fast_distance_runtime_result()` hämtar distanstabeller, tar min distance/any intersection och kombinerar med min i `potential_app.py:8989-9060`.

### Solsemantik

Solens stora etableringspotential använder samma parameterlager, men med ett enklare areal-share-kontrakt.

- Solfiltergrupper finns i `SOLAR_FILTER_GROUP_SPECS` i `potential_app.py:219-357`.
- `_solar_active_filter_configs()` materialiserar `group_id`, `layer_ids`, `buffer_m` och `effect` från applied config i `potential_app.py:4230-4247`.
- `_solar_filter_union_buffer_frame()` unionerar buffer/share över aktiva filter och faller tillbaka till distanstabeller när runtime-GeoJSON saknas i `potential_app.py:5600-5662`.
- `_solar_large_scale_frame()` delar aktiva filter i exclusion och feasibility i `potential_app.py:5891-5901`.
- Exclusion minskar `potential_area_share_pct` med `protected_buffer_share_pct` i `potential_app.py:5902-5915`.
- Feasibility multiplicerar kvarvarande potential med `feasibility_share_pct / 100` i `potential_app.py:5916-5933`.
- Resultatet blir area, score och klass per hex i `potential_app.py:5935-5966`.

Analysoperationer:

- `effect != "feasibility"`: avdrag/hard exclusion på share-nivå.
- `effect == "feasibility"`: positiv mask/inclusion inom avstånd, främst elinfrastruktur/nät.
- Population för storskalig sol är exclusion.
- Land use/skog i V2 är exclusion för storskalig sol, inte generell inclusion.

### Distanstabellfallback

När riktig buffer-GeoJSON inte finns kan V2 approximera share via distanstabeller:

- `_distance_table_filter_share_frame()` läser `distance_table_for_layer()`, hanterar olika `geometry_family` för line/point/polygon och aggregerar max share per hex i `potential_app.py:5478-5552`.
- För line/point cap:ar V2 teoretisk andel av cellen baserat på buffer och cellarea i `potential_app.py:5503-5523`.
- För polygon/övrigt används intersection eller proximity share i `potential_app.py:5524-5530`.

V3 bör porta idén som fallback, men märka resultatet som `approximation` i status/snapshot. För juridiska/planeringskritiska overlaylager bör verklig geometri prioriteras.

## 4. Portera, Förenkla, Ersätt, Undvik

### Portera Direkt

- Analyssemantiken `hard_exclusion`, `distance_conflict`, `proximity_feasibility`.
- Gruppkombinationen: feasible intersection minus conflict union; annars landmask minus conflict union.
- Multi-layer per parametergrupp med `active_layer_ids`.
- Source/buffer separation i layer specs och UI.
- Runtime-cache keyed på config + registry/script/source revision.
- Statuskontrakt för lager: ready kräver source, geojson, feature_count och status `ok`.
- Trøndelag population buffer som dissolvad polygon från 250 m proxy i EPSG:25832.

### Förenkla

- Gör ett gemensamt V3-kontrakt för sol och vind:

```text
ParameterGroupConfig:
  parameter_id
  selected_layer_ids
  operation
  distance_m
  source_visible
  buffer_visible
```

- Flytta styling till V3-lagerkatalogen i stället för hårdkodade funktionsblock.
- Gör `layer_role` explicit: `source`, `buffer`, `combined_result`, `analysis_only`.
- Gör `data_status` explicit: `real`, `proxy`, `synthetic`, `placeholder`, `experimental`, `missing`, `empty`.
- Låt `rendered_snapshot` bära `buffer_status` och `analysis_semantics`.

### Ersätt

- Ersätt vindens implicit form-state med explicit `draft.wind.parameter_groups` och `applied.wind.parameter_groups`.
- Ersätt R-runtimens CRS-fallback `32633` med obligatoriskt region-CRS från V3 regionmanifest.
- Ersätt spridda source/buffer layer builders med en gemensam layer-spec factory som tar `LayerCatalogEntry + AppliedParameterState + BufferResult`.

### Undvik

- Att karta eller analys läser draft/widgetkeys direkt.
- Att exponera buffer overlays som H3 om de ska vara verklig geometri, särskilt Trøndelag population.
- Att tyst hoppa över saknad GeoJSON utan status.
- Att blanda `source_visible` med `selected_for_analysis`: ett lager kan vara analysaktivt men dolt på karta.
- Att behandla Trøndelag proxydata som individuella befolkningspunkter.
- Att kopiera V2:s `32633` fallback till Bornholm.

## 5. Rekommenderade V3-Testfall

### Apply-gräns

1. Ändra draft bufferavstånd för en parametergrupp utan apply.
   - Förväntat: `applied` oförändrad, `rendered_snapshot.layers` oförändrad, dirty-status visas.
2. Tryck `Använd ändringar`.
   - Förväntat: ny applied version, ny buffer cache key, nytt/uppdaterat buffer layer i snapshot.

### Source och buffer separat

3. Välj ett lager för analys, men lämna source/buffer visibility av.
   - Förväntat: analysen påverkas efter apply, men source/buffer saknas i renderade layer specs.
4. Slå på bara source visibility och applicera.
   - Förväntat: source layer finns, buffer layer saknas.
5. Slå på bara buffer visibility och applicera.
   - Förväntat: buffer layer finns, source layer saknas.

### Tomma/saknade lager

6. Simulera `feature_count = 0` eller `status != ok`.
   - Förväntat: UI visar status, checkbox disabled eller validation blockerar apply; karta kraschar inte.
7. Simulera saknad buffer GeoJSON men befintlig distanstabell.
   - Förväntat: analys kan använda fallback om tillåtet, snapshot märks `approximation`.

### CRS

8. Bornholm bufferjobb ska använda EPSG:25833 för metergeometri.
9. Trøndelag bufferjobb ska använda EPSG:25832 för metergeometri.
10. Alla render/export GeoJSON ska vara EPSG:4326.

### Semantik

11. `hard_exclusion`: intersection eller avstånd <= buffer tar bort potential.
12. `distance_conflict`: nära lager reducerar acceptance; utanför rampen är acceptance 1.
13. `proximity_feasibility`: yta utanför maxavstånd till el/nät är ej genomförbar.
14. Multi-layer i samma grupp använder min distance/any intersection och max/union för buffer-share, inte additiv dubbelräkning.
15. Feasibility-grupper kombineras med intersection och conflict-grupper subtraheras.

## V3-Kontrakt Att Sikta På

```text
draft.parameter_groups[group_id].selected_layer_ids
draft.parameter_groups[group_id].distance_m
draft.layer_visibility.source_group_ids
draft.layer_visibility.buffer_group_ids

apply:
  validate draft against layer catalog and region CRS
  normalize selected_layer_ids
  create applied parameter state
  compute buffer jobs from applied only
  build rendered_snapshot from applied only
```

V3:s första analyskoppling behöver inte återskapa hela V2:s etableringsmodell direkt. Den bör börja med en tydlig och testad kontraktkedja:

```text
selected layers + operation + distance_m
  -> buffer job / distance fallback
  -> analysis mask/share
  -> rendered source/buffer/result layers
```
