# Bornholm R9 Export For V2 Handoff

Date: 2026-06-15

## Purpose

This work creates a stable Bornholm R9 export/input package for the V2 multiregion repo. It is not intended to change the v1 app runtime. The v1 Bornholm runtime manifests remain R10-oriented for the existing app unless a later task explicitly migrates them.

V2 package root:

`exports/v2_multiregion/bornholm/`

Recommended V2 consumption:

1. Copy `exports/v2_multiregion/bornholm/` into the V2 repo at the same relative path.
2. Use `exports/v2_multiregion/bornholm/bornholm_region_v2_manifest.json` as the Bornholm region package/manifest.
3. Keep the paths inside that manifest unchanged if the package is copied to the same relative path.

The V2 package advertises active H3 resolutions R6, R7, R8, and R9 only. R10 is retained as source/provenance for aggregation and is not advertised as an active V2 display or analysis choice.

## Checkpoint

Before R9 export work, the dirty tracked Bornholm v1 runtime state was committed as:

`2664c82 chore: checkpoint stable Bornholm v1 runtime before R9 export`

Only tracked Bornholm runtime/documentation changes were included. Pre-existing untracked generated R9/GPKG/HTML/export material was not included in the checkpoint.

## Created Files

Reproducible scripts:

- `scripts/export_bornholm_r9_for_v2.py`
- `scripts/validate_bornholm_r9_v2_export.py`

Export package:

- `exports/v2_multiregion/bornholm/README.md`
- `exports/v2_multiregion/bornholm/build_summary.json`
- `exports/v2_multiregion/bornholm/bornholm_region_v2_manifest.json`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.json`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.csv`
- `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_app.geojson`
- `exports/v2_multiregion/bornholm/bornholm_establishment_placement_score_r9.csv`
- `exports/v2_multiregion/bornholm/bornholm_establishment_placement_score_r9_manifest.json`
- `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9.csv`
- `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9_manifest.json`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_6_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_7_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_8_land_clipped.geojson`
- `exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_9_land_clipped.geojson`

Large generated files are included because the V2 package needs a self-contained R9 GeoJSON and display geometry set. Largest generated export file is `bornholm_lablab_landscape_r9_app.geojson` at about 27.6 MB.

## Row Counts

From `build_summary.json`:

```json
{
  "landscape_rows": 6877,
  "landscape_geojson_features": 6853,
  "landscape_display_features_without_properties": 2,
  "score_rows": 6878,
  "score_source_rows": 47117,
  "social_rows": 6878,
  "social_source_rows": 47117
}
```

Display/landscape mismatch note:

- Display R9 cells without R10-derived landscape properties: `891f2a63347ffff`, `891f2a741cfffff`.
- R9 landscape rows without land-clipped display geometry: 24.
- The export GeoJSON contains the 6,853 display cells that have landscape properties. The CSV keeps the full R10-derived R9 landscape table.

## Aggregation Methods

Landscape:

- Source: `data/processed/bornholm/lablab_landscape_h3/bornholm_lablab_landscape_r10_app.geojson`.
- R10 `hex_id` mapped to H3 R9 parent with `h3.cell_to_parent`.
- Dominant `landscape_type_id`, `landscape_type_name`, `landscape_type`, `class_km`, and `class_k8` use the largest summed `dominant_area_m2` among R10 child cells.
- `F1` to `F5` use area-weighted means by `dominant_area_m2`.
- Existing R9 IVL columns from `bornholm_lablab_landscape_r9_final_delivery_sv.csv` are joined where available.

Establishment placement score:

- Source: `docs/geocontext/potential_framework/data/bornholm_establishment_placement_score_v1/bornholm_establishment_placement_score_r10.csv`.
- R10 `hex_id` mapped to H3 R9 parent.
- Continuous score and component columns are arithmetic means over R10 child hexes.
- Distance columns use minimum R10 child distance inside each R9 parent.
- `wind_eligible` and `solar_eligible` are `any`.
- `wind_hard_stop` and `solar_hard_stop` are `all`, so an R9 parent is a hard stop only when all child R10 cells are hard stops for that technology.
- Reason fields are semicolon-unioned. `*_exclusion_reason` is retained only for all-hard-stop R9 parents.

Social acceptance:

- Source: `docs/geocontext/potential_framework/data/social_acceptance/bornholm_synthetic_social_acceptance_r10.csv`.
- Synthetic R10 scenario values are averaged to R9.
- This remains synthetic UI/integration data, not measured social acceptance.

CRS:

- Export region manifest records Bornholm native CRS as `EPSG:25833`.
- Web/export GeoJSON remains `EPSG:4326`.

## V2 Region Manifest Contract

`bornholm_region_v2_manifest.json` has:

- `available_h3_resolutions`: `[6, 7, 8, 9]`
- `default_h3_resolution`: `9`
- `default_display_h3_resolution`: `8`
- `h3_display_geometries`: only `6`, `7`, `8`, `9`
- `landscape_manifest`: `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.json`
- `establishment_placement_score.path`: `exports/v2_multiregion/bornholm/bornholm_establishment_placement_score_r9.csv`
- `establishment_placement_score.manifest`: `exports/v2_multiregion/bornholm/bornholm_establishment_placement_score_r9_manifest.json`
- `social_acceptance_manifest`: `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9_manifest.json`

## Remaining R10 References

Expected/provenance or v1-runtime references:

- `apps/potential_model/manifests/regions/bornholm.json` still points v1 runtime to R10 landscape and R10 establishment placement score.
- `apps/potential_model/manifests/landscape/bornholm_lablab_landscape_r10.json` remains the v1 LABLAB R10 manifest.
- `apps/potential_model/manifests/social_acceptance/bornholm_synthetic_acceptance_v0.json` remains synthetic R10 test-data manifest for v1.
- `scripts/build_bornholm_establishment_placement_score.py`, `scripts/build_score_preview_map.py`, and `scripts/build_bornholm_lablab_landscape_r10_review.R` still build/review R10 artifacts.
- `scripts/export_bornholm_r9_for_v2.py` intentionally references R10 sources as aggregation inputs.
- `exports/v2_multiregion/bornholm/*_r9_manifest.json` may mention R10 only as `source_h3_resolution` or aggregation provenance.

Not blocking for V2:

- No V2 export region package advertises R10 as an active resolution.
- No V2 export `h3_display_geometries` entry points to R10.

Still to review later:

- The R9 social acceptance export is reasonable because it is synthetic and directly aggregable, but V2 should treat it as synthetic test data until real acceptance data exists.
- Potential/scenario runtime files in v1 are still dynamic/v1 contracts; this task did not create a new R9 potential model. The V2 region package is focused on R9 landscape, display geometries, placement score, and synthetic social acceptance.

## Verification

Commands run successfully:

```powershell
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\export_bornholm_r9_for_v2.py
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\validate_bornholm_r9_v2_export.py
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe -m py_compile scripts\export_bornholm_r9_for_v2.py scripts\validate_bornholm_r9_v2_export.py
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe -m unittest tests.test_score_ranked_allocation
```

Validation result:

- Export validator: OK.
- `tests.test_score_ranked_allocation`: 13 tests OK.
- `py_compile`: OK.
- Streamlit cache warnings appeared during unit test imports outside a Streamlit runtime; they did not block tests.
