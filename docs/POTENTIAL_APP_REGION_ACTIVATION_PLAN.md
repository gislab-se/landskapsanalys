# Potential App: regionaktivering och data-tolerant UI

## Mål

Bornholm, Vara/Skaraborg och Trøndelag ska använda samma appstruktur:

- samma expanders
- samma controllers och sliders
- samma kartlogik
- samma energimodelleringsflöde
- samma högerpanel
- samma beräkningslogik

Det som ska skilja regionerna åt är data och manifest, inte separata kodvägar.

## Data-tolerant princip

En region ska kunna öppnas även när all data inte finns ännu.

Om data saknas ska appen visa vänliga statusmeddelanden, till exempel:

- "Landskapsdata saknas ännu för denna region."
- "Vindpotential visas här när H3-underlag och vindregler är kopplade."
- "Energimodellering aktiveras när scenariomanifest, DuckDB och AreaDemand är kopplade."

Saknad data ska inte stoppa hela appen.

UI-skelettet ska ändå finnas. Det betyder att samma huvudsektioner, expanders och kontroller ska visas för planerade regioner, men vara avstängda tills relevant data kopplas in. Syftet är att användaren ska kunna se exakt vilka dataluckor som behöver fyllas utan att appen byter arbetssätt mellan regioner.

Exempel på disabled UI för planerade regioner:

- H3-upplösning och hexvisningsläge
- Landskapstyper, landskapsstrukturer och landskapsfaktorer
- Vindregelgrupper och buffert-/analysreglage
- Småskalig och storskalig sol med samma filtergrupper
- Energimix, scenario och placering
- Högerpanelens karta, etableringsyta, potentialsektioner och härledningar

## Regionkontrakt

Minsta regionmanifest:

- `region_id`
- `display_name`
- `country`
- `status`
- `web_crs`
- `default_map_center`
- `default_zoom`

För kart- och potentialfunktioner behövs stegvis:

- `available_h3_resolutions`
- `default_h3_resolution`
- `h3_display_geometries`
- `landscape_manifest`
- `potential_manifest`
- `scenario_manifest`

## Status 2026-05-12

Trondelag har nu preliminara manifest sa att regionen kan visas i samma UI-skelett som Bornholm:

- `apps/potential_model/manifests/regions/trondelag.json`
- `apps/potential_model/manifests/landscape/trondelag_landscape_placeholder.json`
- `apps/potential_model/manifests/potential/trondelag_potential_placeholder.json`
- `apps/potential_model/manifests/potential/trondelag_solar_rules_placeholder.json`
- `apps/potential_model/manifests/potential/trondelag_wind_rules_placeholder.json`
- `apps/potential_model/manifests/scenarios/trondelag_scenarios_placeholder.json`

Appen skiljer nu mellan att manifest finns och att full runtime ar redo. Placeholder-manifest far alltsa regionstatusen att visa konkreta filplatser, men full berakning startar inte forran nodvandiga datafiler finns.

Regionstatus och runtime-validering ar nu flyttad till:

- `apps/potential_model/region_status.py`

Det betyder att kommande regioner kan valideras mot samma kontrakt utan att `potential_app.py` far fler region-specifika kontroller.

## Bornholm som referens

Bornholm hämtar regionkonfiguration från:

- `apps/potential_model/manifests/regions/bornholm.json`
- `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json`
- `apps/potential_model/manifests/potential/bornholm_potential_v0.json`
- `apps/potential_model/manifests/scenarios/bornholm_scenarios_placeholder.json`

Viktiga datafiler:

- `docs/geocontext/potential_framework/data/bornholm_landmask/`
- `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/map/bornholm_v10_landscape_types_map_data.geojson`
- `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/model/bornholm_v10_landscape_types_source_v9_cluster_legend.csv`
- `data/processed/speedlocal_times.duckdb`
- `data/raw/AreaDemand.xlsx`
- `C:\gislab\regional-landscape-pipeline\outputs\bornholm\bornholm_v1_higher_h3_local_sprickdal\layers\01_fastboendebefolkningmapinfo.csv`

## Runtime kontra datapipeline

`landskapsanalys` innehåller appens runtime-kod och manifest.

`regional-landscape-pipeline` används för att producera vissa underlag, till exempel befolkningsunderlag för småskalig sol och regionala H3-/landskapslager.

Målet bör vara att appen kan starta utan pipeline-repot, men att funktioner som kräver pipeline-output visar tydlig status om filerna saknas.

## Modularisering

Modularisering betyder att gemensam logik flyttas ut ur `potential_app.py` till tydliga moduler, till exempel:

- regionvalidering
- kartlagerbygge
- högerpanel/härledning
- solpotential
- vindpotential
- energimodellering
- missing-data/status-UI

Det gör att en bugg i gemensam logik kan fixas en gång och slå igenom för Bornholm, Vara och Trøndelag.

## Debuggstrategi

Buggar ska delas upp i två typer:

- gemensamma kodbuggar: fixas i appens gemensamma logik och gäller alla regioner
- dataproblem: fångas av regionvalidering och rapporteras per region

Nästa tekniska steg är att bygga en regionvalideringsrapport som körs för alla regioner och visar:

- saknade manifest
- saknade H3-geometrier
- saknade sol-/vindregler
- saknad landskapsanalys
- saknad energimodell
- vilka UI-funktioner som påverkas

## Trøndelag: rekommenderat nästa steg

1. Lägg in minimalt Trøndelag-regionmanifest med center/zoom och CRS.
2. Lägg till H3-displaygeometrier när de finns.
3. Lägg till ett tomt eller preliminärt potentialmanifest.
4. Koppla sol- och vindregler, även om de först är generiska.
5. Låt landskapshärledning och faktorhärledning visa "data saknas" tills landskapsanalysen är färdig.
6. Koppla energimodell först när scenario-/DuckDB-underlag finns.
