# V3 recommendation: interaktionsmodell

## Rekommenderad modell

V3 bör göra V2:s bästa beteende explicit:

1. Alla widgets skriver till draft-state.
2. Karta, analys och högerpanel läser bara applied-state eller en rendered snapshot byggd från applied-state.
3. `Använd ändringar` validerar draft, normaliserar lagerurval, kopierar draft till applied, räknar ny fingerprint, invalidrar relevant cache och bygger ny snapshot.
4. UI-only ändringar, som panelbredd, lageropacitet och kartvy, ska inte ändra applied analysis state.

Föreslagen state-struktur:

```text
InteractionState
  region_id
  draft
    solar
    wind
    social_acceptance
    layer_visibility
  applied
    solar
    wind
    social_acceptance
    layer_visibility
    version
    source_draft_hash
  rendered_snapshot
    applied_fingerprint
    layers
    map_state
    right_panel_state
    energy_model_state
    notes
  ui
    panels
    opacity
    map_view
    language
```

`has_unapplied_changes` bör vara en ren jämförelse mellan normaliserad draft och `applied.source_draft_hash`.

## Modell per område

### Draft/applied

Porta solens modell från V2. Den är tydlig och redan nära V3:

- applied config: `potential_app.py:4329-4357`
- draft priming: `potential_app.py:4360-4383`
- draft -> applied vid submit: `potential_app.py:12451-12552`

Ändra vind från implicit form-state till samma kontrakt:

- dagens formulärflöde finns i `potential_app.py:8029-8171`;
- `wind_builder_selected_layers` i `potential_app.py:176` och `potential_app.py:7890-7898` bör ersättas av `wind_applied_config.selected_layer_ids_by_group`;
- `wind_control__analysis__{group_id}` bör bli `wind_draft_config.analysis_values_m[group_id]`.

### Apply boundary

`Använd ändringar` ska vara enda gränsen för analysändringar. Vid apply:

- normalisera draft;
- validera regionens regler, t.ex. Trøndelag R7/R6/R5 och EPSG:25832 för metergeometri;
- skriv applied;
- uppdatera `applied.version`;
- invalidra render/analysis cache;
- bygg eller markera ny snapshot.

Efter apply ska kartan och högerpanelen uppdateras tillsammans. V3 bör undvika partiella tillstånd där kartan visar ny applied men högerpanelen gammal analys.

### Karta och lager

Behåll renderer-kontraktet från V2: kart-renderern får färdiga layer specs och ska inte känna till analyslogik.

Bra kod att återanvända eller översätta:

- `build_layered_hex_map_html()` i `apps/potential_model/map_rendering.py:133-153`
- `_render_layers()` i `potential_app.py:7447-7476`
- asset registry och `source_geojson_for_layer()` i `apps/acceptance_model/layers.py:52-96` och `apps/acceptance_model/layers.py:247-256`

I V3 bör source- och buffer-visibility vara applied state om det ändrar renderad karta. Ett valt filterlager kan fortfarande användas i analys även om dess source/buffer overlay är dold.

### Buffertar

Buffertberäkning ska vara keyed och cachebar:

```text
buffer_cache_key = region_id + group_id + sorted(layer_ids) + distance_m + source_revision + native_crs
```

Trøndelag-regeln ska vara hård:

- metergeometri i EPSG:25832;
- export/renderformat i EPSG:4326;
- population/settlement visas som upplöst polygonbuffer från 250 m grid/centroid-proxy, inte som H3-overlay.

Kod att återanvända:

- `apps/acceptance_model/runtime_geometry.py:32-87`
- `script/acceptance/render_wind_acceptance_geometry_runtime.R:28` och `script/acceptance/render_wind_acceptance_geometry_runtime.R:301-321`
- `potential_app.py:5083-5188`
- `script/acceptance/render_trondelag_population_buffer.R:28-58`

### Resultatpanel

Högerpanelen ska läsa samma snapshot som kartan. V2 gör detta bra genom `map_state` och cache:

- `_render_reused_workspace_outputs()` i `potential_app.py:11676-11718`
- `_combined_summary()` i `potential_app.py:11728`
- högerpanelblocket i `potential_app.py:13479-13582`

V3 bör ersätta den lösa dict-strukturen med `RenderedAnalysisSnapshot`, men behålla principen att panelen aldrig läser draft.

## Särskilda V3-beslut

### Social acceptans

V2:s social-acceptance-kontroller i workspace är mer live än sol/vind (`potential_app.py:12580-12631`). V3 bör välja en av två modeller:

- rekommenderad: social acceptans ingår i draft/applied och kräver `Använd ändringar`;
- alternativ: markera social acceptans som live-kontroll och visa separat att den uppdaterar analys direkt.

Eftersom V3-målet säger att applied-state ska styra karta, analys och högerpanel bör social acceptans ingå i apply-gränsen.

### Dirty/stale UX

När draft skiljer sig från applied:

- visa en diskret status: `Ej tillämpade ändringar`;
- låt karta och högerpanel fortsätta visa senaste applied snapshot;
- visa gärna applied-version/tid eller "Visar senast tillämpad analys";
- disable inte kartan, men gör det tydligt att widgets inte slagit igenom.

### Reset och regionbyte

Regionbyte ska:

- byta aktivt region-namespace;
- initiera draft och applied från regionens default om ingen state finns;
- eller rebasera draft från applied om användaren väljer reset;
- invalidra snapshot-cache för föregående region;
- aldrig bära Trøndelag-buffertar eller H3-val in i Bornholm, eller omvänt.

## Kod att porta

- Solens draft/applied helpermönster: `potential_app.py:4329-4425`.
- Solens applyflöde: `potential_app.py:12451-12552`.
- Workspace fingerprint/cache: `potential_app.py:2220-2293` och `potential_app.py:12659-12699`.
- Snapshot reuse för UI-only reruns: `potential_app.py:11676-11718`.
- Asset registry: `apps/acceptance_model/layers.py:52-96`.
- Source GeoJSON lookup: `apps/acceptance_model/layers.py:247-256`.
- Runtime geometry cache wrapper: `apps/acceptance_model/runtime_geometry.py:32-87`.
- Trøndelag population buffer: `potential_app.py:5083-5188` och `script/acceptance/render_trondelag_population_buffer.R:28-58`.

## Kod att förenkla

- Slå ihop sol/vind till samma state-kontrakt.
- Ersätt många top-level `st.session_state` keys med typade/namespacade stateobjekt.
- Gör source/buffer layer visibility till en egen modell, inte separata widgetnamn per teknik.
- Separera `AnalysisState`, `RenderSnapshot` och `UiState`.
- Gör stale/dirty-status central i stället för captions per formulär.

## Kod att undvika

- Implicit vind-apply via enbart `st.form`.
- Direktläsning av widgetkeys från kart- eller panelkod.
- `setdefault` som enda sätt att synka draft från applied.
- Social-acceptance live-state utan tydlig UX om resten av appen är apply-gated.
- Tyst fallback när GeoJSON saknas.
- Trøndelag R8/R9 i interaktiv app. Håll R7/R6/R5 som supported displaynivåer.

## AppTest-fall

1. Ändra sol-draft utan apply och verifiera att karta, analys och högerpanel visar oförändrad applied snapshot.
2. Applicera soländring och verifiera att applied config, fingerprint, karta och högerpanel uppdateras tillsammans.
3. Ändra wind-draft utan apply och verifiera att runtime inte körs och att layer specs inte ändras.
4. Applicera wind-draft och verifiera att runtime-cache key ändras när layer_ids eller buffer_m ändras.
5. Slå på source visibility för ett lager, applicera och verifiera att source layer finns i renderade layer specs.
6. Välj ett filterlager men lämna source/buffer visibility av, applicera och verifiera att analysen använder lagret men kartan inte visar overlayn.
7. Slå på Trøndelag population buffer och verifiera upplöst polygonbuffer/proxy-not, inte H3-buffer.
8. Simulera saknat source GeoJSON och verifiera att UI visar saknad datakälla och att analysen inte kraschar.
9. Ändra panelbredd eller opacitet och verifiera att calculation fingerprint är oförändrat och cached snapshot återanvänds.
10. Byt region och verifiera att draft/applied/cache inte läcker mellan regioner.
11. Verifiera att Trøndelag H3-display bara erbjuder R7, R6 och R5.
12. Ändra social acceptans och verifiera vald V3-modell: antingen apply-gated eller tydligt live.
