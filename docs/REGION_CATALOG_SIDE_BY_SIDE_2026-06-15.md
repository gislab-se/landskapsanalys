# Region Catalog Side-By-Side Review

Date: 2026-06-15

Purpose: quick review page for comparing the active V2 region packages for
Trondelag and Bornholm. This document is a navigation aid, not a replacement for
the JSON manifests.

## Excel Review Files

- Region catalog workbook: `docs/REGION_CATALOG_SIDE_BY_SIDE_2026-06-15.xlsx`
- Parameter/buffer catalog workbook: `docs/REGION_PARAMETER_BUFFER_CATALOG_2026-06-15.xlsx`
- Next steps and governance: `docs/V2_MULTIREGION_NEXT_STEPS_AND_GOVERNANCE_2026-06-15.md`
- Trondelag parameter/buffer JSON: `regions/trondelag/parameter_buffers.json`
- Bornholm parameter/buffer JSON: `regions/bornholm/parameter_buffers.json`
- Rebuild command: `python scripts/export_region_review_workbooks.py`

## Primary Catalog Files

| Area | Trondelag | Bornholm |
| --- | --- | --- |
| Region package | `regions/trondelag/region.json` | `regions/bornholm/region.json` |
| Region index | `regions/index.json` | `regions/index.json` |
| Landscape manifest | `apps/potential_model/manifests/landscape/trondelag_lablab_landscape_r7.json` | `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.json` |
| Potential manifest | `apps/potential_model/manifests/potential/trondelag_potential_placeholder.json` | `apps/potential_model/manifests/potential/bornholm_potential_v0.json` |
| Parameter/buffer catalog | `regions/trondelag/parameter_buffers.json` | `regions/bornholm/parameter_buffers.json` |
| Social acceptance manifest | `apps/potential_model/manifests/social_acceptance/trondelag_synthetic_acceptance_v0.json` | `exports/v2_multiregion/bornholm/bornholm_synthetic_social_acceptance_r9_manifest.json` |
| Acceptance registry | `apps/acceptance_model/registry_trondelag.json` | `apps/acceptance_model/registry.json` |
| Region handoff / provenance | `docs/LANDSCAPE_QGIS_REVIEW_AND_BASELAYER_AUDIT_2026-06-23.md` and `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md` | `docs/BORNHOLM_R9_EXPORT_FOR_V2_HANDOFF_2026-06-15.md` |

## Active Region Contract

| Contract field | Trondelag | Bornholm |
| --- | --- | --- |
| `region_id` | `trondelag` | `bornholm` |
| Native CRS | `EPSG:25832` | `EPSG:25833` |
| Web CRS | `EPSG:4326` | `EPSG:4326` |
| Data status | `proxy` | `r9_v2_export_review` |
| Active H3 levels | R7, R6, R5 | R9, R8, R7, R6 |
| Default analysis H3 | R7 | R9 |
| Default display H3 | R7 | R8 |
| Display geometry root | `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/` | `exports/v2_multiregion/bornholm/h3_display_geometries/` |
| Landing card | Enabled, active pilot | Enabled, R9 export |

## Landscape Data

| Field | Trondelag | Bornholm |
| --- | --- | --- |
| Base landscape source | QGIS-reviewed LABLAB R7 layer clipped to current app extent | Imported Bornholm LABLAB R9 export |
| Source H3 | R7 | R9 |
| Display rollups | R6, R5 | R8, R7, R6 |
| Main GeoJSON | `docs/geocontext/potential_framework/data/trondelag_lablab_landscape_h3_r7/trondelag_lablab_landskapsanalys_h3_r7_app_extent.geojson` | `exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_app.geojson` |
| Factor fields | LABLAB default uses `class_km` and `LT01`-`LT09`; older `F1`-`F5` geocontext remains method/debug context | `F1` to `F5` in R9 export |
| Landscape type status | LABLAB R7 app-extent layer is active after QGIS review; data-driven geocontext is retained as method/debug context | R9 export is aggregated from v1 R10 app source; marked review |
| Known caveat | Full LABLAB extent has `4,795` cells outside the current app extent; keep them reference-only unless a later extent audit expands runtime geography | 2 R9 display cells lack R10-derived landscape properties; 24 R9 landscape rows lack land-clipped display geometry |

## Potential And Buffers

| Field | Trondelag | Bornholm |
| --- | --- | --- |
| Potential manifest status | `placeholder` | `dynamic_res10_scaffold` |
| Current PEY behavior | Shared app logic with Trondelag-specific R7 constraints and proxy layers | Shared app logic with new R9 region package, but old Bornholm potential scaffold still informs controls/runtime |
| Buffer/runtime status | Population uses 250 m proxy rules; user-facing buffers should be dissolved polygons | Parameter buffers are expected to be imperfect now; R9 package did not rebuild the full parameter/buffer runtime |
| What is ready | R7/R6/R5 display family and social acceptance are wired | R9 landscape, display geometries, placement score, synthetic social acceptance |
| What is not complete | Regional energy scenario data and any later full-LABLAB-extent expansion audit | Clean R9-native PEY parameter runtime and buffer semantics |

## Scenario And Social Acceptance

| Field | Trondelag | Bornholm |
| --- | --- | --- |
| Scenario manifest | `apps/potential_model/manifests/scenarios/trondelag_scenarios_placeholder.json` | `apps/potential_model/manifests/scenarios/bornholm_scenarios_placeholder.json` |
| Scenario status | Placeholder using Bornholm TIMES/AreaDemand until regional data exists | Existing Bornholm placeholder/prototype scenario path |
| Social acceptance | Synthetic R7 | Synthetic R9 aggregated from synthetic R10 |
| Placement score | None explicit in region package | R9 placement score from v1 export, source R10 provenance retained |

## Existing Markdown References

These are useful, but they are not the same as this side-by-side review:

- `docs/archive/app_backlog_2026-06-24/POTENTIAL_APP_REGION_DIRECTORY_PROPOSAL_2026-06-15.md`
- `docs/BORNHOLM_R9_EXPORT_FOR_V2_HANDOFF_2026-06-15.md`
- `docs/LANDSCAPE_QGIS_REVIEW_AND_BASELAYER_AUDIT_2026-06-23.md`
- `docs/archive/app_backlog_2026-06-24/POTENTIAL_APP_DATA_INVENTORY_2026-05-22.md`
- `docs/archive/app_backlog_2026-06-24/POTENTIAL_APP_REGION_ACTIVATION_PLAN.md`
- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md`

## Recommended Next Step

The next useful step is not more region-directory work. It is a parameter and
buffer runtime review.

1. Add a small catalog/checklist for per-region parameter sources and buffer
   semantics.
2. Start with Bornholm, because the R9 package is now in place but
   `bornholm_potential_v0.json` is still a `dynamic_res10_scaffold`.
3. For each parameter group, record source layer, CRS, operation, buffer
   distance, source resolution, display resolution and whether it is ready for
   dynamic PEY recalculation.
4. Then decide whether Bornholm should get a true R9 PEY runtime, or whether the
   current scaffold should be labelled as a temporary compatibility mode in the
   UI.
