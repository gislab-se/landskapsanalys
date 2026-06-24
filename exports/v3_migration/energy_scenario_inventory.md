# Energy Scenario Inventory For V3

Syfte: ge V3 ett exakt V2-underlag for energimodell, scenario, ytbehov och kopplingen vidare till potential/resultat. Detta kompletterar:

- `exports/v3_migration/potential_analysis_pipeline_inventory.md`
- `exports/v3_migration/potential_result_properties_contract.json`
- `exports/v3_migration/potential_analysis_v3_recommendation.md`

## Kort slutsats

V2:s energimodell ar manifeststyrd:

1. Scenario-manifestet pekar ut DuckDB och AreaDemand.
2. DuckDB laddas till en mix-tabell med `scenario`, `year`, `energy_key`, `value_twh`.
3. Ett planeringsscenario valjer source scenario, planeringsar och energiskala.
4. V2:s mixslider balanserar om vald mix till default 50 procent sol och 50 procent vind.
5. AreaDemand ger `km2_per_twh` per teknik och area-scenario.
6. `calculate_area_demand(...)` skapar `wind_twh`, `solar_twh`, `wind_area_need_km2`, `solar_area_need_km2`.
7. Dessa falt driver scenarioallokering, inte grundklassningen for potential.

## Kodkarta

Energimodell:

- `apps/potential_model/energy_modeling.py:40` `DEFAULT_DUCKDB_CONFIG` definierar default TIMES-tabeller, kolumnalias, filter och teknikmappning.
- `apps/potential_model/energy_modeling.py:68` `DEFAULT_AREA_DEMAND_CONFIG` definierar default AreaDemand-rader och TIMES-teknikmappning.
- `apps/potential_model/energy_modeling.py:231` `load_energy_model_inputs(manifest, root)` laddar DuckDB.
- `apps/potential_model/energy_modeling.py:332` `planning_scenarios(manifest)` laser planeringsscenarier ur manifest, annars fallback low/medium/high.
- `apps/potential_model/energy_modeling.py:374` `select_planning_mix(mix, scenario)` filtrerar source scenario + ar och multiplicerar `value_twh` med `energy_scale`.
- `apps/potential_model/energy_modeling.py:665` `load_area_demand_bundle(manifest, root)` laddar `AreaDemand.xlsx` och skapar `factors_by_scenario`.
- `apps/potential_model/energy_modeling.py:832` `calculate_area_demand(...)` multiplicerar TWh med `km2_per_twh`.
- `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)` allokerar vindyta i potentialhex.

V2-appens wrapper:

- `potential_app.py:2908` `_cached_energy_inputs(...)` cachar `load_energy_model_inputs(...)`.
- `potential_app.py:2915` `_cached_area_demand(...)` cachar `load_area_demand_bundle(...)`.
- `potential_app.py:2934` `_technology_to_times_map(...)` oversatter `wind -> NRG_WIN`, `solar -> NRG_SOL`.
- `potential_app.py:3013` `_balance_wind_solar_mix(...)` balanserar om vald mix till anvandarens solandel.
- `potential_app.py:3050` `_energy_mix_solar_share_from_session(...)` satter mixdefault till 50 procent sol.
- `potential_app.py:3151` `_render_energy_modeling_panel(...)` bygger `energy_model_state`.
- `potential_app.py:3268` anropar `calculate_area_demand(...)`.
- `potential_app.py:3332-3369` skriver ut output i `energy_model_state`.

## Manifest och datafiler per region

Bornholm:

- `apps/potential_model/manifests/regions/bornholm.json:28` pekar pa `apps/potential_model/manifests/scenarios/bornholm_scenarios_placeholder.json`.
- `apps/potential_model/manifests/scenarios/bornholm_scenarios_placeholder.json:3-4` har `scenario_set_id = bornholm_energy_model_duckdb_v0`, `status = prototype`.
- `bornholm_scenarios_placeholder.json:9` DuckDB: `data/processed/speedlocal_times.duckdb`.
- `bornholm_scenarios_placeholder.json:37` AreaDemand: `data/raw/AreaDemand.xlsx`.
- `bornholm_scenarios_placeholder.json:38` `times_technology_map` kopplar `NRG_WIN -> wind`, `NRG_SOL -> solar`.
- `bornholm_scenarios_placeholder.json:73` manifestets `default_scenario = medium`.
- `bornholm_scenarios_placeholder.json:78-100` low/medium/high anvander `ENERGYISLAND2050`, ar 2050, skala 0.65/1.0/1.25 och area-scenario low/mid/high.
- `bornholm_scenarios_placeholder.json:104` `auto_min_potential_share_pct = 65.0`.

Trondelag:

- `apps/potential_model/manifests/regions/trondelag.json:24` pekar pa `apps/potential_model/manifests/scenarios/trondelag_scenarios_placeholder.json`.
- `trondelag_scenarios_placeholder.json:3-4` har `scenario_set_id = trondelag_bornholm_energy_model_placeholder`, `status = placeholder`.
- `trondelag_scenarios_placeholder.json:9` DuckDB: `data/processed/speedlocal_times.duckdb`.
- `trondelag_scenarios_placeholder.json:37` AreaDemand: `data/raw/AreaDemand.xlsx`.
- `trondelag_scenarios_placeholder.json:73` manifestets `default_scenario = medium`.
- `trondelag_scenarios_placeholder.json:78-100` low/medium/high anvander Bornholm `ENERGYISLAND2050`, ar 2050, skala 0.65/1.0/1.25 och area-scenario low/mid/high.
- `trondelag_scenarios_placeholder.json:104` `auto_min_potential_share_pct = 65.0`.
- `trondelag_scenarios_placeholder.json:107` sager uttryckligen att detta ar en temporar Bornholm-placeholder tills EML/norsk motsvarighet finns.
- `apps/potential_model/manifests/regions/trondelag.json:28` upprepar att energiscenarier anvander Bornholm placeholder TIMES/AreaDemand.

Skaraborg/Vara:

- V2 har en planerad `vara`-region, inte fardig Skaraborg-runtime.
- `apps/potential_model/manifests/regions/vara.json:5-13` har `status = planned`, `native_crs = TBD`, `available_h3_resolutions = []`, `default_h3_resolution = null`, `scenario_manifest = null`.
- Slutsats: V3 far inte gissa energimodell for Skaraborg. Markera energiscenario som `missing` tills regionalt scenario-manifest finns.

## Defaultscenario i V2

Det finns tva defaults:

1. Manifest default:
   - Bornholm och Trondelag anger `default_scenario = medium` i scenario-manifestet.
2. Appens start-default:
   - `potential_app.py:4088` `_ensure_default_start_state(...)` applicerar beslutslage.
   - `potential_app.py:4100-4102` satter `potential_scenario_<region_id> = high`, `energy_model_planning_scenario_<region_id> = high`, `energy_model_area_scenario_<region_id> = high`.
   - `potential_app.py:3050-3061` satter mixdefault till 50 procent sol, alltsa 50 procent vind.

I praktiken startar den nuvarande V2-appen i high/high/50-50, om inte session state redan har ett giltigt val.

## Hur area demand beraknas

I `_render_energy_modeling_panel(...)`:

- `potential_app.py:3177-3184` laddar planeringsscenarier och planning config.
- `potential_app.py:3186-3199` valjer/initialiserar planning scenario key `energy_model_planning_scenario_<region_id>`.
- `potential_app.py:3214-3219` valjer/initialiserar area scenario key `energy_model_area_scenario_<region_id>`.
- `potential_app.py:3246` `selected_mix = select_planning_mix(mix, selected_planning)`.
- `potential_app.py:3254-3257` raknar native wind/solar TWh och native solandel.
- `potential_app.py:3258-3260` laser mixslider och balanserar om mixen till vald solandel.
- `potential_app.py:3262` laser `technology_to_times`.
- `potential_app.py:3268` `calculate_area_demand(...)`.
- `potential_app.py:3278-3285` extraherar `solar_area_need`, `solar_twh`, `solar_factor`, `wind_area_need`, `wind_twh`, `wind_factor`.
- `potential_app.py:3358-3366` skriver `wind_area_need_km2`, `wind_km2_per_twh`, `solar_area_need_km2`, `solar_km2_per_twh`, `wind_twh`, `solar_twh`, `h3_resolution`, `auto_min_potential_share_pct` till `energy_model_state`.

Formeln ar enkel:

```text
twh = sum(selected_mix.value_twh for energy_key)
km2_per_twh = area_bundle.factors_by_scenario[area_scenario_id][times_tech]
area_need_km2 = twh * km2_per_twh
```

## Vindallokering

- `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)`.
- Input: frame med `hex_id`, `potential_area_share_pct`, ev. `potential_area_km2`, `core_score`, `zone_size`, `allocation_priority_score`; area need; hex area; min share; optional `avoid_hex_ids`.
- `energy_modeling.py:931-934` satter `allocation_phase = Karn-LP` om share >= `min_share_pct`, annars `Kompletterande LP`.
- `energy_modeling.py:956-968` sorterar kandidater efter prioritet, core score, potential share, phase, zone size, area, reservation och `hex_id`.
- `energy_modeling.py:970-984` allokerar `allocated_area_km2`, `allocated_hex_share_pct`, `remaining_area_after_km2`, `selected_rank`.
- `energy_modeling.py:994-1010` returnerar stats, bland annat `unmet_area_km2`, `available_candidate_area_km2`, `selected_hex_count`, `min_share_pct`.

## Data status

- Bornholm energy scenario: `prototype`, men DuckDB/AreaDemand-flodet ar verkligt integrerat for Bornholm-prototypen.
- Trondelag energy scenario: `placeholder`; samma Bornholm TIMES/AreaDemand som placeholder.
- Skaraborg/Vara: `missing`; inget scenario-manifest i V2.
- Social acceptans: `synthetic` i nuvarande Bornholm/Trondelag manifests.
- Trondelag befolkning/settlement: `proxy` nar 250 m grid/centroid anvands.
- PDF-derived landskap: `experimental` om det anvands; ska inte behandlas som final analysdata.

## V3-cache-id

V3 bor skapa energiscenario-cache-id av:

- `region_id`
- `scenario_manifest_id` eller manifest path + content hash
- DuckDB path/version eller source hash
- AreaDemand path/version eller source hash
- `planning_scenario_id`
- `area_scenario_id`
- `solar_share_pct`
- `technology_to_times`
- `analysis_h3_resolution`
- data_status flags

Karta/layer visibility och map view ska inte ingå.
