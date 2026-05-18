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
hex_path <- file.path(
  regional_root,
  "outputs/trondelag/potential_app_landscape_r7_rollups_2026-05-18/app_bundle/hex.geojson"
)
road_path <- "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/N500_SL_RoadsClip_TRL_32.shp"
landmask_path <- "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/N500_AD_Merged_TRL_32.gpkg"

if (!file.exists(hex_path)) {
  stop("Active Trondelag R7 app-bundle hex file not found: ", hex_path)
}
if (!file.exists(road_path)) {
  stop("Trondelag N500 road source not found: ", road_path)
}
if (!file.exists(landmask_path)) {
  stop("Trondelag landmask source not found: ", landmask_path)
}

read_projected <- function(path, assumed_epsg = working_epsg) {
  x <- st_read(path, quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
  if (is.na(st_crs(x))) {
    st_crs(x) <- assumed_epsg
  }
  st_transform(st_make_valid(x), working_epsg)
}

to_repo_relative <- function(path) {
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  normalized_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalized_root, "/?"), "", normalized_path)
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

roads <- read_projected(road_path)
roads <- suppressWarnings(st_intersection(roads, landmask)) |>
  st_make_valid()
roads <- roads[!st_is_empty(roads), ]

layer_specs <- list(
  roads_medium = list(
    label = "Mellanvägar",
    group_id = "transport",
    values = c("F"),
    note = "Trondelag N500 roads where vegkategor is F. Mirrors Bornholm roads_medium."
  ),
  roads_large = list(
    label = "Stora vägar",
    group_id = "transport",
    values = c("E", "R"),
    note = "Trondelag N500 roads where vegkategor is E or R. Mirrors Bornholm roads_large."
  )
)

manifest_rows <- list()

for (layer_id in names(layer_specs)) {
  spec <- layer_specs[[layer_id]]
  message("Exporting ", layer_id, " ...")

  source_sf <- roads[trimws(as.character(roads$vegkategor)) %in% spec$values, ]
  source_sf <- source_sf[!st_is_empty(source_sf), ]
  if (nrow(source_sf) == 0) {
    stop("No road features found for layer: ", layer_id)
  }

  distance_df <- tibble(
    hex_id = hex_sf$hex_id,
    distance_m = round(nearest_distance_m(hex_centroids, source_sf), 1),
    intersects = lengths(st_intersects(hex_sf, source_sf)) > 0
  )
  distance_path <- file.path(distance_dir, paste0(layer_id, ".csv"))
  write_csv(distance_df, distance_path)

  analysis_geom <- st_union(st_geometry(source_sf)) |>
    st_make_valid()
  analysis_geom <- suppressWarnings(st_simplify(st_sfc(analysis_geom, crs = working_epsg), dTolerance = 20, preserveTopology = TRUE))
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
      tooltip_body = paste0(spec$note, "<br>Source: N500 road network clipped to Trondelag.")
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
    layer_key = "trl_roads_n500",
    label = spec$label,
    group_id = spec$group_id,
    source_path = road_path,
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

message("Wrote Trondelag road assets to: ", asset_dir)
