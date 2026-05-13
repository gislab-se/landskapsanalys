suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(sf)
  library(terra)
})

args <- commandArgs(trailingOnly = TRUE)
repo_root <- if (length(args) >= 1) normalizePath(args[[1]], winslash = "/", mustWork = TRUE) else normalizePath(getwd(), winslash = "/", mustWork = TRUE)

asset_dir <- file.path(repo_root, "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets")
config_path <- file.path(repo_root, "Trondelag/projects/trondelag/config/potential_app_acceptance_layers.csv")
h3_path <- file.path(repo_root, "data/processed/trondelag/h3/trondelag_h3_r8_land_clipped.geojson")
manifest_path <- file.path(asset_dir, "asset_manifest.csv")

dir.create(file.path(asset_dir, "source_geojson"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(asset_dir, "analysis_rds"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(asset_dir, "distance_tables"), recursive = TRUE, showWarnings = FALSE)

layer_config <- readr::read_csv(config_path, show_col_types = FALSE)
population_source <- layer_config$source_path[layer_config$layer_key == "trl_population_250m_centroids"][1]
if (is.na(population_source) || !nzchar(population_source) || !file.exists(population_source)) {
  stop("Population centroid source is missing: ", population_source)
}

message("Reading population centroids: ", population_source)
points <- sf::st_read(population_source, quiet = TRUE) |>
  sf::st_zm(drop = TRUE, what = "ZM") |>
  sf::st_transform(25832)
points <- points[!sf::st_is_empty(points), ]

make_square_sfc <- function(point_sfc, half_size_m = 125) {
  coords <- sf::st_coordinates(point_sfc)
  polys <- vector("list", nrow(coords))
  for (i in seq_len(nrow(coords))) {
    x <- coords[i, "X"]
    y <- coords[i, "Y"]
    polys[[i]] <- sf::st_polygon(list(matrix(
      c(
        x - half_size_m, y - half_size_m,
        x + half_size_m, y - half_size_m,
        x + half_size_m, y + half_size_m,
        x - half_size_m, y + half_size_m,
        x - half_size_m, y - half_size_m
      ),
      ncol = 2,
      byrow = TRUE
    )))
  }
  sf::st_sfc(polys, crs = sf::st_crs(point_sfc))
}

message("Rasterizing centroids to a 250 m grid and polygonizing occupied cells...")
coords <- sf::st_coordinates(points)
template <- terra::rast(
  xmin = min(coords[, "X"]) - 125,
  xmax = max(coords[, "X"]) + 125,
  ymin = min(coords[, "Y"]) - 125,
  ymax = max(coords[, "Y"]) + 125,
  resolution = 250,
  crs = "EPSG:25832"
)
point_vect <- terra::vect(points)
occupied <- terra::rasterize(point_vect, template, field = 1, background = NA)
cell_polygons <- terra::as.polygons(occupied, dissolve = TRUE, na.rm = TRUE)
population_proxy_geom <- sf::st_geometry(sf::st_as_sf(cell_polygons))
population_proxy_geom <- suppressWarnings(sf::st_make_valid(population_proxy_geom))
population_proxy <- sf::st_sf(
  layer_id = "population_points",
  proxy_type = "250m_grid_cell_from_centroid",
  source_feature_count = nrow(points),
  cell_size_m = 250,
  note = "Proxy polygon: 250 m square around each population-grid centroid, dissolved.",
  geometry = population_proxy_geom
)

rds_path <- file.path(asset_dir, "analysis_rds/population_points.rds")
geojson_path <- file.path(asset_dir, "source_geojson/population_points.geojson")
saveRDS(population_proxy, rds_path)
sf::st_write(sf::st_transform(population_proxy, 4326), geojson_path, driver = "GeoJSON", delete_dsn = TRUE, quiet = TRUE)

message("Keeping existing centroid distance table for now; live app buffers use the dissolved cell proxy polygon.")

manifest <- readr::read_csv(manifest_path, show_col_types = FALSE)
idx <- which(manifest$layer_id == "population_points")
if (length(idx) != 1) {
  stop("Could not find population_points row in asset manifest.")
}
manifest$geometry_family[idx] <- "polygon_proxy_from_250m_centroids"
manifest$feature_count[idx] <- nrow(points)
manifest$geojson_path[idx] <- "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/source_geojson/population_points.geojson"
manifest$distance_path[idx] <- "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/distance_tables/population_points.csv"
manifest$analysis_rds_path[idx] <- "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/analysis_rds/population_points.rds"
manifest$analysis_base_buffer_m[idx] <- 0
manifest$status[idx] <- "ok"
manifest$message[idx] <- "Population proxy: 250 m occupied grid-cell polygon derived from centroids and dissolved. Existing distance table is centroid-based until the polygon-distance table is rebuilt."
readr::write_csv(manifest, manifest_path)

message("Done. Wrote:")
message("  ", rds_path)
message("  ", geojson_path)
message("  ", file.path(asset_dir, "distance_tables/population_points.csv"))
