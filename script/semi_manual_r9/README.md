# Semi-Manual R9 Geocontext Pipeline

This folder is a fresh-start pipeline for aggregating all 46 geocontext layers to hexagons, one layer at a time.

## Why this setup
- One script per layer gives transparent, inspectable runs.
- You can run/validate each layer manually before moving on.
- Output is stored per-layer and merged at the end.

## Hex resolution
- This workflow expects H3 resolution 9.
- Default Postgres source table: `h3.bornholm_r9`.

## Scripts
- `00_check_hex_grid_r9.R`
  - Verifies that the R9 hex table exists in Postgres.
- `layers/01_*.R` ... `layers/46_*.R`
  - Runs one layer per script, in prioritized run order (not original catalog order).
  - Mapping file:
    - `script/semi_manual_r9/config/bornholm_r9_run_order.csv`
  - Example:
    - `layers/01_protected_areas.R` (original layer index 30)
    - `layers/23_population_fastboende.R` (original layer index 1)
- `99_merge_layer_outputs_r9.R`
  - Merges all per-layer CSV outputs into one raw feature table.

## Default inputs
- Layer catalog: `script/semi_manual_r9/config/bornholm_r9_geocontext_layers.csv`
- Aggregation engine reused from: `script/upstream_databas/lib/geocontext_qgis_layers.R`

## Default outputs
- Per layer: `data/interim/geocontext_r9/layers/*.csv`
- Run log: `data/interim/geocontext_r9/run_log.csv`
- Merged raw output: `data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv`
- Report PNG per step: `docs/geocontext/figures/layerNN_overview.png`
- Local interactive QA HTML per step: `docs/geocontext/review/layerNN_review.html`

## Environment variables
- `PIPELINE_ENV_PATH` (for Postgres connection)
- `PIPELINE_SCHEMA` (default `h3`)
- `HEX_TABLE` (default `bornholm_r9`)
- `HEX_SOURCE` (`postgres` or `file`, default `postgres`)
- `HEX_FILE` (required if `HEX_SOURCE=file`)
- `HEX_LAYER` (optional for multi-layer files)
- `SHOW_LAYER_SUMMARY` (`true`/`false`; defaults to `true` in interactive sessions)
- `SHOW_MAPVIEW` (`true`/`false`; default `true`)
- `FORCE_MAPVIEW` (`true` to force mapview even in non-interactive runs)
- `LAYER_PREVIEW_ONLY` (`true` to inspect a layer without writing aggregation outputs)

## Typical run order
1. Run `00_check_hex_grid_r9.R`.
2. For each script in `layers/01` to `layers/46`, run a preview pass (`LAYER_PREVIEW_ONLY=true`) to inspect map, columns, and summary.
3. Re-run that same script with `LAYER_PREVIEW_ONLY=false` to write the aggregated CSV output.
4. Create/update local review HTML for that step:
   - `Rscript script/semi_manual_r9/report/render_step_review_html.R NN`
5. Update PNG (step-specific render script) and rerender report.
6. Run `99_merge_layer_outputs_r9.R`.

