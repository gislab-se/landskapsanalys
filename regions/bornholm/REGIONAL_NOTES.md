# Bornholm Regional Notes

## Active App Contract

Bornholm is an active regional app package. It uses the DAGI Landsdel landmask,
native CRS `EPSG:25833`, and H3 R9 as the analysis baseline. The interactive app
may display R9, R8, R7, and R6 according to `region.json`.

## Regional Exceptions

### Coastal And Strand Protection

What differs:

- Bornholm has reviewed coastal/strand-protection source layers wired through the
  acceptance registry and `parameter_buffers.json`.
- `strand_protection` is treated as a hard coastal/strand-protection constraint.
- For wind establishment, H3 cells intersecting active strand protection are not
  considered wind-suitable in the shared establishment layer, even when a partial
  wind potential area remains inside the H3 cell.

Why:

- The source is a regional Danish planning/legal constraint with reviewed
  Bornholm coastal QA.
- Without the establishment-level intersection rule, users can read coastal cells
  as wind-suitable because H3 area shares may remain positive even where
  strand-protection overlap should be a clear no-go signal.

Source and catalog locations:

- `regions/bornholm/parameter_buffers.json`
- `apps/acceptance_model/registry_bornholm.json`
- `docs/geocontext/acceptance_framework/data/prototype_assets_dagi_landsdel/`

How to remove or generalize:

- Generalize this behavior when other regions have reviewed equivalent
  coastal/strand-protection source layers and a shared legal/planning semantic.
- Until then, do not force this Bornholm behavior onto regions where coastal data
  is missing or only a placeholder.

## Historical/Provenance Notes

Older R10-derived material remains source/provenance only. The active app
contract is the R9 DAGI Landsdel baseline described in `region.json`.
