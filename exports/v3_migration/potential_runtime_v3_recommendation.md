# Potential Runtime V3 Recommendation

## Vad V3 bör portera direkt

Portera den smala delen av V2 som bygger `Potentiell etableringsyta` från två teknikramar:

1. Normalisera vind till `technology_potential_frame`.
2. Normalisera sol till `technology_potential_frame`.
3. Merga båda på display-hex.
4. Sätt `wind_suitable` och `solar_suitable`.
5. Klassificera till `wind_and_solar`, `wind_only`, `solar_only`, `not_suitable`.
6. Bygg GeoJSON FeatureCollection i `EPSG:4326`.
7. Publicera som ett result layer i `rendered_snapshot.layers`.

V2-referenserna är:

- `potential_app.py:9346` `_potential_establishment_source_frame(...)`
- `potential_app.py:9441` `_combined_establishment_class(...)`
- `potential_app.py:9463` `_apply_establishment_style_columns(...)`
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`
- `potential_app.py:10486` `_combined_establishment_feature_collection(...)`
- `potential_app.py:10652` `_combined_potential_establishment_family_layers(...)`

## Vad V3 bör förenkla

V3 bör börja utan scenario-allokering.

Första implementationen kan sätta följande scenariofält till `null`, `0` eller utelämna dem:

- `wind_allocated_area_km2`
- `solar_allocated_area_km2`
- `wind_allocated_gwh`
- `solar_allocated_gwh`
- `outside_lp_shortage`
- `outside_lp_reason`
- `wind_outside_lp_area_km2`
- `solar_outside_lp_area_km2`

Det räcker att visa grundpotential:

- var vind kan vara möjlig
- var sol kan vara möjlig
- var båda kan vara möjliga
- var ingen av dem är möjlig

## Vad V3 bör undvika

Undvik att:

- läsa draft/widget keys direkt i layer-buildern
- kräva energiscenario för att visa grundpotential
- presentera Trøndelag TIMES/AreaDemand-placeholder som verklig scenarioanalys
- exponera Trøndelag R8/R9 i interaktiv app
- använda PDF-/LABLAB-landskap som baspotential utan explicit experimentflagga
- köra `fitBounds` när användaren togglar result layer
- blanda teknisk datastatus i huvudlagrets Leaflet layer control-label

## Kan `Potentiell etableringsyta` renderas utan energiscenario?

Ja, för Bornholm och Trøndelag där V2 har renderbara potential-/displaykällor.

`Potentiell etableringsyta` behöver endast:

- vindpotential per `hex_id`
- solpotential per `hex_id`
- displaygeometri per `hex_id`
- klassningsregeln från `wind_suitable` och `solar_suitable`

Energiscenario behövs först när V3 ska visa scenariofördelning, energimängd, prioritet, eller yta utanför landskapets potential.

För Skaraborg/Vara är svaret nej tills V3 har en faktisk Skaraborg-källa eller generator för potentialframe och displaygeometri.

## Minsta säkra V3-implementation

Minsta säkra steg är:

- Lägg till en runtime loader som returnerar `technology_potential_frame` för `wind` och `solar`.
- Stöd Bornholm och Trøndelag först.
- Returnera `missing` för Skaraborg/Vara utan att rendera placeholder.
- Materialisera `potential_establishment` från dessa frames.
- Publicera layern i `rendered_snapshot.layers`.
- Gör layern default visible, men rendera bara när `feature_collection.features.length > 0`.
- Visa en neutral tomstatus i högerpanel/debug om regionen saknar data.

## Regionpolicy

### Bornholm

Portera som `ok`.

- Analyskälla R10.
- Display kan vara R10/R9/R8/R7/R6.
- Default display enligt V2-regionmanifest: R8.
- Native CRS `EPSG:25833`, render `EPSG:4326`.

### Trøndelag

Portera som `ok`/`proxy` beroende på delkälla.

- Analyskälla R7.
- Display bara R7/R6/R5.
- Native CRS `EPSG:25832`, render `EPSG:4326`.
- Markera energiscenario som placeholder/proxy separat från grundpotential.

### Skaraborg/Vara

Markera som `missing`.

- Ingen V2-runtimekälla hittad.
- Ingen H3-displaygeometri hittad.
- Ingen default H3-resolution.
- Rendera inte syntetiskt lager som om det vore analys.

## Föreslagna tester

- `test_potential_frame_normalizes_wind_share_pct`
- `test_potential_frame_normalizes_solar_area_m2`
- `test_potential_establishment_class_wind_and_solar`
- `test_potential_establishment_class_wind_only`
- `test_potential_establishment_class_solar_only`
- `test_potential_establishment_class_not_suitable`
- `test_bornholm_potential_establishment_without_energy_scenario`
- `test_trondelag_potential_establishment_r7_without_energy_scenario`
- `test_trondelag_display_resolutions_are_r7_r6_r5_only`
- `test_skaraborg_missing_potential_does_not_render_placeholder`
- `test_rendered_snapshot_layer_contains_feature_collection_when_data_exists`
- `test_draft_change_does_not_rebuild_potential_layer_before_apply`
- `test_layer_toggle_does_not_change_zoom_or_recompute_analysis`

## Implementation Order

1. Lägg in regionstatus och source-paths i V3:s datakontrakt.
2. Implementera `load_technology_potential_frame(region_id, technology_id, applied_state)`.
3. Mappa V2-fält till V3-kontraktet och validera required fields.
4. Implementera displaygeometri-loader från `hex_id` och regionens H3-displaykälla.
5. Implementera `materialize_potential_establishment_layer(...)` utan scenariofält.
6. Publicera layern i `rendered_snapshot.layers` med `layer_kind: "result"` och `data_status`.
7. Lägg testerna ovan för Bornholm, Trøndelag och Skaraborg/Vara.
8. Först därefter: bygg scenario-allokering och outside-LP som separata properties/lager.

