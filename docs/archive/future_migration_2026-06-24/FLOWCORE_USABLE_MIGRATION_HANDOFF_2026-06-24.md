# Flowcore/Usable Migration Handoff

Date: 2026-06-24

## Purpose

This note records the migration posture for the regional potential app if the
long-term hosting target changes from the current GitHub-based setup to
Flowcore/Usable.

Use this handoff after the application is functionally complete and stable
across the intended regions. At the time of writing, the app is still an active
development workspace with app code, GIS analysis outputs, review packages,
runtime assets and exploratory material in the same repository.

## Short Answer

Yes: build and stabilize the application first, then evaluate the concrete
migration path.

The migration should not drive major implementation decisions today unless a
decision is already good engineering for the app itself. The useful preparation
now is to keep the app portable, manifest-driven and explicit about runtime
data. The platform-specific migration work should wait until the app behavior,
region scope and data package are stable.

## What Changes Today

Very little should change in current feature work.

Do now:

- keep region behavior manifest/catalog-driven where practical;
- keep Bornholm, Trondelag and Skara/Skaraborg data differences explicit;
- avoid new absolute local paths such as `C:/...` and `D:/...` in app runtime
  code;
- keep generated GIS outputs out of the app runtime package unless they are
  required for the deployed app;
- document new runtime data files in manifests or handoff notes;
- keep heavy preprocessing in reproducible scripts, not hidden app-side
  assumptions;
- keep validation scripts runnable for each region;
- separate writable runtime/cache outputs from checked-in documentation folders
  when touching that part of the code.

Do not do now:

- pause app completion to redesign for Flowcore/Usable before the target
  deployment contract is known;
- move all data to a new storage model before the final runtime data inventory
  is known;
- add Flowcore/Usable-specific branches in app logic just in case;
- force all regions to share identical data flows for migration convenience;
- commit large generated GIS files only because they might be useful later.

## Current Migration Assumption

The app should be treated as two deployable surfaces:

1. Static report/site content under `docs/geocontext`.
2. The interactive Streamlit potential app.

The static site is likely a lower-risk migration because the current GitHub
Pages workflow publishes selected files from `docs/geocontext`.

The interactive app is a medium-risk migration until proven otherwise because
it depends on Python, Streamlit, local runtime data, geospatial packages,
DuckDB/Excel inputs, external map/CDN assets and some R-based geometry runtime
behavior.

## Completion Criteria Before Migration Review

Before doing the final migration assessment, the app should have:

- completed intended functionality for all target regions;
- clear region status for Bornholm, Trondelag and Skara/Skaraborg;
- passing region contract tests for active regions;
- independent validation for Bornholm and Trondelag behavior;
- no unintended exposure of unsupported Trondelag R8/R9 interactive layers;
- clear handling of Trondelag population/settlement buffers as dissolved
  polygon buffers from the 250 m grid/centroid proxy;
- resolved or explicitly accepted placeholder status for regional energy data;
- a final runtime data inventory per region;
- a known start command and dependency list;
- a writable runtime/cache directory outside the source-controlled docs tree;
- a basic smoke test that opens every active region and renders expected map
  layers.

## Migration Readiness Package

When the app is ready, create a migration candidate package with:

- app code;
- region manifests;
- required runtime data only;
- dependency specification;
- deployment/start command;
- environment variable list;
- writable directory requirements;
- data checksums or version ids;
- smoke-test command;
- rollback instructions.

The package should be small enough that a deployment engineer does not need to
understand exploratory analysis folders to run the app.

## Data Strategy To Decide Later

Do not decide final storage before the app data inventory is stable.

At migration time, classify data into:

- bundled runtime data: small and required at app startup;
- mounted/object-storage data: larger files required by the app;
- precomputed artifacts: generated but needed for fast runtime behavior;
- archive/review data: QGIS, handoff and experimental files that should not be
  loaded by the deployed app;
- source/provenance data: important for reproducibility but not app runtime.

Flowcore/Usable can be a good home for app data only if it supports the access
pattern the app actually needs: local-like file reads, object-storage reads, API
reads or some combination. Avoid assuming the answer before testing.

## Questions For Flowcore/Usable Evaluation

When the app is ready, confirm:

- Can it host a Streamlit-style Python web app with WebSocket support?
- Can it install the required Python dependencies?
- Can it install or provide R and geospatial R packages if the R runtime remains
  in the app path?
- What are the limits for repo size, deployment artifact size and individual
  data files?
- Is persistent storage available for runtime cache outputs?
- How are secrets and environment variables configured?
- Can browser/runtime requests reach external map tiles and CDN assets?
- What is the rollback model?
- What CI/CD or preview-deployment workflow is available?
- How should larger GIS files be versioned and audited?

## Suggested Migration Sequence

1. Finish app functionality and regional validation.
2. Freeze a migration candidate version.
3. Build the runtime data inventory.
4. Remove or document remaining local path assumptions.
5. Create a clean deployment spec, preferably container-like if supported.
6. Run a local clean-machine or clean-environment smoke test.
7. Do a Flowcore/Usable deployment spike with one region and minimal data.
8. Add the remaining active regions.
9. Decide final data placement.
10. Promote only after smoke tests, map rendering and runtime geometry behavior
    are verified.

## Risk Posture

Current risk posture:

- static site/report migration: low to medium;
- interactive app migration: medium;
- data migration: medium, potentially high if large files, RDS/GPKG/runtime
  generated assets remain required inside the live app;
- operational migration: unknown until Flowcore/Usable deployment and storage
  capabilities are confirmed.

Expected risk after the app is complete, data is packaged cleanly and a smoke
test exists:

- static site/report migration: low;
- interactive app migration: low to medium;
- data migration: medium;
- operational migration: low to medium if platform support is confirmed.

## Handoff Decision

The correct sequence is:

1. Build the application to the intended functional scope.
2. Stabilize and validate all active regions independently.
3. Package only the runtime app and required runtime data.
4. Evaluate Flowcore/Usable with the real deployment requirements.
5. Then choose the final migration plan.

Until then, migration readiness should be handled as good repo hygiene and
runtime portability, not as a separate platform rewrite.
