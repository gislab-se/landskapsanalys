# Potential Analysis Pipeline Inventory

Syfte: detta dokument beskriver hur V2 skapar berakningsunderlaget bakom resultatlagren, inte hur Leaflet renderar dem. Rendering och lagerkontroll finns redan i:

- `exports/v3_migration/potential_result_layers_inventory.md`
- `exports/v3_migration/potential_result_layer_specs.json`
- `exports/v3_migration/potential_result_v3_recommendation.md`

Viktig V3-regel: V3 ska bygga resultat fran applied state och publicera dem till `rendered_snapshot.layers`. Karta och hogerpanel ska lasa `rendered_snapshot`, inte draft/widgetkeys.

## Kort kedja

V2:s resultatkedja kan lasas som:

1. Regionmanifest och scenario/energimodell laddas.
2. Sol- och vindkontroller ligger forst i draft/UI-state.
3. Vid Apply kopieras sol-draft till `solar_applied_config`; vindens apply invalidaterar arbetscache och gor valda lager/parametrar till berakningsinput.
4. Vindpotential och solpotential byggs som H3-ramar med `hex_id`, potentialandel/area och teknikscore.
5. Energiscenario raknas om till ytbehov per teknik.
6. Scenarioyta allokeras inuti potentialen; eventuell brist expanderas som "Utanför LP".
7. Combined-resultat byggs av potentialramar + allokeringsramar.
8. GeoJSON-resultat skapas av de kombinerade ramarna.

## V2-entrypoint och cache

- `potential_app.py:12335` `_unified_workspace_tab(...)` ar huvudflodet for den gemensamma potentialvyn.
- `potential_app.py:12440` satter `analysis_h3_resolution = _analysis_h3_resolution(region)`.
- `potential_app.py:12642-12644` sparar analys- och displayupplosning i `energy_model_state`.
- `potential_app.py:2220` `_workspace_calculation_fingerprint(...)` bygger cachefingerprint for berakningen.
- `potential_app.py:2248-2268` fingerprint inkluderar region, scenario, H3-resolution, applied solkonfig, vindlager, vindparametrar, energimodell och acceptansval.
- `potential_app.py:168` `WORKSPACE_RENDER_CACHE_KEY = "potential_workspace_render_cache_v2"`.
- `potential_app.py:2281` `_cached_workspace_payload(...)` laser senaste arbetsyta om fingerprint matchar.
- `potential_app.py:2290` `_invalidate_workspace_cache(...)` rensar rendercache.
- `potential_app.py:13457` sparar byggda `layers`, `map_state`, `energy_model_state` och metadata i `WORKSPACE_RENDER_CACHE_KEY`.

Detta ar en V2-implementation, men principen ar viktig for V3: en berakningsfingerprint ska bygga pa applied state och dataversioner, inte pa UI-only karta/lager-toggle.

## Region, CRS och H3-policy

- `apps/potential_model/manifests/regions/bornholm.json:6-14`: Bornholm har `native_crs = EPSG:25833`, `web_crs = EPSG:4326`, tillgangliga H3 `[6,7,8,9,10]`, `default_h3_resolution = 10`, `default_display_h3_resolution = 8`.
- `apps/potential_model/manifests/regions/trondelag.json:6-13`: Trondelag har `native_crs = EPSG:25832`, `web_crs = EPSG:4326`, tillgangliga H3 `[7,6,5]`, `default_h3_resolution = 7`, `default_display_h3_resolution = 7`.
- `apps/potential_model/manifests/regions/trondelag.json:28`: Trondelag kor en latt R7-runtime; R6/R5 ar rollups och R8/R9 exponeras inte.
- `potential_app.py:3522` `_analysis_h3_resolution(region, preferred=WIND_RUNTIME_BASE_RESOLUTION)` valjer analysupplosning utifran regionens default/available.
- `potential_app.py:11539-11541` informerar anvandaren nar karta visas i annan upplosning an analysen.

V2 publicerar webbgeometrier i EPSG:4326. Distans, buffert och regional native-analys ska for V3 ske i regionens native CRS: Bornholm `EPSG:25833`, Trondelag `EPSG:25832`.

## Energimodell och ytbehov

Huvudfunktioner:

- `apps/potential_model/energy_modeling.py:231` `load_energy_model_inputs(manifest, root)` laddar TIMES/energy mix, scenariobeskrivningar och area-demand bundle.
- `apps/potential_model/energy_modeling.py:332` `planning_scenarios(manifest)` skapar planeringsscenarier.
- `apps/potential_model/energy_modeling.py:374` `select_planning_mix(mix, scenario)` filtrerar och skalar energimix.
- `apps/potential_model/energy_modeling.py:832` `calculate_area_demand(times_mix, area_bundle, area_scenario_id, technology_to_times)` raknar `twh`, `km2_per_twh` och `area_need_km2`.
- `potential_app.py:3186` anvander state key `energy_model_planning_scenario_<region_id>`.
- `potential_app.py:3214` anvander state key `energy_model_area_scenario_<region_id>`.
- `potential_app.py:3268` anropar `calculate_area_demand(...)`.
- `potential_app.py:3292` anvander state key `energy_model_show_proposal_<region_id>`.
- `potential_app.py:3013` `_balance_wind_solar_mix(...)` justerar vind/sol-balans.
- `potential_app.py:3050` `_energy_mix_solar_share_from_session(region)` laser mix-slidern.

Resultat fran energimodellen laggs i `energy_model_state`, bland annat:

- `wind_area_need_km2`
- `solar_area_need_km2`
- `wind_twh`
- `solar_twh`
- `wind_km2_per_twh`
- `solar_km2_per_twh`
- `analysis_h3_resolution`
- `display_h3_resolution`

Trondelag-avvikelse: `apps/potential_model/manifests/regions/trondelag.json:28` anger att energiscenarier fortfarande anvander Bornholm-placeholder TIMES/AreaDemand tills EML eller norsk motsvarighet finns.

## Sol: applied/draft och inputs

Konstanter och default:

- `potential_app.py:178` `SOLAR_APPLIED_CONFIG_KEY = "solar_applied_config"`.
- `potential_app.py:219` `SOLAR_FILTER_GROUP_SPECS` definierar filtergrupper, lagernycklar, draftnycklar, buffertnycklar och effekt.
- `potential_app.py:278-299` elinfrastruktur har `effect = "feasibility"` och anvander `solar_grid_max_distance_m` som positiv narhetsregel.
- `potential_app.py:395-430` `DEFAULT_SOLAR_APPLIED_CONFIG` satter bland annat `large_scale_active`, `large_population_active`, skyddade lager, vagfilter, kultur, rennaring, `population_buffer_m`, `protected_buffer_m`, `road_buffer_m` och `solar_grid_max_distance_m`.

Statehantering:

- `potential_app.py:4329` `_solar_config_from_session()` laser applied solkonfig.
- `potential_app.py:4360` `_prime_solar_draft_state(config)` fyller draft controls fran applied.
- `potential_app.py:4385` `_solar_draft_config_from_session()` bygger ny applied-konfig fran draft keys.
- `potential_app.py:12550` Apply skriver `st.session_state[SOLAR_APPLIED_CONFIG_KEY] = _solar_draft_config_from_session()`.
- `potential_app.py:12371-12379` huvudflodet laser applied solkonfig och bygger `solar_large_filter_configs`.

Viktigt for V3: draftnycklar som `solar_draft_*` ska aldrig lasas av result-byggaren. Result-byggaren ska fa en normaliserad applied-konfig.

## Sol: potentialramar

Smaskalig sol:

- `potential_app.py:440-448` pekar ut befolkningsunderlag och count-kolumn for sol v1.
- `potential_app.py:4794` `_solar_v1_frame(region, landscape_manifest, resolution, panel_area_m2_per_person)` bygger smaskalig sol fran befolkning per H3.
- `potential_app.py:4821-4828` raknar `solar_v1_area_m2`, `solar_v1_area_km2`, log-baserad `solar_v1_score` och klass.

Storskalig sol:

- `potential_app.py:5200` `_solar_population_buffer_frame(...)` skapar befolkningsbuffertandel per H3; for Trondelag anvands 250 m befolkningsrutproxy.
- `potential_app.py:5394` `_solar_filter_runtime_result(...)` bygger buffer/resultat for en solfiltergrupp.
- `potential_app.py:5555` `_solar_filter_buffer_frame(...)` oversatter filterbuffert till H3-andel.
- `potential_app.py:5600` `_solar_filter_union_buffer_frame(...)` unionerar filterandelar med max per H3.
- `potential_app.py:5813` `_solar_large_scale_frame(...)` bygger storskalig solpotential fran landskapsramen och aktiva filter.
- `potential_app.py:5841-5855` satter `active_filter_configs`, inklusive befolkning, skyddad natur och konfigurerade filtergrupper.
- `potential_app.py:5865-5872` ofiltrerat startlage ger 100 procent potentialyta och `solar_score = 100`.
- `potential_app.py:5894-5914` exclusion-filter drar av `protected_buffer_share_pct` fran `potential_area_share_pct`.
- `potential_app.py:5920-5932` feasibility-filter, framfor allt elinfrastruktur, multiplicerar aterstaende potential med `feasibility_share_pct`.
- `potential_app.py:5936-5965` raknar `potential_area_m2`, `potential_area_km2`, `potential_area_share_pct`, `solar_score`, `solar_class`, `solar_class_label`, `solar_color`.

Kombinerad solpotential:

- `potential_app.py:5969` `_combined_solar_hex_frame(...)` kombinerar smaskalig och storskalig sol.
- `potential_app.py:5984-6026` bevarar `large_filter_buffer_share_pct` och `large_filter_buffer_area_m2`.
- `potential_app.py:6029-6039` summerar small + large area, klipper till hexarea och skapar `solar_score`, `solar_group`, `solar_class`, `solar_class_label`, `solar_color`.

Solens scenarioallokering:

- `potential_app.py:6175` `_solar_establishment_frame(...)` bygger kandidater fran smaskalig och storskalig sol.
- `potential_app.py:6232-6245` lagger in storskaliga kandidater med `potential_score` och `potential_area_km2`.
- `potential_app.py:6251-6254` returnerar tomt resultat med `unmet_area_km2` om behov eller kandidater saknas.
- `potential_app.py:6259` prioriterar med `_apply_landscape_priority_to_allocation_frame(...)`.
- `potential_app.py:6265` prioriterar med `_apply_social_acceptance_priority_to_solar_candidates(...)`.
- `potential_app.py:6289-6313` allokerar area tills `solar_area_need_km2` ar fylld och skapar `allocated_area_km2`, `allocated_twh`, `allocated_gwh`, `allocated_hex_share_pct`, `selected_rank`.
- `potential_app.py:6415` `_expand_solar_area_outside_lp(...)` lagger till solyta utanfor LP nar scenariot inte ryms.
- `potential_app.py:12946-12976` huvudflodet bygger solens `solar_proposal_frame`, expanderar utfor LP och sparar i `energy_model_state`.

## Vind: inputs och acceptance

Vindens regler finns bade i modulform och som runtime-spår i appen.

Generell acceptance-modul:

- `apps/potential_model/wind_acceptance.py:20` `WIND_GROUP_LAYER_DEFAULTS` definierar default lager per vindgrupp.
- `apps/potential_model/wind_acceptance.py:59` `GROUP_PARAM_MAP` mappar grupp till parameter, t.ex. `settlement_distance_m`, `road_distance_m`, `grid_max_distance_m`, `protected_buffer_m`, `culture_buffer_m`.
- `apps/potential_model/wind_acceptance.py:147` `_group_distance_frame(...)` kombinerar avstands-/intersections-tabeller for valda lager.
- `apps/potential_model/wind_acceptance.py:194` `_distance_conflict_acceptance(...)` ger rampad acceptans fran 0 vid troskel till 1 vid 2x troskel.
- `apps/potential_model/wind_acceptance.py:210` `_proximity_acceptance(...)` ger positiv feasibility nara t.ex. elnat.
- `apps/potential_model/wind_acceptance.py:223` `_hard_exclusion_acceptance(...)` blockerar hard exclusion.
- `apps/potential_model/wind_acceptance.py:237` `_acceptance_for_kind(...)` valjer acceptancefunktion utifran `analysis_kind`.
- `apps/potential_model/wind_acceptance.py:268` `_build_wind_acceptance_frame_cached(...)` kombinerar basvindpotential med gruppacceptans.
- `apps/potential_model/wind_acceptance.py:361` `wind_acceptance_potential_frame(...)` ar publikt wrapper-anrop.
- `potential_app.py:7037` `_wind_source_frame(...)` anropar `wind_acceptance_potential_frame(...)`.

Runtime-spår i appen:

- `potential_app.py:7221` `_default_wind_params()` skapar default vindparametrar.
- `potential_app.py:7890` `_selected_wind_layers()` laser valda vindlager.
- `potential_app.py:8029` `_wind_group_controls(...)` ar UI/apply-kontrollen for vindgrupper.
- `potential_app.py:8931` `_acceptance_series_for_group(...)` implementerar samma acceptance-typer for snabb runtime.
- `potential_app.py:8956` `_finalize_fast_wind_share_frame(...)` satter `potential_area_share_pct`, `potential_area_km2`, klass, farg och core-score.
- `potential_app.py:8989` `_wind_fast_distance_runtime_result(...)` ar Trondelag-optimerad fast-distance-runtime; den startar fran 100 procent potential per displayhex och kombinerar valda gruppavstand.
- `potential_app.py:9041-9055` reducerar acceptans per grupp, markerar roll `feasible` for proximity och `conflict` for andra grupper.
- `potential_app.py:9075` `_wind_runtime_hex_layer_frame(...)` bygger H3-frame fran runtime-resultat.
- `potential_app.py:9096` `_wind_runtime_hex_feature_collection(...)` gor vindpotentialens GeoJSON.
- `potential_app.py:10831` `_wind_polygon_preview_state(...)` valjer forst fast Trondelag-resultat och faller annars tillbaka till `_wind_runtime_result(...)`.
- `potential_app.py:11137` `_wind_runtime_result(...)` ar generellt runtime-resultat for vind.

Vindens scenarioallokering:

- `apps/potential_model/energy_modeling.py:866` `allocate_wind_area_from_core_hexes(...)` valjer vindhexar tills ytbehovet ar fyllt.
- `apps/potential_model/energy_modeling.py:931-943` delar kandidater i `"Karn-LP"` och `"Kompletterande LP"` och raknar potentialarea.
- `apps/potential_model/energy_modeling.py:956-968` sorterar efter `allocation_priority_score`, `core_score`, `potential_area_share_pct`, fas, zonstorlek, area, reservation och `hex_id`.
- `apps/potential_model/energy_modeling.py:970-998` allokerar `allocated_area_km2`, `allocated_hex_share_pct`, `selected_rank` och `unmet_area_km2`.
- `potential_app.py:10698` `_expand_wind_area_outside_et(...)` expanderar vindyta utanfor LP nar brist finns.
- `potential_app.py:10709-10716` laser `unmet_area_km2` som brist.
- `potential_app.py:10746-10763` valjer displayhex utanfor potentialen via granne/expansion ring.
- `potential_app.py:10769-10798` skapar outside-rader med `outside_et = True`, `allocation_phase = "Utanför LP"`, `allocated_area_km2` och uppdaterad briststatistik.
- `potential_app.py:13066-13107` huvudflodet prioriterar vind, allokerar, expanderar utfor LP och sparar `energy_model_state["proposal_frame"]` och `proposal_stats`.

## Landskap och social acceptans i prioritering

- `apps/potential_model/potential.py:98` `apply_potential_classes(...)` klassar teknikscore.
- `apps/potential_model/potential.py:113` `rollup_potential_frame(...)` rullar H3 till grovre upplosning och bevarar klass-/landskapskontext.
- `apps/potential_model/potential.py:277` `wind_potential_frame(...)` ar ett aldre landskaps-/faktorbaserat vindspår.
- `potential_app.py:8805` `_apply_landscape_priority_to_allocation_frame(...)` skapar landskaps-/teknikprioritet for allokering.
- `potential_app.py:7623` `_social_acceptance_values_frame(...)` laser social acceptance per scenario.
- `potential_app.py:7698` `_merge_social_acceptance_for_priority(...)` mergar acceptans till allokeringskandidater.
- `potential_app.py:7719` `_apply_social_acceptance_priority_to_wind_allocation_frame(...)` prioriterar vindkandidater.
- `potential_app.py:7750` `_apply_social_acceptance_priority_to_solar_candidates(...)` prioriterar solkandidater.
- `potential_app.py:7655` `_apply_social_acceptance_impact_to_establishment_frame(...)` paverkar farg/vikt i etableringslagret.

Social acceptans ar inte slutgiltig forskningsdata i nuvarande manifests:

- `apps/potential_model/manifests/social_acceptance/bornholm_synthetic_acceptance_v0.json:5-6` anger `synthetic_test_data` och `synthetic = true`.
- `apps/potential_model/manifests/social_acceptance/bornholm_synthetic_acceptance_v0.json:31` sager uttryckligen att datan ar syntetisk testdata, inte IVL research data.
- `apps/potential_model/manifests/social_acceptance/trondelag_synthetic_acceptance_v0.json:5-6` anger samma for Trondelag.
- `apps/potential_model/manifests/social_acceptance/trondelag_synthetic_acceptance_v0.json:31` sager att Trondelag speglar Bornholm-flodet pa H3 R7 och anvander landskapsfaktorer som proxies.

## Combined-resultat: potentiell etableringsyta

Source/potential till combined:

- `potential_app.py:9254` `_establishment_source_frame(...)` normaliserar valda scenario/allokeringsrader per teknik.
- `potential_app.py:9331-9336` satter `<technology>_outside_lp`, `<technology>_suitable`, `<technology>_conflict_area_km2`.
- `potential_app.py:9346` `_potential_establishment_source_frame(...)` normaliserar hela potentialkallan per teknik.
- `potential_app.py:9368-9396` laser vind/solscore, area och filtershare-kolumner som `large_filter_buffer_share_pct`, `filter_buffer_share_pct`, `protected_buffer_share_pct`.
- `potential_app.py:9432-9435` har Trondelag-specifik coarse-filter-blockering for grov display nar filtershare indikerar traff.

Klassning:

- `potential_app.py:2308` `ESTABLISHMENT_CLASS_SPECS` definierar `not_suitable`, `wind_only`, `solar_only`, `wind_and_solar`.
- `potential_app.py:9441` `_combined_establishment_class(wind_suitable, solar_suitable)` mappar boolean-par till klass.
- `potential_app.py:9451` `_dominant_establishment_class_from_areas(...)` anvands vid Trondelag-rollup.
- `potential_app.py:9463` `_apply_establishment_style_columns(...)` satter `establishment_label`, `fill`, `stroke`, `stroke_weight`, `fill_opacity`.

Ram for potentiell etableringsyta:

- `potential_app.py:9676` `_combined_potential_establishment_frame(...)` ar huvudramen for resultatlagret `Potentiell etableringsyta`.
- `potential_app.py:9685-9690` startar fran alla displaygeometrier.
- `potential_app.py:9693-9710` rullar Trondelag fran källupplosning till grovre display vid behov.
- `potential_app.py:9712-9723` bygger vind- och solkalla via `_potential_establishment_source_frame(...)`; for Trondelag kan grova solfilter blockera vid intersection.
- `potential_app.py:10652` `_combined_potential_establishment_family_layers(...)` bygger Leaflet-layerfamiljen fran combined frame.
- `potential_app.py:10670-10686` anropar `_combined_potential_establishment_frame(...)`, applicerar social acceptance impact och returnerar `_combined_establishment_layer(...)`.

GeoJSON:

- `potential_app.py:10486` `_combined_establishment_feature_collection(...)` skapar GeoJSON.
- `potential_app.py:10494-10515` popupen innehaller per-teknik information om potential efter filter, potentialscore, potentiell yta, scenarioyta, scenarioenergi och konfliktarea.
- `potential_app.py:10517-10521` matchar varje `hex_id` mot displaygeometri.
- `potential_app.py:10555-10576` properties inkluderar `hex_id`, `establishment_class`, `establishment_label`, `outside_lp_shortage`, `outside_lp_reason`, `wind_outside_lp_area_km2`, `solar_outside_lp_area_km2`, `wind_suitable`, `solar_suitable`, styling, social acceptance och tooltip/popup.

## Scenariofordelning i etableringshex

- `potential_app.py:10269` `SCENARIO_ALLOCATION_SPECS` definierar farger for `wind`, `solar`, `both`.
- `potential_app.py:10291` `_scenario_allocation_class(...)` valjer `both`, `wind` eller `solar` utifran allokerad area och om overlap ska markeras.
- `potential_app.py:10309` `_scenario_allocation_child_cell(...)` skapar center-child i `target_resolution + 1` for att visa scenarioyta som mindre markor i parent-hex.
- `potential_app.py:10325` `_scenario_allocation_marker_feature_collection(...)` skapar GeoJSON for scenariofordelningen.
- `potential_app.py:10362-10411` properties inkluderar `hex_id` (child), `parent_hex_id`, `allocation_class`, `allocation_label`, `wind_allocated_area_km2`, `solar_allocated_area_km2`, styling, tooltip och popup.
- `potential_app.py:10418` `_scenario_allocation_marker_layer(...)` skapar resultatlagret.
- `potential_app.py:10454` `_scenario_allocation_marker_family_layers(...)` bygger layer family; Trondelag startar som ej default-visible.
- `potential_app.py:13213-13222` huvudflodet bygger och lagger till `allocation_marker_layers`.

Detta lager ar scenarioresultat, inte source/buffer. Det visar vald placering enligt energimodellens ytbehov och prioritering.

## Ytbehov utanfor landskapets potential

Vind och sol kan fa brist (`unmet_area_km2`) nar scenarioyta inte ryms i potentialen. V2 visualiserar bristen schematiskt.

- `potential_app.py:10698` `_expand_wind_area_outside_et(...)` lagger till vindrader utanfor LP.
- `potential_app.py:6415` `_expand_solar_area_outside_lp(...)` lagger till solrader utanfor LP.
- `potential_app.py:10069` `_outside_lp_need_feature_collection(...)` summerar `wind_outside_lp_area_km2` och `solar_outside_lp_area_km2`.
- `potential_app.py:10049-10063` schematiska features har properties `schematic_technology`, `schematic_label`, `represented_area_km2`, `represented_base_hex_count`, `display_resolution`, styling, tooltip och popup.
- `potential_app.py:10188` `_outside_lp_need_layer(...)` skapar lagret.
- `potential_app.py:10225` `_outside_lp_need_family_layers(...)` bygger layer family.
- `potential_app.py:13231-13242` huvudflodet bygger och lagger till outside-LP-lagret.
- `potential_app.py:13415-13424` huvudflodet skriver notis nar extra yta kravs.

Viktigt: outside-LP-lagret ar inte verklig placering. V2 markerar det som schematiskt extra ytbehov.

## Source layer, buffer layer och result layer

Begreppsmassigt i V2:

- Source layers ar GIS-kallor som befolkning, vagar, skyddad natur, kulturmiljo, elinfrastruktur. De kan visas i kartan men ar inte resultat.
- Buffer layers ar avledda geometrier/andelar kring source layers och anvands som restriktions- eller feasibility-input.
- Result layers ar beraknade fran potentialramar och scenarioallokering: `Potentiell etableringsyta`, `Scenariofördelning i etableringshex`, `Ytbehov utanför landskapets potential`.

Viktigt: V2:s UI kan visa source/buffer separat, men berakningen ska inte styras av om ett lager ar synligt i Leaflet. Synlighet ar UI-state. Berakningsinput ar valda applied-lager och parametrar.

## Restriktionslogik

Vind:

- `hard_exclusion`: blockerar helt vid intersection eller avstand <= troskel.
- `distance_conflict`: minskar acceptans nar cellen ligger for nara konfliktobjekt; acceptans rampas upp till 1 vid 2x troskel.
- `proximity_feasibility`: positiv narhetsregel; celler langt fran t.ex. elinfrastruktur far lagre/ingen feasibility.
- Gruppacceptanser kombineras som minimum/produktliknande reduktion i runtime-flodet; hard block satter potential till 0.

Sol:

- Exclusion-filter drar bort buffertandel fran kandidatytan.
- Feasibility-filter multiplicerar aterstaende kandidatytan med narhetsandel.
- Smaskalig sol ar en separat befolkningsschablon och kombineras med storskalig sol efter att filter applicerats.
- Storskalig sol startar fran landskapsunderlaget och kan i ofiltrerat lage vara 100 procent per hex.

Combined:

- `wind_suitable` och `solar_suitable` ar teknikvisa booleaner efter potential/filter.
- `wind_and_solar` betyder att bada teknikerna ar mojliga i samma etableringshex.
- `wind_only` och `solar_only` betyder att bara en teknik ar mojlig.
- `not_suitable` betyder att ingen teknik har potential efter filter.

## Riktig analys, proxy och placeholder

Bornholm:

- Har etablerad landskapsmanifest `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json`.
- `bornholm_landscape_v10.json:53` anger att v10 anvander v9 K=8 pa H3 R10 och rullar upp till grovre visningsnivaer.
- Social acceptans ar syntetisk testdata, inte IVL research data (`bornholm_synthetic_acceptance_v0.json:5-6`, `:31`).

Trondelag:

- `apps/potential_model/manifests/regions/trondelag.json:28` sager att appen ar en latt R7-runtime med R6/R5 rollups; R8/R9 ar inte exponerade.
- Befolkning/settlement-buffer ar 250 m rutproxy, inte individpunkter (`potential_app.py:12464`, `potential_app.py:12504-12506`).
- `apps/potential_model/manifests/landscape/trondelag_landscape_placeholder.json:107` sager att bundle ar data-driven R7 runtime, men LABLAB:s landskapsanalys ar separat experimentell R7-landskapstypslayer och inte bas-`landscape_geojson` eller factor scores.
- Social acceptans ar syntetisk testdata och proxy (`trondelag_synthetic_acceptance_v0.json:5-6`, `:31`).
- Energiscenarier anvander Bornholm-placeholder tills regionala data finns (`regions/trondelag.json:28`).

PDF-landskap for Trondelag:

- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md:7-12` beskriver malet och att PDF-kartan ar presentationsgrafik, inte ren GIS.
- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md:79` sager att raster/polygoniseringsforsok ar nyttiga experiment men inte finala.
- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md:178-180` markerar outputs som experimentella och noterar risk att `LT09` blandats ihop.
- `AGENTS.md:57-63` sager att PDF-derived outputs inte ska behandlas som finala utan handoff/review och att alla 9 landskapstyper, sarskilt `LT09 Vidsträckt fjällandskap`, maste kontrolleras.

## GeoJSON-resultat och properties

V2 skapar Leaflet-GeoJSON i EPSG:4326 fran H3-displaygeometrier.

Potentiell etableringsyta:

- Feature id: `hex_id`.
- Klassning: `establishment_class`, `establishment_label`.
- Teknikflags: `wind_suitable`, `solar_suitable`.
- Konflikt/shortage: `outside_lp_shortage`, `outside_lp_reason`, `wind_outside_lp_area_km2`, `solar_outside_lp_area_km2`.
- Stil: `fill`, `stroke`, `stroke_weight`, `fill_opacity`.
- UI: `tooltip_title`, `tooltip_body`, `popup`.
- Social acceptance: `social_acceptance_impact_pct`, `social_acceptance_value`, `social_acceptance_weight`, `social_acceptance_source_hex_count`.

Scenariofordelning:

- Feature id: child `hex_id`.
- Parent: `parent_hex_id`.
- Klassning: `allocation_class`, `allocation_label`.
- Allokering: `wind_allocated_area_km2`, `solar_allocated_area_km2`.
- Stil och UI: `fill`, `stroke`, `stroke_weight`, `fill_opacity`, `tooltip_title`, `tooltip_body`, `popup`.

Ytbehov utanfor LP:

- Feature id: schematic `hex_id`.
- Typ: `schematic_technology`, `schematic_label`.
- Representerad area: `represented_area_km2`, `represented_base_hex_count`, `display_resolution`.
- Stil och UI: `fill`, `stroke`, `stroke_weight`, `fill_opacity`, `tooltip_title`, `tooltip_body`, `popup`.

## V3-observationer

Det V3 bor porta:

- Normaliserade analysramar per teknik med `hex_id`, potentialscore, potentialarea, suitability, allocationarea, rank och outside-LP fields.
- Separat berakningskontrakt for applied inputs, skilt fran Leaflet layer visibility.
- Regionens native CRS och H3-policy.
- Explicit markering av proxy/synthetic/experimental status i kontrakt/debug/test, inte som huvudlagertext.

Det V3 bor forenkla:

- Samla vindens dubbla spår till ett tydligt analysis service-kontrakt.
- Gora solens exclusion/feasibility-filter till deklarativa operationer i applied state.
- Skapa strukturerade properties for popupdata i stallet for att bara stoppa siffror i HTML.

Det V3 bor undvika:

- Att lasa `solar_draft_*`, widgetkeys eller Leaflet visibility i analysen.
- Att tolka outside-LP som faktisk placering.
- Att exponera Trondelag R8/R9 i appen utan nytt databeslut.
- Att behandla syntetisk social acceptans eller PDF-derived landskap som slutgiltig analysdata.
