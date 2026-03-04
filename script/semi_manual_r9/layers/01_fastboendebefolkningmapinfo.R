# Layer 01: FastboendeBefolkningMapInfo
#
# This script is intentionally verbose and step-by-step so it is easy to
# inspect and run semi-manually during the fresh R9 aggregation phase.
# It adds two optional mapviews:
# 1) Source layer + hex grid before aggregation
# 2) Aggregated result on hex grid after aggregation

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- NULL

# 1) Normal case: script executed via Rscript and includes --file
if (length(file_arg) > 0) {
  script_file <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
  script_dir <- dirname(script_file)
}

# 2) Interactive fallback: infer location from current working directory
if (is.null(script_dir)) {
  if (file.exists("script/semi_manual_r9/layers/01_fastboendebefolkningmapinfo.R")) {
    script_dir <- normalizePath("script/semi_manual_r9/layers", winslash = "/", mustWork = TRUE)
  } else if (file.exists("layers/01_fastboendebefolkningmapinfo.R")) {
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

# Let shared helper code know where this semi-manual pipeline lives.
Sys.setenv(
  SEMI_MANUAL_R9_HOME = normalizePath(file.path(script_dir, ".."), winslash = "/", mustWork = TRUE)
)
source(file.path(script_dir, "..", "lib", "manual_layer_aggregation.R"))

# ---------------------------
# Runtime configuration
# ---------------------------
layer_index <- 1L
show_mapview <- tolower(Sys.getenv("SHOW_MAPVIEW", "true")) %in% c("1", "true", "yes")
force_mapview <- tolower(Sys.getenv("FORCE_MAPVIEW", "false")) %in% c("1", "true", "yes")
do_mapview <- show_mapview && (interactive() || force_mapview)

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

# ---------------------------
# Resolve selected layer row
# ---------------------------
layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]

if (layer_index < 1 || layer_index > nrow(layers)) {
  stop("layer_index out of range. Valid: 1..", nrow(layers))
}
layer_row <- layers[layer_index, , drop = FALSE]

message(sprintf("Layer %d/%d: %s", layer_index, nrow(layers), layer_row$display_name))
message("Hex source: ", hex_source, " | schema.table: ", schema, ".", hex_table)

# ---------------------------
# Load aggregation dependencies and data
# ---------------------------
# `load_aggregator()` provides:
# - read_layer_sf()
# - aggregate_layer_to_hex()
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
source_layer <- sf::st_zm(source_layer, drop = TRUE, what = "ZM")
source_layer <- sf::st_make_valid(source_layer)
source_layer <- sf::st_transform(source_layer, sf::st_crs(hex))

# ---------------------------
# Mapview BEFORE aggregation
# ---------------------------
if (do_mapview) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
  } else {
    message("Opening pre-aggregation mapview...")
    pre_map <- mapview::mapview(
      hex,
      alpha.regions = 0,
      color = "grey70",
      lwd = 0.5,
      layer.name = "Hex grid (R9)"
    ) + mapview::mapview(
      source_layer,
      layer.name = paste0("Source: ", layer_row$display_name)
    )
    print(pre_map)
  }
}

# ---------------------------
# Aggregate to hex
# ---------------------------
out <- aggregate_layer_to_hex(hex, layer_row)
value_cols <- setdiff(names(out), "hex_id")
value_col <- if (length(value_cols) > 0) value_cols[[1]] else NA_character_

# ---------------------------
# Mapview AFTER aggregation
# ---------------------------
if (do_mapview) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
  } else {
    message("Opening post-aggregation mapview...")
    hex_after <- dplyr::left_join(hex, out, by = "hex_id")
    source_overlay <- mapview::mapview(
      source_layer,
      layer.name = paste0("Source: ", layer_row$display_name)
    )
    if (!is.na(value_col) && nzchar(value_col)) {
      after_map <- mapview::mapview(
        hex_after,
        zcol = value_col,
        layer.name = paste0("Aggregated: ", value_col)
      ) + source_overlay
    } else {
      after_map <- mapview::mapview(
        hex_after,
        layer.name = "Aggregated hex output"
      ) + source_overlay
    }
    print(after_map)
  }
}

# ---------------------------
# Save per-layer output
# ---------------------------
file_base <- sprintf("%02d_%s", layer_index, layer_row$layer_key)
out_csv <- file.path(out_dir, paste0(file_base, ".csv"))
write.csv(out, out_csv, row.names = FALSE, na = "")

# Update run log (one row per layer, replaced on rerun)
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
