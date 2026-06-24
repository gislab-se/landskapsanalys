# Potential App Data Inventory

Status: 2026-05-22
Scope: data that the shared Streamlit potential app can load from current manifests and registries.

Primary source files:

- `apps/potential_model/manifests/regions/*.json`
- `apps/potential_model/manifests/landscape/*.json`
- `apps/potential_model/manifests/potential/*.json`
- `apps/potential_model/manifests/scenarios/*.json`
- `apps/potential_model/manifests/social_acceptance/*.json`
- `apps/acceptance_model/registry.json`
- `apps/acceptance_model/registry_trondelag.json`

## Category Definitions

| Category | Definition | App role |
| --- | --- | --- |
| Region/geometri | Regionmanifest, map center, CRS, H3 display geometry, landmask or clipped H3 geometry. | Defines where the app opens and which H3 resolutions can be shown. |
| Landskapsanalys | Landscape type, cluster/structure, factor scores and factor metadata. | Base layer for landscape interpretation and for derived potential scoring. |
| Landskapspotential | Derived solar and wind potential from landscape roles plus active runtime filters. | Shows where solar/wind can fit under current assumptions. |
| Scenario/ytbehov | TIMES/energy scenario inputs and AreaDemand land-intensity assumptions. | Converts low/medium/high energy scenarios into land demand. |
| Scenariofördelning | Child-hex allocation of scenario area inside establishment/potential hexes. | Shows where the scenario is placed inside available potential. |
| Social acceptans | Synthetic acceptance values by H3 cell and scenario. | Optional modifier for potential and allocation priority. |
| Acceptans-/begränsningslager | Runtime source layers grouped by settlement, transport, grid, culture, protected nature, land use, reindeer, aviation, military, coastal. | Buffers, exclusions, distance conflicts and proximity feasibility. |
| Kandidatkatalog | Candidate GIS sources listed for future regional wiring. | Not necessarily visible in the app unless wired into a registry/manifest. |

## Regions

| Region | Status | Native CRS | Visible H3 levels | Main app data |
| --- | --- | --- | --- | --- |
| Bornholm | active | `EPSG:25833` | R10, R9, R8, R7, R6 | Bornholm v10 landscape types, Bornholm wind/solar rules, Bornholm synthetic social acceptance, Bornholm wind-acceptance source registry. |
| Trondelag | active | `EPSG:25832` | R7, R6, R5 | Offshore-trimmed R7 landscape bundle, placeholder wind/solar rules, Trondelag synthetic social acceptance, Trondelag runtime source registry. |
| Vara | planned | TBD | none | Region shell only; no landscape/potential/scenario manifests wired. |

## Logical Map Layers

These are the layer names users see in the shared potential app. Several are computed dynamically from the source layers further below.

| Layer name in app | Category | Definition |
| --- | --- | --- |
| Landskapstyper | Landskapsanalys | H3 landscape type layer from the regional landscape manifest. |
| Landskapstrukturer | Landskapsanalys | Cluster/structure layer from the regional landscape model. |
| Landskapsfaktorer | Landskapsanalys | Factor score layer; user can choose factor. |
| LABLAB:s Landskapsanalys | Landskapsanalys, experimental | Separate Trondelag R7 landscape-type layer with 18,530 H3 hexes inside the fylke boundary, including fjords/water as part of the landscape context. |
| Landskapspotential Vind | Landskapspotential | Derived wind potential from landscape roles and active wind filters. |
| Landskapspotential Vind polygon | Landskapspotential | Polygon/source version of wind potential and wind filter outputs. |
| Landskapspotential Vind hexagon | Landskapspotential | H3 share/hex visualization of wind potential. |
| Landskapspotential Sol | Landskapspotential | Derived solar potential from small-scale roof proxy and large-scale land potential. |
| Landskapspotential Sol polygon | Landskapspotential | Polygon/source version of solar potential. |
| Landskapspotential Sol hexagon | Landskapspotential | H3 visualization of solar potential. |
| Småskalig anläggning på tak | Landskapspotential | Schematic small-scale solar area from population/hex assumptions. |
| Storskalig anläggning på land | Landskapspotential | Large-scale solar candidate area after active filters. |
| Potentiell etableringsyta | Landskapspotential | Combined establishment layer: wind only, solar only, both, or not suitable. |
| Scenariofördelning i etableringshex | Scenariofördelning | Scenario area allocated into child hexes and ranked by technical/landscape/social priority. |
| Ytbehov utanför landskapets potential | Scenario/ytbehov | Schematic outside-potential area when the selected scenario does not fit. |
| Social acceptans | Social acceptans | Synthetic low/medium/high acceptance score by H3 cell. |

## Landscape Types

### Bornholm

| ID | Name | Category |
| --- | --- | --- |
| LT01 | Klippigt kustlandskap | Landskapstyp |
| LT02 | Sandigt kustlandskap | Landskapstyp |
| LT03 | Jordbruksdominerat sprickdalslandskap | Landskapstyp |
| LT04 | Skogsklätt sprickdalslandskap | Landskapstyp |
| LT05 | Slätt- och jordbrukslandskap | Landskapstyp |

### Trondelag

| ID | Name | Category |
| --- | --- | --- |
| LT01 | Coastal settlement and infrastructure mosaic | Landskapstyp |
| LT02 | Open inland geology and protection landscape | Landskapstyp |
| LT03 | Forested roaded valley landscape | Landskapstyp |
| LT04 | Low fjord and island coastal fringe | Landskapstyp |
| LT05 | High open protected mountain landscape | Landskapstyp |
| LT06 | Coastal fjord forest-open mosaic | Landskapstyp |
| LT07 | Small near-sea settlement and heritage outliers | Landskapstyp |
| LT08 | Inland upland water and geology belt | Landskapstyp |

## Landscape Factors

### Bornholm

| Factor | Name | Category |
| --- | --- | --- |
| F1 | Sprickdal och brant relief | Landskapsfaktor |
| F2 | Flygsand och sandpräglad kust | Landskapsfaktor |
| F3 | Skog och skyddad natur | Landskapsfaktor |
| F4 | Tätort och byggd struktur | Landskapsfaktor |
| F5 | Låglänt öppet land | Landskapsfaktor |

### Trondelag

| Factor | Name | Category |
| --- | --- | --- |
| F1 | Settlement roads and holiday-home intensity | Landskapsfaktor |
| F2 | Rivered inland relief versus sea coast | Landskapsfaktor |
| F3 | Urban and built-up centres | Landskapsfaktor |
| F4 | Cultural-holiday belts versus inland water | Landskapsfaktor |
| F5 | Schist-phyllite and heritage versus granitic gneiss | Landskapsfaktor |

## Scenario And Acceptance Data

| Region | Dataset/layer name | Category | Definition |
| --- | --- | --- | --- |
| Bornholm | Bornholm sol- och vindpotential v0 | Landskapspotential | Dynamic scaffold for solar and wind potential rules. |
| Trondelag | Trondelag sol- och vindpotential placeholder | Landskapspotential | Placeholder manifest; shared controls are active while regional calibration is incomplete. |
| Bornholm | `bornholm_energy_model_duckdb_v0` | Scenario/ytbehov | Prototype low/medium/high scenarios from `speedlocal_times.duckdb` and `AreaDemand.xlsx`. |
| Trondelag | `trondelag_bornholm_energy_model_placeholder` | Scenario/ytbehov | Uses Bornholm TIMES/AreaDemand placeholder data until regional Norwegian scenario data exists. |
| Bornholm | Bornholm syntetisk social acceptans v0 | Social acceptans | Synthetic H3 R10 acceptance data, not research data. |
| Trondelag | Trondelag syntetisk social acceptans v0 | Social acceptans | Synthetic H3 R7 acceptance data, not research data. |

## Trondelag Source Layers Wired In The App

| Layer name | Category | Analysis type | App layer id | Source key |
| --- | --- | --- | --- | --- |
| Befolkning 250 m rutor (centroidproxy) | Bebyggelse/befolkning | Distance conflict | `population_points` | `trl_population_250m_centroids` |
| Tettsted / built centre | Bebyggelse/befolkning | Distance conflict | `built_centre` | `trl_built_centre_tettsted` |
| Fritidshus centroid | Bebyggelse/befolkning | Distance conflict | `built_low_selection` | `trl_holiday_house_centroids` |
| Mellanvägar | Transport | Distance conflict | `roads_medium` | `trl_roads_n500`, `vegkategor = F` |
| Stora vägar | Transport | Distance conflict | `roads_large` | `trl_roads_n500`, `vegkategor in E/R` |
| Kraftnät - transmission | Elinfrastruktur | Proximity feasibility | `high_voltage_lines` | `trl_transmission_network` |
| Sjö-/undervattenskabel | Elinfrastruktur | Proximity feasibility | `underground_cables` | `trl_underwater_cable` |
| Befintliga vindturbiner | Elinfrastruktur | Proximity feasibility | `existing_wind_turbines` | `trl_wind_turbines` |
| Kulturmiljöer och kulturminnen | Kulturmiljö | Hard exclusion | `cultural_preservation` | `trl_cultural_heritage` |
| Värdefulla kulturlandskap | Kulturmiljö | Hard exclusion | `valuable_cultural_environment` | `trl_cultural_landscapes` |
| Naturvernområden | Skyddad natur | Hard exclusion | `protected_areas` | `trl_nature_protection_areas` |
| Skog (N500 markdekke) | Markanvändning | Hard exclusion | `forest_land_cover` | `trl_landcover_n500`, `objtype = Skog` |
| Reindrift - årstidsbete sammanlagt | Rennäring/reindrift | Hard exclusion | `reindeer_grazing_merged` | `trl_reindeer_grazing_merged` |
| Reindrift - flyttleier | Rennäring/reindrift | Hard exclusion | `reindeer_migration_routes` | `trl_reindeer_migration_routes` |

## Bornholm Source Layers Wired In The App

| Layer name | Category | Analysis type | App layer id |
| --- | --- | --- | --- |
| Population points | Bebyggelse/befolkning | Distance conflict | `population_points` |
| Buildings Low | Bebyggelse/befolkning | Distance conflict | `buildings_low` |
| Buildings High | Bebyggelse/befolkning | Distance conflict | `buildings_high` |
| Built Centre | Bebyggelse/befolkning | Distance conflict | `built_centre` |
| Built - Low (Selection) | Bebyggelse/befolkning | Distance conflict | `built_low_selection` |
| Small roads | Transport | Distance conflict | `roads_small` |
| Medium roads | Transport | Distance conflict | `roads_medium` |
| Large roads | Transport | Distance conflict | `roads_large` |
| High-voltage lines | Elinfrastruktur | Proximity feasibility | `high_voltage_lines` |
| Underground cables | Elinfrastruktur | Proximity feasibility | `underground_cables` |
| Power substations | Elinfrastruktur | Proximity feasibility | `power_substations` |
| Existing wind turbines | Elinfrastruktur | Proximity feasibility | `existing_wind_turbines` |
| Cultural preservation | Kulturmiljö | Hard exclusion | `cultural_preservation` |
| Valuable cultural environment | Kulturmiljö | Hard exclusion | `valuable_cultural_environment` |
| Cultural conservation values | Kulturmiljö | Hard exclusion | `cultural_conservation_values` |
| Protected areas | Skyddad natur | Hard exclusion | `protected_areas` |
| Natura 2000 designated land | Skyddad natur | Hard exclusion | `natura_designated_land` |
| Natura bird protection | Skyddad natur | Hard exclusion | `natura_bird_protection` |
| Natura habitat areas | Skyddad natur | Hard exclusion | `natura_habitat_areas` |
| Natura Ramsar | Skyddad natur | Hard exclusion | `natura_ramsar` |
| Nature and wildlife reserve | Skyddad natur | Hard exclusion | `nature_wildlife_reserve` |
| Nature-area forest | Skyddad natur | Hard exclusion | `nature_area_forest` |
| Aviation approach zones | Flyg/luftfart | Hard exclusion | `aviation_approach_zones` |
| Aviation bird-collision zones | Flyg/fågelkollision | Distance conflict | `aviation_bird_collision` |
| Military areas | Militär | Hard exclusion | `military_areas` |
| Coastal zone 3 km | Kust/strandskydd | Hard exclusion | `coastal_zone_3km` |
| Strand protection | Kust/strandskydd | Hard exclusion | `strand_protection` |

## Notes

- Trondelag population/bebyggelse currently uses a 250 m grid/centroid proxy, not individual population points.
- Trondelag R8/R9 landscape layers are intentionally not exposed in the interactive app.
- `LABLAB:s Landskapsanalys` is available as a separate landscape checkbox and uses the R7 fylke-boundary layer with 18,530 hexes. It is still experimental and separate from the offshore-trimmed data-driven base landscape layer.
- Trondelag scenario data is still a placeholder using Bornholm TIMES/AreaDemand inputs.
- Candidate GIS sources in `Trondelag/projects/trondelag/config/potential_app_layer_candidates.csv` are a broader source catalog; only layers listed in `registry_trondelag.json` are wired into the app runtime.
