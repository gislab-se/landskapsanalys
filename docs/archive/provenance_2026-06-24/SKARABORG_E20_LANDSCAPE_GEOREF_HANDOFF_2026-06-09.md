# Skaraborg E20 Landscape Georeference Handoff

Date: 2026-06-09

## Purpose

Create an experimental georeferenced raster from Trafikverket's E20 landscape-type map so Skaraborg V3 can later derive landscape-type polygons and H3/hex attributes.

This is not authoritative GIS data. It is a PDF-derived proxy from a generalized publication map and must be reviewed before use in scoring or the V3 app.

## Source

- Source PDF: `https://bransch.trafikverket.se/contentassets/31699a9e58664144a4291b2397dcd7dc/gestaltningsprogram_e20_150420.pdf`
- Source page: page 8 in the PDF, figure with regional landscape types for E20/Vastra Gotaland.
- Method context: the PDF describes the E20 landscape analysis as based on LiLP and regional landscape types/character areas for Vastra Gotaland.

## Repo Files

- Script: `scripts/georef_skaraborg_e20_landscape.R`
- Initial GCP table: `docs/georef/skaraborg_e20_initial_gcps.csv`
- Source/crop artifacts: `artifacts/skaraborg_landscape_georef/`

Generated artifacts from the current first pass:

- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_map_crop.png`
- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_firstpass_epsg3006.tif`
- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_firstpass_preview.png`
- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_initial_gcp_residuals.csv`

## Current Transform

- Crop geometry: `1930x1250+105+95` from rendered PDF page 8.
- Transform: first-order affine from pixel coordinates to `EPSG:3006`.
- Output raster CRS: `EPSG:3006` / SWEREF99 TM.
- Output raster resolution: 250 m.
- Output raster dimensions: 740 columns x 446 rows x 3 RGB bands.
- Output extent: `xmin=303000`, `xmax=488000`, `ymin=6410250`, `ymax=6521750`.

Current residuals are too high for final use:

- Median fit residual: about 2.5 km.
- Max fit residual: about 7.8 km.
- Highest residuals: Tibro, Karlsborg, Vanersborg, Toreboda, Mariestad, Falkoping.

The first pass is good enough to orient the map and start manual review, not good enough for final polygon boundaries.

## Recommended Next Steps

1. Open `e20_regional_landscape_types_map_crop.png` and `e20_regional_landscape_types_firstpass_epsg3006.tif` in QGIS.
2. Refine the GCP table using precise visual points:
   - Prefer town centers, road junctions, lake shore intersections, and clearly visible E20/E45/rail features.
   - Prioritize the Skaraborg area: Vara, Skara, Skovde, Falkoping, Gotene, Mariestad, Tibro, Hjo, Toreboda, Karlsborg.
   - Keep some points as `role=check` once the script has enough `role=fit` points.
3. Re-run `Rscript scripts/georef_skaraborg_e20_landscape.R`.
4. Aim for local Skaraborg residuals below roughly 1 km before digitizing boundaries.
5. Digitize a reviewed polygon layer in `EPSG:3006` with fields:
   - `landscape_type`
   - `source_pdf`
   - `source_page`
   - `confidence`
   - `review_notes`
6. Clip/dissolve to the Skaraborg V3 region and intersect/rasterize to the V3 hex grid.
7. Mark the final V3 source status as `proxy` or `experimental` unless original LiLP GIS data is obtained.

## Digitizing Notes

The map contains overprinted roads, labels, settlements, and borders, so pure color classification will need manual cleanup. A practical workflow is:

- Use the georeferenced raster as a tracing backdrop.
- Digitize broad landscape-type polygons manually for Skaraborg.
- Add confidence flags where labels, roads, or fuzzy boundaries make interpretation uncertain.
- Convert to hexes only after the polygon layer has had a visual review pass.

Do not commit large generated `.tif` or `.gpkg` outputs unless we decide they are the reviewed deliverable and document provenance.
