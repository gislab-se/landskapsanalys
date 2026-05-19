# Potential App v2: sammanfattning, metod och felsökning

Status: BETA / utvecklingsversion  
Senast genomgången: 2026-05-19  
Kodbas: `C:\tmp\landskapsanalys-v2-multiregion`

Dokumentet har två funktioner:

- ge en sammanhållen analytisk beskrivning av appens syfte, metod och tolkningsram
- fungera som felsökningskarta när vänsterpanel, karta och högerpanel inte verkar stämma

## Analytisk sammanfattning

Potential App v2 är ett interaktivt analysverktyg för att pröva hur sol- och vindetablering kan rymmas i ett landskap under olika antaganden om energibehov, markanspråk, skyddsavstånd och landskapliga begränsningar.

Appen är inte ett slutligt planeringsinstrument. Den är tydligt markerad som **BETA** och bör förstås som ett transparent metod- och granskningsunderlag där antaganden, datakällor och beräknade konsekvenser kan följas.

Appen stödjer just nu:

- **Bornholm**, som fungerar som referensregion.
- **Trøndelag**, som är en regional anpassning av Bornholm-flödet.

I appen arbetar användaren med tre huvuddelar:

- **Vänsterpanelen**: val av region, analysupplösning, landskapslager, vindfilter, solfilter, energiscenario och social acceptans.
- **Kartan**: visar de lager som är aktiva, till exempel potentiell etableringsyta, scenariofördelning och social acceptans.
- **Högerpanelen**: förklarar resultatet med statistik, aktiva filter, ytbehov, hur mycket som ryms inom potentialen och vad som eventuellt hamnar utanför potentialen.

Det viktigaste resultatet är **Potentiell etableringsyta**. Det är den samlade ytan där modellen bedömer att vind, sol eller båda teknikerna kan ingå efter aktuella filter.

## Viktigt om landskapspotential

Begreppen **Landskapspotential Sol** och **Landskapspotential Vind** finns fortfarande i appens kod och i vissa kontrollrubriker, men ska inte förklaras som separata slutlager i normal användning.

De fungerar framför allt som **beräkningssteg**:

- de skapar eller påverkar kandidatyta för sol och vind
- de filtreras med skydd, avstånd, infrastruktur och andra regler
- de matas vidare till **Potentiell etableringsyta**
- de summeras i högerpanelens statistik och härledningstabeller

Den centrala tolkningen är därför:

> Landskapspotentialen är underlaget. Etableringsytan är den praktiska kartbilden att diskutera.

## Vetenskaplig text

### Syfte

Syftet med appen är att skapa ett transparent och testbart beslutsstöd för landskapsbaserad analys av sol- och vindpotential. Appen ska visa hur tekniska energiscenarier omsätts till rumsligt ytbehov och hur detta ytbehov förhåller sig till landskapets möjliga etableringsytor.

Appen ska också göra antaganden synliga. Användaren ska kunna se vilka filter som är aktiva, hur de påverkar ytan, vilka datakällor som används och när resultatet bygger på placeholder- eller syntetisk data.

### Dataunderlag

Appen byggs från regionmanifest och länkar vidare till data för respektive region.

Viktiga datatyper är:

- regionmanifest med koordinatsystem, kartcentrum, analysupplösningar och länkade dataförteckningar
- landskapsdata med sexkantiga analysceller, landskapstyper, landskapsstrukturer och faktorer
- potentialregler för sol och vind
- energiscenarier från DuckDB/TIMES-data
- ytbehovsfaktorer från `AreaDemand.xlsx`
- social acceptans som syntetiskt testlager
- vektorunderlag för till exempel befolkning, vägar, skyddad natur, kulturmiljö, elinfrastruktur och rennäring

Bornholm och Trøndelag använder olika regionala koordinatsystem. Bornholm använder `EPSG:25833`, medan Trøndelag använder `EPSG:25832`. Webbkartan visas i ett webbanpassat koordinatsystem, men avstånds- och ytberäkningar bör förstås utifrån respektive regions lokala koordinatsystem.

Trøndelag använder i nuvarande appgren en lätt regional datapaketstruktur där H3-systemet, alltså ett system av sexkantiga analysceller, ligger på nivå R7 som grund. Grövre nivåer används för översiktlig visning. Regionförteckningen exponerar just nu R7/R6/R5 och öppnar på R7. Det är en viktig granskningspunkt om projektets formella kravbild anger R8/R7/R6.

### Metod

Appen startas via `streamlit_app.py`, som laddar huvudlogiken i `potential_app.py`. Där samordnas användargränssnitt, regionval, filter, kartlager och högerpanelens sammanställningar. Mer avgränsade beräkningsdelar ligger i `apps/potential_model/`, bland annat:

- `energy_modeling.py` för energiscenarier och ytbehov
- `potential.py` för potentialklasser och rolluper
- `social_acceptance.py` för syntetiskt acceptanslager
- `region_status.py` för datastatus och runtime-kontroller
- `map_rendering.py` för Leaflet/HTML-kartan
- `wind_acceptance.py` för vindrelaterade acceptans- och avståndsfilter

Metoden kan beskrivas i sex steg:

1. **Region och datatillgänglighet kontrolleras.** Appen läser regionens dataförteckningar och kontrollerar att landskap, potentialregler, scenarier och kartgeometrier finns.
2. **Landskapet delas in i sexkantiga analysceller.** Varje cell får landskapstyp, struktur och faktorer.
3. **Sol- och vindpotential skapas.** Vind och sol får kandidatytor utifrån landskap och aktiva filter.
4. **Energiscenario översätts till ytbehov.** TIMES/DuckDB anger energi i TWh. `AreaDemand.xlsx` översätter detta till km2/TWh och därmed ytbehov.
5. **Ytbehovet allokeras till möjlig etableringsyta.** Modellen försöker placera vind och sol inom potentialen. Om allt inte ryms skapas ett extra lager för ytbehov utanför potential.
6. **Resultatet visas i karta och högerpanel.** Kartan visar lager; högerpanelen visar om siffrorna hänger ihop.

### Beräkningslogik

Vindlogiken bygger på valda källager och regelgrupper, till exempel befolkning/bebyggelse, vägar, elinfrastruktur, skyddad natur, kulturmiljö och rennäring. Vissa grupper fungerar som avdrag eller buffertar, medan elinfrastruktur kan fungera som närhetskrav.

Sol har två huvuddelar:

- **Småskalig sol**: en schablon där befolkning per hex multipliceras med vald panelyta per person. Den ska inte tolkas som verkliga takpolygoner.
- **Storskalig sol**: utgår från landskapsunderlaget som kandidatbas. Aktiva filter drar bort yta eller begränsar ytan till exempelvis närhet till elinfrastruktur.

Trøndelag befolkningsunderlag är en 250 m rut-/centroidproxy. Det ska inte beskrivas som individuella befolkningspunkter.

Energimodelleringen räknar ut hur mycket yta som behövs för vald mix av vind och sol. Högerpanelen visar bland annat:

- energi i TWh
- ytbehov
- potential efter filter
- yta inom potential
- outnyttjad potential
- ytbehov utanför potential
- andel av scenariot som ryms inom potential

Den kombinerade etableringsytan klassas ungefär så här:

- blå: möjlig för vind
- gul: möjlig för sol
- grön: möjlig för både vind och sol
- röd: inte lämplig enligt aktiv modell

### Resultat och tolkning

Resultatet ska tolkas som en scenariobaserad bedömning, inte som ett slutligt planeringsbesked.

Om högerpanelen säger att scenariot ryms inom potentialen betyder det att valt ytbehov kan allokeras inom de celler som är möjliga efter aktiva filter.

Om högerpanelen visar **Ytbehov utanför potential** betyder det att modellen inte hittar tillräcklig möjlig yta inom de aktiva antagandena. Kartan kan då visa ett separat schematiskt lager för denna brist. Det är en signal om att användaren bör granska antaganden, filter, energimix eller scenario.

Social acceptans är ett syntetiskt testlager. Det har värden 0-1 och tre scenarier, men ska inte tolkas som IVL-resultat eller verklig social acceptans.

### Begränsningar

Viktiga begränsningar i nuvarande BETA-version:

- Trøndelag-scenarierna är placeholder-data och använder Bornholm/TIMES/AreaDemand tills regionala EML- eller norska data finns.
- Social acceptans är syntetiskt testdata.
- Småskalig sol är en befolkningsschablon, inte byggnads- eller takdata.
- Sexkantiga analysceller kan överstiga faktisk landyta vid kuster eftersom celler räknas som hela analysenheter.
- Trøndelag befolkning bygger på 250 m proxydata.
- Separata sol-/vindpotentialbegrepp bör förklaras som underlag till etableringsytan, inte som slutliga kartlager.
- Nuvarande kodgren exponerar Trøndelag R7/R6/R5; om projektkravet är R8/R7/R6 behöver detta hanteras explicit.

### Vidare utveckling

Nästa steg bör vara:

- ersätta Trøndelag placeholder-scenarier med regionala energidata
- ersätta syntetisk social acceptans med verkligt granskat dataunderlag
- tydliggöra UI-språk så att landskapspotential inte uppfattas som separat slutlager
- fortsätta stresstesta vänsterpanelens filter mot högerpanelens statistik
- dokumentera varje regional avvikelse från Bornholm
- se över analysupplösningar för Trøndelag så att dataförteckningar, tester och kravbild beskriver samma sak

## Felsökningskarta

### Snabb kontroll i appen

När något ser konstigt ut, kontrollera i denna ordning:

1. Rätt region i vänsterpanelen.
2. Rätt analysupplösning och sammanvägningsnivå.
3. Att soländringar är applicerade med **Använd ändringar**.
4. Att social acceptans inte tolkas som verkligt resultat.
5. Att högerpanelen visar samma aktiva filter som vänsterpanelen.
6. Att **potential efter filter** minskar när ett avdragsfilter slås på.
7. Att **ytbehov utanför potential** ökar om filtren gör etableringsytan för liten.
8. Att kartans lagerkontroll faktiskt har rätt lager tända.

### Vad ska matcha mellan panelerna?

Vänsterpanelen styr antagandena. Högerpanelen ska spegla effekten.

Exempel:

- Slås solfilter för vägar på i vänsterpanelen ska högerpanelen visa aktivt vägfilter och en solfiltereffekt om filtret påverkar ytan.
- Slås befolkningsavstånd på för sol ska högerpanelen visa detta som aktivt solfilter.
- Byter man region ska gammal analysupplösning och gamla regioninställningar inte ligga kvar.
- Slås social acceptans på ska kartan visa syntetisk acceptans och texten ska varna för testdata.
- Om scenarioytan inte ryms ska högerpanelen visa brist och kartan kunna visa **Ytbehov utanför landskapets potential**.

### Inbyggda debugytor

Högerpanelen innehåller flera felsökningsdelar:

- **Etableringsyta**: huvudkontroll för ytbehov, potential och brist.
- **Karta**: visar scenario, vald visningsupplösning, analysupplösning och lagerstatus.
- **Aktiva beräkningar**: visar prestanda, senaste energiberäkning, antal genererade vind-/solhex och kartlager i senaste rendering.
- **Data och metod**: visar manifestvägar och regionens metadata.

Detta är användbart när en karta ser korrekt ut men statistiken inte gör det, eller tvärtom.

### Testkommandon

Kör dessa från v2-worktreet:

```powershell
C:\gislab\landskapsanalys\.venv\Scripts\python.exe scripts\stress_potential_app_v2.py
C:\gislab\landskapsanalys\.venv\Scripts\python.exe scripts\smoke_potential_app_v2_ui.py
```

Stresstestet kontrollerar bland annat:

- BETA-markering i kod och UI-text
- regionbyte och reset av gammalt session state
- Bornholm som referensflöde före Trøndelag
- solfilter från vänsterpanelen mot statistik i högerpanelen
- vind/sol-summering i etableringsytan
- social acceptans som syntetiskt lager
- Trøndelag befolkningsbuffert som polygon/proxy, inte som separat hexagonlager

UI-smoketestet kontrollerar bland annat:

- att appen renderar utan Streamlit-fel
- att Trøndelag startar som default
- att analysupplösning och regionbyte fungerar
- att BETA-texten syns
- att social acceptans kan slås på
- att solfilter för vägar kan appliceras och synas i högerpanelen

### Kodspår vid felsökning

Använd dessa filer som karta:

- `streamlit_app.py`: laddar appen.
- `potential_app.py`: huvud-UI, session state, filter, kartlager och högerpanel.
- `apps/potential_model/manifests/regions/bornholm.json`: Bornholm regionkontrakt.
- `apps/potential_model/manifests/regions/trondelag.json`: Trøndelag regionkontrakt.
- `apps/potential_model/region_status.py`: avgör om regionen är runtime-ready.
- `apps/potential_model/energy_modeling.py`: läser TIMES/DuckDB och AreaDemand.
- `apps/potential_model/social_acceptance.py`: skapar social acceptans-lager.
- `apps/potential_model/wind_acceptance.py`: vindfilter och regelgrupper.
- `scripts/stress_potential_app_v2.py`: funktionellt stresstest.
- `scripts/smoke_potential_app_v2_ui.py`: UI-smoketest.

## Kort version att klistra in i mail eller presentation

Potential App v2 är en BETA-version för att testa hur sol- och vindscenarier kan översättas till möjlig etableringsyta i landskapet. Appen låter användaren välja region, scenario, analysupplösning och filter för bland annat befolkning, vägar, skyddad natur, kulturmiljö, elinfrastruktur och rennäring. Resultatet visas som en kombinerad etableringsyta där vind, sol eller båda teknikerna kan rymmas.

Det viktigaste är inte separata lager för "landskapspotential sol" eller "landskapspotential vind", utan hur dessa beräkningssteg leder fram till **Potentiell etableringsyta** och till högerpanelens statistik. Högerpanelen visar om valt energiscenario ryms inom potentialen, hur mycket yta som behövs, hur mycket som finns efter filter och om något måste hanteras utanför landskapets potential.

Bornholm fungerar som referensregion. Trøndelag är en regional anpassning och använder just nu delvis placeholder-data för energiscenarier. Social acceptans är syntetiskt testdata och ska inte tolkas som forskningsresultat. Appen är därför ett utvecklings- och dialogverktyg, inte ett färdigt planeringsbesked.
