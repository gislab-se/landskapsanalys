# Future: What's Next

## Later Phase: Multi-Resolution H3 Landscape Typing
- Keep current focus on clean, semi-manual aggregation at H3 resolution 9 for all 37 layers.
- In a later phase, evaluate aggregation behavior between H3 resolutions (for example r8 <-> r9 <-> r10).
- Goal for later: derive landscape type decisions from cross-resolution consistency/stability, not from one fixed resolution only.
- Suggested later deliverables:
  - A reproducible comparison script for key indicators across neighboring resolutions.
  - Stability metrics per hex neighborhood (variance/rank drift across resolutions).
  - Rules for selecting final landscape type using both local (r9) and cross-resolution evidence.

## Model Improvement: Binary Potential Review And Area Reports

The next potential-model improvement should add a binary review mode on top of an already created potential layer.

### Prompt / spec

When a potential layer exists, add a button called `Skapa binär modell`.

The binary model should split the current potential result into:

- `Ja` = area where potential exists
- `Nej` = area where potential does not exist

### Visual logic

The purpose is to reveal the landscape context under the potential result.

The binary layer should therefore render like this:

- `Nej` as a dark mask, preferably black or dark gray
- `Ja` as transparent or nearly transparent

This should make it easy to place landscape layers underneath and inspect what lies inside the potential areas:

- landscape types
- landscape structures
- landscape factors

### Functional requirements

1. The button `Skapa binär modell` should operate on the currently active potential layer.
2. The binary model must be derived from the current potential result, not from a separate new model.
3. The binary model should appear as its own layer that can be toggled on and off.
4. It should work as an interpretation layer on top of the regular potential view.

### Next step after the binary layer

The next analytical step should be to convert contiguous `Ja` areas into selectable polygons.

Requirements:

1. Create one polygon per contiguous `Ja` area.
2. Give each polygon a unique ID.
3. Make it possible to select one area.
4. When an area is selected, show a summary and allow printing or exporting a report for that specific area.

### Report requirements

The report should be built from H3 resolution 10 for all underlying landscape context.

Use the R10 hexagons intersecting the selected `Ja` polygon to summarize:

- all landscape types present in the area
- all landscape structures present in the area
- all landscape factors present in the area

The report should aim to help a user understand what kind of landscape the selected potential area actually contains.

Suggested contents:

- selected area ID
- area size
- number of intersecting R10 hexagons
- dominant landscape type(s)
- dominant landscape structure(s)
- mean values for each landscape factor across the selected area
- a short interpretable summary text

### Narrative summary goal

The report should not only list raw values. It should also produce a readable synthesis, for example:

- `Detta område domineras av klippigt kustlandskap.`
- `Området har övervägande kuperad och sprickdalspräglad struktur.`
- `Faktorsammanfattningen tyder på ett relativt kuperat område med stark relief och begränsad låglandsprägel.`

The narrative summary can be based on average factor values and dominant shares, as long as the underlying statistics still remain visible in the report.

### Design intent

This feature should support a two-step interpretation workflow:

1. first identify where potential exists through a binary mask
2. then inspect and report what landscape character exists inside each potential area

