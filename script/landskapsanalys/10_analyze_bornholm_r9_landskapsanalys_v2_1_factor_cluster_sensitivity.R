suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(psych)
  library(cluster)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
source_analysis_id <- Sys.getenv(
  "LANDSKAPSANALYS_SOURCE_ANALYSIS_ID",
  unset = "landskapsanalys_v2_1_geomweight58_res9"
)
sensitivity_id <- Sys.getenv(
  "LANDSKAPSANALYS_SENSITIVITY_ID",
  unset = "landskapsanalys_v2_1_factor_cluster_sensitivity"
)
source_dir <- file.path(repo_root, "data/interim/landskapsanalys_versions", source_analysis_id)
out_dir <- Sys.getenv(
  "LANDSKAPSANALYS_OUT_DIR",
  unset = file.path(repo_root, "data/interim/landskapsanalys_versions", sensitivity_id)
)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

points_with_context_path <- file.path(source_dir, paste0(source_analysis_id, "_points_with_context.csv"))
indicator_catalog_path <- file.path(source_dir, paste0(source_analysis_id, "_indicator_catalog.csv"))
run_summary_path <- file.path(source_dir, paste0(source_analysis_id, "_run_summary.csv"))

rotations <- c("varimax", "oblimin")
n_factors <- 5
k_candidates <- 5:10
focus_k <- c(5, 6)

adjusted_rand_index <- function(x, y) {
  tab <- table(x, y)
  n <- sum(tab)
  if (n <= 1) {
    return(NA_real_)
  }

  choose2 <- function(v) v * (v - 1) / 2
  sum_ij <- sum(choose2(tab))
  sum_i <- sum(choose2(rowSums(tab)))
  sum_j <- sum(choose2(colSums(tab)))
  expected <- sum_i * sum_j / choose2(n)
  max_index <- 0.5 * (sum_i + sum_j)
  denom <- max_index - expected
  if (!is.finite(denom) || denom == 0) {
    return(NA_real_)
  }
  (sum_ij - expected) / denom
}

compute_k_scores <- function(score_mat, k_values) {
  dist_basis <- tryCatch(stats::dist(score_mat), error = function(e) NULL)
  sample_idx <- NULL
  sil_basis <- "full"
  if (is.null(dist_basis)) {
    sil_basis <- "sample"
    sample_idx <- sort(sample(seq_len(nrow(score_mat)), min(3000, nrow(score_mat))))
    dist_basis <- stats::dist(score_mat[sample_idx, , drop = FALSE])
  }

  purrr::map_dfr(k_values, function(k) {
    set.seed(42)
    km_fit <- stats::kmeans(
      score_mat,
      centers = k,
      nstart = 50,
      iter.max = 500,
      algorithm = "Lloyd"
    )
    sil_score <- if (length(unique(km_fit$cluster)) > 1) {
      sil <- if (sil_basis == "full") {
        cluster::silhouette(km_fit$cluster, dist_basis)
      } else {
        cluster::silhouette(km_fit$cluster[sample_idx], dist_basis)
      }
      mean(sil[, "sil_width"])
    } else {
      NA_real_
    }

    tibble::tibble(
      K = k,
      silhouette = sil_score,
      silhouette_basis = sil_basis
    )
  })
}

message("Reading v2.1 points_with_context...")
points_with_context <- read.csv(points_with_context_path, stringsAsFactors = FALSE, check.names = FALSE)
indicator_catalog <- read.csv(indicator_catalog_path, stringsAsFactors = FALSE)
run_summary <- read.csv(run_summary_path, stringsAsFactors = FALSE)

X <- points_with_context |>
  select(matches("^(mean_|std_).*_k[0-9]+$"))
Xz <- as.data.frame(scale(X))
Xz_clean <- Xz
Xz_clean[] <- lapply(Xz_clean, function(v) {
  v[is.infinite(v)] <- NA_real_
  v
})
Xz_clean <- Xz_clean[, colSums(!is.na(Xz_clean)) > 0, drop = FALSE]
std_vec <- vapply(Xz_clean, stats::sd, numeric(1), na.rm = TRUE)
Xz_clean <- Xz_clean[, std_vec > 0 & !is.na(std_vec), drop = FALSE]
row_keep <- stats::complete.cases(Xz_clean)
Xz_clean <- Xz_clean[row_keep, , drop = FALSE]
hex_ids <- points_with_context$hex_id[row_keep]

message(sprintf("Sensitivity matrix shape: %s rows x %s cols", nrow(Xz_clean), ncol(Xz_clean)))

analysis_metadata <- tibble::tibble(
  sensitivity_id = sensitivity_id,
  source_analysis_id = source_analysis_id,
  n_hex = nrow(Xz_clean),
  n_context_columns = ncol(Xz_clean),
  n_input_layers = nrow(indicator_catalog),
  compared_rotations = paste(rotations, collapse = ","),
  compared_k = paste(k_candidates, collapse = ","),
  focus_k = paste(focus_k, collapse = ","),
  source_k_best = run_summary$value[run_summary$metric == "k_best"][1]
)
write.csv(
  analysis_metadata,
  file.path(out_dir, paste0(sensitivity_id, "_metadata.csv")),
  row.names = FALSE
)

fit_results <- purrr::map(rotations, function(rotation_name) {
  message("Fitting factor model with rotation = ", rotation_name)
  set.seed(42)
  fa_fit <- suppressWarnings(
    psych::fa(
      Xz_clean,
      nfactors = n_factors,
      rotate = rotation_name,
      fm = "minres",
      scores = "tenBerge",
      warnings = FALSE
    )
  )

  factor_names <- paste0("F", seq_len(n_factors))
  score_df <- as.data.frame(unclass(fa_fit$scores))
  colnames(score_df) <- factor_names
  score_df$hex_id <- hex_ids
  score_df <- score_df |>
    relocate(hex_id) |>
    mutate(rotation = rotation_name)

  loadings_df <- as.data.frame(unclass(fa_fit$loadings))
  colnames(loadings_df) <- factor_names
  loadings_df$variable <- rownames(loadings_df)
  rownames(loadings_df) <- NULL
  loadings_df <- loadings_df |>
    select(variable, everything()) |>
    mutate(rotation = rotation_name, .before = 1)

  variance_df <- as.data.frame(unclass(fa_fit$Vaccounted))
  colnames(variance_df) <- factor_names
  variance_df$metric <- rownames(variance_df)
  rownames(variance_df) <- NULL
  variance_df <- variance_df |>
    select(metric, everything()) |>
    mutate(rotation = rotation_name, .before = 1)

  phi_df <- if (!is.null(fa_fit$Phi)) {
    phi <- as.data.frame(unclass(fa_fit$Phi))
    phi$factor_from <- rownames(phi)
    rownames(phi) <- NULL
    phi |>
      relocate(factor_from) |>
      mutate(rotation = rotation_name, .before = 1)
  } else {
    NULL
  }

  score_mat <- as.matrix(score_df[, factor_names, drop = FALSE])
  k_scores <- compute_k_scores(score_mat, k_candidates) |>
    mutate(rotation = rotation_name, .before = 1)

  cluster_assignments <- purrr::map_dfr(k_candidates, function(k) {
    set.seed(42)
    km_fit <- stats::kmeans(
      score_mat,
      centers = k,
      nstart = 50,
      iter.max = 500,
      algorithm = "Lloyd"
    )
    tibble::tibble(
      rotation = rotation_name,
      K = k,
      hex_id = score_df$hex_id,
      class_km = km_fit$cluster
    )
  })

  cluster_sizes <- cluster_assignments |>
    count(rotation, K, class_km, name = "n_hex") |>
    group_by(rotation, K) |>
    mutate(share = n_hex / sum(n_hex)) |>
    ungroup()

  top_loadings <- loadings_df |>
    pivot_longer(cols = all_of(factor_names), names_to = "factor", values_to = "loading") |>
    mutate(abs_loading = abs(loading)) |>
    group_by(rotation, factor) |>
    arrange(desc(abs_loading), .by_group = TRUE) |>
    slice_head(n = 15) |>
    ungroup()

  list(
    fa_fit = fa_fit,
    scores = score_df,
    loadings = loadings_df,
    variance = variance_df,
    phi = phi_df,
    k_scores = k_scores,
    cluster_assignments = cluster_assignments,
    cluster_sizes = cluster_sizes,
    top_loadings = top_loadings
  )
})
names(fit_results) <- rotations

factor_names <- paste0("F", seq_len(n_factors))
congruence_mat <- psych::factor.congruence(
  fit_results$varimax$fa_fit,
  fit_results$oblimin$fa_fit
)
congruence_df <- as.data.frame(unclass(congruence_mat))
congruence_df$varimax_factor <- rownames(congruence_df)
rownames(congruence_df) <- NULL
congruence_df <- congruence_df |>
  relocate(varimax_factor)

matched_congruence <- purrr::map_dfr(seq_len(nrow(congruence_mat)), function(i) {
  j <- which.max(abs(congruence_mat[i, ]))
  tibble::tibble(
    varimax_factor = rownames(congruence_mat)[i],
    matched_oblimin_factor = colnames(congruence_mat)[j],
    congruence = unname(congruence_mat[i, j])
  )
})

all_scores <- bind_rows(purrr::map(fit_results, "scores"))
all_loadings <- bind_rows(purrr::map(fit_results, "loadings"))
all_variance <- bind_rows(purrr::map(fit_results, "variance"))
all_k_scores <- bind_rows(purrr::map(fit_results, "k_scores"))
all_cluster_assignments <- bind_rows(purrr::map(fit_results, "cluster_assignments"))
all_cluster_sizes <- bind_rows(purrr::map(fit_results, "cluster_sizes"))
all_top_loadings <- bind_rows(purrr::map(fit_results, "top_loadings"))
all_phi <- bind_rows(purrr::compact(purrr::map(fit_results, "phi")))

cluster_wide <- all_cluster_assignments |>
  filter(K %in% focus_k) |>
  mutate(model_id = paste(rotation, paste0("K", K), sep = "_")) |>
  select(hex_id, model_id, class_km) |>
  tidyr::pivot_wider(names_from = model_id, values_from = class_km)

comparison_pairs <- list(
  c("varimax_K5", "varimax_K6"),
  c("oblimin_K5", "oblimin_K6"),
  c("varimax_K5", "oblimin_K5"),
  c("varimax_K6", "oblimin_K6")
)

cluster_comparison <- purrr::map_dfr(comparison_pairs, function(pair) {
  left <- pair[[1]]
  right <- pair[[2]]
  tibble::tibble(
    comparison = paste(left, "vs", right),
    ari = adjusted_rand_index(cluster_wide[[left]], cluster_wide[[right]])
  )
})

focus_cluster_summary <- all_cluster_sizes |>
  filter(K %in% focus_k) |>
  group_by(rotation, K) |>
  summarise(
    largest_cluster_share = max(share, na.rm = TRUE),
    smallest_cluster_share = min(share, na.rm = TRUE),
    n_clusters = dplyr::n(),
    .groups = "drop"
  ) |>
  left_join(
    all_k_scores |>
      filter(K %in% focus_k) |>
      select(rotation, K, silhouette),
    by = c("rotation", "K")
  ) |>
  arrange(rotation, K)

write.csv(all_scores, file.path(out_dir, paste0(sensitivity_id, "_factor_scores.csv")), row.names = FALSE)
write.csv(all_loadings, file.path(out_dir, paste0(sensitivity_id, "_factor_loadings.csv")), row.names = FALSE)
write.csv(all_variance, file.path(out_dir, paste0(sensitivity_id, "_factor_variance.csv")), row.names = FALSE)
write.csv(all_k_scores, file.path(out_dir, paste0(sensitivity_id, "_k_scores.csv")), row.names = FALSE)
write.csv(all_cluster_assignments, file.path(out_dir, paste0(sensitivity_id, "_cluster_assignments.csv")), row.names = FALSE)
write.csv(all_cluster_sizes, file.path(out_dir, paste0(sensitivity_id, "_cluster_sizes.csv")), row.names = FALSE)
write.csv(all_top_loadings, file.path(out_dir, paste0(sensitivity_id, "_top_loadings.csv")), row.names = FALSE)
write.csv(congruence_df, file.path(out_dir, paste0(sensitivity_id, "_rotation_congruence.csv")), row.names = FALSE)
write.csv(matched_congruence, file.path(out_dir, paste0(sensitivity_id, "_rotation_matched_congruence.csv")), row.names = FALSE)
write.csv(cluster_comparison, file.path(out_dir, paste0(sensitivity_id, "_cluster_comparison.csv")), row.names = FALSE)
write.csv(focus_cluster_summary, file.path(out_dir, paste0(sensitivity_id, "_focus_cluster_summary.csv")), row.names = FALSE)
if (nrow(all_phi) > 0) {
  write.csv(all_phi, file.path(out_dir, paste0(sensitivity_id, "_phi.csv")), row.names = FALSE)
}

message("Finished v2.1 factor/cluster sensitivity analysis: ", sensitivity_id)
