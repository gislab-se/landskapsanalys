# V2 Multiregion Next Steps And Governance

Date: 2026-06-15

## Recommendation

Use `landskapsanalys-v2-multiregion` as the main track for the regional
potential app.

The separate V3/`landskapspotential` migration track should be paused and
treated as an archive/backlog of useful ideas until the V2 multiregion catalog
flow is stable. The V3 work contains valuable inventories and contracts, but the
current V2 region-package direction is simpler, closer to the working app, and
already handles Trondelag and Bornholm in one shell.

Do not delete V3 material yet. Mark it as paused/archived, then selectively pull
back useful concepts such as rendered-layer status, applied/draft semantics and
result-layer contracts into V2.

## Short Answer: Is Trondelag Fully Catalog-Driven?

No. Trondelag is partly catalog-driven, but not fully.

The app now reads major regional facts from `regions/trondelag/region.json` and
linked manifests. That includes CRS, H3 resolutions, display geometries,
landing-card text, manifest paths, acceptance registry and the new
`parameter_buffers.json` review catalog.

However, `potential_app.py` still contains Trondelag-specific behavior:

- default app region is hardcoded as `DEFAULT_REGION_ID = "trondelag"`;
- the tutorial is Trondelag-only and has Trondelag-specific storage keys/text;
- social acceptance has a Trondelag fallback manifest path;
- population buffers use hardcoded Trondelag RDS/script/cache paths;
- Trondelag population/settlement buffer rendering uses special dissolved
  polygon logic;
- Trondelag fast-distance runtime is gated by `region_id == "trondelag"`;
- establishment-area rollup has a Trondelag-specific R7-to-R6/R5 path;
- some map-layer visibility defaults and captions are Trondelag-specific;
- validation scripts encode Trondelag R7/R6/R5 expectations directly.

Some of this is legitimate regional behavior. The next step is not to remove all
special cases. The next step is to separate:

- regional data and policy that belongs in catalogs/manifests;
- app algorithms that can stay in code but should be selected by catalog flags;
- temporary compatibility branches that should be removed after Bornholm and
  Trondelag are both validated.

## What Is Already Catalog-Driven

The following are already in the regional package flow:

- region discovery through `regions/index.json`;
- region package files under `regions/<region>/region.json`;
- landing-card metadata for Trondelag, Bornholm and Skara;
- native CRS and web CRS;
- map center, bounds and zoom;
- available H3 display resolutions;
- default analysis and display H3 resolutions;
- display geometry paths and, for Trondelag, expected feature counts;
- linked landscape, potential, scenario, social-acceptance and acceptance
  registry manifests;
- new per-region parameter/buffer review catalogs:
  - `regions/trondelag/parameter_buffers.json`
  - `regions/bornholm/parameter_buffers.json`
- review workbooks:
  - `docs/REGION_CATALOG_SIDE_BY_SIDE_2026-06-15.xlsx`
  - `docs/REGION_PARAMETER_BUFFER_CATALOG_2026-06-15.xlsx`

The loader side is also mostly general:

- `apps/potential_model/manifests.py` finds `regions/index.json`, reads
  `regions/*/region.json` and resolves linked manifests.
- `apps/potential_model/region_status.py` builds runtime status from linked
  manifests and H3 geometry paths.

## What Is Still Hardcoded To Trondelag

These are the important remaining Trondelag-specific code paths.

| Area | Current location | Assessment | Suggested destination |
| --- | --- | --- | --- |
| Default app region | `potential_app.py` `DEFAULT_REGION_ID` | Acceptable for now, but duplicated with `regions/index.json`. | Read default from `regions/index.json`. |
| Tutorial availability and text | `potential_app.py` `_trondelag_tutorial_available`, `_trondelag_tutorial_steps` | App feature, but should not be hardcoded to one region forever. | Add `tutorial` config to `region.json` or a linked tutorial manifest. |
| Social acceptance fallback | `potential_app.py` `_social_acceptance_manifest` | Temporary compatibility fallback. | Remove fallback once every active region declares `social_acceptance_manifest`. |
| Population proxy RDS/script/cache paths | `potential_app.py` `_trondelag_population_*` | Real regional policy, but paths should be catalog fields. | `regions/trondelag/parameter_buffers.json` under settlement/population render policy. |
| Population buffer polygon rendering | `potential_app.py` `_trondelag_population_buffer_polygon_layer` | Legitimate regional algorithm because Trondelag uses a 250 m proxy. | Keep algorithm in code, select via catalog flag such as `render_mode: dissolved_polygon_proxy`. |
| Fast-distance runtime | `potential_app.py` `_wind_fast_distance_runtime_result` | Legitimate large-region optimization. | Keep algorithm in code, select via `runtime_strategy: fast_distance` in region/parameter catalog. |
| R7-to-R6/R5 establishment rollup | `potential_app.py` `_trondelag_rollup_potential_establishment_frame` | Legitimate Trondelag display strategy. | Keep algorithm in code, select via `rollup_strategy: dominant_child_area`. |
| Solar source resolution choice | `potential_app.py` region-id check around solar source resolution | Likely catalog policy. | `region.json` or potential manifest field for `runtime_base_resolution`. |
| Scenario allocation hidden by default | `potential_app.py` Trondelag visibility branch | UI policy. | Region UI preferences in `region.json`. |
| Trondelag-specific captions/help | `potential_app.py` UI text near population controls | User-facing truth, but should be derived from region notes. | `parameter_buffers.json` notes/help text. |
| Contract test constants | `scripts/validate_potential_region_contract.py` | Good as assertions, but brittle as hardcoded literals. | Read expected H3 family/counts from `region.json` where possible. |

## AGENTS And Governance Cleanup

Root `AGENTS.md` is mostly aligned with the new V2 multiregion direction. It
already says:

- Bornholm and Trondelag share the app shell;
- data paths can differ;
- Bornholm and Trondelag must be validated independently;
- Trondelag uses `EPSG:25832`;
- Bornholm uses `EPSG:25833`;
- Trondelag population buffers should be dissolved polygon buffers from the
  250 m proxy;
- generated GIS outputs should not be committed casually.

What should be cleaned up:

1. Add a short "Main Track" section:
   - V2 multiregion is the active app track.
   - V3/`landskapspotential` is paused/backlog unless the user explicitly
     reactivates it.

2. Add a "Region Catalog First" section:
   - When adding region behavior, first ask whether it belongs in
     `regions/<region>/region.json`, `parameter_buffers.json` or a linked
     manifest.
   - Code-level region branches are allowed only for real algorithmic
     differences, and they must be documented in the region catalog.

3. Keep the existing Trondelag population-buffer rule. It is still correct.

4. Clarify the `landskapspotential vind` warning:
   - The warning is useful, but should say that V2's shared establishment-area
     behavior is the reference model while V3 is paused.

5. Leave `script/semi_manual_r9/AGENTS.md` as-is. It governs the Bornholm
   semi-manual R9 workflow and does not conflict with the V2 multiregion path.

Documents/scripts to mark as V3 archive/backlog rather than active direction:

- `docs/archive/v3_backlog_2026-06-24/V3_RENDERED_LAYER_STATUS_CONTRACT_2026-06-09.md`
- `exports/v3_migration/*`
- `exports/v3_geojson/*`
- `scripts/export_trondelag_v3_inventory.py`
- V3-oriented Skaraborg handoffs until Skara/Skaraborg is reintroduced through
  `regions/skara/region.json`.

## V3 Backport Review For Next Session

Before deleting or rewriting V2 UI pieces, review the first V3 migration notes
in `C:/tmp/landskapspotential`. They are useful as a cleanup lens even if V3 is
paused.

Relevant V3 files:

- `C:/tmp/landskapspotential/docs/V3_MIGRATION_PLAN.md`
- `C:/tmp/landskapspotential/docs/V3_PRODUCT_DEFINITION.md`
- `C:/tmp/landskapspotential/docs/V3_HANDOFF_2026-06-08.md`
- `C:/tmp/landskapspotential/docs/V3_MAP_LAYER_CONTRACT.md`
- `C:/tmp/landskapspotential/config/map_layers/v3_core_layers.json`

Important V3 cleanup decisions that may be worth backporting into V2:

- V2 remains the behavioral source of truth for analysis meaning, but the large
  V2 Streamlit file should not be treated as the desired architecture.
- Geocontext factors, geocontext structures and old geocontext landscape types
  should not be standard decision-support layers. Keep them as method/debug or
  backlog material unless stakeholders explicitly need them.
- LABLAB landscape analysis should be the primary landscape basis where data is
  ready; PDF-derived or proxy sources must stay visibly experimental.
- Source and buffer overlays should be advanced/map-inspection controls, not the
  first thing the user sees in standard mode.
- Missing or not-yet-wired layers should not appear as ordinary runtime
  checkboxes. Move them to a "possible layers to add" or backlog section until
  they have real data and runtime behavior.
- Long explanatory method text should move out of the standard view and into
  advanced expanders, documentation or tooltips.
- Technical data-quality/debug status should not be prominent in the main
  end-user UI, but should remain available for validation and troubleshooting.
- The "show proposed establishment area" pattern should be reconsidered: the
  potential establishment area is the core result layer, not a secondary
  technical toggle.
- Social acceptance should remain, but synthetic/placeholder status must be
  clear and advanced scenario-steering controls can be separated from the simple
  acceptance-impact slider.
- Trondelag R8/R9 should remain hidden in the interactive app even if older
  analysis artifacts exist.

Next-session task:

Create a V2 cleanup checklist from these V3 notes. Mark each item as one of:
`keep`, `move_to_advanced`, `move_to_catalog`, `archive/backlog`, or
`remove_after_review`. Do not delete exploratory outputs without explicit user
approval.

## Next Technical Steps

### 1. Validate Parameter/Buffer Catalogs

Create `scripts/validate_region_parameter_buffers.py`.

Minimum checks:

- every active region with `parameter_buffer_catalog` can load it;
- `schema_version`, `region_id`, `native_crs`, `groups` and `app_defaults`
  exist;
- every group has `group_id`, `analysis_kind`, default/min/max/step values and
  readiness;
- every layer has `layer_id`, `group_id`, `layer_key` and readiness;
- Bornholm catalog uses `EPSG:25833`;
- Trondelag catalog uses `EPSG:25832`;
- Trondelag settlement/population group declares the 250 m proxy and dissolved
  polygon behavior;
- no active Trondelag app catalog exposes R8/R9;
- groups marked `not_wired_for_trondelag_prototype` are not treated as active
  defaults.

### 2. Bornholm Parameter/Buffer Audit

Bornholm should be audited first because the region package now has R9 landscape,
display geometries, placement score and synthetic social acceptance, but the
potential manifest is still `dynamic_res10_scaffold`.

For every Bornholm parameter group:

- confirm the source layer exists in the imported V2/R9 package or in the v1
  source package;
- confirm CRS and distance/buffer units;
- decide whether runtime output should be polygon, H3 coverage share or distance
  table;
- confirm default value and UI range;
- mark whether the control is ready for dynamic PEY recalculation.

Decision point:

- Either build a true R9-native Bornholm PEY runtime.
- Or label Bornholm clearly as "R9 display + compatibility-mode PEY" until that
  work is done.

### 3. Move Easy Hardcodings Into Catalogs

Good first moves:

- read default region from `regions/index.json` instead of duplicating
  `DEFAULT_REGION_ID = "trondelag"`;
- add `parameter_buffer_catalog` to legacy alias loading in
  `apps/potential_model/manifests.py`;
- add region UI flags for tutorial availability and scenario-allocation default
  visibility;
- move Trondelag population buffer paths into `regions/trondelag/parameter_buffers.json`;
- move Trondelag fast-distance and rollup strategies into explicit catalog
  fields, while keeping the implementation in code.

### 4. Keep Regional Deviations Explicit

Do not force Bornholm and Trondelag into false parity.

Examples of legitimate deviation:

- Trondelag population uses a 250 m grid/centroid proxy; Bornholm uses different
  population/built-environment sources.
- Trondelag supports R7/R6/R5 in app display; Bornholm supports R9/R8/R7/R6.
- Trondelag reindeer husbandry has no Bornholm equivalent.
- Bornholm R9 has imported v1 provenance; Trondelag is an R7 app bundle with
  proxy status.

Each meaningful deviation should be visible in at least one of:

- `region.json`;
- `parameter_buffers.json`;
- a linked manifest;
- a validation test;
- a handoff note.

### 5. Decide What To Do With V3 Material

Suggested policy:

- keep V3 material in the repo for now;
- add a short archive note explaining that V2 multiregion is the active track;
- stop adding new V3-specific inventories unless explicitly requested;
- harvest useful V3 ideas into V2 under normal docs and scripts rather than
  extending `exports/v3_migration`.

## Proposed Near-Term Commit Sequence

1. Add this roadmap/governance note.
2. Add `scripts/validate_region_parameter_buffers.py`.
3. Update `AGENTS.md` with active-track and catalog-first guidance.
4. Run Bornholm parameter/buffer audit and update
   `regions/bornholm/parameter_buffers.json`.
5. Convert one low-risk hardcoding to catalog-driven behavior, preferably
   default region from `regions/index.json` or tutorial availability.
6. Only after those checks pass: wire app defaults to `parameter_buffers.json`.

## Open Decisions

- Should V2 multiregion become the only active app track, or should V3 remain as
  a named research branch?
- Should Bornholm get true R9-native PEY before stakeholder review, or is a
  compatibility label acceptable for the next demo?
- Should tutorials be region-specific manifests or simple fields in
  `region.json`?
- Should parameter/buffer catalogs become runtime contracts immediately, or go
  through one more Excel/stakeholder review pass first?
