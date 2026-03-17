# NEXT SESSION QUICKSTART

## Open These First
1. `docs/geocontext/GC4_TO_R9_FACTOR_MIGRATION.md`
2. `docs/geocontext/landskapsanalys.qmd`
3. `script/landskapsanalys/07_build_bornholm_r9_landskapsanalys_58lager_geologi_restriktioner_res9.R`

## Current Baseline
- Active model: `landskapsanalys_58lager_geologi_restriktioner_res9`
- Previous staged step: `landskapsanalys_47lager_geologi_res9`
- Saved comparison baseline: `landskapsanalys_26lager_res9`
- Archived bridge model: `landskapsanalys_gc4_res9`
- Hex resolution: `R9`
- Current chosen cluster count: `K = 5`
- Sea hex without any selected signal are now excluded before context modeling and factor analysis
- Current context scales `10, 50, 100, 250, 1000` are weighted thresholds, not fixed hex-ring counts

## Current Input Layers
- 26 baseline layers from the previous active model
- 21 geology subtype layers
  - 10 from `Jordart 1:25 000 v7.1`
  - 11 from `Prekvart Bornholm`
- 11 added protection, restriction and settlement-selection layers
  - protected/nature candidates
  - other infrastructure/restriction layers
  - `built_low_gd_v_buildings_low_selection_by_bol_33`

## Rerun Commands
```powershell
cd C:\gislab\landskapsanalys
Rscript script\landskapsanalys\07_build_bornholm_r9_landskapsanalys_58lager_geologi_restriktioner_res9.R
quarto render docs\geocontext\landskapsanalys.qmd
```

## Main Outputs
- Report source:
  - `docs/geocontext/landskapsanalys.qmd`
- Rendered report:
  - `docs/geocontext/landskapsanalys.html`
- Standalone interactive maps:
  - `docs/geocontext/maps/landskapsanalys_58lager_geologi_restriktioner_res9_cluster_map.html`
  - `docs/geocontext/maps/landskapsanalys_58lager_geologi_restriktioner_res9_factor_mapview.html`
- Versioned run output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_58lager_geologi_restriktioner_res9/`

## Available Comparison Runs
1. `script/landskapsanalys/06_build_bornholm_r9_landskapsanalys_47lager_geologi_res9.R`
   - 26-layer baseline + 21 geology subtype layers from Jordart and Prekvart
2. `script/landskapsanalys/07_build_bornholm_r9_landskapsanalys_58lager_geologi_restriktioner_res9.R`
   - step 1 above + protected/nature candidates + other infrastructure/restriction layers + built low selection

## Comparison Commands
```powershell
cd C:\gislab\landskapsanalys
Rscript script\landskapsanalys\06_build_bornholm_r9_landskapsanalys_47lager_geologi_res9.R
Rscript script\landskapsanalys\07_build_bornholm_r9_landskapsanalys_58lager_geologi_restriktioner_res9.R
quarto render docs\geocontext\landskapsanalys.qmd
```

## What To Do Next
1. Use the 58-layer run as the active landscape-character baseline.
2. Compare `landskapsanalys_58lager_geologi_restriktioner_res9` against `landskapsanalys_47lager_geologi_res9` to isolate what the protected-nature, restriction and built-low-selection layers changed.
3. Compare `landskapsanalys_47lager_geologi_res9` against `landskapsanalys_26lager_res9` to isolate what the geology subtype layers changed.
4. Check whether the new factors and clusters better match Bornholm's known coast, inland forest, mosaic and agricultural structures.
5. After that, run the planned sensitivity test with and without `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32` if it is still analytically relevant.

## Note For Next Time
- Find out where the main agricultural-land landscapes are in the active model.
- Find out where the crack-valley (`sprickdalslandskap`) landscapes are in the active model.

## Key Interpretation Reminders
- Equal factor-score standard deviations are expected because the factor-score columns are normalized.
- Use `SS loadings` and `Proportion Var` to judge factor importance.
- Silhouette measures separation in factor space, not geographic distance on the map.
- Step 27 is the cultural-historical layer to keep; step 15 is the duplicate to exclude from factor input.
