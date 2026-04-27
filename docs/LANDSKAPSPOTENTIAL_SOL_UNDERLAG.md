# Landskapspotential Sol - underlag från Sol over land

Källa: `sol_over_land_guide_H.pdf`, Plan22+ / Urland, 2024. PDF:en är inte en officiell vägledning, men är användbar som metodstöd för ett första `Landskapspotential Sol`-lager.

## Modellidé

`Landskapspotential Sol` bör visa hur väl landskapet kan bära större solenergianlägg, inte bara teknisk solinstrålning. Lagret kan därför byggas som en kombination av:

- landskapets robusthet och skala
- terräng och siktkänslighet
- närhet till bebyggelse, rekreation, vägar och stigar
- natur- och skyddsintressen
- kulturhistoriska och landskapsmässiga intressen
- närhet till elinfrastruktur och transformatorstationer
- möjlighet att skapa sammanhängande, tydliga projektfält

## Föreslagen poängmodell

Starta med `50` poäng och justera med positiva och negativa termer. Klassa sedan till 0-100.

| Tema | Effekt | Motivering från PDF |
| --- | ---: | --- |
| Storskaligt, jämnt jordbrukslandskap | +20 till +30 | Slettelandskap beskrivs som robusta, öppna och lämpliga för stora sammanhängande solenergianlägg. Se s. 8, 12. |
| Storbakkade men stora landskapsrum | +5 till +15 | Storbakkede landskaber kan bära mellanstora anläggningar när landskapsrummen är stora och få natur-/bosättnings-/fritidsintressen finns. Se s. 8, 13. |
| Småbakkigt, småskaligt landskap | -15 till -30 | Småbakkede landskaber bör främst bära mindre anläggningar, och bara där visuella konsekvenser är små. Se s. 8, 14. |
| Dalar, markerade skränter och utsiktsrum | -25 till -45 | Dallandskaber kräver restriktiv syn på solenergianläggningar på grund av utsikt och terräng. Se s. 8, 16. |
| Kustlandskap / kystnærhed | -30 till -60 | Kystlandskaber kräver restriktiv syn, särskilt vid visuell kontakt med kustlinje, stränder och strandängar. Se s. 8, 17-18. |
| Avstånd från kustkaraktär > 300-400 m | mildra kuststraff | Guiden anger att 300-400 m i öppet terräng kan göra det visuella samspelet mindre markant. Se s. 17-18. |
| Hög naturvärde / skyddad natur | hård exkludering eller -60 | Solenergianläggningar bör inte placeras i områden med särskild natur och hög biodiversitet. Se s. 24-25. |
| Närhet till särskilda naturområden | -20 till -40 | Guiden betonar försiktighet nära särskilda naturområden, även när platsen inte ligger direkt i dem. Se s. 24. |
| Tät befolkning, bynära landskap, rekreation | -20 till -45 | Stora solenergianläggningar kan skapa konflikter i tätbefolkade eller rekreativt viktiga landskap. Se s. 9, 26. |
| Synlighet från cykel-/stiförbindelser, utsiktspunkter | -15 till -35 | Visuell påverkan från vardags- och fritidsrörelser lyfts som viktig. Se s. 26, 49-50. |
| Närhet till transformatorstationer / starkt elnät | +10 till +25 | Solparker behöver stor elnätskapacitet och kan med fördel ligga nära elnät och transformatorstationer. Se s. 28, 34. |
| Närhet till PtX / energikomplex / vind | +5 till +15 | Guiden pekar på samspel mellan sol, vind, PtX och elnät. Se s. 28. |
| Markanta sluttningar och höjdpunkter | -15 till -35 | Guiden rekommenderar att markanta sluttningar och visuellt högt liggande koter bevaras. Se s. 20, 51. |
| Möjlighet till grön avskärmning och naturkorridorer | +5 till +15 | Projekt bör stärka natur, gröna korridorer och landskapsanpassning. Se s. 49-54. |

## Hårda exkluderingar

Första versionen bör behandla dessa som `0` eller `ej lämplig`:

- Natura 2000 och motsvarande starkt skyddade naturområden
- nationalparker, fredade områden och skyddad natur
- områden med hög biodiversitet / bioscore, om data finns
- öppna kustmiljöer där solparken får direkt visuell kontakt med kustlinje, strand, strandäng, klit eller marsk
- markerade dalrum, branta skränter och utsiktspunkter där synligheten är central
- befintliga naturbiotoper som inte bör röjas

## Klassning och legend

Föreslagen femklassig legend:

| Klass | Namn | Tolkning |
| --- | --- | --- |
| 80-100 | Mycket hög LP Sol | Robust landskap, låg konflikt, god elnätslogik |
| 65-80 | Hög LP Sol | Lämpligt men behöver lokal gestaltning |
| 45-65 | Möjlig LP Sol | Kräver avvägning, storlek och design avgör |
| 20-45 | Låg LP Sol | Sårbart eller konfliktfyllt landskap |
| 0-20 | Ej lämpligt | Skydd, natur, kust, dal/utsikt eller stark konflikt |

Färgförslag: gult till mörkorange för positiv solpotential, grå/rödbrun för låg eller ej lämplig yta. Sol bör inte använda samma blå/röd-logik som vindens energimodelleringslager.

## Koppling till befintliga data i appen

Möjliga befintliga Bornholm-lager:

- landskapstyper / landskapsfaktorer: robusthet, relief, kust, sprickdal, vardagslandskap
- höjdkurvor / relief: branta sluttningar, högt liggande visuella lägen
- bebyggelse och bykärnor: tät befolkning och bynära konflikt
- vägar och stigar: visuell exponering och rekreativ användning
- skyddade områden, Natura 2000, habitat, fågelskydd, Ramsar, natur- och viltreservat
- kulturmiljöer och kulturhistoriska bevaringsvärden
- transformatorstationer, högspänningsledningar och kablar
- kust-/strandsskydd och kystnærhedszonen
- jordart/markblock kan senare användas för jordbruks- och markanvändningslogik

## Första app-version

En praktisk första implementation kan göras som ett H3-baserat scorelager:

1. Beräkna baspoäng från landskapsfaktorer:
   - plus för öppna, jämna, storskaliga produktionslandskap
   - minus för kust, dal, brant relief, småskalighet och höga natur-/kulturvärden
2. Sätt hårda maskar för skyddad natur och starka kust-/strandkonflikter.
3. Lägg till teknisk bonus för närhet till transformatorstationer och elnät.
4. Lägg till bosättnings-/rekreationsstraff nära byar, tät bebyggelse, vägar/stigar och viktiga utsiktspunkter.
5. Klassificera till `Landskapspotential Sol` med samma H3-rollup/zoomlogik som övriga hexlager.

## Särskilt användbara sidor i PDF:en

- s. 8-18: landskapstyper och deras generella lämplighet
- s. 24-26: naturinnehåll, skyddad natur och befolkning/rekreation
- s. 28: energipotentialer, elnät och samspel sol/vind/PtX
- s. 32-34: zoneplanering och screeninglager
- s. 48-54: projektprinciper för avstånd, avskärmning, terräng, natur och korridorer
