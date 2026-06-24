#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(magick)
  library(sf)
  library(terra)
})

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || is.na(x)) y else x
}

script_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else ""
repo_root <- if (nzchar(script_path)) {
  normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
} else {
  normalizePath(getwd(), mustWork = TRUE)
}
if (!dir.exists(file.path(repo_root, "scripts"))) {
  repo_root <- normalizePath(getwd(), mustWork = TRUE)
}

artifact_dir <- file.path(repo_root, "artifacts", "skaraborg_landscape_georef")
page_dir <- file.path(artifact_dir, "pages")
dir.create(page_dir, recursive = TRUE, showWarnings = FALSE)

pdf_url <- "https://bransch.trafikverket.se/contentassets/31699a9e58664144a4291b2397dcd7dc/gestaltningsprogram_e20_150420.pdf"
pdf_path <- file.path(artifact_dir, "gestaltningsprogram_e20_150420.pdf")
page_png <- file.path(page_dir, "e20_page_08.png")
crop_png <- file.path(artifact_dir, "e20_regional_landscape_types_map_crop.png")
gcp_path <- file.path(repo_root, "docs", "georef", "skaraborg_e20_initial_gcps.csv")
residual_path <- file.path(artifact_dir, "e20_regional_landscape_types_initial_gcp_residuals.csv")
geotiff_path <- file.path(artifact_dir, "e20_regional_landscape_types_firstpass_epsg3006.tif")
preview_path <- file.path(artifact_dir, "e20_regional_landscape_types_firstpass_preview.png")

write_rgb_preview <- function(red, green, blue, path) {
  colors <- matrix(
    grDevices::rgb(
      as.vector(t(red)),
      as.vector(t(green)),
      as.vector(t(blue)),
      maxColorValue = 255
    ),
    nrow = nrow(red),
    ncol = ncol(red),
    byrow = TRUE
  )
  image_write(image_read(as.raster(colors)), path, format = "png")
}

if (!file.exists(pdf_path)) {
  message("Downloading source PDF...")
  download.file(pdf_url, pdf_path, mode = "wb", quiet = FALSE)
}

if (!file.exists(page_png)) {
  message("Rendering PDF page 8...")
  page_img <- image_read_pdf(pdf_path, pages = 8, density = 180)
  image_write(page_img, page_png, format = "png")
}

if (!file.exists(crop_png)) {
  message("Cropping map area...")
  page_img <- image_read(page_png)
  crop_img <- image_crop(page_img, geometry = "1930x1250+105+95")
  image_write(crop_img, crop_png, format = "png")
}

if (!file.exists(gcp_path)) {
  stop("Missing GCP table: ", gcp_path)
}

gcps <- read.csv(gcp_path, stringsAsFactors = FALSE)
required <- c("id", "label", "src_x", "src_y", "lon", "lat", "role")
missing <- setdiff(required, names(gcps))
if (length(missing)) {
  stop("GCP table is missing columns: ", paste(missing, collapse = ", "))
}

fit_gcps <- gcps[gcps$role == "fit", , drop = FALSE]
if (nrow(fit_gcps) < 6) {
  stop("Need at least 6 fit GCPs for a stable first-pass affine transform.")
}

gcp_sf <- st_as_sf(gcps, coords = c("lon", "lat"), crs = 4326, remove = FALSE)
gcp_sf <- st_transform(gcp_sf, 3006)
coords <- st_coordinates(gcp_sf)
gcps$target_x <- coords[, "X"]
gcps$target_y <- coords[, "Y"]
fit_gcps <- gcps[gcps$role == "fit", , drop = FALSE]

fit_x <- lm(target_x ~ src_x + src_y, data = fit_gcps)
fit_y <- lm(target_y ~ src_x + src_y, data = fit_gcps)

gcps$pred_x <- as.numeric(predict(fit_x, gcps))
gcps$pred_y <- as.numeric(predict(fit_y, gcps))
gcps$residual_m <- sqrt((gcps$pred_x - gcps$target_x)^2 + (gcps$pred_y - gcps$target_y)^2)
write.csv(gcps, residual_path, row.names = FALSE)
fit_residuals <- gcps[gcps$role == "fit", "residual_m"]

message(sprintf(
  "Affine residuals: median %.0f m, max %.0f m. This is a first-pass raster for manual review.",
  median(fit_residuals, na.rm = TRUE),
  max(fit_residuals, na.rm = TRUE)
))

img <- image_read(crop_png)
img_info <- image_info(img)
img_raw <- image_data(img, channels = "rgb")
src_width <- dim(img_raw)[2]
src_height <- dim(img_raw)[3]
if (!identical(src_width, img_info$width) || !identical(src_height, img_info$height)) {
  stop("Unexpected image dimensions while reading crop raster.")
}
src_red <- t(matrix(as.integer(img_raw[1, , ]), nrow = src_width, ncol = src_height))
src_green <- t(matrix(as.integer(img_raw[2, , ]), nrow = src_width, ncol = src_height))
src_blue <- t(matrix(as.integer(img_raw[3, , ]), nrow = src_width, ncol = src_height))

cx <- coef(fit_x)
cy <- coef(fit_y)
forward <- function(x, y) {
  cbind(
    unname(cx[1] + cx[2] * x + cx[3] * y),
    unname(cy[1] + cy[2] * x + cy[3] * y)
  )
}

corners <- data.frame(
  src_x = c(1, src_width, src_width, 1),
  src_y = c(1, 1, src_height, src_height)
)
corner_xy <- forward(corners$src_x, corners$src_y)
target_res_m <- 250
xmin <- floor(min(corner_xy[, 1]) / target_res_m) * target_res_m
xmax <- ceiling(max(corner_xy[, 1]) / target_res_m) * target_res_m
ymin <- floor(min(corner_xy[, 2]) / target_res_m) * target_res_m
ymax <- ceiling(max(corner_xy[, 2]) / target_res_m) * target_res_m
ncols <- ceiling((xmax - xmin) / target_res_m)
nrows <- ceiling((ymax - ymin) / target_res_m)

xs <- xmin + (seq_len(ncols) - 0.5) * target_res_m
ys <- ymax - (seq_len(nrows) - 0.5) * target_res_m

matrix_affine <- matrix(c(cx[2], cx[3], cy[2], cy[3]), nrow = 2, byrow = TRUE)
inverse_affine <- solve(matrix_affine)
origin <- c(cx[1], cy[1])

red <- green <- blue <- matrix(255L, nrow = nrows, ncol = ncols)
for (row_index in seq_len(nrows)) {
  target_x <- xs
  target_y <- rep(ys[row_index], ncols)
  delta <- rbind(target_x - origin[1], target_y - origin[2])
  src <- inverse_affine %*% delta
  sx <- round(src[1, ])
  sy <- round(src[2, ])
  valid <- sx >= 1 & sx <= src_width & sy >= 1 & sy <= src_height
  if (!any(valid)) {
    next
  }
  valid_idx <- which(valid)
  red[row_index, valid_idx] <- src_red[cbind(sy[valid], sx[valid])]
  green[row_index, valid_idx] <- src_green[cbind(sy[valid], sx[valid])]
  blue[row_index, valid_idx] <- src_blue[cbind(sy[valid], sx[valid])]
}

r <- rast(
  nrows = nrows,
  ncols = ncols,
  nlyrs = 3,
  xmin = xmin,
  xmax = xmax,
  ymin = ymin,
  ymax = ymax,
  crs = "EPSG:3006"
)
names(r) <- c("red", "green", "blue")
values(r) <- cbind(as.vector(t(red)), as.vector(t(green)), as.vector(t(blue)))
writeRaster(r, geotiff_path, overwrite = TRUE, datatype = "INT1U")
write_rgb_preview(red, green, blue, preview_path)

message("Wrote: ", geotiff_path)
message("Wrote: ", preview_path)
message("Wrote: ", residual_path)
