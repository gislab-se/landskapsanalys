# GEOCONTEXT REPO BLUEPRINT

## Goal

Build a reusable repository named `geocontext` that can take a hex-based feature matrix from any project and produce:

- contextualized features
- factor scores
- cluster labels
- review-ready outputs

The generic repo should not be tied to Bornholm, QGIS file paths, or one app.

## Design Principle

The reusable unit is not "raw shapefiles to everything." The reusable unit is:

`hex feature table in -> contextual features -> factor model -> clusters -> exports`

That keeps project-specific GIS ingestion outside the core engine and makes the package easier to test.

## Suggested Repository Layout

```text
geocontext/
  README.md
  pyproject.toml
  src/geocontext/
    __init__.py
    io.py
    config.py
    context.py
    transforms.py
    factor.py
    cluster.py
    report.py
    manifest.py
    cli.py
  tests/
    test_context.py
    test_factor.py
    test_cluster.py
    test_config.py
  examples/
    bornholm_r9/
      dataset.yml
      features.csv
      feature_roles.csv
      factor_model.yml
      clustering.yml
  docs/
    concepts.md
    cookbook.md
    migration-notes.md
```

## Core Modules

### `io.py`

Responsible for reading and validating input tables:

- required key column, e.g. `hex_id`
- optional geometry or centroid columns
- feature columns
- optional metadata columns

### `config.py`

Loads and validates config files such as:

- feature selection
- transforms
- grouping rules
- k-values
- factor model settings
- cluster settings

### `context.py`

Implements the geocontext transformation from base features to contextual variables.

Inputs:

- hex identifiers
- coordinates or neighbourhood graph
- selected feature columns
- k-values
- aggregation statistics such as `mean`, `std`, `min`, `max`

Outputs:

- contextualized feature matrix
- manifest of generated columns

### `transforms.py`

Applies project-declared transformations before or after contextualization:

- `log1p`
- `asinh`
- winsorization
- min/max caps for shares
- optional robust scaling

### `factor.py`

Owns the generic factor-analysis workflow:

- column cleaning
- zero-variance removal
- optional missing-data rules
- factor extraction
- rotation
- score generation
- loadings export

### `cluster.py`

Builds clusters from factor scores:

- candidate `k` values
- silhouette or alternative metrics
- stable random seed
- export of `class_km` or equivalent labels

### `report.py`

Creates reusable summary outputs:

- factor summary tables
- loading heatmaps
- cluster profiles
- strongest feature-factor relationships
- run metadata

### `manifest.py`

Writes a machine-readable run manifest:

- timestamp
- config files used
- input row count
- selected features
- generated output columns
- factor count
- chosen cluster count

### `cli.py`

Suggested commands:

- `geocontext context`
- `geocontext factor`
- `geocontext cluster`
- `geocontext report`
- `geocontext run`

## Config Files To Expect

### `dataset.yml`

Defines input locations and ID columns.

### `feature_roles.csv`

Defines which features are included and how they should be treated.

Suggested columns:

- `include`
- `feature_name`
- `source_feature`
- `feature_group`
- `metric_type`
- `transform`
- `analysis_role`
- `notes`

### `factor_model.yml`

Defines the factor-analysis settings.

Suggested keys:

- `n_factors`
- `rotation`
- `method`
- `drop_zero_variance`
- `drop_all_na`
- `winsorize`

### `clustering.yml`

Defines the cluster step.

Suggested keys:

- `enabled`
- `candidate_k`
- `selection_metric`
- `random_state`
- `n_init`

## Recommended Scope For v1

Version 1 should focus on reproducibility and clarity, not maximal feature count.

A good first release would support:

- tabular input from CSV or parquet
- centroid-based nearest-neighbour context
- factor analysis with loadings and scores
- k-means clustering on factor scores
- manifest export
- a minimal HTML or markdown report

## What Stays In Project Repos

Project repos should still own:

- GIS ingestion from shapefiles/geopackages/databases
- project-specific layer definitions
- human review of candidate layers
- app integration
- country or region specific naming

## Migration Strategy

1. Rebuild the R9 factor workflow inside `landskapsanalys` first.
2. Identify the functions that are clearly reusable.
3. Move only those functions into the new generic repo.
4. Keep Bornholm as the first example dataset in `examples/bornholm_r9/`.
