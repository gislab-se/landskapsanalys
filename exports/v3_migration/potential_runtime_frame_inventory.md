# Potential Runtime Frame Inventory

Syftet med denna handoff är smalt: V3 ska kunna visa lagret `Potentiell etableringsyta` från faktisk grundpotential, utan att först implementera scenario-allokering, ytbehov eller energiscenario.

## Kort slutsats

V2 har en separat runtimekedja som kan bygga ett kombinerat etableringslager från två teknikramar:

- vindpotential
- solpotential

Den kombinerade ramen klassar varje display-hex som:

- `wind_and_solar`
- `wind_only`
- `solar_only`
- `not_suitable`

Scenario-allokering och "yta utanför landskapets potential" mergas in senare som extra properties. De behövs inte för att rendera grundlagret.

## 1. V2-kodreferenser

### Vind: grundpotential

V2 bygger vindpotential på två sätt beroende på region och runtimegren.

Generell Bornholm-/manifestbaserad källa:

- `potential_app.py:7037` `_wind_source_frame(...)`
  - anropar `wind_acceptance_potential_frame(...)`
  - läser region, landskapsmanifest, social acceptansmanifest/scenario och upplösning
- `potential_app.py:7052` `_wind_frame(...)`
  - gör rollup via `wind_acceptance_rollup_frame(...)` när visningsupplösning skiljer sig från källupplösning
  - filtrerar till befintliga displaygeometrier
- `apps/potential_model/wind_acceptance.py:268` `_build_wind_acceptance_frame_cached(...)`
  - bygger cached frame för vindacceptans/potential
- `apps/potential_model/wind_acceptance.py:361` `wind_acceptance_potential_frame(...)`
  - publik entrypoint för vindpotential
- `apps/potential_model/wind_acceptance.py:388` `wind_acceptance_rollup_frame(...)`
  - rollup till grövre H3

Trøndelag runtimegren:

- `potential_app.py:8989` `_wind_fast_distance_runtime_result(...)`
  - Trøndelag-specifik snabb runtimeberäkning från displaygeometrier och valda vindlager
  - använder `trondelag_fast_distance_r{target_resolution}` som intern cache-id-del
- `potential_app.py:9075` `_wind_runtime_hex_layer_frame(...)`
  - bygger vind-hexlayer från runtime-resultat
- `potential_app.py:10831` `_wind_polygon_preview_state(...)`
  - väljer Trøndelag fast-distance-grenen före generell runtime
- `potential_app.py:10953` `_unfiltered_wind_summary_frame(...)`
  - skapar ofiltrerad basvindram
- `potential_app.py:10998` `_wind_polygon_summary_frame(...)`
  - normaliserar runtimevind till fält som `hex_id`, `potential_area_share_pct`, `potential_area_km2`, `wind_score`, `wind_class`, `wind_color`

### Sol: grundpotential

- `potential_app.py:4794` `_solar_v1_frame(...)`
  - småskalig sol/proxygren, baserad på befolkning
- `potential_app.py:5813` `_solar_large_scale_frame(...)`
  - storskalig solpotential från landskaps-/filterram
  - viktiga fält: `potential_area_m2`, `potential_area_km2`, `potential_area_share_pct`, `solar_score`, `solar_class`, `solar_color`
- `potential_app.py:5969` `_combined_solar_hex_frame(...)`
  - kombinerar småskalig och storskalig sol till en solram

### Kombinerad `Potentiell etableringsyta`

- `potential_app.py:9346` `_potential_establishment_source_frame(...)`
  - normaliserar teknikram till `hex_id`, `<technology>_suitable`, `<technology>_potential_score`, `<technology>_potential_area_km2`
  - för vind används `potential_area_share_pct` om det finns, annars `wind_score`
  - för sol används `potential_area_km2`, annars `potential_area_m2`, annars score/area-derivering
  - suitability sätts från positiv potentiell yta
- `potential_app.py:9441` `_combined_establishment_class(...)`
  - mappar `wind_suitable` + `solar_suitable` till etableringsklass
- `potential_app.py:9463` `_apply_establishment_style_columns(...)`
  - sätter label och stylefält från `ESTABLISHMENT_CLASS_SPECS`
- `potential_app.py:9560` `_trondelag_rollup_potential_establishment_frame(...)`
  - Trøndelag-rollup från R7 till R6/R5
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`
  - skapar bas från displaygeometrier, mergar vind/solpotential och kan dessutom merga scenario-allokering om den finns
- `potential_app.py:10486` `_combined_establishment_feature_collection(...)`
  - gör ramen till GeoJSON FeatureCollection för Leaflet
- `potential_app.py:10652` `_combined_potential_establishment_family_layers(...)`
  - bygger layer family för `Potentiell etableringsyta`
- `potential_app.py:13186` till `potential_app.py:13201`
  - huvudflödet skapar `combined_establishment_layers` och lägger till dem i `layers`

### H3-id och geometri

- `apps/potential_model/geometry.py:15` `_full_h3_geometry(hex_id)`
  - använder `h3.cell_to_boundary(...)`
  - returnerar GeoJSON polygon i lon/lat
- `apps/potential_model/geometry.py:31` `load_h3_display_geometries(path_str)`
  - läser GeoJSON med `hex_id` eller `h3_address`
  - ersätter lagrad geometri med full H3-boundary när H3-biblioteket finns
- `apps/potential_model/geometry.py:44` `geometry_for_hex(...)`
  - lookup för en enskild H3-geometri
- `potential_app.py:3531` `_h3_display_geometry_path(region, resolution)`
  - hämtar regionens displaygeometri från manifest

### Leaflet layer control

- `potential_app.py:7462` `_render_layers(...)`
  - skickar lager till HTML-renderern
- `apps/potential_model/map_rendering.py:133` `build_layered_hex_map_html(...)`
  - V2:s direkta Leaflet-renderer för lagerfamiljer
- `apps/potential_model/map_rendering.py:415`
  - skapar `L.geoJSON(spec.feature_collection, ...)`
- `apps/potential_model/map_rendering.py:504`
  - lägger lager i `overlays[spec.name]`
- `apps/potential_model/map_rendering.py:608` till `apps/potential_model/map_rendering.py:619`
  - lägger zoom-/familjekontroll i `L.control.layers(...)`
- `apps/potential_model/map_rendering.py:632` och `apps/potential_model/map_rendering.py:641`
  - `overlayadd` och `overlayremove` uppdaterar klient-UI/legend och visibility-state; de kör inte analys

### Cache och session state

- `potential_app.py:168` `WORKSPACE_RENDER_CACHE_KEY = "potential_workspace_render_cache_v2"`
- `potential_app.py:176` `WIND_LAYER_SELECTION_KEY = "wind_builder_selected_layers"`
- `potential_app.py:178` `SOLAR_APPLIED_CONFIG_KEY = "solar_applied_config"`
- `potential_app.py:2220` `_workspace_calculation_fingerprint(...)`
  - inkluderar region, scenario, H3-upplösningar, zoom-family, sol/vindkonfig, valda vindlager, social acceptans och energimodellstatus
- `potential_app.py:2281` `_cached_workspace_payload(...)`
- `potential_app.py:2290` `_invalidate_workspace_cache(...)`
- `potential_app.py:12550`
  - kopierar sol-draft till `SOLAR_APPLIED_CONFIG_KEY`
- `potential_app.py:13457`
  - skriver cachepayload med `fingerprint`, `layers`, `energy_model_state`, `map_state.potential_frames`, `resolution`, `analysis_resolution`

## 2. Runtime-källor per region

### Bornholm

Status: `ok` för renderbar grundram, men vissa vind-/acceptansdelar är modellbaserade.

- Regionmanifest: `apps/potential_model/manifests/regions/bornholm.json`
- Landskapsmanifest: `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json`
- Native CRS: `EPSG:25833`
- Leaflet/render CRS: `EPSG:4326`
- Käll-H3: R10
- Analys-H3: normalt R10
- Default display-H3 i regionmanifest: R8
- Tillgängliga displaynivåer: R6, R7, R8, R9, R10
- Primär source path:
  - `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/map/bornholm_v10_landscape_types_map_data.geojson`
- Filformat: GeoJSON FeatureCollection
- Geometri:
  - finns i filen
  - V2 kan ändå bygga full H3 boundary från `hex_id`
- Relevanta manifestfält:
  - `landscape_geojson`
  - `factor_scores`
  - `h3_display_geometries`

Bornholm har alltså tillräckligt för att V3 ska kunna materialisera `technology_potential_frame` och bygga etablerings-GeoJSON utan energiscenario.

### Trøndelag

Status: `ok`/`proxy` för renderbar grundpotential i appens R7/R6/R5-kedja. Energiscenario/TIMES/AreaDemand är däremot placeholder/proxy och ska inte blandas in i grundpotentialen.

- Regionmanifest: `apps/potential_model/manifests/regions/trondelag.json`
- Landskapsmanifest: `apps/potential_model/manifests/landscape/trondelag_landscape_placeholder.json`
- Native CRS: `EPSG:25832`
- Leaflet/render CRS: `EPSG:4326`
- Käll-H3: R7
- Analys-H3: R7
- Display-H3: R7, R6, R5
- Primär source path:
  - `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson`
- R6/R5-rollups:
  - `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r6_rollup.geojson`
  - `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r5_rollup.geojson`
- Filformat: GeoJSON FeatureCollection
- Geometri:
  - finns i app bundle
  - V2 bygger/normaliserar displaygeometri via `load_h3_display_geometries(...)`
- Viktig avgränsning:
  - `trondelag_landscape_placeholder.json` är namngivet "placeholder", men app-bundlens R7/R6/R5 geocontext och displayhexar är faktiska runtimekällor.
  - LABLAB/PDF-landskap ligger separat som experimentellt lager och används inte som bas `landscape_geojson` eller `factor_scores`.
  - Bornholm/TIMES/AreaDemand-placeholder gäller energiscenario, inte nödvändigtvis grundpotential.

Trøndelag får inte exponera R8/R9 i V3 om V3 ska följa V2/AGENTS-regeln. Stöd R7, R6 och R5.

### Skaraborg/Vara

Status: `missing` i V2 runtime.

- Regionmanifest: `apps/potential_model/manifests/regions/vara.json`
- Native CRS: `TBD`
- Leaflet/render CRS: `EPSG:4326`
- Tillgängliga H3-upplösningar: tom lista
- `default_h3_resolution`: `null`
- `scenario_manifest`: `null`
- Renderbar grundpotential: saknas
- Geometri: saknas
- V2 source path/generator: ingen faktisk V2-runtimekedja hittad

Skaraborg/Vara behöver ny datakälla eller generator innan V3 kan visa `Potentiell etableringsyta` utan att använda placeholder.

## 3. Potential-frame kontrakt och V2-mappning

V3-normalizern kräver:

- `hex_id`
- `technology_id`: `wind` eller `solar`
- `suitable`: bool
- `potential_score_pct`: 0-100
- `potential_area_km2`: >= 0

### Vind

| V2-fält | V3-fält | Typ | Enhet | Krav | Ursprung/regel |
|---|---|---:|---|---|---|
| `hex_id` | `hex_id` | string | H3-id | required | läses från GeoJSON/frame |
| implicit technology | `technology_id` | string | enum | required | defaultas till `wind` |
| `potential_area_share_pct` | `potential_score_pct` | number | procent | preferred | läses/beräknas i runtimevind |
| `wind_score` | `potential_score_pct` | number | procent | fallback | används om `potential_area_share_pct` saknas |
| `potential_area_km2` | `potential_area_km2` | number | km2 | preferred | läses/beräknas |
| score + H3-area | `potential_area_km2` | number | km2 | fallback | `score / 100 * h3_hex_area_km2(source_resolution)` |
| `potential_area_km2 > 1e-9` | `suitable` | bool | - | required | exakt normaliseringsregel i `_potential_establishment_source_frame(...)` |

### Sol

| V2-fält | V3-fält | Typ | Enhet | Krav | Ursprung/regel |
|---|---|---:|---|---|---|
| `hex_id` | `hex_id` | string | H3-id | required | läses från GeoJSON/frame |
| implicit technology | `technology_id` | string | enum | required | defaultas till `solar` |
| `potential_area_share_pct` | `potential_score_pct` | number | procent | preferred | läses från storskalig/combined sol |
| `solar_score` | `potential_score_pct` | number | procent | fallback | används när share saknas |
| `potential_area_km2` | `potential_area_km2` | number | km2 | preferred | läses/beräknas |
| `potential_area_m2 / 1e6` | `potential_area_km2` | number | km2 | fallback | används när km2 saknas |
| `potential_area_km2 > 1e-9` | `suitable` | bool | - | required | exakt normaliseringsregel i `_potential_establishment_source_frame(...)` |

Trøndelag har dessutom en solregel i `potential_app.py:9428` till `potential_app.py:9435`: om en grov R7-cell har filteröverlapp men ingen småskalig yta kan suitability tvingas till false så att den grova kartan speglar Bornholms finare etableringslogik.

## 4. Geometri till `Potentiell etableringsyta`

V3 bör följa V2:s geometriordning:

1. Välj regionens display-H3-upplösning.
2. Läs displaygeometrier från regionmanifestets `h3_display_geometries`.
3. Slå upp varje `hex_id`.
4. Om H3-bibliotek finns, bygg full H3-boundary från `hex_id`.
5. Skicka GeoJSON till Leaflet i `EPSG:4326`.

V2:s `load_h3_display_geometries(...)` returnerar GeoJSON polygons med koordinater i lon/lat. Native CRS används för analys, buffert och area; inte för Leaflet-output.

Minsta feature properties för V3:s runtime-etableringslager:

- `hex_id`
- `layer_kind`: `result`
- `result_type`: `potential_establishment`
- `establishment_class`
- `establishment_label`
- `wind_suitable`
- `solar_suitable`
- `wind_potential_score_pct`
- `solar_potential_score_pct`
- `wind_potential_area_km2`
- `solar_potential_area_km2`
- `fill`
- `stroke`
- `stroke_weight`
- `fill_opacity`
- `data_status`

Scenariofält som kan vänta:

- `wind_allocated_area_km2`
- `solar_allocated_area_km2`
- `wind_allocated_gwh`
- `solar_allocated_gwh`
- `outside_lp_shortage`
- `outside_lp_reason`
- `wind_outside_lp_area_km2`
- `solar_outside_lp_area_km2`

## 5. Exempeldata

Se `exports/v3_migration/potential_runtime_source_examples.json`.

Filen innehåller:

- Bornholm: source-/unfiltered-exempel från R10-landskaps-GeoJSON, mappade till vind och sol som neutral potentialframe
- Trøndelag: faktisk ofiltrerad vindbas från R7 runtime samt faktisk storskalig solframe från R7
- Skaraborg/Vara: markerad som `missing`

## 6. V3-regel

V3 ska läsa detta från applied/rendered runtime, inte direkt från draft/widget keys.

Rekommenderad kedja:

1. Applied state väljer region, H3 display resolution och teknikfilter.
2. Runtime bygger `technology_potential_frame` för vind och sol.
3. Runtime materialiserar `Potentiell etableringsyta` som result layer.
4. Layer publiceras i `rendered_snapshot.layers`.
5. Kartan läser bara `rendered_snapshot.layers`.
6. Leaflet layer control togglar synlighet utan ny analys och utan `fitBounds`.

