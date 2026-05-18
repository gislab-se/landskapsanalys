# Potential App Layer Collection Handoff

## Syfte

Denna not sammanfattar kandidatlager for appens landskapspotential-controllers/expanders. Den hor ihop med `projects/trondelag/config/potential_app_layer_candidates.csv`, som ar den maskinlasbara katalogen for lager som kan visas, slas av/paa och kombineras i vind/sol- och andra landskapsrelaterade utvecklingsscenarier.

Reindrift ar medvetet katalogiserat som konflikt-/acceptans- och controllerlager, inte som primar geocontext-landskapstyp for den forsta landskapsanalysen.

## Var jag letade

Jag gick igenom prioriterade Trondelag-kallor i:

- `D:\LABLAB_Energiforsk\Projekt SL01\Geodatakatalog_SL01\Inkommande_SL01\IN_Trondelag_SL01\`
- `D:\LABLAB_Energiforsk\Projekt SL01\Geodatakatalog_SL01\Utkommande_SL01\UT_Trondelag_SL01\`
- `D:\LABLAB_Energiforsk\Projekt SL01\Geodatakatalog_SL01\GeoPackage_SL01\GPKG_TRL_SL01\`
- `D:\LABLAB_Energiforsk\Projekt SL01\Arbetsfil_SL01\Arbetsfiler_TRL_SL01\`

De mest appklara lagren finns i `UTM 32`, `UTM 33/Reindrift`, `UTM 33` och samlings-GPKG:n `QGS_TRL_SL01_Fylke_UTM32_080225.gpkg`. QGIS-projekten `QGS_TRL_SL01_Fylke_UTM32.qgz`, `QGS_TRL_SL01_Fylke_UTM32 _V2.qgz`, `QGS_TRL_SL01_Befaringskarta_UTM32.qgz` och `QGS_TRL_SL01_Nationell_UTM33.qgz` anvandes for att bekrafta display-namn och att lagren faktiskt forekommer i kartprojekten.

## Rekommenderade hogprioritetslager

- Vind: `TRL_WIND_FRAMEWORK_AREAS`, `TRL_WIND_POWER_AREA_STATUS`, `TRL_WIND_PARKS_ACTIVE`, `TRL_WIND_TURBINES`
- El/infrastruktur: `TRL_TRANSMISSION_NETWORK`, `TRL_UNDERWATER_CABLE`, `TRL_AIRPORTS`, `TRL_ROADS_ALL`
- Reindrift: `TRL_REINDEER_GRAZING_MERGED`, `TRL_REINDEER_MIGRATION_ROUTES`, `TRL_REINDEER_RESTRICTION_AREAS`
- Natur/skydd: `TRL_NATURE_PROTECTION_AREAS`, `TRL_PROTECTED_WATERCOURSES`, `TRL_WATER_PROTECTION`
- Kultur/samhalle: `TRL_CULTURAL_HERITAGE`, `TRL_CULTURAL_LANDSCAPES`, `TRL_POPULATION_250M_CENTROIDS`, `TRL_DENSELY_POPULATED_AREAS`, `TRL_HOLIDAY_HOUSES_CENTROIDS`, `TRL_POPULATION_1KM_GRID`
- Bas/context: `TRL_COASTLINE`, `TRL_WATER_AREAS`, `TRL_RIVER_NETWORK`, `TRL_LAND_MASK`, `TRL_ADMIN_FYLKE`

## Bor vara app-toggles

Alla hogprioritetslager ovan bor kunna togglas. Sarskilt viktiga synliga overlays ar reindriftens merged/season-lager, flyttleier, naturvern, protected watercourses, wind power area status, kulturmiljoer, tatorer, kraftnat, vattenytor, kustlinje och kommun/fylke-granser.

Reindriftens sasongslager (`TRL_REINDEER_GRAZING_SPRING`, `SUMMER`, `AUTUMN`, `AUTUMN_WINTER`, `WINTER`) passar bra som en samlad season-selector i appen.

For befolkning/bebyggelse-controller ska `TRL_POPULATION_250M_CENTROIDS` vara iklickad som default tills riktiga befolkningspunkter finns. `TRL_DENSELY_POPULATED_AREAS` fungerar som built-centre/tettsted-proxy och `TRL_HOLIDAY_HOUSES_CENTROIDS` som fritidshusproxy; bada ska vara valbara i avancerade installningar men urklickade fran start.

## Bor bli score-, distance- eller buffer-inputs

- Vind/energi: vindkraftsomraden, aktiva vindparker, turbiner, kraftnat, sjokabel, vattenkraftverk och dammar.
- Reindrift: merged grazing, flyttleier, restriktionsomraden och reinbeitedistrikt.
- Natur/skydd: naturvern, protected watercourses och water protection som hard/soft constraints.
- Samhalle: befolkning 250 m-centroider som default distance-conflict, samt tatorer/built-centre och fritidshus-centroider som avancerade optionala distance-/buffer-inputs. Befolkning 1 km kan ligga kvar som QA/fallback eller grovre exponeringsscore.
- Infrastruktur: flygplatser, vagar, europavagar, jarnvag och kraftnat som distance-to eller buffertkontroller.
- Terrang/vatten: kust, vattendrag och vattenytor som context, distance eller mask beroende scenario.

## Appkoppling 2026-05-18

Forsta naturkopplingen i Potential App v2 ar medvetet smal: `TRL_NATURE_PROTECTION_AREAS` (`NEA_Naturvern_TRL+_32`) ar kopplat som `protected_areas` i samma hard-exclusion-grupp som Bornholm anvander for skyddad natur. `TRL_PROTECTED_WATERCOURSES` och `TRL_WATER_PROTECTION` ligger kvar som nasta natur/skydd-steg.

Skog, jordbruksmark, myr och andra Arealdekke-klasser ska inte blandas in i `protected`-gruppen. De hor till en senare markanvandnings-controller dar anvandaren kan valja bort separata markslag, exempelvis skog, jordbruksmark eller myr.

## Endast QA/context

`TRL_NATIONAL_PARKS_N500`, `TRL_N2000_NATURE_OVERVIEW`, `TRL_CULTURAL_HERITAGE_MERGED_NW`, `TRL_HOLIDAY_HOUSES_CENTROIDS`, `TRL_CONTOUR_LINES`, `TRL_OCEAN_MASK`, `TRL_ADMIN_KOMMUNER` och `TRL_NATIONAL_BORDER` bor i forsta hand anvandas for QA, bakgrund eller kartorientering. De kan bli skarpa inputs senare om pipeline-agenten verifierar tackning, attribut och dubbelrakning.

## Saknade eller osakra kallor

- DEM/hillshade/terrangraster hittades inte som tydligt appklart lager i de prioriterade utgaende mapparna. Endast topolinjer identifierades.
- Hamnar/farjeleder hittades inte som tydligt hamnlager. `Hurtigruten` finns och ar katalogiserat som lagprioriterat kusttransport-context.
- Reinbeitedistrikt och reindriftens restriksjonsomrader finns i inkommande FileGDB-kallor men verkar inte vara lyfta till appklar shapefile/GPKG i utkommande. De ar markerade med `needs_processing=TRUE`.
- `TRL_TRANSMISSION_NETWORK` har ett trunkerat filnamn och metadata som anger UTM33 trots placering i UTM32-mappen. CRS och faktisk geometri bor verifieras innan scoring.
- Vissa SSB-lager har CRS-namnet `UTM_Zone_32_Northern_Hemisphere` i stallet for explicit EPSG. Pipeline bor verifiera detta mot `.prj`.
- Kommunlagret `N500_AO_Kommun_ORK_32` kan vara delomrade; kontrollera att det tacker hela Trondelag innan det anvands for appfilter.

## CRS-not for appen

Bornholm och Trondelag ska inte antas ha samma native CRS. Bornholm-regionmanifestet anger `EPSG:25833`, medan Trondelag-regionmanifestet anger `EPSG:25832`. Trondelag-kallorna i denna appkoppling ligger huvudsakligen i UTM 32 och buffertar/distansberakningar for Trondelag bor darfor goras i meter i `EPSG:25832`.

Det finns fortfarande aldre Bornholm-runtimekod som internt anvander `EPSG:32633` i R-scriptet. Trondelag bor pa sikt fa en regionstyrd runtime-CRS sa att Bornholm- och Trondelag-geometrier inte delar hardkodad UTM-zon. Nuvarande Trondelag-befolkningsproxy ar byggd i `EPSG:25832`: 250 m rutor fran population-centroider, upplosta till polygonproxy for visning och app-buffer.

## Nasta steg for pipeline-agenten

1. Las `potential_app_layer_candidates.csv` och filtrera pa `priority=high` samt `needs_processing=TRUE`.
2. Valj en gemensam app-CRS, troligen ETRS89 / UTM zone 32N eller 33N beroende pa befintlig Trondelag-pipeline, och normalisera alla lager dit.
3. Lista interna layer names for de inkommande FileGDB-kallorna innan extraktion, sarskilt reindrift restriksjon/distrikt och selected agricultural/cultural landscapes.
4. Skapa appoptimerade derivat: clipped, simplified, 2D, valid geometries, dissolved classes och H3/aggregerade score-features.
5. Skapa distance-to/buffer-inputs for vindparker/turbiner, kraftnat, flygplatser, tatorer, fritidshus, reindrift flyttleier, vatten och vag/jarnvag.
6. Undvik dubbelrakning: anvand QA-lager for jamforelse mot primara lager, inte parallell scoring.
7. Koppla controller-grupperna i appen till `controller_group`, `role`, `recommended_app_use`, `default_visibility` och `priority` fran CSV:n.
