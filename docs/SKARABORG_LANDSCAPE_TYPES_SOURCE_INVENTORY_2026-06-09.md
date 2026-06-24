# Skaraborg landskapstyper - källinventering

Status: 2026-06-09

Syfte: hitta bästa väg till landskapstyper för V3-region Skaraborg innan vi digitaliserar från bild/PDF.

## Rekommendation

Försök först få tag i original-GIS för Trafikverkets/Länsstyrelsens regionala landskapskaraktärsanalys för Västra Götaland. PDF-vektorisering bör vara reservspår, inte huvudspår.

Skälet: Trafikverkets E20-gestaltningsprogram säger att kartan över E20:s landskapstyper kommer från `Landskap i långsiktig planering, Pilotstudie i Västra Götaland` och att indelningen är gjord i landskapskaraktärsanalysen. Det betyder att kartan sannolikt har funnits som GIS-underlag innan den blev PDF-illustration.

## Kandidatkällor

### 1. Primär källa: LiLP / regional landskapskaraktärsanalys Västra Götaland

Källa:

- Trafikverket, `Including landscape in long-term spatial planning: A pilot study of Västra Götaland`
- Trafikverket/Länsstyrelsen, `Landskap i långsiktig planering - Pilotstudie i Västra Götaland`
- E20-programmet refererar till `Landskap i långsiktig planering, Pilotstudie i Västra Götaland Trafikverket 2011:122`

Vad vi behöver fråga efter:

- regionala landskapstyper som polygoner
- regionala karaktärsområden som polygoner
- attribut för typnamn, karaktärsområdesnamn, eventuell känslighet/potential
- original-CRS och metadata

Föreslaget frågeord:

`GIS-underlag/shapefile/GeoPackage för regionala landskapstyper och karaktärsområden från Landskap i långsiktig planering, Pilotstudie i Västra Götaland, Trafikverket 2011:122/2013:004. Vi behöver använda polygonerna som planeringsunderlag för Skaraborg/Västra Götaland och aggregera till H3-hexagoner.`

Styrka:

- bäst matchning mot Trafikverkets karta
- täcker hela Västra Götaland, inte bara E20-korridoren
- bör kunna klippas direkt till Skaraborg och omvandlas till V3-hex

Risk:

- GIS-filerna verkar inte ligga öppet publikt i en enkel nedladdningslänk
- kan behöva begäras via Trafikverket eller Länsstyrelsen Västra Götaland

### 2. Sekundär källa: Trafikverkets E20-PDF:er

Källor:

- `Övergripande Gestaltningsprogram, E20 genom Västra Götaland`, Trafikverket publ. 2013:088
- `Landskap i långsiktig planering - PM övergripande gestaltningsprogram för E20, sträckan genom Västra Götaland`, publ. 2014:088
- etappvisa handlingar, t.ex. `E20 förbi Skara` och `E20 Vårgårda-Vara`

Användning:

- referens för klassnamn, legend och kontroll mot E20:s egna beskrivningar
- möjlig reserv för manuell/semiautomatisk georeferering om original-GIS inte går att få

Styrka:

- offentligt tillgängliga handlingar
- visar vilka landskapstyper E20 passerar
- E20 Skara-handlingen beskriver lokala övergångar: Skaraberg, mosaikartad slätt och öppen slätt

Risk:

- PDF:erna är kartillustrationer, inte säkert GeoPDF
- E20-kartor täcker en vägkorridor och är inte nödvändigtvis tillräckliga för hela V3-region Skaraborg
- vektorisering från bild riskerar fel gränser, särskilt där färger/etiketter överlappar

### 3. Reserv/komplettering: bygg datadriven landskapstypologi

Om vi inte får original-GIS och PDF-kartan inte räcker kan vi skapa en Skaraborg-typologi med samma princip som Bornholm v10: samla GIS-signaler per hex, köra faktor/kluster, och göra en crosswalk till kommunikativa landskapstyper.

Möjliga svenska geodatakällor:

- Naturvårdsverket Nationella Marktäckedata, NMD2023: markanvändning/marktäcke, jordbruksdominans, skog, våtmark, exploaterad mark
- Lantmäteriet Markhöjdmodell Nedladdning: höjd, relief, lutning, platåberg/åsar
- SGU jordartsdata: lera, sand, morän, berg, isälvsmaterial
- SCB öppna geodata: tätorter, småorter, befolkningsrutor
- Naturvårdsverket skyddad natur/riksintressen
- Riksantikvarieämbetet/Länsstyrelsen kulturmiljöunderlag
- Lantmäteriet topografi/kommunikationer/vatten

Styrka:

- reproducerbart och kan täcka hela Skaraborg
- liknar Bornholm v10-flödet som redan fungerar i potentialappen
- kan även ge faktorer och osäkerhet, inte bara klasspolygoner

Risk:

- blir vår egen tolkning, inte Trafikverkets/LiLP:s expertindelning
- kräver review/crosswalk mot Skara-Varaslätten, Vadsboslätten, platåberg, mosaiklandskap etc.

## Förväntade landskapstyper runt Skaraborg

Utifrån E20-programmet och LiLP-kartan bör Skaraborg inte reduceras till bara en klass. Min preliminära förväntan är minst:

- `Slättlandskap`
- `Mosaiklandskap`
- `Platåberg`
- `Åslandskap`
- eventuellt `Storskaligt böljande landskap`
- eventuellt `Skogs- och sjödominerat sprickdalslandskap`

E20-programmet beskriver att E20 i Västra Götaland passerar småbrutet sprickdalslandskap, mosaiklandskap, slättlandskap och storskaligt böljande landskap. För Skaraborgs regionyta behöver vi däremot troligen hela den regionala typindelningen, inte bara de fyra E20-typerna.

## V2-referenser

Relevanta lokala arbetssätt:

- Bornholm v10 är datadriven och använder faktor/kluster som sedan tolkas till fem landskapstyper:
  - `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/report/bornholm_v10_landscape_types_report.md`
  - `apps/potential_model/manifests/landscape/bornholm_landscape_v10.json`
- Trøndelag PDF-spåret visar varför PDF-vektorisering måste ha review:
  - `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md`
  - särskilt kontroll av alla typer, gaps/overlaps och felklassningar
- Bornholm PDF-spåret är separerat från den datadrivna Bornholm v10-modellen:
  - `docs/BORNHOLM_PDF_LANDSCAPE_HANDOFF_2026-05-28.md`

## Föreslagen pipeline

1. Kontakta/begär original-GIS för LiLP Västra Götaland.
2. Om GIS fås:
   - kontrollera CRS och attribut
   - klipp till Skaraborg/V3-regiongräns
   - topologikontroll: gaps, overlaps, multipart, okända klasser
   - skapa GPKG/GeoJSON review layer
   - aggregera till H3 med dominant typ och typandelar per hex
   - skapa V3 manifest och review-tabell
3. Om GIS inte fås:
   - extrahera relevant kartbild ur PDF
   - kontrollera om PDF-vektorer kan extraheras direkt
   - georeferera mot kommungräns/sjöar/E20/tätorter i EPSG:3006
   - semimanuell vektorisering och review enligt Trøndelag/Bornholm PDF-handoffs
4. Om PDF blir för osäker:
   - bygg datadriven Skaraborg-typologi från NMD, DEM, SGU, SCB, skydd/kultur/topografi
   - kalibrera typnamn mot LiLP/E20-beskrivningarna

## Föreslaget första beslut

Gå inte direkt på PDF-vektorisering. Första praktiska steget bör vara att begära original-GIS från Trafikverket/Länsstyrelsen. Parallellt kan vi förbereda en datadriven fallback med Bornholm v10-metoden.

## Webbunderlag som kontrollerats

- Trafikverket E20 övergripande gestaltningsprogram: https://bransch.trafikverket.se/contentassets/31699a9e58664144a4291b2397dcd7dc/gestaltningsprogram_e20_150420.pdf
- Trafikverket PM E20 / LiLP: https://www.diva-portal.org/smash/get/diva2%3A1364685/FULLTEXT01.pdf
- Trafikverket DiVA, LiLP pilot study: https://trafikverket.diva-portal.org/smash/record.jsf?pid=diva2:1364688
- Trafikverket, Integrated landscape character assessment: https://bransch.trafikverket.se/en/startpage/planning/landscape/Landscape-planning/
- Trafikverket E20 mötesfri väg Västra Götaland: https://www.trafikverket.se/vara-projekt/projekt-i-vastra-gotalands-lan/e20-motesfri-vag-vastra-gotaland/
- Trafikverket dokument E20 förbi Skara: https://bransch.trafikverket.se/e20forbiskara-dokument
- Naturvårdsverket NMD nedladdning: https://www.naturvardsverket.se/verktyg-och-tjanster/kartor-och-karttjanster/nationella-marktackedata/ladda-ner-nationella-marktackedata/
- Lantmäteriet produktlista/geodata: https://www2.lantmateriet.se/sv/geodata/vara-produkter/produktlista/
- SGU jordartsdata: https://www.sgu.se/produkter-och-tjanster/geologiska-data/jordarter--geologiska-data/jordartsdata/
- SCB öppna geodata/statistik på rutor: https://www.scb.se/vara-tjanster/oppna-data/oppna-geodata/statistik-pa-rutor/
