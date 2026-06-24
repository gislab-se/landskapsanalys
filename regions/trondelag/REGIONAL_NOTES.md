# Trondelag Regional Notes

## Active App Contract

Trondelag is an active regional app package. It uses native CRS `EPSG:25832`,
default H3 R7 analysis/display, and R6/R5 rollups for lighter overview display.
The interactive app must not expose Trondelag R8/R9.

## Regional Exceptions

### Population And Settlement Proxy

What differs:

- Trondelag population currently uses a 250 m population-grid/centroid proxy, not
  individual population points.
- User-facing settlement/population buffers should render as dissolved polygon
  proxy buffers, not H3 buffer overlays.
- Small-scale solar uses the population count value in each 250 m grid cell and
  aggregates that to H3, so the panel-area setting is still per person.

Why:

- The available regional population source is grid-based.
- Showing this as individual points would misrepresent the data.

Source and catalog locations:

- `regions/trondelag/parameter_buffers.json`
- `docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/`

How to remove or generalize:

- Replace or supplement the proxy when reviewed individual point/building-level
  population data is available.
- Keep the UI explicit about the proxy until that happens.

### H3 Display Resolution

What differs:

- Trondelag exposes R7, R6, and R5 only in the app.
- R8/R9 material should not be exposed in the interactive app.

Why:

- The active reviewed app bundle is R7 with rollups. Higher-resolution outputs
  are not part of the current interactive contract.

Source and catalog locations:

- `regions/trondelag/region.json`
- `docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/`

How to remove or generalize:

- Only expose higher resolutions after a reviewed data package, performance
  budget, and region contract tests exist for them.

### Placeholder Energy/Scenario Data

What differs:

- Trondelag currently uses placeholder energy/scenario inputs until regional data
  is supplied.

Why:

- EML or an equivalent Norwegian regional energy source has not yet supplied the
  final Trondelag inputs.

Source and catalog locations:

- `regions/trondelag/region.json`
- `apps/potential_model/manifests/scenarios/trondelag_scenarios_placeholder.json`

How to remove or generalize:

- Replace the placeholder once reviewed regional energy inputs exist and contract
  tests pass.
