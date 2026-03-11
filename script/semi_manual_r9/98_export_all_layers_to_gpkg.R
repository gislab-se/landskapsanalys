suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
})

sf::sf_use_s2(FALSE)

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")

sanitize_layer_name <- function(step_no, layer_key, used_names) {
  base <- paste0("r9_", sprintf("%02d", step_no), "_", slugify(layer_key))
  if (nchar(base) > 60) {
    base <- substr(base, 1, 60)
  }
  name <- base
  suffix <- 1
  while (name %in% used_names) {
    extra <- paste0("_", suffix)
    keep_n <- max(1, 60 - nchar(extra))
    name <- paste0(substr(base, 1, keep_n), extra)
    suffix <- suffix + 1
  }
  name
}

home <- semi_manual_home()
repo <- repo_root(home)

run_order_csv <- file.path(repo, "script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")
layers_out_dir <- file.path(repo, "data", "interim", "geocontext_r9", "layers")
merged_csv <- file.path(repo, "data", "interim", "geocontext_r9", "bornholm_r9_geocontext_raw_manual.csv")

out_gpkg <- Sys.getenv(
  "R9_GPKG_OUT",
  file.path(repo, "data", "interim", "geocontext_r9", "bornholm_r9_all_44_layers.gpkg")
)
out_gpkg <- normalizePath(out_gpkg, winslash = "/", mustWork = FALSE)
dir.create(dirname(out_gpkg), recursive = TRUE, showWarnings = FALSE)

if (!file.exists(run_order_csv)) stop("Missing run order csv: ", run_order_csv)
if (!file.exists(layer_csv)) stop("Missing layer catalog: ", layer_csv)
if (!dir.exists(layers_out_dir)) stop("Missing layer output folder: ", layers_out_dir)
if (!file.exists(merged_csv)) stop("Missing merged csv: ", merged_csv)

run_order <- read.csv(run_order_csv, stringsAsFactors = FALSE)
run_order$run_order <- as.integer(run_order$run_order)
run_order$original_layer_index <- as.integer(run_order$original_layer_index)
run_order <- run_order[order(run_order$run_order), , drop = FALSE]

layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]
layers$layer_index <- seq_len(nrow(layers))

if (nrow(run_order) == 0) stop("Run order is empty")
if (nrow(run_order) != nrow(layers)) {
  warning("Run order rows (", nrow(run_order), ") != included layers (", nrow(layers), "). Proceeding with run order rows.")
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

hex <- hex %>% select(hex_id, geometry)

# Layer 1: full merged table
all_df <- read.csv(merged_csv, stringsAsFactors = FALSE)
if (!"hex_id" %in% names(all_df)) stop("Merged csv lacks hex_id: ", merged_csv)
all_sf <- left_join(hex, all_df, by = "hex_id")

if (file.exists(out_gpkg)) {
  unlink(out_gpkg)
}

sf::st_write(all_sf, out_gpkg, layer = "r9_all_44_combined", quiet = TRUE)
message("Wrote combined layer: r9_all_44_combined")

# Layers 2..45: one layer per run step
used_names <- character(0)
meta <- data.frame(
  run_order = integer(),
  gpkg_layer = character(),
  layer_key = character(),
  original_layer_index = integer(),
  display_name = character(),
  source_csv = character(),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(run_order))) {
  row <- run_order[i, , drop = FALSE]
  step_no <- as.integer(row$run_order)
  key <- row$layer_key
  idx <- as.integer(row$original_layer_index)
  display_name <- row$display_name

  out_csv <- file.path(layers_out_dir, sprintf("%02d_%s.csv", idx, key))
  if (!file.exists(out_csv)) {
    stop("Missing step csv for run_order ", step_no, ": ", out_csv)
  }

  df <- read.csv(out_csv, stringsAsFactors = FALSE)
  if (!"hex_id" %in% names(df)) {
    stop("Step csv lacks hex_id: ", out_csv)
  }

  nm <- sanitize_layer_name(step_no, key, used_names)
  used_names <- c(used_names, nm)

  layer_sf <- left_join(hex, df, by = "hex_id")
  sf::st_write(layer_sf, out_gpkg, layer = nm, append = TRUE, quiet = TRUE)
  message(sprintf("Wrote step %02d layer: %s", step_no, nm))

  meta <- rbind(
    meta,
    data.frame(
      run_order = step_no,
      gpkg_layer = nm,
      layer_key = key,
      original_layer_index = idx,
      display_name = display_name,
      source_csv = out_csv,
      stringsAsFactors = FALSE
    )
  )
}

meta_csv <- sub("\\.gpkg$", "_layer_index.csv", out_gpkg, ignore.case = TRUE)
write.csv(meta, meta_csv, row.names = FALSE, na = "")

message("Wrote GPKG: ", out_gpkg)
message("Wrote layer index: ", meta_csv)
