# landskapsanalys

Standalone Streamlit app for geocontext-based landscape analysis on Bornholm.

## Included assets

- `data/gc4/bornholm_points_with_context_gc4.csv`
- `data/gc4/bornholm_r8_factor_scores_gc4.csv`
- `docs/geocontext/bornholm_37_lager_svenska.csv`
- `script/config/bornholm_r8_geocontext_feature_map.csv`
- `script/config/bornholm_r8_geocontext_scoring.csv`
- `data/raw/lablab/SpeedLocal/Bornholm/*` (validation reference material)

## Run locally (Windows, using project venv)

```powershell
cd C:\gislab\speedlocal
.\.venv\Scripts\python.exe -m pip install -r external\landskapsanalys\requirements.txt
.\.venv\Scripts\python.exe -m streamlit run external\landskapsanalys\app.py
```

## Purpose

This repo isolates landscape and geocontext logic from the energy app, so geocontext assumptions can be reviewed independently.
