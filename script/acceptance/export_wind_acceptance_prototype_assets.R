suppressPackageStartupMessages({
  library(dplyr)
  library(jsonlite)
  library(readr)
  library(sf)
  library(tibble)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
registry_path <- file.path(repo_root, "apps", "acceptance_model", "registry.json")

if (!file.exists(registry_path)) {
  stop("Registry not found: ", registry_path)
}

source(file.path(repo_root, "script", "semi_manual_r9", "lib", "subcategory_splits.R"))

registry <- jsonlite::fromJSON(registry_path, simplifyVector = TRUE)
layer_config <- read.csv(file.path(repo_root, registry$source_config_csv), stringsAsFactors = FALSE)

asset_dir <- file.path(repo_root, registry$asset_dir)
geojson_dir <- file.path(asset_dir, "source_geojson")
distance_dir <- file.path(asset_dir, "distance_tables")
analysis_rds_dir <- file.path(asset_dir, "analysis_rds")
landmask_dir <- file.path(asset_dir, "landmask")
dir.create(geojson_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(distance_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(analysis_rds_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(landmask_dir, recursive = TRUE, showWarnings = FALSE)

hex_sf <- st_read(file.path(repo_root, registry$hex_gpkg), quiet = TRUE) |>
  st_transform(32633) |>
  select(hex_id)
hex_centroids <- st_point_on_surface(hex_sf)

layer_path <- function(layer_key) {
  path <- layer_config$source_path[layer_config$layer_key == layer_key][1]
  if (is.na(path) || !nzchar(path)) {
    return(NA_character_)
  }
  path
}

load_landmask <- function() {
  landmask_key <- registry$landmask_layer_key[[1]]
  landmask_path <- layer_path(landmask_key)
  if (is.na(landmask_path) || !file.exists(landmask_path)) {
    stop("Landmask source not found for layer_key: ", landmask_key)
  }
  landmask_sf <- st_read(landmask_path, quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM")) |>
    st_make_valid() |>
    st_transform(32633)

  st_sf(mask_id = "bornholm_landmass", geometry = st_sfc(st_union(landmask_sf), crs = 32633)) |>
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
  geom_sfc <- if (inherits(geom, "sfc")) geom else st_sfc(geom, crs = 32633)
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

geometry_family <- function(x) {
  kinds <- unique(as.character(st_geometry_type(x, by_geometry = TRUE)))
  if (length(kinds) == 0) {
    return("unknown")
  }
  if (all(grepl("POINT", kinds))) {
    return("point")
  }
  if (all(grepl("LINE", kinds))) {
    return("line")
  }
  "polygon"
}

nearest_distance_m <- function(from_features, to_features) {
  if (nrow(to_features) == 0) {
    return(rep(Inf, nrow(from_features)))
  }
  idx <- st_nearest_feature(from_features, to_features)
  as.numeric(st_distance(from_features, to_features[idx, ], by_element = TRUE))
}

to_repo_relative <- function(path) {
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  normalized_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalized_root, "/?"), "", normalized_path)
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
  analysis_geom <- suppressWarnings(st_simplify(st_sfc(analysis_geom, crs = 32633), dTolerance = 20, preserveTopology = TRUE))
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

manifest_rows <- list()

for (i in seq_len(nrow(registry$layers))) {
  spec <- registry$layers[i, ]
  source_path <- layer_path(spec$layer_key[[1]])
  message("Exporting ", spec$label[[1]], " ...")

  base_row <- tibble(
    layer_id = spec$id[[1]],
    layer_key = spec$layer_key[[1]],
    label = spec$label[[1]],
    group_id = spec$group_id[[1]],
    source_path = source_path,
    source_exists = !is.na(source_path) && file.exists(source_path),
    geometry_family = NA_character_,
    feature_count = 0L,
    geojson_path = NA_character_,
    distance_path = NA_character_,
    analysis_rds_path = NA_character_,
    analysis_base_buffer_m = 0L,
    status = "missing_source",
    message = "Source path missing or unreadable."
  )

  if (is.na(source_path) || !file.exists(source_path)) {
    manifest_rows[[length(manifest_rows) + 1]] <- base_row
    next
  }

  exported <- tryCatch(
    {
      source_sf <- st_read(source_path, quiet = TRUE) |>
        suppressWarnings(st_zm(drop = TRUE, what = "ZM")) |>
        st_make_valid() |>
        st_transform(32633)

      source_sf <- apply_registry_filter(source_sf, spec)
      source_sf <- clip_to_landmass(source_sf)
      source_sf <- source_sf[!st_is_empty(source_sf), ]

      if (nrow(source_sf) == 0) {
        filter_message <- "Source layer contains no features after landmass clipping."
        if ("filter_value" %in% names(spec) && !is.na(spec$filter_value[[1]]) && nzchar(spec$filter_value[[1]])) {
          filter_message <- paste0(
            "No features found after applying filter ",
            spec$filter_field[[1]],
            " -> ",
            spec$filter_value[[1]],
            ", then clipping to Bornholm landmass."
          )
        }

        base_row |>
          mutate(
            source_exists = TRUE,
            geometry_family = "empty",
            feature_count = 0L,
            status = "empty_after_filter",
            message = filter_message
          )
      } else {
        family <- geometry_family(source_sf)

        distance_df <- tibble(
          hex_id = hex_sf$hex_id,
          distance_m = round(nearest_distance_m(hex_centroids, source_sf), 1),
          intersects = lengths(st_intersects(hex_sf, source_sf)) > 0
        )
        distance_path <- file.path(distance_dir, paste0(spec$id[[1]], ".csv"))
        readr::write_csv(distance_df, distance_path)

        analysis_asset <- build_analysis_asset(source_sf, spec)
        analysis_sf <- analysis_asset$sf
        analysis_path <- file.path(analysis_rds_dir, paste0(spec$id[[1]], ".rds"))
        saveRDS(analysis_sf, analysis_path, compress = FALSE)

        if (spec$id[[1]] == "population_points") {
          display_sf <- analysis_sf |>
            mutate(
              tooltip_title = paste0("Source layer: ", spec$label[[1]]),
              tooltip_body = paste0(spec$note[[1]], "<br>Display mode: dissolved 100 m buffer around points, clipped to Bornholm landmass.")
            )
        } else {
          display_sf <- source_sf
          if (family != "point") {
            display_sf <- st_simplify(display_sf, dTolerance = 20, preserveTopology = TRUE)
          }
          display_sf <- st_sf(
            tibble(
              layer_id = rep(spec$id[[1]], nrow(display_sf)),
              label = rep(spec$label[[1]], nrow(display_sf)),
              tooltip_title = rep(paste0("Source layer: ", spec$label[[1]]), nrow(display_sf)),
              tooltip_body = rep(paste0(spec$note[[1]], "<br>Clipped to Bornholm landmass."), nrow(display_sf))
            ),
            geometry = st_geometry(display_sf),
            crs = st_crs(display_sf)
          )
        }

        display_sf <- st_transform(display_sf, 4326)
        geojson_path <- file.path(geojson_dir, paste0(spec$id[[1]], ".geojson"))
        if (file.exists(geojson_path)) {
          unlink(geojson_path)
        }
        st_write(display_sf, geojson_path, driver = "GeoJSON", quiet = TRUE, delete_dsn = TRUE)

        tibble(
          layer_id = spec$id[[1]],
          layer_key = spec$layer_key[[1]],
          label = spec$label[[1]],
          group_id = spec$group_id[[1]],
          source_path = source_path,
          source_exists = TRUE,
          geometry_family = family,
          feature_count = nrow(source_sf),
          geojson_path = to_repo_relative(geojson_path),
          distance_path = to_repo_relative(distance_path),
          analysis_rds_path = to_repo_relative(analysis_path),
          analysis_base_buffer_m = as.integer(analysis_asset$base_buffer_m),
          status = "ok",
          message = ""
        )
      }
    },
    error = function(e) {
      base_row |>
        mutate(status = "read_error", message = conditionMessage(e))
    }
  )

  manifest_rows[[length(manifest_rows) + 1]] <- exported
}

manifest_df <- bind_rows(manifest_rows)
manifest_path <- file.path(asset_dir, "asset_manifest.csv")
readr::write_csv(manifest_df, manifest_path)

message("Wrote prototype asset manifest to: ", manifest_path)
