suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
})

if (!requireNamespace("mapview", quietly = TRUE) || !requireNamespace("htmlwidgets", quietly = TRUE)) {
  stop("Packages 'mapview' and 'htmlwidgets' are required to render combined subcategory HTML.")
}

args <- commandArgs(trailingOnly = TRUE)
step_no <- suppressWarnings(as.integer(if (length(args) >= 1) args[1] else Sys.getenv("STEP_RUN_ORDER", "")))
run_order_guard_csv <- file.path("script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
run_order_guard <- if (file.exists(run_order_guard_csv)) read.csv(run_order_guard_csv, stringsAsFactors = FALSE) else data.frame(run_order = 44)
max_step <- suppressWarnings(max(as.integer(run_order_guard$run_order), na.rm = TRUE))
if (!is.finite(max_step)) max_step <- 44
if (is.na(step_no) || step_no < 1 || step_no > max_step) {
  stop(sprintf("Provide run step number 1..%d as argument, e.g. Rscript .../render_step_subcategory_combined_html.R 45", max_step))
}

output_path_override <- Sys.getenv("OUTPUT_PATH", "")
output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
  output_alpha <- 0.35
}

format_meter <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  if (is.na(x)) return("NA")
  if (x < 10) return(format(round(x, 1), trim = TRUE, nsmall = 1))
  format(round(x), scientific = FALSE, big.mark = " ", trim = TRUE)
}

compute_breaks <- function(x, n_target = 5L) {
  x <- suppressWarnings(as.numeric(x))
  x <- x[!is.na(x)]
  if (length(x) == 0) return(numeric(0))

  uniq <- sort(unique(x))
  n_bins <- min(as.integer(n_target), length(uniq))
  if (n_bins <= 1) return(range(x))

  brks <- NULL
  if (requireNamespace("classInt", quietly = TRUE)) {
    brks <- tryCatch(
      classInt::classIntervals(x, n = n_bins, style = "jenks")$brks,
      error = function(e) NULL
    )
  }
  if (is.null(brks)) {
    probs <- seq(0, 1, length.out = n_bins + 1)
    brks <- as.numeric(stats::quantile(x, probs = probs, na.rm = TRUE, names = FALSE, type = 7))
  }

  brks <- sort(unique(as.numeric(brks)))
  if (length(brks) < 2) return(range(x))
  brks[1] <- min(x)
  brks[length(brks)] <- max(x)
  sort(unique(brks))
}

length_palette <- function(n_nonzero) {
  if (n_nonzero <= 0) return(c("#ffffff10"))
  ramp <- grDevices::colorRampPalette(c("#fee8c8", "#fdbb84", "#fc8d59", "#ef6548", "#990000"))
  c("#ffffff10", ramp(n_nonzero))
}

classify_length_jenks <- function(vals, zero_level = "0", n_target = 5L) {
  vals <- suppressWarnings(as.numeric(vals))
  cls <- rep(NA_character_, length(vals))
  cls[!is.na(vals) & vals == 0] <- zero_level

  nz_idx <- which(!is.na(vals) & vals > 0)
  if (length(nz_idx) == 0) {
    return(list(class = factor(cls, levels = zero_level, ordered = TRUE), palette = c("#ffffff10")))
  }

  nz_vals <- vals[nz_idx]
  brks <- compute_breaks(nz_vals, n_target = n_target)
  if (length(brks) < 2 || (length(brks) == 2 && brks[1] == brks[2])) {
    pos_label <- ">0 m"
    cls[nz_idx] <- pos_label
    lev <- c(zero_level, pos_label)
    return(list(
      class = factor(cls, levels = lev, ordered = TRUE),
      palette = length_palette(length(lev) - 1)
    ))
  }

  labels <- vapply(seq_len(length(brks) - 1), function(i) {
    paste0(format_meter(brks[i]), "-", format_meter(brks[i + 1]), " m")
  }, character(1))

  bins <- cut(
    nz_vals,
    breaks = brks,
    include.lowest = TRUE,
    right = TRUE,
    labels = labels
  )
  cls[nz_idx] <- as.character(bins)
  lev <- c(zero_level, labels)

  list(
    class = factor(cls, levels = lev, ordered = TRUE),
    palette = length_palette(length(lev) - 1)
  )
}

format_area_share_percent <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  out <- rep(NA_character_, length(x))
  ok <- !is.na(x)
  out[ok] <- paste0(format(round(x[ok] * 100, 1), trim = TRUE, scientific = FALSE, nsmall = 1), "%")
  out
}

format_area_share_columns <- function(sf_obj) {
  share_cols <- names(sf_obj)[grepl("_area_share($|_)", names(sf_obj))]
  if (length(share_cols) == 0) {
    return(sf_obj)
  }
  for (nm in share_cols) {
    sf_obj[[nm]] <- format_area_share_percent(sf_obj[[nm]])
  }
  sf_obj
}

classify_values <- function(vals, value_col) {
  if (identical(value_col, "fastboendebefolkningmapinfo_count")) {
    cls <- rep(NA_character_, length(vals))
    cls[!is.na(vals) & vals == 0] <- "0"
    cls[!is.na(vals) & vals >= 1 & vals <= 5] <- "1-5"
    cls[!is.na(vals) & vals >= 6 & vals <= 20] <- "6-20"
    cls[!is.na(vals) & vals >= 21 & vals <= 50] <- "21-50"
    cls[!is.na(vals) & vals >= 51 & vals <= 100] <- "51-100"
    cls[!is.na(vals) & vals >= 101 & vals <= 250] <- "101-250"
    cls[!is.na(vals) & vals >= 251 & vals <= 1000] <- "251-1000"
    cls[!is.na(vals) & vals >= 1001 & vals <= 2000] <- "1001-2000"
    cls[!is.na(vals) & vals > 2000] <- ">2000"
    lev <- c("0", "1-5", "6-20", "21-50", "51-100", "101-250", "251-1000", "1001-2000", ">2000")
    pal <- c("#ffffff10", "#fee08b", "#fdae61", "#f46d43", "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5")
    return(list(class = factor(cls, levels = lev, ordered = TRUE), palette = pal))
  }

  if (grepl("_area_share$", value_col)) {
    cls <- rep(NA_character_, length(vals))
    cls[!is.na(vals) & vals == 0] <- "0"
    cls[!is.na(vals) & vals > 0 & vals <= 0.01] <- "0-1%"
    cls[!is.na(vals) & vals > 0.01 & vals <= 0.05] <- "1-5%"
    cls[!is.na(vals) & vals > 0.05 & vals <= 0.10] <- "5-10%"
    cls[!is.na(vals) & vals > 0.10 & vals <= 0.20] <- "10-20%"
    cls[!is.na(vals) & vals > 0.20] <- ">20%"
    lev <- c("0", "0-1%", "1-5%", "5-10%", "10-20%", ">20%")
    pal <- c("#ffffff10", "#e5f5e0", "#a1d99b", "#74c476", "#31a354", "#006d2c")
    return(list(class = factor(cls, levels = lev, ordered = TRUE), palette = pal))
  }

  if (grepl("_length_m($|_)", value_col) || grepl("_m$", value_col)) {
    return(classify_length_jenks(vals))
  }

  cls <- rep(NA_character_, length(vals))
  cls[!is.na(vals) & vals == 0] <- "0"
  cls[!is.na(vals) & vals > 0] <- ">0"
  lev <- c("0", ">0")
  pal <- c("#ffffff10", "#3182bd")
  list(class = factor(cls, levels = lev, ordered = TRUE), palette = pal)
}

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")
source("script/semi_manual_r9/lib/subcategory_splits.R")

home <- semi_manual_home()
repo <- repo_root(home)
load_aggregator(home)

split_rows <- read_subcategory_splits(home, parent_run_order = step_no)
split_rows <- split_rows[split_rows$render_under_parent, , drop = FALSE]
if (nrow(split_rows) == 0) {
  stop("No renderable subcategories configured for step ", step_no)
}
child_rows <- collapse_split_children(split_rows)

run_order_csv <- file.path(repo, "script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")
run_order <- read.csv(run_order_csv, stringsAsFactors = FALSE)
run_row <- run_order[run_order$run_order == step_no, , drop = FALSE]
if (nrow(run_row) != 1) {
  stop("Could not resolve run step in mapping: ", step_no)
}

layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]

orig_idx <- as.integer(run_row$original_layer_index)
if (orig_idx < 1 || orig_idx > nrow(layers)) {
  stop("Invalid original layer index in mapping: ", orig_idx)
}
layer_row <- layers[orig_idx, , drop = FALSE]

out_csv <- file.path(
  repo, "data", "interim", "geocontext_r9", "layers",
  sprintf("%02d_%s.csv", orig_idx, layer_row$layer_key)
)
if (!file.exists(out_csv)) {
  stop("Missing aggregated CSV for this step: ", out_csv)
}

schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r9")
hex_source <- Sys.getenv("HEX_SOURCE", "postgres")
hex_file <- Sys.getenv("HEX_FILE", "")
hex_layer <- Sys.getenv("HEX_LAYER", "")

hex <- load_hex_grid(
  hex_source = hex_source,
  schema = schema,
  hex_table = hex_table,
  home = home,
  hex_file = hex_file,
  hex_layer = hex_layer
)

out <- read.csv(out_csv, stringsAsFactors = FALSE)
hex_after <- dplyr::left_join(hex, out, by = "hex_id")

source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex_after))
source_layer <- map_source_to_subcategories(source_layer, split_rows)

bbox_hex <- sf::st_bbox(hex_after)
bbox_poly <- sf::st_as_sfc(bbox_hex)
inside_bbox <- lengths(sf::st_intersects(source_layer, bbox_poly)) > 0
source_layer <- source_layer[inside_bbox, , drop = FALSE]

review_dir <- file.path(repo, "docs", "geocontext", "review")
dir.create(review_dir, recursive = TRUE, showWarnings = FALSE)
out_html <- if (nzchar(output_path_override)) {
  output_path_override
} else {
  file.path(review_dir, sprintf("layer%02d_subcategories_review.html", step_no))
}

map_list <- list(
  mapview::mapview(
    hex,
    alpha.regions = 0,
    color = "grey70",
    lwd = 0.5,
    layer.name = "Hex grid (R9)"
  ),
  mapview::mapview(
    source_layer,
    zcol = "child_display_name",
    alpha.regions = 0.22,
    layer.name = paste0("Input grupperad: ", layer_row$display_name)
  )
)

for (i in seq_len(nrow(child_rows))) {
  child_row <- child_rows[i, , drop = FALSE]
  col_nm <- child_row$child_output_column
  if (!col_nm %in% names(hex_after)) {
    next
  }

  vals <- suppressWarnings(as.numeric(hex_after[[col_nm]]))
  class_info <- classify_values(vals, col_nm)
  hex_child <- hex_after
  hex_child$review_class <- class_info$class

  map_list[[length(map_list) + 1]] <- mapview::mapview(
    format_area_share_columns(hex_child),
    zcol = "review_class",
    col.regions = class_info$palette,
    alpha.regions = output_alpha,
    layer.name = paste0("Output: ", child_row$child_display_name)
  )
}

combined_map <- Reduce(`+`, map_list)
review_leaflet <- mapview:::mapview2leaflet(combined_map)
htmlwidgets::saveWidget(review_leaflet, file = out_html, selfcontained = FALSE)
message("Wrote HTML: ", out_html)
