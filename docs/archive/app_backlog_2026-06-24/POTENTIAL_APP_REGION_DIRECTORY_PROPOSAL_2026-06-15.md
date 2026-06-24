# Potential App Region Directory Proposal

Date: 2026-06-15

## Goal

Make the V2 potential app region-agnostic by moving region-specific configuration,
data references, runtime adapters, and stakeholder-facing landing-page cards into
region packages.

The shared app should consume one selected region package at runtime. Trondelag
must remain available as the current default pilot, but stakeholders should be
able to replace it or add new regions such as municipalities without changing
shared app code.

## Current State

The app already has a partial region abstraction:

- `streamlit_app.py` starts `potential_app.py`.
- Region manifests are loaded by `apps/potential_model/manifests.py`.
- Existing region manifests live in `apps/potential_model/manifests/regions/`.
- `bornholm.json` and `trondelag.json` are active; `vara.json` is planned.
- Linked manifests already separate landscape, potential, scenario, and social
  acceptance inputs.
- `apps/potential_model/region_status.py` validates linked manifests and H3
  display geometry.

The abstraction is not complete:

- `potential_app.py` still forces `DEFAULT_REGION_ID = "trondelag"` and
  `_active_region()` always loads Trondelag.
- The landing/selection flow does not exist yet, even though `list_regions()`
  is available.
- Acceptance registries are selected through a Trondelag special case in
  `apps/acceptance_model/layers.py`.
- Several Trondelag-specific runtime adapters remain in `potential_app.py`,
  especially population/settlement buffer handling from the 250 m proxy.
- Tests currently assert the fixed Trondelag behavior in
  `scripts/validate_potential_region_contract.py`.

## Existing Regional Differences To Preserve

Do not force false parity between regions.

Bornholm:

- Native CRS: `EPSG:25833`.
- Render/export CRS: `EPSG:4326`.
- Current source/default analysis is finer than Trondelag.
- Existing region manifest exposes H3 R6/R7/R8/R9/R10.

Trondelag:

- Native CRS: `EPSG:25832`.
- Render/export CRS: `EPSG:4326`.
- Interactive app must expose only H3 R7/R6/R5.
- R8/R9 must not appear in the interactive app.
- Current display counts are R7 `13735`, R6 `2163`, R5 `365`.
- Population/settlement uses a 250 m grid/centroid proxy.
- User-facing population and settlement buffers should be dissolved polygon
  buffers from the proxy, not H3 buffer overlays.
- Reindeer husbandry is a Trondelag-specific controller.
- PDF-derived landscape type outputs are experimental and must not become base
  app data without the documented review checks.

Skaraborg/Skara/Vara:

- The repo currently has `vara` as a planned region manifest, not a finished
  Skaraborg runtime.
- A landing card can exist as planned/missing, but the app should not synthesize
  final H3, energy, or potential data for it.

## Recommended Directory Structure

Use one region package per selectable region:

```text
regions/
  index.json
  trondelag/
    region.json
    manifests/
      landscape.json
      potential.json
      scenarios.json
      social_acceptance.json
      acceptance_registry.json
      layer_catalog.json
    data/
      h3/
      landscape/
      acceptance/
      energy/
      runtime/
    scripts/
      render_population_buffer.R
    docs/
      handoff.md
      provenance.md
  bornholm/
    region.json
    manifests/
      landscape.json
      potential.json
      scenarios.json
      social_acceptance.json
      acceptance_registry.json
      layer_catalog.json
    data/
      h3/
      landscape/
      acceptance/
      energy/
    docs/
      handoff.md
      provenance.md
  skara/
    region.json
    docs/
      data_requirements.md
```

`regions/index.json` should define card order and which region packages are
published in the landing page:

```json
{
  "schema_version": "2026-06-15",
  "default_region_id": "trondelag",
  "regions": [
    "trondelag",
    "bornholm",
    "skara"
  ]
}
```

The app can also scan `regions/*/region.json`, but an index is useful for
stakeholder deployments because it controls order and can hide draft/private
packages without deleting files.

## Proposed `region.json`

The region manifest should be the single entry point for both the landing page
and the analysis view.

```json
{
  "schema_version": "2026-06-15",
  "region_id": "trondelag",
  "display_name": "Trondelag",
  "country": "Norway",
  "status": "active",
  "data_status": "proxy",
  "landing_card": {
    "title": "Trondelag",
    "subtitle": "Regional pilot for solar and wind potential",
    "description": "Large-region potential view using R7/R6/R5 display data and documented proxy layers.",
    "badge": "Active pilot",
    "sort_order": 10,
    "enabled": true
  },
  "crs": {
    "native": "EPSG:25832",
    "web": "EPSG:4326"
  },
  "map": {
    "default_center": [63.43, 10.39],
    "default_zoom": 6
  },
  "h3": {
    "available_display_resolutions": [7, 6, 5],
    "default_analysis_resolution": 7,
    "default_display_resolution": 7,
    "display_geometries": {
      "7": "data/h3/trondelag_h3_r7.geojson",
      "6": "data/h3/trondelag_h3_r6.geojson",
      "5": "data/h3/trondelag_h3_r5.geojson"
    },
    "display_geometry_counts": {
      "7": 13735,
      "6": 2163,
      "5": 365
    }
  },
  "manifests": {
    "landscape": "manifests/landscape.json",
    "potential": "manifests/potential.json",
    "scenarios": "manifests/scenarios.json",
    "social_acceptance": "manifests/social_acceptance.json",
    "acceptance_registry": "manifests/acceptance_registry.json",
    "layer_catalog": "manifests/layer_catalog.json"
  },
  "runtime_adapters": {
    "population_buffer": {
      "kind": "dissolved_polygon_from_250m_centroid_proxy",
      "script": "scripts/render_population_buffer.R",
      "source": "data/acceptance/analysis_rds/population_points.rds",
      "cache_dir": "data/runtime/population_buffers",
      "native_crs": "EPSG:25832",
      "render_crs": "EPSG:4326",
      "ui_note": "Population uses a 250 m grid/centroid proxy, not individual population points."
    }
  },
  "constraints": [
    "Do not expose H3 R8/R9 in the interactive app.",
    "Render population/settlement buffers as dissolved polygons from the 250 m proxy.",
    "Treat PDF-derived landscape types as experimental unless handoff checks pass."
  ],
  "runtime_note": "Trondelag uses proxy/modelled inputs for some layers. Energy scenarios still use placeholder data until regional model outputs exist."
}
```

Recommended compatibility aliases during migration:

- `native_crs` can temporarily mirror `crs.native`.
- `web_crs` can temporarily mirror `crs.web`.
- `available_h3_resolutions` can temporarily mirror
  `h3.available_display_resolutions`.
- Existing linked manifest keys can remain at the top level until all loaders
  understand `manifests.*`.

## Landing Page Data Flow

1. `main()` sets page config and language.
2. The app loads `regions/index.json` or scans `regions/*/region.json`.
3. If no selected region exists in session/query params, render the landing page.
4. Region cards are generated from `region.json.landing_card`.
5. Active cards call `select_region(region_id)`.
6. Planned/missing cards are visible but disabled or open a data-status view.
7. `select_region()` sets `st.session_state[REGION_SELECT_KEY]` and
   `st.query_params["region"]`.
8. The analysis view loads that region package through one region loader.
9. A header/sidebar control lets the user return to the landing page or switch
   region.

Suggested route/query behavior:

```text
/?view=landing
/?region=trondelag
/?region=bornholm
/?region=skara
```

The landing page should describe the app briefly, then show cards. The cards
must be data-driven; adding `regions/my_municipality/region.json` plus an index
entry should be enough to expose a new card.

## What Should Move Into Region Packages

Move or mirror these into `regions/<region>/`:

- Region manifest.
- Landscape manifest and landscape source paths.
- Potential model manifest and technology rules.
- Scenario/energy model manifest.
- Social acceptance manifest.
- Acceptance registry and source layer catalog.
- Region-specific H3 display geometries and counts.
- Region-specific runtime frame manifests.
- Region-specific documentation/handoff/provenance notes.
- Region-specific runtime adapters such as Trondelag population proxy buffering.

Keep these shared:

- `potential_app.py` app shell and shared UI components.
- `apps/potential_model/*` shared loaders, potential logic, energy modeling, map
  rendering, and region status validation.
- `apps/acceptance_model/*` shared registry parsing, layer semantics, runtime
  geometry wrapper, and i18n.
- Common result-layer contracts in `exports/v3_migration/`.
- Tests that validate shared behavior across all active region packages.

## Migration Plan

1. Add a region package loader that supports both legacy manifests and the new
   `regions/<region>/region.json` shape.
2. Add `landing_card` metadata to existing `bornholm`, `trondelag`, and
   `vara/skara` manifests without changing analysis behavior.
3. Implement a landing page in `potential_app.py` using `list_regions()`.
4. Replace `_active_region()` fixed loading with query/session-selected loading,
   keeping Trondelag as the default fallback only when no region is selected.
5. Reset only region-scoped session keys when switching region; keep language and
   generic display preferences.
6. Move acceptance registry selection from `apps/acceptance_model/layers.py`
   special cases to the selected region manifest.
7. Move Trondelag population-buffer paths and script references into the
   Trondelag region package, then make the app call a generic
   `population_buffer_adapter` when present.
8. Move current flat manifests into `regions/<region>/manifests/`, leaving
   compatibility stubs or updating paths in one controlled change.
9. Update tests:
   - fixed-Trondelag contract becomes default-region/landing contract;
   - Bornholm and Trondelag are validated independently;
   - Trondelag R7/R6/R5 and population proxy behavior remain explicit;
   - planned Skara/Skaraborg card is visible but not runtime-ready.
10. Add a stakeholder guide: "How to add a region card and package."

## Minimal Safe First Code Step

The safest implementation increment is:

- extend `apps/potential_model/manifests.py` with `regions_root()` and support
  for `regions/*/region.json`;
- add `landing_card` fields to current region manifests or create thin region
  package wrappers that point back to legacy manifests;
- add `_render_region_landing()` and selected-region loading in `potential_app.py`;
- keep all existing Trondelag paths unchanged for the first pass.

That gives stakeholders the landing page and region cards before any data moves.

## Risks And Open Questions

- Existing tests currently expect fixed Trondelag loading; they must be updated
  with the landing-page change.
- Moving large generated GIS data into region packages may be undesirable. Keep
  scripts, manifests, review tables, and documentation in git; keep large GPKG,
  TIF, and generated HTML out unless explicitly justified.
- Some paths point to external pipeline roots. Region manifests should allow
  path tokens such as `${REGIONAL_LANDSCAPE_PIPELINE_ROOT}`.
- "Skara", "Skaraborg", and "Vara" need a naming decision. The current app
  manifest says `vara`; the landing card could display `Skara/Skaraborg` while
  using a stable `region_id` such as `skara` or `skaraborg`.
- The current `app.py` is an older Bornholm/Geocontext view. It should not block
  the potential app migration, but it should be documented as outside this
  region-directory refactor unless the user wants it folded in later.
