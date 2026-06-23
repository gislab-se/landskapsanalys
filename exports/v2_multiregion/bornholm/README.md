# Bornholm R9 Export For V2

Purpose: stable Bornholm export/input package for the V2 multiregion repo. This package does not change the v1 app runtime contract.

Created: 2026-06-15

Primary consumer path in V2: copy or reference `bornholm_region_v2_manifest.json`.

Active H3 resolutions: R6, R7, R8, R9. R10 is retained only as source/provenance for aggregation and is not advertised by the V2 region package.

Key files:

- `bornholm_region_v2_manifest.json`
- `bornholm_lablab_landscape_r9.json`
- `bornholm_lablab_landscape_r9_app.geojson`
- `bornholm_lablab_landscape_r9.csv`
- `bornholm_establishment_placement_score_r9.csv`
- `bornholm_establishment_placement_score_r9_manifest.json`
- `bornholm_synthetic_social_acceptance_r9.csv`
- `bornholm_synthetic_social_acceptance_r9_manifest.json`
- `h3_display_geometries/bornholm_h3_res_{6,7,8,9}_land_clipped.geojson`

Aggregation summary:

- Landscape: R10 child cells grouped by H3 R9 parent. Dominant landscape type and `class_km` use largest summed `dominant_area_m2`; `F1`-`F5` use area-weighted means.
- Establishment placement score: R10 child scores/components averaged to R9; distance fields use minimum child distance; eligibility is `any`; hard_stop is `all`; reason fields are unioned.
- Social acceptance: synthetic R10 scenario values averaged to R9. Still synthetic test data, not measured social acceptance.

Generated row counts:

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
