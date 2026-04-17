from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "docs" / "geocontext" / "published_report"
SOURCE = REPORT_DIR / "landskapsanalys_v4.knit.md"
TARGET = REPORT_DIR / "landskapsanalys_v4_english_review.md"


def clean_quarto_wrappers(text: str) -> str:
    text = re.sub(
        r"```{=html}\s*<iframe.*?</iframe>\s*```",
        (
            "**Interactive map placeholder:** The combined cluster and factor map is "
            "available in the original web report: "
            "https://gislab-se.github.io/landskapsanalys/published_report/"
            "landskapsanalys_v4_combined_map.html"
        ),
        text,
        flags=re.S,
    )
    text = re.sub(
        r'<p><a class="btn btn-primary btn-sm" href="landskapsanalys_v4_combined_map.html".*?</a></p>',
        (
            "[Open the combined map in the web report]"
            "(https://gislab-se.github.io/landskapsanalys/published_report/"
            "landskapsanalys_v4_combined_map.html)"
        ),
        text,
        flags=re.S,
    )
    text = re.sub(
        r'<p><a class="btn btn-outline-primary btn-sm" href="tables/landskapsanalys_v4_factor_loadings_readable.xlsx".*?</a></p>',
        (
            "[Open the readable factor-loadings workbook]"
            "(https://gislab-se.github.io/landskapsanalys/published_report/"
            "tables/landskapsanalys_v4_factor_loadings_readable.xlsx)"
        ),
        text,
        flags=re.S,
    )
    text = re.sub(
        r'<p><a class="btn btn-outline-secondary btn-sm" href="#combined-map-top">.*?</a></p>',
        (
            "[Return to the combined map in the web report]"
            "(https://gislab-se.github.io/landskapsanalys/published_report/"
            "landskapsanalys_v4_combined_map.html)"
        ),
        text,
        flags=re.S,
    )
    text = text.replace("::: {.cell-output-display}\n", "")
    text = text.replace("::: {.cell}\n", "")
    text = text.replace(":::\n", "")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def apply_replacements(text: str) -> str:
    replacements = [
        (
            'title: "Landskapsanalys Bornholm"',
            'title: "Landscape Analysis Bornholm"',
        ),
        ("lang: sv", "lang: en"),
        ("format:\n  html:\n    toc: true\n    toc-depth: 3\n    embed-resources: true", "format: docx"),
        (
            "> Denna rapport presenterar den aktuella landskapsanalysen för Bornholm. Fokus ligger på hur öns landskapskaraktär kan beskrivas med ett multiskalärt, hexagonbaserat analysramverk som kombinerar natur, bebyggelse, tillgänglighet, skydd, restriktioner och geologi.",
            "> This report presents the current landscape analysis for Bornholm. It focuses on how the island's landscape character can be described through a multiscalar, hexagon-based analytical framework that combines nature, settlement, accessibility, protection, restrictions, and geology.",
        ),
        ("## Kartöversikt", "## Map Overview"),
        (
            "Den samlade kartan ligger först i rapporten och är tänkt som huvudytan för tolkning. Här kan du växla mellan kluster och faktorer i samma HTML-karta, läsa tydliga legender och öppna popup-rutor som visar typ, tolkning, faktorprofil och de lager i hexet som bidrar mest till analysen.",
            "The combined map is placed first in the report and is intended as the main surface for interpretation. In the web version, the reader can switch between clusters and factors in the same HTML map, read clear legends, and open popups showing type, interpretation, factor profile, and the layers in each hexagon that contribute most to the analysis.",
        ),
        ("## 1. Syfte och huvudfråga", "## 1. Purpose and Main Question"),
        (
            "Denna rapport beskriver den aktuella landskapsanalysen för Bornholm. Målet är att ge ett tydligt och spårbart underlag för att beskriva hur öns landskap är uppbyggt, var olika landskapssammanhang dominerar och vilka mönster som återkommer på flera skalor.",
            "This report describes the current landscape analysis for Bornholm. The aim is to provide a clear and traceable basis for describing how the island's landscape is structured, where different landscape contexts dominate, and which patterns recur across several scales.",
        ),
        ("Huvudfrågan är:", "The main question is:"),
        (
            "**Vilken landskapskaraktär har Bornholm när ön beskrivs med ett multiskalärt, hexagonbaserat analysramverk som kombinerar natur, bebyggelse, tillgänglighet, skydd, restriktioner och geologi?**",
            "**What landscape character does Bornholm have when the island is described through a multiscalar, hexagon-based analytical framework that combines nature, settlement, accessibility, protection, restrictions, and geology?**",
        ),
        ("Rapporten har tre konkreta uppgifter:", "The report has three concrete tasks:"),
        ("- att dokumentera vilken data som faktiskt ingår i modellen", "- to document which data are actually included in the model"),
        ("- att steg för steg förklara hur rådata blir till faktorer och preliminära landskapstyper", "- to explain, step by step, how raw data become factors and preliminary landscape types"),
        ("- att ge en tolkning som är begriplig även för läsare som inte arbetar dagligen med faktoranalys och klustring", "- to provide an interpretation that is understandable even for readers who do not work with factor analysis and clustering on a daily basis"),
        (
            "På längre sikt kan samma analyskedja vara ett av flera underlag i ett acceptanslager för vindkraft och solenergi. Den här rapporten är dock en **landskapskaraktärsrapport**, inte ett färdigt planeringsbeslut. Den säger något viktigt om struktur, mönster och landskapstyper, men gör inte hela avvägningen mellan landskapsvärden, juridik, teknik och social acceptans.",
            "In the longer term, the same analytical chain may become one of several inputs to an acceptance layer for wind power and solar energy. This report is, however, a **landscape-character report**, not a completed planning decision. It says something important about structure, patterns, and landscape types, but it does not make the full trade-off between landscape values, law, technology, and social acceptance.",
        ),
        (
            "Det centrala värdet i nuläget är att modellen täcker stora delar av Bornholms relevanta landskapsinnehåll och dessutom använder ett terrängspår från originalhöjdkurvorna. Kvarvarande arbete handlar därför främst om validering, namnsättning och finjustering av hur jordbruksplatåer och sprickdalsliknande terräng ska uttryckas.",
            "The central value at this stage is that the model covers large parts of Bornholm's relevant landscape content and also uses a terrain track derived from the original contour lines. The remaining work is therefore mainly about validation, naming, and fine-tuning how agricultural plateaus and fracture-valley-like terrain should be expressed.",
        ),
        ("## 2. Studieområde, skala och avgränsning", "## 2. Study Area, Scale, and Delimitation"),
        (
            "Analysen omfattar Bornholm på samma R9-hexgrid som tidigare körningar, enligt H3:s upplösningssystem ([H3: Tables of Cell Statistics Across Resolutions](https://h3geo.org/docs/core-library/restable/)). Den fasta analysenheten är alltså en regelbunden hexagon, medan landskapskaraktären uppstår genom att varje hexagon beskrivs både lokalt och genom sin omgivning.",
            "The analysis covers Bornholm using the same R9 hex grid as earlier runs, following H3's resolution system ([H3: Tables of Cell Statistics Across Resolutions](https://h3geo.org/docs/core-library/restable/)). The fixed analytical unit is therefore a regular hexagon, while landscape character emerges by describing each hexagon both locally and through its surroundings.",
        ),
        ("Skalvalet har tre konsekvenser:", "The scale choice has three consequences:"),
        ("- analysen är bra på att beskriva regionala och mellanskaliga mönster", "- the analysis is good at describing regional and medium-scale patterns"),
        ("- den är svagare för mycket små lokala kvaliteter som bara finns i några få hektar", "- it is weaker for very small local qualities that exist only across a few hectares"),
        ("- den får inte läsas som om varje enskild hexagon redan vore ett landskapsområde i sig", "- it should not be read as if each individual hexagon were already a landscape area in itself"),
        ("## 3. Datagrund", "## 3. Data Basis"),
        (
            "Analysen bygger på 68 lagersignaler. Datagrunden är därför bred nog för att fånga Bornholm som både naturgeografiskt och kulturgeografiskt landskap: skog, jordbruk, topografi, kust, vatten, kulturmiljö, bebyggelse, skydd, restriktioner och geologi finns nu i samma analysram.",
            "The analysis is based on 68 layer signals. The data basis is therefore broad enough to capture Bornholm as both a physical-geographic and cultural-geographic landscape: forest, agriculture, topography, coast, water, cultural environment, settlement, protection, restrictions, and geology are now included in the same analytical framework.",
        ),
        (
            "Det betyder konkret att varje rålager först översätts till en jämförbar hexsignal: punktlager som antal eller summerade attributvärden per hexagon, linjelager som linjelängd inom hexagonen, polygonlager som area eller areaandel, och terränglager som sammanfattad statistik per hexagon.",
            "In concrete terms, this means that each raw layer is first translated into a comparable hex signal: point layers as counts or summed attribute values per hexagon, line layers as line length within the hexagon, polygon layers as area or area share, and terrain layers as summary statistics per hexagon.",
        ),
        (
            "Särskilt viktigt i denna rapport är att topografin inte bara beskrivs via tidigare hexaggregerade höjdmått. Analysen använder också en **konturhärledd pseudo-DEM** från originalhöjdkurvorna, varifrån medelhöjd, lutning och lokal daldjupssignal aggregeras tillbaka till hexagonerna.",
            "A particularly important point in this report is that topography is not described only through earlier hex-aggregated elevation metrics. The analysis also uses a **contour-derived pseudo-DEM** from the original contour lines, from which mean elevation, slope, and a local valley-depth signal are aggregated back to the hexagons.",
        ),
        (
            "Särskilt viktigt i denna rapport är att två tidigare provisoriska geologilager har ersatts av **21 tolkbara underkategorier** från Jordart och Prekvart. Det gör att geologi inte längre bara finns som nästan heltäckande bakgrund, utan som faktisk landskapssignal som går att läsa och jämföra med andra teman.",
            "Another particularly important point in this report is that two earlier provisional geology layers have been replaced by **21 interpretable subcategories** from Jordart and Prekvart. This means that geology is no longer present only as an almost complete background, but as an actual landscape signal that can be read and compared with other themes.",
        ),
        ("I stora drag består datagrunden av följande grupper:", "Broadly speaking, the data basis consists of the following groups:"),
        ("- bosättning och tillgänglighet: befolkning, vägar, färjerutter och flera bebyggelselager", "- settlement and accessibility: population, roads, ferry routes, and several settlement layers"),
        ("- blågröna strukturer: sjöar, våtmarker, hede, skog, ekologiska samband, naturtyper och vattendrag", "- blue-green structures: lakes, wetlands, heath, forest, ecological connectivity, nature types, and watercourses"),
        ("- kustsammanhang: kustlinje, kustzon, sanddyner och strandskydd", "- coastal context: coastline, coastal zone, sand dunes, and shore protection"),
        ("- kultur och markanvändning: kulturmiljövärden, värdefulla kulturmiljöer och jordbruksmark", "- culture and land use: cultural-environment values, valuable cultural environments, and agricultural land"),
        ("- topografi och geologi: relief, högsta höjd, konturhärledd medelhöjd, konturhärledd lutning, konturhärlett daldjup, jordartsunderlag och prekvartär berggrund", "- topography and geology: relief, highest elevation, contour-derived mean elevation, contour-derived slope, contour-derived valley depth, Quaternary surface geology, and pre-Quaternary bedrock"),
        ("- skydd och restriktioner: Natura, fredade områden, reservat, militära ytor och flygrestriktionslager", "- protection and restrictions: Natura areas, protected areas, reserves, military areas, and aviation-restriction layers"),
        (
            "Tabellen nedan är den viktigaste referensen för exakt innehåll och bör läsas som modellens officiella lagerlista. Här ligger fokus på vad lagret är, vilken typ av hexsignal det blir, och varifrån datan kommer.",
            "The table below is the most important reference for exact content and should be read as the model's official layer list. The focus is on what the layer is, what type of hex signal it becomes, and where the data come from.",
        ),
        (
            "Tabellen ovan visar hur brett modellen faktiskt täcker ön. Den ska läsas som en snabb översikt: vissa teman består av många lager därför att de har splittrats i mer tolkbara undergrupper, medan andra teman representeras av färre men mycket starka signaler.",
            "The table above shows how broadly the model actually covers the island. It should be read as a quick overview: some themes consist of many layers because they have been split into more interpretable subgroups, while other themes are represented by fewer but very strong signals.",
        ),
        (
            "**Styrka i datagrunden:** modellen täcker nu Bornholms huvudsakliga landskapssystem på ett sätt som gör den användbar som sammanhållen typologi och inte bara som en preliminär testkörning.",
            "**Strength of the data basis:** the model now covers Bornholm's main landscape systems in a way that makes it useful as a coherent typology, not only as a preliminary test run.",
        ),
        (
            "**Det som fortfarande står utanför den aktiva 58-lagersmodellen:** totalt 22 lager finns i den sammanfogade råmatrisen men används inte i den aktiva analysen. Vissa av dessa är medvetet ersatta av bättre representationer, till exempel att parentlagren för Jordart och Prekvart har bytts ut mot mer tolkbara underkategorier. Andra är rimliga kandidater för nästa prövning, särskilt energiinfrastruktur, bevaringsvärda landskap samt finare uppdelningar av vattendrag och naturtyper.",
            "**What still remains outside the active 58-layer model:** a total of 22 layers exist in the merged raw matrix but are not used in the active analysis. Some of these have deliberately been replaced by better representations, for example where the parent layers for Jordart and Prekvart have been replaced by more interpretable subcategories. Others are reasonable candidates for the next test, especially energy infrastructure, landscapes worthy of preservation, and finer subdivisions of watercourses and nature types.",
        ),
        ("## 4. Metod och transparens", "## 4. Method and Transparency"),
        (
            "Metoden följer samma grundidé som i Juta Kawalerowicz och Bo Malmbergs multiskalära typologiarbete ([Multiscalar Typology of Residential Areas in Sweden](https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826)): en plats ska inte bara beskrivas av vad som finns **i själva rutan**, utan också av **vilket sammanhang rutan ligger i** när omgivningen läses på flera skalor. I deras fall gäller det bostadsområden; här överförs samma logik till landskapstyper på Bornholm.",
            "The method follows the same basic idea as Juta Kawalerowicz and Bo Malmberg's work on multiscalar typology ([Multiscalar Typology of Residential Areas in Sweden](https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826)): a place should not only be described by what is found **inside the cell itself**, but also by **the context in which the cell is located** when the surroundings are read at several scales. In their case this concerns residential areas; here the same logic is transferred to landscape types on Bornholm.",
        ),
        ("Översatt till denna rapport betyder det:", "Translated into this report, this means:"),
        ("- först samlas många olika landskapssignaler i samma hexagonala analysenhet", "- first, many different landscape signals are gathered in the same hexagonal analytical unit"),
        ("- sedan beskrivs varje hexagon både lokalt och genom sin omgivning på flera skalor", "- then each hexagon is described both locally and through its surroundings at several scales"),
        ("- därefter komprimeras den stora mängden mönster till ett mindre antal faktorer", "- after that, the large set of patterns is compressed into a smaller number of factors"),
        ("- slutligen grupperas hexagoner med liknande faktorprofiler till preliminära landskapstyper", "- finally, hexagons with similar factor profiles are grouped into preliminary landscape types"),
        (
            "Analysen följer därmed en tydlig kedja från rådata till tolkning. Det gör också att varje steg kan granskas för sig: dataurvalet, kontextbyggandet, faktoranalysen, klustringen och den slutliga karttolkningen.",
            "The analysis therefore follows a clear chain from raw data to interpretation. This also makes it possible to review each step separately: the data selection, context building, factor analysis, clustering, and final map interpretation.",
        ),
        ("### 4.1 Från rådata till kontext", "### 4.1 From Raw Data to Context"),
        (
            "Varje ingångslager aggregeras först till R9-hexagoner. Därefter byggs en **kontextmatris** där varje hexagon får information om sin omgivning vid `k = 10, 50, 100, 250, 1000`.",
            "Each input layer is first aggregated to R9 hexagons. A **context matrix** is then built in which each hexagon receives information about its surroundings at `k = 10, 50, 100, 250, 1000`.",
        ),
        (
            "I praktiken betyder det att alla geometrier först översätts till samma analysenhet. Punktlager summeras som antal eller summerade attributvärden för de punkter som faller inom hexagonen. Linjelager summeras som den linjelängd som ligger inom hexagonen. Polygonlager översätts till total area eller areaandel inom hexagonen. Kontinuerliga terrängmått sammanfattas som statistik per hexagon, till exempel medelvärde, relief eller högsta värde. Först när alla lager uttrycks i denna gemensamma form kan de jämföras, viktas och läsas tillsammans i samma analysmatris.",
            "In practice, this means that all geometries are first translated into the same analytical unit. Point layers are summarized as counts or summed attribute values for points that fall within the hexagon. Line layers are summarized as the line length located within the hexagon. Polygon layers are translated into total area or area share within the hexagon. Continuous terrain metrics are summarized as statistics per hexagon, for example mean value, relief, or highest value. Only when all layers are expressed in this common form can they be compared, weighted, and read together in the same analysis matrix.",
        ),
        ("Två mått beräknas för varje lager och varje skala:", "Two metrics are calculated for each layer and each scale:"),
        ("- `mean`: hur mycket av signalen som i genomsnitt finns i omgivningen", "- `mean`: how much of the signal is present on average in the surroundings"),
        ("- `std`: hur jämn eller splittrad signalen är i omgivningen", "- `std`: how even or fragmented the signal is in the surroundings"),
        (
            "Detta steg är avgörande. En hexagon med lite skog kan ligga mitt i ett stort skogligt inland, i en kustnära övergångszon eller i ett jordbrukslandskap med små skogsöar. Lokalt värde räcker därför inte; det är kombinationen av lokalt innehåll och omgivande struktur som gör tolkningen landskaplig.",
            "This step is crucial. A hexagon with little forest may lie in the middle of a large forested inland, in a coastal transition zone, or in an agricultural landscape with small forest islands. The local value is therefore not enough; it is the combination of local content and surrounding structure that makes the interpretation landscape-based.",
        ),
        (
            "I denna modell är `k` inte samma sak som antal hexringar. I stället anger `k` hur mycket kumulativ kontextvikt som ska fångas upp när modellen går utåt genom närmaste grannar. Det betyder att samma `k` kan motsvara olika geografiska utbredningar i olika delar av ön beroende på hur stark signalstrukturen är.",
            "In this model, `k` is not the same as the number of hex rings. Instead, `k` indicates how much cumulative context weight should be captured as the model moves outward through nearest neighbours. This means that the same `k` can correspond to different geographic extents in different parts of the island, depending on the strength of the signal structure.",
        ),
        (
            "Den aktiva viktstrategin i denna körning är Per-layer robust q99 scaling, theme-balanced aggregation within each geometry type, moderate agricultural-land priority, mild continuous-metric uplift, six terrain bands from relief and absolute height, and four contour-derived terrain metrics from an interpolated pseudo-DEM.. Det betyder i praktiken att modellen inte bara frågar vilka grannar som ligger närmast, utan också hur mycket samlad signalvikt som fångas när kontexten byggs utåt från varje hexagon.",
            "The active weighting strategy in this run is per-layer robust q99 scaling, theme-balanced aggregation within each geometry type, moderate agricultural-land priority, mild continuous-metric uplift, six terrain bands from relief and absolute height, and four contour-derived terrain metrics from an interpolated pseudo-DEM. In practice, this means that the model does not only ask which neighbours are closest, but also how much combined signal weight is captured as the context is built outward from each hexagon.",
        ),
        (
            "I denna körning reskalas den balanserade kontextvikten dessutom med faktor 68.000 enligt rescale-läget 'n_input_layers' innan k-trösklarna beräknas.",
            "In this run, the balanced context weight is also rescaled by a factor of 68.000 according to the rescale mode 'n_input_layers' before the k thresholds are calculated.",
        ),
        (
            "Med 68 lager och två kontextmått över fem skalor får modellen 680 kontextvariabler. Det är dessa variabler, inte de råa lagren ensamma, som utgör den egentliga analysmatrisen.",
            "With 68 layers and two context metrics across five scales, the model produces 680 context variables. These variables, not the raw layers alone, constitute the actual analysis matrix.",
        ),
        ("### 4.2 Vad en faktor är, och vad den inte är", "### 4.2 What a Factor Is, and What It Is Not"),
        (
            "Faktoranalys kan lätt uppfattas som abstrakt. I den här rapporten är det därför viktigt att definiera begreppet tydligt:",
            "Factor analysis can easily seem abstract. In this report it is therefore important to define the concept clearly:",
        ),
        ("- en **faktor** är inte ett färdigt område på kartan", "- a **factor** is not a finished area on the map"),
        ("- en faktor är inte heller ett juridiskt eller administrativt lager", "- a factor is also not a legal or administrative layer"),
        ("- en faktor är i stället en **återkommande gradient** i datan: ett sätt på vilket flera lager och flera skalor tenderar att samvariera", "- instead, a factor is a **recurring gradient** in the data: a way in which several layers and several scales tend to co-vary"),
        (
            "Om exempelvis skog, fredskov och vissa natur- eller geologisignaler ofta förekommer tillsammans på flera skalor, kommer faktoranalysen att försöka fånga detta som en sammanhållen riktning. Varje hexagon får sedan ett faktorscore som visar hur starkt den hör ihop med just den gradienten.",
            "If, for example, forest, fredskov, and certain nature or geology signals often occur together at several scales, the factor analysis will try to capture this as a coherent direction. Each hexagon then receives a factor score showing how strongly it belongs to that particular gradient.",
        ),
        ("I denna körning görs faktoranalysen i fyra steg:", "In this run, the factor analysis is carried out in four steps:"),
        ("1. kontextmatrisen standardiseras så att olika enheter blir jämförbara", "1. the context matrix is standardized so that different units become comparable"),
        ("2. kolumner med nollvarians, bara saknade värden eller infinita värden tas bort", "2. columns with zero variance, only missing values, or infinite values are removed"),
        ("3. endast rader med komplett faktorinput används i själva faktorberäkningen", "3. only rows with complete factor input are used in the factor calculation itself"),
        ("4. `minres` med `varimax` används för att få en tolkbar uppsättning relativt ortogonala faktorer", "4. `minres` with `varimax` is used to obtain an interpretable set of relatively orthogonal factors"),
        (
            "Resultatet ska läsas som en komprimerad beskrivning av Bornholms viktigaste återkommande landskapssamband, inte som ett facit över färdiga landskapsrum.",
            "The result should be read as a compressed description of Bornholm's most important recurring landscape relationships, not as a definitive answer about finished landscape areas.",
        ),
        ("### 4.3 Vad ett kluster är, och vad det inte är", "### 4.3 What a Cluster Is, and What It Is Not"),
        (
            "Efter faktoranalysen grupperas hexagoner med liknande faktorprofiler. Det är detta som ger rapportens **preliminära landskapstyper**.",
            "After the factor analysis, hexagons with similar factor profiles are grouped. This is what produces the report's **preliminary landscape types**.",
        ),
        ("Även här behövs en tydlig definition:", "Here too, a clear definition is needed:"),
        ("- ett **kluster** är en grupp hexagoner som liknar varandra i faktorrummet", "- a **cluster** is a group of hexagons that resemble each other in factor space"),
        ("- ett kluster behöver inte vara sammanhängande som en enda polygon på kartan", "- a cluster does not have to be contiguous as a single polygon on the map"),
        ("- klustret blir meningsfullt först när dess faktorprofil jämförs med kartläge, datainnehåll och Bornholms kända landskapsstruktur", "- the cluster becomes meaningful only when its factor profile is compared with map position, data content, and Bornholm's known landscape structure"),
        (
            "Klustren är alltså modellens bästa försök att översätta abstrakta faktorer till läsbara landskapstyper. Därför är klusterkartan mer konkret än faktorernas kartor, men den bygger fortfarande på en statistisk typologi och måste tolkas med landskapskunskap.",
            "The clusters are therefore the model's best attempt to translate abstract factors into readable landscape types. The cluster map is consequently more concrete than the factor maps, but it is still based on a statistical typology and must be interpreted with landscape knowledge.",
        ),
        ("### 4.4 Viktiga metodiska förbehåll", "### 4.4 Important Methodological Reservations"),
        ("- Faktoranalysen bygger på 680 kontextvariabler, inte direkt på de 68 rålagren.", "- The factor analysis is based on 680 context variables, not directly on the 68 raw layers."),
        ("- 605 rena havshex utan signal har tagits bort före kontextmatris, faktoranalys och klustring.", "- 605 pure sea hexagons without signal have been removed before the context matrix, factor analysis, and clustering."),
        ("- Kust- eller havshex med faktisk signal ligger däremot kvar, till exempel om de träffas av kustlinje, kustzon, färjerutter eller andra aktiva lager. Masken är alltså en signalmask, inte en ren landmask.", "- Coastal or sea hexagons with actual signal remain, however, for example if they intersect the coastline, coastal zone, ferry routes, or other active layers. The mask is therefore a signal mask, not a pure land mask."),
        ("- 0 hexagoner saknar total signal i viktkolumnen. De ligger kvar i geografin men visar att vissa delar av modellen fortfarande är tunna.", "- 0 hexagons lack total signal in the weight column. They remain in the geography but show that some parts of the model are still thin."),
        ("- Den nuvarande viktlogiken blandar ytor, linjelängder och punktvärden i samma `total`, vilket kan ge slagsida redan före faktoranalysen.", "- The current weighting logic mixes areas, line lengths, and point values in the same `total`, which can introduce bias even before the factor analysis."),
        ("- De fem faktorerna förklarar cirka 37.3% av totalvariansen. Det är användbart men innebär att rapporten fortfarande är en förenkling av verkligheten.", "- The five factors explain about 37.3% of the total variance. This is useful, but it means that the report is still a simplification of reality."),
        ("- Flera lager är skydds- eller restriktionslager snarare än direkta landskapsprocesser. De är viktiga för planeringsrelevans, men kräver försiktig tolkning i den rena landskapstypologin.", "- Several layers are protection or restriction layers rather than direct landscape processes. They are important for planning relevance, but require careful interpretation in the pure landscape typology."),
        ("## 5. Resultat: faktorernas landskapsgradienter", "## 5. Results: Landscape Gradients of the Factors"),
        (
            "Tabellen ovan är den enklaste vägen in i faktorresultatet. Om en läsare bara ska ta med sig en sak från faktorsteget är det att varje faktor får sin mening av **vilka signaler som drar åt samma håll över flera skalor**, inte av ett enda kartlager.",
            "The table above is the simplest way into the factor result. If a reader takes only one thing from the factor step, it should be that each factor gets its meaning from **which signals pull in the same direction across several scales**, not from a single map layer.",
        ),
        (
            "Den sakliga tolkningen av faktorerna ska i första hand styras av deras starkaste och mest sammanhängande laddningar. Tabellen nedan visar därför de `6` största absoluta laddningarna per faktor och är den primära läsnyckeln till faktorernas innehåll.",
            "The factual interpretation of the factors should primarily be guided by their strongest and most coherent loadings. The table below therefore shows the `6` largest absolute loadings per factor and is the primary reading key to the content of the factors.",
        ),
        (
            "Den kompletta laddningsmatrisen finns kvar som diagnostik och rimlighetskontroll, men den ska inte vara rapportens huvudsakliga tolkningsyta. Den lasbara huvudytan for hela matrisen finns nu som filtrerbar Excel-fil.",
            "The complete loading matrix remains available for diagnostics and plausibility checks, but it should not be the report's main interpretive surface. The readable main surface for the whole matrix is now available as a filterable Excel file.",
        ),
        (
            "**Vad som är viktigast i faktorsteget:** modellen skiljer nu tydligt mellan minst fem olika logiker i Bornholms landskap: låglänta sandkuster, brant relief och dalinslag, skogligt skyddsinland med habitatkärnor, bosättning och byggd struktur samt marina sand- och gruskuster. Ingen faktor är ensam en landskapstyp, men tillsammans beskriver de vad som återkommer på ön som stabila gradienter.",
            "**What matters most in the factor step:** the model now clearly distinguishes between at least five different logics in Bornholm's landscape: low-lying sandy coasts, steep relief and valley features, forested protected inland with habitat cores, settlement and built structure, and marine sand and gravel coasts. No single factor is a landscape type on its own, but together they describe what recurs on the island as stable gradients.",
        ),
        ("## 6. Resultat: preliminära landskapstyper", "## 6. Results: Preliminary Landscape Types"),
        (
            "Klustren är rapportens mest konkreta resultat. För en läsare utan förkunskaper är det därför ofta bäst att börja här: ett kluster är helt enkelt en grupp hexagoner som liknar varandra i faktorprofil och därför kan tolkas som en preliminär landskapstyp.",
            "The clusters are the report's most concrete result. For a reader without prior knowledge, it is therefore often best to start here: a cluster is simply a group of hexagons that resemble each other in factor profile and can therefore be interpreted as a preliminary landscape type.",
        ),
        (
            "I tabellen ovan betyder positiva värden att klustret har mer av en viss faktor än ö-genomsnittet, medan negativa värden betyder att faktorn är svagare där än i Bornholms typiska bakgrundslandskap. Man ska därför inte läsa siffrorna som absoluta mängder, utan som riktning och styrka i relation till resten av ön.",
            "In the table above, positive values mean that the cluster has more of a given factor than the island average, while negative values mean that the factor is weaker there than in Bornholm's typical background landscape. The numbers should therefore not be read as absolute quantities, but as direction and strength in relation to the rest of the island.",
        ),
        (
            "I denna analys väljs `K = r k_best`. Det viktigaste med det valet är att lösningen ger flera tydligt olika typer utan att splittra resultatet i många små restkluster. Samtidigt visar fördelningen att kluster `2` fungerar som öns breda vardagsmatris, medan övriga kluster fångar mer specialiserade bosättnings-, låglandskust-, brant terräng- och skogliga naturmönster.",
            "In this analysis, `K = 5` is selected. The most important point about that choice is that the solution gives several clearly different types without splitting the result into many small residual clusters. At the same time, the distribution shows that cluster `2` functions as the island's broad everyday matrix, while the other clusters capture more specialized settlement, lowland-coast, steep-terrain, and forested nature patterns.",
        ),
        ("## 7. Tolkning, osäkerheter och begränsningar", "## 7. Interpretation, Uncertainties, and Limitations"),
        (
            "Den här analysen kan beskrivas som en **mogen arbetsmodell**. Den är tillräckligt bred och sammanhängande för att ge en meningsfull typologi av Bornholm, men den kräver fortfarande slutlig validering och viss komplettering innan den bör behandlas som helt stabil referensmodell.",
            "This analysis can be described as a **mature working model**. It is broad and coherent enough to provide a meaningful typology of Bornholm, but it still requires final validation and some supplementation before it should be treated as a fully stable reference model.",
        ),
        ("Det starkaste i nuläget är att modellen kan skilja mellan flera olika landskapssammanhang som också är begripliga i kartan:", "The strongest point at present is that the model can distinguish between several different landscape contexts that are also legible on the map:"),
        ("- flygsands- och låglänta kuststråk", "- aeolian-sand and low-lying coastal corridors"),
        ("- bosättnings- och bebyggelsestrukturer med olika täthet", "- settlement and built structures with different densities"),
        ("- skogligt skyddsinland med habitatkärnor", "- forested protected inland with habitat cores"),
        ("- branta och dalpräglade inlandsmiljöer", "- steep and valley-shaped inland environments"),
        ("- marina sand- och gruspräglade kustsedimentmiljöer", "- coastal sediment environments characterized by marine sand and gravel"),
        ("De viktigaste kvarvarande osäkerheterna är däremot fortfarande tydliga:", "The most important remaining uncertainties are still clear:"),
        ("- viktkolumnen i kontextsteget blandar flera måttenheter och kan därför påverka grannskap och faktorstruktur", "- the weight column in the context step mixes several units of measurement and may therefore affect neighbourhoods and factor structure"),
        ("- pseudo-DEM:en är härledd från höjdkurvor, inte från en fullständig laserbaserad höjdmodell", "- the pseudo-DEM is derived from contour lines, not from a complete laser-based elevation model"),
        ("- vissa ännu ej använda underkategorier, energilager och bevarandelager kan förändra delar av bilden", "- some as-yet unused subcategories, energy layers, and preservation layers may change parts of the picture"),
        ("- skydds- och restriktionslager bidrar till planeringsrelevans men är inte alltid samma sak som egen landskapsprocess", "- protection and restriction layers contribute to planning relevance but are not always the same thing as an independent landscape process"),
        ("- faktor- och klusternamn är fortfarande tolkningar och bör ses som arbetsnamn tills de har verklighetskontrollerats mot kartor och Bornholmskännedom", "- factor and cluster names are still interpretations and should be regarded as working names until they have been ground-truthed against maps and local knowledge of Bornholm"),
        ("Rapporten bör därför användas som:", "The report should therefore be used as:"),
        ("- en transparent beskrivning av Bornholms landskapstyper i flera skalor", "- a transparent description of Bornholm's landscape types at several scales"),
        ("- ett arbetsunderlag för fortsatt expertgranskning, karttolkning och typologisk namnsättning", "- a working basis for continued expert review, map interpretation, and typological naming"),
        ("- en möjlig grund för senare acceptans- eller känslighetsbedömningar", "- a possible basis for later acceptance or sensitivity assessments"),
        ("Rapporten bör ännu inte användas som ensam beslutsgrund för lokalisering, tillstånd eller slutlig värdering av enskilda platser.", "The report should not yet be used as the sole decision basis for siting, permits, or final valuation of individual places."),
        ("## 8. Typologisk tolkning och nästa steg", "## 8. Typological Interpretation and Next Steps"),
        (
            "Som tolkningsram är två referenser särskilt viktiga för denna rapport. Den första är Juta Kawalerowicz och Bo Malmbergs multiskalära typologitänkande ([Multiscalar Typology of Residential Areas in Sweden](https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826)): platser ska beskrivas både av sina lokala egenskaper och av sin omgivning på flera skalor. Här används det som en **metodisk anpassning**, inte som en direkt kopia av deras bostadstypologi. Den andra är den befintliga Bornholmsanalysen i [Landskapstyper Bornholm (PDF)](https://github.com/gislab-se/landskapsanalys/blob/main/data/Landskapstyper%20Bornholm.pdf), som fungerar som verklighetskontroll för hur översiktliga landskapsrum faktiskt brukar beskrivas på ön.",
            "Two references are particularly important as an interpretive frame for this report. The first is Juta Kawalerowicz and Bo Malmberg's multiscalar typology thinking ([Multiscalar Typology of Residential Areas in Sweden](https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826)): places should be described both by their local properties and by their surroundings at several scales. Here it is used as a **methodological adaptation**, not as a direct copy of their residential typology. The second is the existing Bornholm analysis in [Landscape Types Bornholm (PDF)](https://github.com/gislab-se/landskapsanalys/blob/main/data/Landskapstyper%20Bornholm.pdf), which functions as a reality check for how broad landscape areas are usually described on the island.",
        ),
        (
            "Det viktiga är inte att denna modell ska kopiera någon tidigare typologi exakt. Det viktiga är att den ska återge huvuddragen i Bornholms landskap på ett sätt som är både statistiskt hållbart och geografiskt begripligt. Om låglänta sandkuster, skogligt skyddsinland, brant dalpräglat inland, vardagslandskap och bebyggda kärnor går att läsa tydligt i samma modell, då är typologin på väg att gå i mål.",
            "The important point is not that this model should copy any previous typology exactly. The important point is that it should reproduce the main features of Bornholm's landscape in a way that is both statistically robust and geographically understandable. If low-lying sandy coasts, forested protected inland, steep valley-shaped inland, everyday landscapes, and built cores can be read clearly in the same model, then the typology is close to completion.",
        ),
        ("Nästa steg är därför både validerande och metodiskt riktade:", "The next steps are therefore both validating and methodologically targeted:"),
        ("1. kontrollera att faktor- och klusternamn stämmer med kartornas faktiska geografi", "1. check that factor and cluster names match the actual geography of the maps"),
        ("2. pröva om jordbruksplatå och sprickdalsmönster blir tydligare med fler konturhärledda derivat eller med verklig DEM", "2. test whether agricultural plateau and fracture-valley patterns become clearer with more contour-derived derivatives or with a real DEM"),
        ("3. jämföra huvudmönstren mot Bornholms befintliga landskapstypologi och lokal kunskap", "3. compare the main patterns with Bornholm's existing landscape typology and local knowledge"),
        ("4. därefter låsa en stabil referensmodell för fortsatt planeringsanvändning", "4. then lock a stable reference model for continued planning use"),
        (
            "Det betyder att rapporten nu bör läsas som en nästan färdig landskapstypologi: tillräckligt utvecklad för att diskuteras som huvudmodell, men fortfarande öppen för en sista omgång tolkning, kalibrering och expertkontroll.",
            "This means that the report should now be read as an almost finished landscape typology: sufficiently developed to be discussed as the main model, but still open to a final round of interpretation, calibration, and expert review.",
        ),
        ("## Utdata från analysen", "## Analysis Outputs"),
        (
            "Rapporten bygger på ett sammanhållet analysunderlag som innehåller lagerdata, factorscores, klusterprofiler och hexagonlager för kartor och tolkning.",
            "The report is based on a coherent analytical dataset that contains layer data, factor scores, cluster profiles, and hexagon layers for maps and interpretation.",
        ),
        ("Till analysen hör bland annat följande utdata:", "The analysis includes, among other things, the following outputs:"),
        ("- punkt- och kontextdata per hexagon", "- point and context data per hexagon"),
        ("- factorscores per hexagon", "- factor scores per hexagon"),
        ("- faktorladdningar och klusterprofiler", "- factor loadings and cluster profiles"),
        ("- hexagonlager för kartor och tolkning", "- hexagon layers for maps and interpretation"),
        ("## Referenser", "## References"),
        ("*Landskapstyper Bornholm (PDF)*", "*Landscape Types Bornholm (PDF)*"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    term_replacements = [
        ("|aspekt                          |varde    |", "|Aspect                         |Value    |"),
        ("|Studieområde                    |Bornholm |", "|Study area                     |Bornholm |"),
        ("|Grundupplösning                 |R9-hex   |", "|Base resolution                |R9 hex   |"),
        ("|Antal analyshexagoner           |7,286    |", "|Number of analysis hexagons    |7,286    |"),
        ("|Exkluderade havshex utan signal |605      |", "|Excluded sea hexagons without signal |605 |"),
        ("|Antal ingångslager              |68       |", "|Number of input layers         |68       |"),
        ("|Antal kontextvariabler          |680      |", "|Number of context variables    |680      |"),
        ("|Valt klusterantal               |5        |", "|Selected number of clusters    |5        |"),
        ("|Hex utan signal i totalvikten   |0 (0.0%) |", "|Hexagons without signal in total weight |0 (0.0%) |"),
        ("|Lager", "|Layer"),
        ("|Geometri", "|Geometry"),
        ("|Tema", "|Theme"),
        ("|Datakälla", "|Data source"),
        ("|Hexsignal", "|Hex signal"),
        ("Källdata i Bornholm geocontext-stack", "Source data in the Bornholm geocontext stack"),
        ("Andel av hexagonens yta", "Share of hexagon area"),
        ("Linjelängd inom hexagonen", "Line length within the hexagon"),
        ("Antal per hexagon", "Count per hexagon"),
        ("Sammanfattat terrängmått per hexagon", "Summary terrain metric per hexagon"),
        ("Härlett från höjdkurvor och terrängunderlag", "Derived from contours and terrain base data"),
        ("Andel av hex i reliefklass", "Share of hex in relief class"),
        ("Andel av hex i höjdklass", "Share of hex in elevation class"),
        ("Medelhöjd från konturhärledd pseudo-DEM", "Mean elevation from contour-derived pseudo-DEM"),
        ("Medellutning från konturhärledd pseudo-DEM", "Mean slope from contour-derived pseudo-DEM"),
        ("Lokalt max daldjup från konturhärledd pseudo-DEM", "Local maximum valley depth from contour-derived pseudo-DEM"),
        ("Proxy för hög jordbruksplatå", "Proxy for high agricultural plateau"),
        ("Markblokke 2026 (lokal jordbruksdata; ej i SL01-PDF)", "Markblokke 2026 (local agricultural data; not in the SL01 PDF)"),
        ("Danmarks Miljoportal / Miljostyrelsen", "Danmarks Miljoeportal / Miljoestyrelsen"),
        ("Moor and hede", "Moor and heath"),
        ("Strand protection", "Shore protection"),
        ("Marina sand och grus - ovrigt", "Marine sand and gravel - other"),
        ("Farskvatten och organiskt - ovrigt", "Freshwater and organic deposits - other"),
        ("Smaltvatten - ovrigt", "Meltwater - other"),
        ("Ovrigt anlagt eller okant", "Other artificial or unknown"),
        ("Hammer och Almindinge", "Hammer and Almindinge"),
        ("Vang och Svaneke Gran", "Vang and Svaneke Granite"),
        ("Sandsten och gronsand - ovrigt", "Sandstone and greensand - other"),
        ("Sedimentara formationer - ovrigt", "Sedimentary formations - other"),
        ("Skifrar - ovrigt", "Shales - other"),
        ("Kristallint - ovrigt", "Crystalline rocks - other"),
        ("Kalkbergarter - ovrigt", "Limestone rocks - other"),
        ("Ovrigt stratigrafiskt", "Other stratigraphic units"),
        ("| Antal lager|Exempel", "|Number of layers|Examples"),
        ("|Ej aktiv grupp", "|Inactive group"),
        ("Energiinfrastruktur", "Energy infrastructure"),
        ("Transformatorstationer", "Transformer substations"),
        ("Markkablar", "Underground cables"),
        ("Högspänningsledningar", "High-voltage lines"),
        ("Skyddade naturtyper: underkategorier", "Protected nature types: subcategories"),
        ("Vattendrag: underkategorier", "Watercourses: subcategories"),
        ("River okänd bredd", "River unknown width"),
        ("Vägar: ej använda varianter", "Roads: unused variants"),
        ("Vägar small", "Roads small"),
        ("Vägar other", "Roads other"),
        ("Vägar total", "Roads total"),
        ("Parentgeologi ersatt av underkategorier", "Parent geology replaced by subcategories"),
        ("Jordart parentlager", "Jordart parent layer"),
        ("Prekvart parentlager", "Prekvart parent layer"),
        ("Bevaringsvärda landskap", "Landscapes worthy of preservation"),
        ("Bevaringsvärdiga landskap", "Landscapes worthy of preservation"),
        ("Dubbel kulturmiljösignal", "Duplicate cultural-environment signal"),
        ("Kulturhistorisk bevaringsværdi vedtaget", "Adopted cultural-historical preservation value"),
        ("| Steg|Analyssteg", "| Step|Analysis step"),
        ("|Vad det betyder i praktiken", "|What it means in practice"),
        ("Aggregera rådata till hexagoner", "Aggregate raw data to hexagons"),
        ("Punkter, linjer och polygoner översätts till jämförbara signaler i samma R9-hexgrid.", "Points, lines, and polygons are translated into comparable signals in the same R9 hex grid."),
        ("Bygg multiskalig kontext", "Build multiscalar context"),
        ("Varje hexagon får inte bara sitt lokala värde utan också information om sin omgivning på flera skalor.", "Each hexagon receives not only its local value but also information about its surroundings at several scales."),
        ("Rensa och standardisera analysmatrisen", "Clean and standardize the analysis matrix"),
        ("Kolumner utan faktisk variation eller med tekniska problem tas bort så att modellen arbetar med meningsfull signal.", "Columns without actual variation or with technical problems are removed so the model works with meaningful signal."),
        ("Extrahera faktorer", "Extract factors"),
        ("Återkommande samvariationer mellan många lager komprimeras till ett mindre antal tydliga gradienter.", "Recurring co-variation among many layers is compressed into a smaller number of clear gradients."),
        ("Beräkna faktorscore per hexagon", "Calculate factor score per hexagon"),
        ("Varje hexagon får ett värde på varje faktor och kan därmed beskrivas i samma faktorrum som resten av ön.", "Each hexagon receives a value for each factor and can therefore be described in the same factor space as the rest of the island."),
        ("Gruppera hexagoner till preliminära landskapstyper", "Group hexagons into preliminary landscape types"),
        ("Hexagoner med liknande faktorprofiler samlas till kluster som tolkas som preliminära landskapstyper.", "Hexagons with similar factor profiles are gathered into clusters interpreted as preliminary landscape types."),
        ("|Metodsteg", "|Method step"),
        ("|Method step             |Val", "|Method step             |Choice"),
        ("Analysenheter", "Analysis units"),
        ("Hexagoner med raw_total > 0 behalls som analysenheter; rena havshex tas bort fore kontextmatris och faktoranalys.", "Hexagons with raw_total > 0 are kept as analysis units; pure sea hexagons are removed before the context matrix and factor analysis."),
        ("Kontextskalor", "Context scales"),
        ("Kontextvikt", "Context weighting"),
        ("Skallogik", "Scale logic"),
        ("kumulativ vikt, inte fasta hexringar", "cumulative weight, not fixed hex rings"),
        ("Kontextmått per lager", "Context metrics per layer"),
        ("mean och std", "mean and std"),
        ("Antal faktorer", "Number of factors"),
        ("Faktoranalys", "Factor analysis"),
        ("Faktorscore", "Factor score"),
        ("Klusterprövning", "Cluster testing"),
        ("Klusterval", "Cluster selection"),
        ("högst silhouette, nu K = 5", "highest silhouette, now K = 5"),
        ("|Metrik", "|Metric"),
        ("Andel av total varians", "Share of total variance"),
        ("Kumulativ andel av total varians", "Cumulative share of total variance"),
        ("Andel av forklarad varians", "Share of explained variance"),
        ("Kumulativ andel av forklarad varians", "Cumulative share of explained variance"),
        ("|Faktor |Aktuell tolkning", "|Factor |Current interpretation"),
        ("|Starkaste signaler", "|Strongest signals"),
        ("|Hur faktorn ska läsas", "|How the factor should be read"),
        ("Flygsands- och låglänta kustmiljöer", "Aeolian-sand and low-lying coastal environments"),
        ("Brant relief och sprickdalspräglad terräng", "Steep relief and fracture-valley terrain"),
        ("Skogligt skyddsinland och habitatkärnor", "Forested protected inland and habitat cores"),
        ("Bosättning och byggd struktur", "Settlement and built structure"),
        ("Marina sand- och gruskuster", "Marine sand and gravel coasts"),
        ("Domineras av flygsand, låga höjdband och låg konturhärledd medelhöjd över flera skalor. Faktorn fångar sandiga, låglänta kustmiljöer och skiljer dem från högre inlandslägen och platåsignaler på den negativa polen.", "Dominated by aeolian sand, low elevation bands, and low contour-derived mean elevation across several scales. The factor captures sandy, low-lying coastal environments and distinguishes them from higher inland locations and plateau signals on the negative pole."),
        ("Drivs mycket tydligt av konturhärledd lutning, relief och maximal lokal daldjupssignal. Faktorn beskriver ett brant, terrängkontrasterat och delvis sprickdalspräglat inland snarare än enbart allmän höjd.", "Very clearly driven by contour-derived slope, relief, and maximum local valley-depth signal. The factor describes a steep, terrain-contrasted, and partly fracture-valley-shaped inland rather than only general elevation."),
        ("Domineras av skog, fredskov och Natura-habitat- och fågelskydd på mellanstora och stora skalor och beskriver ett skogligt skyddsinland med tydliga habitatkärnor.", "Dominated by forest, fredskov, and Natura habitat and bird protection at medium and large scales, and describes a forested protected inland with clear habitat cores."),
        ("Drivs främst av fastboende, låg bebyggelse, centrumfunktioner, vägar och verksamhetsmark och beskriver öns bosättnings- och bebyggelsestruktur snarare än enbart tätorter.", "Driven mainly by permanent population, low buildings, centre functions, roads, and business land, and describes the island's settlement and built structure rather than only urban areas."),
        ("Kopplar marina sand- och grusavlagringar till låga kustsedimentära miljöer och beskriver särskilda kustbundna sedimentpaket snarare än hela den generella kustzonen.", "Links marine sand and gravel deposits to low coastal sedimentary environments and describes specific coast-bound sediment packages rather than the entire general coastal zone."),
        ("|factor", "|Factor"),
        ("|variabel", "|Variable"),
        ("(medel, k=", "(mean, k="),
        ("|  K| Silhouette|Beräkningsbas", "|  K| Silhouette|Computation base"),
        ("|Kluster", "|Cluster"),
        ("| Andel", "| Share"),
        ("|Dominerande faktor", "|Dominant factor"),
        ("|Nästa tydliga faktor", "|Next clear factor"),
        ("|Kort läsning", "|Brief reading"),
        ("|Tolkning", "|Interpretation"),
        ("Tätorts- och verksamhetskärnor", "Urban and business cores"),
        ("Vardagslandskap med blandad bakgrundskaraktär", "Everyday landscape with mixed background character"),
        ("Flygsands- och låglänta kuststråk", "Aeolian-sand and low-lying coastal corridors"),
        ("Brant relief och dalpräglat inland", "Steep relief and valley-shaped inland"),
        ("Mycket hög F4 visar öns tydligaste tätorts- och verksamhetskärnor, där byggd struktur, fastboende och tillgänglighet samlas starkare än övriga faktorer.", "Very high F4 shows the island's clearest urban and business cores, where built structure, permanent population, and accessibility are concentrated more strongly than the other factors."),
        ("Låga eller svagt negativa värden på de flesta faktorer visar öns breda bakgrundslandskap där flera signaler blandas utan stark specialisering i någon riktning.", "Low or slightly negative values for most factors show the island's broad background landscape, where several signals mix without strong specialization in any one direction."),
        ("Hög F1 och svag bosättnings- och skogssignal visar låglänta sand- och kuststråk där flygsand, låga höjder och kustnära lågland logiskt samverkar.", "High F1 and weak settlement and forest signals show low-lying sandy and coastal corridors where aeolian sand, low elevations, and coastal lowland logically interact."),
        ("Mycket hög F2 tillsammans med viss positiv F5-signal markerar öns branta, terrängkontrasterade och dalpräglade inlandslägen där konturhärledd lutning och daldjup gör störst skillnad.", "Very high F2 together with some positive F5 signal marks the island's steep, terrain-contrasted, and valley-shaped inland locations where contour-derived slope and valley depth make the greatest difference."),
        ("Mycket hög F3 markerar Bornholms tydligaste skogliga, habitatpräglade och skyddsinriktade inlandsmiljöer.", "Very high F3 marks Bornholm's clearest forested, habitat-influenced, and protection-oriented inland environments."),
    ]
    for old, new in term_replacements:
        text = text.replace(old, new)

    return text


def make_word_friendly(text: str) -> str:
    def clean_cell(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def split_row(row: str) -> list[str]:
        return [clean_cell(cell) for cell in row.strip().strip("|").split("|")]

    def table_to_sections(
        pattern: re.Pattern[str],
        replacement_heading: str,
        row_formatter,
        text_value: str,
    ) -> str:
        match = pattern.search(text_value)
        if not match:
            return text_value
        rows = [split_row(row) for row in match.group("rows").strip().splitlines()]
        replacement = "\n" + replacement_heading + "\n\n" + "\n\n".join(
            row_formatter(row) for row in rows
        ) + "\n\n"
        return pattern.sub(replacement, text_value)

    method_table_pattern = re.compile(
        r"\n\|Method step\s+\|Choice.*?\n"
        r"\|:?-+.*?\n"
        r"\|Analysis units\s+\|(?P<analysis_units>.*?)\|\s*\n"
        r"\|Context scales\s+\|(?P<context_scales>.*?)\|\s*\n"
        r"\|Context weighting\s+\|(?P<context_weighting>.*?)\|\s*\n"
        r"\|Scale logic\s+\|(?P<scale_logic>.*?)\|\s*\n"
        r"\|Context metrics per layer\s+\|(?P<context_metrics>.*?)\|\s*\n"
        r"\|Number of factors\s+\|(?P<number_of_factors>.*?)\|\s*\n"
        r"\|Factor analysis\s+\|(?P<factor_analysis>.*?)\|\s*\n"
        r"\|Rotation\s+\|(?P<rotation>.*?)\|\s*\n"
        r"\|Factor score\s+\|(?P<factor_score>.*?)\|\s*\n"
        r"\|Cluster testing\s+\|(?P<cluster_testing>.*?)\|\s*\n"
        r"\|Cluster selection\s+\|(?P<cluster_selection>.*?)\|\s*\n",
        flags=re.S,
    )

    match = method_table_pattern.search(text)
    if match:
        rows = [
            ("Analysis units", "analysis_units"),
            ("Context scales", "context_scales"),
            ("Context weighting", "context_weighting"),
            ("Scale logic", "scale_logic"),
            ("Context metrics per layer", "context_metrics"),
            ("Number of factors", "number_of_factors"),
            ("Factor analysis", "factor_analysis"),
            ("Rotation", "rotation"),
            ("Factor score", "factor_score"),
            ("Cluster testing", "cluster_testing"),
            ("Cluster selection", "cluster_selection"),
        ]
        replacement = "\n### Method Choices\n\n" + "\n".join(
            f"- **{label}:** {clean_cell(match.group(key))}" for label, key in rows
        ) + "\n\n"
        text = method_table_pattern.sub(replacement, text)

    factor_table_pattern = re.compile(
        r"\n\|Factor\s+\|Current interpretation.*?\n"
        r"\|:?-+.*?\n"
        r"(?P<rows>(?:\|F[1-5]\s+\|.*?\|\s*\n)+)",
        flags=re.S,
    )

    def format_factor(row: list[str]) -> str:
        factor, interpretation, signals, reading = row[:4]
        return (
            f"#### {factor}: {interpretation}\n\n"
            f"- **Strongest signals:** {signals}\n"
            f"- **How to read the factor:** {reading}"
        )

    text = table_to_sections(
        factor_table_pattern,
        "### Factor Interpretations",
        format_factor,
        text,
    )

    cluster_summary_pattern = re.compile(
        r"\n\|Cluster\s+\|\s*Share\|Dominant factor.*?\n"
        r"\|:?-+.*?\n"
        r"(?P<rows>(?:\|[1-5] .*?\|\s*\n)+)",
        flags=re.S,
    )

    def format_cluster_summary(row: list[str]) -> str:
        cluster, share, dominant, next_factor, reading = row[:5]
        return (
            f"#### {cluster}\n\n"
            f"- **Share:** {share}\n"
            f"- **Dominant factor:** {dominant}\n"
            f"- **Next clear factor:** {next_factor}\n"
            f"- **Brief reading:** {reading}"
        )

    text = table_to_sections(
        cluster_summary_pattern,
        "### Cluster Readings",
        format_cluster_summary,
        text,
    )

    cluster_profile_pattern = re.compile(
        r"\n\|Cluster\s+\|\s*Share\|\s+F1\|\s+F2\|\s+F3\|\s+F4\|\s+F5\|Interpretation.*?\n"
        r"\|:?-+.*?\n"
        r"(?P<rows>(?:\|[1-5] .*?\|\s*\n)+)",
        flags=re.S,
    )

    def format_cluster_profile(row: list[str]) -> str:
        cluster, share, f1, f2, f3, f4, f5, interpretation = row[:8]
        return (
            f"#### {cluster}\n\n"
            f"- **Share:** {share}\n"
            f"- **Factor profile:** F1 {f1}; F2 {f2}; F3 {f3}; F4 {f4}; F5 {f5}\n"
            f"- **Interpretation:** {interpretation}"
        )

    text = table_to_sections(
        cluster_profile_pattern,
        "### Cluster Factor Profiles",
        format_cluster_profile,
        text,
    )

    return text


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    text = clean_quarto_wrappers(text)
    text = apply_replacements(text)
    text = make_word_friendly(text)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(TARGET)


if __name__ == "__main__":
    main()
