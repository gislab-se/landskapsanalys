# NEXT SESSION QUICKSTART

## Open These First
1. `SESSION_HANDOFF.md`
2. `docs/geocontext/landskapsanalys.qmd`
3. `script/landskapsanalys/02_build_bornholm_r9_landskapsanalys_9lager_res9.R`

## Current Baseline
- Active model: `landskapsanalys_9lager_res9`
- Archived bridge model: `landskapsanalys_gc4_res9`
- Hex resolution: `R9`
- Current chosen cluster count: `K = 8`

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

## Rerun Commands
```powershell
cd C:\gislab\landskapsanalys
Rscript script\landskapsanalys\02_build_bornholm_r9_landskapsanalys_9lager_res9.R
quarto render docs\geocontext\landskapsanalys.qmd
```

## Main Outputs
- Report source:
  - `docs/geocontext/landskapsanalys.qmd`
- Rendered report:
  - `docs/geocontext/landskapsanalys.html`
- Standalone interactive maps:
  - `docs/geocontext/maps/landskapsanalys_9lager_res9_cluster_map.html`
  - `docs/geocontext/maps/landskapsanalys_9lager_res9_factor_mapview.html`
- Versioned run output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_9lager_res9/`

## What To Do Next
1. Use the 9-layer run as the baseline.
2. Run a sensitivity test with and without:
   - `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32`
3. Compare:
   - factor loadings
   - factor interpretability
   - cluster geography
   - whether the planning layer enriches the model or pre-codes the answer
4. After that, prepare two parallel experiments:
   - `naturgeografisk`
   - `kulturgeografisk`

## Key Interpretation Reminders
- Equal factor-score standard deviations are expected because the factor-score columns are normalized.
- Use `SS loadings` and `Proportion Var` to judge factor importance.
- Silhouette measures separation in factor space, not geographic distance on the map.
- Step 27 is the cultural-historical layer to keep; step 15 is the duplicate to exclude from factor input.
