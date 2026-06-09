# V3 Potential Runtime Handoff Summary

Datum: 2026-06-09

## Vad vi har gjort

Vi har inventerat V2:s kart- och analyskedja i flera steg, med fokus på att V3 inte ska behöva gissa.

Det viktigaste resultatet är att V3 nu kan behandla `Potentiell etableringsyta` som ett grundpotentiallager, separat från energiscenario och scenario-allokering.

Vi har särskilt rett ut:

- hur V2 renderar result layers i Leaflet
- hur V2 håller kartvy och zoom stabil vid layer toggles
- hur V2 bygger potentialresultat och GeoJSON-properties
- hur V2:s energimodell/scenario hänger ihop med potentialkedjan
- vilka delar som är faktisk analys, proxy, placeholder, experimentellt eller saknas
- vilka runtimekällor som finns för Bornholm, Trøndelag och Skaraborg/Vara
- hur vind- och solpotential kan normaliseras till ett V3-kontrakt
- hur `Potentiell etableringsyta` kan renderas utan energiscenario

## Vad som redan levererats till V3

### Layer control, Leaflet och kartvy

- `exports/v3_migration/leaflet_layer_control_inventory.md`
- `exports/v3_migration/leaflet_layer_spec_examples.json`
- `exports/v3_migration/leaflet_renderer_minimal_port.md`
- `exports/v3_migration/leaflet_view_persistence_inventory.md`

Kärnbudskap:

- layer toggles ska vara UI-only
- `overlayadd` och `overlayremove` får inte trigga analys eller `fitBounds`
- karta ska läsa `rendered_snapshot.layers`
- kartvy ska vara UI-state och bevaras över lagerändringar

### Result layer-rendering

- `exports/v3_migration/potential_result_layers_inventory.md`
- `exports/v3_migration/potential_result_layer_specs.json`
- `exports/v3_migration/potential_result_v3_recommendation.md`

Kärnbudskap:

- result layers ska vara separata från source/buffer layers
- Leaflet layer control ska visa användarnära lager, inte teknisk datastatus
- teknisk status hör hemma i kontrakt, test och debug

### Potentialanalys och properties

- `exports/v3_migration/potential_analysis_pipeline_inventory.md`
- `exports/v3_migration/potential_result_properties_contract.json`
- `exports/v3_migration/potential_analysis_v3_recommendation.md`

Kärnbudskap:

- V2:s kombinerade etableringsklass bygger på `wind_suitable` och `solar_suitable`
- scenario/allocation-fält är separata från grundpotential
- placeholder/proxy ska inte presenteras som färdig analys

### Energimodell och scenario

- `exports/v3_migration/energy_scenario_inventory.md`
- `exports/v3_migration/energy_scenario_contract.json`
- `exports/v3_migration/potential_frame_contract.json`
- `exports/v3_migration/potential_layer_runtime_recommendation.md`

Kärnbudskap:

- energiscenario behövs för ytbehov och allokering
- energiscenario behövs inte för att visa grundlagret `Potentiell etableringsyta`
- Trøndelag har verklig runtime-geometri/potentialbas, men energiscenario/TIMES/AreaDemand ska behandlas försiktigt som proxy/placeholder

### Ny runtime-handoff för grundpotential

Nyligen levererat:

- `exports/v3_migration/potential_runtime_frame_inventory.md`
- `exports/v3_migration/potential_runtime_frame_contract.json`
- `exports/v3_migration/potential_runtime_source_examples.json`
- `exports/v3_migration/potential_runtime_v3_recommendation.md`

Kärnbudskap:

- V3 kan bygga `Potentiell etableringsyta` från två `technology_potential_frame`: en för vind och en för sol
- required V3-fält är:
  - `hex_id`
  - `technology_id`
  - `suitable`
  - `potential_score_pct`
  - `potential_area_km2`
- V2:s klassning är:
  - `wind_and_solar`
  - `wind_only`
  - `solar_only`
  - `not_suitable`
- GeoJSON ska skickas till Leaflet i `EPSG:4326`
- native CRS används för analys och area, inte för Leaflet-rendering

JSON-filerna är validerade med:

```powershell
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe -m json.tool exports\v3_migration\potential_runtime_frame_contract.json
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe -m json.tool exports\v3_migration\potential_runtime_source_examples.json
```

## Regionstatus

### Bornholm

Status: `ok`

- faktisk renderbar grundpotential/geometri finns i V2
- käll-H3: R10
- default display-H3: R8
- tillgängligt display: R10/R9/R8/R7/R6
- native CRS: `EPSG:25833`
- render CRS: `EPSG:4326`

V3 kan börja här.

### Trøndelag

Status: `ok` för runtimebas, med vissa proxy-/modellkommentarer

- faktisk R7 app bundle finns
- display ska vara R7/R6/R5
- R8/R9 ska inte exponeras i appen
- native CRS: `EPSG:25832`
- render CRS: `EPSG:4326`
- energiscenario/AreaDemand ska hållas separat från grundpotential

V3 kan börja här också, men måste vara tydlig med status och inte blanda in scenario-placeholder.

### Skaraborg/Vara

Status: `missing`

- V2 har planerat manifest men ingen renderbar potentialkälla
- ingen H3-displaygeometri
- ingen default H3-upplösning

V3 ska inte rendera syntetisk `Potentiell etableringsyta` för Skaraborg som om det vore analys. Först behövs faktisk Skaraborg-källa/generator.

## Nästa steg för V3

1. Läs in `potential_runtime_frame_contract.json` som målkontrakt för `technology_potential_frame`.
2. Implementera `load_technology_potential_frame(region_id, technology_id, applied_state)`.
3. Implementera regionstatus:
   - Bornholm: `ok`
   - Trøndelag: `ok`/`proxy` enligt källa
   - Skaraborg/Vara: `missing`
4. Implementera V2-mappningen:
   - vind: `potential_area_share_pct` eller `wind_score` till `potential_score_pct`
   - sol: `potential_area_km2` eller `potential_area_m2 / 1e6`
   - `suitable = potential_area_km2 > 1e-9`
5. Implementera displaygeometri från `hex_id` och regionens H3-displaykälla.
6. Materialisera `potential_establishment` som result layer utan scenariofält.
7. Publicera layern i `rendered_snapshot.layers`.
8. Gör lagret default visible när feature collection finns.
9. Låt Leaflet layer toggle ändra synlighet utan `fitBounds`, utan analys och utan draft-läsning.

## Föreslagna V3-tester

- normalisering av V2-vindframe med `potential_area_share_pct`
- normalisering av V2-solframe med `potential_area_m2`
- klassning av `wind_and_solar`
- klassning av `wind_only`
- klassning av `solar_only`
- klassning av `not_suitable`
- Bornholm kan materialisera `Potentiell etableringsyta` utan energiscenario
- Trøndelag kan materialisera R7 utan energiscenario
- Trøndelag R8/R9 exponeras inte
- Skaraborg/Vara returnerar `missing` och renderar inte placeholder
- draftändring ändrar inte `rendered_snapshot` före apply
- layer toggle ändrar inte zoom, center eller kör om analys

## Rekommenderad arbetsordning

Bygg först grundpotentialen hela vägen till karta för Bornholm och Trøndelag. När det fungerar stabilt kan V3 lägga på scenario-allokering och outside-LP som separata properties eller separata lager.

Det här håller första V3-steget ärligt: användaren ser faktisk etableringspotential där data finns, och får tydlig missing-status där data inte finns.

