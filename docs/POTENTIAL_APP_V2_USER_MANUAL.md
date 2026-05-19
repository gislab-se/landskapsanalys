# Potential App v2: kort användarmanual

För en längre förklaring av appens syfte, metod, resultat och felsökning, se
`docs/POTENTIAL_APP_V2_STAKEHOLDER_METHOD_DEBUG.md`.

## Status

Appen är en **BETA / utvecklingsversion**. Den är gjord för test, dialog och felsökning, inte som färdig planeringsprodukt.

Social acceptans är just nu syntetiskt testdata. För Trøndelag bygger befolkningsunderlaget på en 250 m rut-/centroidproxy, inte individuella befolkningspunkter.

## Start

Öppna appen via `streamlit_app.py`.

Välj region i vänsterpanelen:

- `Trondelag`
- `Bornholm`

Trøndelag öppnar i H3 R7. R8/R9 ska inte användas i den interaktiva Trøndelag-vyn.

## Vänsterpanelen

Vänsterpanelen styr vad som räknas och visas.

Använd:

- **Region** för att byta region.
- **Landskapslager** för landskapstyper, strukturer och faktorer.
- **Vind** för vindpotential och vindrelaterade avstånd/filter.
- **Sol** för storskalig sol, småskalig sol och solfilter.
- **Social acceptans** för syntetiskt testlager.
- **Energimodellering** för scenario, energimix och etableringsyta.

När du ändrar sol- eller vindfilter: tryck **Använd ändringar** för att räkna om appen.

## Landskapspotential och etableringsyta

Landskapspotential för sol och vind används främst som beräkningsunderlag. Den hjälper appen att avgöra var sol, vind eller båda teknikerna kan ingå i den gemensamma etableringsytan efter aktiva filter.

I normal användning ska du därför läsa **Potentiell etableringsyta** som huvudlagret, inte leta efter separata landskapspotential-lager som slutresultat. Landskapspotentialen syns framför allt indirekt i etableringsytan, högerpanelens statistik och härledningstabeller.

## Kartan

Kartan visar aktiva lager.

Viktiga lager:

- **Potentiell etableringsyta**
- **Scenariofördelning i etableringshex**
- **Ytbehov utanför landskapets potential**
- **Social acceptans**

Vissa debug- eller granskningslägen kan fortfarande visa underlagslager för sol/vind, men huvudtolkningen ska göras via etableringsytan och högerpanelen.

Du kan tända och släcka lager i kartans lagerkontroll. Opacitet styrs med reglagen.

## Högerpanelen

Högerpanelen sammanfattar resultatet.

Titta särskilt på:

- hur mycket scenarioyta som ryms inom potential
- hur mycket ytbehov som ligger utanför potential
- vilka filter som är aktiva
- kartlager och debugtabeller
- landskapshärledning för sol och vind

Om högerpanelen säger att scenariot inte ryms inom potential visas extra ytbehov som ett eget kartlager.

## Vanligt arbetsflöde

1. Välj region.
2. Kontrollera H3-upplösning.
3. Välj vilka sol- och vindfilter som ska ingå i beräkningen.
4. Justera filter i vänsterpanelen.
5. Tryck **Använd ändringar**.
6. Läs etableringsytan och sammanfattningen i högerpanelen.
7. Kontrollera kartlagren.
8. Testa ett annat scenario eller energimix.

## Tolka med försiktighet

Resultaten ska läsas som ett utvecklingsunderlag. Kontrollera alltid:

- att rätt region är vald
- att rätt H3-upplösning används
- att filtren verkligen är applicerade
- att social acceptans inte tolkas som verkligt IVL-resultat
- att Trøndelag befolkningsbuffertar förstås som 250 m proxydata

## Test och debug

Det finns två hjälpskript för v2:

```powershell
C:\gislab\landskapsanalys\.venv\Scripts\python.exe scripts\stress_potential_app_v2.py
C:\gislab\landskapsanalys\.venv\Scripts\python.exe scripts\smoke_potential_app_v2_ui.py
```

Använd dem när appen ändras. De kontrollerar att regionbyte, filter, högerpanel, social acceptans och BETA-märkning fortfarande fungerar.
