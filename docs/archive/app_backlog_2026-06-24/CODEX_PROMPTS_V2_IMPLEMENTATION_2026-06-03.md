# Codex implementation prompts for v2

Date: 2026-06-03

These prompts are saved for a future Codex agent working in `landskapsanalys-v2-multiregion`.

## 1. Small-scale rooftop solar

```text
Implement "Small-scale rooftop installation" in the v2 Bornholm potential app, based on the v1 logic but using v2's population squares instead of v1 population points.

First, inspect the v1 implementation in `potential_app.py`, especially:
- `_population_count_frame_for_resolution`
- `_solar_v1_frame`
- `_solar_v1_class`
- `_solar_v1_stats`
- `_combined_solar_hex_frame`
- the UI controls around "Smaskalig anlaggning pa tak" / "Panel area per person"

V1 logic summary:
- Small-scale rooftop solar is a schematic rooftop potential model, not actual roof polygons.
- Population is aggregated to the active H3 resolution.
- Formula: `small_rooftop_area_m2 = population * panel_area_m2_per_person`
- Default `panel_area_m2_per_person` is `10.0`.
- Area is converted to km2 with `/ 1_000_000`.
- Score is relative/log-scaled:
  `score = log1p(area_m2) / log1p(max_area_m2) * 100`
- Classes are based on area:
  - `0 m2`
  - `>0-25 m2`
  - `25-100 m2`
  - `100-250 m2`
  - `250-1 000 m2`
  - `>1 000 m2`
- The map should show the result as small/yellow schematic hexes or square-derived schematic features, clearly labelled as a schematic rooftop estimate, not as actual roof polygons or continuous land area.
- Stats should include total small-scale rooftop area, covered solar area need, remaining solar area need, covered TWh if the energy model is active, and total population used.
- In the combined solar model, small-scale rooftop area should be added before large-scale land solar, clipped to the hex/cell area where needed. The UI/narrative should make clear that solar allocation is handled first from rooftop potential, then from large-scale land potential.

Important v2 adaptation:
- V1 uses population points/H3 population counts. V2 uses population squares.
- Do not assume point geometry or a point-buffer workflow for the small-scale rooftop area calculation.
- Find the v2 population square layer/source and identify the population count column.
- Aggregate population squares into the v2 analysis/display grid. If the app uses H3, intersect/area-weight or otherwise aggregate square population into H3 cells. If the app uses another grid, aggregate to that grid consistently with existing v2 patterns.
- Preserve total population as much as possible when converting from squares to the app grid.
- If population squares are finer than the display grid, sum them into each grid cell.
- If population squares are coarser than the display grid, distribute population by square/grid intersection area, not evenly by child count unless that is already the established v2 pattern.

UI requirements:
- Add/port the "Small-scale rooftop installation" group under Landscape Potential Solar.
- Include a checkbox for the v2 population squares source.
- Include the "Panel area per person" slider, default `10.0`, range roughly `0-25 m2/person`.
- Use wording such as "Population squares" instead of "Population points".
- Include help text explaining: "Schematic rooftop solar: population per grid cell x m2 panel area per person."
- Keep the v1 Swedish/English naming style if v2 uses the same translation system.

Validation:
- Add or update tests for:
  - population-square aggregation preserves total population
  - `area_m2 = population * panel_area_m2_per_person`
  - score is `0` when all areas are zero
  - score reaches `100` for the max area cell
  - class thresholds match v1
  - combined solar area includes small-scale rooftop area before/with large-scale solar
- Run the relevant app/unit tests and report what changed.

Do not implement actual roof detection. This feature is explicitly a population-based schematic estimate of rooftop solar potential.
```

## 2. Deepest hole / etableringshex

```text
Revise the v2 "deepest hole" / etableringshex logic.

Correct goal:
The landscape is a continuous basin. The deepest holes fill first, meaning the most suitable places are selected first. When the scenario demands more wind or solar than the best areas can hold, the water flows outward into less suitable areas. Eventually the whole on-land/regional analysis area can be filled before any remaining shortage is represented by schematic polygons at sea.

Important correction:
Do not treat restrictions as absolute walls by default. Restrictions, distance to settlement, protected/cultural layers, roads, grid proximity, etc. should affect the suitability score unless the app explicitly marks a layer as legally impossible/outside analysis. A restricted or sensitive hex can still be filled if scenario demand is large enough and all better places are already filled.

Visual goal:
- Wind allocation fills hexes in blue.
- Solar allocation fills hexes in yellow.
- If both wind and solar allocate to the same hex, it becomes green.
- Red should not be used as a scenario-fill color.
- Schematic sea polygons should only represent remaining demand after all relevant land/regional hexes have been exhausted.

Implementation concept:
1. Build separate continuous suitability/depth scores for wind and solar.
2. Start allocation at the highest score.
3. Continue outward/downward through lower scores until the scenario area demand is met.
4. If all land/regional hexes are filled and demand still remains, allocate the remainder to schematic sea/off-map polygons.
5. Preserve explanatory columns such as:
   - `allocation_priority_score`
   - `technical_priority_score`
   - `landscape_priority_score`
   - `infrastructure_priority_score`
   - `restriction_penalty_score`
   - `social_acceptance_priority_score`
   - `allocation_priority_reason`

Layer interpretation:
- Electrical infrastructure proximity: higher priority when nearer, within reasonable distance.
- Settlement/population: lower priority when too close, but not automatically impossible unless explicitly configured.
- Protected nature/culture/reindeer/coastal/land-use layers: penalties or reduced suitability by default.
- Existing wind/solar potential scores remain important base components.
- Large contiguous areas and high usable-area share should rank higher.

Tests:
- Lower-scored/restricted cells are selected only after higher-scored cells.
- Scenario allocation can continue into restricted/penalized cells when demand exceeds preferred areas.
- Red cells are not used as scenario allocation fill.
- Sea schematic polygons are used only after all eligible land/regional hexes are exhausted.
- Green appears only where wind and solar actually overlap.
```
