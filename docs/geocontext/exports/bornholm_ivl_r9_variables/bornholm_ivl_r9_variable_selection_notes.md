# Bornholm IVL R9 variable selection

Den här exporten är en smalare R9-version av Bornholms landskapsanalys, avsedd som GIS-/geografiunderlag till IVL:s acceptansundersökning.

## Urvalsprinciper

- Raderna är aktiva H3 R9-hexagoner från `landskapsanalys_v3_2_contourterrain68_res9`.
- Acceptansvariabler är exkluderade eftersom IVL ska undersöka acceptans.
- Area i m2/km2 är bortvald när en jämförbar `share`-variabel finns.
- Fullständig kontextmatris och interna vikter är bortvalda för att filen ska vara begriplig externt.
- Ett litet urval `mean`/`std` behålls eftersom omgivningskaraktär och heterogenitet kan vara analytiskt intressant för acceptans.

## Hur `mean` och `std` ska läsas

`mean` beskriver genomsnittlig omgivningskontext runt hexagonen, till exempel genomsnittlig skogsandel i modellens k100-omgivning. Det är alltså inte samma sak som hexagonens lokala skogsandel.

`std` beskriver variation eller heterogenitet i samma omgivning. Ett högt `std` betyder ofta att hexagonen ligger i en blandad zon eller övergångszon, medan lågt `std` antyder en mer homogen omgivning.

`k100` är modellens k100-omgivning från landskapsanalysen. Den ska läsas som en modellbaserad närmiljöskala, inte som 100 meter eller exakt 100 hexagoner.

## Filer

- CSV: `docs/geocontext/exports/bornholm_ivl_r9_variables/bornholm_ivl_r9_variables.csv`
- Kodbok: `docs/geocontext/exports/bornholm_ivl_r9_variables/bornholm_ivl_r9_variables_codebook.csv`
- Exkluderingslista: `docs/geocontext/exports/bornholm_ivl_r9_variables/bornholm_ivl_r9_excluded_variables.csv`
- Summering: `docs/geocontext/exports/bornholm_ivl_r9_variables/bornholm_ivl_r9_variables_summary.csv`
