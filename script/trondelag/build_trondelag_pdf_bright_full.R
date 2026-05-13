#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(pdftools)
  library(png)
  library(sf)
  library(terra)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)

pdf_gis <- file.path(
  repo_root,
  "data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper Trondelag.pdf"
)

out_dir <- file.path(repo_root, "data/processed/trondelag/pdf_polygon_bright_full_safe")
artifact_dir <- file.path(out_dir, "artifacts")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(artifact_dir, recursive = TRUE, showWarnings = FALSE)

rendered_png <- file.path(artifact_dir, "pdf_gis_landskapstyper_trondelag_page01_180dpi.png")
if (!file.exists(rendered_png)) {
  message("Rendering GIS PDF at 180 dpi...")
  bitmap <- pdftools::pdf_render_page(pdf_gis, page = 1, dpi = 180, numeric = TRUE)
  png::writePNG(bitmap, rendered_png)
}

img <- png::readPNG(rendered_png)
img_rows <- dim(img)[1]
img_cols <- dim(img)[2]

# Geospatial metadata read from the QGIS GIS-PDF in the earlier pipeline.
lon_min <- 5.2259725346819259
lon_max <- 16.5493091473392795
lat_min <- 62.0893610343025841
lat_max <- 65.612607873276616

corners <- st_as_sf(
  data.frame(
    corner = c("lower_left", "upper_right"),
    lon = c(lon_min, lon_max),
    lat = c(lat_min, lat_max)
  ),
  coords = c("lon", "lat"),
  crs = 4326
)
corners_3857 <- st_coordinates(st_transform(corners, 3857))
x_min <- corners_3857[1, 1]
y_min <- corners_3857[1, 2]
x_max <- corners_3857[2, 1]
y_max <- corners_3857[2, 2]

landscape_types <- tibble::tibble(
  class_value = 1:9,
  type_id = sprintf("LT%02d", 1:9),
  type_name = c(
    "Ytterkustlandskap",
    "Fjordlandskap",
    "Fjordnara jordbrukslandskap",
    "Fjallnara skogslandskap",
    "Dalgangslandskap",
    "Lagfjallslandskap",
    "Hogfjallslandskap",
    "Sjo- och vatmarkslandskap",
    "Vidstrackt fjallandskap"
  ),
  source_hex = c(
    "#5F7FA1",
    "#C4D2DA",
    "#E6E8B6",
    "#92B08E",
    "#BDAA87",
    "#99A395",
    "#E5E8E1",
    "#A1A557",
    "#CAD0C6"
  ),
  bright_hex = c(
    "#1E5AF0", # electric blue
    "#18DCEB", # cyan
    "#F2DC10", # yellow
    "#19D64A", # green
    "#F07818", # orange
    "#A020E8", # violet
    "#E81AAE", # magenta
    "#F01818", # red
    "#20E8A8"  # mint
  )
)

source_rgb <- t(grDevices::col2rgb(landscape_types$source_hex) / 255)
bright_rgb_255 <- t(grDevices::col2rgb(landscape_types$bright_hex))
colnames(source_rgb) <- c("r", "g", "b")
colnames(bright_rgb_255) <- c("r", "g", "b")

rgb_distance <- function(rgb_mat, palette_mat) {
  out <- matrix(NA_real_, nrow = nrow(rgb_mat), ncol = nrow(palette_mat))
  for (idx in seq_len(nrow(palette_mat))) {
    out[, idx] <- sqrt(rowSums((rgb_mat - matrix(palette_mat[idx, ], nrow(rgb_mat), 3, byrow = TRUE))^2))
  }
  out
}

modal_fun <- function(values, ...) {
  values <- values[!is.na(values)]
  if (!length(values)) return(NA_real_)
  as.numeric(names(sort(table(values), decreasing = TRUE)[1]))
}

message("Classifying whole GIS PDF raster: ", img_cols, " x ", img_rows, " pixels...")
rgb <- matrix(img[, , 1:3], ncol = 3)
best_dist <- rep(Inf, nrow(rgb))
best_idx <- rep(NA_integer_, nrow(rgb))
for (idx in seq_len(nrow(source_rgb))) {
  dist <- sqrt(rowSums((rgb - matrix(source_rgb[idx, ], nrow(rgb), 3, byrow = TRUE))^2))
  hit <- dist < best_dist
  best_dist[hit] <- dist[hit]
  best_idx[hit] <- idx
}

max_distance <- 0.16
class_vec <- landscape_types$class_value[best_idx]
class_vec[is.na(best_dist) | best_dist > max_distance] <- NA_integer_
class_mat <- matrix(class_vec, nrow = img_rows, ncol = img_cols)
dist_min_mat <- matrix(best_dist, nrow = img_rows, ncol = img_cols)
unknown_mat <- is.na(class_mat)

full_extent <- terra::ext(x_min, x_max, y_min, y_max)
r_raw <- terra::rast(class_mat, extent = full_extent, crs = "EPSG:3857")
r_dist <- terra::rast(dist_min_mat, extent = full_extent, crs = "EPSG:3857")
r_unknown <- terra::rast(unknown_mat * 1, extent = full_extent, crs = "EPSG:3857")
names(r_raw) <- "class_value"
names(r_dist) <- "rgb_distance"
names(r_unknown) <- "unknown_flag"

raw_tif <- file.path(out_dir, "trondelag_pdf_bright_full_raw_class.tif")
unknown_tif <- file.path(out_dir, "trondelag_pdf_bright_full_unknown_flag.tif")
dist_tif <- file.path(out_dir, "trondelag_pdf_bright_full_rgb_distance.tif")
terra::writeRaster(r_raw, raw_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(r_unknown, unknown_tif, overwrite = TRUE, datatype = "INT1U")
terra::writeRaster(r_dist, dist_tif, overwrite = TRUE, datatype = "FLT4S")

do_modal_fill <- identical(Sys.getenv("DO_MODAL_FILL"), "1")
r_clean <- r_raw
if (do_modal_fill) {
  message("Filling uncertain/linework pixels by local modal class...")
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
  }
} else {
  message("Skipping modal fill by default; set DO_MODAL_FILL=1 for a filled class raster.")
}
names(r_clean) <- "class_value"

message("Creating bright RGB class raster...")
clean_vals <- terra::values(r_clean, mat = FALSE)
red <- green <- blue <- rep(NA_integer_, length(clean_vals))
for (idx in seq_len(nrow(landscape_types))) {
  hit <- clean_vals == landscape_types$class_value[idx]
  red[hit] <- bright_rgb_255[idx, "r"]
  green[hit] <- bright_rgb_255[idx, "g"]
  blue[hit] <- bright_rgb_255[idx, "b"]
}
r_red <- r_clean
r_green <- r_clean
r_blue <- r_clean
terra::values(r_red) <- red
terra::values(r_green) <- green
terra::values(r_blue) <- blue
r_rgb <- c(r_red, r_green, r_blue)
names(r_rgb) <- c("red", "green", "blue")

clean_tif <- file.path(out_dir, "trondelag_pdf_bright_full_clean_class.tif")
bright_tif <- file.path(out_dir, "trondelag_pdf_bright_full_bright_rgb.tif")

terra::writeRaster(r_clean, clean_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(r_rgb, bright_tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255)

out_gpkg <- file.path(out_dir, "trondelag_pdf_bright_full_polygons.gpkg")
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
      source = "pdf_fixed_palette_bright_full",
      confidence = "full_cleaned_raster",
      area_m2 = as.numeric(st_area(geometry))
    ) |>
    st_transform(4326)
  if (file.exists(out_gpkg)) file.remove(out_gpkg)
  st_write(poly_sf, out_gpkg, layer = "landscape_type_polygons_bright_full", quiet = TRUE)
} else {
  out_gpkg <- NA_character_
}

palette_csv <- file.path(out_dir, "trondelag_pdf_bright_full_palette.csv")
write.csv(landscape_types, palette_csv, row.names = FALSE, fileEncoding = "UTF-8")

clean_freq <- terra::freq(r_clean) |>
  as.data.frame() |>
  rename(class_value = value, n_pixels = count) |>
  filter(!is.na(class_value)) |>
  mutate(class_value = as.integer(class_value)) |>
  left_join(landscape_types, by = "class_value") |>
  arrange(class_value)
cell_area_m2 <- prod(terra::res(r_clean))
summary_df <- clean_freq |>
  transmute(type_id, type_name, bright_hex, n_pixels, approx_area_km2 = n_pixels * cell_area_m2 / 1e6)
summary_csv <- file.path(out_dir, "trondelag_pdf_bright_full_summary.csv")
write.csv(summary_df, summary_csv, row.names = FALSE, fileEncoding = "UTF-8")

unknown_share <- terra::global(r_unknown, "mean", na.rm = TRUE)[1, 1]
remaining_na_share <- terra::global(is.na(r_clean), "mean", na.rm = TRUE)[1, 1]

report <- c(
  "# Trondelag PDF bright full-area class raster",
  "",
  paste0("- Source GIS PDF: `", pdf_gis, "`"),
  paste0("- Rendered image: `", rendered_png, "`"),
  paste0("- Raster size: ", img_cols, " x ", img_rows),
  paste0("- Initial unknown pixel share: ", round(unknown_share, 4)),
  paste0("- Modal fill applied: ", do_modal_fill),
  paste0("- Remaining NA share in output class raster: ", round(remaining_na_share, 6)),
  "",
  "## Best file for QGIS plugin colour picking",
  "",
  paste0("- `", bright_tif, "`"),
  "",
  "This is a 3-band RGB GeoTIFF where each landscape type has a solid high-contrast colour. Use this instead of the original PDF if a plugin asks you to pick colours and set tolerance. By default, uncertain PDF pixels are NoData rather than filled.",
  "",
  "## Suggested tolerance workflow",
  "",
  "1. Load `trondelag_pdf_bright_full_bright_rgb.tif`.",
  "2. Pick one of the bright colours.",
  "3. Use a narrow tolerance first. Because the colours are solid, it should not need a broad spectrum.",
  "4. Extract one colour/type at a time if the plugin behaves better that way.",
  "",
  "## Bright palette",
  "",
  paste(capture.output(print(as.data.frame(landscape_types[, c("type_id", "type_name", "bright_hex")]), row.names = FALSE)), collapse = "\n"),
  "",
  "## Other outputs",
  "",
  paste0("- Clean class raster: `", clean_tif, "`"),
  paste0("- Raw class raster: `", raw_tif, "`"),
  paste0("- Unknown flag raster: `", unknown_tif, "`"),
  paste0("- RGB distance raster: `", dist_tif, "`"),
  paste0("- Polygon GeoPackage: `", ifelse(is.na(out_gpkg), "not written by default; run with WRITE_FULL_POLYGONS=1", out_gpkg), "`"),
  paste0("- Palette CSV: `", palette_csv, "`"),
  paste0("- Summary CSV: `", summary_csv, "`"),
  "",
  "## Summary",
  "",
  paste(capture.output(print(as.data.frame(summary_df), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(report), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", bright_tif)
if (!is.na(out_gpkg)) message("Wrote: ", out_gpkg)
message("Wrote: ", file.path(out_dir, "README.md"))
