# Landscape Character Model Memo - 2026-03-18

## Purpose

This memo captures the current methodological investigation of the Bornholm landscape analysis and sets the recommended direction for the next phase of work.

It is meant to be a practical reference for future sessions, not a full restatement of the review.

## Decision

- Do not build an acceptance layer directly from the current 58-layer model.
- First split the workflow in two: a cleaned landscape-character model and a separate staged acceptance framework.
- Current priority is only the first track: improve the landscape analysis itself.

## Why This Decision

The current model is strong enough to keep as a working baseline, but not strong enough to become acceptance logic.

Key reasons:

- The neighborhood engine is driven by a mixed raw `total` that adds point counts, line lengths, polygon shares, and continuous metrics in the same weight logic.
- The lower context scales are largely self-collapsed rather than truly contextual.
- The factor and cluster solution is interpretable but still structurally fragile.
- Several variables needed for wind acceptance are missing or conceptually belong outside the landscape factor model.

## Short Evidence Summary

| Issue | Current signal | Why it matters |
|---|---|---|
| Mixed-unit neighborhood weight | Raw `total` is dominated by Blue-green `48.9%`, Access `28.2%`, Topography `16.0%` | The context engine is not neutral across themes or geometry types |
| Collapsed lower scales | Zero radius in `93.97%` of `k=10`, `89.98%` of `k=50`, `83.04%` of `k=100`, `64.97%` of `k=250` | Much of the claimed multiscale context is actually the own cell |
| Factor count fixed in code | `n_factors <- 5` | Factor dimensionality is chosen, not demonstrated |
| K choice weakly separated | `K=5` silhouette `0.422032`, `K=6` `0.420808` | The preference for `K=5` is numerically weak |
| Large residual cluster | Cluster `3` contains `59.8%` of hexes | The model may be under-segmenting a broad background class |
| Low variance captured | Five factors explain `19.8%` of total variance | The factor story is useful but still a heavy simplification |
| Omitted but relevant raw groups | `80` raw layers are inactive, including `6` energy infrastructure layers | Selection logic is still provisional and path-dependent |

## v2.1 Result Snapshot

The first active cleanup run is now:

- `landskapsanalys_v2_1_geomweight58_res9`

What changed:

- Context weighting now uses `geometry_balanced_q99`
- Each active layer is robust-scaled before context growth
- Geometry types are balanced before neighborhood growth
- The balanced score is rescaled by active layer count, not by the old raw-total logic

Observed result against frozen `v2` baseline:

| Metric | Frozen `v2` baseline | Active `v2.1` | Reading |
|---|---:|---:|---|
| `K_BEST` | `5` | `6` | Preferred cluster count changed materially |
| Silhouette | `0.422` | `0.312` | Clusters are less compact in factor space |
| Cumulative explained variance | `19.78%` | `36.02%` | Factor structure captures much more of the standardized context matrix |
| Largest cluster share | `59.8%` | `50.9%` | Less dominance by one broad residual class |
| Zero-radius share at `k=10` | `93.97%` | `17.90%` | Lower-scale context is much less self-collapsed |
| Zero-radius share at `k=50` | `89.98%` | `0.00%` | Context now extends beyond the own cell almost everywhere |

Interpretation:

- This is a real methodological improvement in the neighborhood engine.
- It does **not** mean the model is finished.
- The next risks have shifted from raw self-collapse toward model selection: factor count, rotation, and `K=5` vs `K=6` now need direct testing on `v2.1`.

## What To Keep

- The current R9 Bornholm pipeline as a reproducible baseline.
- The versioned output structure in `data/interim/landskapsanalys_versions/`.
- The broad multi-theme layer inventory.
- The geology expansion and existing layer-review workflow.
- Factor and cluster outputs as interpretive tools, not decision logic.

## What To Change Next

### 1. Clean the landscape-character model

This is the next work phase.

Priority changes:

- Rebuild the neighborhood weighting so raw point counts, line lengths, polygon shares, and continuous values do not share one summed `total`.
- Compare the current cumulative-weight context against fixed ring, fixed distance, or decay-based alternatives.
- Test factor-count sensitivity instead of fixing `5` as a starting truth.
- Compare `varimax` against `oblimin` or `promax`.
- Compare `K=5` against `K=6` seriously, not just by a single silhouette ranking.
- Run leave-one-theme-out tests to see which themes are truly driving the model.

### 2. Delay the acceptance framework

This work should wait until the character model is cleaner.

Reasons:

- Acceptance is not the same thing as landscape character.
- Acceptance needs explicit settlement, visibility, ecology, technical, grid, and policy logic.
- Several of those inputs do not belong in the factor model itself.

## Recommended Implementation Sequence

1. Keep `landskapsanalys_58lager_geologi_restriktioner_res9` as the long frozen reference.
2. Keep `landskapsanalys_v2_baseline58_res9` as the frozen `v2` comparison run.
3. Use `landskapsanalys_v2_1_geomweight58_res9` as the active cleanup track.
4. Run sensitivity tests for factor count, rotation, factor scores, and `K` on `v2.1`.
5. Only after the core structure is more stable, retest selected inactive groups such as protected-nature subcategories, river subcategories, and conservation landscapes.
6. Keep energy, grid, viewshed, settlement thresholds, and legal-policy logic out of the factor model until the character model is stable enough to serve as a clean contextual input.

## Recommended Repository Strategy

Recommendation: do **not** start a new repo yet.

Reasons:

- The current pipeline is tightly coupled to existing Bornholm data paths, Quarto reporting, layer review outputs, and versioned run folders.
- Splitting now would create overhead before the current analysis logic is stable.
- The next phase is still model cleanup inside the same analytical lineage, not a clean new product.

Recommended approach inside this repo:

- Keep the current 58-layer run as a frozen reference.
- Add the next work as a new internal version track focused on a cleaned character model.
- Keep acceptance-layer work as a later, separate workstream once the character model has been revalidated.

When a new repo would make sense:

- If the character model becomes reusable across multiple regions.
- If you want to turn the method into a standalone package or framework.
- If the later acceptance framework becomes a distinct planning product with separate governance, inputs, and outputs.

## Practical Naming Recommendation

If you want a clearer internal label for the next phase, use a name like:

- `landscape_character_model_v2`
- `bornholm_landscape_character_model`
- `landskapsanalys_character_cleanup`

I would avoid creating a fresh repo named `landscape-character-model` until the current method has survived the robustness pass.

## Resolution Stance

Recommendation: do **not** switch the active baseline from `res9` to `res10` yet.

Why:

- The current biggest problem is not only spatial resolution. It is the context-weight logic.
- A finer grid may help some local structure, but it will also make the model sparser and more sensitive to aggregation noise.
- If this is a one-step finer H3-style move, expect substantially more cells and heavier computation.
- With the current neighborhood engine, a move to `res10` could just produce a more unstable version of the same bias.

Recommended order:

1. build `v2` on the frozen `res9` baseline
2. clean the context weighting and retest factor robustness
3. then run `res9` versus `res10` as an explicit sensitivity comparison

What `res10` may improve:

- finer coastal transitions
- smaller settlement edges
- less forced mixing inside each cell

What `res10` may worsen:

- more zero or near-zero cells
- noisier line and point signals
- weaker comparability across runs if the weighting logic is unchanged

## Immediate Next Move

The single best next move is:

- keep the current repo
- keep the 58-layer model and `v2` baseline frozen
- use `v2.1` as the active cleanup iteration
- focus next on factor robustness, rotation choice, and `K=5` versus `K=6`

In plain terms:

**First split the workflow in two: a cleaned landscape-character model and a separate staged acceptance framework with hard exclusions plus explicit settlement, visibility, ecology, technical, and grid surfaces.**

Then work only on the first half until it is substantially cleaner than the current baseline.

## Useful Anchors For Next Session

- V2.1 report source: `docs/geocontext/current_landscape_model/landskapsanalys_v2_1.qmd`
- V2.1 light report source: `docs/geocontext/current_landscape_model/landskapsanalys_v2_1_light.qmd`
- V2.1 run script: `script/landskapsanalys/09_build_bornholm_r9_landskapsanalys_v2_1_geomweight58_res9.R`
- Frozen V2 baseline run script: `script/landskapsanalys/08_build_bornholm_r9_landskapsanalys_v2_baseline58_res9.R`
- Shared pipeline logic: `script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R`
- Current quickstart: `docs/geocontext/NEXT_SESSION_QUICKSTART.md`
