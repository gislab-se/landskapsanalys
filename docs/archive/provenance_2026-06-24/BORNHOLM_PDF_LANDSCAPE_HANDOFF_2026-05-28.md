# Bornholm LABLAB PDF landscape types handoff - 2026-05-28

This note starts the Bornholm equivalent of the earlier Trondelag LABLAB/PDF landscape-type workflow.

## Goal

Create a reviewed Bornholm LABLAB landscape-type GIS layer from the source PDF material, eventually usable as:

- clean vector polygons in QGIS
- optional H3/area-share app data after manual review

This is separate from the current app's existing data-driven Bornholm v10 landscape model.

## Source Material

Descriptive/report PDF:

- `C:/gislab/landskapsanalys/data/Landskapstyper Bornholm.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Landskapstyper Bornholm.pdf`

GIS PDF:

- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Landskapstyper Bornholm.pdf`

Related SpeedLocal folder:

- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/`

Useful reference PDFs in the same folder:

- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Bornholm Landskasptyper Linjer.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Bornholm Landskasptyper Linjer 2.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Ortofoto Bornholm.pdf`

Important CRS note:

- The Bornholm GIS PDF reports `EPSG:3006` / SWEREF99 TM.
- Bornholm app/analysis geometry should still use `EPSG:25833`.
- The helper rasters stay aligned to the PDF CRS; reviewed polygon outputs are transformed to `EPSG:25833`.

## Landscape Types

The report describes five Bornholm landscape types:

| ID | Name |
| --- | --- |
| LT01 | Klippigt kustlandskap |
| LT02 | Sandigt kustlandskap |
| LT03 | Jordbruksdominerat sprickdalslandskap |
| LT04 | Skogsklatt sprickdalslandskap |
| LT05 | Slatt- och jordbrukslandskap |

The source PDF text has minor label inconsistencies/typos, including `Jordbruks-och Sprickdalslandskap` in the legend and an LT04 label where LT03 appears expected in the descriptive pages. Use the reviewed type table above unless the user decides otherwise in QGIS review.

## What Codex Did Here

Created Bornholm helper scripts:

- `script/bornholm/build_bornholm_pdf_bright_full.R`
- `script/bornholm/build_bornholm_pdf_bright_type_masks.R`
- `script/bornholm/name_manual_vectorized_landscape_types.R`

The first script reads the geospatial PDF directly with `terra`, classifies approximate source colours, applies the existing Bornholm landmask by default, and writes helper rasters.

The second script writes one binary/RGB mask per landscape type for easier QGIS inspection or polygonizing.

The third script is the post-QGIS import step. It does not guess type names from raster colour. It expects a manually reviewed GeoPackage plus a decision CSV, then writes clean named/dissolved outputs in `EPSG:25833`.

## Current Helper Outputs

The helper scripts were run once in this setup. Output folders are:

- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/`
- `data/processed/bornholm/lablab_pdf_landscape/manual_vectorized/`

Most useful QGIS helper files:

- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/bornholm_pdf_bright_full_bright_rgb.tif`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT01_rgb_mask.tif`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT02_rgb_mask.tif`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT03_rgb_mask.tif`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT04_rgb_mask.tif`
- `data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe/type_masks/bornholm_pdf_bright_full_LT05_rgb_mask.tif`
- `data/processed/bornholm/lablab_pdf_landscape/manual_vectorized/manual_layer_review_decisions.csv`

## What The User Should Do In QGIS

1. Open the original GIS PDF as reference.
2. Open `bornholm_pdf_bright_full_bright_rgb.tif` and the per-type masks.
3. Inspect each LT01-LT05 class against the original PDF/report.
4. Vectorize or manually trace corrected polygons per type.
5. Fix obvious gaps/overlaps only after type assignment is correct.
6. Save the reviewed layers to:

   - `C:/gislab/data/ut_bornholm/landskapsanalys_bornholm.gpkg`

7. Run:

   - `Rscript script/bornholm/name_manual_vectorized_landscape_types.R`

If the decision CSV does not exist, the script creates:

- `data/processed/bornholm/lablab_pdf_landscape/manual_vectorized/manual_layer_review_decisions.csv`

Fill it with:

- `source_layer`
- `landscape_type_id`
- `type_part`
- `review_note`

Then rerun the script.

## Why This Mirrors Trondelag

Same principle as the Trondelag PDF work:

- Codex prepares reproducible helper rasters, masks, summaries, and import scripts.
- The user makes the visual/manual QGIS decisions.
- The code uses explicit review decisions as truth, not raster-majority guesses.

Bornholm differs from Trondelag because:

- Bornholm has 5 LABLAB landscape types, not 9.
- The Bornholm GIS PDF is transparent fills over imagery, so colour classification is only a helper.
- The PDF source CRS is `EPSG:3006`, while the app/native Bornholm geometry should be `EPSG:25833`.

## Not Final Yet

Do not wire this Bornholm LABLAB layer into the potential app until:

1. All five types are present.
2. The LT03/LT04 label inconsistency has been checked.
3. Gaps/overlaps have been reviewed.
4. The QGIS decision CSV exists and has notes for uncertain boundaries.
5. A clean app-ready H3/area-share layer has been generated from reviewed polygons.
