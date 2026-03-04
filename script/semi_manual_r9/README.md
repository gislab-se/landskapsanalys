# Semi-Manual R9 Geocontext Pipeline

This folder is a fresh-start pipeline for aggregating all 37 geocontext layers to hexagons, one layer at a time.

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
- `layers/01_*.R` ... `layers/37_*.R`
  - Runs aggregation for one layer each.
- `99_merge_layer_outputs_r9.R`
  - Merges all per-layer CSV outputs into one raw feature table.

## Default inputs
- Layer catalog: `script/semi_manual_r9/config/bornholm_r9_geocontext_layers.csv`
- Aggregation engine reused from: `script/upstream_databas/lib/geocontext_qgis_layers.R`

## Default outputs
- Per layer: `data/interim/geocontext_r9/layers/*.csv`
- Run log: `data/interim/geocontext_r9/run_log.csv`
- Merged raw output: `data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv`

## Environment variables
- `PIPELINE_ENV_PATH` (for Postgres connection)
- `PIPELINE_SCHEMA` (default `h3`)
- `HEX_TABLE` (default `bornholm_r9`)
- `HEX_SOURCE` (`postgres` or `file`, default `postgres`)
- `HEX_FILE` (required if `HEX_SOURCE=file`)
- `HEX_LAYER` (optional for multi-layer files)

## Typical run order
1. Run `00_check_hex_grid_r9.R`.
2. Run each script in `layers/` in order.
3. Review per-layer outputs.
4. Run `99_merge_layer_outputs_r9.R`.

