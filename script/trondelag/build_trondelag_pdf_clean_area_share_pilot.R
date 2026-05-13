#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(h3jsr)
  library(pdftools)
  library(png)
  library(sf)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)

pdf_gis <- file.path(
  repo_root,
  "data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper Trondelag.pdf"
)
current_pdf_h3 <- file.path(
  repo_root,
  "data/processed/trondelag/landscape/trondelag_landscape_pdf_h3_r8.geojson"
)
land_mask_path <- file.path(
  repo_root,
  "data/processed/trondelag/mask/trondelag_land_region_mask_25832.gpkg"
)

out_dir <- file.path(repo_root, "data/processed/trondelag/pdf_clean_pilot")
artifact_dir <- file.path(out_dir, "artifacts")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(artifact_dir, recursive = TRUE, showWarnings = FALSE)

rendered_png <- file.path(artifact_dir, "pdf_gis_landskapstyper_trondelag_page01_180dpi.png")
if (!file.exists(rendered_png)) {
  bitmap <- pdftools::pdf_render_page(pdf_gis, page = 1, dpi = 180, numeric = TRUE)
  png::writePNG(bitmap, rendered_png)
}

img <- png::readPNG(rendered_png)
img_rows <- dim(img)[1]
img_cols <- dim(img)[2]

# Geospatial metadata read from the QGIS GIS-PDF in the previous pipeline run.
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
  hex = c(
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
palette_rgb <- t(grDevices::col2rgb(landscape_types$hex) / 255)
colnames(palette_rgb) <- c("r", "g", "b")

rgb_distance <- function(rgb_mat, palette_mat) {
  out <- matrix(NA_real_, nrow = nrow(rgb_mat), ncol = nrow(palette_mat))
  for (idx in seq_len(nrow(palette_mat))) {
    out[, idx] <- sqrt(rowSums((rgb_mat - matrix(palette_mat[idx, ], nrow(rgb_mat), 3, byrow = TRUE))^2))
  }
  out
}

points_to_pixel <- function(coords_3857) {
  data.frame(
    col = round(((coords_3857[, 1] - x_min) / (x_max - x_min)) * (img_cols - 1) + 1),
    row = round(((y_max - coords_3857[, 2]) / (y_max - y_min)) * (img_rows - 1) + 1)
  )
}

sample_pixel_rgb <- function(pixel_df, radius = 1) {
  rgb <- matrix(NA_real_, nrow = nrow(pixel_df), ncol = 3)
  colnames(rgb) <- c("r", "g", "b")
  for (idx in seq_len(nrow(pixel_df))) {
    col <- pixel_df$col[idx]
    row <- pixel_df$row[idx]
    if (is.na(col) || is.na(row) || col < 1 || row < 1 || col > img_cols || row > img_rows) {
      next
    }
    rows <- max(1, row - radius):min(img_rows, row + radius)
    cols <- max(1, col - radius):min(img_cols, col + radius)
    values <- matrix(img[rows, cols, 1:3], ncol = 3)
    rgb[idx, ] <- apply(values, 2, median)
  }
  rgb
}

classify_rgb <- function(rgb_mat, max_distance = 0.16) {
  d <- rgb_distance(rgb_mat, palette_rgb)
  min_idx <- max.col(-d, ties.method = "first")
  min_dist <- d[cbind(seq_len(nrow(d)), min_idx)]
  type_id <- landscape_types$type_id[min_idx]
  type_id[is.na(min_dist) | min_dist > max_distance] <- NA_character_
  list(type_id = type_id, distance = min_dist)
}

# Pilot window chosen around Trondheimfjorden, where the current app screenshot
# shows pale boundary artifacts between several landscape types.
pilot_bbox <- st_as_sfc(st_bbox(
  c(xmin = 10.10, ymin = 63.22, xmax = 10.78, ymax = 63.62),
  crs = 4326
))

message("Reading current PDF-derived H3 layer for pilot hex ids...")
current <- st_read(current_pdf_h3, quiet = TRUE)
current <- st_make_valid(current)
current_pilot <- current[lengths(st_intersects(current, pilot_bbox)) > 0, ]
pilot_hex_ids <- current_pilot$hex_id
pilot_hex_ids <- unique(as.character(pilot_hex_ids))
if (length(pilot_hex_ids) == 0) {
  stop("No H3 cells found in pilot bbox.")
}
current_lookup <- current_pilot |>
  st_drop_geometry() |>
  transmute(
    hex_id = as.character(hex_id),
    current_type_id = landscape_type_id,
    current_type_name = landscape_type_name,
    current_pdf_confidence = pdf_confidence
  )

message("Building full H3 polygons for ", length(pilot_hex_ids), " pilot cells...")
full_hex <- h3jsr::cell_to_polygon(pilot_hex_ids, simple = FALSE) |>
  rename(hex_id = h3_address) |>
  st_make_valid()
full_hex_3857 <- st_transform(full_hex, 3857)

land_mask <- st_read(land_mask_path, quiet = TRUE) |>
  st_make_valid() |>
  st_transform(3857)

samples_per_hex <- 36
hex_area_m2 <- as.numeric(st_area(full_hex_3857))
land_intersections <- suppressWarnings(st_intersection(full_hex_3857[, "hex_id"], land_mask))
land_by_hex <- land_intersections |>
  mutate(part_area_m2 = as.numeric(st_area(geometry))) |>
  st_drop_geometry() |>
  group_by(hex_id) |>
  summarise(land_area_m2 = sum(part_area_m2), .groups = "drop")

message("Sampling ", samples_per_hex, " interior points per full hex...")
share_rows <- vector("list", nrow(full_hex_3857))
for (idx in seq_len(nrow(full_hex_3857))) {
  geom <- st_geometry(full_hex_3857[idx, ])
  pts <- st_sample(geom, size = samples_per_hex, type = "regular", exact = FALSE)
  if (length(pts) == 0) {
    share_rows[[idx]] <- tibble::tibble(hex_id = full_hex_3857$hex_id[idx], n_samples = 0L)
    next
  }
  coords <- st_coordinates(pts)
  pix <- points_to_pixel(coords)
  rgb <- sample_pixel_rgb(pix, radius = 1)
  cls <- classify_rgb(rgb, max_distance = 0.16)
  tab <- table(factor(cls$type_id, levels = landscape_types$type_id), useNA = "no")
  unknown_n <- sum(is.na(cls$type_id))
  n_total <- length(cls$type_id)
  shares <- as.numeric(tab) / n_total
  names(shares) <- paste0(landscape_types$type_id, "_share")
  dominant_idx <- if (sum(tab) > 0) which.max(tab) else NA_integer_
  share_rows[[idx]] <- tibble::tibble(
    hex_id = full_hex_3857$hex_id[idx],
    n_samples = n_total,
    unknown_share = unknown_n / n_total,
    mean_color_distance = mean(cls$distance, na.rm = TRUE),
    dominant_type_id = if (!is.na(dominant_idx)) landscape_types$type_id[dominant_idx] else NA_character_,
    dominant_type_name = if (!is.na(dominant_idx)) landscape_types$type_name[dominant_idx] else NA_character_,
    dominant_share = if (!is.na(dominant_idx)) max(as.numeric(tab)) / n_total else NA_real_
  ) |>
    bind_cols(as.data.frame(as.list(shares)))
}

share_df <- bind_rows(share_rows)
share_df <- share_df |>
  left_join(
    tibble::tibble(hex_id = full_hex_3857$hex_id, full_hex_area_m2 = hex_area_m2),
    by = "hex_id"
  ) |>
  left_join(current_lookup, by = "hex_id") |>
  left_join(land_by_hex, by = "hex_id") |>
  mutate(
    land_area_m2 = ifelse(is.na(land_area_m2), 0, land_area_m2),
    land_share = pmax(0, pmin(1, land_area_m2 / full_hex_area_m2)),
    changed_from_current = !is.na(current_type_id) & !is.na(dominant_type_id) & current_type_id != dominant_type_id
  )

pilot_sf <- full_hex |>
  left_join(share_df, by = "hex_id") |>
  st_transform(4326)

out_gpkg <- file.path(out_dir, "trondelag_pdf_clean_pilot_h3_r8_area_share.gpkg")
out_geojson <- file.path(out_dir, "trondelag_pdf_clean_pilot_h3_r8_area_share.geojson")
out_csv <- file.path(out_dir, "trondelag_pdf_clean_pilot_h3_r8_area_share_summary.csv")
if (file.exists(out_gpkg)) file.remove(out_gpkg)
if (file.exists(out_geojson)) file.remove(out_geojson)
st_write(pilot_sf, out_gpkg, layer = "h3_r8_area_share_pilot", quiet = TRUE)
st_write(pilot_sf, out_geojson, driver = "GeoJSON", quiet = TRUE)

summary_df <- pilot_sf |>
  st_drop_geometry() |>
  count(dominant_type_id, dominant_type_name, name = "n_hex") |>
  arrange(dominant_type_id)
write.csv(summary_df, out_csv, row.names = FALSE, fileEncoding = "UTF-8")

report <- c(
  "# Trondelag PDF clean area-share pilot",
  "",
  paste0("- Source GIS PDF: `", pdf_gis, "`"),
  paste0("- Rendered image: `", rendered_png, "`"),
  "- Pilot bbox: lon 10.10-10.78, lat 63.22-63.62",
  paste0("- H3 cells: ", nrow(pilot_sf)),
  paste0("- Samples per full H3 cell: ", samples_per_hex),
  "- Classification: nearest fixed landscape-type palette; pixels farther than RGB distance 0.16 are `unknown`.",
  "- Geometry: full H3 R8 cells, not clipped to the land mask.",
  "- Land mask is used only to add `land_share` and `land_area_m2`.",
  "",
  "## Outputs",
  "",
  paste0("- `", out_gpkg, "`"),
  paste0("- `", out_geojson, "`"),
  paste0("- `", out_csv, "`"),
  "",
  "## Fields",
  "",
  "- `LT01_share` to `LT09_share`: approximate share of sampled full-hex area classified as each landscape type.",
  "- `unknown_share`: sampled share rejected as linework, labels, basemap texture, white gaps, or other non-palette colour.",
  "- `dominant_type_id`, `dominant_type_name`, `dominant_share`: dominant class from the sampled shares.",
  "- `current_type_id`, `current_type_name`, `current_pdf_confidence`: values from the current app layer for comparison.",
  "- `changed_from_current`: whether the new dominant type differs from the current app layer.",
  "- `land_share`: share of the full H3 hex covered by the preliminary land mask.",
  "",
  "## Dominant type counts",
  "",
  paste(capture.output(print(as.data.frame(summary_df), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(report), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", out_gpkg)
message("Wrote: ", out_geojson)
message("Wrote: ", out_csv)
message("Wrote: ", file.path(out_dir, "README.md"))
