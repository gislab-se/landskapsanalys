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
layer_id <- "forest_land_cover"
layer_key <- "trl_landcover_n500"
layer_label <- "Skog (N500 markdekke)"
source_path <- "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/UT_Trondelag_SL01/UTM 32/N500_AD_Merged_TRL_32.gpkg"
source_layer <- "N500_AD_Merged_TRL_32"
forest_objtype <- "Skog"

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

if (is.na(hex_path) || !nzchar(hex_path) || !file.exists(hex_path)) {
  stop("Active Trondelag R7 app-bundle hex file not found.")
}
if (!file.exists(source_path)) {
  stop("Trondelag N500 landcover source not found: ", source_path)
}

to_repo_relative <- function(path) {
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = TRUE)
  normalized_path <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalized_root, "/?"), "", normalized_path)
}

read_projected <- function(path, layer = NULL, assumed_epsg = working_epsg) {
  x <- st_read(path, layer = layer, quiet = TRUE) |>
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

hex_sf <- st_read(hex_path, quiet = TRUE) |>
  suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
if (is.na(st_crs(hex_sf))) {
  st_crs(hex_sf) <- 4326
}
hex_sf <- st_transform(st_make_valid(hex_sf), working_epsg) |>
  select(hex_id)
hex_centroids <- st_point_on_surface(hex_sf)

landcover <- read_projected(source_path, layer = source_layer)
if (!"objtype" %in% names(landcover)) {
  stop("N500 landcover source is missing expected `objtype` field.")
}

landmask <- landcover |>
  filter(objtype != "Havflate") |>
  st_union() |>
  st_make_valid()

forest_source <- landcover |>
  filter(objtype == forest_objtype) |>
  st_make_valid()
forest_clipped <- suppressWarnings(st_intersection(forest_source, landmask)) |>
  st_make_valid()
forest_clipped <- forest_clipped[!st_is_empty(forest_clipped), ]

if (nrow(forest_clipped) == 0) {
  stop("N500 landcover contains no `", forest_objtype, "` features after clipping.")
}

distance_source <- forest_clipped |>
  select() |>
  st_simplify(dTolerance = 25, preserveTopology = TRUE) |>
  st_make_valid()
distance_source <- distance_source[!st_is_empty(distance_source), ]

forest_union <- st_union(st_geometry(forest_clipped)) |>
  st_make_valid()
forest_union <- suppressWarnings(
  st_simplify(st_sfc(forest_union, crs = working_epsg), dTolerance = 25, preserveTopology = TRUE)
)

analysis_sf <- st_sf(
  tibble(
    layer_id = layer_id,
    label = layer_label,
    analysis_base_buffer_m = 0L
  ),
  geometry = forest_union
)
analysis_path <- file.path(analysis_rds_dir, paste0(layer_id, ".rds"))
saveRDS(analysis_sf, analysis_path, compress = FALSE)

display_sf <- st_sf(
  tibble(
    layer_id = layer_id,
    label = layer_label,
    tooltip_title = paste0("Source layer: ", layer_label),
    tooltip_body = paste0(
      "Norwegian N500 markdekke polygons filtered to objtype = ", forest_objtype,
      ". Used as a separate land-use forest controller for large-scale solar."
    )
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

distance_df <- tibble(
  hex_id = hex_sf$hex_id,
  distance_m = round(nearest_distance_m(hex_centroids, distance_source), 1),
  intersects = lengths(st_intersects(hex_sf, distance_source)) > 0
)
distance_path <- file.path(distance_dir, paste0(layer_id, ".csv"))
write_csv(distance_df, distance_path)

manifest_path <- file.path(asset_dir, "asset_manifest.csv")
existing_manifest <- if (file.exists(manifest_path)) {
  read_csv(manifest_path, show_col_types = FALSE)
} else {
  tibble()
}
new_row <- tibble(
  layer_id = layer_id,
  layer_key = layer_key,
  label = layer_label,
  group_id = "land_use",
  source_path = paste0(source_path, "|layer=", source_layer, "|objtype=", forest_objtype),
  source_exists = TRUE,
  geometry_family = "polygon",
  feature_count = nrow(forest_clipped),
  geojson_path = to_repo_relative(geojson_path),
  distance_path = to_repo_relative(distance_path),
  analysis_rds_path = to_repo_relative(analysis_path),
  analysis_base_buffer_m = 0L,
  status = "ok",
  message = "Trondelag N500 markdekke filtered to objtype = Skog; separate land-use forest controller for large-scale solar."
)

if (nrow(existing_manifest) > 0) {
  existing_manifest <- existing_manifest |>
    filter(layer_id != !!layer_id)
}
bind_rows(existing_manifest, new_row) |>
  write_csv(manifest_path)

message("Wrote Trondelag forest land-use asset: ", geojson_path)
message("Feature count before dissolve: ", nrow(forest_clipped))
