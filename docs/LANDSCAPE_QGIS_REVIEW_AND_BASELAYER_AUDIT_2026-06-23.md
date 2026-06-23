# Landscape QGIS Review And Baselayer Audit

Date: 2026-06-23

## Purpose

Prepare QGIS review inputs for making the LABLAB/PDF landscape analyses app-ready
for Trondelag, Bornholm and Skaraborg, and record the current calculation
baselayer status for each region.

Generated review package:

- `exports/qgis_review/landscape_baselayers/README.md`
- `exports/qgis_review/landscape_baselayers/qgis_review_index.csv`
- `exports/qgis_review/landscape_baselayers/calculation_baselayer_audit.csv`

Reproducible builder:

- `scripts/build_landscape_qgis_review_package.py`

## QGIS Review Files

## Extent Decision

Decision: keep the current offshore-trimmed Trondelag app extent for runtime.

The full LABLAB/PDF extent should remain available for QGIS review, but it
should not redefine the app geography unless a later extent-expansion audit
confirms that population, settlement, roads, grid, protected nature, reindeer,
potential frames and R6/R5 rollups all support the larger area.

Practical implication:

- Use the clipped `13,735`-cell Trondelag LABLAB R7 layer as the app-default
  landscape layer.
- Keep the `4,795` outside-extent LABLAB cells as a separate review/reference
  layer.
- Do not change Trondelag's validated R7/R6/R5 display counts as part of the
  LABLAB-default switch.

Promotion implemented after QGIS review:

- Default manifest: `apps/potential_model/manifests/landscape/trondelag_lablab_landscape_r7.json`
- Runtime GeoJSON: `docs/geocontext/potential_framework/data/trondelag_lablab_landscape_h3_r7/trondelag_lablab_landskapsanalys_h3_r7_app_extent.geojson`
- Region manifests now point to the LABLAB manifest; the previous data-driven
  geocontext manifest remains method/debug context.

### Trondelag

Reviewed default source:

- `exports/qgis_review/landscape_baselayers/trondelag_lablab_r7_current_app_extent.geojson`

Companion extent-review layer:

- `exports/qgis_review/landscape_baselayers/trondelag_lablab_r7_outside_current_app_extent.geojson`

Reference/current app display layer:

- `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson`

Status:

- QGIS review accepted the clipped current-app-extent layer for runtime use.
- The LABLAB/PDF R7 layer covers all current app R7 display cells: `13,735 / 13,735`.
- The full LABLAB/PDF layer has `18,530` R7 cells, so `4,795` cells are outside the current offshore-trimmed app extent.
- All 9 LABLAB landscape types are present inside the current app extent.
- `LT09 Vidsträckt fjällandskap` is present with `359` current-app-extent R7 cells.

Type counts inside current app extent:

- `LT01 Ytterkustlandskap`: 1,255
- `LT02 Fjordlandskap`: 1,648
- `LT03 Fjordnära jordbrukslandskap`: 1,015
- `LT04 Fjällnära skogslandskap`: 1,254
- `LT05 Dalgångslandskap`: 1,076
- `LT06 Lågfjällslandskap`: 4,661
- `LT07 Högfjällslandskap`: 1,892
- `LT08 Sjö- och våtmarkslandskap`: 575
- `LT09 Vidsträckt fjällandskap`: 359

QGIS review outcome:

1. The clipped current-app-extent layer is accepted as the intended Trondelag app geography.
2. The extra `4,795` LABLAB cells outside the current app extent stay excluded from runtime and remain review/reference material.
3. `LT09 Vidsträckt fjällandskap` was reviewed in QGIS and accepted.
4. Visible boundary/gap behavior was reviewed in QGIS and accepted.
5. The data-driven geocontext layer is no longer the default landscape basis; it remains method/debug context.

### Bornholm

Active V2 LABLAB layer:

- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_app.geojson`

QA layers:

- `exports/qgis_review/landscape_baselayers/bornholm_lablab_r9_display_without_landscape.geojson`
- `exports/qgis_review/landscape_baselayers/bornholm_lablab_r9_landscape_without_display.geojson`

Status:

- The active Bornholm V2 region package already points to the LABLAB R9 manifest.
- The R9 display geometry has `6,855` cells.
- The LABLAB R9 app GeoJSON has `6,853` cells.
- There are `2` display cells without landscape properties.
- There are `24` landscape CSV rows without display geometry.
- At R8, the mismatch still matters: one display parent is missing from the landscape rollup and six landscape parents sit outside the display rollup.

The two display cells without landscape properties are tiny slivers:

- `891f2a63347ffff`, display area about `522 m2`
- `891f2a741cfffff`, display area about `6 m2`

QGIS review questions:

1. Are the two display-only cells meaningful land, or can they be dropped as clipping slivers?
2. Are the 24 landscape-without-display cells outside the intended Bornholm landmask, or did the display geometry clip too aggressively?
3. Should the display geometry be rebuilt from the LABLAB landscape surface, or should the landscape export be clipped exactly to the display geometry?
4. Should Bornholm remain "R9 display + compatibility-mode PEY", or do we need a true R9-native PEY runtime before review?

Likely issue:

- This is not only a visual landscape issue. Bornholm's region package advertises R9/R8/R7/R6, but the potential manifest is still `dynamic_res10_scaffold`. That means the app can show a good R9 LABLAB landscape package while the potential/runtime semantics still carry R10/v1 compatibility assumptions.

### Skaraborg

Current source/reference files:

- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_firstpass_epsg3006.tif`
- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_map_crop.png`
- `docs/georef/skaraborg_e20_initial_gcps.csv`
- `artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_initial_gcp_residuals.csv`

Status:

- Skaraborg is not app-ready.
- It has no region H3 display geometry, no landscape manifest and no potential manifest.
- The current E20 raster is only a first-pass georeference of a PDF map.
- Existing handoff records residuals around kilometres, so it is usable as orientation/tracing reference only.

QGIS review questions:

1. Can the GCP table be improved locally around Skara, Vara, Skövde, Falköping, Götene, Mariestad, Tibro, Hjo, Töreboda and Karlsborg?
2. Can original LiLP/Västra Götaland GIS polygons be obtained from Trafikverket/Länsstyrelsen instead of digitizing the PDF?
3. What is the intended Skaraborg region boundary and native CRS? Likely `EPSG:3006`, but the region manifest still says `TBD`.
4. Which H3 resolution should be the first app-ready target?

## Baselayer Readiness

| Region | Landscape review status | Calculation baselayer status | Main blocker |
| --- | --- | --- | --- |
| Trondelag | LABLAB R7 app-extent layer is QGIS-reviewed and promoted as default. | R7/R6/R5 display family exists and is validated. | Regional scenario data and any future full-extent expansion audit remain separate work. |
| Bornholm | LABLAB R9 is already active in V2 package. | Display/landscape mismatch exists; potential runtime still has R10 compatibility semantics. | Decide whether to repair slivers only or rebuild true R9-native PEY runtime. |
| Skaraborg | First-pass PDF georef only. | No H3/display/potential baselayers yet. | Need original GIS or a reviewed digitized polygon source, then H3 package. |

## Recommended Sequence

1. Done: review Trondelag in QGIS using the current-app-extent LABLAB layer and the outside-extent companion layer.
2. Done: create a proper `trondelag_lablab_landscape_r7` manifest and make it the default landscape basis.
3. Repair or explicitly document the Bornholm R9 display/landscape mismatch before relying on it for calculation QA.
4. Decide whether Bornholm needs true R9-native PEY before stakeholder review.
5. For Skaraborg, try to obtain original LiLP GIS first. Use the PDF georeference only as fallback/tracing material.

## Generated Data Policy

The files under `exports/qgis_review/landscape_baselayers/` are review artifacts.
Do not commit them blindly if repository size or generated-output hygiene matters.
Usually commit the script and this note first, then commit selected GeoJSON review
outputs only if they become the agreed review package.
