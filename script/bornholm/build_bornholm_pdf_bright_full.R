#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(terra)
  library(tibble)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)

pdf_gis <- Sys.getenv(
  "BORNHOLM_LABLAB_GIS_PDF",
  "C:/gislab/landskapsanalys/data/raw/lablab/SpeedLocal/Bornholm/PDF GIS/Landskapstyper Bornholm.pdf"
)
source_report_pdf <- Sys.getenv(
  "BORNHOLM_LABLAB_REPORT_PDF",
  "C:/gislab/landskapsanalys/data/Landskapstyper Bornholm.pdf"
)

out_dir <- file.path(repo_root, "data/processed/bornholm/lablab_pdf_landscape/pdf_bright_full_safe")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

if (!file.exists(pdf_gis)) {
  stop("GIS PDF not found: ", pdf_gis, call. = FALSE)
}

landscape_types <- tibble(
  class_value = 1:5,
  type_id = sprintf("LT%02d", 1:5),
  type_name = c(
    "Klippigt kustlandskap",
    "Sandigt kustlandskap",
    "Jordbruksdominerat sprickdalslandskap",
    "Skogskl\u00e4tt sprickdalslandskap",
    "Sl\u00e4tt- och jordbrukslandskap"
  ),
  source_legend_hex = c(
    "#8DB5BD",
    "#C0BE8E",
    "#A58B75",
    "#94AF9C",
    "#E2E5BD"
  ),
  bright_hex = c(
    "#1E5AF0",
    "#18DCEB",
    "#F07818",
    "#19D64A",
    "#F2DC10"
  )
)

# The Bornholm GIS PDF uses semi-transparent landscape fills over imagery.
# These samples include the legend colour and common in-map mixed colours.
source_samples <- tribble(
  ~type_id, ~source_hex, ~sample_note,
  "LT01", "#8DB5BD", "legend / light coastal blue",
  "LT01", "#416B74", "coastal blue mixed with dark orthophoto",
  "LT01", "#426C77", "coastal blue mixed with dark orthophoto",
  "LT02", "#C0BE8E", "legend / sand coast",
  "LT02", "#BDBB8B", "sand coast mixed with orthophoto",
  "LT02", "#A5A5A5", "grey sand/coastal mixed tone",
  "LT03", "#A58B75", "legend / agricultural fracture valley",
  "LT03", "#A28872", "agricultural fracture valley mixed tone",
  "LT03", "#83735F", "darker agricultural mixed tone",
  "LT04", "#94AF9C", "legend / forested fracture valley",
  "LT04", "#507258", "forested fracture valley mixed tone",
  "LT04", "#53755B", "forested fracture valley mixed tone",
  "LT05", "#E2E5BD", "legend / open plain agriculture",
  "LT05", "#C3C191", "open plain agriculture mixed tone",
  "LT05", "#A0A87A", "darker open plain mixed tone"
) |>
  left_join(landscape_types |> select(type_id, class_value, type_name), by = "type_id")

modal_fun <- function(values, ...) {
  values <- values[!is.na(values)]
  if (!length(values)) return(NA_real_)
  as.numeric(names(sort(table(values), decreasing = TRUE)[1]))
}

mask_to_land <- function(r, raster_crs) {
  use_landmask <- !identical(Sys.getenv("USE_LANDMASK"), "0")
  landmask_path <- Sys.getenv(
    "BORNHOLM_LANDMASK",
    file.path(repo_root, "docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_landmask_wgs84.geojson")
  )
  if (!use_landmask || !file.exists(landmask_path)) {
    return(list(raster = r, note = "No landmask applied."))
  }

  buffer_m <- as.numeric(Sys.getenv("LANDMASK_BUFFER_M", "250"))
  message("Applying Bornholm landmask: ", landmask_path)
  landmask <- st_read(landmask_path, quiet = TRUE) |>
    st_make_valid() |>
    st_transform(st_crs(raster_crs))
  landmask <- st_union(landmask)
  if (is.finite(buffer_m) && buffer_m > 0) {
    landmask <- st_buffer(landmask, buffer_m)
  }

  mask_raster <- terra::rasterize(terra::vect(landmask), r, field = 1, background = NA)
  list(
    raster = terra::mask(r, mask_raster),
    note = paste0("Applied landmask with ", buffer_m, " m buffer: ", landmask_path)
  )
}

message("Reading geospatial PDF raster...")
r_pdf <- terra::rast(pdf_gis)
names(r_pdf) <- c("red", "green", "blue")
pdf_crs <- terra::crs(r_pdf)

message("PDF raster CRS: ", terra::crs(r_pdf, describe = TRUE)$name)
message("PDF raster size: ", ncol(r_pdf), " x ", nrow(r_pdf), " pixels")

rgb_values <- terra::values(r_pdf, mat = TRUE)
rgb_values <- rgb_values[, 1:3, drop = FALSE] / 255
valid_rgb <- complete.cases(rgb_values)

sample_rgb <- t(grDevices::col2rgb(source_samples$source_hex) / 255)
best_dist <- rep(Inf, nrow(rgb_values))
best_class <- rep(NA_integer_, nrow(rgb_values))

message("Classifying PDF pixels against Bornholm source colour samples...")
for (idx in seq_len(nrow(sample_rgb))) {
  dist <- sqrt(rowSums((rgb_values - matrix(sample_rgb[idx, ], nrow(rgb_values), 3, byrow = TRUE))^2))
  hit <- valid_rgb & dist < best_dist
  best_dist[hit] <- dist[hit]
  best_class[hit] <- source_samples$class_value[idx]
}

max_distance <- as.numeric(Sys.getenv("MAX_RGB_DISTANCE", "0.18"))
min_brightness <- as.numeric(Sys.getenv("MIN_BRIGHTNESS", "0.12"))
max_brightness <- as.numeric(Sys.getenv("MAX_BRIGHTNESS", "0.98"))
brightness <- rowMeans(rgb_values, na.rm = TRUE)

class_values <- best_class
class_values[!valid_rgb | best_dist > max_distance] <- NA_integer_
class_values[brightness < min_brightness | brightness > max_brightness] <- NA_integer_

r_raw <- r_pdf[[1]]
terra::values(r_raw) <- class_values
names(r_raw) <- "class_value"

dist_raster <- r_pdf[[1]]
terra::values(dist_raster) <- best_dist
names(dist_raster) <- "rgb_distance"

raw_masked <- mask_to_land(r_raw, pdf_crs)
r_raw <- raw_masked$raster

do_modal_fill <- identical(Sys.getenv("DO_MODAL_FILL"), "1")
r_clean <- r_raw
if (do_modal_fill) {
  message("Filling uncertain pixels by local modal class...")
  for (idx in 1:3) {
    message("  modal fill pass ", idx, "/3")
    fill <- terra::focal(
      r_clean,
      w = matrix(1, 7, 7),
      fun = modal_fun,
      na.policy = "only",
      fillvalue = NA
    )
    r_clean <- terra::cover(r_clean, fill)
    r_clean <- mask_to_land(r_clean, pdf_crs)$raster
  }
} else {
  message("Skipping modal fill by default; set DO_MODAL_FILL=1 for a filled class raster.")
}
names(r_clean) <- "class_value"

unknown_raster <- is.na(r_clean)
names(unknown_raster) <- "unknown_flag"

message("Creating bright RGB class raster...")
clean_vals <- terra::values(r_clean, mat = FALSE)
bright_rgb_255 <- t(grDevices::col2rgb(landscape_types$bright_hex))
red <- green <- blue <- rep(NA_integer_, length(clean_vals))
for (idx in seq_len(nrow(landscape_types))) {
  hit <- clean_vals == landscape_types$class_value[idx]
  red[hit] <- bright_rgb_255[idx, "red"]
  green[hit] <- bright_rgb_255[idx, "green"]
  blue[hit] <- bright_rgb_255[idx, "blue"]
}

r_red <- r_clean
r_green <- r_clean
r_blue <- r_clean
terra::values(r_red) <- red
terra::values(r_green) <- green
terra::values(r_blue) <- blue
r_bright <- c(r_red, r_green, r_blue)
names(r_bright) <- c("red", "green", "blue")

raw_tif <- file.path(out_dir, "bornholm_pdf_bright_full_raw_class.tif")
clean_tif <- file.path(out_dir, "bornholm_pdf_bright_full_clean_class.tif")
bright_tif <- file.path(out_dir, "bornholm_pdf_bright_full_bright_rgb.tif")
unknown_tif <- file.path(out_dir, "bornholm_pdf_bright_full_unknown_flag.tif")
dist_tif <- file.path(out_dir, "bornholm_pdf_bright_full_rgb_distance.tif")

terra::writeRaster(r_raw, raw_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(r_clean, clean_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(r_bright, bright_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(unknown_raster, unknown_tif, overwrite = TRUE, datatype = "INT1U")
terra::writeRaster(dist_raster, dist_tif, overwrite = TRUE, datatype = "FLT4S")

out_gpkg <- file.path(out_dir, "bornholm_pdf_bright_full_polygons.gpkg")
write_polygons <- identical(Sys.getenv("WRITE_FULL_POLYGONS"), "1")
if (write_polygons) {
  message("Polygonising full cleaned class raster...")
  poly <- terra::as.polygons(r_clean, dissolve = TRUE, values = TRUE, na.rm = TRUE)
  poly_sf <- st_as_sf(poly) |>
    st_make_valid() |>
    rename(class_value = class_value) |>
    mutate(class_value = as.integer(class_value)) |>
    left_join(landscape_types, by = "class_value") |>
    mutate(
      source = "bornholm_pdf_fixed_palette_bright_full",
      confidence = "helper_class_raster_needs_qgis_review",
      area_m2_pdf_crs = as.numeric(st_area(geometry))
    ) |>
    st_transform(25833)
  if (file.exists(out_gpkg)) file.remove(out_gpkg)
  st_write(poly_sf, out_gpkg, layer = "landscape_type_polygons_bright_full", quiet = TRUE)
} else {
  out_gpkg <- NA_character_
}

palette_csv <- file.path(out_dir, "bornholm_pdf_bright_full_palette.csv")
source_samples_csv <- file.path(out_dir, "bornholm_pdf_bright_full_source_samples.csv")
write.csv(landscape_types, palette_csv, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(source_samples, source_samples_csv, row.names = FALSE, fileEncoding = "UTF-8")

freq <- terra::freq(r_clean) |>
  as.data.frame()
if ("value" %in% names(freq)) {
  freq <- freq |>
    filter(!is.na(value)) |>
    transmute(class_value = as.integer(value), n_pixels = count)
} else {
  freq <- tibble(class_value = integer(), n_pixels = integer())
}

cell_area_m2 <- prod(terra::res(r_clean))
summary_df <- freq |>
  left_join(landscape_types, by = "class_value") |>
  arrange(class_value) |>
  transmute(
    type_id,
    type_name,
    bright_hex,
    n_pixels,
    approx_area_km2 = n_pixels * cell_area_m2 / 1e6
  )
summary_csv <- file.path(out_dir, "bornholm_pdf_bright_full_summary.csv")
write.csv(summary_df, summary_csv, row.names = FALSE, fileEncoding = "UTF-8")

classified_share <- sum(!is.na(clean_vals)) / length(clean_vals)

report <- c(
  "# Bornholm LABLAB PDF bright full-area class raster",
  "",
  paste0("- Source GIS PDF: `", pdf_gis, "`"),
  paste0("- Descriptive report PDF: `", source_report_pdf, "`"),
  paste0("- Output folder: `", out_dir, "`"),
  paste0("- PDF CRS: `", terra::crs(r_pdf, describe = TRUE)$code, "`, ", terra::crs(r_pdf, describe = TRUE)$name),
  paste0("- Raster size: ", ncol(r_pdf), " x ", nrow(r_pdf)),
  paste0("- Max RGB distance: ", max_distance),
  paste0("- Brightness filter: ", min_brightness, " to ", max_brightness),
  paste0("- Modal fill applied: ", do_modal_fill),
  paste0("- Classified pixel share after mask/fill: ", round(classified_share, 4)),
  paste0("- Landmask note: ", raw_masked$note),
  "",
  "## Status",
  "",
  "This is a helper product for QGIS review, not a final landscape-type layer.",
  "Bornholm's GIS PDF uses transparent landscape fills over orthophoto/imagery, so colour classification is inherently approximate.",
  "Use the bright RGB raster and per-type masks to support manual extraction and visual correction in QGIS.",
  "",
  "## Best file for QGIS colour picking",
  "",
  paste0("- `", bright_tif, "`"),
  "",
  "## Other outputs",
  "",
  paste0("- Clean class raster: `", clean_tif, "`"),
  paste0("- Raw class raster: `", raw_tif, "`"),
  paste0("- Unknown flag raster: `", unknown_tif, "`"),
  paste0("- RGB distance raster: `", dist_tif, "`"),
  paste0("- Polygon GeoPackage: `", ifelse(is.na(out_gpkg), "not written by default; run with WRITE_FULL_POLYGONS=1", out_gpkg), "`"),
  paste0("- Palette CSV: `", palette_csv, "`"),
  paste0("- Source colour sample CSV: `", source_samples_csv, "`"),
  paste0("- Summary CSV: `", summary_csv, "`"),
  "",
  "## Bright palette",
  "",
  paste(capture.output(print(as.data.frame(landscape_types[, c("type_id", "type_name", "bright_hex")]), row.names = FALSE)), collapse = "\n"),
  "",
  "## Summary",
  "",
  paste(capture.output(print(as.data.frame(summary_df), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(report), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", bright_tif)
message("Wrote: ", clean_tif)
message("Wrote: ", file.path(out_dir, "README.md"))
