# Step 11 (Original layer 16): BES_NATURTYPER split by Natyp_navn
# Explicit manual workflow:
# 1) Inspect input + naturtype classes (default; no aggregation)
# 2) Aggregate total + selected split columns when approved
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
  if (file.exists("script/semi_manual_r9/layers/11_bes_naturtyper.R")) {
    script_dir <- normalizePath("script/semi_manual_r9/layers", winslash = "/", mustWork = TRUE)
  } else if (file.exists("layers/11_bes_naturtyper.R")) {
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
source(file.path(script_dir, "..", "lib", "subcategory_splits.R"))

layer_index <- 16L
parent_run_order <- 11L
show_mapview <- is_truthy(Sys.getenv("SHOW_MAPVIEW", "true"))
force_mapview <- is_truthy(Sys.getenv("FORCE_MAPVIEW", "false"))
do_mapview <- show_mapview && (interactive() || force_mapview)
show_layer_summary <- is_truthy(Sys.getenv("SHOW_LAYER_SUMMARY", if (interactive()) "true" else "false"))
preview_only <- is_truthy(Sys.getenv("LAYER_PREVIEW_ONLY", "false"))
run_aggregation <- is_truthy(Sys.getenv("RUN_AGGREGATION", "false"))
if (preview_only) run_aggregation <- FALSE
write_output <- is_truthy(Sys.getenv("WRITE_OUTPUT", "true"))
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
split_rows <- read_subcategory_splits(home, parent_run_order = parent_run_order)
if (nrow(split_rows) == 0) {
  stop("No active split rows found for step ", parent_run_order)
}

split_field <- unique(split_rows$split_field)
if (length(split_field) != 1) {
  stop("Expected exactly one split field for BES_NATURTYPER, got: ", paste(split_field, collapse = ", "))
}
split_field <- split_field[1]
allowed_values <- split_rows$split_value
allowed_slugs <- split_rows$split_value_slug

message(sprintf("Layer %d/%d: %s", layer_index, nrow(layers), layer_row$display_name))
message("Hex source: ", hex_source, " | schema.table: ", schema, ".", hex_table)
message("Split field: ", split_field)
print(split_rows[, c("child_order", "child_key", "split_value", "child_output_column")])

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

if (!split_field %in% names(source_layer)) {
  stop(
    "Split field not found in source layer: ", split_field, "\n",
    "Available fields include: ", paste(names(source_layer), collapse = ", ")
  )
}

source_layer$split_value_raw <- trimws(as.character(source_layer[[split_field]]))
source_layer$split_value_raw[is.na(source_layer$split_value_raw) | !nzchar(source_layer$split_value_raw)] <- "(empty)"
source_layer$split_slug <- slugify_text(source_layer$split_value_raw)

value_counts <- sort(table(source_layer$split_value_raw), decreasing = TRUE)
message("Naturtype split values in source layer:")
print(data.frame(
  split_value = names(value_counts),
  n_features = as.integer(value_counts),
  row.names = NULL,
  stringsAsFactors = FALSE
))

unexpected <- setdiff(unique(source_layer$split_value_raw), c(allowed_values, "(empty)"))
if (length(unexpected) > 0) {
  warning(
    "BES_NATURTYPER contains values outside the selected split list: ",
    paste(unexpected, collapse = ", "),
    ". These remain visible only in the original total column."
  )
}

if (do_mapview) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
  } else {
    message("Opening pre-aggregation mapview (Naturtype by Natyp_navn)...")
    pre_map <- mapview::mapview(
      hex,
      alpha.regions = 0,
      color = "grey70",
      lwd = 0.5,
      layer.name = "Hex grid (R9)"
    ) + mapview::mapview(
      source_layer,
      zcol = "split_value_raw",
      layer.name = paste0("Input naturtyper (", split_field, ")")
    )
    print(pre_map)
  }
}

if (!run_aggregation) {
  message("RUN_AGGREGATION=false -> stopped after input inspection and split review.")
} else {
  join_metric_column <- function(out_df, tmp_df, col_nm) {
    out_df <- dplyr::left_join(out_df, tmp_df, by = "hex_id")
    if (paste0(col_nm, ".x") %in% names(out_df) || paste0(col_nm, ".y") %in% names(out_df)) {
      out_df[[col_nm]] <- dplyr::coalesce(out_df[[paste0(col_nm, ".y")]], out_df[[paste0(col_nm, ".x")]], 0)
      out_df[[paste0(col_nm, ".x")]] <- NULL
      out_df[[paste0(col_nm, ".y")]] <- NULL
    } else {
      out_df[[col_nm]] <- dplyr::coalesce(out_df[[col_nm]], 0)
    }
    out_df
  }

  hex_m <- sf::st_transform(hex, metric_crs) %>% dplyr::select(hex_id)
  hex_area_m2 <- as.numeric(sf::st_area(sf::st_geometry(hex_m)))
  natur_m <- sf::st_transform(source_layer, metric_crs) %>% dplyr::select(split_slug)
  ix <- suppressWarnings(sf::st_intersection(natur_m, hex_m))

  prefix <- layer_row$layer_key
  total_col <- paste0(prefix, "_area_share")
  out <- hex_m %>% sf::st_drop_geometry() %>% dplyr::transmute(hex_id, hex_area_m2 = hex_area_m2)
  out[[total_col]] <- 0
  for (col_nm in split_rows$child_output_column) {
    out[[col_nm]] <- 0
  }

  if (nrow(ix) > 0) {
    area_vals <- as.numeric(sf::st_area(sf::st_geometry(ix)))
    ag_total <- ix %>%
      sf::st_drop_geometry() %>%
      dplyr::mutate(area_m2 = area_vals) %>%
      dplyr::group_by(hex_id) %>%
      dplyr::summarise(area_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop") %>%
      dplyr::mutate(area_share = ifelse(hex_id %in% hex_m$hex_id, area_m2, 0))
    ag_total <- dplyr::left_join(out[, c("hex_id", "hex_area_m2")], ag_total, by = "hex_id") %>%
      dplyr::mutate(
        area_m2 = dplyr::coalesce(area_m2, 0),
        area_share = ifelse(hex_area_m2 > 0, area_m2 / hex_area_m2, 0)
      )
    tmp_total <- ag_total[, c("hex_id", "area_share"), drop = FALSE]
    names(tmp_total)[2] <- total_col
    out <- join_metric_column(out, tmp_total, total_col)

    ag_split <- ix %>%
      sf::st_drop_geometry() %>%
      dplyr::mutate(area_m2 = area_vals) %>%
      dplyr::group_by(hex_id, split_slug) %>%
      dplyr::summarise(area_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")

    for (i in seq_len(nrow(split_rows))) {
      row_i <- split_rows[i, , drop = FALSE]
      col_nm <- row_i$child_output_column
      slug_i <- row_i$split_value_slug
      tmp <- ag_split[ag_split$split_slug == slug_i, c("hex_id", "area_m2"), drop = FALSE]
      if (nrow(tmp) > 0) {
        tmp <- dplyr::left_join(out[, c("hex_id", "hex_area_m2")], tmp, by = "hex_id") %>%
          dplyr::mutate(
            area_m2 = dplyr::coalesce(area_m2, 0),
            area_share = ifelse(hex_area_m2 > 0, area_m2 / hex_area_m2, 0)
          ) %>%
          dplyr::select(hex_id, area_share)
      } else {
        tmp <- out[, c("hex_id"), drop = FALSE]
        tmp$area_share <- 0
      }
      names(tmp)[2] <- col_nm
      out <- join_metric_column(out, tmp, col_nm)
    }
  }

  out$hex_area_m2 <- NULL

  if (do_mapview) {
    if (!requireNamespace("mapview", quietly = TRUE)) {
      warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    } else {
      message("Opening post-aggregation mapview (Naturtype total share)...")
      hex_after <- dplyr::left_join(hex, out, by = "hex_id")
      post_map <- mapview::mapview(
        hex_after,
        zcol = total_col,
        alpha.regions = output_alpha,
        layer.name = paste0("Output: ", total_col)
      ) + mapview::mapview(
        source_layer,
        zcol = "split_value_raw",
        alpha.regions = 0.30,
        layer.name = paste0("Input naturtyper by ", split_field)
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
