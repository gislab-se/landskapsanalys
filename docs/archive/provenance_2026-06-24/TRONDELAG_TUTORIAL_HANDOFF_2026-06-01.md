# Trondelag Tutorial Handoff 2026-06-01

## Status efter fortsatt arbete

Efter commit `6744c5f` har steg 7 och 8 justerats i arbetskatalogen.

Nuvarande arbetsversion:

- steg 7 stänger andra expanders, öppnar `Geografier` och highlightar `Landskapspotential Vind` + `Landskapspotential Sol`
- steg 8 stänger andra expanders, öppnar `Geografier -> Landskapspotential Vind -> Befolkning och bebyggelse`, scrollar till `Använd ändringar` och highlightar knappen
- `scripts/test_potential_tutorial_ui.py` är utökat så testet kontrollerar steg 7 och 8
- UI-testet passerade mot `http://localhost:8505`

Detta är ännu inte committat efter `6744c5f`.

## Sparad version

Bra mellanversion är committad:

- `6744c5f feat: harden Trondelag guided tutorial`

Den committen innehåller:

- kort guide för Trondelag i `potential_app.py`
- robustare kart-targeting för steg 5 och 6
- Selenium-baserat UI-test i `scripts/test_potential_tutorial_ui.py`
- passerande test mot `http://localhost:8505` innan handoff

Generated screenshots i `artifacts/tutorial_ui_test/` är inte committade.

## Kvarvarande problem

Steg 7 och 8 kommer fortfarande fel i manuell körning.

I användarens skärmdump för steg 7:

- tutorialen säger "Vind och sol styrs under Geografier"
- highlighten hamnar ändå över fel del av vänsterpanelen
- synligt läge visar bland annat slutet av energimodellering/social acceptans i stället för tydligt `Geografier -> Landskapspotential Vind/Sol`

Trolig orsak:

- tutorialen förlitar sig på textmatchning i Streamlits `details`-DOM
- sidebaren kan vara scrollad eller ha gamla expanders öppna från tidigare steg/användarinteraktion
- när texttarget inte hittas stabilt faller guiden tillbaka till för stor panel/sektion

## Önskad omskrivning

### Steg 7

Syfte:

Visa tydligt att det finns två controllers under `Geografier`:

- `Landskapspotential Vind`
- `Landskapspotential Sol`

Förslag:

- stäng andra huvudexpanders innan steget, särskilt `Energimodellering` och `Social acceptans`
- sätt sidebaren till ett förutsägbart läge, helst scrollTop nära toppen
- öppna `Geografier`
- visa bara `Landskapspotential Vind` och `Landskapspotential Sol` som synliga mål
- highlighta de två controller-raderna, inte hela sidebaren

Textförslag:

> Under Geografier finns separata controllers för Landskapspotential Vind och Landskapspotential Sol. De styr vilka geografiska antaganden, lager och restriktioner som påverkar respektive teknik.

### Steg 8

Syfte:

Visa hur användaren öppnar vindpotentialen och tillämpar ett filter.

Förslag:

- behåll `Geografier` öppnad
- öppna `Landskapspotential Vind`
- öppna `Befolkning och bebyggelse`
- scrolla bara så mycket att `Befolkning och bebyggelse` och knappen `Använd ändringar` syns
- highlighta helst `Befolkning och bebyggelse` plus `Använd ändringar`, eller bara knappen om det blir för trångt

Textförslag:

> Öppna Landskapspotential Vind och justera till exempel Befolkning och bebyggelse. När du ändrar ett lager behöver du klicka på Använd ändringar för att kartan och resultatet ska räknas om.

## Rekommenderad implementation

Gör steg 7 och 8 mer explicita än övriga steg:

- lägg till stöd i tutorial-JS för `closeTexts`
- lägg till stöd för `scrollSidebarTop` eller `scrollToText`
- överväg att lägga faktiska `data-potential-tutorial-anchor` runt controller-raderna i stället för att bara söka text
- undvik fallback till hela `section[data-testid="stSidebar"]` för steg som har `highlightTexts`; om target saknas är det bättre att visa en liten fallback nära `Geografier`

## Test att lägga till

Utöka `scripts/test_potential_tutorial_ui.py`:

- kontrollera att steg 7-highlight överlappar `Landskapspotential Vind` och `Landskapspotential Sol`
- kontrollera att steg 7 inte överlappar `Social acceptans`
- klicka vidare till steg 8
- kontrollera att `Befolkning och bebyggelse` är synlig
- kontrollera att `Använd ändringar` är synlig och highlightad eller nära highlighten
