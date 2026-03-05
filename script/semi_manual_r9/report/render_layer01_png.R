suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(ggplot2)
})

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")

home <- semi_manual_home()
repo <- repo_root(home)
load_aggregator(home)

layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")
layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]
layer_row <- layers[1, , drop = FALSE]

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

out_csv <- file.path(repo, "data", "interim", "geocontext_r9", "layers", "01_fastboendebefolkningmapinfo.csv")
if (!file.exists(out_csv)) {
  stop("Missing aggregated layer output: ", out_csv)
}
agg <- read.csv(out_csv, stringsAsFactors = FALSE)
hex_after <- left_join(hex, agg, by = "hex_id")

source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
source_layer <- prepare_source_layer(source_layer, st_crs(hex_after))

# Use hex grid extent as authoritative map window and drop source outliers.
bbox_hex <- st_bbox(hex_after)
bbox_poly <- st_as_sfc(bbox_hex)
inside_bbox <- lengths(st_intersects(source_layer, bbox_poly)) > 0
source_layer <- source_layer[inside_bbox, , drop = FALSE]

show_source_points <- tolower(Sys.getenv("LAYER01_SHOW_SOURCE_POINTS", "false")) %in% c("1", "true", "yes")

classify_layer01_population <- function(x) {
  vals <- suppressWarnings(as.numeric(x))
  out_class <- rep(NA_character_, length(vals))
  out_class[!is.na(vals) & vals == 0] <- "0"
  out_class[!is.na(vals) & vals >= 1 & vals <= 5] <- "1-5"
  out_class[!is.na(vals) & vals >= 6 & vals <= 20] <- "6-20"
  out_class[!is.na(vals) & vals >= 21 & vals <= 50] <- "21-50"
  out_class[!is.na(vals) & vals >= 51 & vals <= 100] <- "51-100"
  out_class[!is.na(vals) & vals >= 101 & vals <= 250] <- "101-250"
  out_class[!is.na(vals) & vals >= 251 & vals <= 1000] <- "251-1000"
  out_class[!is.na(vals) & vals >= 1001 & vals <= 2000] <- "1001-2000"
  out_class[!is.na(vals) & vals > 2000] <- ">2000"
  factor(
    out_class,
    levels = c("0", "1-5", "6-20", "21-50", "51-100", "101-250", "251-1000", "1001-2000", ">2000"),
    ordered = TRUE
  )
}

hex_after$pop_class <- classify_layer01_population(hex_after$fastboendebefolkningmapinfo_count)
hex_zero <- hex_after[!is.na(hex_after$pop_class) & hex_after$pop_class == "0", , drop = FALSE]
hex_nonzero <- hex_after[!is.na(hex_after$pop_class) & hex_after$pop_class != "0", , drop = FALSE]

out_png <- file.path(repo, "docs", "geocontext", "figures", "layer23_overview.png")
out_png_legacy <- file.path(repo, "docs", "geocontext", "layer01_fastboende_in_agg_out.png")
out_html <- file.path(repo, "docs", "geocontext", "review", "layer23_review.html")
dir.create(dirname(out_png), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(out_html), recursive = TRUE, showWarnings = FALSE)

fill_values <- c(
  "1-5" = "#fee08b",
  "6-20" = "#fdae61",
  "21-50" = "#f46d43",
  "51-100" = "#d53e4f",
  "101-250" = "#9e0142",
  "251-1000" = "#5e4fa2",
  "1001-2000" = "#3288bd",
  ">2000" = "#66c2a5"
)

p <- ggplot() +
  geom_sf(data = hex_zero, fill = "white", color = "white", alpha = 0.06, linewidth = 0.08) +
  geom_sf(data = hex_nonzero, aes(fill = pop_class), color = "#7a7a7a", alpha = 0.88, linewidth = 0.12) +
  scale_fill_manual(values = fill_values, drop = FALSE, na.translate = FALSE) +
  labs(
    title = "Steg 23: Fastboende befolkning",
    subtitle = "Lager in (punkter) + aggregat till R9-hexagoner (klassad befolkningsmangd)",
    fill = "Befolkningsklass"
  ) +
  coord_sf(
    xlim = c(bbox_hex["xmin"], bbox_hex["xmax"]),
    ylim = c(bbox_hex["ymin"], bbox_hex["ymax"]),
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
    legend.position = c(0.86, 0.84),
    legend.background = element_rect(fill = scales::alpha("white", 0.88), color = NA),
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(size = 10)
  )

if (show_source_points) {
  p <- p + geom_sf(data = source_layer, color = "#3c8d40", alpha = 0.07, size = 0.06)
}

ggsave(
  filename = out_png,
  plot = p,
  width = 10.5,
  height = 9.2,
  dpi = 170,
  bg = "#b7c6cf"
)

file.copy(out_png, out_png_legacy, overwrite = TRUE)
message("Wrote PNG: ", out_png)
message("Wrote PNG (legacy): ", out_png_legacy)

if (requireNamespace("mapview", quietly = TRUE) && requireNamespace("htmlwidgets", quietly = TRUE)) {
  output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
  if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
    output_alpha <- 0.35
  }

  hex_after$pop_class <- factor(
    as.character(hex_after$pop_class),
    levels = c("0", "1-5", "6-20", "21-50", "51-100", "101-250", "251-1000", "1001-2000", ">2000"),
    ordered = TRUE
  )
  map_colors <- c("#ffffff10", unname(fill_values))
  output_map <- mapview::mapview(
    hex_after,
    zcol = "pop_class",
    col.regions = map_colors,
    alpha.regions = output_alpha,
    layer.name = "Output: fastboendebefolkningmapinfo_count (classed)"
  )
  input_map <- mapview::mapview(
    source_layer,
    layer.name = paste0("Input: ", layer_row$display_name)
  )
  review_map <- output_map + input_map
  review_leaflet <- mapview:::mapview2leaflet(review_map)
  htmlwidgets::saveWidget(review_leaflet, file = out_html, selfcontained = FALSE)
  message("Wrote HTML: ", out_html)
} else {
  warning("Skipping HTML output: 'mapview' or 'htmlwidgets' not installed.")
}
