# Synthetic Social Acceptance Handoff - 2026-05-19

This note documents the temporary social-acceptance test layer for the v2 potential app.

## Scope

- Region manifests now point to optional social-acceptance manifests.
- Bornholm is the reference implementation and uses H3 R10.
- Trondelag mirrors the Bornholm flow and uses H3 R7 because the light Trondelag app bundle is R7.
- The app exposes three discrete scenarios: low, medium, high.
- Values are synthetic test data in the range 0-1 with max three decimals.

## Files

- Generator: `script/potential/build_synthetic_social_acceptance.py`
- Bornholm manifest: `apps/potential_model/manifests/social_acceptance/bornholm_synthetic_acceptance_v0.json`
- Trondelag manifest: `apps/potential_model/manifests/social_acceptance/trondelag_synthetic_acceptance_v0.json`
- Bornholm CSV: `docs/geocontext/potential_framework/data/social_acceptance/bornholm_synthetic_social_acceptance_r10.csv`
- Trondelag CSV: `docs/geocontext/potential_framework/data/social_acceptance/trondelag_synthetic_social_acceptance_r7.csv`

## Synthetic Logic

The generator uses existing landscape factors and semantic roles as proxies. It lowers acceptance around settlement/built-structure signals and sensitive landscape/protection/relief signals, then adds local-benefit, self-interest and irregular human-preference terms. The low and high scenarios shift the same base logic down/up.

This is not IVL research data and must not be interpreted as measured social acceptance.

## Validation

Run:

```powershell
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\validate_potential_region_contract.py
```

The validation checks region-switch reset behavior, synthetic flags, expected H3 resolution, one row per source hex, scenario order, value range and max three decimals.
