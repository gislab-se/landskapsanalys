# V3 kartlagerstatus och rendered snapshot layers

Status: 2026-06-09

Syfte: inventera hur V2 hanterar kartlagerstatus, source layers och buffer layers, och föreslå ett V3-kontrakt för `rendered_snapshot.layers` innan mer analyslogik byggs.

## Kort slutsats

V2:s viktigaste princip är att analysval och kartvisning är separata saker. Ett källager kan vara valt och påverka analysen utan att källgeometrin visas i kartan. När användaren faktiskt vill se källor eller buffertar görs det via opt-in-kontroller som sedan materialiseras som Leaflet-lager med `source_layer_id` eller `buffer_layer_id`.

För V3 bör samma princip bli mer explicit: kartans statusrader ska inte läsa draft/widgets. De ska läsa en applied-bunden `rendered_snapshot.layers`, där varje renderat lager har eget `layer_id`, `layer_kind`, `visible`, `data_status`, `operation`, CRS, cache key och style.

## 1. Kartlagerstatus och lagerkontroll i V2

### Hur aktiva lager visas

V2 visar aktiva analyslager i kontrollpanelen, inte primärt under kartan. För vind byggs gruppkontroller i `potential_app.py:8029`; varje regelgrupp ligger i en expander och får suffixet `- ej tillgänglig` om gruppen saknar redo källager (`potential_app.py:8053`). Om en grupp saknar data visas texten `Ej tillgängligt för vald region ännu...` (`potential_app.py:8056`).

För sol ligger kontrollerna i formen `solar_landscape_potential_controls_unified` (`potential_app.py:12451`). V2 säger uttryckligen att ändringar i lager och sliders inte appliceras förrän användaren trycker på `Använd ändringar` (`potential_app.py:12454`). Det är samma mentala modell V3 bör behålla.

### Source layers och buffer layers

V2 skiljer mellan:

- analyslager: valda källager och avstånd som används i beräkningen
- source layer: källgeometrin som kan visas i kartan
- buffer layer: buffert-/närhetsgeometrin som kan visas i kartan
- result layer: potential-, etablerings- eller hex/polygonresultat

Source/buffer-visning är opt-in. V2:s UI-texter är `Visa källa i kartan` och `Visa buffert i kartan` för både vind (`potential_app.py:8140`, `potential_app.py:8145`) och sol (`potential_app.py:12484`, `potential_app.py:12488`, `potential_app.py:12510`, `potential_app.py:12514`). För sol läses det renderade kartläget från applied config (`potential_app.py:12371`) och sparas först vid submit (`potential_app.py:12550`).

När användaren har valt att visa källor/buffertar läggs V2-lagren in i kartans `layers`-lista med `_layer_visible_by_default(...)` (`potential_app.py:4996`). Själva lagerdictarna har ofta `default_visible: False` som säker default, men opt-in-flödet gör dem synliga när de faktiskt ska renderas.

### Standardläge kontra opt-in

I standardläget visar V2 de huvudsakliga resultatlagren och döljer tekniska detaljer. Source/buffer-lager visas bara om användaren har aktiverat dem i avancerade kontroller och applicerat ändringen. Det finns också en Leaflet-lagerkontroll i kartan: renderer lägger `spec.name` i `overlays` (`apps/potential_model/map_rendering.py:504`) och använder `spec.default_visible !== false` som initial synlighet (`apps/potential_model/map_rendering.py:489`, `apps/potential_model/map_rendering.py:508`). Leaflet-kontrollen skapas collapsed (`apps/potential_model/map_rendering.py:619`).

Teknisk lagerstatus visas inte i standardläge. V2 har en dold expander `Debug och prestanda` (`potential_app.py:13503`) där `map_layer_debug_rows` kan visas med rubriken `Kartlager i senaste HTML-renderingen.` (`potential_app.py:13539`). Raderna byggs av `_map_layer_debug_rows(...)` och innehåller `lager`, `namn`, `typ`, `features`, `default` och `z` (`potential_app.py:3892`).

### Labels och statusord i V2

V2:s labels är mer UI-strängar än ett strikt kontrakt:

- Källa: `Källa: ...`, `Vind källa: ...`, `Sol källa: ...` (`potential_app.py:8245`, `potential_app.py:8346`, `potential_app.py:8375`, `potential_app.py:5038`, `potential_app.py:5321`)
- Buffert: `Vindbuffert: ...`, `Solbuffert: ...` (`potential_app.py:5755`, `potential_app.py:8420`, `potential_app.py:5264`)
- Närhets-/feasibility-lager: `Vind nära nät: ...`, `Sol nära nät: Elinfrastruktur` (`potential_app.py:5755`, `potential_app.py:219`)
- Avdrag/exkludering: exempelvis `Solavdrag: skog` i solspecarna (`potential_app.py:219`)
- Missing/unavailable: `missing_assets` i acceptance-lagerstatus (`apps/acceptance_model/layers.py:188`, `apps/acceptance_model/layers.py:208`) och `- ej tillgänglig` i UI (`potential_app.py:8053`)
- Empty: V2 returnerar ofta inget lager om `features` saknas, exempelvis source layers (`potential_app.py:5317`) och buffer layers (`potential_app.py:5675`)
- Proxy: Trøndelag befolkning märks i tooltip/popup som `250 m befolkningsrutproxy` och förklaras som centroidbaserad, upplöst polygonbuffert (`potential_app.py:5168`)
- Experimental: V2 har experimentella lager främst som caption/handoff, inte som förstaklassad `data_status`

## 2. Rendered layer specs i V2

### V2 source layer spec

V2 använder fria dictar som direkt serialiseras till Leaflet (`apps/potential_model/map_rendering.py:133`, `apps/potential_model/map_rendering.py:144`). Ett source layer har typiskt:

```json
{
  "name": "Vind källa: Befolkningsunderlag (Befolkning och bebyggelse)",
  "source_layer_id": "wind:population_points",
  "feature_collection": "<GeoJSON FeatureCollection>",
  "fill_property": "fill",
  "legend_items": [],
  "legend_id": "wind_polygon_source_population_points",
  "legend_title": "",
  "default_visible": false,
  "stroke_color": "#...",
  "fill_color": "#...",
  "stroke_opacity": 0.85,
  "fill_opacity": 0.28,
  "weight": 2.0,
  "point_radius": 4,
  "use_global_opacity": false,
  "layer_kind": "vector"
}
```

Exempel finns i solens befolkningskälla (`potential_app.py:5028`) och generella solkällor (`potential_app.py:5284`). Vindens polygon-source-lager använder samma mönster och sätter `source_layer_id` per källa (`potential_app.py:8375`, `potential_app.py:8389`).

### V2 buffer layer spec

Ett buffer layer liknar source layer, men har `buffer_layer_id` i stället för `source_layer_id`. Avståndet ligger ofta inbakat i id:t och i popup/tooltip, inte som eget fält.

```json
{
  "name": "Vindbuffert: Befolkning och bebyggelse",
  "buffer_layer_id": "wind:settlement:buffer:500:population_points",
  "feature_collection": "<GeoJSON FeatureCollection>",
  "fill_property": "fill",
  "legend_items": [],
  "legend_id": "wind_polygon_buffer_settlement",
  "legend_title": "",
  "default_visible": false,
  "stroke_color": "#...",
  "fill_color": "#...",
  "stroke_opacity": 0.48,
  "fill_opacity": 0.20,
  "weight": 2.2,
  "point_radius": 6,
  "use_global_opacity": false,
  "layer_kind": "vector"
}
```

Exempel finns i solens befolkningsbuffert (`potential_app.py:5235`), generella solbuffertar (`potential_app.py:5665`) och vindbuffertar (`potential_app.py:8396`). V2 deduplikerar lager via `source_layer_id`, `buffer_layer_id` eller `name` (`potential_app.py:4981`, `potential_app.py:5004`).

### Fält V3 bör ha i rendered_snapshot.layers

V3 bör inte kopiera V2:s fria dict rakt av. Behåll renderbar stilinformation, men gör status och identitet förstaklassade.

Obligatoriska fält:

- `layer_id`: stabilt render-id, unikt inom snapshotten
- `layer_kind`: `source`, `buffer` eller `result`
- `parameter_id`: t.ex. `population`, `protected_nature`, `electrical_grid`
- `technology_id`: `wind`, `solar` eller `shared`
- `source_layer_id`: id för källagret som ligger bakom source/buffer, `null` för rena resultatlager
- `label`: användarlabel i lagerstatus och Leaflet
- `visible`: applied-renderad kartvisning, inte draft och inte analysaktivitet
- `data_status`: maskinläsbar status
- `operation`: analyssemantik, t.ex. `distance_conflict`, `hard_exclusion`, `proximity_feasibility`, `display_only`
- `distance_m`: meter för buffer layers, annars `null`
- `native_crs`: CRS där avstånd/buffert/area gjorts
- `render_crs`: CRS för GeoJSON/webbrendering
- `cache_key`: stabil nyckel för den renderade geometrin/statusen
- `style`: begränsat style-objekt, inte hela renderer-interna dict

Rekommenderade extra fält:

- `feature_count`: antal features i renderad GeoJSON
- `status_message`: kort förklaring vid `missing`, `empty`, `proxy` eller `experimental`
- `legend_items`: om lagret behöver egen legend
- `selected_layer_ids`: när flera källager slås ihop till ett renderlager
- `default_visible`: kan härledas från `visible`, men användbart vid Leaflet-export
- `geometry_role`: `raw_source`, `buffer_polygon`, `score_hex`, `establishment_area`

### Föreslaget JSON-kontrakt

```json
{
  "schema_version": "rendered-snapshot-layers/v0.1",
  "rendered_snapshot": {
    "applied_fingerprint": "sha256-of-applied-config",
    "region_id": "bornholm",
    "layers": [
      {
        "layer_id": "wind:population:population_points:source",
        "layer_kind": "source",
        "parameter_id": "population",
        "technology_id": "wind",
        "source_layer_id": "population_points",
        "label": "Vind - Befolkning och bebyggelse - källa",
        "visible": true,
        "data_status": "ready",
        "operation": "distance_conflict",
        "distance_m": null,
        "native_crs": "EPSG:25833",
        "render_crs": "EPSG:4326",
        "cache_key": "source:bornholm:population_points:sha256",
        "feature_count": 128,
        "status_message": "",
        "selected_layer_ids": ["population_points"],
        "style": {
          "geometry_type": "point",
          "stroke_color": "#2563eb",
          "fill_color": "#2563eb",
          "stroke_opacity": 0.85,
          "fill_opacity": 0.28,
          "weight": 1.2,
          "point_radius": 4,
          "z_index": 456
        }
      },
      {
        "layer_id": "wind:population:population_points:buffer:500",
        "layer_kind": "buffer",
        "parameter_id": "population",
        "technology_id": "wind",
        "source_layer_id": "population_points",
        "label": "Vind - Befolkning och bebyggelse - buffert 500 m",
        "visible": true,
        "data_status": "ready",
        "operation": "distance_conflict",
        "distance_m": 500,
        "native_crs": "EPSG:25833",
        "render_crs": "EPSG:4326",
        "cache_key": "buffer:bornholm:wind:population:population_points:500:sha256",
        "feature_count": 1,
        "status_message": "Buffert renderad från applied state.",
        "selected_layer_ids": ["population_points"],
        "style": {
          "geometry_type": "polygon",
          "stroke_color": "#0f766e",
          "fill_color": "#14b8a6",
          "stroke_opacity": 0.48,
          "fill_opacity": 0.20,
          "weight": 0.55,
          "point_radius": null,
          "z_index": 458
        }
      },
      {
        "layer_id": "wind:establishment_area:result",
        "layer_kind": "result",
        "parameter_id": null,
        "technology_id": "wind",
        "source_layer_id": null,
        "label": "Vind - möjlig etableringsyta",
        "visible": true,
        "data_status": "ready",
        "operation": "result",
        "distance_m": null,
        "native_crs": "EPSG:25833",
        "render_crs": "EPSG:4326",
        "cache_key": "result:bornholm:wind:establishment_area:sha256",
        "feature_count": 42,
        "status_message": "",
        "selected_layer_ids": [],
        "style": {
          "geometry_type": "polygon",
          "stroke_color": "#7f1d1d",
          "fill_color": "#ef4444",
          "stroke_opacity": 0.65,
          "fill_opacity": 0.35,
          "weight": 1.0,
          "point_radius": null,
          "z_index": 430
        }
      }
    ]
  }
}
```

Rekommenderad `data_status`-enum:

- `ready`
- `missing_assets`
- `missing_source`
- `empty`
- `disabled`
- `not_selected`
- `proxy`
- `experimental`
- `error`

`proxy` och `experimental` kan kombineras med `ready` via ett extra `status_tags`-fält om V3 vill undvika att status blir dubbeltydig:

```json
{
  "data_status": "ready",
  "status_tags": ["proxy"],
  "status_message": "Befolkning använder 250 m rut-/centroidproxy, inte individpunkter."
}
```

## 3. Applied vs draft

### Måste komma från applied/rendered snapshot

Följande fält ska alltid komma från applied/rendered snapshot, aldrig direkt från widgets:

- vilka source layers som finns i statusraderna
- vilka buffer layers som finns i statusraderna
- `visible`
- `data_status`
- `operation`
- `distance_m`
- `selected_layer_ids`
- `native_crs`
- `render_crs`
- `cache_key`
- `feature_count`
- `status_message`
- `style`
- `layer_id`

V2:s solflöde är den tydligaste referensen: applied config hämtas via `_solar_config_from_session()` (`potential_app.py:4329`), draft byggs separat (`potential_app.py:4385`) och applied skrivs bara vid `Använd ändringar` (`potential_app.py:12550`). Kartlagren skapas sedan från applied-valen (`potential_app.py:12731`, `potential_app.py:12799`, `potential_app.py:12813`).

V3 har redan samma grundstruktur: `RenderedAnalysisSnapshot` ligger i interaction state och innehåller applied fingerprint (`C:/tmp/landskapspotential/src/landskapspotential/interaction_state.py:42`), `_rendered_snapshot_from_applied(...)` bygger snapshotten från applied config (`C:/tmp/landskapspotential/src/landskapspotential/app.py:721`), och `_analysis_state_from_applied(...)` kopierar `source_visible`, `buffer_visible`, `operation`, `native_crs` och `render_crs` från applied semantik (`C:/tmp/landskapspotential/src/landskapspotential/app.py:1518`).

### Får inte läsa draft/widgetkeys

Layer-statusrader ska inte läsa:

- `solar_draft_*`
- `_solar_visual_control_key(...)`
- `_solar_draft_config_from_session()`
- `_wind_control_key("visual_source", ...)`
- `_wind_control_key("visual_buffer", ...)`
- V3:s `_parameter_draft_key(..., "source-visible", ...)`
- V3:s `_parameter_draft_key(..., "buffer-visible", ...)`
- V3:s `_current_draft_from_widgets(...)`
- temporära Streamlit widgetvärden för lager innan apply

Draft får styra formuläret och visa en "ej applicerade ändringar"-indikator. Kartstatus och renderer ska däremot läsa `state.rendered_snapshot.layers`.

## 4. Rekommenderat V3-beteende

### Ersätt tekniska rader under kartan med opt-in

Ja: tekniska source/buffer-rader under kartan bör ersättas av en stängd expander eller toggle. Rekommenderat namn:

`Kartlager och datastatus`

Alternativet `Tekniska kartlager` är tydligare för utvecklare, men sämre för vanliga användare. `Kartlager och datastatus` fångar både "vad visas?" och "varför saknas något?" utan att låta som debug.

### Standardläge

I standardläge bör V3 visa:

- huvudresultat i kartan
- vanliga Leaflet/Map-lagerkontroller om de behövs
- ingen tabell med source/buffer-status under kartan
- eventuell kort applied-indikator, t.ex. `Kartan visar senast applicerade val`

### Expanderinnehåll

Expander/toggle bör visa en tabell byggd från `rendered_snapshot.layers` med dessa kolumner:

- `visas`: ja/nej
- `typ`: källa/buffert/resultat
- `teknik`
- `parameter`
- `lager`
- `status`
- `operation`
- `avstånd`
- `CRS`
- `meddelande`

Visa följande rader:

- alla `visible: true` source/buffer/result layers
- source/buffer layers med `data_status` i `missing_assets`, `missing_source`, `empty`, `proxy`, `experimental`, `error`
- aktiva men dolda analyslager som kort status, t.ex. `används i analys, visas inte`, om V3 vill hjälpa användaren förstå varför kartan inte visar rågeometrier
- cache key bara bakom extra debug eller i utvecklingsläge

### När ingen källa eller buffert är aktiv

Om analysparametrar är aktiva men inga source/buffer-lager visas:

`Inga käll- eller buffertlager visas i kartan. Aktiva parametrar kan fortfarande påverka analysen. Slå på källa eller buffert i avancerade inställningar och klicka Använd ändringar.`

Om inga parameterlager är aktiva i applied state:

`Inga käll- eller buffertlager är aktiva i senast applicerade läge.`

Om lager saknas:

`Källager saknas eller är tomt för senast applicerade läge. Kontrollera datakoppling innan parametern används i analys.`

## 5. Föreslagna testfall

### Blocktester för state och kontrakt

1. `test_rendered_snapshot_layers_from_applied_only`
   - skapa base applied utan source/buffer synliga
   - ändra draft till source/buffer synliga
   - verifiera att `state.rendered_snapshot.layers` är oförändrad före apply

2. `test_apply_updates_rendered_snapshot_layers`
   - applicera draft med `source_visible=True` och `buffer_visible=True`
   - verifiera att snapshotten innehåller två separata lager: ett `layer_kind="source"` och ett `layer_kind="buffer"`
   - verifiera att `applied_fingerprint` matchar applied hash

3. `test_buffer_layer_contract_contains_distance_and_crs`
   - bygg buffert från applied state
   - verifiera `distance_m`, `native_crs`, `render_crs`, `operation`, `source_layer_id` och `cache_key`

4. `test_source_and_buffer_can_be_visible_independently`
   - source on, buffer off: endast source-lager i visible status
   - source off, buffer on: endast buffer-lager i visible status
   - båda on: båda lager finns med olika `layer_id`

5. `test_missing_empty_proxy_status_is_machine_readable`
   - simulera saknat source asset, tom GeoJSON och proxykälla
   - verifiera `data_status`/`status_tags` och `status_message`

### AppTest eller UI-blocktester

1. `test_layer_status_rows_hidden_by_default`
   - rendera appen med en applied source/buffer-konfiguration
   - verifiera att detaljerade statusrader inte syns innan expandern öppnas

2. `test_layer_status_expander_shows_source_buffer_status`
   - öppna `Kartlager och datastatus`
   - verifiera att source och buffer visas med typ, label, status och avstånd

3. `test_draft_change_does_not_update_status_before_apply`
   - toggla `Visa källa` eller `Visa buffert` i UI
   - verifiera att statusraderna fortfarande speglar applied snapshot
   - verifiera att en "ej applicerade ändringar"-indikator kan visas separat

4. `test_apply_refreshes_layer_status_and_map_labels`
   - klicka `Använd ändringar`
   - verifiera att `rendered_snapshot.layers` och kartans lagerlabels uppdateras

5. `test_no_source_or_buffer_message`
   - applied state med aktiva parametrar men `source_visible=False` och `buffer_visible=False`
   - öppna status-expander
   - verifiera rekommenderad tomtext

V3:s befintliga `scripts/test_interaction_model.py` testar redan början på detta: draft kan skilja sig från applied och snapshot labels/statusnotiser uppdateras först när changed applied används. Nästa steg är att ersätta lösa labels/notiser med kontraktet ovan.
