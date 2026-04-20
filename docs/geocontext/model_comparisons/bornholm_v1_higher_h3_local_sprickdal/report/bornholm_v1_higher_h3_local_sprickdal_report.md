# Bornholm v1 Higher H3 Local Sprickdal

Controlled Prompt 1 rerun. This version changes the analysis unit from H3 res9 to H3 res10 while keeping the current Bornholm modelling method as close as possible to the published baseline.

## Run Design

- Version id: `bornholm_v1_higher_h3_local_sprickdal`
- Purpose: test whether northwest sprickdal terrain becomes clearer at higher H3 resolution.
- H3 resolution: res10, generated as children of the published res9 grid.
- K values: `10,50,100,250,1000`; intentionally not scaled upward, so the neighbourhood context becomes more local.
- Context mode: Same as published v3.2/v4 baseline: per-layer robust q99 scaling, theme-balanced aggregation within each geometry type, moderate agricultural-land priority, mild continuous-metric uplift, terrain bands, and contour-derived terrain metrics. Only the H3 unit is changed from res9 to res10; k values are intentionally kept unchanged for a more local context test.
- Factor method: psych::fa fm=minres rotate=varimax scores=tenBerge
- Factor count: 5
- Cluster method: k-means on factor scores, K candidates 5:10, selected by silhouette.

## Run Summary

                     metric
1               analysis_id
2                     n_hex
3            n_input_layers
4         n_context_columns
5          n_factor_columns
6                    k_best
7           weight_strategy
8           weight_quantile
9        theme_balance_mode
10        layer_weight_spec
11        theme_weight_spec
12     geometry_weight_spec
13      weight_rescale_mode
14    weight_rescale_factor
15            raw_total_sum
16           base_total_sum
17         total_weight_sum
18       zero_raw_total_hex
19           zero_total_hex
20 excluded_zero_signal_hex
                                                                                                                                                                                                               value
1                                                                                                                                                                              bornholm_v1_higher_h3_local_sprickdal
2                                                                                                                                                                                                              50189
3                                                                                                                                                                                                                 68
4                                                                                                                                                                                                                680
5                                                                                                                                                                                                                  5
6                                                                                                                                                                                                                  7
7                                                                                                                                                                                              geometry_balanced_q99
8                                                                                                                                                                                                               0.99
9                                                                                                                                                                                                    within_geometry
10 gc_agricultural_land_share=1.40; gc_relief_m=1.05; gc_highest_point_m=1.05; gc_contour_mean_elevation_m=1.10; gc_contour_mean_slope_deg=1.15; gc_contour_valley_depth_max_m=1.25; gc_high_agri_plateau_proxy=1.35
11                                                                                                                                                                                                     Land use=1.60
12                                                                                                                                                                                            Continuous metric=1.20
13                                                                                                                                                                                                    n_input_layers
14                                                                                                                                                                                                                68
15                                                                                                                                                                                                  9521262.98738869
16                                                                                                                                                                                                  6505.50995232733
17                                                                                                                                                                                                  442374.676758258
18                                                                                                                                                                                                                 0
19                                                                                                                                                                                                                 0
20                                                                                                                                                                                                              5048

## Cluster Sizes

  class_km n_hex      share
1        1  1337 0.02663930
2        2  5671 0.11299289
3        3  3767 0.07505629
4        4  2084 0.04152304
5        5 21006 0.41853793
6        6 12013 0.23935524
7        7  4311 0.08589532

## Cluster Profile

  class_km          F1          F2          F3          F4          F5 n_hex
1        1 -0.47432633  4.23444759 -0.14804699 -0.65743415 -0.58073552  1337
2        2 -0.09583507 -0.14337869  2.15899134 -0.18461266 -0.59545708  5671
3        3 -0.20516769  1.65045383 -0.08014069  0.36695651  0.39688608  3767
4        4 -0.16513960 -0.09374595 -0.14253576  3.90723669 -0.04736255  2084
5        5 -0.15305888 -0.42387783 -0.51288281 -0.26140305 -0.57943001 21006
6        6 -0.38411617 -0.18899231 -0.02687733 -0.17884467  1.19514872 12013
7        7  2.34846088  0.07053894 -0.08125097  0.00937481  0.13247493  4311

## K Scores

   K silhouette silhouette_basis
1  7  0.3365440             full
2  6  0.3353997             full
3  5  0.3089320             full
4  8  0.2992256             full
5 10  0.2803762             full
6  9  0.2772974             full

## Factor Variance

                 metric          F1          F2         F3          F4
1           SS loadings 49.51101982 46.25312830 38.2283941 36.25951308
2        Proportion Var  0.07389704  0.06903452  0.0570573  0.05411868
3        Cumulative Var  0.07389704  0.14293156  0.1999889  0.25410755
4  Proportion Explained  0.24338728  0.22737207  0.1879239  0.17824526
5 Cumulative Proportion  0.24338728  0.47075936  0.6586833  0.83692853
           F5
1 33.17278807
2  0.04951162
3  0.30361917
4  0.16307147
5  1.00000000

## Review Notes To Fill In

- Northwest sprickdal clarity:
- Cluster vs subcluster vs factor-score zone:
- Smaller-hex artifacts:
- Interpretation gain:
