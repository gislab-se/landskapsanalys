# V5 Regional Plan (2026-04-09)

## Purpose

This note captures the current shared plan for the next phase:

- move the next region work into `regional-landscape-pipeline`
- keep the strongest parts of the Bornholm `v4` delivery as the publication reference
- continue first with Dalarna, then Vara

The goal is not to copy Bornholm `v4` mechanically, but to repeat the same broad working method in a cleaner regional pipeline.

## Recommended Working Split

### `regional-landscape-pipeline` should own

- region config
- source inventory and acquisition
- boundary setup and H3 grid generation
- harmonized layer staging in PostGIS
- hex feature matrix generation
- geocontext / context generation
- factor analysis and clustering
- audit outputs and run manifests

### `landskapsanalys` should remain the publication reference for now

- the clearest example of the current best final delivery is still:
  - `docs/geocontext/published_report/landskapsanalys_v4.html`
  - `docs/geocontext/published_report/landskapsanalys_v4_combined_map.html`
- this repo still shows how the final report, combined map, factor naming, cluster naming, and explanatory narrative were polished into a presentation-ready product

## V5 Model Strategy

Do not build `v5` as "Bornholm v4 with another region's data dropped in".

Instead, build `v5` in three layers:

1. reusable analysis core
   - `hex feature table -> context/geocontext -> factor analysis -> clusters -> exports`
2. region package
   - boundary
   - source registry
   - layer catalog
   - feature roles
   - reference material
   - QA rules
3. publication layer
   - final report
   - combined fullscreen map
   - factor and cluster naming
   - interpretation text tailored to the region

## First V5 Run Pattern For A New Region

For each new region, start with three runs:

1. `core` / `baseline`
   - comparable core stack
   - topography
   - hydrology
   - land cover / land use
   - settlement / infrastructure
   - protection / culture
2. `terrain` challenger
   - stronger terrain and physical landscape emphasis
3. `region-specific` challenger
   - additional layers that matter especially for the chosen region

Then:

- compare factor interpretability
- compare cluster geography
- compare stability and obvious failure modes
- freeze one chosen `source_analysis_id`
- build the published `v5` report from that chosen run

## What Must Stay Manual For Now

These parts should still be treated as expert interpretation work, not automatic pipeline outputs:

- final factor labels
- final cluster labels
- explanatory factor text
- explanatory cluster text
- region-specific map display mask
- publication wording and narrative framing

## Near-Term Recommendation

### Main recommendation

Use `regional-landscape-pipeline` as the active workspace for the next region.

Reason:

- it is the correct long-term home for reusable regional work
- it already has the right config and output structure
- Dalarna has already progressed into real first-pass outputs there

### Important limitation

Do not assume that `regional-landscape-pipeline` already replaces the full Bornholm `v4` publication layer.

It is strong enough for:

- staging
- feature generation
- geocontext
- factor and cluster outputs
- audit structure

It is not yet fully finished for:

- region-neutral final publication
- shared app bundle runtime
- robust multi-region tests

So the current plan is:

- do the next region analysis work in `regional-landscape-pipeline`
- use Bornholm `v4` in `landskapsanalys` as the publication benchmark
- only fully migrate the final publication layer after at least two non-Bornholm regions have run end-to-end

## Sequence Agreed For Next Work

1. Continue in `regional-landscape-pipeline`
2. Focus first on Dalarna
3. After Dalarna, continue with Vara
4. Keep Bornholm `v4` as the reference for what "finished" should feel like

## Practical Next Step

When resuming in `regional-landscape-pipeline`, the next work should be:

- make Dalarna the first clear `v5` candidate region
- stabilize the first chosen Dalarna layer universe
- run baseline and challenger variants
- decide which Dalarna run deserves the publication track
- then mirror the same approach for Vara
