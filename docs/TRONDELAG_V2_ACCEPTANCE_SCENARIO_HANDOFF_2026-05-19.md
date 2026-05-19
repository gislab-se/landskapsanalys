# Trondelag V2 Acceptance Scenario Handoff - 2026-05-19

This handoff captures the current stable state of the Trondelag-focused v2 potential app after the social-acceptance UI and scenario-priority work.

## Repository State

- Worktree: `C:\tmp\landskapsanalys-v2-multiregion`
- Branch: `potential-v2-multiregion`
- App entrypoint: `streamlit_app.py`, with most app logic in `potential_app.py`
- Current v2 direction: Trondelag-focused app. Do not reintroduce region switching or Bornholm default-reset behavior in v2.
- Root `AGENTS.md` still says "Bornholm First". Use Bornholm as a behavioral reference, but keep v2 as the Trondelag app unless the user explicitly changes strategy.

## Recent Stable Commits

- `b457dae Add acceptance-adjusted potential column`
- `1e5dd53 Prioritize scenario hexes by social acceptance`

## Current Behavior

- Zoom-adaptive H3 display is active by default for Trondelag and uses R7/R6/R5.
- Zoom thresholds are kept at 30 km, 50 km and 100 km.
- Social acceptance uses synthetic H3 R7 test data with rollups to R6 and R5.
- No separate acceptance map layer was added. Acceptance affects existing establishment/scenario behavior.
- `Acceptanspåverkan` tints the existing `Potentiell etableringsyta` toward red where acceptance is low.
- The right-panel table has a derived column, `potential efter acceptanspåverkan`, while the original columns remain unchanged.
- `Acceptansstyrning av scenariohexar` is a separate slider. At 0%, scenariohex allocation follows the existing technical priority. At higher values, high-acceptance cells can be prioritized earlier.
- The small darker scenariohexes represent proposed scenario allocation, not existing built energy infrastructure.

## Relevant Files

- App logic: `potential_app.py`
- Contract validation: `scripts/validate_potential_region_contract.py`
- Parity validation: `scripts/validate_potential_region_parity.py`
- Synthetic acceptance manifest: `apps/potential_model/manifests/social_acceptance/trondelag_synthetic_acceptance_v0.json`
- Synthetic acceptance data: `docs/geocontext/potential_framework/data/social_acceptance/trondelag_synthetic_social_acceptance_r7.csv`
- Earlier acceptance-data handoff: `docs/SYNTHETIC_SOCIAL_ACCEPTANCE_HANDOFF_2026-05-19.md`

## Validation Commands

```powershell
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe -m py_compile potential_app.py scripts\validate_potential_region_contract.py
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\validate_potential_region_contract.py
C:\Users\henri\AppData\Local\Programs\Python\Python311\python.exe scripts\validate_potential_region_parity.py
```

Latest known results:

- Contract validation: 66 passed, 0 blockers.
- Parity validation: 92 passed, 0 blockers.

## Suggested Next Steps

1. Test in Streamlit Cloud that `Acceptansstyrning av scenariohexar` triggers recalculation and visibly moves scenariohex priority.
2. Consider clearer labels:
   - `Visuell acceptanspåverkan`
   - `Acceptans i scenariofördelning`
3. Add a right-panel metric for average acceptance of selected scenariohexes, so the user can see whether the scenario allocation improves when the slider increases.
4. Add a regression test that `Acceptansstyrning av scenariohexar = 0%` gives the exact same scenario allocation as the baseline.
5. If the user likes the interaction, consider showing a small note when scenariohex priority changes, for example "Scenariofördelningen prioriterar nu högre social acceptans."

## Caution

- Leave existing untracked exploratory/generated material alone unless the user explicitly asks for cleanup.
- Do not commit large generated GIS outputs without documenting why.
- Keep acceptance behavior as a soft weighting. Avoid turning social acceptance into a hard yes/no filter unless the user explicitly asks for that.
