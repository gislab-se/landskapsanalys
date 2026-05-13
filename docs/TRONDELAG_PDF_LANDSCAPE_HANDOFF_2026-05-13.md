# Trondelag PDF landscape types handoff - 2026-05-13

This note captures where we stopped with the Trondelag landscape-type digitizing work. The current result is useful as process material, but **not yet good enough as a final dataset**.

## Goal

Create a clean GIS layer for Trondelag's 9 landscape types from the source PDF map material, eventually usable both as:

- vector polygons in QGIS, with clean names and no accidental gaps/overlaps
- H3/hex layers for the potential app, preferably with area-share per type where a hex crosses boundaries

The main problem is that the PDF map is visually styled for presentation, not clean GIS extraction. The white/dashed boundary lines and semi-transparent fills create gaps, intermediate colours, and class confusion when raster/vector extraction is automated.

## Source Material

Raw PDF/GIS material:

- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper Trondelag.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper linjer.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper linjer 2.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper linjer 3.pdf`

Other PDFs mentioned:

- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/Norra Trondelag.pdf`
- `C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Trondelag/Södra Trondelag.pdf`

QGIS/manual extraction output from user review:

- `C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg`

CRS:

- Use `EPSG:25832 - ETRS89 / UTM zone 32N` for Trondelag work.
- Do not save analysis outputs in `EPSG:3857` except for temporary rendered/raster intermediates.

## What Was Done

### 1. Earlier hex layer from PDF

An H3 R8 layer was generated from the rendered PDF using colour sampling/classification:

- `data/processed/trondelag/landscape/trondelag_landscape_pdf_h3_r8.geojson`

This is the layer currently useful in the app, but it has visible edge artifacts:

- white/dashed line zones become intermediate or missing hexes
- class transitions are not clean
- cells are clipped/assigned by dominant colour rather than true area-share

Conclusion: useful prototype, not final.

### 2. Clean PDF / area-share pilot

Script:

- `script/trondelag/build_trondelag_pdf_clean_area_share_pilot.R`

Output:

- `data/processed/trondelag/pdf_clean_pilot/trondelag_pdf_clean_pilot_h3_r8_area_share.gpkg`

This tested a better idea: full H3 cells with share fields like `LT01_share` ... `LT09_share`.

Conclusion: directionally good for the future app, but still depends on a clean underlying classification.

### 3. Polygon-first pilot

Script:

- `script/trondelag/build_trondelag_pdf_polygon_pilot.R`

Output:

- `data/processed/trondelag/pdf_polygon_pilot/trondelag_pdf_polygon_pilot.gpkg`

This tried to classify the PDF raster first, then polygonize it.

Conclusion: useful experiment, but not final. The PDF styling still causes gaps and wrong merges.

### 4. Bright colour extraction helper

Script:

- `script/trondelag/build_trondelag_pdf_bright_full.R`

Main output:

- `data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_bright_rgb.tif`
- `data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_clean_class.tif`
- `data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_palette.csv`

Purpose:

- create a bright, high-contrast raster where each type has a unique colour
- make QGIS colour extraction easier

Conclusion: helpful for manual extraction, but still not a final truth source. It misleads around similar grey/green types and white line zones.

### 5. Per-type masks

Script:

- `script/trondelag/build_trondelag_pdf_bright_type_masks.R`

Output folder:

- `data/processed/trondelag/pdf_polygon_bright_full_safe/type_masks/`

Purpose:

- one raster mask per type, easier to use with QGIS extraction tools

Conclusion: potentially useful, but needs visual review per type.

### 6. Southeast green/grey patch candidate

Script:

- `script/trondelag/build_trondelag_se_green_patch_mask.R`

Output:

- `data/processed/trondelag/pdf_polygon_bright_full_safe/patches/trondelag_se_green_patch_candidate.gpkg`

Conclusion: this was a targeted repair attempt, not final.

### 7. Manual vectorized naming attempts

Input:

- `C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg`

Detected layers:

- `vectorized`
- `vidstrackt_fjallandskap`
- `dalgangslandskap`
- `1`
- `vectorized2`
- `vectorized3`
- `vectorized4`
- `vectorized5`
- `vectorized6`
- `merged`

First naming script:

- `script/trondelag/name_manual_vectorized_landscape_types.R`

Output:

- `data/processed/trondelag/manual_vectorized/landskapsanalys_trondelag_named.gpkg`

Problem:

- it used modal overlap with the clean raster
- that copied raster classification errors into the manual polygons
- not reliable enough

Second naming script:

- `script/trondelag/name_manual_vectorized_landscape_types_v2.R`

Output:

- `data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_manual_layer_named_v2.gpkg`

This trusted the 9 manual extraction layers more directly.

Then we made:

- `data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_manual_v2_with_lt07_candidate.gpkg`
- `data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_confirmed_lt09_split.gpkg`

Important status:

- These are **experimental**.
- They are useful to inspect, but should not be treated as final.
- The latest issue discovered: `Vidsträckt fjällandskap` / `LT09` got merged or confused with another type in the south/southeast.
- We should not keep building final data on top of this until the source layer mapping is reviewed visually in QGIS.

## Current Understanding

There are 9 landscape types in the PDF legend:

| ID | Swedish name |
|---|---|
| LT01 | Kustslättslandskap |
| LT02 | Fjordlandskap |
| LT03 | Fjordnära jordbrukslandskap |
| LT04 | Fjällnära skogslandskap |
| LT05 | Dalgångslandskap |
| LT06 | Lågfjällslandskap |
| LT07 | Högfjällslandskap |
| LT08 | Sjö- och våtmarkslandskap |
| LT09 | Vidsträckt fjällandskap |

The highest-risk classes are:

- `LT07 Högfjällslandskap`
- `LT09 Vidsträckt fjällandskap`
- the grey/green highland-looking polygons in the south/southeast

The immediate confusion was not simply "a missing new type"; it appears that **Vidsträckt fjällandskap was joined/confused across separated areas**.

## What Is Not Solved Yet

The following are still open:

- clean final mapping from each manual/QGIS extracted layer to the correct `LT01-LT09`
- clean gap removal between polygons
- whether to use polygon-first as final source, or use polygons only as a stepping stone to H3 area-share
- how to handle white/dashed line gaps without manually redrawing everything
- final app-ready H3 layer with area shares

## Recommended Next Step

Do not continue from the latest "confirmed" GPKG as if it is final.

Instead:

1. Open `C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg` in QGIS.
2. Also open the original PDF/map reference underneath.
3. Make a review table that maps each manual source layer to a landscape type:

   - `vectorized`
   - `vidstrackt_fjallandskap`
   - `dalgangslandskap`
   - `1`
   - `vectorized2`
   - `vectorized3`
   - `vectorized4`
   - `vectorized5`
   - `vectorized6`

4. For each layer, record:

   - correct `landscape_type_id`
   - correct Swedish name
   - whether the layer should be split
   - whether it contains mixed types
   - whether it is uncertain

Suggested output CSV:

- `data/processed/trondelag/manual_vectorized_v2/manual_layer_review_decisions.csv`

Suggested columns:

- `source_layer`
- `landscape_type_id`
- `landscape_type_name_sv`
- `type_part`
- `needs_split`
- `review_note`

Once that table exists, the code should use it as the source of truth instead of guessing from raster colours or layer names.

## Recommended Gap Strategy

Gap filling does not have to be fully manual.

Use this order:

1. First make the polygon classes correct.
2. Dissolve polygons by correct type.
3. Build a narrow gap layer from the space between adjacent polygons.
4. Assign each gap by:

   - nearest touching type if the gap is only a white/dashed line artifact
   - raster majority only as a helper, not as authority
   - manual review for large or ambiguous gaps

Do not use a broad automatic raster fill yet, because it can repeat the same class-confusion problem.

## Files Most Worth Opening Next

Manual source:

- `C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg`

Experimental named outputs:

- `data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_manual_layer_named_v2.gpkg`
- `data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_confirmed_lt09_split.gpkg`

Bright helper raster:

- `data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_bright_rgb.tif`

Clean class raster, useful only as a guide:

- `data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_clean_class.tif`

Original app layer/prototype:

- `data/processed/trondelag/landscape/trondelag_landscape_pdf_h3_r8.geojson`

## Code Created In This Session

- `script/trondelag/build_trondelag_pdf_clean_area_share_pilot.R`
- `script/trondelag/build_trondelag_pdf_polygon_pilot.R`
- `script/trondelag/build_trondelag_pdf_bright_full.R`
- `script/trondelag/build_trondelag_pdf_bright_type_masks.R`
- `script/trondelag/build_trondelag_se_green_patch_mask.R`
- `script/trondelag/name_manual_vectorized_landscape_types.R`
- `script/trondelag/name_manual_vectorized_landscape_types_v2.R`
- `script/trondelag/build_trondelag_lt07_candidate_from_clean_class.R`
- `script/trondelag/combine_manual_v2_with_lt07_candidate.R`
- `script/trondelag/export_confirmed_lt09_split.R`

Some scripts are exploratory and should be cleaned up once the correct workflow is chosen.

## Best Next Work Package

Create a small, explicit review workflow:

1. Produce a QGIS project or GeoPackage with the 9 source layers styled in strong colours.
2. Add fields for `proposed_type`, `confirmed_type`, `review_note`.
3. Review just the confusing south/southeast first.
4. Export `manual_layer_review_decisions.csv`.
5. Re-run a clean naming script based on that CSV.
6. Only after that: automate gap filling and H3 area-share generation.

This keeps human judgement in the one place where it is needed: deciding the correct type from the map. Everything after that can be automated.
