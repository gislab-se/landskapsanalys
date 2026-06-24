# Active Project Documents - 2026-06-24

This index separates current steering documents from historical handoffs. Use it
to avoid treating old transition notes as active implementation instructions.

## Active Steering

- `AGENTS.md` is the top-level working rule set for this repo. It now says that
  fixes should start in shared app behavior, and regional exceptions must be
  documented near the relevant region package.
- `regions/bornholm/REGIONAL_NOTES.md` documents current Bornholm regional
  exceptions, including the DAGI Landsdel baseline and coastal/strand-protection
  establishment semantics.
- `regions/trondelag/REGIONAL_NOTES.md` documents current Trondelag regional
  exceptions, including EPSG:25832, R7/R6/R5 display, and the 250 m population
  grid proxy.
- `docs/V2_MULTIREGION_NEXT_STEPS_AND_GOVERNANCE_2026-06-15.md` remains the
  main roadmap for the V2 multiregion app track.
- `docs/REGIONAL_ENERGY_POTENTIAL_APP_INSTRUCTIONS.md` remains the general app
  usage and product instruction document.
- `REPO_CLEANUP_BACKLOG.md` is the backlog for deferred cleanup, including
  future R10/R8/R9 artifact audits.

## Active Source And Review References

- `docs/LANDSCAPE_QGIS_REVIEW_AND_BASELAYER_AUDIT_2026-06-23.md` is the current
  cross-region landscape/base-layer review note.
- `docs/SKARABORG_LANDSCAPE_TYPES_SOURCE_INVENTORY_2026-06-09.md` remains the
  active Skaraborg source-inventory/request note.
- `docs/BORNHOLM_R9_EXPORT_FOR_V2_HANDOFF_2026-06-15.md` remains Bornholm V1 to
  V2 provenance and is referenced by `regions/bornholm/region.json`.
- `docs/TRONDELAG_PDF_LANDSCAPE_HANDOFF_2026-05-13.md` remains the relevant
  warning note before using PDF-derived Trondelag landscape layers.
- `docs/REGION_CATALOG_SIDE_BY_SIDE_2026-06-15.md` remains the current
  region-catalog navigation aid.
- `docs/LANDSKAPSPOTENTIAL_SOL_UNDERLAG.md` remains a source/model reference for
  the landscape-solar concept.
- `docs/POTENTIAL_APP_SCENARIO_ALLOCATION_EXPLANATION.md` remains a runtime
  explanation of scenario allocation, not a governance document.
- `docs/archive/provenance_2026-06-24/BORNHOLM_PDF_LANDSCAPE_HANDOFF_2026-05-28.md`
  remains historical Bornholm PDF landscape provenance unless a newer review
  note supersedes it.
- `docs/archive/provenance_2026-06-24/SYNTHETIC_SOCIAL_ACCEPTANCE_HANDOFF_2026-05-19.md`
  remains provenance for synthetic social-acceptance data.

## Paused Or Backlog Material

- `exports/v3_migration/*` and
  `docs/archive/v3_backlog_2026-06-24/V3_RENDERED_LAYER_STATUS_CONTRACT_2026-06-09.md`
  are useful reference material, but V2 multiregion is the active
  implementation track.
- `docs/archive/future_migration_2026-06-24/FLOWCORE_USABLE_MIGRATION_HANDOFF_2026-06-24.md`
  is a future migration reference, not the current runtime app contract.
- `docs/archive/app_backlog_2026-06-24/` contains older app proposals, TODOs,
  prompts, and backlog notes. They are not active unless promoted back into this
  index or a region note.

## Archived Transition Handoffs

The Bornholm DAGI transition handoffs from 2026-06-23 and 2026-06-24 were moved
to `docs/archive/bornholm_dagi_transition_2026-06-24/`.

They remain available as audit trail, but their "next steps" are superseded by
the current Bornholm region manifest, `regions/bornholm/REGIONAL_NOTES.md`, and
the app bugfixes made after the QGIS review.

Older provenance and handoff notes that remain useful for audit trail were moved
to `docs/archive/provenance_2026-06-24/`. They are not active implementation
instructions.

## Next Larger Focus

After the current bugfix pass, the larger direction is to keep the app on the V2
multiregion track, move durable behavior into region manifests/catalogs, and
only keep code-level regional branches for real data or algorithm differences.
