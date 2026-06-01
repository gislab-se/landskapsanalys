# Handoff: djupaste hålan-analys

Datum: 2026-06-01
Planerad fortsättning: 2026-06-02

## Syfte

Vi ska undersöka om "djupaste hålan"-analysen bör beräknas som en stabil, förberäknad lämplighetsyta per region, teknik och H3-upplösning, i stället för att räknas om tungt varje gång appen körs.

Analogin: landskapet fylls som med vatten. De djupaste hålen fylls först, där "djupast" betyder mest lämpligt utifrån aktiva filter och parametrar. Ett restriktionsområde ska dock inte vara ett grunt eller dåligt hål, utan helt sakna kandidatstatus.

## Nuläge efter senaste ändringar

- Scenariofördelningen använder nu en prioritetspoäng, `allocation_priority_score`, för vind- och solkandidater.
- Vind väljer de bästa vindlägena, och sol väljer de bästa sollägena, oavsett om hexen även kan vara relevant för den andra tekniken.
- Gröna scenariohexar betyder att vind och sol faktiskt delar samma scenariohex, inte att kombinationen ska vara förstahandsval.
- Vektorvisning av käll- och buffertlager är opt-in i avancerade inställningar. Analysen använder fortfarande filtren även när vektorerna inte skickas till kartan.
- Tutorialen aktiverar relevanta kartlager för scenariofördelning och ytbehov utanför landskapets potential när lagren finns i aktuell karta.

## Frågor att analysera

1. Ska baslämplighet för vind och sol förberäknas en gång per region, teknik och H3-upplösning?
2. Vilka delar ska vara hårda exkluderingar, och vilka ska vara graderade lämplighetspoäng?
3. Hur ska runtime-val i appen påverka en förberäknad yta utan att dölja användarens filterlogik?
4. Ska vägavstånd, transformatorstationsnärhet, bebyggelseavstånd och skyddade områden beräknas som separata komponenter som sedan vägs samman?
5. Hur verifierar vi att scenariohexar aldrig väljs inom aktiva restriktionsområden?

## Tolkning av regler

- Naturreservat, rennäring och andra hårda restriktioner bör tas bort från kandidatmängden när de är aktiva.
- Avstånd till väg bör kunna tolkas som att längre bort är bättre, om filtret uttrycker störning eller konflikt.
- Närhet till transformatorstationer bör kunna tolkas som att närmare är bättre, om filtret uttrycker nätanslutningsnytta.
- Vind och sol bör ha separata lämplighetspoäng, eftersom deras bästa lägen inte nödvändigtvis är samma.
- En gemensam grön hex bör uppstå när båda teknikerna väljer samma starka plats, inte för att grönt prioriteras som kategori.

## Tekniska utgångspunkter

Relevanta kodställen att läsa först:

- `potential_app.py::_apply_landscape_priority_to_allocation_frame`
- `potential_app.py::_solar_establishment_frame`
- `potential_app.py::_combined_potential_establishment_frame`
- `apps/potential_model/energy_modeling.py::allocate_wind_area_from_core_hexes`
- `apps/potential_model/map_rendering.py` för kartlager och tutorialens overlay-API
- `acceptance_model.layers.distance_table_for_layer` för distansbaserade underlag

Regionala ramar:

- Trøndelag ska göra avstånd, buffert och area i `EPSG:25832`.
- Trøndelag ska inte exponera R9 i den interaktiva appen.
- Bornholm och Trøndelag bör valideras var för sig. Undvik att tvinga fram paritet om dataflödena skiljer sig.

## Föreslagen analys i morgon

1. Inventera vilka filter som idag är hårda exkluderingar respektive mjuka poäng.
2. Spåra vilka kolumner som faktiskt matar `allocation_priority_score`.
3. Kontrollera om alla scenario-kandidater har rimliga poäng och förklaringar.
4. Bygg ett litet testfall där en kandidat inom restriktionsområde aldrig får väljas.
5. Bygg ett testfall där två kandidater jämförs med tydlig väg-/transformatorlogik.
6. Bedöm om förberäknade tabeller kan skapas per region, teknik och H3-upplösning utan att låsa appens interaktiva filter.
7. Mät runtime före och efter eventuell förberäkning.

## Tester som bör finnas

- Kandidater inom aktiva hårda restriktioner väljs inte.
- Vind- och solkandidater får separata `allocation_priority_score`.
- Scenariofördelningen väljer högre lämplighet före lägre lämplighet även när färgkategori skiljer sig.
- Gröna scenariohexar uppstår bara när båda teknikerna faktiskt delar hex.
- Tutorialstegen för scenariofördelning och ytbehov aktiverar rätt lager när lagren finns.

## Status

Ingen ny förberäknad analys är implementerad i denna handoff. Syftet är att frysa frågan, nuläget och nästa beslutspunkt så arbetet kan fortsätta kontrollerat.
