# Scenariofordelning i etableringshex

## Kort svar

`Scenariofordelning i etableringshex` visar var energiscenariots ytbehov har placerats automatiskt. Lagret ar inte en full optimering over hela landskapet. Det ar ett greedy urval: appen rangordnar kandidathexa efter teknikens egna regler och tar de basta tills ytbehovet ar uppfyllt.

## Vad betyder linjerna?

Lagret ritar sma vita child-hex ovanpa den storre etableringshexen.

Konturen visar teknik:

- bla kontur: scenarioyta for vind
- brun/orange kontur: scenarioyta for sol
- gron kontur: samma etableringshex anvands av bade vind och sol

Definition finns i `potential_app.py`:

- `SCENARIO_ALLOCATION_LAYER_LABEL`
- `SCENARIO_ALLOCATION_SPECS`
- `_scenario_allocation_marker_feature_collection`
- `_scenario_allocation_marker_layer`

Observera att den synliga linjen kan uppfattas som rod/brun for sol eftersom solkonturen ar satt till en mork orange/brun farg.

## Vad styr placeringen?

Placeringen styrs av energimodelleringen och potentiallagren:

1. Vald energiscenario-niva anger TWh for vind och sol.
2. Energimix-reglaget flyttar andel mellan vind och sol.
3. AreaDemand oversatter TWh till ytbehov i km2.
4. Appen bygger kandidathexa for vind respektive sol.
5. Varje teknik sorterar sina kandidater.
6. Appen tar kandidater i sorteringsordning tills ytbehovet ar uppfyllt.

Det finns alltsa en ranking, men inte en gemensam global "basta hex for allt"-optimering.

## Vindens urval

Vind anvander:

- `allocate_wind_area_from_core_hexes` i `apps/potential_model/energy_modeling.py`
- vindens potentiella areaandel per hex
- `core_score`
- `zone_size`
- minsta karnkrav, normalt `auto_min_potential_share_pct = 65`

Vind sorteras ungefar sa har:

1. karn-LP forst: hex med potentialandel >= minsta karnkrav
2. hogre `core_score`
3. storre sammanhangande zon, `zone_size`
4. hogre potentialandel
5. storre potentiell area
6. hex-id som stabil tie-break

Det betyder att en vindhex inte bara valjs for att den har hog potential, utan ocksa for att den ligger djupt i en sammanhangande vindzon.

## Solens urval

Sol anvander:

- `_solar_establishment_frame` i `potential_app.py`
- forst smaskalig sol pa tak om den ar aktiv
- sedan storskalig sol pa land
- `potential_score`
- `potential_area_km2`

Sol sorteras ungefar sa har:

1. smaskalig sol fore storskalig sol
2. hogre solscore
3. storre potentiell solyta
4. hex-id som stabil tie-break

Det gor att sol kan hamna pa andra platser an vind aven om kartan visar overlappande landskapspotential.

## Varfor skiljer sig vind och sol?

Vind och sol ar olika modeller:

- Vind bygger pa andel mojlig vindyta, harda lager/filter, karnlage och sammanhangande zoner.
- Sol bygger pa solens egna score, schablonyta for tak eller storskalig solyta.
- Energimixen ger olika ytbehov for respektive teknik.
- Varje teknik fyller sitt ytbehov separat.

En hex kan darfor vara mycket bra for vind men inte toppad for sol, eller tvartom.

## Finns det en mest lamplig hexagon?

Ja, per teknik finns det en forsta vald kandidat:

- vind: lagst `selected_rank`, normalt rank 1 i `proposal_frame`
- sol: lagst `selected_rank`, normalt rank 1 i `solar_proposal_frame`

Men det finns inte idag en gemensam "bast totalt"-hex som vager ihop vind, sol, landskapsfaktorer, energimix och samnyttjande i en enda score.

## Viktig slutsats

Scenariofordelningen ar greedy, inte optimering.

Det betyder:

- den ar begriplig och snabb
- den ar stabil sa lange sorteringsreglerna ar stabila
- den hittar inte nodvandigtvis den globalt basta kombinationen av hexagoner
- den forklarar placering genom ranking och kandidatregler, inte genom optimeringsmal

## Forslag till nasta kodandring

Lagg till en expander i hogerpanelen: `Varfor placerades scenariot har?`

Den bor visa:

- vald scenario-niva
- energimix
- ytbehov for vind och sol
- antal valda hex
- topp 10 vindhex med `selected_rank`, `potential_area_share_pct`, `core_score`, `zone_size`, `allocated_area_km2`
- topp 10 solhex med `selected_rank`, `source_group`, `potential_score`, `potential_area_km2`, `allocated_area_km2`
- en kort text: "Urvalet ar greedy: kandidater sorteras och fylls tills ytbehovet ar tackt."

Det ar en liten UI-forbattring som gor placeringen begriplig utan att andra berakningslogiken andras.
