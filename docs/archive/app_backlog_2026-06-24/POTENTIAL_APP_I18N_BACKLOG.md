# Potential App I18n Backlog

## Status 2026-05-12

Forsta sprakstodet ar inkopplat i `potential_app.py`:

- sprakval sparas i `st.session_state`
- tre val finns: danska/norska, svenska och engelska
- sprakvaxlaren visas som kompakta flagg-/sprakkodknappar
- huvudrubrik, panelstruktur, H3-kontroller, missing-data-vy, energikontroller och centrala hogerpanelsrubriker anvander oversattningshelper
- saknade oversattningar faller tillbaka till svensk standardtext

## Kvar att lyfta

Appen har fortfarande manga hardkodade meningar i loptext, tabellkolumner, kart-popuptexter och vissa dynamiska sammanfattningar. Nasta pass bor fokusera pa:

- kartlegend och popuptexter
- tabellkolumner i sammanfattningar och harledningar
- alla varnings- och infomeddelanden
- sol- och vindfiltergruppernas hjalptexter
- energimodelleringens datakvalitetstexter
- manifeststyrda etiketter om de ska oversattas utan att andra regiondata andras

Principen ligger fast: regiondata, filvagar, scenario-id och kallnamn ska inte oversattas.
