# AGENTS.md - Semi-manual R9 workflow

This folder uses a deliberate semi-manual process. Do not optimize away manual checkpoints unless the user explicitly asks.

## Scope

Applies to:
- `script/semi_manual_r9/layers/*.R`
- `script/semi_manual_r9/lib/*.R`
- `script/semi_manual_r9/report/*`
- `script/semi_manual_r9/config/*`

## Core principles

1. Preview input before aggregation, every time.
2. One layer script at a time, manually reviewed.
3. Keep the process explainable for stakeholders.
4. Automation is allowed only as support, not as a replacement for manual control.

## Run order

- Script order `layers/01` to `layers/46` is the active priority order.
- Mapping to original catalog index is stored in:
  - `script/semi_manual_r9/config/bornholm_r9_run_order.csv`

## Mandatory per-layer workflow

For each step script `NN_*.R`:

1. Preview pass (input-first)
   - Standard wrapper scripts:
     - `LAYER_PREVIEW_ONLY=true`
     - `SHOW_LAYER_SUMMARY=true`
     - `SHOW_MAPVIEW=true` (or false in headless runs)
   - Verify:
     - column names
     - basic summary
     - geometry type / CRS
     - pre-aggregation map

2. Manual checkpoint
   - Wait for user confirmation that preview looks correct.
   - Do not write aggregation output before confirmation.

3. Aggregation pass
   - Standard wrapper scripts:
     - `LAYER_PREVIEW_ONLY=false`
   - Confirm output files are updated:
     - `data/interim/geocontext_r9/layers/*.csv`
     - `data/interim/geocontext_r9/run_log.csv`

4. Reporting artifact
   - Produce/update one PNG for the step:
     - `docs/geocontext/figures/layerNN_overview.png`
   - Produce/update one local interactive HTML review map for the same step:
     - `docs/geocontext/review/layerNN_review.html`
     - Must include both input layer and aggregated output layer.
     - This HTML is for internal QA only at this stage.
   - Generic helper for HTML:
     - `Rscript script/semi_manual_r9/report/render_step_review_html.R NN`
   - Re-render:
     - `script/semi_manual_r9/report/all_layers_progress.qmd`

## Special case: population layer (run step 23)

`layers/23_population_fastboende.R` is intentionally explicit and has custom post-aggregation classes.

Use:
- preview-like run without write:
  - `RUN_AGGREGATION=true`
  - `WRITE_OUTPUT=false`
  - `SHOW_LAYER_SUMMARY=true`
  - `SHOW_MAPVIEW=true`
- production write:
  - `RUN_AGGREGATION=true`
  - `WRITE_OUTPUT=true`

Do not move population-specific class styling into generic helper code.

## Editing rules

When changing scripts:
- Preserve transparency over cleverness.
- Prefer clear, short comments for non-obvious logic.
- Avoid hidden side effects.
- Keep file names aligned with priority run order and mapping CSV.
- Keep short report text explicit about geometry type (point/line/polygon) and how aggregation was applied.

## What not to do

- Do not run all 46 layers in one bulk command unless explicitly requested.
- Do not skip preview to "save time".
- Do not silently change run order or layer mapping.

