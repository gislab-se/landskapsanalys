# LANDSKAPSANALYS METHOD REPORT

## Why This Document Exists

This document is the working method note for what the project now calls `landskapsanalys`.

Historically, the workflow was often described as:

- geocontext
- factor analysis
- cluster assignment

That older language is still useful, but `landskapsanalys` is the broader term we now use for the full analytical chain and its interpretation.

## Working Definition

In this project, `landskapsanalys` means the full workflow from spatial source layers to interpretable landscape patterns.

It includes:

1. source-layer aggregation to hexagons
2. quality control and visual review of each layer
3. contextualization / geocontext-style neighbourhood calculations
4. factor analysis on the resulting feature matrix
5. cluster assignment on factor scores
6. interpretation of factors and clusters in relation to landscape character
7. app/report delivery for inspection and iteration

## Relationship To The Older GC4 Workflow

The earlier GC4 workflow is still the closest verified reference implementation.

That legacy chain used:

- 4 raw layers
- geocontext context variables at several `k` values
- factor analysis producing `F1..F5`
- k-means clustering producing `class_km`
- rendered review pages and an app-facing export

In the current project, the goal is not only to reproduce that logic, but to extend it with:

- a larger and better-audited R9 layer universe
- parent/child handling for split layers
- clearer provenance and QA
- stronger cultural-geographic interpretation

## Current R9 Landscape-Analysis Chain

The intended R9 chain is:

1. aggregate selected Bornholm layers to R9 hexagons
2. inspect each layer through report maps and QA outputs
3. choose the factor-analysis feature universe explicitly
4. generate geocontext/context variables
5. run factor analysis
6. assign clusters from factor scores
7. compare and interpret results in the report and app

This means factor analysis should be treated as one stage inside the landscape analysis, not as the whole method.

## Important Method Rule

Do not treat every available layer as automatically suitable for the first factor model.

The landscape-analysis workflow must separate:

- layers that are useful as direct analytical inputs
- layers that are useful mainly for QA or interpretation
- layers that are synthetic enough that they may partially encode the answer already

That is why the first serious R9 runs should be curated and compared, not maximized.

## Planned Comparison Track

The following comparison track should be used as the project matures.

### 1. Legacy Bridge Run

Run a legacy-like model using the old GC4 theme family so the new workflow can be compared to a known reference.

### 2. Curated R9 v1 Run

Run a broader but still curated R9 model that reflects the current Bornholm landscape-analysis goals.

### 3. Special-Layer Sensitivity Test

Run the R9 model in two variants:

- without `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32`
- with `landscapes_worthy_of_preservation_pdk_bevaringsvaerdigelandskaber_bol_32`

This tests whether that interpreted planning layer enriches the model or prematurely bakes in a landscape-character answer.

### 4. Nature vs Culture Experimental Split

Later in the project, explicitly test two separate landscape-analysis runs:

- a `naturgeografisk` run
- a `kulturgeografisk` run

Purpose:

- see whether the factor structure becomes clearer when nature-oriented and culture-oriented layers are separated
- compare whether cluster geography changes substantially between the two perspectives
- test whether the combined model hides meaningful distinctions that become visible in the split runs

This should be treated as a planned experiment, not as a requirement for the first R9 production run.

## Suggested Interpretation Of The Two Experimental Runs

### Naturgeografisk Run

Candidate emphasis:

- topography
- relief
- water systems
- wetlands
- coasts
- forest and hede/moor
- ecological connectivity
- selected protected-nature layers

Main question:

- what natural or physical landscape structure emerges when human/institutional layers are minimized?

### Kulturgeografisk Run

Candidate emphasis:

- settlement and built structure
- roads and accessibility
- agricultural land use
- cultural-historical conservation
- valuable cultural environment
- selected planning and heritage layers
- energy infrastructure if relevant to landscape use and transformation

Main question:

- what human-shaped landscape structure emerges when cultural and land-use signals are foregrounded?

## How To Compare Runs

Whenever multiple runs are tested, compare them on the same dimensions:

- factor loadings
- factor interpretability
- cluster stability
- cluster geography
- sensitivity to adding/removing specific layers
- whether outputs are analytically useful, not only statistically distinct

## Naming Convention Going Forward

Recommended working language:

- `landskapsanalys` = the full workflow
- `geocontext` = the contextualization step or legacy framing
- `factor analysis` = the dimensionality-reduction step
- `cluster assignment` = the grouping step on factor outputs

This keeps the terminology clear while still honoring the project's origin in the earlier geocontext framing.

## External Method Reference

A key external reference for the next phase is the Stockholm University work on a multiscalar typology of residential areas in Sweden.

This project treats that work as methodological inspiration for:

- multiscalar contextualization
- dimensionality reduction / factor-style summarization
- clustering into interpretable spatial types

For Bornholm, the method is adapted from residential-area typology to landscape analysis. That is scientifically reasonable if the transfer is documented clearly, the data universe is reported transparently, and the resulting factors/clusters are interpreted and validated in a landscape context.

Reference URLs:

- `https://su.figshare.com/articles/dataset/Multiscalar_typology_of_residential_areas_in_Sweden/14753826?file=28351917`
- `https://www.diva-portal.org/smash/record.jsf?pid=diva2:1624901`
- `https://www.diva-portal.org/smash/get/diva2:1624901/FULLTEXT01.pdf`
