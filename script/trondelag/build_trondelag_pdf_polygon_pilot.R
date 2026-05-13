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
pdf_north <- file.path(repo_root, "data/raw/lablab/SpeedLocal/Trondelag/Norra Trondelag.pdf")
pdf_south <- file.path(repo_root, "data/raw/lablab/SpeedLocal/Trondelag/Södra Trondelag.pdf")

out_dir <- file.path(repo_root, "data/processed/trondelag/pdf_polygon_pilot")
artifact_dir <- file.path(out_dir, "artifacts")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(artifact_dir, recursive = TRUE, showWarnings = FALSE)

rendered_png <- file.path(artifact_dir, "pdf_gis_landskapstyper_trondelag_page01_240dpi.png")
if (!file.exists(rendered_png)) {
  message("Rendering GIS PDF at 240 dpi...")
  bitmap <- pdftools::pdf_render_page(pdf_gis, page = 1, dpi = 240, numeric = TRUE)
  png::writePNG(bitmap, rendered_png)
}

# Reference PDFs are rendered only for side-by-side QGIS/desktop inspection.
for (ref in c(pdf_north, pdf_south)) {
  if (file.exists(ref)) {
    out_ref <- file.path(
      artifact_dir,
      paste0(tools::file_path_sans_ext(basename(ref)), "_page01_180dpi.png")
    )
    if (!file.exists(out_ref)) {
      message("Rendering reference PDF: ", basename(ref))
      bitmap <- pdftools::pdf_render_page(ref, page = 1, dpi = 180, numeric = TRUE)
      png::writePNG(bitmap, out_ref)
    }
  }
}

img <- png::readPNG(rendered_png)
img_rows <- dim(img)[1]
img_cols <- dim(img)[2]

# Geospatial metadata read from the QGIS GIS-PDF in the earlier Trondelag pipeline.
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
  color_hex = c(
    "#5F7FA1",
    "#C4D2DA",
    "#E6E8B6",
    "#92B08E",
    "#BDAA87",
    "#99A395",
    "#E5E8E1",
    "#A1A557",
    "#CAD0C6"
  )
)
palette_rgb <- t(grDevices::col2rgb(landscape_types$color_hex) / 255)
colnames(palette_rgb) <- c("r", "g", "b")

rgb_distance <- function(rgb_mat, palette_mat) {
  out <- matrix(NA_real_, nrow = nrow(rgb_mat), ncol = nrow(palette_mat))
  for (idx in seq_len(nrow(palette_mat))) {
    out[, idx] <- sqrt(rowSums((rgb_mat - matrix(palette_mat[idx, ], nrow(rgb_mat), 3, byrow = TRUE))^2))
  }
  out
}

xy_to_pixel <- function(x, y) {
  data.frame(
    col = round(((x - x_min) / (x_max - x_min)) * (img_cols - 1) + 1),
    row = round(((y_max - y) / (y_max - y_min)) * (img_rows - 1) + 1)
  )
}

pixel_to_x <- function(col) x_min + ((col - 1) / (img_cols - 1)) * (x_max - x_min)
pixel_to_y <- function(row) y_max - ((row - 1) / (img_rows - 1)) * (y_max - y_min)

# Same review window as the first H3 area-share pilot.
pilot_bbox_wgs84 <- st_as_sfc(st_bbox(
  c(xmin = 10.10, ymin = 63.22, xmax = 10.78, ymax = 63.62),
  crs = 4326
))
pilot_bbox_3857 <- st_bbox(st_transform(pilot_bbox_wgs84, 3857))

pix_min <- xy_to_pixel(pilot_bbox_3857[["xmin"]], pilot_bbox_3857[["ymax"]])
pix_max <- xy_to_pixel(pilot_bbox_3857[["xmax"]], pilot_bbox_3857[["ymin"]])
col_min <- max(1, min(pix_min$col, pix_max$col))
col_max <- min(img_cols, max(pix_min$col, pix_max$col))
row_min <- max(1, min(pix_min$row, pix_max$row))
row_max <- min(img_rows, max(pix_min$row, pix_max$row))

message("Cropping PDF raster to rows ", row_min, ":", row_max, ", cols ", col_min, ":", col_max)
crop_img <- img[row_min:row_max, col_min:col_max, 1:3, drop = FALSE]
crop_rows <- dim(crop_img)[1]
crop_cols <- dim(crop_img)[2]
rgb <- matrix(crop_img, ncol = 3)

dist_mat <- rgb_distance(rgb, palette_rgb)
best_idx <- max.col(-dist_mat, ties.method = "first")
best_dist <- dist_mat[cbind(seq_len(nrow(dist_mat)), best_idx)]

# Conservative threshold: keep real landscape colours, reject white linework,
# black boundaries, labels, roads and basemap texture.
max_distance <- 0.16
class_vec <- landscape_types$class_value[best_idx]
class_vec[is.na(best_dist) | best_dist > max_distance] <- NA_integer_
class_mat <- matrix(class_vec, nrow = crop_rows, ncol = crop_cols)
dist_mat_min <- matrix(best_dist, nrow = crop_rows, ncol = crop_cols)
unknown_mat <- is.na(class_mat)

crop_extent <- terra::ext(
  pixel_to_x(col_min),
  pixel_to_x(col_max),
  pixel_to_y(row_max),
  pixel_to_y(row_min)
)

r_raw <- terra::rast(class_mat, extent = crop_extent, crs = "EPSG:3857")
r_dist <- terra::rast(dist_mat_min, extent = crop_extent, crs = "EPSG:3857")
r_unknown <- terra::rast(unknown_mat * 1, extent = crop_extent, crs = "EPSG:3857")

names(r_raw) <- "class_value"
names(r_dist) <- "rgb_distance"
names(r_unknown) <- "unknown_flag"

# Fill linework/gaps by local modal class. Repeating this creates a complete
# categorical surface for the pilot window without drawing individual hexes.
modal_fun <- function(values, ...) {
  values <- values[!is.na(values)]
  if (!length(values)) return(NA_real_)
  as.numeric(names(sort(table(values), decreasing = TRUE)[1]))
}
r_filled <- r_raw
for (idx in 1:5) {
  fill <- terra::focal(
    r_filled,
    w = matrix(1, 7, 7),
    fun = modal_fun,
    na.policy = "only",
    fillvalue = NA
  )
  r_filled <- terra::cover(r_filled, fill)
}

# A light modal smoothing pass removes isolated colour speckles but still keeps
# the broad boundaries visible for review.
r_clean <- terra::focal(
  r_filled,
  w = matrix(1, 3, 3),
  fun = modal_fun,
  na.policy = "all",
  fillvalue = NA
)
names(r_filled) <- "class_value"
names(r_clean) <- "class_value"

raw_tif <- file.path(out_dir, "trondelag_pdf_polygon_pilot_raw_class.tif")
clean_tif <- file.path(out_dir, "trondelag_pdf_polygon_pilot_clean_class.tif")
unknown_tif <- file.path(out_dir, "trondelag_pdf_polygon_pilot_unknown_flag.tif")
dist_tif <- file.path(out_dir, "trondelag_pdf_polygon_pilot_rgb_distance.tif")
terra::writeRaster(r_raw, raw_tif, overwrite = TRUE, datatype = "INT1U")
terra::writeRaster(r_clean, clean_tif, overwrite = TRUE, datatype = "INT1U")
terra::writeRaster(r_unknown, unknown_tif, overwrite = TRUE, datatype = "INT1U")
terra::writeRaster(r_dist, dist_tif, overwrite = TRUE, datatype = "FLT4S")

message("Polygonising cleaned class raster...")
poly <- terra::as.polygons(r_clean, dissolve = TRUE, values = TRUE, na.rm = TRUE)
poly_sf <- st_as_sf(poly) |>
  st_make_valid() |>
  rename(class_value = class_value) |>
  mutate(class_value = as.integer(class_value)) |>
  left_join(landscape_types, by = "class_value") |>
  mutate(
    source = "pdf_fixed_palette_polygon_pilot",
    confidence = "pilot_cleaned_raster",
    area_m2 = as.numeric(st_area(geometry))
  ) |>
  st_transform(4326)

pilot_bbox_sf <- st_sf(
  name = "polygon_pilot_bbox",
  geometry = pilot_bbox_wgs84
)

out_gpkg <- file.path(out_dir, "trondelag_pdf_polygon_pilot.gpkg")
if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(poly_sf, out_gpkg, layer = "landscape_type_polygons_clean", quiet = TRUE)
st_write(st_transform(pilot_bbox_sf, 4326), out_gpkg, layer = "pilot_bbox", append = TRUE, quiet = TRUE)

summary_df <- poly_sf |>
  st_drop_geometry() |>
  group_by(type_id, type_name) |>
  summarise(n_parts = n(), area_km2 = sum(area_m2) / 1e6, .groups = "drop") |>
  arrange(type_id)
write.csv(
  summary_df,
  file.path(out_dir, "trondelag_pdf_polygon_pilot_summary.csv"),
  row.names = FALSE,
  fileEncoding = "UTF-8"
)

unknown_share <- global(r_unknown, "mean", na.rm = TRUE)[1, 1]
remaining_na_share <- global(is.na(r_clean), "mean", na.rm = TRUE)[1, 1]

report <- c(
  "# Trondelag PDF polygon pilot",
  "",
  paste0("- Source GIS PDF: `", pdf_gis, "`"),
  paste0("- North reference PDF: `", pdf_north, "`"),
  paste0("- South reference PDF: `", pdf_south, "`"),
  paste0("- Rendered GIS image: `", rendered_png, "`"),
  "- Pilot bbox: lon 10.10-10.78, lat 63.22-63.62",
  paste0("- Crop pixels: ", crop_cols, " x ", crop_rows),
  paste0("- Initial unknown pixel share: ", round(unknown_share, 4)),
  paste0("- Remaining NA share after modal fill: ", round(remaining_na_share, 6)),
  "",
  "## Outputs",
  "",
  paste0("- `", out_gpkg, "`"),
  paste0("- `", raw_tif, "`"),
  paste0("- `", clean_tif, "`"),
  paste0("- `", unknown_tif, "`"),
  paste0("- `", dist_tif, "`"),
  "",
  "## Method",
  "",
  "1. Rendered the georeferenced QGIS PDF to a 240 dpi raster.",
  "2. Cropped the raster to the Trondheimfjorden pilot area.",
  "3. Classified every pixel to the nearest fixed landscape-type palette colour.",
  "4. Rejected pixels farther than RGB distance 0.16 as linework/text/basemap/uncertain.",
  "5. Filled rejected pixels by repeated local modal class assignment.",
  "6. Applied a light 3x3 modal smoothing pass.",
  "7. Polygonised the cleaned class raster and dissolved by class.",
  "",
  "## Important limitation",
  "",
  "This is still raster-derived. It is polygon-first in topology, not yet a manually verified final vector interpretation. Use it to review whether polygon boundaries are cleaner than direct H3 classification.",
  "",
  "## Polygon summary",
  "",
  paste(capture.output(print(as.data.frame(summary_df), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(report), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", out_gpkg)
message("Wrote: ", clean_tif)
message("Wrote: ", file.path(out_dir, "README.md"))
