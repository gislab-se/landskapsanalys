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
layer_row <- layers[2, , drop = FALSE]

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

out_csv <- file.path(
  repo,
  "data", "interim", "geocontext_r9", "layers",
  "02_industry_business_gd_v_erhverv_business_industry_bol_33.csv"
)
if (!file.exists(out_csv)) {
  stop("Missing aggregated layer output: ", out_csv)
}

agg <- read.csv(out_csv, stringsAsFactors = FALSE)
value_col <- "industry_business_gd_v_erhverv_business_industry_bol_33_area_share"
if (!value_col %in% names(agg)) {
  stop("Expected value column missing: ", value_col)
}

hex_after <- left_join(hex, agg, by = "hex_id")

source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
source_layer <- prepare_source_layer(source_layer, st_crs(hex_after))
bbox_hex <- st_bbox(hex_after)
bbox_poly <- st_as_sfc(bbox_hex)
inside_bbox <- lengths(st_intersects(source_layer, bbox_poly)) > 0
source_layer <- source_layer[inside_bbox, , drop = FALSE]

classify_area_share <- function(x) {
  vals <- suppressWarnings(as.numeric(x))
  out <- rep(NA_character_, length(vals))
  out[!is.na(vals) & vals == 0] <- "0"
  out[!is.na(vals) & vals > 0 & vals <= 0.01] <- "0-1%"
  out[!is.na(vals) & vals > 0.01 & vals <= 0.05] <- "1-5%"
  out[!is.na(vals) & vals > 0.05 & vals <= 0.10] <- "5-10%"
  out[!is.na(vals) & vals > 0.10 & vals <= 0.20] <- "10-20%"
  out[!is.na(vals) & vals > 0.20] <- ">20%"
  factor(out, levels = c("0", "0-1%", "1-5%", "5-10%", "10-20%", ">20%"), ordered = TRUE)
}

hex_after$class <- classify_area_share(hex_after[[value_col]])
hex_zero <- hex_after[!is.na(hex_after$class) & hex_after$class == "0", , drop = FALSE]
hex_nonzero <- hex_after[!is.na(hex_after$class) & hex_after$class != "0", , drop = FALSE]
hex_nonzero$class <- factor(as.character(hex_nonzero$class), levels = c("0-1%", "1-5%", "5-10%", "10-20%", ">20%"), ordered = TRUE)

fill_values <- c(
  "0-1%" = "#e5f5e0",
  "1-5%" = "#a1d99b",
  "5-10%" = "#74c476",
  "10-20%" = "#31a354",
  ">20%" = "#006d2c"
)

out_png <- file.path(repo, "docs", "geocontext", "figures", "layer29_overview.png")
out_html <- file.path(repo, "docs", "geocontext", "review", "layer29_review.html")
dir.create(dirname(out_png), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(out_html), recursive = TRUE, showWarnings = FALSE)

p <- ggplot() +
  geom_sf(data = hex_zero, fill = "white", color = "white", alpha = 0.06, linewidth = 0.08) +
  geom_sf(data = hex_nonzero, aes(fill = class), color = "#7a7a7a", alpha = 0.90, linewidth = 0.12) +
  scale_fill_manual(values = fill_values, drop = FALSE, na.translate = FALSE) +
  labs(
    title = "Steg 29: Industry/Business",
    subtitle = "Aggregerad andel industrimark per R9-hexagon",
    fill = "Andelsklass"
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

ggsave(
  filename = out_png,
  plot = p,
  width = 10.5,
  height = 9.2,
  dpi = 170,
  bg = "#b7c6cf"
)

message("Wrote PNG: ", out_png)

if (requireNamespace("mapview", quietly = TRUE) && requireNamespace("htmlwidgets", quietly = TRUE)) {
  output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
  if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
    output_alpha <- 0.35
  }

  hex_after$class <- factor(
    as.character(hex_after$class),
    levels = c("0", "0-1%", "1-5%", "5-10%", "10-20%", ">20%"),
    ordered = TRUE
  )
  map_colors <- c("#ffffff10", unname(fill_values))
  output_map <- mapview::mapview(
    hex_after,
    zcol = "class",
    col.regions = map_colors,
    alpha.regions = output_alpha,
    layer.name = paste0("Output: ", value_col)
  )
  input_map <- mapview::mapview(
    source_layer,
    alpha.regions = 0.20,
    color = "#1f78b4",
    layer.name = paste0("Input: ", layer_row$display_name)
  )
  review_map <- output_map + input_map
  review_leaflet <- mapview:::mapview2leaflet(review_map)
  htmlwidgets::saveWidget(review_leaflet, file = out_html, selfcontained = FALSE)
  message("Wrote HTML: ", out_html)
} else {
  warning("Skipping HTML output: 'mapview' or 'htmlwidgets' not installed.")
}
