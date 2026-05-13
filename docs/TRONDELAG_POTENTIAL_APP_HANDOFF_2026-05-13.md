# Trøndelag Potential App Handoff 2026-05-13

## Syfte

Kort handoff efter dagens Trøndelag-anpassning av potentialappen. Appen ska följa Bornholm-logiken: gemensam potentiell etableringsyta, scenariobehov utanför potentialen och controller-lager som kan tändas/släckas utan att blanda ihop potential, acceptans och landskapstypologi.

## Gjort idag

- Trøndelag är defaultregion i appöppning.
- R9 är borttagen från Trøndelag-appens H3-val. Kvar är R8, R7 och R6, med R7/zoomanpassad som praktiskt utgångsläge.
- Trøndelag kör Bornholm-liknande energimodelleringsscenario som placeholder.
- Appen startar med ofiltrerad potentiell etableringsyta när inga lager är tända.
- Befolkning/bebyggelse använder `trl_population_250m_centroids` som 250 m rut-/centroidproxy.
- Befolkningsbufferten renderas nu som dissolvad polygonbuffer från rutproxyn, inte som H3-bufferlager.
- Sol- och vindlager får separata lagernamn: `Sol källa`, `Solbuffert`, `Vind källa`, `Vindbuffert`.
- Root-`AGENTS.md` säger uttryckligen att Trøndelag-arbete först ska jämföras med Bornholm.

## Viktiga filer

- `potential_app.py`
- `apps/potential_model/manifests/regions/trondelag.json`
- `script/acceptance/render_trondelag_population_buffer.R`
- `AGENTS.md`
- `docs/TRONDELAG_POTENTIAL_APP_HANDOFF_2026-05-13.md`

## Aktuellt beteende

- Potentiell etableringsyta verkar fungera bra i Trøndelag.
- Solens befolkningskälla och solbuffert syns som egna lager.
- Vindens befolkningskälla och vindbuffert ska nu också få följa med i Trøndelag-kartan när energimodellen är aktiv. Tidigare filtrerades vindbufferten bort eftersom bara lager vars namn började med `Källa:` behölls.
- Samma befolkningsunderlag kan användas av sol och vind samtidigt, därför har lagernamnen fått teknikprefix.

## Kvar att kontrollera

- Öppna appen och verifiera visuellt att `Vindbuffert: Befolkningsunderlag` syns när vindens befolkning/bebyggelse-controller är aktiv.
- Testa att sol och vind kan ha olika buffertavstånd samtidigt utan att lagren dedupliceras bort.
- Första genereringen av en ny Trøndelag-buffertdistans kan ta runt 20-25 sekunder, men resultatet cachas som GeoJSON. Fundera på om vanliga avstånd ska förgenereras.
- Score/avståndstabellen är fortfarande centroidbaserad. På sikt bör den byggas om mot den upplösta 250 m rutpolygonen om vi vill att analys och visuell buffer ska vara helt geometriskt samstämda.
- Kontrollera att inga stora genererade runtime-bufferfiler råkar commitas utan aktivt beslut.

## Nästa steg

1. Visuell QA i appen för vindbuffert, solbuffert och lagerkontrollen.
2. Prestandatest efter kall cache och varm cache.
3. Förgenerera eventuellt ett litet set vanliga buffertar, exempelvis 500 m, 1000 m och 1500 m.
4. Bygg polygonbaserad distance table för befolkningsproxyn.
5. Fortsätt flytta Trøndelag mot Bornholm-mönstret innan nya speciallösningar läggs till.
