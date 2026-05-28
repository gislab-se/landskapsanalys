suppressPackageStartupMessages({
  library(dplyr)
  library(h3jsr)
  library(jsonlite)
  library(sf)
})

repo_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
repo_path <- function(...) file.path(repo_root, ...)

out_dir <- repo_path("docs", "geocontext", "exports", "bornholm_res10_hex_variables")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

out_csv <- file.path(out_dir, "bornholm_res10_hex_variables.csv")
out_codebook <- file.path(out_dir, "bornholm_res10_hex_variables_codebook.csv")
out_summary <- file.path(out_dir, "bornholm_res10_hex_variables_summary.csv")

landscape_manifest_path <- repo_path(
  "apps", "potential_model", "manifests", "landscape", "bornholm_landscape_v10.json"
)
landscape_geojson <- repo_path(
  "docs", "geocontext", "model_comparisons", "bornholm_v10_landscape_types",
  "map", "bornholm_v10_landscape_types_map_data.geojson"
)
land_share_csv <- repo_path(
  "docs", "geocontext", "potential_framework", "data", "bornholm_landmask",
  "bornholm_h3_land_share.csv"
)
acceptance_csv <- repo_path(
  "docs", "geocontext", "potential_framework", "data", "social_acceptance",
  "bornholm_synthetic_social_acceptance_r10.csv"
)
solar_markblokke_csv <- repo_path(
  "docs", "geocontext", "potential_framework", "data",
  "bornholm_solar_large_scale_markblokke", "h3_r10_area_share",
  "markblokke_bornholm_outside_population_000m_h3_r10_area_share.csv"
)
v32_dir <- repo_path(
  "docs", "geocontext", "model_comparisons", "data",
  "landskapsanalys_v3_2_contourterrain68_res9"
)
v32_raw_csv <- file.path(v32_dir, "landskapsanalys_v3_2_contourterrain68_res9_raw_augmented.csv")
v32_context_csv <- file.path(v32_dir, "landskapsanalys_v3_2_contourterrain68_res9_points_with_context.csv")
v32_factor_scores_csv <- file.path(v32_dir, "landskapsanalys_v3_2_contourterrain68_res9_factor_scores.csv")
v32_indicator_catalog_csv <- file.path(v32_dir, "landskapsanalys_v3_2_contourterrain68_res9_indicator_catalog.csv")

stop_if_missing <- function(paths) {
  missing <- paths[!file.exists(paths)]
  if (length(missing) > 0) {
    stop("Missing required input files:\n", paste(missing, collapse = "\n"), call. = FALSE)
  }
}

stop_if_missing(c(
  landscape_manifest_path,
  landscape_geojson,
  land_share_csv,
  acceptance_csv,
  solar_markblokke_csv,
  v32_raw_csv,
  v32_context_csv,
  v32_factor_scores_csv,
  v32_indicator_catalog_csv
))

rel_path <- function(path) {
  out <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", gsub("([\\^$.|?*+(){}\\[\\]\\\\])", "\\\\\\1", repo_root), "/?"), "", out)
}

prefix_columns <- function(frame, prefix, key = "hex_id") {
  names(frame) <- ifelse(names(frame) == key, names(frame), paste0(prefix, names(frame)))
  frame
}

infer_unit <- function(column) {
  dplyr::case_when(
    grepl("(^|_)east$|(^|_)north$", column) ~ "m",
    grepl("_area_m2$|_area_m2_", column) ~ "m2",
    grepl("_area_km2$|_area_km2_", column) ~ "km2",
    grepl("_length_m$|_length_m_", column) ~ "m",
    grepl("_elevation_m$|_relief_m$|_point_m$|_depth_max_m$|_height_m$|_m$", column) ~ "m",
    grepl("_slope_deg$|_deg$", column) ~ "degrees",
    grepl("_share_pct$|_pct$", column) ~ "percent",
    grepl("_share$|_share_", column) ~ "ratio",
    grepl("_count$|_count_", column) ~ "count",
    grepl("_score$|^F[0-9]+$|_F[0-9]+$", column) ~ "score",
    TRUE ~ ""
  )
}

metric_lookup <- function(names_vec, indicator_catalog) {
  gc_lookup <- setNames(indicator_catalog$display_name, indicator_catalog$gc_name)
  source_lookup <- setNames(indicator_catalog$display_name, indicator_catalog$source_name)
  theme_lookup <- setNames(indicator_catalog$theme, indicator_catalog$gc_name)
  geometry_lookup <- setNames(indicator_catalog$geometry_type, indicator_catalog$gc_name)

  lapply(names_vec, function(value) {
    source_col <- value
    normalized <- sub("^parent_r9_raw_", "", source_col)
    normalized <- sub("^parent_r9_context_", "", normalized)
    normalized <- sub("^parent_r9_v32_", "", normalized)
    normalized <- sub("^mean_", "", normalized)
    normalized <- sub("^std_", "", normalized)
    normalized <- sub("_k[0-9]+$", "", normalized)

    description <- ""
    theme <- ""
    geometry_type <- ""

    if (normalized %in% names(source_lookup)) {
      description <- unname(source_lookup[[normalized]])
      idx <- match(normalized, indicator_catalog$source_name)
      theme <- indicator_catalog$theme[[idx]]
      geometry_type <- indicator_catalog$geometry_type[[idx]]
    } else if (normalized %in% names(gc_lookup)) {
      description <- unname(gc_lookup[[normalized]])
      theme <- unname(theme_lookup[[normalized]])
      geometry_type <- unname(geometry_lookup[[normalized]])
    }

    if (grepl("^parent_r9_context_mean_", source_col)) {
      description <- paste("Neighborhood mean:", description)
    } else if (grepl("^parent_r9_context_std_", source_col)) {
      description <- paste("Neighborhood standard deviation:", description)
    } else if (grepl("^parent_r9_context_radius_k[0-9]+$", source_col)) {
      description <- "Neighborhood radius used by the v3.2 context model."
    } else if (grepl("^parent_r9_context_total", source_col)) {
      description <- "Combined weighted signal total from the v3.2 context model."
    } else if (grepl("^parent_r9_context_weight_", source_col)) {
      description <- "Weight diagnostic from the v3.2 context model."
    } else if (grepl("^parent_r9_v32_F[0-9]+$", source_col)) {
      description <- "Parent res9 v3.2 factor score."
    } else if (identical(source_col, "parent_r9_v32_class_km")) {
      description <- "Parent res9 v3.2 k-means class."
    }

    if (!nzchar(description)) {
      description <- source_col
    }

    list(
      description = description,
      theme = theme,
      geometry_type = geometry_type
    )
  })
}

make_codebook <- function(columns, indicator_catalog, manifest) {
  factor_labels <- manifest$factor_labels
  cluster_labels <- manifest$cluster_labels
  landscape_type_labels <- manifest$landscape_type_labels

  base_description <- c(
    hex_id = "H3 res10 cell id.",
    h3_resolution = "H3 resolution of the row geometry.",
    h3_parent_res9 = "Parent H3 res9 cell used to attach v3.2/v4 parent variables.",
    class_k8 = "v9 K=8 cluster assigned to the res10 cell.",
    F1 = factor_labels$F1 %||% "Factor 1 score.",
    F2 = factor_labels$F2 %||% "Factor 2 score.",
    F3 = factor_labels$F3 %||% "Factor 3 score.",
    F4 = factor_labels$F4 %||% "Factor 4 score.",
    F5 = factor_labels$F5 %||% "Factor 5 score.",
    v10_type_id = "Interpreted v10 landscape type id.",
    v10_type_name = "Interpreted v10 landscape type name.",
    v10_type_name_en = "Interpreted v10 landscape type name in English.",
    v10_rule = "Rule text used to translate v9 cluster/factor signal into v10 type.",
    v10_rule_en = "English rule text used to translate v9 cluster/factor signal into v10 type.",
    v10_confidence = "Qualitative confidence for the v10 interpretation.",
    land_area_m2 = "Land area inside the full H3 cell according to the current Bornholm landmask.",
    land_area_km2 = "Land area inside the full H3 cell according to the current Bornholm landmask.",
    hex_area_m2 = "Full H3 cell area.",
    hex_area_km2 = "Full H3 cell area.",
    land_share = "Land area divided by full H3 cell area.",
    land_share_pct = "Land area divided by full H3 cell area.",
    water_share_pct = "Water share inferred as 100 - land_share_pct.",
    water_area_m2 = "Water area inferred as full H3 cell area minus land area.",
    water_area_km2 = "Water area inferred as full H3 cell area minus land area.",
    land_share_source = "Source path for the landmask calculation.",
    land_share_reason = "Short interpretation of the land/water split.",
    acceptance_low = "Synthetic low social acceptance score.",
    acceptance_medium = "Synthetic medium social acceptance score.",
    acceptance_high = "Synthetic high social acceptance score.",
    data_status = "Status note for the social acceptance data.",
    method_version = "Method version for the social acceptance data.",
    solar_markblokke_000m_hex_area_m2 = "Full H3 cell area from the 0 m markblokke solar source table.",
    solar_markblokke_000m_potential_area_m2 = "Potential markblokke area outside the population buffer at 0 m.",
    solar_markblokke_000m_potential_area_km2 = "Potential markblokke area outside the population buffer at 0 m.",
    solar_markblokke_000m_potential_area_share_pct = "Potential markblokke area share outside the population buffer at 0 m."
  )

  source_file_for <- function(column) {
    dplyr::case_when(
      column %in% c("hex_id", "h3_resolution", "h3_parent_res9", "class_k8", "F1", "F2", "F3", "F4", "F5", "v10_type_id", "v10_type_name", "v10_type_name_en", "v10_rule", "v10_rule_en", "v10_confidence") ~ rel_path(landscape_geojson),
      grepl("^land_|^hex_area_|^water_|^land_share", column) ~ rel_path(land_share_csv),
      column %in% c("acceptance_low", "acceptance_medium", "acceptance_high", "data_status", "method_version") ~ rel_path(acceptance_csv),
      grepl("^solar_markblokke_000m_", column) ~ rel_path(solar_markblokke_csv),
      grepl("^parent_r9_raw_", column) ~ rel_path(v32_raw_csv),
      grepl("^parent_r9_context_", column) ~ rel_path(v32_context_csv),
      grepl("^parent_r9_v32_", column) ~ rel_path(v32_factor_scores_csv),
      TRUE ~ ""
    )
  }

  source_resolution_for <- function(column) {
    dplyr::case_when(
      column %in% c("hex_id", "h3_resolution", "class_k8", "F1", "F2", "F3", "F4", "F5", "v10_type_id", "v10_type_name", "v10_type_name_en", "v10_rule", "v10_rule_en", "v10_confidence") ~ "10",
      column == "h3_parent_res9" ~ "derived from res10",
      grepl("^parent_r9_", column) ~ "9 parent",
      TRUE ~ "10"
    )
  }

  provenance_for <- function(column) {
    dplyr::case_when(
      grepl("^parent_r9_", column) ~ "Attached from parent H3 res9 cell and repeated for each res10 child; not recomputed at res10 in this export.",
      grepl("^solar_markblokke_000m_", column) ~ "Joined from the res10 markblokke area-share export; missing cells are filled with zero potential area.",
      column %in% c("water_area_m2", "water_area_km2") ~ "Derived in this export from hex_area minus land_area.",
      TRUE ~ ""
    )
  }

  lookups <- metric_lookup(columns, indicator_catalog)

  tibble::tibble(
    column = columns,
    description = vapply(seq_along(columns), function(i) {
      col <- columns[[i]]
      if (col %in% names(base_description)) {
        unname(base_description[[col]])
      } else {
        lookups[[i]]$description
      }
    }, character(1)),
    unit = vapply(columns, infer_unit, character(1)),
    source_resolution = vapply(columns, source_resolution_for, character(1)),
    source_file = vapply(columns, source_file_for, character(1)),
    source_column = vapply(columns, function(col) {
      col |>
        sub("^parent_r9_raw_", "", x = _) |>
        sub("^parent_r9_context_", "", x = _) |>
        sub("^parent_r9_v32_", "", x = _) |>
        sub("^solar_markblokke_000m_", "", x = _)
    }, character(1)),
    theme = vapply(lookups, `[[`, character(1), "theme"),
    geometry_type = vapply(lookups, `[[`, character(1), "geometry_type"),
    provenance_note = vapply(columns, provenance_for, character(1))
  )
}

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0) y else x
}

message("Reading res10 landscape cells")
landscape_manifest <- jsonlite::fromJSON(landscape_manifest_path, simplifyVector = FALSE)
res10_landscape <- st_read(landscape_geojson, quiet = TRUE) |>
  st_drop_geometry() |>
  mutate(
    hex_id = as.character(hex_id),
    h3_resolution = 10L,
    h3_parent_res9 = as.character(get_parent(hex_id, res = 9, simple = TRUE))
  ) |>
  relocate(hex_id, h3_resolution, h3_parent_res9)

message("Reading res10 land/water shares")
land_share <- read.csv(land_share_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  filter(h3_resolution == 10) |>
  mutate(
    hex_id = as.character(hex_id),
    water_area_m2 = pmax(hex_area_m2 - land_area_m2, 0),
    water_area_km2 = water_area_m2 / 1e6
  ) |>
  select(
    hex_id,
    land_area_m2,
    land_area_km2,
    hex_area_m2,
    hex_area_km2,
    land_share,
    land_share_pct,
    water_share_pct,
    water_area_m2,
    water_area_km2,
    land_share_source,
    land_share_reason
  )

message("Reading res10 synthetic acceptance")
acceptance <- read.csv(acceptance_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  filter(h3_resolution == 10) |>
  mutate(hex_id = as.character(hex_id)) |>
  select(-h3_resolution)

message("Reading res10 solar markblokke area share")
solar_markblokke <- read.csv(solar_markblokke_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  mutate(hex_id = as.character(hex_id)) |>
  rename(
    solar_markblokke_000m_hex_area_m2 = hex_area_m2,
    solar_markblokke_000m_potential_area_m2 = potential_area_m2,
    solar_markblokke_000m_potential_area_km2 = potential_area_km2,
    solar_markblokke_000m_potential_area_share_pct = potential_area_share_pct
  )

message("Reading parent res9 v3.2 raw variables")
v32_raw <- read.csv(v32_raw_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  mutate(hex_id = as.character(hex_id)) |>
  prefix_columns("parent_r9_raw_")

message("Reading parent res9 v3.2 context variables")
v32_context <- read.csv(v32_context_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  mutate(hex_id = as.character(hex_id)) |>
  prefix_columns("parent_r9_context_")

message("Reading parent res9 v3.2 factor scores")
v32_factor_scores <- read.csv(v32_factor_scores_csv, stringsAsFactors = FALSE, check.names = FALSE) |>
  mutate(hex_id = as.character(hex_id)) |>
  prefix_columns("parent_r9_v32_")

indicator_catalog <- read.csv(v32_indicator_catalog_csv, stringsAsFactors = FALSE, check.names = FALSE)

message("Joining export frame")
export_frame <- res10_landscape |>
  left_join(land_share, by = "hex_id") |>
  left_join(acceptance, by = "hex_id") |>
  left_join(solar_markblokke, by = "hex_id") |>
  left_join(v32_raw, by = c("h3_parent_res9" = "hex_id")) |>
  left_join(v32_context, by = c("h3_parent_res9" = "hex_id")) |>
  left_join(v32_factor_scores, by = c("h3_parent_res9" = "hex_id"))

solar_zero_cols <- c(
  "solar_markblokke_000m_potential_area_m2",
  "solar_markblokke_000m_potential_area_km2",
  "solar_markblokke_000m_potential_area_share_pct"
)
for (column in solar_zero_cols) {
  export_frame[[column]][is.na(export_frame[[column]])] <- 0
}

if ("solar_markblokke_000m_hex_area_m2" %in% names(export_frame)) {
  export_frame$solar_markblokke_000m_hex_area_m2[
    is.na(export_frame$solar_markblokke_000m_hex_area_m2)
  ] <- export_frame$hex_area_m2[is.na(export_frame$solar_markblokke_000m_hex_area_m2)]
}

codebook <- make_codebook(names(export_frame), indicator_catalog, landscape_manifest)

summary <- tibble::tibble(
  metric = c(
    "rows",
    "columns",
    "unique_hex_id",
    "duplicate_hex_id",
    "missing_land_share",
    "missing_acceptance_medium",
    "missing_solar_potential_area_after_zero_fill",
    "missing_parent_r9_raw",
    "missing_parent_r9_context",
    "missing_parent_r9_factor_scores",
    "source_res10_landscape_features",
    "source_res10_land_share_rows",
    "source_res10_acceptance_rows",
    "source_res10_solar_markblokke_rows",
    "source_parent_r9_raw_rows",
    "source_parent_r9_context_rows",
    "source_parent_r9_factor_score_rows"
  ),
  value = as.character(c(
    nrow(export_frame),
    ncol(export_frame),
    length(unique(export_frame$hex_id)),
    anyDuplicated(export_frame$hex_id),
    sum(is.na(export_frame$land_share)),
    sum(is.na(export_frame$acceptance_medium)),
    sum(is.na(export_frame$solar_markblokke_000m_potential_area_m2)),
    sum(is.na(export_frame$parent_r9_raw_fastboendebefolkningmapinfo_count)),
    sum(is.na(export_frame$parent_r9_context_gc_fastboende_count)),
    sum(is.na(export_frame$parent_r9_v32_F1)),
    nrow(res10_landscape),
    nrow(land_share),
    nrow(acceptance),
    nrow(solar_markblokke),
    nrow(v32_raw),
    nrow(v32_context),
    nrow(v32_factor_scores)
  ))
)

message("Writing CSV export")
write.csv(export_frame, out_csv, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(codebook, out_codebook, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(summary, out_summary, row.names = FALSE, fileEncoding = "UTF-8")

message("Wrote ", nrow(export_frame), " rows and ", ncol(export_frame), " columns to ", out_csv)
message("Wrote codebook to ", out_codebook)
message("Wrote summary to ", out_summary)
