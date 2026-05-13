suppressPackageStartupMessages({
  library(sf)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("Usage: Rscript render_trondelag_population_buffer.R <repo_root> <buffer_m> <output_geojson>")
}

repo_root <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
buffer_m <- as.numeric(args[[2]])
output_geojson <- args[[3]]
if (is.na(buffer_m) || buffer_m < 0) {
  stop("buffer_m must be a non-negative number.")
}

rds_path <- file.path(
  repo_root,
  "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/analysis_rds/population_points.rds"
)
if (!file.exists(rds_path)) {
  stop("Missing Trondelag population proxy RDS: ", rds_path)
}

dir.create(dirname(output_geojson), recursive = TRUE, showWarnings = FALSE)

population_proxy <- readRDS(rds_path)
population_proxy <- sf::st_transform(population_proxy, 25832)
population_proxy <- population_proxy[!sf::st_is_empty(population_proxy), ]
if (nrow(population_proxy) < 1) {
  stop("Trondelag population proxy contains no features.")
}

geom <- sf::st_geometry(population_proxy)
if (length(geom) > 1) {
  geom <- suppressWarnings(sf::st_union(geom))
}
if (buffer_m > 0) {
  geom <- sf::st_buffer(geom, dist = buffer_m, nQuadSegs = 8)
}
geom <- suppressWarnings(sf::st_make_valid(geom))
if (any(as.character(sf::st_geometry_type(geom)) == "GEOMETRYCOLLECTION")) {
  geom <- sf::st_collection_extract(geom, "POLYGON", warn = FALSE)
}
geom <- suppressWarnings(sf::st_simplify(geom, dTolerance = 10, preserveTopology = TRUE))

buffered <- sf::st_sf(
  layer_id = "population_points_buffer",
  proxy_type = "dissolved_250m_grid_cell_from_centroid_buffer",
  buffer_m = buffer_m,
  note = paste0(
    "Dissolved polygon buffer around 250 m population-grid cell proxy derived from centroids. ",
    "This is not individual population point data."
  ),
  geometry = geom
)
buffered <- sf::st_transform(buffered, 4326)
sf::st_write(buffered, output_geojson, driver = "GeoJSON", delete_dsn = TRUE, quiet = TRUE)
