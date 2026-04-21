# Bornholm v10: landskapstyper

## Kort sammanfattning

v10 är en tolkad landskapstyp-version ovanpå v9 K=8. Den ersätter inte v9 som analytisk klusterdemo, utan översätter v9-kluster och faktorer till fem mer kommunicerbara landskapstyper inspirerade av referenskartan `Landskapstyper Bornholm.pdf`.

## Metod

- Utgångspunkt: v9/v3 K=8 med fem faktorer och åtta ursprungliga kluster.
- Reklassning: v9-kluster förs till fem landskapstyper genom en dokumenterad crosswalk.
- Delning: det stora lågprofilerade kluster 3 delas mellan jordbruksdominerat sprickdalslandskap och slätt-/jordbrukslandskap.
- Absorbering: tätort/verksamhet blir inte egen landskapstyp, utan förs till närmaste tolkade omgivande typ.
- Status: pedagogisk syntes och kartografisk tolkning, inte ny oövervakad klustring och inte fältverifierad klassning.

## Landskapstyper

| ID | Namn | Tolkning |
|---|---|---|
| LT01 | Klippigt kustlandskap | Kust- och reliefpräglade delar där brant/sprickdalsrelief och kustsignal sammanfaller. |
| LT02 | Sandigt kustlandskap | Sand- och kustpräglade delar, främst där flygsand/sandkustfaktorn är stark. |
| LT03 | Jordbruksdominerat sprickdalslandskap | Öppet jordbruksdominerat landskap med tydlig sprickdals- eller lågkullig struktur. |
| LT04 | Skogsklätt sprickdalslandskap | Skogsklädda sprickdals- och naturmiljöer med stark skog/naturfaktor. |
| LT05 | Slätt- och jordbrukslandskap | Större öppna, låglänta och jordbruksdominerade landskapsrum. |

## Källor och metodstöd

- Kawalerowicz, Juta & Malmberg, Bo. 2021. *Multiscalar Typology of Residential Areas in Sweden*. Kulturgeografiskt seminarium 2021:1. Kulturgeografiska institutionen, Stockholms universitet.
- *Bornholms Landskapstyper*. PDF, lokalt referensmaterial, 2025.

Kawalerowicz och Malmberg (2021) använder faktoranalys för att reducera många multiskalära kontextmått till faktorpoäng, använder faktorpoängen i klustring och tolkar/namnger sedan klustertyper utifrån egenskaper och geografisk utbredning. v10 följer samma principiella arbetsgång, men med landskapsdata och en explicit manuell crosswalk från v9-kluster till fem landskapstyper.

PDF-kartan *Bornholms Landskapstyper* beskriver underlaget som en skrivbordsanalys baserad på GIS-analyser och befintligt kartmaterial, med subjektiva tolkningar och utan fältverifiering. v10 ska därför läsas som en transparent tolkning snarare än som facit.

## Filer

- Interaktiv karta: `../map/bornholm_v10_landscape_types_map.html`
- Crosswalk: `../model/bornholm_v10_landscape_types_crosswalk.csv`
- Faktorloadings: `../model/bornholm_v10_landscape_types_factor_loadings_from_v1.csv`
