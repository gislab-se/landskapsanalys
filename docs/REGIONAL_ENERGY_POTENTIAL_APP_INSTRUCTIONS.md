# Regional Energy Potential App Instructions

Last updated: 2026-04-15

## Purpose

This document defines the target architecture for the next version of the energy app. The existing wind acceptance app must remain intact. The new app should become a regional, version-aware **solar and wind potential** app that can eventually sit beside or replace the current SpeedLocal regional Streamlit delivery.

The app must support:

- multiple regions with different coordinate systems, analysis scales and available data
- energy-model scenarios from external modelers
- detailed vector potential surfaces for solar and wind
- H3 rollups of potential and landscape-analysis outputs at multiple resolutions
- evolving landscape-analysis methods without hard-coding the current Bornholm v4 factors or clusters

## Rewritten Target Outcome

The final product should be a single regional Streamlit app for comparing energy scenarios, renewable-energy potential and landscape-analysis context across three pilot regions:

- **Trondelag, Norway**
- **Vara, Sweden**
- **Bornholm, Denmark**

Each region can have different source data, CRS, scale and analysis resolution. Trondelag may operate closer to regional overview scale around 1:1,000,000, Bornholm closer to detailed local scale around 1:25,000, and Vara between those. These differences should be handled through region-specific manifests and data products, not by creating separate app logic for each region.

The app should contain three main analytical modules:

1. **Energy Scenarios**
   - Show scenario outputs from the relevant energy modeler for the selected region.
   - Support at least three scenario levels: **high**, **medium** and **low**.
   - Treat scenarios as region-specific model outputs, because each region may have different modeling assumptions, formats and input data.

2. **Solar and Wind Potential**
   - Present **Solpotential** and **Vindpotential** with consistent terminology.
   - Support detailed vector outputs that can point to candidate areas relatively precisely.
   - Support H3-aggregated potential outputs at multiple resolutions for less exact regional comparison.
   - Support parent-to-child and child-to-parent rollups, so coarse and fine H3 products stay connected.

3. **Landscape Analysis**
   - Show the current landscape-analysis result for the selected region.
   - Allow switching H3 resolution where rollup products exist.
   - Show both clusters and factors, but read factor labels, cluster labels and interpretations from versioned landscape-analysis manifests.
   - Avoid assuming that the Bornholm v4 factor structure is permanent.

## One App, Not Three Separate Apps

The recommended target is **one app with a top-level region selector**, not three independent apps.

Reason:

- users need to compare regions through the same conceptual interface
- scenarios, potential and landscape analysis are shared app modules
- the differences between regions are primarily data/configuration differences
- one app makes it easier to keep terminology, legends and export behavior consistent

The app can use pages or tabs, but the region should be global app state. A good structure is:

- region selector in the sidebar or page header
- main navigation: `Scenarios`, `Potential`, `Landscape Analysis`, `Data and Method`
- module-specific controls inside each page

Separate apps should only be considered if deployment constraints force them, for example severe performance limits, private data access differences, or separate public/internal releases. Even then, they should share the same codebase and data contracts.

## Core Architecture Rule

Do not put region-specific assumptions directly into app code.

The app should read from versioned manifests:

- `RegionManifest`
- `ScenarioManifest`
- `LandscapeAnalysisManifest`
- `PotentialModelManifest`

The app code should know how to render a region, scenario, landscape analysis or potential layer. It should not know that a specific Bornholm factor is `F1`, that one cluster means "Flygsands- och laglanta kuststrak", or that a region uses a particular CRS.

## Region Manifest

Each region needs a manifest that describes its spatial and display assumptions.

Recommended fields:

```json
{
  "region_id": "bornholm",
  "display_name": "Bornholm",
  "country": "Denmark",
  "native_crs": "EPSG:25833",
  "web_crs": "EPSG:4326",
  "default_map_center": [55.14, 14.92],
  "default_zoom": 9,
  "nominal_scale": "1:25000",
  "available_h3_resolutions": [6, 7, 8, 9],
  "default_h3_resolution": 8,
  "scenario_manifest": "path/to/scenario_manifest.json",
  "landscape_manifest": "path/to/landscape_manifest.json",
  "potential_manifest": "path/to/potential_manifest.json"
}
```

CRS handling must be explicit:

- analysis should use the region's appropriate projected CRS
- web maps should render in WGS84
- H3 products should be generated from WGS84 geometries or from a controlled conversion step
- the app must not assume that all regions share Bornholm's CRS, scale or H3 resolution

## Scenario Manifest

Scenarios should be modeled as region-specific outputs from external energy modelers.

Recommended fields:

```json
{
  "region_id": "bornholm",
  "modeler": "modeler_or_team_name",
  "scenario_set_id": "bornholm_energy_scenarios_2026_01",
  "scenario_levels": ["low", "medium", "high"],
  "layers": [
    {
      "scenario": "medium",
      "technology": "combined",
      "path": "path/to/medium_scenario.gpkg",
      "layer": "medium_scenario",
      "native_crs": "EPSG:25833",
      "description": "Medium regional energy scenario."
    }
  ]
}
```

The app should not require all regions to have identical scenario schemas. Instead, each scenario manifest should define the available layers and attributes.

## Landscape Analysis Manifest

The landscape-analysis method will continue to evolve. The app must treat landscape analysis as a versioned input product.

Recommended fields:

```json
{
  "analysis_id": "landskapsanalys_v3_2_contourterrain68_res9",
  "display_name": "Landskapsanalys Bornholm v4",
  "region_id": "bornholm",
  "hex_gpkg": "path/to/hex.gpkg",
  "cluster_profile": "path/to/cluster_profile.csv",
  "factor_scores": "path/to/factor_scores.csv",
  "available_h3_resolutions": [6, 7, 8, 9],
  "default_h3_resolution": 8,
  "factor_labels": {
    "F1": "Flygsands- och laglanta kustmiljoer"
  },
  "cluster_labels": {
    "1": "Tatorts- och verksamhetskarnor"
  },
  "semantic_roles": {
    "coastal_lowland": ["F1", "F5"],
    "steep_valley_relief": ["F2"],
    "protected_forest_habitat": ["F3"],
    "settlement_built_structure": ["F4"]
  }
}
```

Potential models should refer to `semantic_roles`, not directly to factor IDs. If the next landscape-analysis version changes the factor structure, the manifest changes while the app remains stable.

## Potential Model Manifest

Potential should be technology-specific but structurally consistent between solar and wind.

Recommended fields:

```json
{
  "region_id": "bornholm",
  "potential_model_id": "bornholm_energy_potential_2026_01",
  "technologies": ["solar", "wind"],
  "vector_layers": [
    {
      "technology": "solar",
      "potential_class": "combined",
      "path": "path/to/solar_potential_vectors.gpkg",
      "layer": "solar_potential",
      "native_crs": "EPSG:25833"
    }
  ],
  "h3_rollups": [
    {
      "technology": "solar",
      "h3_resolution": 7,
      "source_resolution": 8,
      "path": "path/to/solar_potential_res_7_rollup_from_res_8.gpkg",
      "summary_path": "path/to/solar_potential_res_7_rollup_from_res_8_summary.csv"
    }
  ]
}
```

The app should support both:

- precise vector layers for detailed candidate-area review
- H3 rollups for regional comparison and scale-aware summaries

## H3 Resolution And Rollup Rules

H3 outputs should be precomputed and versioned by the pipeline. The app should select among available products; it should not perform heavy rollups during normal interaction.

Rules:

- every rollup product must record source resolution and target resolution
- every rollup product must include a summary table
- parent-to-child and child-to-parent logic must be explicit
- map controls should only show H3 resolutions that exist for the selected region and analysis version
- the UI should make clear that coarser H3 layers are less spatially precise than detailed vector layers

Example naming pattern:

```text
<region>_<product>_res_<target>_rollup_from_res_<source>.gpkg
<region>_<product>_res_<target>_rollup_from_res_<source>_summary.csv
```

## Solar Potential Logic

Solar potential should be inspired by `Sol over land - Guide til planlaegning af solenergi`, but translated into each region's own landscape-analysis structure.

The guide's landscape types should not be copied directly into Bornholm's cluster names. Instead, create a crosswalk layer such as `solar_landscape_capacity`.

For Bornholm v4, a reasonable starting crosswalk is:

| Bornholm landscape-analysis type | Solar interpretation |
| --- | --- |
| Urban and business cores | Low for large parks; possible relevance for smaller technical or grid-adjacent sites |
| Everyday landscape with mixed background character | Main candidate matrix; must be split by openness, agriculture, relief and settlement pressure |
| Aeolian sand and lowland coastal belts | Restrictive coastal and lowland sensitivity |
| Steep relief and valley-incised interior | Low or conditional potential; small well-designed sites only |
| Forested protected interior and habitat cores | Very low potential or exclusion |

More generally:

```text
Solar potential =
  landscape capacity
+ grid / infrastructure feasibility
- protected nature and legal restrictions
- coastal and view sensitivity
- settlement and recreation sensitivity
```

## Wind Potential Logic

The existing wind app is useful, but the new app should not preserve the old "acceptance" model unchanged. It should evolve into **wind potential**.

Wind potential should distinguish:

- hard exclusions
- distance and settlement conflicts
- technical feasibility
- grid and infrastructure proximity
- landscape sensitivity
- scenario relevance
- remaining or ranked potential

Suggested structure:

```text
Wind potential =
  technical feasibility
+ grid / infrastructure feasibility
- hard restrictions
- settlement and safety distances
- landscape sensitivity
- coastal / aviation / nature conflicts
```

The old wind app may still provide the first geometry-first implementation pattern, but labels, outputs and summary metrics should move from "acceptance" to "potential".

## UI Guidance

Recommended user flow:

1. Select region.
2. Start in the combined potential view.
3. Toggle default and user-built solar/wind potential layers.
4. Choose H3 rollup and opacity for all active hex layers in the map-control row.
5. Move to the solar or wind builder view to adjust assumptions.
6. Return to the combined potential view to compare default and user-built outputs.

The map should clearly distinguish:

- detailed vector potential
- H3 aggregated potential
- landscape clusters
- landscape factors
- scenario outputs
- restrictions and explanatory overlays

## Interactive Potential Builders

The app should separate results from model-building:

- `Samlad potential` is the comparison view. It shows the main map and lets users toggle default/user-built solar and wind potential, landscape clusters, and landscape factors.
- `Bygg solpotential` is a model workshop for solar. It exposes user-facing sliders for the assumptions that increase or reduce solar potential.
- `Bygg vindpotential` is a model workshop for wind. It follows the wind-acceptance app's interaction pattern, but translates it into potential terminology and H3 score outputs.

Builder outputs should be stored in session state and become available as toggleable layers in the combined view. Default outputs must remain available and resettable.

All H3 hex layers should share the same rollup control in the current map view. The H3 rollup selector belongs next to the opacity slider so users understand that resolution and transparency are display controls for the active hex layers.

Builder previews and saved potentials must be separate states. Slider changes in a builder view update an unsaved preview. The combined map may only consume a user-built potential after the user has clicked `Spara solpotential` or `Spara vindpotential`.

If a user toggles a custom potential in `Samlad potential` before saving it, the app should show a red warning and provide a direct navigation action to the correct builder view.

Each builder view should include bottom actions:

- `Spara solpotential` or `Spara vindpotential`
- `Gå tillbaka till huvudkartan`

Potential layers should support display modes:

- `Hexagon`
- `Vektor`
- `Båda`

Hexagon mode is the current fully working display product. Vektor mode should remain a clear placeholder until detailed vector potential layers are connected through manifests. When both modes are active, vector and H3 should eventually be visible together.

For the first implementation:

- solar builder sliders can directly modify the manifest-driven solar score terms
- wind builder sliders can start as a landscape-role score proxy while the geometry-first wind-acceptance runtime is migrated
- missing or approximate data should be labelled clearly rather than hidden
- detailed wind geometry and source-layer selections should be added incrementally from the old wind app

## Data And Performance Guidance

Use lazy loading and region-specific caching. Large regions such as Trondelag must not force the app to load Bornholm and Vara data at startup.

Recommended approach:

- load only the selected region's manifests
- load only the selected module's data
- simplify or tile large vector layers before publication
- use precomputed H3 products for fast map display
- keep heavy geoprocessing in the pipeline, not in the Streamlit runtime

## Display Clipping

H3 products may contain full hexagons that extend outside the land area. For public-facing maps, display geometries should be clipped or filtered against a region-level land mask so users do not read offshore cells as real potential areas.

Preferred mask hierarchy:

1. Maintained municipal or regional land polygon with coastline and islands.
2. Authoritative coastline-derived land polygon.
3. Stable geological or topographic land-coverage polygon when no clean administrative land polygon is available.

For Bornholm v0, `data/raw/manual_extra_layers/shape format/Prekvart_Bornholm.shp` is used as a pragmatic landmask because it covers Bornholm's landmass, is small enough for preprocessing, and is independent of the current landscape-analysis clusters. This should stay manifest-driven and can be replaced by a better regional boundary without changing app code.

## Implementation Instructions

1. Keep the existing wind app intact.
2. Create a new app version for regional energy potential.
3. Replace "acceptance" terminology with "potential" in the new app only.
4. Move reusable map and layer-loading code into shared modules only when it reduces duplication.
5. Do not hard-code Bornholm v4 factor IDs, cluster labels or paths in app logic.
6. Add manifest readers before adding more technology-specific UI.
7. Add solar and wind as technology modules under the same potential framework.
8. Add region selection before trying to generalize every map interaction.
9. Treat CRS, scale and H3 resolution as data described by manifests.
10. Treat landscape-analysis labels and semantic roles as versioned interpretation products.

## Open Decisions

These decisions should be resolved before full implementation:

- exact storage location for regional manifests
- final naming convention for potential GPKG layers and H3 rollups
- whether scenario outputs should be converted to a common schema or rendered as modeler-specific layers
- minimum H3 resolutions per region
- which detailed vector layers are safe and performant enough for public Streamlit deployment
- how to expose uncertainty and method-version differences to users

## Session Notes

2026-04-15:

- A Streamlit navigation error occurred after clicking `Gå tillbaka till huvudkartan` from a builder view:
  `st.session_state.active_view cannot be modified after the widget with key active_view is instantiated`.
- Cause: the app tried to mutate the `active_view` widget state after the segmented-control widget had already been created in the same run.
- Follow-up: navigation between builder views and the combined map should use widget callbacks or another state key that is not owned by the view selector widget.
