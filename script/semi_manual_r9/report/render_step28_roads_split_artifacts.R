suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(ggplot2)
})

if (!requireNamespace("mapview", quietly = TRUE) || !requireNamespace("htmlwidgets", quietly = TRUE)) {
  stop("Packages 'mapview' and 'htmlwidgets' are required to render roads split artifacts.")
}

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")

args <- commandArgs(trailingOnly = TRUE)
step_no <- suppressWarnings(as.integer(if (length(args) >= 1) args[1] else "28"))
if (is.na(step_no) || step_no != 28) {
  stop("This script is dedicated to step 28 (roads).")
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

length_palette <- function(levels_vec, zero_level = "0") {
  nonzero_levels <- setdiff(levels_vec, zero_level)
  n_nonzero <- length(nonzero_levels)
  if (n_nonzero <= 0) return(c("#ffffff10"))
  ramp <- grDevices::colorRampPalette(c("#fee8c8", "#fdbb84", "#fc8d59", "#ef6548", "#990000"))
  c("#ffffff10", ramp(n_nonzero))
}

classify_length <- function(vals, n_target = 5L, zero_level = "0") {
  vals <- suppressWarnings(as.numeric(vals))
  cls <- rep(NA_character_, length(vals))
  cls[!is.na(vals) & vals == 0] <- zero_level

  nz_idx <- which(!is.na(vals) & vals > 0)
  if (length(nz_idx) == 0) {
    return(factor(cls, levels = zero_level, ordered = TRUE))
  }

  nz_vals <- vals[nz_idx]
  brks <- compute_breaks(nz_vals, n_target = n_target)
  if (length(brks) < 2 || (length(brks) == 2 && brks[1] == brks[2])) {
    pos_label <- ">0 m"
    cls[nz_idx] <- pos_label
    return(factor(cls, levels = c(zero_level, pos_label), ordered = TRUE))
  }

  labels <- vapply(seq_len(length(brks) - 1), function(i) {
    paste0(format_meter(brks[i]), "-", format_meter(brks[i + 1]), " m")
  }, character(1))

  nz_class <- cut(
    nz_vals,
    breaks = brks,
    include.lowest = TRUE,
    right = TRUE,
    labels = labels
  )
  cls[nz_idx] <- as.character(nz_class)

  factor(cls, levels = c(zero_level, labels), ordered = TRUE)
}

plot_hex_class <- function(hex_after, class_col, title, subtitle) {
  zero_level <- "0"
  class_vec <- hex_after[[class_col]]
  has_zero <- zero_level %in% levels(class_vec)

  if (has_zero) {
    hex_zero <- hex_after[!is.na(class_vec) & as.character(class_vec) == zero_level, , drop = FALSE]
    hex_nonzero <- hex_after[!is.na(class_vec) & as.character(class_vec) != zero_level, , drop = FALSE]
  } else {
    hex_zero <- hex_after[FALSE, , drop = FALSE]
    hex_nonzero <- hex_after[!is.na(class_vec), , drop = FALSE]
  }

  legend_levels <- setdiff(levels(class_vec), zero_level)
  pal_all <- length_palette(levels(class_vec), zero_level = zero_level)
  legend_palette <- pal_all[match(legend_levels, levels(class_vec))]

  bb <- sf::st_bbox(hex_after)

  p <- ggplot() +
    geom_sf(data = hex_zero, fill = "white", color = "white", alpha = 0.06, linewidth = 0.08)

  if (nrow(hex_nonzero) > 0 && length(legend_levels) > 0) {
    hex_nonzero$class_nonzero <- factor(
      as.character(hex_nonzero[[class_col]]),
      levels = legend_levels,
      ordered = TRUE
    )
    p <- p +
      geom_sf(data = hex_nonzero, aes(fill = class_nonzero), color = "#7a7a7a", alpha = 0.88, linewidth = 0.12) +
      scale_fill_manual(
        values = stats::setNames(legend_palette, legend_levels),
        drop = FALSE,
        na.translate = FALSE
      ) +
      labs(fill = "Vaglangd per hex")
  }

  p +
    labs(title = title, subtitle = subtitle) +
    coord_sf(
      xlim = c(bb["xmin"], bb["xmax"]),
      ylim = c(bb["ymin"], bb["ymax"]),
      expand = FALSE,
      datum = NA
    ) +
    theme_minimal(base_size = 11) +
    theme(
      panel.background = element_rect(fill = "#b7c6cf", color = NA),
      plot.background = element_rect(fill = "#b7c6cf", color = NA),
      panel.grid = element_blank(),
      axis.title = element_blank(),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      legend.position = c(0.85, 0.84),
      legend.background = element_rect(fill = scales::alpha("white", 0.88), color = NA),
      plot.title = element_text(face = "bold"),
      plot.subtitle = element_text(size = 10)
    )
}

normalize_txt <- function(x) {
  tolower(trimws(iconv(as.character(x), to = "ASCII//TRANSLIT")))
}

classify_road_class <- function(x) {
  y <- normalize_txt(x)
  out <- rep("other", length(y))
  out[grepl("stor|motor|major|primary", y)] <- "large"
  out[grepl("mellem|mellan|medium|secondary", y)] <- "medium"
  out[grepl("lille|small|minor|local|residential", y)] <- "small"
  out
}

home <- semi_manual_home()
repo <- repo_root(home)
load_aggregator(home)

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
layer_row <- layers[orig_idx, , drop = FALSE]
prefix <- layer_row$layer_key

out_csv <- file.path(
  repo, "data", "interim", "geocontext_r9", "layers",
  sprintf("%02d_%s.csv", orig_idx, layer_row$layer_key)
)
if (!file.exists(out_csv)) {
  stop("Missing aggregated CSV for step 28: ", out_csv)
}

out <- read.csv(out_csv, stringsAsFactors = FALSE)
col_medium <- paste0(prefix, "_length_m_medium")
col_large <- paste0(prefix, "_length_m_large")
if (!all(c(col_medium, col_large) %in% names(out))) {
  stop("Expected medium/large columns are missing in output CSV.")
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

hex_after <- dplyr::left_join(hex, out, by = "hex_id")
hex_after$medium_class <- classify_length(suppressWarnings(as.numeric(hex_after[[col_medium]])))
hex_after$large_class <- classify_length(suppressWarnings(as.numeric(hex_after[[col_large]])))

source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex_after))
source_layer$road_class <- classify_road_class(source_layer$vejkategor)

bbox_hex <- sf::st_bbox(hex_after)
bbox_poly <- sf::st_as_sfc(bbox_hex)
inside_bbox <- lengths(sf::st_intersects(source_layer, bbox_poly)) > 0
source_layer <- source_layer[inside_bbox, , drop = FALSE]
in_medium <- source_layer[source_layer$road_class == "medium", , drop = FALSE]
in_large <- source_layer[source_layer$road_class == "large", , drop = FALSE]

fig_dir <- file.path(repo, "docs", "geocontext", "figures")
review_dir <- file.path(repo, "docs", "geocontext", "review")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(review_dir, recursive = TRUE, showWarnings = FALSE)

png_medium <- file.path(fig_dir, "layer28_roads_medium_overview.png")
png_large <- file.path(fig_dir, "layer28_roads_large_overview.png")
html_path <- file.path(review_dir, "layer28_roads_medium_large_review.html")

p_medium <- plot_hex_class(
  hex_after,
  class_col = "medium_class",
  title = "Steg 28: Roads Simplified - Mellan vagar",
  subtitle = paste0("Aggregerad kolumn: ", col_medium)
)
p_large <- plot_hex_class(
  hex_after,
  class_col = "large_class",
  title = "Steg 28: Roads Simplified - Stora vagar",
  subtitle = paste0("Aggregerad kolumn: ", col_large)
)

ggsave(filename = png_medium, plot = p_medium, width = 10.5, height = 9.2, dpi = 170, bg = "#b7c6cf")
ggsave(filename = png_large, plot = p_large, width = 10.5, height = 9.2, dpi = 170, bg = "#b7c6cf")

output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) output_alpha <- 0.35

medium_palette <- length_palette(levels(hex_after$medium_class))
large_palette <- length_palette(levels(hex_after$large_class))

out_medium_map <- mapview::mapview(
  hex_after,
  zcol = "medium_class",
  col.regions = medium_palette,
  alpha.regions = output_alpha,
  layer.name = paste0("Output medium: ", col_medium)
)
out_large_map <- mapview::mapview(
  hex_after,
  zcol = "large_class",
  col.regions = large_palette,
  alpha.regions = output_alpha,
  layer.name = paste0("Output large: ", col_large)
)
in_medium_map <- mapview::mapview(
  in_medium,
  color = "#ef8a62",
  alpha.regions = 0.70,
  layer.name = "Input medium roads"
)
in_large_map <- mapview::mapview(
  in_large,
  color = "#b2182b",
  alpha.regions = 0.90,
  layer.name = "Input large roads"
)

review_leaflet <- mapview:::mapview2leaflet(out_medium_map + out_large_map + in_medium_map + in_large_map)
htmlwidgets::saveWidget(review_leaflet, file = html_path, selfcontained = FALSE)

message("Wrote PNG: ", png_medium)
message("Wrote PNG: ", png_large)
message("Wrote HTML: ", html_path)
