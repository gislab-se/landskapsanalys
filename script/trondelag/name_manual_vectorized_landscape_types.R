#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(terra)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
input_gpkg <- "C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg"
class_raster <- file.path(
  repo_root,
  "data/processed/trondelag/pdf_polygon_bright_full_safe/trondelag_pdf_bright_full_clean_class.tif"
)
out_dir <- file.path(repo_root, "data/processed/trondelag/manual_vectorized")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_gpkg <- file.path(out_dir, "landskapsanalys_trondelag_named.gpkg")

type_lookup <- tibble::tibble(
  class_value = 1:9,
  landscape_type_id = sprintf("LT%02d", 1:9),
  landscape_type_name_sv = c(
    "Kustslättslandskap",
    "Fjordlandskap",
    "Fjordnära jordbrukslandskap",
    "Fjällnära skogslandskap",
    "Dalgångslandskap",
    "Lågfjällslandskap",
    "Högfjällslandskap",
    "Sjö- och våtmarkslandskap",
    "Vidsträckt fjällandskap"
  )
)

modal_fun <- function(z, ...) {
  z <- z[!is.na(z)]
  if (!length(z)) return(NA_real_)
  as.numeric(names(sort(table(z), decreasing = TRUE)[1]))
}

message("Reading merged vector layer...")
merged <- st_read(input_gpkg, layer = "merged", quiet = TRUE) |>
  st_make_valid()

message("Assigning landscape types from clean class raster...")
r <- terra::rast(class_raster)
merged_raster_crs <- st_transform(merged, st_crs(r)$wkt)
modal_class <- terra::extract(r, terra::vect(merged_raster_crs), fun = modal_fun, na.rm = TRUE)

named <- merged |>
  mutate(
    source_row_id = row_number(),
    modal_class_value = as.integer(modal_class$class_value)
  ) |>
  left_join(type_lookup, by = c("modal_class_value" = "class_value")) |>
  mutate(
    landscape_type_id = ifelse(is.na(landscape_type_id), "LT??", landscape_type_id),
    landscape_type_name_sv = ifelse(is.na(landscape_type_name_sv), "Okänd", landscape_type_name_sv),
    assignment_method = "modal overlap with bright clean class raster",
    review_needed = is.na(modal_class_value)
  ) |>
  st_transform(25832)
named$area_m2_calc <- as.numeric(st_area(named))

message("Dissolving by landscape type...")
dissolved <- named |>
  group_by(landscape_type_id, landscape_type_name_sv) |>
  summarise(
    n_source_polygons = n(),
    area_m2_calc = sum(area_m2_calc),
    assignment_method = "dissolved from merged_named",
    .groups = "drop"
  ) |>
  st_make_valid() |>
  st_transform(25832)

summary <- named |>
  st_drop_geometry() |>
  count(landscape_type_id, landscape_type_name_sv, name = "n_polygons") |>
  left_join(
    named |>
      st_drop_geometry() |>
      group_by(landscape_type_id, landscape_type_name_sv) |>
      summarise(area_km2 = sum(area_m2_calc) / 1e6, .groups = "drop"),
    by = c("landscape_type_id", "landscape_type_name_sv")
  ) |>
  arrange(landscape_type_id)

if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(named, out_gpkg, layer = "merged_named", quiet = TRUE)
st_write(dissolved, out_gpkg, layer = "merged_named_dissolved", append = TRUE, quiet = TRUE)
write.csv(summary, file.path(out_dir, "landskapsanalys_trondelag_named_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

readme <- c(
  "# Trondelag manually vectorized landscape types - named copy",
  "",
  paste0("- Source GeoPackage: `", input_gpkg, "`"),
  paste0("- Output GeoPackage: `", out_gpkg, "`"),
  paste0("- Class raster used for names: `", class_raster, "`"),
  "",
  "## Layers",
  "",
  "- `merged_named`: original merged polygons with added landscape type fields.",
  "- `merged_named_dissolved`: polygons dissolved by landscape type.",
  "",
  "## Added fields",
  "",
  "- `landscape_type_id`: LT01-LT09.",
  "- `landscape_type_name_sv`: Swedish landscape type name.",
  "- `modal_class_value`: majority class from the clean class raster under the polygon.",
  "- `assignment_method`: how the type was assigned.",
  "- `review_needed`: TRUE if no class could be assigned.",
  "",
  "## Summary",
  "",
  paste(capture.output(print(as.data.frame(summary), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(readme), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", out_gpkg)
message("Wrote: ", file.path(out_dir, "README.md"))
