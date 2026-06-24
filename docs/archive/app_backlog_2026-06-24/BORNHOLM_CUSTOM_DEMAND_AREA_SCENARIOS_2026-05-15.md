# Egna efterfragebaserade ytbehovsscenarier for Bornholm

Datum: 2026-05-15

## Syfte

Den har notisen tar fram egna planeringsnivaer for en datacenter-/elforbrukningsfraga utan att anvanda Bornholms `ENERGYISLAND2050` som efterfrageprognos.

Bornholms DuckDB-scenario `ENERGYISLAND2050` ar ett energy-island-/produktionsscenario. Det ger cirka 26,3 TWh 2040 och 49,7 TWh 2050, nastan helt som vindproduktion. Det ar darfor anvandbart som energimodellkontext, men inte som ett direkt antagande om datacenterforbrukning.

## Egna planeringsnivaer

Egen efterfragan:

- Lag: 10 TWh/ar
- Mellan: 15 TWh/ar
- Hog: 20 TWh/ar

Huvudmix:

- 50 procent landvind
- 50 procent sol

Motiv: potentialappen startar energimixreglaget pa 50 procent sol, och AreaDemand kan rakna yta for vind och sol var for sig. Vind-only och sol-only visas som kanslighetsfall.

## AreaDemand-faktorer

Faktorer fran `data/raw/AreaDemand.xlsx`, med samma tolkning som `apps/potential_model/energy_modeling.py`:

| Teknik | Lag km2/TWh | Median km2/TWh | Hog km2/TWh |
|---|---:|---:|---:|
| Landvind | 8,3 | 37,0 | 1000,0 |
| Sol | 8,6 | 14,2 | 28,6 |

Notera: vindens hoga scenario ar mycket konservativt och drivs av den breda litteraturspannet i AreaDemand. Det bor beskrivas som ett stress-/kanslighetsfall, inte som basta skattning.

## Huvudresultat: 50/50 vind och sol

| Efterfrageniva | Vind TWh/ar | Sol TWh/ar | Lag markintensitet km2 | Median km2 | Hog markintensitet km2 |
|---:|---:|---:|---:|---:|---:|
| 10 TWh/ar | 5,0 | 5,0 | 85 | 256 | 5143 |
| 15 TWh/ar | 7,5 | 7,5 | 127 | 384 | 7714 |
| 20 TWh/ar | 10,0 | 10,0 | 170 | 512 | 10286 |

## Kanslighet vid medianfaktor

| Efterfrageniva | 100 procent landvind km2 | 50/50 vind och sol km2 | 100 procent sol km2 |
|---:|---:|---:|---:|
| 10 TWh/ar | 370 | 256 | 142 |
| 15 TWh/ar | 556 | 384 | 213 |
| 20 TWh/ar | 741 | 512 | 284 |

## Fardigt mejlsvar

Hej Daniel,

Jag gjorde en egen overslagskorning i stallet for att anvanda Bornholms `ENERGYISLAND2050` rakt av. Skalet ar att `ENERGYISLAND2050` ar ett energy-island-/produktionsscenario, inte en datacenterprognos. I DuckDB ger det cirka 26,3 TWh 2040 och 49,7 TWh 2050, nastan helt vind, sa det ar for stort och for produktionsinriktat for fragan i bilden.

Som enklare planeringsnivaer anvande jag i stallet 10, 15 och 20 TWh per ar. Jag raknade sedan om dem med samma `AreaDemand.xlsx` som potentialappen anvander. Med en neutral 50/50-mix mellan landvind och sol blir median-ytbehovet ungefar:

| Efterfragan | Ytbehov, median |
|---:|---:|
| 10 TWh/ar | ca 260 km2 |
| 15 TWh/ar | ca 380 km2 |
| 20 TWh/ar | ca 510 km2 |

Som kanslighet ger samma medianfaktorer ungefarligen:

- 10 TWh/ar: ca 370 km2 om allt tas med landvind, ca 140 km2 om allt tas med sol.
- 15 TWh/ar: ca 560 km2 med landvind, ca 210 km2 med sol.
- 20 TWh/ar: ca 740 km2 med landvind, ca 280 km2 med sol.

Det har ar grova arlig-energi-ytor, inte en lokaliserings- eller tillstandsbedomning. De tar inte heller hand om effektprofil, natanslutning, lagring eller leveranssakerhet. Men som storleksordning ar slutsatsen tydlig: 10-20 TWh/ar ar sa stort att det bor behandlas som ett eget planeringsscenario, inte som en liten justering av Bornholms befintliga scenario.
