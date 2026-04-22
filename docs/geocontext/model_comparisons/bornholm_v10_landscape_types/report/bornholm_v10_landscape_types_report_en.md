# Bornholm Landscape Structure Analysis

## Start Here

This report is the main entry point to the Bornholm landscape structure analysis. It builds on several previous model versions and presents v10 as the current integrated interpretation for now. The purpose is to explain how landscape metrics, factors, clusters and landscape types connect, and how the result can support further analysis of landscape structure and potential for solar and wind energy.

v10 is not a new clustering. It is an interpreted synthesis on top of v9 K=8: the analytical v9 clusters and factor scores are translated into five more communicable landscape types. It should therefore be read as a transparent cartographic and methodological summary, not as a field-verified classification.

## Knowledge From Earlier Versions

The Bornholm work has developed step by step. In `regional-landscape-pipeline`, v1 and v3 showed that higher H3 resolution and K=8 made the fracture-valley structure clearer. v4 and v5 tested more theme-balanced inputs and showed that the factor signal was present, even when the cluster names needed more careful interpretation. v6, v7 and v9 helped us understand the K=8 solution, cluster size, factor layers and how the results can be shown pedagogically.

The `landskapsanalys` repository also contains earlier report versions, model comparisons and scenario/potential apps. They contributed methodological knowledge, presentation formats and practical understanding of how the landscape analysis can be used. Older versions should therefore be read as development steps and supporting evidence, not as competing main results.

## Method In Brief

The analysis starts with many GIS layers and landscape metrics summarized in a hexagon grid. The metrics describe relief, elevation differences, coastal and sandy environments, forest and protected nature, settlement, open lowland and agriculture-dominated landscape rooms.

These metrics are reduced with factor analysis. Factor loadings show which layers and metrics build each factor. Factor scores then show how strongly each hexagon expresses each factor. In v9, the factor scores are used to create eight clusters. In v10, the eight clusters are translated into five landscape types through a documented crosswalk.

## Layer Families And Factors

- `F1`: fracture valleys and steep relief.
- `F2`: aeolian sand and sandy coast.
- `F3`: forest and protected nature.
- `F4`: settlement and built structure.
- `F5`: low-lying open land.

## v9 Clusters

- cluster 1: settlement and activity cores, strongly linked to `F4`.
- cluster 2: fracture-valley influenced transition landscape, linked to `F1`.
- cluster 3: mixed everyday landscape with a low factor profile and no single dominant factor.
- cluster 4: aeolian sand and sandy coast, a core zone with very strong `F2`.
- cluster 5: fracture valley and steep relief, a core zone with strong `F1` and some `F2`.
- cluster 6: open and low-lying mixed landscape, linked to `F5`.
- cluster 7: forest and protected nature, a core zone with strong `F3`.
- cluster 8: sandy and coastal landscape, linked to `F2` but more mixed than cluster 4.

## From v9 To v10

In v10, the clear v9 clusters are transferred directly to landscape types. The large mixed cluster 3 is split with `F1`, because `F1` captures the fracture-valley and relief signal inside the agricultural landscape.

- `LT01 Rocky coastal landscape` is created from v9 cluster 5.
- `LT02 Sandy coastal landscape` is created from v9 clusters 4 and 8.
- `LT03 Agricultural fracture-valley landscape` is created from v9 cluster 2 and the part of cluster 3 with a clearer `F1` signal.
- `LT04 Forested fracture-valley landscape` is created from v9 cluster 7.
- `LT05 Plain and agricultural landscape` is created from v9 cluster 6 and the part of cluster 3 with lower `F1` signal.

v10 is therefore an interpreted synthesis: the landscape types are based on statistical clusters, the meaning of factor loadings and the geographic expression of factor scores.

## Further Use

The landscape types do not by themselves decide where new technology should be built. They provide structural context: which landscape rooms are coastal, sandy, fracture-valley influenced, forest/nature dominated or low-lying agricultural. This context can then be combined with technical, legal and planning layers in the solar and wind potential apps.

## Files

- Interactive map: `../map/bornholm_v10_landscape_types_map.html`
- Crosswalk: `../model/bornholm_v10_landscape_types_crosswalk.csv`
- Factor loadings: `../model/bornholm_v10_landscape_types_factor_loadings_from_v1.csv`
