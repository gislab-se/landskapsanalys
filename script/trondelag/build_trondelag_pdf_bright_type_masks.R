#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(sf)
  library(terra)
})

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
source_dir <- file.path(repo_root, "data/processed/trondelag/pdf_polygon_bright_full_safe")
class_raster_path <- file.path(source_dir, "trondelag_pdf_bright_full_clean_class.tif")
palette_path <- file.path(source_dir, "trondelag_pdf_bright_full_palette.csv")

out_dir <- file.path(source_dir, "type_masks")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

classes <- read.csv(palette_path, stringsAsFactors = FALSE)
r_class <- terra::rast(class_raster_path)

make_rgb_mask <- function(mask, rgb_values) {
  red <- green <- blue <- mask
  terra::values(red) <- ifelse(terra::values(mask, mat = FALSE) == 1, rgb_values[1], 0)
  terra::values(green) <- ifelse(terra::values(mask, mat = FALSE) == 1, rgb_values[2], 0)
  terra::values(blue) <- ifelse(terra::values(mask, mat = FALSE) == 1, rgb_values[3], 0)
  out <- c(red, green, blue)
  names(out) <- c("red", "green", "blue")
  out
}

written <- list()
for (idx in seq_len(nrow(classes))) {
  class_value <- classes$class_value[idx]
  type_id <- classes$type_id[idx]
  type_name <- classes$type_name[idx]
  bright_hex <- classes$bright_hex[idx]
  rgb <- as.integer(grDevices::col2rgb(bright_hex)[, 1])

  message("Writing mask for ", type_id, " - ", type_name)
  mask <- r_class == class_value
  mask[mask == 0] <- NA
  names(mask) <- paste0(type_id, "_mask")

  binary_path <- file.path(out_dir, paste0("trondelag_pdf_bright_full_", type_id, "_binary_mask.tif"))
  rgb_path <- file.path(out_dir, paste0("trondelag_pdf_bright_full_", type_id, "_rgb_mask.tif"))

  terra::writeRaster(mask, binary_path, overwrite = TRUE, datatype = "INT1U", NAflag = 255)
  rgb_mask <- make_rgb_mask(mask, rgb)
  terra::writeRaster(rgb_mask, rgb_path, overwrite = TRUE, datatype = "INT1U")

  written[[idx]] <- data.frame(
    type_id = type_id,
    type_name = type_name,
    class_value = class_value,
    bright_hex = bright_hex,
    binary_mask = binary_path,
    rgb_mask = rgb_path,
    stringsAsFactors = FALSE
  )
}

index <- do.call(rbind, written)
index_path <- file.path(out_dir, "trondelag_pdf_bright_full_type_masks_index.csv")
write.csv(index, index_path, row.names = FALSE, fileEncoding = "UTF-8")

readme <- c(
  "# Trondelag bright type masks",
  "",
  "These rasters are made for QGIS colour-picking/vectorization plugins that behave best when one colour is extracted at a time.",
  "",
  "## How to use",
  "",
  "1. Load one `*_rgb_mask.tif` at a time.",
  "2. Pick the visible colour in the plugin.",
  "3. Use a very narrow tolerance; the mask contains only one solid RGB colour plus black background.",
  "4. Save each extracted polygon layer with its `type_id`.",
  "5. Merge extracted polygon layers afterwards.",
  "",
  "Do not pick the black background colour.",
  "",
  "The `*_binary_mask.tif` files are 1/NoData masks if you prefer QGIS/Processing polygonize instead of the plugin.",
  "",
  "## Index",
  "",
  paste(capture.output(print(index[, c("type_id", "type_name", "bright_hex", "rgb_mask")], row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(readme), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote index: ", index_path)
message("Wrote README: ", file.path(out_dir, "README.md"))
