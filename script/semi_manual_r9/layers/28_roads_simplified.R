# Step 28 (Original layer 14): Roads Simplified
# Explicit manual workflow:
# 1) Inspect input + road types (default; no aggregation)
# 2) Aggregate per road class when approved
#
# Preview (recommended first):
#   Sys.setenv(SHOW_MAPVIEW = "true", SHOW_LAYER_SUMMARY = "true", RUN_AGGREGATION = "false")
#
# Aggregate and write output:
#   Sys.setenv(RUN_AGGREGATION = "true", WRITE_OUTPUT = "true")

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- NULL

if (length(file_arg) > 0) {
  script_file <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
  script_dir <- dirname(script_file)
}

if (is.null(script_dir)) {
  if (file.exists("script/semi_manual_r9/layers/28_roads_simplified.R")) {
    script_dir <- normalizePath("script/semi_manual_r9/layers", winslash = "/", mustWork = TRUE)
  } else if (file.exists("layers/28_roads_simplified.R")) {
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

layer_index <- 14L
show_mapview <- is_truthy(Sys.getenv("SHOW_MAPVIEW", "true"))
force_mapview <- is_truthy(Sys.getenv("FORCE_MAPVIEW", "false"))
do_mapview <- show_mapview && (interactive() || force_mapview)
show_layer_summary <- is_truthy(Sys.getenv("SHOW_LAYER_SUMMARY", if (interactive()) "true" else "false"))
preview_only <- is_truthy(Sys.getenv("LAYER_PREVIEW_ONLY", "false"))
run_aggregation <- is_truthy(Sys.getenv("RUN_AGGREGATION", "false"))
if (preview_only) run_aggregation <- FALSE
write_output <- is_truthy(Sys.getenv("WRITE_OUTPUT", "true"))
road_type_field <- Sys.getenv("ROAD_TYPE_FIELD", "vejkategor")
metric_crs <- suppressWarnings(as.integer(Sys.getenv("METRIC_CRS", "25832")))
if (is.na(metric_crs)) metric_crs <- 25832L
output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) output_alpha <- 0.35

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

if (!road_type_field %in% names(source_layer)) {
  stop(
    "ROAD_TYPE_FIELD not found in source layer: ", road_type_field, "\n",
    "Available fields include: ", paste(names(source_layer), collapse = ", ")
  )
}

raw_type <- as.character(source_layer[[road_type_field]])
raw_type[is.na(raw_type) | !nzchar(trimws(raw_type))] <- "(empty)"
type_counts <- sort(table(raw_type), decreasing = TRUE)
message("Road type field: ", road_type_field)
message("Number of unique road types: ", length(type_counts))
print(data.frame(
  road_type = names(type_counts),
  n_features = as.integer(type_counts),
  row.names = NULL,
  stringsAsFactors = FALSE
))

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

source_layer$road_class <- classify_road_class(source_layer[[road_type_field]])
class_counts <- sort(table(source_layer$road_class), decreasing = TRUE)
message("Mapped road classes (small/medium/large/other):")
print(data.frame(
  road_class = names(class_counts),
  n_features = as.integer(class_counts),
  row.names = NULL,
  stringsAsFactors = FALSE
))

if (do_mapview) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
  } else {
    message("Opening pre-aggregation mapview (roads by class)...")
    pre_map <- mapview::mapview(
      hex,
      alpha.regions = 0,
      color = "grey70",
      lwd = 0.5,
      layer.name = "Hex grid (R9)"
    ) + mapview::mapview(
      source_layer,
      zcol = "road_class",
      layer.name = paste0("Input roads (", road_type_field, " -> road_class)")
    )
    print(pre_map)
  }
}

if (!run_aggregation) {
  message("RUN_AGGREGATION=false -> stopped after input inspection and road type review.")
} else {
  hex_m <- sf::st_transform(hex, metric_crs) %>% dplyr::select(hex_id)
  roads_m <- sf::st_transform(source_layer, metric_crs) %>% dplyr::select(road_class)
  ix <- suppressWarnings(sf::st_intersection(roads_m, hex_m))

  out <- hex %>% sf::st_drop_geometry() %>% dplyr::transmute(hex_id)
  prefix <- layer_row$layer_key
  out_cols <- c(
    paste0(prefix, "_length_m_small"),
    paste0(prefix, "_length_m_medium"),
    paste0(prefix, "_length_m_large"),
    paste0(prefix, "_length_m_other")
  )
  for (nm in out_cols) out[[nm]] <- 0

  if (nrow(ix) > 0) {
    lens <- as.numeric(sf::st_length(sf::st_geometry(ix)))
    ag <- ix %>%
      sf::st_drop_geometry() %>%
      dplyr::mutate(len_m = lens) %>%
      dplyr::group_by(hex_id, road_class) %>%
      dplyr::summarise(len_m = sum(len_m, na.rm = TRUE), .groups = "drop")

    for (cls in c("small", "medium", "large", "other")) {
      col_nm <- paste0(prefix, "_length_m_", cls)
      tmp <- ag[ag$road_class == cls, c("hex_id", "len_m"), drop = FALSE]
      names(tmp)[2] <- col_nm
      out <- dplyr::left_join(out, tmp, by = "hex_id")
      if (paste0(col_nm, ".x") %in% names(out) || paste0(col_nm, ".y") %in% names(out)) {
        out[[col_nm]] <- dplyr::coalesce(out[[paste0(col_nm, ".y")]], out[[paste0(col_nm, ".x")]], 0)
        out[[paste0(col_nm, ".x")]] <- NULL
        out[[paste0(col_nm, ".y")]] <- NULL
      } else {
        out[[col_nm]] <- dplyr::coalesce(out[[col_nm]], 0)
      }
    }
  }

  out[[paste0(prefix, "_length_m_total")]] <- out[[paste0(prefix, "_length_m_small")]] +
    out[[paste0(prefix, "_length_m_medium")]] +
    out[[paste0(prefix, "_length_m_large")]] +
    out[[paste0(prefix, "_length_m_other")]]

  if (do_mapview) {
    if (!requireNamespace("mapview", quietly = TRUE)) {
      warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    } else {
      message("Opening post-aggregation mapview (total road length)...")
      hex_after <- dplyr::left_join(hex, out, by = "hex_id")
      total_col <- paste0(prefix, "_length_m_total")
      post_map <- mapview::mapview(
        hex_after,
        zcol = total_col,
        alpha.regions = output_alpha,
        layer.name = paste0("Output: ", total_col)
      ) + mapview::mapview(
        source_layer,
        zcol = "road_class",
        alpha.regions = 0.30,
        layer.name = "Input roads by class"
      )
      print(post_map)
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
