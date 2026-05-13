# AGENTS.md

## Rule 1: Bornholm First

Before implementing anything for Trondelag, inspect the corresponding Bornholm implementation first.

At this stage, Trondelag should mirror Bornholm as closely as possible in:

- data flow
- app logic
- user interface
- layer naming
- scenario handling
- establishment-area behavior
- map controls
- text/labels
- validation approach

Only deviate from Bornholm when Trondelag data truly requires it. Any deviation must be documented in the code, manifest, or a handoff note.

Do not invent a new Trondelag-specific pattern when a Bornholm pattern already exists.

## Regional CRS

Bornholm and Trondelag do not share native CRS.

- Bornholm uses `EPSG:25833`
- Trondelag uses `EPSG:25832`

Do Trondelag distance, buffer, and area geometry in `EPSG:25832` unless a source-specific check proves otherwise.

Use `EPSG:4326` only for web/export formats that require lon/lat.
Use `EPSG:3857` only for temporary map rendering or raster intermediates.

## Trondelag Potential App

Trondelag is currently a regional adaptation of the Bornholm potential app.

Before changing Trondelag potential-app behavior:

1. Find the matching Bornholm implementation.
2. Understand how Bornholm handles the same concept.
3. Copy the structure unless there is a documented reason not to.
4. Keep labels and user-facing explanations consistent with Bornholm.

Current Trondelag constraints:

- Do not expose Trondelag R9 in the interactive app.
- Supported Trondelag H3 display resolutions are R8, R7, and R6.
- Establishment-area logic should follow Bornholm.
- Do not introduce a separate `landskapspotential vind` hex-only concept if Bornholm handles it through establishment area and scenario area demand.

## Population And Settlement Buffers

For Trondelag, user-facing population and settlement buffers should be dissolved polygon buffers from the 250 m population-grid cell proxy.

Do not show these as H3 buffer overlays in the user-facing app.

H3 can still be used internally for scoring or rollup where appropriate.

Always be explicit in labels and notes that Trondelag population currently uses a 250 m grid/centroid proxy, not individual population points.

## PDF Landscape-Type Work

The Trondelag PDF landscape-type extraction is experimental.

Relevant handoff:

- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md`

Do not treat generated PDF-derived GPKG/TIF outputs as final unless the handoff or a later review note says so.

Before using a PDF-derived Trondelag landscape layer in the app:

1. Check the handoff.
2. Confirm the layer has all 9 landscape types.
3. Confirm `LT09 Vidsträckt fjällandskap` has not been incorrectly merged or confused.
4. Confirm gaps/overlaps have been reviewed.
5. Prefer explicit review tables over guessing from raster colours.

## Generated Data

Be conservative about committing generated GIS outputs.

Usually commit:

- scripts
- manifests
- handoff notes
- small CSV review tables
- documentation

Usually do not commit:

- large `.gpkg`
- large `.tif`
- generated map HTML folders
- temporary QGIS/plugin outputs
- Streamlit logs

If a generated GIS file is important enough to commit, document why and where it came from.

## Repo Hygiene

This repo contains exploratory analysis, app code, generated reports, and GIS data.

When cleaning or refactoring:

- Do not delete exploratory outputs unless the user explicitly approves.
- Prefer moving uncertain material into a clearly named archive or backlog.
- Keep reproducible scripts close to the workflow they belong to.
- Add handoff notes when a workflow is incomplete.
- Avoid mixing unrelated cleanup with app behavior changes.

## Semi-Manual R9 Workflow

The folder `script/semi_manual_r9/` has its own local instructions:

- `script/semi_manual_r9/AGENTS.md`

Follow that file for semi-manual R9 work.
Do not override its manual checkpoint process from the root instructions.
