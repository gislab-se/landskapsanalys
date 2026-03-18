suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(tidyr)
  library(stringr)
  library(purrr)
  library(psych)
  library(cluster)
  library(FNN)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
analysis_id <- Sys.getenv("LANDSKAPSANALYS_ANALYSIS_ID", unset = "landskapsanalys_17lager_res9")
analysis_subtitle <- Sys.getenv("LANDSKAPSANALYS_ANALYSIS_SUBTITLE", unset = "17 lager, R9")
archived_previous_version <- Sys.getenv("LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION", unset = "landskapsanalys_9lager_res9")
source_model_note <- Sys.getenv(
  "LANDSKAPSANALYS_SOURCE_MODEL_NOTE",
  unset = paste(
    "9-lagersbaslinjen utokad med kust, sjo, vatmark, hede, faktisk skog,",
    "hogsta hojd och ett kompletterande kulturmiljolager."
  )
)
input_csv <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv")
hex_gpkg <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_hex_44_combined.gpkg")
hex_layer <- "r9_hex_44_combined"
config_csv <- Sys.getenv(
  "LANDSKAPSANALYS_CONFIG_CSV",
  unset = file.path(repo_root, "script/landskapsanalys/config/landskapsanalys_17lager_res9_input_layers.csv")
)
out_dir <- Sys.getenv(
  "LANDSKAPSANALYS_OUT_DIR",
  unset = file.path(repo_root, "data/interim/landskapsanalys_versions", analysis_id)
)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
weight_strategy <- Sys.getenv("LANDSKAPSANALYS_WEIGHT_STRATEGY", unset = "raw_sum")
weight_quantile <- suppressWarnings(as.numeric(Sys.getenv("LANDSKAPSANALYS_WEIGHT_QUANTILE", unset = "0.99")))
if (!is.finite(weight_quantile)) {
  weight_quantile <- 0.99
}
weight_quantile <- max(0.50, min(weight_quantile, 0.9999))
weight_description <- Sys.getenv("LANDSKAPSANALYS_WEIGHT_DESCRIPTION", unset = "")
weight_rescale_mode <- Sys.getenv(
  "LANDSKAPSANALYS_WEIGHT_RESCALE_MODE",
  unset = if (identical(weight_strategy, "geometry_balanced_q99")) "n_input_layers" else "none"
)
if (!nzchar(weight_description)) {
  weight_description <- dplyr::case_when(
    weight_strategy == "raw_sum" ~ "Raw row-sum across selected signals",
    weight_strategy == "geometry_balanced_q99" ~ paste(
      "Per-layer robust scaling to the",
      paste0("q", format(weight_quantile, trim = TRUE)),
      "cap, then equal weighting across geometry types"
    ),
    TRUE ~ weight_strategy
  )
}

k_values_env <- Sys.getenv("LANDSKAPSANALYS_K_VALUES", unset = "")
k_values <- if (nzchar(k_values_env)) {
  parsed_k <- suppressWarnings(as.numeric(strsplit(k_values_env, ",")[[1]]))
  parsed_k <- sort(unique(parsed_k[is.finite(parsed_k) & parsed_k > 0]))
  if (length(parsed_k) == 0) {
    stop("Invalid LANDSKAPSANALYS_K_VALUES: ", k_values_env)
  }
  parsed_k
} else {
  c(10, 50, 100, 250, 1000)
}
n_factors <- 5
k_candidates <- 5:10

indicator_catalog <- read.csv(config_csv, stringsAsFactors = FALSE)
selected_cols <- stats::setNames(indicator_catalog$source_name, indicator_catalog$gc_name)

write.csv(
  indicator_catalog |>
    select(gc_name, source_name, display_name, geometry_type, theme, selection_note),
  file.path(out_dir, paste0(analysis_id, "_indicator_catalog.csv")),
  row.names = FALSE
)

analysis_metadata <- tibble::tibble(
  analysis_id = analysis_id,
  analysis_title = "Landskapsanalys: Bornholm R9",
  analysis_subtitle = analysis_subtitle,
  archived_previous_version = archived_previous_version,
  n_input_layers = nrow(indicator_catalog),
  purpose_statement = paste(
    "Analysen ska beskriva vilken landskapskaraktar Bornholm har idag",
    "och pa langre sikt ge ett robust underlag for acceptansbedomning",
    "vid etablering av vindkraft och solenergi."
  ),
  source_model_note = source_model_note,
  analysis_unit_mask = "Hexagoner med raw_total > 0 behalls som analysenheter; rena havshex tas bort fore kontextmatris och faktoranalys.",
  context_k_values = paste(k_values, collapse = ","),
  context_weight_strategy = weight_strategy,
  context_weight_quantile = weight_quantile,
  context_weight_description = weight_description,
  context_weight_rescale_mode = weight_rescale_mode,
  factor_method = "psych::fa fm=minres rotate=varimax scores=tenBerge",
  factor_count = n_factors,
  cluster_candidates = paste(k_candidates, collapse = ",")
)
write.csv(analysis_metadata, file.path(out_dir, paste0(analysis_id, "_metadata.csv")), row.names = FALSE)

message("Reading merged R9 matrix...")
raw_df <- read.csv(input_csv, check.names = FALSE)
selected <- raw_df |>
  select(hex_id, all_of(unname(selected_cols)))
colnames(selected) <- c("hex_id", names(selected_cols))

message("Reading R9 hex geometry...")
hex <- st_read(hex_gpkg, layer = hex_layer, quiet = TRUE) |>
  select(hex_id)
hex <- hex |>
  left_join(selected, by = "hex_id") |>
  mutate(across(all_of(names(selected_cols)), ~tidyr::replace_na(.x, 0)))

hex_proj <- st_transform(hex, 25832)
pts_proj <- st_point_on_surface(st_geometry(hex_proj))
coords <- st_coordinates(pts_proj)

points <- tibble::tibble(
  hex_id = hex$hex_id,
  east = coords[, 1],
  north = coords[, 2]
)

weight_name <- function(x) {
  x |>
    tolower() |>
    stringr::str_replace_all("[^a-z0-9]+", "_") |>
    stringr::str_replace_all("^_+|_+$", "")
}

normalize_signal_robust <- function(v, quantile_prob = 0.99) {
  v <- as.numeric(v)
  v[!is.finite(v)] <- 0
  pos_v <- v[v > 0]

  if (length(pos_v) == 0) {
    return(list(scaled = rep(0, length(v)), scale_cap = 0))
  }

  scale_cap <- as.numeric(stats::quantile(
    pos_v,
    probs = quantile_prob,
    na.rm = TRUE,
    names = FALSE,
    type = 8
  ))
  if (!is.finite(scale_cap) || scale_cap <= 0) {
    scale_cap <- max(pos_v, na.rm = TRUE)
  }
  if (!is.finite(scale_cap) || scale_cap <= 0) {
    scale_cap <- 1
  }

  list(
    scaled = pmax(0, pmin(v / scale_cap, 1)),
    scale_cap = scale_cap
  )
}

build_context_weights <- function(
  pop_df,
  indicator_catalog,
  strategy = "raw_sum",
  quantile_prob = 0.99,
  rescale_mode = "none"
) {
  signal_df <- pop_df |>
    select(all_of(indicator_catalog$gc_name))

  raw_total <- rowSums(signal_df, na.rm = TRUE)
  raw_total_sum <- sum(raw_total, na.rm = TRUE)
  diagnostics <- indicator_catalog |>
    mutate(
      raw_mean = vapply(signal_df, mean, numeric(1), na.rm = TRUE),
      raw_max = vapply(signal_df, max, numeric(1), na.rm = TRUE),
      scale_cap = NA_real_,
      scaled_mean = NA_real_
    )

  if (strategy == "raw_sum") {
    diagnostics$scale_cap <- diagnostics$raw_max
    diagnostics$scaled_mean <- diagnostics$raw_mean
    return(list(
      total = raw_total,
      raw_total = raw_total,
      total_base = raw_total,
      scale_factor = 1,
      geometry_scores = NULL,
      diagnostics = diagnostics
    ))
  }

  if (strategy != "geometry_balanced_q99") {
    stop("Unknown LANDSKAPSANALYS_WEIGHT_STRATEGY: ", strategy)
  }

  normalized_list <- lapply(indicator_catalog$gc_name, function(gc_name) {
    normalize_signal_robust(signal_df[[gc_name]], quantile_prob = quantile_prob)
  })
  names(normalized_list) <- indicator_catalog$gc_name

  normalized_df <- as.data.frame(
    setNames(lapply(normalized_list, `[[`, "scaled"), indicator_catalog$gc_name),
    check.names = FALSE
  )

  diagnostics$scale_cap <- vapply(normalized_list, `[[`, numeric(1), "scale_cap")
  diagnostics$scaled_mean <- vapply(normalized_df, mean, numeric(1), na.rm = TRUE)

  geometry_groups <- split(indicator_catalog$gc_name, indicator_catalog$geometry_type)
  geometry_scores <- purrr::imap_dfc(geometry_groups, function(cols, geometry_type) {
    tibble::tibble(
      !!paste0("weight_", weight_name(geometry_type)) := rowMeans(
        as.matrix(normalized_df[, cols, drop = FALSE]),
        na.rm = TRUE
      )
    )
  })

  total_base <- rowMeans(as.matrix(geometry_scores), na.rm = TRUE)
  base_total_sum <- sum(total_base, na.rm = TRUE)
  scale_factor <- dplyr::case_when(
    !is.finite(base_total_sum) || base_total_sum <= 0 ~ 1,
    identical(rescale_mode, "none") ~ 1,
    identical(rescale_mode, "match_raw_total_sum") ~ raw_total_sum / base_total_sum,
    identical(rescale_mode, "n_input_layers") ~ nrow(indicator_catalog),
    identical(rescale_mode, "target_mean_1") ~ 1 / mean(total_base, na.rm = TRUE),
    TRUE ~ NA_real_
  )
  if (!is.finite(scale_factor) || scale_factor <= 0) {
    stop("Unknown or invalid LANDSKAPSANALYS_WEIGHT_RESCALE_MODE: ", rescale_mode)
  }
  total <- total_base * scale_factor

  list(
    total = total,
    raw_total = raw_total,
    total_base = total_base,
    scale_factor = scale_factor,
    geometry_scores = geometry_scores,
    diagnostics = diagnostics
  )
}

pop_locations_full <- bind_cols(points, st_drop_geometry(hex) |> select(all_of(names(selected_cols))))
weight_info <- build_context_weights(
  pop_locations_full,
  indicator_catalog,
  strategy = weight_strategy,
  quantile_prob = weight_quantile,
  rescale_mode = weight_rescale_mode
)
if (!is.null(weight_info$geometry_scores)) {
  pop_locations_full <- bind_cols(pop_locations_full, weight_info$geometry_scores)
}
pop_locations_full <- pop_locations_full |>
  mutate(
    total_raw = weight_info$raw_total,
    total_base = weight_info$total_base,
    total = weight_info$total
  )

write.csv(
  weight_info$diagnostics,
  file.path(out_dir, paste0(analysis_id, "_weight_diagnostics.csv")),
  row.names = FALSE
)

analysis_mask <- pop_locations_full$total_raw > 0
removed_hex <- tibble::tibble(
  hex_id = pop_locations_full$hex_id[!analysis_mask],
  total_raw = pop_locations_full$total_raw[!analysis_mask],
  total = pop_locations_full$total[!analysis_mask]
)
write.csv(
  removed_hex,
  file.path(out_dir, paste0(analysis_id, "_excluded_zero_signal_hex.csv")),
  row.names = FALSE
)

hex <- hex[analysis_mask, ]
points <- points[analysis_mask, , drop = FALSE]
pop_locations <- pop_locations_full[analysis_mask, , drop = FALSE]

message(sprintf(
  "Keeping %s analysis hex and excluding %s zero-signal hex before context modeling",
  nrow(points),
  nrow(removed_hex)
))

choose_nn <- function(coords_mat, weights, target_k, start_k = 64) {
  current_k <- min(nrow(coords_mat), start_k)
  repeat {
    nn <- FNN::get.knnx(data = coords_mat, query = coords_mat, k = current_k)
    reach <- apply(nn$nn.index, 1, function(ii) {
      cs <- cumsum(weights[ii])
      hit <- which(cs >= target_k)[1]
      ifelse(is.na(hit), Inf, hit)
    })
    if (all(is.finite(reach))) {
      return(list(nn = nn, reach = reach, k = current_k))
    }
    if (current_k >= nrow(coords_mat)) {
      stop(sprintf("Could not reach target_k=%s even using all neighbours", target_k))
    }
    current_k <- min(nrow(coords_mat), current_k * 2)
  }
}

compute_context <- function(points_df, pop_df, groups, weight_col = "total", k_values = c(10, 50, 100, 250, 1000)) {
  weights <- pop_df[[weight_col]]
  coords_mat <- as.matrix(points_df[, c("east", "north")])
  nn_info <- choose_nn(coords_mat, weights, target_k = max(k_values), start_k = 64)
  idx_mat <- nn_info$nn$nn.index
  dist_mat <- nn_info$nn$nn.dist

  results <- vector("list", nrow(points_df))
  for (i in seq_len(nrow(points_df))) {
    idx <- idx_mat[i, ]
    w <- weights[idx]
    cs <- cumsum(w)
    row_out <- list()
    for (k_val in k_values) {
      reach <- which(cs >= k_val)[1]
      sel_idx <- idx[seq_len(reach)]
      sel_w <- weights[sel_idx]
      row_out[[paste0("radius_k", k_val)]] <- dist_mat[i, reach]
      row_out[[paste0("total_k", k_val)]] <- sum(sel_w)
      for (group in groups) {
        vals <- pop_df[[group]][sel_idx]
        w_mean <- if (sum(sel_w) > 0) weighted.mean(vals, sel_w) else mean(vals)
        w_var <- if (sum(sel_w) > 0) weighted.mean((vals - w_mean)^2, sel_w) else stats::var(vals)
        if (is.na(w_var)) w_var <- 0
        row_out[[paste0("mean_", group, "_k", k_val)]] <- w_mean
        row_out[[paste0("std_", group, "_k", k_val)]] <- sqrt(w_var)
      }
    }
    results[[i]] <- row_out
  }

  bind_cols(points_df, pop_df |> select(all_of(groups), all_of(weight_col)), bind_rows(results))
}

message("Computing multiscalar context variables...")
points_with_context <- compute_context(points, pop_locations, groups = names(selected_cols), k_values = k_values)
weight_extra_cols <- c("total_raw", "total_base", grep("^weight_", names(pop_locations), value = TRUE))
if (length(weight_extra_cols) > 0) {
  points_with_context <- points_with_context |>
    left_join(pop_locations |> select(hex_id, all_of(weight_extra_cols)), by = "hex_id")
}
write.csv(points_with_context, file.path(out_dir, paste0(analysis_id, "_points_with_context.csv")), row.names = FALSE)

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

message(sprintf("Factor matrix shape after cleaning: %s rows x %s cols", nrow(Xz_clean), ncol(Xz_clean)))

set.seed(42)
fa_fit <- suppressWarnings(
  psych::fa(
    Xz_clean,
    nfactors = n_factors,
    rotate = "varimax",
    fm = "minres",
    scores = "tenBerge",
    warnings = FALSE
  )
)

factor_names <- paste0("F", seq_len(n_factors))
scores_df <- as.data.frame(unclass(fa_fit$scores))
colnames(scores_df) <- factor_names
scores_df$hex_id <- points_with_context$hex_id[row_keep]
scores_df <- scores_df |>
  relocate(hex_id)

loadings_df <- as.data.frame(unclass(fa_fit$loadings))
colnames(loadings_df) <- factor_names
loadings_df$variable <- rownames(loadings_df)
rownames(loadings_df) <- NULL
loadings_df <- loadings_df |>
  select(variable, everything())
write.csv(loadings_df, file.path(out_dir, paste0(analysis_id, "_factor_loadings.csv")), row.names = FALSE)

variance_df <- as.data.frame(unclass(fa_fit$Vaccounted))
colnames(variance_df) <- factor_names
variance_df$metric <- rownames(variance_df)
rownames(variance_df) <- NULL
variance_df <- variance_df |>
  select(metric, everything())
write.csv(variance_df, file.path(out_dir, paste0(analysis_id, "_factor_variance.csv")), row.names = FALSE)

score_mat <- as.matrix(scores_df[, factor_names, drop = FALSE])

message("Computing silhouette scores across K candidates...")
dist_basis <- tryCatch(stats::dist(score_mat), error = function(e) NULL)
sample_idx <- NULL
sil_basis <- "full"
if (is.null(dist_basis)) {
  sil_basis <- "sample"
  sample_idx <- sort(sample(seq_len(nrow(score_mat)), min(3000, nrow(score_mat))))
  dist_basis <- stats::dist(score_mat[sample_idx, , drop = FALSE])
}

k_scores <- purrr::map_dfr(k_candidates, function(k) {
  km_try <- stats::kmeans(score_mat, centers = k, nstart = 50, iter.max = 100)
  if (length(unique(km_try$cluster)) > 1) {
    sil <- if (sil_basis == "full") {
      cluster::silhouette(km_try$cluster, dist_basis)
    } else {
      cluster::silhouette(km_try$cluster[sample_idx], dist_basis)
    }
    sil_score <- mean(sil[, "sil_width"])
  } else {
    sil_score <- NA_real_
  }
  tibble::tibble(K = k, silhouette = sil_score, silhouette_basis = sil_basis)
}) |>
  arrange(desc(silhouette))
write.csv(k_scores, file.path(out_dir, paste0(analysis_id, "_k_scores.csv")), row.names = FALSE)

K_BEST <- k_scores$K[[1]]
message(sprintf("Selected K_BEST=%s", K_BEST))
final_km <- stats::kmeans(score_mat, centers = K_BEST, nstart = 50, iter.max = 100)

factor_scores <- scores_df |>
  mutate(class_km = final_km$cluster)
write.csv(factor_scores, file.path(out_dir, paste0(analysis_id, "_factor_scores.csv")), row.names = FALSE)

cluster_profile <- factor_scores |>
  group_by(class_km) |>
  summarise(across(all_of(factor_names), ~mean(.x, na.rm = TRUE)), n_hex = dplyr::n(), .groups = "drop")
write.csv(cluster_profile, file.path(out_dir, paste0(analysis_id, "_cluster_profile.csv")), row.names = FALSE)

cluster_sizes <- factor_scores |>
  count(class_km, name = "n_hex") |>
  mutate(share = n_hex / sum(n_hex))
write.csv(cluster_sizes, file.path(out_dir, paste0(analysis_id, "_cluster_sizes.csv")), row.names = FALSE)

points_with_model <- points_with_context |>
  left_join(factor_scores, by = "hex_id")
write.csv(points_with_model, file.path(out_dir, paste0(analysis_id, "_points_with_context_and_scores.csv")), row.names = FALSE)

hex_model <- hex |>
  left_join(points_with_model, by = c("hex_id", names(selected_cols)))
out_gpkg <- file.path(out_dir, paste0(analysis_id, "_hex.gpkg"))
if (file.exists(out_gpkg)) invisible(file.remove(out_gpkg))
st_write(hex_model, out_gpkg, layer = analysis_id, quiet = TRUE)

run_summary <- tibble::tibble(
  metric = c(
    "analysis_id",
    "n_hex",
    "n_input_layers",
    "n_context_columns",
    "n_factor_columns",
    "k_best",
    "weight_strategy",
    "weight_quantile",
    "weight_rescale_mode",
    "weight_rescale_factor",
    "raw_total_sum",
    "base_total_sum",
    "total_weight_sum",
    "zero_raw_total_hex",
    "zero_total_hex",
    "excluded_zero_signal_hex"
  ),
  value = c(
    analysis_id,
    nrow(points_with_context),
    length(selected_cols),
    ncol(X),
    ncol(score_mat),
    K_BEST,
    weight_strategy,
    weight_quantile,
    weight_rescale_mode,
    weight_info$scale_factor,
    sum(pop_locations$total_raw, na.rm = TRUE),
    sum(pop_locations$total_base, na.rm = TRUE),
    sum(pop_locations$total, na.rm = TRUE),
    sum(pop_locations$total_raw <= 0, na.rm = TRUE),
    sum(pop_locations$total <= 0, na.rm = TRUE),
    nrow(removed_hex)
  )
)
write.csv(run_summary, file.path(out_dir, paste0(analysis_id, "_run_summary.csv")), row.names = FALSE)

message("Finished R9 landscape analysis run: ", analysis_id)
