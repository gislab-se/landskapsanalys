#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(terra)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
manual_gpkg <- "C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg"
class_raster <- file.path(
  repo_root,
  "data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_clean_class.tif"
)
out_dir <- file.path(repo_root, "data/processed/trondelag/manual_vectorized_v2")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_gpkg <- file.path(out_dir, "trondelag_lt07_candidate_from_clean_class.gpkg")

message("Reading manual merged polygons...")
manual <- st_read(manual_gpkg, layer = "merged", quiet = TRUE) |>
  st_make_valid() |>
  st_transform(25832)

manual_union <- st_union(st_geometry(manual))
target_area <- st_buffer(manual_union, 2500)

message("Cropping clean class raster to the reviewed manual footprint...")
r <- rast(class_raster)
target_area_r <- st_transform(st_as_sf(target_area), st_crs(r)$wkt)
r_crop <- crop(r, vect(target_area_r))
r_lt07 <- ifel(r_crop == 7, 1, NA)

message("Polygonizing LT07 class candidate...")
lt07_poly <- as.polygons(r_lt07, dissolve = TRUE, na.rm = TRUE) |>
  st_as_sf() |>
  st_transform(25832) |>
  st_make_valid()

candidate <- lt07_poly |>
  st_intersection(st_as_sf(target_area)) |>
  st_make_valid() |>
  st_difference(manual_union) |>
  st_make_valid() |>
  st_collection_extract("POLYGON")

candidate$area_m2_calc <- as.numeric(st_area(candidate))
candidate <- candidate |>
  filter(area_m2_calc > 50000) |>
  mutate(
    landscape_type_id = "LT07",
    landscape_type_name_sv = "H\u00f6gfj\u00e4llslandskap",
    assignment_method = "candidate from clean class raster class 7, clipped to manual footprint buffer",
    review_needed = TRUE
  )

if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(candidate, out_gpkg, layer = "lt07_candidate", quiet = TRUE)

summary <- candidate |>
  st_drop_geometry() |>
  summarise(
    n_polygons = n(),
    area_km2 = sum(area_m2_calc) / 1e6
  )
write.csv(summary, file.path(out_dir, "lt07_candidate_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

message("Wrote: ", out_gpkg)
message("Features: ", nrow(candidate))
message("Area km2: ", round(sum(candidate$area_m2_calc) / 1e6, 2))
