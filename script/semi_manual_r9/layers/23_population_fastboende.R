# Step 23 (Original layer 01): FastboendeBefolkningMapInfo
# This script is explicit on purpose, so population-layer behavior is visible here.
#
# Typical inspect run (pre + post map, no file write):
#   Sys.setenv(SHOW_MAPVIEW = "true", SHOW_LAYER_SUMMARY = "true", RUN_AGGREGATION = "true", WRITE_OUTPUT = "false")
#
# Typical production run (pre + post map + write):
#   Sys.setenv(SHOW_MAPVIEW = "true", SHOW_LAYER_SUMMARY = "true", RUN_AGGREGATION = "true", WRITE_OUTPUT = "true")

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- NULL

if (length(file_arg) > 0) {
  script_file <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
  script_dir <- dirname(script_file)
}

if (is.null(script_dir)) {
  if (file.exists("script/semi_manual_r9/layers/23_population_fastboende.R")) {
    script_dir <- normalizePath("script/semi_manual_r9/layers", winslash = "/", mustWork = TRUE)
  } else if (file.exists("layers/23_population_fastboende.R")) {
    script_dir <- normalizePath("layers", winslash = "/", mustWork = TRUE)
  } else if (nzchar(Sys.getenv("SEMI_MANUAL_R9_HOME")) &&
             dir.exists(file.path(Sys.getenv("SEMI_MANUAL_R9_HOME"), "layers"))) {
    script_dir <- normalizePath(file.path(Sys.getenv("SEMI_MANUAL_R9_HOME"), "layers"), winslash = "/", mustWork = TRUE)
  } else {
    stop(
      "Could not infer script directory in interactive mode.\n",
      "Run from repo root, or set:\n",
      "Sys.setenv(SEMI_MANUAL_R9_HOME='C:/gislab/landskapsanalys/script/semi_manual_r9')"
    )
  }
}

Sys.setenv(
  SEMI_MANUAL_R9_HOME = normalizePath(file.path(script_dir, ".."), winslash = "/", mustWork = TRUE)
)
source(file.path(script_dir, "..", "lib", "manual_layer_aggregation.R"))

layer_index <- 1L
show_mapview <- is_truthy(Sys.getenv("SHOW_MAPVIEW", "true"))
force_mapview <- is_truthy(Sys.getenv("FORCE_MAPVIEW", "false"))
do_mapview <- show_mapview && (interactive() || force_mapview)
show_layer_summary <- is_truthy(Sys.getenv("SHOW_LAYER_SUMMARY", if (interactive()) "true" else "false"))
run_aggregation <- is_truthy(Sys.getenv("RUN_AGGREGATION", "true"))
write_output <- is_truthy(Sys.getenv("WRITE_OUTPUT", "true"))
output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
  output_alpha <- 0.35
}

home <- semi_manual_home()
repo <- repo_root(home)

layer_csv <- Sys.getenv(
  "GEOCONTEXT_LAYER_CSV",
  normalizePath(file.path(home, "config", "bornholm_r9_geocontext_layers.csv"), winslash = "/", mustWork = TRUE)
)

schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r9")
hex_source <- Sys.getenv("HEX_SOURCE", "postgres")
hex_file <- Sys.getenv("HEX_FILE", "")
hex_layer <- Sys.getenv("HEX_LAYER", "")

out_dir <- Sys.getenv(
  "GEOCONTEXT_LAYER_OUTPUT_DIR",
  normalizePath(file.path(repo, "data", "interim", "geocontext_r9", "layers"), winslash = "/", mustWork = FALSE)
)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]

if (layer_index < 1 || layer_index > nrow(layers)) {
  stop("layer_index out of range. Valid: 1..", nrow(layers))
}
layer_row <- layers[layer_index, , drop = FALSE]

message(sprintf("Layer %d/%d: %s", layer_index, nrow(layers), layer_row$display_name))
message("Hex source: ", hex_source, " | schema.table: ", schema, ".", hex_table)

load_aggregator(home)
hex <- load_hex_grid(
  hex_source = hex_source,
  schema = schema,
  hex_table = hex_table,
  home = home,
  hex_file = hex_file,
  hex_layer = hex_layer
)

source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex))

if (show_layer_summary) {
  print_layer_diagnostics(source_layer)
}

if (do_mapview) {
  show_pre_aggregation_map(hex, source_layer, layer_row$display_name)
}

if (!run_aggregation) {
  message("RUN_AGGREGATION=false -> stopped after pre-aggregation checks.")
} else {
  out <- aggregate_layer_to_hex(hex, layer_row)

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

  if (do_mapview) {
    if (!requireNamespace("mapview", quietly = TRUE)) {
      warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    } else {
      message("Opening post-aggregation mapview with layer-01 bins...")
      hex_after <- dplyr::left_join(hex, out, by = "hex_id")
      hex_after$pop_class <- classify_layer01_population(hex_after$fastboendebefolkningmapinfo_count)

      # Draw class 0 separately to make empty-population hexes nearly invisible.
      hex_zero <- hex_after[!is.na(hex_after$pop_class) & hex_after$pop_class == "0", , drop = FALSE]
      hex_nonzero <- hex_after[!is.na(hex_after$pop_class) & hex_after$pop_class != "0", , drop = FALSE]

      nonzero_levels <- c("1-5", "6-20", "21-50", "51-100", "101-250", "251-1000", "1001-2000", ">2000")
      nonzero_colors <- c("#fee08b", "#fdae61", "#f46d43", "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5")
      if (nrow(hex_nonzero) > 0) {
        hex_nonzero$pop_class <- factor(as.character(hex_nonzero$pop_class), levels = nonzero_levels, ordered = TRUE)
      }

      zero_map <- mapview::mapview(
        hex_zero,
        color = "white",
        alpha.regions = 0.03,
        layer.name = "Population class: 0 (near invisible)"
      )

      nonzero_map <- mapview::mapview(
        hex_nonzero,
        zcol = "pop_class",
        col.regions = nonzero_colors,
        alpha.regions = output_alpha,
        layer.name = "Aggregated: fastboendebefolkningmapinfo_count (classed)"
      )

      after_map <- zero_map + nonzero_map + mapview::mapview(
        source_layer,
        layer.name = paste0("Source: ", layer_row$display_name)
      )
      print(after_map)
    }
  }

  if (!write_output) {
    message("WRITE_OUTPUT=false -> aggregation completed, map shown, no CSV/log write.")
  } else {
    file_base <- sprintf("%02d_%s", layer_index, layer_row$layer_key)
    out_csv <- file.path(out_dir, paste0(file_base, ".csv"))
    write.csv(out, out_csv, row.names = FALSE, na = "")

    log_path <- file.path(dirname(out_dir), "run_log.csv")
    log_row <- data.frame(
      run_ts = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
      layer_index = layer_index,
      layer_key = layer_row$layer_key,
      display_name = layer_row$display_name,
      output_csv = out_csv,
      n_rows = nrow(out),
      n_cols = ncol(out),
      stringsAsFactors = FALSE
    )

    if (file.exists(log_path)) {
      old <- read.csv(log_path, stringsAsFactors = FALSE)
      old <- old[old$layer_index != layer_index, , drop = FALSE]
      log_df <- rbind(old, log_row)
    } else {
      log_df <- log_row
    }
    write.csv(log_df, log_path, row.names = FALSE, na = "")

    message("Wrote: ", out_csv)
  }
}
