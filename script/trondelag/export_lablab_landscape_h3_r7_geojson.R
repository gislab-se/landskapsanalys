#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(sf)
})

args <- commandArgs(trailingOnly = TRUE)

input_gpkg <- if (length(args) >= 1) {
  args[[1]]
} else {
  "C:/gislab/landskapsanalys/data/processed/trondelag/qgis_trondelag_landskapstyper_h3/trondelag_landskapstyper_h3_fylke_boundary.gpkg"
}

output_geojson <- if (length(args) >= 2) {
  args[[2]]
} else {
  "docs/geocontext/potential_framework/data/trondelag_lablab_landscape_h3_r7/trondelag_lablab_landskapsanalys_h3_r7.geojson"
}

layer_name <- if (length(args) >= 3) args[[3]] else "landskapstyper_h3_r7"

if (!file.exists(input_gpkg)) {
  stop("Input GPKG does not exist: ", input_gpkg, call. = FALSE)
}

dir.create(dirname(output_geojson), recursive = TRUE, showWarnings = FALSE)

landscape <- sf::st_read(input_gpkg, layer = layer_name, quiet = TRUE)

required <- c("hex_id", "landscape_type_id", "landscape_type_name_sv")
missing <- setdiff(required, names(landscape))
if (length(missing) > 0) {
  stop("Input layer is missing required columns: ", paste(missing, collapse = ", "), call. = FALSE)
}

landscape <- landscape[, intersect(c(required, "assignment_method"), names(landscape))]
landscape$v10_type_id <- landscape$landscape_type_id
landscape$v10_type_name <- landscape$landscape_type_name_sv
landscape$landscape_type <- landscape$landscape_type_name_sv
landscape$class_km <- suppressWarnings(as.integer(sub("^LT0?", "", landscape$landscape_type_id)))
landscape$class_k8 <- landscape$class_km
landscape$source_model <- "LABLAB:s Landskapsanalys"

landscape <- sf::st_make_valid(landscape)
landscape <- sf::st_transform(landscape, 4326)

sf::st_write(
  landscape,
  output_geojson,
  driver = "GeoJSON",
  delete_dsn = TRUE,
  quiet = TRUE
)

message("Wrote ", nrow(landscape), " features to ", normalizePath(output_geojson, winslash = "/", mustWork = FALSE))
