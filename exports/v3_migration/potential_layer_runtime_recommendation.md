# Potential Layer Runtime Recommendation

Syfte: ge V3 en konkret runtime-vag for att kora `Potentiell etableringsyta` utan att blanda ihop grundpotential, scenarioallokering och placeholderdata.

## Rekommenderad minsta V3-vag

Forsta sakra steget:

1. Bygg `energy_model_state` fran applied scenario input.
2. Bygg normaliserade `wind_potential_frame` och `solar_potential_frame`.
3. Bygg `combined_establishment_frame` fran potentialramarna utan att krava scenarioallokering.
4. Materialisera `Potentiell etableringsyta` nar riktig `feature_collection` finns.
5. Markera region-/delstatus i kontrakt/debug, t.ex. `placeholder`, `proxy`, `synthetic`, `missing`.

Vanta med `Scenariofördelning i etableringshex` och `Ytbehov utanför landskapets potential` tills V3 har en reproducerbar area-demand/allokeringskedja.

## Energiscenario

Portera dessa regler:

- Manifesten beskriver data, men V2-appens start-state ar high/high/50-50.
- `planning_scenario_id` och `area_scenario_id` ska komma fran applied state.
- `solar_share_pct` ska komma fran applied state.
- `wind_share_pct = 100 - solar_share_pct`.
- `select_planning_mix(...)` filtrerar source scenario + ar och skalar TWh.
- `balance_wind_solar_mix(...)` bevarar total TWh men fordelar om mellan wind/solar.
- `calculate_area_demand(...)` ger `area_need_km2 = twh * km2_per_twh`.

V3 ska inte lasa widgetkeys direkt. Widgetar skriver draft; `Använd ändringar` uppdaterar applied; runtime laser applied.

## Potentialramar

Normalisera varje teknik till:

```text
hex_id
technology_id
suitable
potential_score_pct
potential_area_km2
potential_area_share_pct
data_status
```

V2-kallor:

- Vind, generellt/Bornholm: `potential_app.py:7037` `_wind_source_frame(...)` -> `wind_acceptance_potential_frame(...)`.
- Vind, Trondelag: `potential_app.py:8989` `_wind_fast_distance_runtime_result(...)`, `potential_app.py:10998` `_wind_polygon_summary_frame(...)`.
- Sol: `potential_app.py:4794` `_solar_v1_frame(...)`, `potential_app.py:5813` `_solar_large_scale_frame(...)`, `potential_app.py:5969` `_combined_solar_hex_frame(...)`.

Trondelag ska i V3 behandlas som R7 app/source level med R6/R5 rollups. R8/R9 ska inte exponeras utan nytt data-/produktbeslut.

## Combined establishment

V2:s centrala funktioner:

- `potential_app.py:9346` `_potential_establishment_source_frame(...)`
- `potential_app.py:9441` `_combined_establishment_class(...)`
- `potential_app.py:9463` `_apply_establishment_style_columns(...)`
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`
- `potential_app.py:10486` `_combined_establishment_feature_collection(...)`

V3 bor implementera klassning exakt:

```text
wind_suitable=true,  solar_suitable=true  -> wind_and_solar / Vind och sol
wind_suitable=true,  solar_suitable=false -> wind_only      / Endast vind
wind_suitable=false, solar_suitable=true  -> solar_only     / Endast sol
wind_suitable=false, solar_suitable=false -> not_suitable   / Inte lämplig
```

Minsta properties som V3 ska satta direkt:

- `hex_id`
- `establishment_class`
- `establishment_label`
- `wind_suitable`
- `solar_suitable`
- `wind_potential_score`
- `solar_potential_score`
- `wind_potential_area_km2`
- `solar_potential_area_km2`
- `fill`
- `stroke`
- `stroke_weight`
- `fill_opacity`
- `data_status`

Scenario/allocation fields far vanta eller vara optional:

- `wind_allocated_area_km2`
- `solar_allocated_area_km2`
- `wind_allocated_gwh`
- `solar_allocated_gwh`
- `wind_rank`
- `solar_rank`
- `outside_lp_shortage`
- `outside_lp_reason`

Grundpotential ska inte bli false bara for att scenario allocation saknas. Scenario allocation ar en annan berakning.

## Scenario allocation

V2 bygger scenario allocation sa har:

- Vind: `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)`.
- Sol: `potential_app.py:6175` `_solar_establishment_frame(...)`.
- Combined selected frame: `potential_app.py:9254` `_establishment_source_frame(...)`.
- Scenario marker GeoJSON: `potential_app.py:10325` `_scenario_allocation_marker_feature_collection(...)`.
- Layer family: `potential_app.py:10454` `_scenario_allocation_marker_family_layers(...)`.

Detta ar faktisk modellplacering inom potentialramarna, men fortfarande modellens scenarioforslag, inte beslutad etablering.

## Outside-LP

V2 bygger outside-LP sa har:

- Vind: `potential_app.py:10698` `_expand_wind_area_outside_et(...)`.
- Sol: `potential_app.py:6415` `_expand_solar_area_outside_lp(...)`.
- Schematiskt GeoJSON: `potential_app.py:10069` `_outside_lp_need_feature_collection(...)`.
- Layer family: `potential_app.py:10225` `_outside_lp_need_family_layers(...)`.

Outside-LP ar **schematisk visualisering av brist**, inte verklig placering. V3-properties ska darfor ha:

```json
{
  "is_schematic": true,
  "is_real_location": false
}
```

## State och cache

V2 fingerprintar arbetsytan i:

- `potential_app.py:2220` `_workspace_calculation_fingerprint(...)`
- `potential_app.py:2248-2275` payload med region, scenario, H3, applied solkonfig, vindlager, vindparametrar, energimodell och acceptans.
- `potential_app.py:168` `WORKSPACE_RENDER_CACHE_KEY = "potential_workspace_render_cache_v2"`.
- `potential_app.py:13457` sparar senaste workspace payload.

V3 cache-id bor inkludera:

- `region_id`
- `analysis_h3_resolution`
- `display_h3_resolution`
- scenario manifest hash
- energy source hash/version
- AreaDemand source hash/version
- `planning_scenario_id`
- `area_scenario_id`
- `solar_share_pct`
- applied wind config
- applied solar config
- social acceptance applied config
- data status/versioner

V3 cache-id ska exkludera:

- map center/zoom
- Leaflet base layer
- overlay visibility
- draft widgetkeys innan apply

## Regionrekommendation

Bornholm:

- Kan porteras som prototypflode med V2:s DuckDB/AreaDemand och H3 R10/R8-policy.
- Social acceptans ska vara `synthetic`.

Trondelag:

- Energimodell ska markeras `placeholder`.
- H3-policy ar R7/R6/R5.
- Befolkning/settlement ar proxy nar 250 m grid/centroid anvands.
- PDF-landskap ar experimental om det kopplas in.

Skaraborg:

- V2 saknar scenario-manifest och potentialruntime.
- V3 ska inte visa fardig potential som om den vore riktig analys.
- Minsta sakra steg ar att skapa tom/missing snapshot med tydlig `data_status = "missing"` tills regionala energiscenarier och potentialramar finns.

## Rekommenderade tester

- `test_energy_defaults_high_high_50_50_match_v2_start_state`
- `test_energy_scenario_contract_requires_duckdb_and_area_demand`
- `test_calculate_area_demand_formula`
- `test_potential_frame_minimum_columns`
- `test_combined_establishment_without_allocation_still_classifies_base_potential`
- `test_scenario_allocation_fields_are_optional_for_base_potential_layer`
- `test_outside_lp_is_schematic_not_real_location`
- `test_trondelag_placeholder_energy_status`
- `test_skaraborg_missing_energy_does_not_materialize_final_result`
- `test_cache_key_excludes_leaflet_visibility_and_map_view`
