# Förbättringsförslag: interaktiva härledningsfilter i Potential App

## Bakgrund

I högra panelen finns härledningar för till exempel landskapstyper, landskapsstrukturer och landskapsfaktorer. De visar hur stor del av en potential som ligger i olika landskapliga kategorier.

Ett användarbehov är att kunna exkludera vissa härledda delar direkt från beräkning och karta. Exempel: om 4,4 % av solpotentialen ligger i "Klippigt kustlandskap" och användaren inte vill planera solpaneler i den landskapstypen, ska raden kunna avmarkeras.

## Förslag

Lägg till en checkbox eller inkluderingskolumn per rad i härledningstabellerna.

Om en rad avmarkeras ska motsvarande yta tas bort från:

- potentialunderlaget
- kartvisualiseringen
- etableringsytan
- energimodellens summeringar
- tabellerna i högerpanelen
- beräkningen av potential efter filter, inom potential och ytbehov utanför potential

## Omfattning

Gör detta för:

- Landskapstyper
- Landskapsstrukturer
- Landskapsfaktorer/laddningar

## Krav

1. Lägg till en checkbox per rad i härledningstabellerna.
2. Alla rader ska vara inkluderade som default.
3. Checkbox-state ska sparas i session state.
4. Exkludering ska vara teknik-specifik.
5. Om en rad exkluderas under Landskapspotential Sol ska det påverka solpotentialen, men inte automatiskt vindpotentialen.
6. Samma princip ska gälla för vind.
7. Exkludering ska slå igenom i hela pipeline: potential_frame, karta, energimodell, högerpanel och härledningstabeller.
8. Kartans center och zoom ska bevaras när exkluderingar ändras.
9. Lägg till "Återställ exkluderingar" per potentiallager.

## Faktorhantering

För landskapsfaktorer/laddningar kan första versionen vara enkel:

- visa checkbox per faktor-rad
- avmarkering exkluderar hex där faktorn är starkt positiv eller negativ enligt härledningen
- UI-texten måste tydligt förklara vad exkluderingen betyder

En mer avancerad senare version kan ge intervallfilter per faktor, till exempel positiva, negativa eller extrema laddningar.

## UI-text

Föreslagen hjälptext ovanför härledningstabellerna:

> Avmarkera rader för att ta bort motsvarande ytor från potential och scenario.

Visa gärna också:

- antal aktiva exkluderingar
- borttagen km²
- vilken teknik exkluderingen gäller

## Acceptanskriterier

- Användaren kan avmarkera till exempel "Klippigt kustlandskap" i Landskapspotential Sol.
- Solpotentialen i den landskapstypen försvinner från kartan.
- Solens potential efter filter och etableringsberäkningar räknas om.
- Vind påverkas inte av solens exkludering.
- Härledningstabellerna visar uppdaterade värden efter exkludering.
- Det finns en tydlig reset för exkluderingar.
