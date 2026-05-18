suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(sf)
  library(tibble)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = getwd())
regional_root <- Sys.getenv("REGIONAL_LANDSCAPE_PIPELINE_ROOT", unset = "C:/gislab/regional-landscape-pipeline")

asset_dir <- file.path(repo_root, "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets")
geojson_dir <- file.path(asset_dir, "source_geojson")
distance_dir <- file.path(asset_dir, "distance_tables")
analysis_rds_dir <- file.path(asset_dir, "analysis_rds")
dir.create(geojson_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(distance_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(analysis_rds_dir, recursive = TRUE, showWarnings = FALSE)

working_epsg <- 25832L
hex_candidates <- c(
  file.path(repo_root, "docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson"),
  file.path(
    regional_root,
    "outputs/trondelag/potential_app_landscape_r7_rollups_original_labels_offshore_trim_2026-05-18/app_bundle/hex.geojson"
  ),
  file.path(
    regional_root,
    "outputs/trondelag/potential_app_landscape_r7_rollups_2026-05-18/app_bundle/hex.geojson"
  )
)
hex_path <- hex_candidates[file.exists(hex_candidates)][1]

landmask_path <- "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/N500_AD_Merged_TRL_32.gpkg"

layer_specs <- list(
  high_voltage_lines = list(
    layer_key = "trl_transmission_network",
    label = "Kraftnät - transmission",
    source_path = "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/NVE1_Kraftnett_Transmission_TRL_32.shp",
    source_kind = "LINESTRING",
    simplify_m = 20,
    clip_to_landmask = TRUE,
    note = "NVE transmission network from the cleaner UTM32 source NVE1_Kraftnett_Transmission_TRL_32. The older truncated transmission source in the UTM32 folder declares UTM33 and is intentionally not used."
  ),
  underground_cables = list(
    layer_key = "trl_underwater_cable",
    label = "Sjö-/undervattenskabel",
    source_path = "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/NVE-PKG1_Kraftnett_Sjokabel-Underwater-Cable_TRL_32.shp",
    source_kind = "LINESTRING",
    simplify_m = 20,
    clip_to_landmask = FALSE,
    note = "NVE underwater cable source. Kept as an optional grid-connection source; app runtime clips its feasibility buffer back to the Trondelag landmass."
  ),
  existing_wind_turbines = list(
    layer_key = "trl_wind_turbines",
    label = "Befintliga vindturbiner",
    source_path = "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/NVE_WindTurbine_Point_TRL_32.shp",
    source_kind = "POINT",
    simplify_m = 0,
    clip_to_landmask = TRUE,
    note = "NVE wind turbine points. Mirrors Bornholm's optional existing-wind-turbine electrical source."
  )
)

if (is.na(hex_path) || !nzchar(hex_path) || !file.exists(hex_path)) {
  stop("Active Trondelag R7 app-bundle hex file not found.")
}
if (!file.exists(landmask_path)) {
  stop("Trondelag landmask source not found: ", landmask_path)
}
for (layer_id in names(layer_specs)) {
  if (!file.exists(layer_specs[[layer_id]]$source_path)) {
    stop("Trondelag electrical source not found for ", layer_id, ": ", layer_specs[[layer_id]]$source_path)
  }
}

to_repo_relative <- function(path) {
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  normalized_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalized_root, "/?"), "", normalized_path)
}

read_projected <- function(path, assumed_epsg = working_epsg) {
  x <- st_read(path, quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
  if (is.na(st_crs(x))) {
    st_crs(x) <- assumed_epsg
  }
  st_transform(st_make_valid(x), working_epsg)
}

nearest_distance_m <- function(from_features, to_features) {
  if (nrow(to_features) == 0) {
    return(rep(Inf, nrow(from_features)))
  }
  idx <- st_nearest_feature(from_features, to_features)
  as.numeric(st_distance(from_features, to_features[idx, ], by_element = TRUE))
}

geometry_family <- function(x) {
  kinds <- unique(as.character(st_geometry_type(x, by_geometry = TRUE)))
  if (all(grepl("POINT", kinds))) {
    return("point")
  }
  if (all(grepl("LINE", kinds))) {
    return("line")
  }
  "polygon"
}

clip_to_landmask <- function(source_sf, landmask_geom) {
  clipped <- suppressWarnings(st_intersection(source_sf, landmask_geom)) |>
    st_make_valid()
  clipped[!st_is_empty(clipped), ]
}

keep_geometry_kind <- function(source_sf, source_kind) {
  if (nrow(source_sf) == 0) {
    return(source_sf)
  }
  extracted <- suppressWarnings(st_collection_extract(source_sf, source_kind))
  extracted[!st_is_empty(extracted), ]
}

hex_sf <- st_read(hex_path, quiet = TRUE) |>
  suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
if (is.na(st_crs(hex_sf))) {
  st_crs(hex_sf) <- 4326
}
hex_sf <- st_transform(st_make_valid(hex_sf), working_epsg) |>
  select(hex_id)
hex_centroids <- st_point_on_surface(hex_sf)

landmask <- read_projected(landmask_path) |>
  st_union() |>
  st_make_valid()

manifest_rows <- list()

for (layer_id in names(layer_specs)) {
  spec <- layer_specs[[layer_id]]
  message("Exporting ", layer_id, " ...")

  source_sf <- read_projected(spec$source_path)
  source_sf <- keep_geometry_kind(source_sf, spec$source_kind)
  if (isTRUE(spec$clip_to_landmask)) {
    source_sf <- clip_to_landmask(source_sf, landmask)
    source_sf <- keep_geometry_kind(source_sf, spec$source_kind)
  }
  source_sf <- source_sf[!st_is_empty(source_sf), ]
  if (nrow(source_sf) == 0) {
    stop("Electrical layer contains no usable features after preprocessing: ", layer_id)
  }

  tolerance <- as.numeric(spec$simplify_m)
  distance_source <- source_sf |>
    select() |>
    st_make_valid()
  if (tolerance > 0) {
    distance_source <- suppressWarnings(st_simplify(distance_source, dTolerance = tolerance, preserveTopology = TRUE))
  }
  distance_source <- distance_source[!st_is_empty(distance_source), ]

  distance_df <- tibble(
    hex_id = hex_sf$hex_id,
    distance_m = round(nearest_distance_m(hex_centroids, distance_source), 1),
    intersects = lengths(st_intersects(hex_sf, distance_source)) > 0
  )
  distance_path <- file.path(distance_dir, paste0(layer_id, ".csv"))
  write_csv(distance_df, distance_path)

  analysis_geom <- st_union(st_geometry(source_sf)) |>
    st_make_valid()
  analysis_geom <- st_sfc(analysis_geom, crs = working_epsg)
  if (tolerance > 0) {
    analysis_geom <- suppressWarnings(st_simplify(analysis_geom, dTolerance = tolerance, preserveTopology = TRUE))
  }
  analysis_sf <- st_sf(
    tibble(
      layer_id = layer_id,
      label = spec$label,
      analysis_base_buffer_m = 0L
    ),
    geometry = analysis_geom
  )
  analysis_path <- file.path(analysis_rds_dir, paste0(layer_id, ".rds"))
  saveRDS(analysis_sf, analysis_path, compress = FALSE)

  display_sf <- st_sf(
    tibble(
      layer_id = layer_id,
      label = spec$label,
      tooltip_title = paste0("Source layer: ", spec$label),
      tooltip_body = paste0(spec$note, "<br>Source transformed to EPSG:25832 for distance and buffer logic.")
    ),
    geometry = st_geometry(analysis_sf),
    crs = working_epsg
  ) |>
    st_transform(4326)

  geojson_path <- file.path(geojson_dir, paste0(layer_id, ".geojson"))
  if (file.exists(geojson_path)) {
    unlink(geojson_path)
  }
  st_write(display_sf, geojson_path, driver = "GeoJSON", quiet = TRUE, delete_dsn = TRUE)

  manifest_rows[[length(manifest_rows) + 1]] <- tibble(
    layer_id = layer_id,
    layer_key = spec$layer_key,
    label = spec$label,
    group_id = "electrical",
    source_path = spec$source_path,
    source_exists = TRUE,
    geometry_family = geometry_family(source_sf),
    feature_count = nrow(source_sf),
    geojson_path = to_repo_relative(geojson_path),
    distance_path = to_repo_relative(distance_path),
    analysis_rds_path = to_repo_relative(analysis_path),
    analysis_base_buffer_m = 0L,
    status = "ok",
    message = spec$note
  )
}

manifest_path <- file.path(asset_dir, "asset_manifest.csv")
existing_manifest <- if (file.exists(manifest_path)) read_csv(manifest_path, show_col_types = FALSE) else tibble()
new_rows <- bind_rows(manifest_rows)
if (nrow(existing_manifest) > 0) {
  existing_manifest <- existing_manifest |>
    filter(!layer_id %in% new_rows$layer_id)
}
bind_rows(existing_manifest, new_rows) |>
  write_csv(manifest_path)

message("Wrote Trondelag electrical assets to: ", asset_dir)
