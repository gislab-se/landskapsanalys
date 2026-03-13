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

## Provenance and Attribution

This repo builds on the original geocontext idea and early implementation published by Pontus Hennerdal:

- Upstream project: `https://github.com/PonHen/geocontext`

As inspected on 2026-03-13, the upstream GitHub repository presents `geocontext.ipynb` as the core implementation and shows an MIT license. This repo should therefore treat `PonHen/geocontext` as the conceptual and historical origin of the method, while documenting clearly which parts here are new project-specific work:

- Bornholm layer aggregation and QA pipeline
- R8/R9 feature engineering and config files
- Streamlit app integration
- review reports, audits, and migration planning

If code is copied or adapted directly from upstream in the future, keep explicit attribution close to that code and preserve the upstream license notice.

## Related Methodological Reference

A second important methodological reference is the Stockholm University work on a multiscalar typology of residential areas in Sweden. In this project, that work is treated as inspiration and guidance for multiscalar contextualization, factor analysis, and clustering, while remaining explicit that the Bornholm use case is a landscape-analysis adaptation rather than a direct replication.

- Figshare material: `https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826?file=28351917`
- DiVA record: `https://www.diva-portal.org/smash/record.jsf?pid=diva2:1624901`
- Fulltext PDF: `https://www.diva-portal.org/smash/get/diva2:1624901/FULLTEXT01.pdf`

## Geocontext Planning Docs

- `docs/geocontext/GC4_RUNBOOK.md`
- `docs/geocontext/WHEN_TO_EXTRACT_GEOCONTEXT.md`
- `docs/geocontext/GEOCONTEXT_REPO_BLUEPRINT.md`
- `docs/geocontext/GC4_TO_R9_FACTOR_MIGRATION.md`
- `docs/geocontext/LANDSKAPSANALYS_METHOD_REPORT.md`
- `docs/geocontext/landskapsanalys.qmd` (`landskapsanalys.html` after render)
- `docs/geocontext/archive/` (arkiverade rapportversioner, till exempel `landskapsanalys_gc4_res9` och `landskapsanalys_9lager_res9`)
