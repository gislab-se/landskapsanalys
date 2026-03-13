# WHEN TO EXTRACT GEOCONTEXT

## Recommendation

Do not extract a new generic `geocontext` repository before the landscape-analysis workflow works end-to-end in `landskapsanalys` and the app-facing flow in `speedlocal` is stable.

Recommended sequence:

1. Finish the Bornholm workflow in the project context where it is being used.
2. Freeze a first reproducible R9 geocontext run.
3. Extract the reusable parts into a new generic repo.
4. Point `landskapsanalys` and `speedlocal` back to that shared engine.

This keeps us from abstracting too early and helps ensure that the future API is based on real needs rather than guesses.

## Why Not Extract First

If we generalize too early, we risk baking Bornholm-specific assumptions into a supposedly generic package, or designing interfaces around temporary workarounds.

Current project work still contains moving parts:

- the R9 layer universe is expanding
- some layers are now split into child categories under parent layers
- the reporting pipeline is still evolving
- the factor-analysis path has not yet been rebuilt for the R9 workflow

That is exactly the stage where a project-specific repo is the right place to learn.

## What "Ready To Extract" Looks Like

The right time to extract is when all of the following are true:

1. We have one accepted R9 feature universe for a first production run.
2. We have a written rule for how parent layers and child layers enter factor analysis.
3. We can reproduce the same outputs from config plus scripts, without notebook-only manual steps.
4. The app uses those outputs successfully.
5. The review report is part of the workflow, not an afterthought.
6. At least a small smoke-test set exists for context generation and factor scoring.

## Best-Practice Path

### Now

Keep working in `landskapsanalys` and `speedlocal`.

Use these repos to answer:

- which features belong in the first R9 factor model
- how child categories should be handled
- what outputs the app really needs
- which parts are generic enough to extract

### Next

Create a new repo named `geocontext` once the R9 workflow is stable enough to define a clean public interface.

That repo should own only the reusable engine, not all Bornholm-specific ETL.

### Optional Provenance Step

If wanted, fork `PonHen/geocontext` for provenance and archival respect, but do not use the fork as the main implementation target unless the goal is to continue that project directly.

The cleaner pattern here is:

- upstream repo remains credited as origin
- optional fork preserves provenance
- new `geocontext` repo becomes the reusable engine

## What Should Stay Outside The Generic Repo

The future generic repo should not initially own:

- local raw-data paths
- project-specific shapefile/QGIS ingestion details
- Bornholm naming conventions
- manual review figures tied to one dataset
- app-specific UI logic

Those belong in project repos such as `landskapsanalys` and `speedlocal`.

## What Should Move Into The Generic Repo Later

The future generic repo should aim to own:

- context-from-feature-matrix generation
- factor-analysis workflow
- clustering workflow
- reusable reporting helpers
- run manifests and provenance logs
- config validation and tests
