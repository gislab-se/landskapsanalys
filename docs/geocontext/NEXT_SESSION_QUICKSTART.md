# NEXT SESSION QUICKSTART

## New Direction (2026-03-18)
- Read `docs/geocontext/LANDSCAPE_CHARACTER_MODEL_MEMO_2026-03-18.md` first.
- Current decision: do not build acceptance layers yet.
- First split the workflow in two: a cleaned landscape-character model and a separate staged acceptance framework for later.
- Immediate priority: improve the landscape analysis baseline.
- All new work should use the `v2` track, with `v2.1` as the active method-improvement run.
- Keep `res9` as the frozen `v2` baseline until context weighting and factor robustness have been retested.
- Treat `res10` as a planned sensitivity test, not as the new default yet.

## Report Folders
- Active working report folder: `docs/geocontext/current_landscape_model/`
- Comparison and sensitivity folder: `docs/geocontext/model_comparisons/`
- Older legacy report folder: `docs/geocontext/legacy_reports/`

## Open These First
1. `docs/geocontext/GC4_TO_R9_FACTOR_MIGRATION.md`
2. `docs/geocontext/current_landscape_model/landskapsanalys_v2_1.qmd`
3. `docs/geocontext/model_comparisons/landskapsanalys_v2_1_sensitivity.html`
4. `docs/geocontext/model_comparisons/landskapsanalys_v2_1_factor_count_sensitivity.html`
5. `docs/geocontext/model_comparisons/landskapsanalys_v2_1_scale_sensitivity.html`
6. `script/landskapsanalys/09_build_bornholm_r9_landskapsanalys_v2_1_geomweight58_res9.R`

## Current Baseline
- Active frozen comparison baseline: `landskapsanalys_58lager_geologi_restriktioner_res9`
- Frozen `v2` baseline: `landskapsanalys_v2_baseline58_res9`
- Active `v2.1` run: `landskapsanalys_v2_1_geomweight58_res9`
- Previous staged step: `landskapsanalys_47lager_geologi_res9`
- Saved comparison baseline: `landskapsanalys_26lager_res9`
- Archived bridge model: `landskapsanalys_gc4_res9`
- Hex resolution: `R9`
- Current chosen cluster count in frozen baseline: `K = 5`
- Current chosen cluster count in active `v2.1`: `K = 6`
- Sea hex without any selected signal are now excluded before context modeling and factor analysis
- Sea-adjacent hex can still remain if they carry non-zero coastal or marine signal such as coastline, coastal zone, ferry routes, or other active layers
- Current context scales `10, 50, 100, 250, 1000` are weighted thresholds, not fixed hex-ring counts

## Current v2.1 Result Snapshot
- Weight logic: `geometry_balanced_q99` with `n_input_layers` rescaling
- Zero-radius share improved sharply:
  - `k10`: `93.97% -> 17.90%`
  - `k50`: `89.98% -> 0.00%`
  - `k100`: `83.04% -> 0.00%`
  - `k250`: `64.97% -> 0.00%`
  - `k1000`: `10.02% -> 0.00%`
- Cumulative explained variance increased:
  - `19.78% -> 36.02%`
- Clustering changed materially:
  - `K_BEST: 5 -> 6`
  - silhouette: `0.422 -> 0.312`
  - largest cluster share: `59.8% -> 50.9%`
- Interpretation:
  - neighborhood context is much less self-collapsed
  - factor structure is stronger
  - cluster compactness is lower, so `K=5` vs `K=6` and rotation choice must now be retested explicitly

## Current Sensitivity Result Snapshot
- Source report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_sensitivity.html`
- Source script:
  - `script/landskapsanalys/10_analyze_bornholm_r9_landskapsanalys_v2_1_factor_cluster_sensitivity.R`
- Rotation finding:
  - matched factor congruence between `varimax` and `oblimin`: `0.97-0.99`
  - highest absolute oblimin factor correlation: `0.163`
  - working read: oblimin does not yet force a rotation change
- K finding:
  - `varimax` prefers `K=6` with silhouette `0.312`
  - `oblimin` prefers `K=5` with silhouette `0.330`
  - `K=6` is much more stable across rotations: `ARI = 0.864`
  - `K=5` is less stable across rotations: `ARI = 0.582`
- Working decision:
  - keep `varimax` as report default for now
  - use `K=6` as working map-review default
  - keep `K=5` alive as a live challenger, not a discarded option

## Current Factor-Count Result Snapshot
- Source report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_factor_count_sensitivity.html`
- Source script:
  - `script/landskapsanalys/11_analyze_bornholm_r9_landskapsanalys_v2_1_factor_count_sensitivity.R`
- Tested factor counts:
  - `4, 5, 6, 7, 8`
- Main trade-off:
  - `4` factors gives best clustering: silhouette `0.379` with best `K=5`
  - `5` factors gives stronger structural split and best `K=6` with silhouette `0.311`
  - `6-8` factors improve FA fit but weaken clustering and introduce narrower, less clean factors
- Fit direction:
  - cumulative variance: `32.1% -> 44.3%` from `4` to `8`
  - TLI: `0.765 -> 0.875`
  - RMSEA: `0.131 -> 0.096`
- Working decision:
  - keep `5` factors as working default
  - keep `K=6` as working map-review default
  - treat `4` factors as the main simplification challenger
  - do not move to `6+` factors yet

## Current Scale Result Snapshot
- Source report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_scale_sensitivity.html`
- Source script:
  - `script/landskapsanalys/12_run_bornholm_r9_landskapsanalys_v2_1_scale_sensitivity.R`
- Tested scale families:
  - legacy: `10, 50, 100, 250, 1000`
  - local geometric: `8, 24, 72, 216, 648`
  - broad geometric: `15, 45, 135, 405, 1215`
- Main trade-off:
  - local geometric gives best silhouette: `0.348`, but makes the first scale much more self-local (`45.1%` zero radius)
  - broad geometric gives highest explained variance: `37.76%`, but weakens clustering and shifts best `K` back to `5`
  - legacy remains the most even compromise: `36.02%` variance, silhouette `0.312`, best `K = 6`
- Working decision:
  - keep `10, 50, 100, 250, 1000` as the current working scale family
  - treat the local geometric family as the main future challenger if we later want more local contrast

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
Rscript script\landskapsanalys\09_build_bornholm_r9_landskapsanalys_v2_1_geomweight58_res9.R
Rscript script\landskapsanalys\10_analyze_bornholm_r9_landskapsanalys_v2_1_factor_cluster_sensitivity.R
Rscript script\landskapsanalys\11_analyze_bornholm_r9_landskapsanalys_v2_1_factor_count_sensitivity.R
Rscript script\landskapsanalys\12_run_bornholm_r9_landskapsanalys_v2_1_scale_sensitivity.R
quarto render docs\geocontext\current_landscape_model\landskapsanalys_v2_1.qmd
quarto render docs\geocontext\current_landscape_model\landskapsanalys_v2_1_light.qmd
quarto render docs\geocontext\model_comparisons\landskapsanalys_v2_1_sensitivity.qmd
quarto render docs\geocontext\model_comparisons\landskapsanalys_v2_1_factor_count_sensitivity.qmd
quarto render docs\geocontext\model_comparisons\landskapsanalys_v2_1_scale_sensitivity.qmd
```

## Main Outputs
- Report source:
  - `docs/geocontext/current_landscape_model/landskapsanalys_v2_1.qmd`
- Rendered report:
  - `docs/geocontext/current_landscape_model/landskapsanalys_v2_1.html`
- Lightweight report:
  - `docs/geocontext/current_landscape_model/landskapsanalys_v2_1_light.html`
- Sensitivity report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_sensitivity.html`
- Factor-count report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_factor_count_sensitivity.html`
- Scale-sensitivity report:
  - `docs/geocontext/model_comparisons/landskapsanalys_v2_1_scale_sensitivity.html`
- Standalone interactive maps:
  - `docs/geocontext/current_landscape_model/maps/landskapsanalys_v2_1_geomweight58_res9_cluster_map.html`
  - `docs/geocontext/current_landscape_model/maps/landskapsanalys_v2_1_geomweight58_res9_factor_mapview.html`
- Versioned run output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_v2_1_geomweight58_res9/`
- Sensitivity output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_v2_1_factor_cluster_sensitivity/`
- Factor-count output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_v2_1_factor_count_sensitivity/`
- Scale-sensitivity output:
  - `data/interim/landskapsanalys_versions/landskapsanalys_v2_1_scale_sensitivity/`

## Available Comparison Runs
1. `script/landskapsanalys/06_build_bornholm_r9_landskapsanalys_47lager_geologi_res9.R`
   - 26-layer baseline + 21 geology subtype layers from Jordart and Prekvart
2. `script/landskapsanalys/07_build_bornholm_r9_landskapsanalys_58lager_geologi_restriktioner_res9.R`
   - step 1 above + protected/nature candidates + other infrastructure/restriction layers + built low selection
3. `script/landskapsanalys/08_build_bornholm_r9_landskapsanalys_v2_baseline58_res9.R`
   - frozen `v2` reference with raw-sum neighborhood weighting
4. `script/landskapsanalys/09_build_bornholm_r9_landskapsanalys_v2_1_geomweight58_res9.R`
   - active `v2.1` run with geometry-balanced context weighting
5. `script/landskapsanalys/10_analyze_bornholm_r9_landskapsanalys_v2_1_factor_cluster_sensitivity.R`
   - compares `varimax` vs `oblimin` and `K=5` vs `K=6` on the frozen `v2.1` context matrix
6. `script/landskapsanalys/11_analyze_bornholm_r9_landskapsanalys_v2_1_factor_count_sensitivity.R`
   - compares factor counts `4..8` on the frozen `v2.1` context matrix with `varimax`
7. `script/landskapsanalys/12_run_bornholm_r9_landskapsanalys_v2_1_scale_sensitivity.R`
   - compares alternative `k` scale families around the frozen `v2.1` legacy scale ladder

## Comparison Commands
```powershell
cd C:\gislab\landskapsanalys
Rscript script\landskapsanalys\08_build_bornholm_r9_landskapsanalys_v2_baseline58_res9.R
Rscript script\landskapsanalys\09_build_bornholm_r9_landskapsanalys_v2_1_geomweight58_res9.R
```

## What To Do Next
1. Use `landskapsanalys_v2_1_geomweight58_res9` as the active starting point for all further `v2` work.
2. Keep `varimax`, `5` factors and `K = 6` as the current working model.
3. Keep `10, 50, 100, 250, 1000` as the current working scale family.
4. Next real robustness step: run leave-one-theme-out tests against `v2.1`.
5. After leave-one-theme-out, compare selected inactive groups rather than all at once.
6. Only after the `v2.1` `res9` model is cleaner, test whether `res10` improves or worsens sparsity, interpretability and stability.
7. Keep acceptance-layer work paused until the character model is cleaner.

## Note For Next Time
- Find out where the main agricultural-land landscapes are in the active model.
- Find out where the crack-valley (`sprickdalslandskap`) landscapes are in the active model.

## Key Interpretation Reminders
- Equal factor-score standard deviations are expected because the factor-score columns are normalized.
- Use `SS loadings` and `Proportion Var` to judge factor importance.
- Silhouette measures separation in factor space, not geographic distance on the map.
- Step 27 is the cultural-historical layer to keep; step 15 is the duplicate to exclude from factor input.
