# Bornholm Landmask Candidate Review - 2026-06-23

## Status

The current Bornholm app/helper landmask is derived from `Prekvart_Bornholm.shp`. QGIS review against satellite/XYZ tiles showed poor coastline alignment and internal residual linework/rings.

This means the current landmask should be treated as a v0 clipping helper, not an app-ready Bornholm land boundary.

Comparison builder:

- `scripts/build_bornholm_landmask_candidate_comparison.py`

QGIS comparison package:

- `exports/qgis_review/bornholm_landmask_candidate_comparison/qgis_candidate_comparison_index.csv`
- `exports/qgis_review/bornholm_landmask_candidate_comparison/candidate_metrics.csv`
- `exports/qgis_review/bornholm_landmask_candidate_comparison/README.md`

## Candidate Sources

Compared candidates from:

- `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Bornholm_SL01/Basmap_BOR/DAGI_KommunIND_Scale10000_BOL_33.shp`
- `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Bornholm_SL01/Basmap_BOR/DAGI_Landsdel_Scale10000_BOL_33.shp`

Reference coastline exported from:

- `D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Bornholm_SL01/Basmap_BOR/GD-V_Kyst-Coast-Line_BOL_33.shp`

## Key Metrics

Current Prekvart-derived landmask:

- Area: 587.915476 km2
- Perimeter: 296.991691 km
- Polygon parts: 1
- Interior rings: 99
- Current R9 display cells: 6855

DAGI KommunIND, filtered to `navn = Bornholm`:

- Area: 587.283056 km2
- Perimeter: 190.612249 km
- Interior rings: 0
- R9 display cells from existing source universe: 6852
- Added vs current R9 display: 14
- Removed vs current R9 display: 17
- Current source-extra cells that become inside candidate: 14
- Source CRS reported by file: EPSG:25832

DAGI Landsdel Bornholm:

- Area: 587.635333 km2
- Perimeter: 199.203129 km
- Interior rings: 0
- R9 display cells from existing source universe: 6852
- Added vs current R9 display: 14
- Removed vs current R9 display: 17
- Current source-extra cells that become inside candidate: 14
- Source CRS reported by file: EPSG:25833

## Interpretation

Both DAGI candidates remove the old mask's 99 interior rings and produce a much cleaner perimeter than the Prekvart-derived mask.

Both candidates have nearly identical impact on the current R9 runtime universe:

- 14 R9 cells would be added.
- 17 R9 cells would be removed.
- 14 of the previous 24 source rows outside display would become inside the candidate display mask.

The source-asset GeoJSON folder is not independent evidence for landmask correctness. Those layers were exported after clipping to the old landmask, and their distance tables were computed from the clipped geometries.

## Recommendation

Decision after review:

- `DAGI_Landsdel_Scale10000_BOL_33.shp` was selected as the Bornholm app landmask candidate.
- Runtime handoff: `docs/BORNHOLM_DAGI_LANDSDEL_RUNTIME_HANDOFF_2026-06-23.md`

The QGIS comparison package remains the audit trail for the choice between the two DAGI candidates.

Initial technical preference:

- Prefer `DAGI_Landsdel_Scale10000_BOL_33.shp` if the app's region concept is "Bornholm as a regional pilot including associated islands/landsdel geometry".
- Prefer `DAGI_KommunIND_Scale10000_BOL_33.shp` filtered to Bornholm if the app's region concept should be the municipal boundary only.

Either candidate is better than the current Prekvart-derived mask for app display clipping.

## Rebuild Scope If Replaced

Replacing the landmask requires a controlled Bornholm refresh:

1. Export the selected candidate as the new Bornholm landmask.
2. Rebuild R6/R7/R8/R9 display geometries.
3. Re-export/clips acceptance source assets from raw source layers.
4. Rebuild distance tables.
5. Rebuild establishment placement score if it depends on those distance tables.
6. Re-run Bornholm runtime QA.
7. Update region manifests and handoff notes.

This is a meaningful pipeline refresh, but not a full restart. It should not require changing the shared app shell or redoing Trondelag.
