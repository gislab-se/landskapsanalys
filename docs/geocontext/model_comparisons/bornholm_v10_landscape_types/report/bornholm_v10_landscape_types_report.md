# Bornholm landskapstrukturanalys

## Start här

Den här rapporten är den samlade ingången till Bornholms landskapstrukturanalys. Den bygger vidare på flera tidigare modellversioner och visar v10 som aktuell samlad tolkning tills vidare. Syftet är att förklara hur landskapsmått, faktorer, kluster och landskapstyper hänger ihop, och hur resultatet kan användas som underlag för fortsatt analys av landskapets struktur och potential för sol- och vindteknik.

v10 är inte en ny klustring. Det är en tolkad syntes ovanpå v9 K=8: de analytiska v9-klustren och faktorpoängen översätts till fem mer kommunicerbara landskapstyper. Därför ska v10 läsas som en transparent kartografisk och metodisk sammanfattning av arbetet, inte som ett fältverifierat facit.

## Kunskap från tidigare versioner

Bornholm-arbetet har vuxit fram stegvis. I `regional-landscape-pipeline` visade v1 och v3 att högre H3-upplösning och K=8 gjorde sprickdalsstrukturen tydligare. v4 och v5 testade mer temabalanserade indata och visade att faktorsignalen fanns, även när klusternamnen behövde tolkas mer varsamt. v6, v7 och v9 hjälpte oss förstå K=8-lösningen, klusterstorlek, faktorlager och hur resultaten kan visas pedagogiskt.

I repo `landskapsanalys` finns dessutom tidigare rapportversioner, modelljämförelser och scenario-/potentialappar. De har bidragit med metodkunskap, presentationsform och förståelse för hur landskapsanalysen kan användas praktiskt. De äldre versionerna ska därför läsas som utvecklingssteg och kunskapsunderlag, inte som konkurrerande huvudresultat.

## Metoden i korthet

Analysen börjar med många GIS-lager och landskapsmått som sammanfattas i ett hexagonnät. Måtten beskriver bland annat relief, höjdskillnader, kust- och sandmiljöer, skog och skyddad natur, bebyggelse, öppet lågland och jordbrukspräglade landskapsrum.

Dessa mått reduceras med faktoranalys. Faktorladdningarna visar vilka lager och mått som bygger upp varje faktor. Faktorpoängen visar sedan hur starkt varje hexagon uttrycker respektive faktor. I v9 används faktorpoängen för att skapa åtta kluster. I v10 översätts de åtta klustren till fem landskapstyper genom en dokumenterad crosswalk.

## Lagerfamiljer och faktorer

- `F1`: sprickdal och brant relief. Laddar starkt på brant relief, höjdskillnader och sprickdalspräglad terräng.
- `F2`: flygsand och sandpräglad kust. Laddar på flygsand, sanddyner och strand-/kustmiljöer.
- `F3`: skog och skyddad natur. Laddar på skog, fredskov, habitat och andra natur-/skyddslager.
- `F4`: tätort och byggd struktur. Laddar på byggnader, fastboende och andra bebyggelsemått.
- `F5`: låglänt öppet land. Laddar på låga höjdlägen och öppna landskapsrum.

## v9-kluster

- kluster 1: tätorts- och verksamhetskärnor, starkt kopplat till `F4`.
- kluster 2: sprickdalspåverkat övergångslandskap, kopplat till `F1`.
- kluster 3: blandat vardagslandskap med låg faktorprofil, utan en ensam tydlig dominerande faktor.
- kluster 4: flygsand och sandkust, kärnzon med mycket stark `F2`.
- kluster 5: sprickdal och brant relief, kärnzon med stark `F1` och viss `F2`.
- kluster 6: öppet och låglänt blandlandskap, kopplat till `F5`.
- kluster 7: skog och skyddad natur, kärnzon med stark `F3`.
- kluster 8: sand- och kustpräglat landskap, kopplat till `F2` men mer blandat än kluster 4.

## Från v9 till v10

I v10 förs de tydliga v9-klustren över direkt till landskapstyper. Det stora blandade kluster 3 delas däremot med hjälp av `F1`, eftersom `F1` fångar sprickdals- och reliefsignal inom jordbrukslandskapet.

- `LT01 Klippigt kustlandskap` skapas från v9 kluster 5.
- `LT02 Sandigt kustlandskap` skapas från v9 kluster 4 och 8.
- `LT03 Jordbruksdominerat sprickdalslandskap` skapas från v9 kluster 2 och den del av kluster 3 som har tydligare `F1`-signal.
- `LT04 Skogsklätt sprickdalslandskap` skapas från v9 kluster 7.
- `LT05 Slätt- och jordbrukslandskap` skapas från v9 kluster 6 och den del av kluster 3 som har lägre `F1`-signal.

På så sätt blir v10 en tolkad syntes: landskapstyperna bygger på statistiska kluster, faktorladdningarnas betydelse och faktorpoängens geografiska uttryck.

## Landskapstyper

| ID | Namn | Tolkning |
|---|---|---|
| LT01 | Klippigt kustlandskap | Kust- och reliefpräglade delar där brant/sprickdalsrelief och kustsignal sammanfaller. |
| LT02 | Sandigt kustlandskap | Sand- och kustpräglade delar, främst där flygsand/sandkustfaktorn är stark. |
| LT03 | Jordbruksdominerat sprickdalslandskap | Öppet jordbruksdominerat landskap med tydlig sprickdals- eller lågkullig struktur. |
| LT04 | Skogsklätt sprickdalslandskap | Skogsklädda sprickdals- och naturmiljöer med stark skog/naturfaktor. |
| LT05 | Slätt- och jordbrukslandskap | Större öppna, låglänta och jordbruksdominerade landskapsrum. |

## Vidare användning

Landskapstyperna beskriver inte i sig var ny teknik ska byggas. De ger en strukturell kontext: vilka landskapsrum som är kustpräglade, sandpräglade, sprickdalspräglade, skogligt/naturpräglade eller låglänt jordbrukspräglade. Denna kontext kan sedan kombineras med tekniska, juridiska och planeringsmässiga lager i potentialapparna för sol och vind.

## Källor och metodstöd

- Kawalerowicz, Juta & Malmberg, Bo. 2021. *Multiscalar Typology of Residential Areas in Sweden*. Kulturgeografiskt seminarium 2021:1. Kulturgeografiska institutionen, Stockholms universitet.
- *Bornholms Landskapstyper*. PDF, lokalt referensmaterial, 2025.

Kawalerowicz och Malmberg (2021) använder faktoranalys för att reducera många multiskalära kontextmått till faktorpoäng, använder faktorpoängen i klustring och tolkar/namnger sedan klustertyper utifrån egenskaper och geografisk utbredning. v10 följer samma principiella arbetsgång, men med landskapsdata och en explicit crosswalk från v9-kluster till fem landskapstyper.

PDF-kartan *Bornholms Landskapstyper* beskriver underlaget som en skrivbordsanalys baserad på GIS-analyser och befintligt kartmaterial, med subjektiva tolkningar och utan fältverifiering. v10 ska därför läsas som en transparent tolkning snarare än som facit.

## Filer

- Interaktiv karta: `../map/bornholm_v10_landscape_types_map.html`
- Crosswalk: `../model/bornholm_v10_landscape_types_crosswalk.csv`
- Faktorloadings: `../model/bornholm_v10_landscape_types_factor_loadings_from_v1.csv`
