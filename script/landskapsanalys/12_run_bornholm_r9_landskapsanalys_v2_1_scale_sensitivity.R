suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(purrr)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
source_analysis_id <- "landskapsanalys_v2_1_geomweight58_res9"
sensitivity_id <- Sys.getenv(
  "LANDSKAPSANALYS_SENSITIVITY_ID",
  unset = "landskapsanalys_v2_1_scale_sensitivity"
)
main_script <- file.path(repo_root, "script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R")
config_csv <- file.path(
  repo_root,
  "script/landskapsanalys/config/landskapsanalys_v2_1_geomweight58_res9_input_layers.csv"
)
summary_out_dir <- Sys.getenv(
  "LANDSKAPSANALYS_OUT_DIR",
  unset = file.path(repo_root, "data/interim/landskapsanalys_versions", sensitivity_id)
)
dir.create(summary_out_dir, recursive = TRUE, showWarnings = FALSE)

variants <- tibble::tribble(
  ~scale_label, ~analysis_id, ~k_values, ~analysis_subtitle, ~source_note, ~reuse_existing,
  "legacy", source_analysis_id, "10,50,100,250,1000",
  "v2.1 legacy scales, 58 lager, R9",
  "Legacy scale family inherited from earlier GC4/R9 work.",
  TRUE,
  "local_geom", "landskapsanalys_v2_1_k_local_geom58_res9", "8,24,72,216,648",
  "v2.1 local geometric scales, 58 lager, R9",
  "Scale family shifted toward more local context with approximate x3 spacing.",
  FALSE,
  "broad_geom", "landskapsanalys_v2_1_k_broad_geom58_res9", "15,45,135,405,1215",
  "v2.1 broad geometric scales, 58 lager, R9",
  "Scale family shifted toward broader context with approximate x3 spacing.",
  FALSE
)

run_variant <- function(scale_label, analysis_id, k_values, analysis_subtitle, source_note, reuse_existing) {
  out_dir <- file.path(repo_root, "data/interim/landskapsanalys_versions", analysis_id)
  metadata_path <- file.path(out_dir, paste0(analysis_id, "_metadata.csv"))

  if (!reuse_existing && !file.exists(metadata_path)) {
    message("Running scale variant: ", scale_label, " -> ", analysis_id)
    Sys.setenv(
      LANDSKAPSANALYS_REPO_ROOT = repo_root,
      LANDSKAPSANALYS_ANALYSIS_ID = analysis_id,
      LANDSKAPSANALYS_ANALYSIS_SUBTITLE = analysis_subtitle,
      LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION = source_analysis_id,
      LANDSKAPSANALYS_CONFIG_CSV = config_csv,
      LANDSKAPSANALYS_OUT_DIR = out_dir,
      LANDSKAPSANALYS_WEIGHT_STRATEGY = "geometry_balanced_q99",
      LANDSKAPSANALYS_WEIGHT_QUANTILE = "0.99",
      LANDSKAPSANALYS_WEIGHT_RESCALE_MODE = "n_input_layers",
      LANDSKAPSANALYS_WEIGHT_DESCRIPTION = paste(
        "Per-layer robust q99 scaling, equal weighting across geometry types,",
        "and rescaling by active layer count to express neighborhood growth in layer-equivalent context mass."
      ),
      LANDSKAPSANALYS_K_VALUES = k_values,
      LANDSKAPSANALYS_SOURCE_MODEL_NOTE = paste(
        "Scale sensitivity variant in v2.1.",
        source_note,
        "All other model choices are held constant."
      )
    )
    sys.source(main_script, envir = new.env(parent = globalenv()))
  } else {
    message("Reusing existing v2.1 run for scale variant: ", scale_label)
  }

  list(
    scale_label = scale_label,
    analysis_id = analysis_id,
    out_dir = out_dir
  )
}

summarise_variant <- function(scale_label, analysis_id, out_dir) {
  metadata <- read.csv(file.path(out_dir, paste0(analysis_id, "_metadata.csv")), stringsAsFactors = FALSE)
  run_summary <- read.csv(file.path(out_dir, paste0(analysis_id, "_run_summary.csv")), stringsAsFactors = FALSE)
  variance_df <- read.csv(file.path(out_dir, paste0(analysis_id, "_factor_variance.csv")), stringsAsFactors = FALSE)
  k_scores <- read.csv(file.path(out_dir, paste0(analysis_id, "_k_scores.csv")), stringsAsFactors = FALSE)
  cluster_sizes <- read.csv(file.path(out_dir, paste0(analysis_id, "_cluster_sizes.csv")), stringsAsFactors = FALSE)
  points_with_context <- read.csv(file.path(out_dir, paste0(analysis_id, "_points_with_context.csv")), stringsAsFactors = FALSE)

  best_row <- k_scores |>
    slice_max(order_by = silhouette, n = 1, with_ties = FALSE)

  factor_cols <- grep("^F[0-9]+$", names(variance_df), value = TRUE)
  cumulative_var <- variance_df |>
    filter(metric == "Cumulative Var") |>
    select(all_of(factor_cols)) |>
    unlist(use.names = FALSE) |>
    max()

  mean_total <- as.numeric(run_summary$value[run_summary$metric == "total_weight_sum"]) /
    as.numeric(run_summary$value[run_summary$metric == "n_hex"])

  k_vec <- suppressWarnings(as.numeric(strsplit(metadata$context_k_values[1], ",")[[1]]))
  radius_summary <- purrr::map_dfr(k_vec, function(k_val) {
    radius_col <- paste0("radius_k", k_val)
    r <- points_with_context[[radius_col]]
    tibble::tibble(
      scale_label = scale_label,
      analysis_id = analysis_id,
      k = k_val,
      approx_avg_cells = k_val / mean_total,
      zero_share = mean(r == 0, na.rm = TRUE),
      median_radius = median(r, na.rm = TRUE),
      p90_radius = as.numeric(stats::quantile(r, 0.9, na.rm = TRUE))
    )
  })

  summary_row <- tibble::tibble(
    scale_label = scale_label,
    analysis_id = analysis_id,
    context_k_values = metadata$context_k_values[1],
    cumulative_var = cumulative_var,
    k_best = best_row$K[1],
    best_silhouette = best_row$silhouette[1],
    largest_cluster_share = max(cluster_sizes$share, na.rm = TRUE),
    smallest_cluster_share = min(cluster_sizes$share, na.rm = TRUE),
    mean_total = mean_total
  )

  list(summary_row = summary_row, radius_summary = radius_summary, k_scores = mutate(k_scores, scale_label = scale_label, .before = 1))
}

executed_variants <- purrr::pmap(variants, run_variant)
variant_summaries <- purrr::map(
  executed_variants,
  ~ summarise_variant(.x$scale_label, .x$analysis_id, .x$out_dir)
)

summary_table <- bind_rows(purrr::map(variant_summaries, "summary_row"))
radius_table <- bind_rows(purrr::map(variant_summaries, "radius_summary"))
k_score_table <- bind_rows(purrr::map(variant_summaries, "k_scores"))

write.csv(summary_table, file.path(summary_out_dir, paste0(sensitivity_id, "_summary.csv")), row.names = FALSE)
write.csv(radius_table, file.path(summary_out_dir, paste0(sensitivity_id, "_radius_summary.csv")), row.names = FALSE)
write.csv(k_score_table, file.path(summary_out_dir, paste0(sensitivity_id, "_k_scores.csv")), row.names = FALSE)

metadata_out <- tibble::tibble(
  sensitivity_id = sensitivity_id,
  source_analysis_id = source_analysis_id,
  tested_scale_labels = paste(variants$scale_label, collapse = ","),
  tested_analysis_ids = paste(variants$analysis_id, collapse = ",")
)
write.csv(metadata_out, file.path(summary_out_dir, paste0(sensitivity_id, "_metadata.csv")), row.names = FALSE)

message("Finished v2.1 scale sensitivity analysis: ", sensitivity_id)
