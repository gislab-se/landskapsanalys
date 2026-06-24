# Potential Analysis V3 Recommendation

Detta ar rekommendation for hur V3 bor porta berakningskedjan bakom V2:s resultatlager. Den ar skild fran Leaflet-renderingen: kartan ska bara konsumera `rendered_snapshot.layers`.

## Grundregel

V3 ska ha tre tydliga state-lager:

- `draft`: widgetar och sidopanel, aldrig direkt input till analys.
- `applied`: normaliserad och validerad analysinput efter `Använd ändringar`.
- `rendered_snapshot`: fryst resultat fran senaste applied-analys, inklusive layer specs, feature collections och paneldata.

Resultatlagren `Potentiell etableringsyta`, `Scenariofördelning i etableringshex` och `Ytbehov utanför landskapets potential` ska skapas fran applied state och sedan publiceras till `rendered_snapshot.layers`.

## Portera direkt

Portera dessa principer fran V2:

- Regionens native CRS styr distans, buffert och area: Bornholm `EPSG:25833`, Trondelag `EPSG:25832`.
- GeoJSON till karta ska vara EPSG:4326.
- H3-upplosning ar regionpolicy, inte global konstant.
- Source/buffer visibility i Leaflet ar UI-only och ska inte paverka analys.
- `wind_suitable` och `solar_suitable` ska klassas till `wind_and_solar`, `wind_only`, `solar_only`, `not_suitable`.
- Scenarioyta ska hallas separat fran potential: potential visar var teknik kan vara mojlig; scenario allocation visar var ytbehovet placeras.
- Outside-LP ska vara tydligt schematiskt extra ytbehov, inte verklig placering.
- Social acceptance och experimentell/proxy-data ska finnas i kontrakt/debug/test som `data_status`, men inte forvandla huvud-UI till teknisk lagerstatus.

Kodreferenser i V2:

- `potential_app.py:9441` `_combined_establishment_class(...)`
- `potential_app.py:9676` `_combined_potential_establishment_frame(...)`
- `potential_app.py:10325` `_scenario_allocation_marker_feature_collection(...)`
- `potential_app.py:10069` `_outside_lp_need_feature_collection(...)`
- `apps/potential_model/energy_modeling.py:832` `calculate_area_demand(...)`
- `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)`

## Forenkla i V3

V2 har mycket historik i samma fil. V3 bor dela upp det till smala steg:

1. `build_applied_analysis_input(applied_state, manifests)`.
2. `build_wind_potential(input) -> technology_potential_frame`.
3. `build_solar_potential(input) -> technology_potential_frame`.
4. `calculate_area_demand(input.energy)`.
5. `allocate_scenario_area(wind_potential, solar_potential, area_demand)`.
6. `build_combined_establishment_frame(...)`.
7. `build_result_layers(frame_bundle) -> rendered_snapshot.layers`.

Gor vind och sol symmetriska i kontraktet aven om deras metoder skiljer sig. Anvand t.ex.:

- `technology_id`
- `potential_score_pct`
- `potential_area_km2`
- `suitable`
- `allocated_area_km2`
- `allocated_gwh`
- `selected_rank`
- `outside_lp`
- `data_status`

V2:s popup-HTML bor inte vara datakontraktet. I V3 bor popup byggas fran strukturerade properties.

## Undvik

Undvik att porta foljande som V3-arkitektur:

- Direkt lasning av `st.session_state["solar_draft_*"]` i analyskedjan.
- Analyslogik som beror pa Leaflet `overlayadd`, `overlayremove` eller layer control visibility.
- Dubbla vindspår utan tydlig ansvarslinje. V2 har bade `wind_acceptance.py` och runtime-snabbspår i `potential_app.py`.
- Att anvanda `popup` HTML som enda plats for viktiga siffror.
- Att behandla Trondelag R8/R9 som appstod utan nytt databeslut; V2 exponerar R7/R6/R5.
- Att behandla syntetisk social acceptans eller PDF-derived landskap som final data.

## Minimal sakert V3-steg

Ett sakert forsta V3-steg ar:

1. Bygg en normaliserad `applied_analysis_input` fran applied state.
2. Stod en region och en analysupplosning i taget.
3. Publicera bara `Potentiell etableringsyta` med strukturerade properties:
   - `hex_id`
   - `wind_suitable`
   - `solar_suitable`
   - `establishment_class`
   - `establishment_label`
   - `wind_potential_area_km2`
   - `solar_potential_area_km2`
   - `data_status`
4. Lagga scenario allocation och outside-LP forst nar area-demand och allokeringsramen ar reproducerbar.

For Skaraborg/Vara dar data/CRS fortfarande ar ofullstandigt ska V3 hellre visa `data_status = "missing"` eller `placeholder"` i debug/kontrakt an att simulera ett fullstandigt resultat utan tydlig markering.

## Rekommenderat applied input-kontrakt

```json
{
  "region_id": "trondelag",
  "native_crs": "EPSG:25832",
  "analysis_h3_resolution": 7,
  "display_h3_resolution": 7,
  "energy": {
    "planning_scenario_id": "high",
    "area_scenario_id": "high",
    "solar_share_pct": 50
  },
  "wind": {
    "selected_group_layers": {
      "settlement": ["population_grid_250m"],
      "transport": ["roads"],
      "electrical": ["grid"]
    },
    "parameters_m": {
      "settlement_distance_m": 1000,
      "road_distance_m": 300,
      "grid_max_distance_m": 5000
    }
  },
  "solar": {
    "small_population_active": false,
    "large_scale_active": true,
    "large_population_active": true,
    "population_buffer_m": 500,
    "filters": [
      {
        "group_id": "protected",
        "operation": "exclusion",
        "layer_ids": ["protected_nature"],
        "distance_m": 250
      },
      {
        "group_id": "electrical",
        "operation": "proximity_feasibility",
        "layer_ids": ["grid"],
        "distance_m": 2000
      }
    ]
  },
  "social_acceptance": {
    "scenario_id": "baseline",
    "impact_pct": 0,
    "allocation_priority_pct": 0,
    "data_status": "synthetic"
  }
}
```

## Rekommenderad result builder-output

`build_potential_results(applied_analysis_input)` bor returnera:

```json
{
  "snapshot_id": "uuid-or-hash",
  "input_fingerprint": "sha256:...",
  "region_id": "trondelag",
  "analysis_h3_resolution": 7,
  "display_h3_resolution": 7,
  "frames": {
    "wind_potential": "dataframe-or-arrow-ref",
    "solar_potential": "dataframe-or-arrow-ref",
    "wind_allocation": "dataframe-or-arrow-ref",
    "solar_allocation": "dataframe-or-arrow-ref",
    "combined_establishment": "dataframe-or-arrow-ref"
  },
  "layers": [
    {
      "id": "result:combined_establishment:r7",
      "label": "Potentiell etableringsyta",
      "layer_kind": "result",
      "result_kind": "potential_establishment_area",
      "visible": true,
      "feature_collection": {}
    }
  ],
  "panel": {
    "area_balance": {},
    "data_status": []
  }
}
```

Karta och hogerpanel ska lasa just denna snapshot. Nar draft andras ska snapshoten ligga kvar tills `Använd ändringar` skapar en ny.

## Rekommenderade tester

AppTest/blocktest:

- Draftandring i solfilter andrar inte `rendered_snapshot.input_fingerprint` fore apply.
- Draftandring i vindlager andrar inte `rendered_snapshot.layers` fore apply.
- Apply skapar ny `rendered_snapshot` nar applied input faktiskt andras.
- Leaflet overlay-toggle andrar inte `rendered_snapshot` och triggar inte ny analys.
- Baslagerbyte andrar inte `rendered_snapshot`.
- `Potentiell etableringsyta` klassar fyra fall korrekt: vind+sol, endast vind, endast sol, inte lamplig.
- Scenario allocation kan visas/slackas separat fran potentiallagret.
- Outside-LP feature har `is_schematic = true` och `is_real_location = false`.
- Trondelag snapshot innehaller `data_status` for 250 m befolkningsproxy och syntetisk social acceptans.
- Trondelag accepterar bara R7/R6/R5 om ingen ny datapolicy lagts till.
- Bornholm och Trondelag valideras separat med sina native CRS.

## Stabil kartvy

Berakningskedjan ska inte styra kartans view. Kartvy ar UI-only state:

- `fitBounds` far ske vid forsta render/ny region/ingen sparad view.
- Layer toggle far aldrig kora om analys eller fitBounds.
- Ny applied snapshot far uppdatera lager, men bor bevara kartvy for samma region.

Detta hor ihop med `exports/v3_migration/leaflet_view_persistence_inventory.md`.
