# NEXT SESSION QUICKSTART

## Open These First
1. `SESSION_HANDOFF.md`
2. `docs/geocontext/landskapsanalys.qmd`
3. `script/landskapsanalys/04_build_bornholm_r9_landskapsanalys_26lager_res9.R`

## Current Baseline
- Active model: `landskapsanalys_26lager_res9`
- Previous baseline: `landskapsanalys_17lager_res9`
- Earlier baseline: `landskapsanalys_9lager_res9`
- Archived bridge model: `landskapsanalys_gc4_res9`
- Hex resolution: `R9`
- Current chosen cluster count: `K = 8`
- Sea hex without any selected signal are now excluded before context modeling and factor analysis
- Current context scales `10, 50, 100, 250, 1000` are weighted thresholds, not fixed hex-ring counts

## Current Input Layers
1. permanent population
2. roads medium
3. roads large
4. ecological connectivity
5. cultural-historical conservation
6. fredskov
7. agricultural land / Markblokke
8. relief
9. protected watercourses
10. lake
11. wetland
12. moor / hede
13. forest
14. coastal zone
15. coastline
16. valuable cultural environment
17. highest contour value
18. river
19. sand dune
20. protected nature types
21. mapped nature types
22. industry and business land
23. built centre
24. buildings high
25. buildings low
26. strand protection

## Rerun Commands
```powershell
cd C:\gislab\landskapsanalys
Rscript script\landskapsanalys\04_build_bornholm_r9_landskapsanalys_26lager_res9.R
quarto render docs\geocontext\landskapsanalys.qmd
```

## Main Outputs
- Report source:
  - `docs/geocontext/landskapsanalys.qmd`
- Rendered report:
  - `docs/geocontext/landskapsanalys.html`
- Standalone interactive maps:
  - `docs/geocontext/maps/landskapsanalys_26lager_res9_cluster_map.html`
  - `docs/geocontext/maps/landskapsanalys_26lager_res9_factor_mapview.html`
- Versioned run output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_26lager_res9/`

## What To Do Next
1. Use the 26-layer run as the active landscape-character baseline, but treat the current context weighting as provisional.
2. Test the geometry-mixing weakness explicitly:
   - run one model for polygon layers only
   - run one model for line layers only
   - run one model for point / point-aggregated layers only
   - compare factor stability, cluster geography and similarity to known Bornholm landscape structure
3. Compare the current model against:
   - `landskapsanalys_17lager_res9`
   - `landskapsanalys_9lager_res9`
   - `data/Landskapstyper Bornholm.pdf`
4. Check whether the new factors and clusters actually match Bornholm's known coast, inland forest, mosaic and agricultural structures.
5. After that, run the planned sensitivity test with and without:
   - `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32`

## Key Interpretation Reminders
- Equal factor-score standard deviations are expected because the factor-score columns are normalized.
- Use `SS loadings` and `Proportion Var` to judge factor importance.
- Silhouette measures separation in factor space, not geographic distance on the map.
- Step 27 is the cultural-historical layer to keep; step 15 is the duplicate to exclude from factor input.
