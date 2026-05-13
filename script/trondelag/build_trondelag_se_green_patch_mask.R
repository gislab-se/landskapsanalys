#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(pdftools)
  library(png)
  library(sf)
  library(terra)
})

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
pdf_gis <- file.path(
  repo_root,
  "data/raw/lablab/SpeedLocal/Trondelag/pdf-GIS/Landskapstyper Trondelag.pdf"
)

out_dir <- file.path(repo_root, "data/processed/trondelag/pdf_polygon_bright_full_safe/patches")
artifact_dir <- file.path(out_dir, "artifacts")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(artifact_dir, recursive = TRUE, showWarnings = FALSE)

rendered_png <- file.path(artifact_dir, "pdf_gis_landskapstyper_trondelag_page01_240dpi.png")
if (!file.exists(rendered_png)) {
  bitmap <- pdftools::pdf_render_page(pdf_gis, page = 1, dpi = 240, numeric = TRUE)
  png::writePNG(bitmap, rendered_png)
}

img <- png::readPNG(rendered_png)
img_rows <- dim(img)[1]
img_cols <- dim(img)[2]

# GIS-PDF georeferencing from the earlier pipeline.
lon_min <- 5.2259725346819259
lon_max <- 16.5493091473392795
lat_min <- 62.0893610343025841
lat_max <- 65.612607873276616

corners <- st_as_sf(
  data.frame(corner = c("lower_left", "upper_right"), lon = c(lon_min, lon_max), lat = c(lat_min, lat_max)),
  coords = c("lon", "lat"),
  crs = 4326
)
corners_3857 <- st_coordinates(st_transform(corners, 3857))
x_min <- corners_3857[1, 1]
y_min <- corners_3857[1, 2]
x_max <- corners_3857[2, 1]
y_max <- corners_3857[2, 2]

xy_to_pixel <- function(x, y) {
  data.frame(
    col = round(((x - x_min) / (x_max - x_min)) * (img_cols - 1) + 1),
    row = round(((y_max - y) / (y_max - y_min)) * (img_rows - 1) + 1)
  )
}
pixel_to_x <- function(col) x_min + ((col - 1) / (img_cols - 1)) * (x_max - x_min)
pixel_to_y <- function(row) y_max - ((row - 1) / (img_rows - 1)) * (y_max - y_min)

# Focus area: lower-right part of the Trondheimfjorden pilot where the pale
# green class is easy to absorb into the grey-green class.
patch_bbox_wgs84 <- st_as_sfc(st_bbox(c(xmin = 10.52, ymin = 63.22, xmax = 10.79, ymax = 63.38), crs = 4326))
patch_bbox_3857 <- st_bbox(st_transform(patch_bbox_wgs84, 3857))
pix_min <- xy_to_pixel(patch_bbox_3857[["xmin"]], patch_bbox_3857[["ymax"]])
pix_max <- xy_to_pixel(patch_bbox_3857[["xmax"]], patch_bbox_3857[["ymin"]])
col_min <- max(1, min(pix_min$col, pix_max$col))
col_max <- min(img_cols, max(pix_min$col, pix_max$col))
row_min <- max(1, min(pix_min$row, pix_max$row))
row_max <- min(img_rows, max(pix_min$row, pix_max$row))

crop <- img[row_min:row_max, col_min:col_max, 1:3, drop = FALSE]
r <- crop[, , 1]
g <- crop[, , 2]
b <- crop[, , 3]

# Candidate for the missing pale green / grey-green landscape type.
# It targets greenish low-saturation pixels that are darker/greener than the
# near-white grey class, while excluding dark boundary lines and basemap texture.
greenish <- (
  r > 0.62 & r < 0.88 &
    g > 0.66 & g < 0.90 &
    b > 0.58 & b < 0.84 &
    g >= r - 0.03 &
    g >= b + 0.015 &
    abs(r - b) < 0.16
)

extent <- terra::ext(pixel_to_x(col_min), pixel_to_x(col_max), pixel_to_y(row_max), pixel_to_y(row_min))
mask <- terra::rast(greenish * 1, extent = extent, crs = "EPSG:3857")
mask[mask == 0] <- NA
names(mask) <- "se_green_patch"

# Plugin-friendly RGB mask: one strong safe colour plus black background.
red <- green <- blue <- mask
terra::values(red) <- ifelse(terra::values(mask, mat = FALSE) == 1, 32, 0)
terra::values(green) <- ifelse(terra::values(mask, mat = FALSE) == 1, 232, 0)
terra::values(blue) <- ifelse(terra::values(mask, mat = FALSE) == 1, 168, 0)
rgb_mask <- c(red, green, blue)
names(rgb_mask) <- c("red", "green", "blue")

binary_path <- file.path(out_dir, "trondelag_se_green_patch_binary_mask.tif")
rgb_path <- file.path(out_dir, "trondelag_se_green_patch_rgb_mask.tif")
terra::writeRaster(mask, binary_path, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
terra::writeRaster(rgb_mask, rgb_path, overwrite = TRUE, datatype = "INT1U")

poly <- terra::as.polygons(mask, dissolve = TRUE, values = TRUE, na.rm = TRUE)
poly_sf <- st_as_sf(poly) |>
  st_make_valid() |>
  st_transform(4326)
poly_sf$type_id <- "SE_GREEN_PATCH"
poly_sf$review_note <- "Candidate missing pale green area; review and assign target LT in QGIS."
gpkg_path <- file.path(out_dir, "trondelag_se_green_patch_candidate.gpkg")
if (file.exists(gpkg_path)) file.remove(gpkg_path)
st_write(poly_sf, gpkg_path, layer = "se_green_patch_candidate", quiet = TRUE)

readme <- c(
  "# SE green patch candidate",
  "",
  "This is a focused mask for the lower-right greenish type that was being absorbed into the grey class.",
  "",
  "## Files",
  "",
  paste0("- RGB mask for plugin: `", rgb_path, "`"),
  paste0("- Binary mask: `", binary_path, "`"),
  paste0("- Candidate polygon: `", gpkg_path, "`"),
  "",
  "## QGIS use",
  "",
  "Load `trondelag_se_green_patch_rgb_mask.tif`, pick the visible mint colour, extract, and merge/assign it to the correct landscape type after visual review.",
  "",
  "The polygon is intentionally called `SE_GREEN_PATCH` because it is a candidate correction, not a final class assignment."
)
writeLines(enc2utf8(readme), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", rgb_path)
message("Wrote: ", binary_path)
message("Wrote: ", gpkg_path)
