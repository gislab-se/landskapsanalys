# V2 -> V3 inventory: interaktionsmodell

Inventering utförd i V2-repot 2026-06-09. Radreferenserna pekar på aktuell arbetskopia och kan flytta sig vid senare editering.

## Kort slutsats

V2 har redan den modell V3 bör ha för sol: widgets skriver till draft-state, `Använd ändringar` kopierar draft till applied-state, och karta/resultatpanel läser applied. För vind är modellen praktiskt likadan för användaren, men tekniskt svagare: Streamlit-formulärets batching används som draft-gräns och det finns ingen separat `wind_applied_config`. För V3 bör detta göras explicit.

Karta, analys och högerpanel bör i V3 läsa en gemensam applicerad analys-snapshot. Widgetändringar ska bara göra snapshoten "dirty/stale" tills användaren trycker `Använd ändringar`.

## 1. Draft vs applied state

### Sol

Sol har en tydlig draft/applied-separering.

- Applied-state ligger i `st.session_state["solar_applied_config"]`, definierad som `SOLAR_APPLIED_CONFIG_KEY` i `potential_app.py:178`.
- Defaultvärden finns i `DEFAULT_SOLAR_APPLIED_CONFIG` i `potential_app.py:394-436`.
- Applied-state läses och normaliseras i `_solar_config_from_session()` i `potential_app.py:4329-4357`.
- Draft-state skapas från applied i `_prime_solar_draft_state(config)` i `potential_app.py:4360-4383`.
- Draft läses ihop till config i `_solar_draft_config_from_session()` i `potential_app.py:4385-4425`.
- I workspace startas flödet med `applied_solar_config = _solar_config_from_session()` och `_prime_solar_draft_state(applied_solar_config)` i `potential_app.py:12371-12372`.

Viktiga draft-keys:

- `solar_draft_small_population_active`
- `solar_draft_large_population_active`
- `solar_draft_area_m2_per_person`
- `solar_draft_population_buffer_m`
- `solar_draft_{group_id}_active`
- `solar_draft_{group_id}_buffer_m`
- `solar_draft_{group_id}_layer__{layer_id}`
- `solar_draft_protected_layer__{layer_id}`
- `solar_draft_visual_{source|buffer}__{group_id}`

Draft skapas när workspace renderas och `_prime_solar_draft_state()` körs. Funktionen använder `setdefault`, vilket betyder att befintlig draft inte skrivs över av en ny applied config. Det är bra för användarens pågående ändringar, men är lätt att missbruka vid regionbyte eller extern reset. V3 bör använda en explicit draft-version eller `draft_origin_applied_version`.

### Vind

Vind har en användarmässigt applicerad modell, men inte en lika ren state-modell.

- Persistent valda lager ligger i `st.session_state["wind_builder_selected_layers"]`, definierad i `potential_app.py:176`.
- `_selected_wind_layers()` normaliserar och skriver tillbaka selection i `potential_app.py:7890-7898`.
- Widgetkeys byggs av `_wind_control_key(prefix, item_id)` i `potential_app.py:7906-7907`.
- `_wind_group_controls()` renderar ett `st.form`, vilket gör att slider- och checkboxändringar hålls i formuläret tills submit i `potential_app.py:8029-8171`.
- Vid submit skrivs normaliserat urval till `WIND_LAYER_SELECTION_KEY`, cache invaliders och `WIND_EMPTY_SELECTION_ACTIVE_KEY` sätts i `potential_app.py:8157-8163`.
- UI-parametrar för analys läses från `wind_control__analysis__{group_id}` i `potential_app.py:8165-8170`.

Det här fungerar eftersom `st.form` batchar widgetvärden, men efter submit finns inget separat objekt som heter `wind_applied_config`. V3 bör inte porta den implicitheten. Gör i stället vind symmetrisk med sol: `wind_draft_config` och `wind_applied_config`.

### Reset och regionbyte

Regionens start/default-state hanteras i `_ensure_default_start_state(region, force=False)` i `potential_app.py:4088-4135`.

Funktionen:

- använder versionsnyckeln `potential_start_default_version_{region_id}` i `potential_app.py:4088-4091`;
- applicerar vindreferens/default i `potential_app.py:4092-4096`;
- sätter `solar_applied_config` till default i `potential_app.py:4097-4098`;
- sätter H3-display till `current`/R7 i `potential_app.py:4104-4105`;
- döljer landskap och social acceptans initialt i `potential_app.py:4109-4113`;
- skriver även sol-draftkeys från default i `potential_app.py:4114-4133`.

Workspace-anropet kör `_ensure_default_start_state(region)` tidigt i `_unified_workspace_tab()` i `potential_app.py:12347-12352`. Det gör regiondefaulten reproducerbar, men V3 bör samla reset i en typad funktion som nollställer både draft, applied, cache och stale-status för aktiv region.

## 2. `Använd ändringar`

### Sol

Solpanelen är tydligast. Användaren får en caption om att ändringar bara slår igenom efter `Använd ändringar` i `potential_app.py:12451-12455`.

Vid submit i solformuläret:

- scenariokompatibla gamla keys synkas i `potential_app.py:12535-12548`;
- workspace-cache invaliders med `_invalidate_workspace_cache("solar controls applied")` i `potential_app.py:12549`;
- draft kopieras till applied: `st.session_state[SOLAR_APPLIED_CONFIG_KEY] = _solar_draft_config_from_session()` i `potential_app.py:12550`;
- flaggan `solar_controls_applied` sätts i `potential_app.py:12551`;
- appen rerunnas i `potential_app.py:12552`.

Karta, analys och högerpanel uppdateras först efter apply eftersom de läser `applied_solar_config`, inte draft.

### Vind

Vind använder `st.form` som apply-gräns:

- formulär och controls finns i `potential_app.py:8029-8157`;
- submitknappen ligger i `potential_app.py:8157`;
- på submit skrivs normaliserad selection till `WIND_LAYER_SELECTION_KEY` i `potential_app.py:8159-8160`;
- cache invaliders i `potential_app.py:8161`;
- tomt val markeras i `WIND_EMPTY_SELECTION_ACTIVE_KEY` i `potential_app.py:8162-8163`.

Karta och analys uppdateras efter form-submit, eftersom formwidgets inte skickar delvärden till scriptet innan submit. Det finns dock ingen explicit dirty/stale-status för osparade formulärändringar på serversidan.

### Status för ej tillämpade ändringar

V2 har ingen central `draft != applied`-status. I stället bygger beteendet på Streamlit-formulär: innan submit har servern inte de nya värdena. Efter submit visas captions som `controls_applied` eller `solar_controls_applied`.

För UI-only ändringar finns ett separat flöde:

- `UI_ONLY_RERUN_KEY`, `UI_ONLY_RERUN_REASON_KEY` och `WORKSPACE_RENDER_CACHE_KEY` definieras i `potential_app.py:166-168`;
- `_request_ui_only_rerun()`, `_ui_only_rerun_requested()` och `_clear_ui_only_rerun()` finns i `potential_app.py:2202-2217`;
- `_workspace_calculation_fingerprint()` avgör om analysen behöver räknas om i `potential_app.py:2220-2277`;
- cache läses/invaliders i `potential_app.py:2280-2293`;
- UI-only rerun återanvänder workspace-cache om fingerprint matchar i `potential_app.py:12685-12699`;
- snapshoten sparas i `potential_app.py:13457-13477`.

V3 bör behålla fingerprint/cachestrategin men lägga till en explicit `has_unapplied_changes = hash(draft) != applied.source_draft_hash`.

## 3. Karta

### Vilka source layers visas?

Source layers kommer från asset registry och assetmanifest:

- rätt registry väljs per region i `apps/acceptance_model/layers.py:52-56`;
- registry läses till `GroupSpec` och `SourceLayerSpec` i `apps/acceptance_model/layers.py:70-96`;
- source GeoJSON hämtas via assetmanifest i `source_geojson_for_layer()` i `apps/acceptance_model/layers.py:247-256`.

Sol:

- befolkningssource hämtas i `_solar_population_source_layer()` i `potential_app.py:5028-5056`;
- övriga source layers byggs i `_solar_filter_source_layers()` i `potential_app.py:5284-5339`;
- source-visibility styrs av applied config via `_solar_visual_enabled(applied_solar_config, "source", group_id)` i kartbygget i `potential_app.py:12790-12865`.

Vind:

- source layers byggs i `_wind_polygon_source_layers()` i `potential_app.py:8299-8393`;
- `source_group_ids` kommer från `_wind_visual_options_from_state()` i `potential_app.py:7910-7937`;
- previewen lägger in source layers när gruppen är aktiv och visual-source är vald i `potential_app.py:10886-10892`.

### Vilka buffer layers visas?

Sol:

- buffer layers skapas via `_solar_filter_buffer_layer()` i `potential_app.py:5665-5725`;
- Trøndelag befolkning har särskild polygonbuffer i `_trondelag_population_buffer_polygon_layer()` i `potential_app.py:5147-5188`;
- buffer-visibility styrs av applied config via `visible_buffer_groups`.

Vind:

- `_wind_filter_buffer_layer()` bygger bufferlager för vind i `potential_app.py:5728-5786`;
- `_wind_polygon_preview_state()` lägger på Trøndelag fast-distance-bufferlager i `potential_app.py:10893-10914`;
- Trøndelag settlement/population får upplöst befolkningsbuffer i `potential_app.py:10915-10936`;
- övriga grupp-/bufferlager läggs till via `_wind_polygon_group_layers()` i `potential_app.py:8396-8443` och `potential_app.py:10937-10939`.

### Vilka lager går till renderern?

Alla färdiga lager specs samlas i `layers` och skickas till `_render_layers()` i `potential_app.py:13427-13438`. `_render_layers()` anropar `build_layered_hex_map_html()` i `potential_app.py:7447-7476`.

Leaflet-renderern tar bara emot de redan avgjorda layer specs:

- `build_layered_hex_map_html(layers, center, zoom, ...)` definieras i `apps/potential_model/map_rendering.py:133-153`;
- GeoJSON layers byggs i Javascriptfunktionen `buildGeoJsonLayer()` i `apps/potential_model/map_rendering.py:409-477`;
- overlay-state hanteras i kartkontrollen i `apps/potential_model/map_rendering.py:628-684`.

### Skillnad mellan UI-val och renderad karta

Ja. För sol är skillnaden tydlig och avsiktlig:

- valda filterlager kan användas i analys även om source/buffer är dolda;
- texten i `_render_solar_filter_control()` säger detta explicit i `potential_app.py:4451`;
- renderad karta läser applied visibility, inte draft visibility.

För vind finns samma separation begreppsligt: selection och visual source/buffer är separata widgetgrupper. Men V2 blandar widgetkeys och applied-liknande state, så V3 bör modellera detta som separata fält i applied config:

- `selected_layer_ids`
- `analysis_values_m`
- `visible_source_group_ids`
- `visible_buffer_group_ids`

### Flera aktiva tekniker eller grupper samtidigt

Workspace bygger sol- och vindlager separat och lägger ihop dem i samma `layers`-lista. Solens aktiva filterkonfigurationer hämtas från applied i `potential_app.py:4199-4247` och `potential_app.py:12415-12421`. Vindens preview byggs via `_wind_polygon_preview_state()` och läggs till i huvudflödet i `potential_app.py:12990-13065`.

V3 bör behålla "många aktiva grupper samtidigt" som första klassens modell och undvika en global single-active-layer-flagga.

## 4. Buffertar

### Var skapas buffertgeometri?

Generisk vind-/acceptansgeometri:

- Python-wrappern `run_geometry_runtime(config_json)` finns i `apps/acceptance_model/runtime_geometry.py:45-87`;
- den kör `script/acceptance/render_wind_acceptance_geometry_runtime.R`;
- runtime-cache nycklas på config plus revision token från script och registry i `apps/acceptance_model/runtime_geometry.py:32-42`.

R-runtime:

- registry väljer `working_epsg` från `native_crs_epsg` i `script/acceptance/render_wind_acceptance_geometry_runtime.R:28`;
- geometrier transformeras till working CRS i `script/acceptance/render_wind_acceptance_geometry_runtime.R:124-144` och `script/acceptance/render_wind_acceptance_geometry_runtime.R:222-244`;
- buffert skapas med `st_buffer(..., dist = buffer_distance_m)` i `script/acceptance/render_wind_acceptance_geometry_runtime.R:301-321`;
- metadata/lager exporteras till 4326 via helpern runt `script/acceptance/render_wind_acceptance_geometry_runtime.R:258`.

Trøndelag population:

- population proxy ligger i `docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/analysis_rds/population_points.rds`, se `potential_app.py:5083-5084`;
- cachefil skrivs under `docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/runtime_buffers/` i `potential_app.py:5091-5097`;
- R-scriptet körs från `_load_trondelag_population_buffer_geojson()` i `potential_app.py:5101-5127`;
- R-scriptet transformerar till EPSG:25832 före buffert i `script/acceptance/render_trondelag_population_buffer.R:28`;
- `st_buffer` körs i EPSG:25832 i `script/acceptance/render_trondelag_population_buffer.R:38-39`;
- resultatet förenklas och exporteras till EPSG:4326 i `script/acceptance/render_trondelag_population_buffer.R:43-58`.

### Live eller först efter apply?

Solbuffertar skapas från applied config och ändras först efter `Använd ändringar`. Vindbuffertar skapas efter form-submit, eftersom runtime får de submit:ade widgetvärdena. UI-only ändringar ska inte skapa om buffertar; cache/fingerprint skyddar detta.

### Avståndsändring utan apply

För sol ligger ändringen i draft och påverkar inte analys/karta. För vind ligger ändringen i Streamlit-formuläret och skickas inte till servern före submit. V3 bör representera detta explicit med draft/applied och dirty-status.

### Saknad geometri

V2 gör flera defensiva fallbackar:

- `source_geojson_for_layer()` returnerar `None` när asset saknas i `apps/acceptance_model/layers.py:247-256`;
- `_solar_filter_buffer_geojson()` returnerar `None` om runtime saknar gruppgeojson i `potential_app.py:5423-5433`;
- `_solar_filter_union_buffer_frame()` faller tillbaka till distanstabellsbaserad share-frame om geometrisk buffer saknas i `potential_app.py:5623-5638`;
- Trøndelag population buffer layer returnerar `None` om GeoJSON saknas eller saknar features i `potential_app.py:5156-5160`.

V3 bör visa en icke-blockerande lagerstatus och fortsätta analysen med tydligt markerad fallback när det är metodmässigt korrekt.

## 5. Resultat och analys

### Läser resultatpanelen draft eller applied?

Resultatpanelen läser beräknad `map_state`/snapshot, inte draft.

- `_combined_summary(map_state, scenario_state)` börjar i `potential_app.py:11728`.
- Geografisammanfattningen läser `map_state` i `_render_geography_user_summary()` i `potential_app.py:4039-4052`.
- Högerpanelen renderas efter kartbygget och får samma `layers`, `potential_frames`, `energy_model_state`, `geography_filter_notes` och `geography_effect_notes` som kartan i `potential_app.py:13479-13582`.
- Vid UI-only rerun används `_render_reused_workspace_outputs(cache, ...)` i `potential_app.py:11676-11718`, vilket återanvänder senaste beräknade karta och högerpanel.

### Finns central analysis_state?

Inte som typad datamodell. Närmast är:

- `WORKSPACE_RENDER_CACHE_KEY = "potential_workspace_render_cache_v2"` i `potential_app.py:168`;
- fingerprinten i `_workspace_calculation_fingerprint()` i `potential_app.py:2220-2277`;
- cachepayloaden som sparas i `potential_app.py:13457-13477`, med `layers`, `note_body`, `performance_log`, `energy_model_state` och `map_state`.

V3 bör skapa en explicit `AppliedAnalysisState` och en `RenderedAnalysisSnapshot`.

### Aktiva filter och stale-signal

Sammanfattningar av aktiva filter byggs på flera ställen:

- geografiska filternoter i `_geography_filter_notes()` i `potential_app.py:3927-3998`;
- effekt-/energinoter i `_geography_effect_notes()` i `potential_app.py:4001-4026`;
- solfilter i `_solar_active_filter_configs()` i `potential_app.py:4199-4247`;
- högerpanelens summaries i `_combined_summary()` och panelblocket i `potential_app.py:11728-12024` samt `potential_app.py:13479-13582`.

Det finns ingen central stale-signal för `draft != applied`. V3 bör lägga till den och visa t.ex. "Ej tillämpade ändringar" när draft skiljer sig från applied.

## 6. Koddelar att porta, förenkla och undvika

### Bör porteras till V3

- Solens explicita draft/applied-kontrakt: `_solar_config_from_session()`, `_prime_solar_draft_state()`, `_solar_draft_config_from_session()` och applyflödet i `potential_app.py:4329-4425` samt `potential_app.py:12451-12552`.
- Fingerprint/cache-idén: `_workspace_calculation_fingerprint()`, `_cached_workspace_payload()` och `_invalidate_workspace_cache()` i `potential_app.py:2220-2293`.
- UI-only rerun för panelbredd, opacitet och liknande visuella ändringar i `potential_app.py:2202-2217`, `potential_app.py:2412-2469` och `potential_app.py:3590-3645`.
- Asset registry och source lookup: `apps/acceptance_model/layers.py:52-96` och `apps/acceptance_model/layers.py:247-256`.
- Runtime geometry cache: `apps/acceptance_model/runtime_geometry.py:32-87`.
- Trøndelag population-buffer som upplöst 250 m grid/centroid-proxy, med EPSG:25832-beräkning och EPSG:4326-export: `potential_app.py:5083-5188` och `script/acceptance/render_trondelag_population_buffer.R:28-58`.
- Renderer-kontraktet där kartan får färdiga layer specs och inte själv beslutar analyslogik: `potential_app.py:7447-7476` och `apps/potential_model/map_rendering.py:133-153`.

### Bör förenklas i V3

- Gör sol och vind symmetriska: `technology_draft_config` och `technology_applied_config`.
- Ersätt utspridda session keys med namespacade stateobjekt per region, t.ex. `interaction.draft.trondelag.wind`.
- Ersätt `setdefault`-baserad draft priming med explicit `draft_origin_applied_version`.
- Samla source-/buffer-visibility i en typad `LayerVisibilityState`.
- Samla kartans renderade snapshot och högerpanelens analysdata i en typad `RenderedAnalysisSnapshot`.
- Gör social acceptans antingen explicit live eller explicit draft/apply. V2:s workspace-kontroller i `potential_app.py:12580-12631` är live och sticker ut från huvudmodellen.

### Bör undvikas i V3

- Att låta `st.form` vara den enda definitionen av draft/applied för vind.
- Att karta eller högerpanel läser widgetkeys direkt.
- Att duplicera gamla builder-keys och nya unified workspace-keys utan adapter.
- Att blanda analysis-state, render-cache och UI-only state i samma session namespace.
- Att exponera Trøndelag-befolkningsbuffer som H3-overlay. V2:s handlingslinje och repo-instruktionen pekar på upplöst polygonbuffer från 250 m proxy.
- Att behandla saknade source GeoJSON som tyst "tom analys"; visa lagerstatus eller fallback-not.

## Edge cases att testa i V3

- Draft ändras men apply trycks inte: karta, analys och högerpanel ska vara oförändrade och visa dirty-status.
- Apply trycks efter bufferavståndsändring: ny buffergeometri och resultatpanel ska uppdateras i samma applied snapshot.
- Source layer synlighet ändras utan apply: renderad karta ska inte ändras före apply.
- Aktivt filterlager används i analys även när source/buffer visibility är av.
- Flera solfilter och vindgrupper är aktiva samtidigt.
- Inga vindlager är valda: appen ska följa en tydlig default/empty-selection-regel och inte krascha.
- Trøndelag population buffer saknar cache: runtime ska skapa EPSG:25832-buffer och exportera 4326.
- Trøndelag population source saknas: UI ska visa saknat lager och inte visa falsk buffer.
- Panelbredd, kartopacitet och språkändring ska återanvända cache när calculation fingerprint är oförändrat.
- Regionbyte ska resetta eller rebasera draft/applied och cache för ny region.
- Social acceptans ska antingen vara live by design eller omfattas av samma apply-gräns.
- Render-cache får bara återanvändas när fingerprint matchar.

## Konkreta AppTest-fall för V3

1. Starta Trøndelag workspace och verifiera att applied H3-display är R7/current och att R9 inte exponeras.
2. Ändra `solar.draft.population_buffer_m`, kör rerun utan apply och verifiera att map snapshot och right-panel snapshot fortfarande har gammalt applied-värde.
3. Tryck `Använd ändringar` för sol och verifiera att `solar.applied.population_buffer_m` uppdateras, dirty-status försvinner och cache invaliders.
4. Kryssa i ett solfilterlager men lämna source/buffer-visibility av; verifiera att analysen använder lagret efter apply men att source/buffer inte visas på kartan.
5. Ändra vindens settlement-buffer i draft utan apply; verifiera att `wind.applied.analysis_values_m` inte ändras.
6. Applicera vindändring och verifiera att runtime-cache key ändras när bufferavstånd eller layer_ids ändras.
7. Slå på vind source layer visibility, applicera, och verifiera att source layer finns i renderade layer specs.
8. Slå på vind buffer visibility för Trøndelag settlement/population och verifiera att layer spec är upplöst polygonbuffer med proxy-not, inte H3.
9. Simulera saknad GeoJSON för ett source layer och verifiera att checkbox/lagerstatus visar saknad datakälla utan krasch.
10. Ändra bara opacitet/panelbredd och verifiera att calculation fingerprint är oförändrat och att senaste snapshot återanvänds.
11. Byt region och verifiera att draft/applied/cache är namespacade eller reset till regiondefault.
12. Ändra social acceptans enligt vald V3-modell och verifiera antingen live-uppdatering med egen märkning eller draft/apply-beteende.
