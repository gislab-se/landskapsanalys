suppressPackageStartupMessages({
  library(dplyr)
  library(jsonlite)
  library(readr)
  library(sf)
  library(tibble)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
registry_path <- Sys.getenv(
  "ACCEPTANCE_REGISTRY_PATH",
  unset = file.path(repo_root, "apps", "acceptance_model", "registry_bornholm.json")
)

if (!file.exists(registry_path)) {
  stop("Registry not found: ", registry_path)
}

source(file.path(repo_root, "script", "semi_manual_r9", "lib", "subcategory_splits.R"))

registry <- jsonlite::fromJSON(registry_path, simplifyVector = TRUE)
layer_config <- read.csv(file.path(repo_root, registry$source_config_csv), stringsAsFactors = FALSE, fileEncoding = "UTF-8")
working_epsg <- if (!is.null(registry$native_crs_epsg)) as.integer(registry$native_crs_epsg[[1]]) else 25833L
landmask_label <- if (!is.null(registry$landmask_label)) as.character(registry$landmask_label[[1]]) else "Bornholm DAGI landmass"

asset_dir <- file.path(repo_root, registry$asset_dir)
analysis_rds_dir <- file.path(asset_dir, "analysis_rds")
landmask_dir <- file.path(asset_dir, "landmask")
dir.create(analysis_rds_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(landmask_dir, recursive = TRUE, showWarnings = FALSE)

to_repo_relative <- function(path) {
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  normalized_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalized_root, "/?"), "", normalized_path)
}

layer_path <- function(layer_key) {
  path <- layer_config$source_path[layer_config$layer_key == layer_key][1]
  if (is.na(path) || !nzchar(path)) {
    return(NA_character_)
  }
  path
}

load_landmask <- function() {
  if (!is.null(registry$landmask_source_path) && nzchar(as.character(registry$landmask_source_path[[1]]))) {
    landmask_path <- as.character(registry$landmask_source_path[[1]])
  } else {
    landmask_path <- layer_path(registry$landmask_layer_key[[1]])
  }

  if (is.na(landmask_path) || !file.exists(landmask_path)) {
    stop("Landmask source not found: ", landmask_path)
  }

  landmask_sf <- st_read(landmask_path, quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM")) |>
    st_make_valid() |>
    st_transform(working_epsg)

  st_sf(mask_id = landmask_label, geometry = st_sfc(st_union(landmask_sf), crs = working_epsg)) |>
    st_make_valid()
}

landmask_sf <- load_landmask()
landmask_geom <- st_geometry(landmask_sf)
saveRDS(landmask_sf, file.path(landmask_dir, "bornholm_landmass.rds"), compress = FALSE)

clip_to_landmass <- function(x) {
  if (nrow(x) == 0) {
    return(x)
  }
  suppressWarnings(st_intersection(st_make_valid(x), landmask_sf)) |>
    st_make_valid()
}

clip_geom_to_landmass <- function(geom) {
  geom_sfc <- if (inherits(geom, "sfc")) geom else st_sfc(geom, crs = working_epsg)
  clipped <- suppressWarnings(st_intersection(st_make_valid(geom_sfc), landmask_geom))
  st_make_valid(clipped)
}

apply_registry_filter <- function(source_sf, spec) {
  if (!"filter_field" %in% names(spec) || !"filter_value" %in% names(spec)) {
    return(source_sf)
  }

  filter_field <- as.character(spec$filter_field[[1]])
  filter_value <- as.character(spec$filter_value[[1]])
  filter_mode <- if ("filter_mode" %in% names(spec)) as.character(spec$filter_mode[[1]]) else "field_equals"

  if (is.na(filter_field) || !nzchar(filter_field) || is.na(filter_value) || !nzchar(filter_value)) {
    return(source_sf)
  }

  subset_source_by_split(
    source_layer = source_sf,
    split_field = filter_field,
    split_value = filter_value,
    input_filter_mode = filter_mode
  )
}

build_analysis_asset <- function(source_sf, spec) {
  if (spec$id[[1]] == "population_points") {
    analysis_geom <- st_union(st_buffer(source_sf, dist = 100, nQuadSegs = 4))
    base_buffer_m <- 100L
  } else {
    analysis_geom <- st_union(st_geometry(source_sf))
    base_buffer_m <- 0L
  }

  analysis_geom <- st_make_valid(analysis_geom)
  analysis_geom <- suppressWarnings(st_simplify(st_sfc(analysis_geom, crs = working_epsg), dTolerance = 20, preserveTopology = TRUE))
  analysis_geom <- clip_geom_to_landmass(analysis_geom)
  analysis_sf <- st_sf(
    tibble(
      layer_id = spec$id[[1]],
      label = spec$label[[1]],
      analysis_base_buffer_m = base_buffer_m
    ),
    geometry = analysis_geom
  )
  list(sf = analysis_sf, base_buffer_m = base_buffer_m)
}

manifest_path <- file.path(asset_dir, "asset_manifest.csv")
if (!file.exists(manifest_path)) {
  stop("Asset manifest not found: ", manifest_path)
}

manifest <- readr::read_csv(manifest_path, show_col_types = FALSE)
if (!"analysis_rds_path" %in% names(manifest)) {
  manifest$analysis_rds_path <- NA_character_
}
if (!"analysis_base_buffer_m" %in% names(manifest)) {
  manifest$analysis_base_buffer_m <- 0L
}

report_rows <- list()

for (i in seq_len(nrow(registry$layers))) {
  spec <- registry$layers[i, ]
  layer_id <- spec$id[[1]]
  source_path <- layer_path(spec$layer_key[[1]])
  manifest_idx <- which(manifest$layer_id == layer_id)[1]

  message("Building analysis RDS for ", layer_id, " ...")

  if (is.na(source_path) || !file.exists(source_path)) {
    report_rows[[length(report_rows) + 1]] <- tibble(layer_id = layer_id, status = "missing_source", message = source_path)
    next
  }

  result <- tryCatch(
    {
      source_sf <- st_read(source_path, quiet = TRUE) |>
        suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
      if (is.na(st_crs(source_sf))) {
        st_crs(source_sf) <- working_epsg
      }
      source_sf <- source_sf |>
        st_make_valid() |>
        st_transform(working_epsg)

      source_sf <- apply_registry_filter(source_sf, spec)
      source_sf <- clip_to_landmass(source_sf)
      source_sf <- source_sf[!st_is_empty(source_sf), ]

      if (nrow(source_sf) == 0) {
        if (!is.na(manifest_idx)) {
          manifest$analysis_rds_path[manifest_idx] <- NA_character_
          manifest$analysis_base_buffer_m[manifest_idx] <- 0L
        }
        tibble(layer_id = layer_id, status = "empty_after_filter", message = "No features after filtering and DAGI clipping.")
      } else {
        analysis_asset <- build_analysis_asset(source_sf, spec)
        analysis_path <- file.path(analysis_rds_dir, paste0(layer_id, ".rds"))
        saveRDS(analysis_asset$sf, analysis_path, compress = FALSE)

        if (!is.na(manifest_idx)) {
          manifest$analysis_rds_path[manifest_idx] <- to_repo_relative(analysis_path)
          manifest$analysis_base_buffer_m[manifest_idx] <- as.integer(analysis_asset$base_buffer_m)
        }

        tibble(layer_id = layer_id, status = "ok", message = "")
      }
    },
    error = function(e) {
      tibble(layer_id = layer_id, status = "error", message = conditionMessage(e))
    }
  )

  report_rows[[length(report_rows) + 1]] <- result
}

readr::write_csv(manifest, manifest_path)
report <- bind_rows(report_rows)
report_path <- file.path(asset_dir, "analysis_rds_export_report.csv")
readr::write_csv(report, report_path)

failed <- report |>
  filter(status == "error")

message("Wrote RDS manifest updates to: ", manifest_path)
message("Wrote RDS export report to: ", report_path)

if (nrow(failed) > 0) {
  stop("One or more analysis RDS exports failed: ", paste(failed$layer_id, collapse = ", "))
}
