suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
})

if (!requireNamespace("mapview", quietly = TRUE) || !requireNamespace("htmlwidgets", quietly = TRUE)) {
  stop("Packages 'mapview' and 'htmlwidgets' are required to render review HTML.")
}

args <- commandArgs(trailingOnly = TRUE)
step_no <- suppressWarnings(as.integer(if (length(args) >= 1) args[1] else Sys.getenv("STEP_RUN_ORDER", "")))
run_order_guard_csv <- file.path("script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
run_order_guard <- if (file.exists(run_order_guard_csv)) read.csv(run_order_guard_csv, stringsAsFactors = FALSE) else data.frame(run_order = 44)
max_step <- suppressWarnings(max(as.integer(run_order_guard$run_order), na.rm = TRUE))
if (!is.finite(max_step)) max_step <- 44
if (is.na(step_no) || step_no < 1 || step_no > max_step) {
  stop(sprintf("Provide run step number 1..%d as argument, e.g. Rscript .../render_step_review_html.R 01", max_step))
}
output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
  output_alpha <- 0.35
}

choose_value_col <- function(out_df) {
  value_cols <- setdiff(names(out_df), "hex_id")
  if (length(value_cols) == 0) {
    return(NA_character_)
  }

  preferred_patterns <- c(
    "_length_m_total$",
    "_area_share$",
    "_count$",
    "_sum$",
    "_length_m($|_)",
    "_m$"
  )
  for (pat in preferred_patterns) {
    hit <- value_cols[grepl(pat, value_cols)]
    if (length(hit) > 0) {
      return(hit[1])
    }
  }

  numeric_cols <- value_cols[vapply(out_df[value_cols], is.numeric, logical(1))]
  if (length(numeric_cols) > 0) {
    nonzero_n <- vapply(numeric_cols, function(nm) {
      v <- suppressWarnings(as.numeric(out_df[[nm]]))
      sum(!is.na(v) & v > 0)
    }, numeric(1))
    return(numeric_cols[which.max(nonzero_n)])
  }

  value_cols[1]
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

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")

home <- semi_manual_home()
repo <- repo_root(home)
load_aggregator(home)

run_order_csv <- file.path(repo, "script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")
if (!file.exists(run_order_csv)) {
  stop("Missing run-order mapping: ", run_order_csv)
}

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

bbox_hex <- sf::st_bbox(hex_after)
bbox_poly <- sf::st_as_sfc(bbox_hex)
inside_bbox <- lengths(sf::st_intersects(source_layer, bbox_poly)) > 0
source_layer <- source_layer[inside_bbox, , drop = FALSE]

value_col <- choose_value_col(out)
if (is.na(value_col) || !nzchar(value_col)) {
  output_map <- mapview::mapview(
    hex_after,
    alpha.regions = 0.10,
    color = "grey65",
    layer.name = "Output: no value column"
  )
} else {
  if (identical(value_col, "fastboendebefolkningmapinfo_count")) {
    vals <- suppressWarnings(as.numeric(hex_after[[value_col]]))
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
    hex_after$review_class <- factor(
      cls,
      levels = c("0", "1-5", "6-20", "21-50", "51-100", "101-250", "251-1000", "1001-2000", ">2000"),
      ordered = TRUE
    )
    output_map <- mapview::mapview(
      hex_after,
      zcol = "review_class",
      col.regions = c("#ffffff10", "#fee08b", "#fdae61", "#f46d43", "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5"),
      alpha.regions = output_alpha,
      layer.name = paste0("Output: ", value_col, " (classed)")
    )
  } else if (grepl("_area_share$", value_col)) {
    vals <- suppressWarnings(as.numeric(hex_after[[value_col]]))
    cls <- rep(NA_character_, length(vals))
    cls[!is.na(vals) & vals == 0] <- "0"
    cls[!is.na(vals) & vals > 0 & vals <= 0.01] <- "0-1%"
    cls[!is.na(vals) & vals > 0.01 & vals <= 0.05] <- "1-5%"
    cls[!is.na(vals) & vals > 0.05 & vals <= 0.10] <- "5-10%"
    cls[!is.na(vals) & vals > 0.10 & vals <= 0.20] <- "10-20%"
    cls[!is.na(vals) & vals > 0.20] <- ">20%"
    hex_after$review_class <- factor(
      cls,
      levels = c("0", "0-1%", "1-5%", "5-10%", "10-20%", ">20%"),
      ordered = TRUE
    )
    output_map <- mapview::mapview(
      hex_after,
      zcol = "review_class",
      col.regions = c("#ffffff10", "#e5f5e0", "#a1d99b", "#74c476", "#31a354", "#006d2c"),
      alpha.regions = output_alpha,
      layer.name = paste0("Output: ", value_col, " (classed)")
    )
  } else if (grepl("_length_m($|_)", value_col)) {
    vals <- suppressWarnings(as.numeric(hex_after[[value_col]]))
    out <- classify_length_jenks(vals)
    hex_after$review_class <- out$class
    output_map <- mapview::mapview(
      hex_after,
      zcol = "review_class",
      col.regions = out$palette,
      alpha.regions = output_alpha,
      layer.name = paste0("Output: ", value_col, " (classed)")
    )
  } else if (grepl("_m$", value_col)) {
    vals <- suppressWarnings(as.numeric(hex_after[[value_col]]))
    out <- classify_length_jenks(vals)
    hex_after$review_class <- out$class
    output_map <- mapview::mapview(
      hex_after,
      zcol = "review_class",
      col.regions = out$palette,
      alpha.regions = max(output_alpha, 0.55),
      layer.name = paste0("Output: ", value_col, " (classed hojdintervall)")
    )
  } else {
    output_map <- mapview::mapview(
      hex_after,
      zcol = value_col,
      alpha.regions = output_alpha,
      layer.name = paste0("Output: ", value_col)
    )
  }
}

input_map <- mapview::mapview(
  source_layer,
  alpha.regions = 0.25,
  layer.name = paste0("Input: ", layer_row$display_name)
)

review_map <- output_map + input_map
review_leaflet <- mapview:::mapview2leaflet(review_map)

out_html <- file.path(repo, "docs", "geocontext", "review", sprintf("layer%02d_review.html", step_no))
dir.create(dirname(out_html), recursive = TRUE, showWarnings = FALSE)
htmlwidgets::saveWidget(review_leaflet, file = out_html, selfcontained = FALSE)
message("Wrote HTML: ", out_html)
