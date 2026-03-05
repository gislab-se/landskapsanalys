suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(DBI)
})

sf::sf_use_s2(FALSE)

`%||%` <- function(a, b) if (!is.null(a) && nzchar(a)) a else b

is_truthy <- function(x) {
  tolower(trimws(x %||% "")) %in% c("1", "true", "yes", "y", "on")
}

format_crs <- function(crs_obj) {
  if (is.null(crs_obj)) {
    return("NA")
  }
  epsg <- crs_obj$epsg
  if (!is.null(epsg) && !is.na(epsg)) {
    return(paste0("EPSG:", epsg))
  }
  input <- crs_obj$input %||% ""
  if (nzchar(input)) {
    return(input)
  }
  "NA"
}

semi_manual_home <- function() {
  env_home <- Sys.getenv("SEMI_MANUAL_R9_HOME", "")
  candidates <- unique(c(
    env_home,
    "script/semi_manual_r9",
    "semi_manual_r9",
    "."
  ))
  candidates <- candidates[nzchar(candidates)]

  for (cand in candidates) {
    if (!dir.exists(cand)) {
      next
    }
    if (
      file.exists(file.path(cand, "config", "bornholm_r9_geocontext_layers.csv")) &&
      file.exists(file.path(cand, "lib", "manual_layer_aggregation.R"))
    ) {
      return(normalizePath(cand, winslash = "/", mustWork = TRUE))
    }
  }

  stop(
    "Could not locate semi_manual_r9 home.\n",
    "Tried: ", paste(normalizePath(candidates, winslash = "/", mustWork = FALSE), collapse = ", "), "\n",
    "Set SEMI_MANUAL_R9_HOME to the script/semi_manual_r9 folder."
  )
}

repo_root <- function(home) {
  normalizePath(file.path(home, "..", ".."), winslash = "/", mustWork = FALSE)
}

find_db_connect <- function(root) {
  candidates <- c(
    file.path(root, "databas/generell_databas_setup/R/db_connect.R"),
    file.path(root, "generell_databas_setup/R/db_connect.R"),
    file.path(root, "speedlocal_bornholm/R/db_connect.R"),
    "C:/gislab/databas/generell_databas_setup/R/db_connect.R",
    "C:/gislab/speedlocal_bornholm/R/db_connect.R"
  )
  candidates[file.exists(candidates)][1]
}

resolve_pipeline_env_path <- function(root) {
  from_env <- Sys.getenv("PIPELINE_ENV_PATH", "")
  candidates <- unique(c(
    from_env,
    ".env",
    file.path(root, ".env"),
    file.path(root, "generell_databas_setup/.env"),
    file.path(root, "databas/generell_databas_setup/.env"),
    "C:/gislab/databas/generell_databas_setup/.env",
    "C:/gislab/speedlocal_bornholm/.env"
  ))
  candidates <- candidates[nzchar(candidates)]
  hit <- candidates[file.exists(candidates)][1]
  if (is.na(hit) || !nzchar(hit)) {
    stop(
      "Could not find .env for Postgres connection. Tried: ",
      paste(normalizePath(candidates, winslash = "/", mustWork = FALSE), collapse = ", "),
      "\nSet PIPELINE_ENV_PATH explicitly if needed."
    )
  }
  normalizePath(hit, winslash = "/", mustWork = TRUE)
}

load_hex_grid <- function(hex_source, schema, hex_table, home, hex_file = "", hex_layer = "") {
  if (tolower(hex_source) == "postgres") {
    root <- repo_root(home)
    db_connect_path <- find_db_connect(root)
    if (is.na(db_connect_path) || !nzchar(db_connect_path)) {
      stop("db_connect.R not found. Set HEX_SOURCE=file or ensure db_connect.R exists.")
    }
    source(db_connect_path)
    cfg_env <- resolve_pipeline_env_path(root)
    message("Using PIPELINE_ENV_PATH: ", cfg_env)
    con <- connect_pg(cfg_env)
    on.exit(DBI::dbDisconnect(con), add = TRUE)
    hex <- sf::st_read(
      con,
      query = sprintf("SELECT h3 AS hex_id, geometry FROM %s.%s", schema, hex_table),
      quiet = TRUE
    )
    if (nrow(hex) == 0) {
      stop("Hex table is empty: ", schema, ".", hex_table)
    }
    return(hex)
  }

  if (!nzchar(hex_file) || !file.exists(hex_file)) {
    stop("HEX_SOURCE=file requires HEX_FILE to exist.")
  }
  if (nzchar(hex_layer)) {
    hex <- sf::st_read(hex_file, layer = hex_layer, quiet = TRUE)
  } else {
    hex <- sf::st_read(hex_file, quiet = TRUE)
  }

  if (!"hex_id" %in% names(hex)) {
    stop("Hex file must contain column 'hex_id'.")
  }
  hex
}

load_aggregator <- function(home) {
  agg_path <- normalizePath(file.path(home, "..", "upstream_databas", "lib", "geocontext_qgis_layers.R"), winslash = "/", mustWork = TRUE)
  source(agg_path)
}

prepare_source_layer <- function(layer_sf, target_crs) {
  layer_sf <- sf::st_zm(layer_sf, drop = TRUE, what = "ZM")
  layer_sf <- sf::st_make_valid(layer_sf)
  sf::st_transform(layer_sf, target_crs)
}

print_layer_diagnostics <- function(source_layer) {
  attr_df <- sf::st_drop_geometry(source_layer)

  message("Column names (", ncol(source_layer), "):")
  for (nm in names(source_layer)) {
    message("  - ", nm)
  }

  message("Basic summary:")
  message("  Rows: ", nrow(source_layer))
  message("  Attribute columns: ", ncol(attr_df))
  message("  CRS: ", format_crs(sf::st_crs(source_layer)))

  bbox <- sf::st_bbox(source_layer)
  bbox_vals <- as.numeric(bbox)
  if (all(is.finite(bbox_vals))) {
    message(
      sprintf(
        "  BBOX: xmin=%.2f ymin=%.2f xmax=%.2f ymax=%.2f",
        bbox_vals[1], bbox_vals[2], bbox_vals[3], bbox_vals[4]
      )
    )
  }

  geom_types <- sort(table(as.character(sf::st_geometry_type(source_layer, by_geometry = TRUE))), decreasing = TRUE)
  if (length(geom_types) == 0) {
    message("  Geometry types: none")
  } else {
    pairs <- paste0(names(geom_types), "=", as.integer(geom_types))
    message("  Geometry types: ", paste(pairs, collapse = ", "))
  }

  if (ncol(attr_df) > 0) {
    message("Attribute summary:")
    print(summary(attr_df))
  } else {
    message("No non-geometry attributes to summarize.")
  }
}

show_pre_aggregation_map <- function(hex, source_layer, display_name) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    return(invisible(NULL))
  }

  message("Opening pre-aggregation mapview...")
  pre_map <- mapview::mapview(
    hex,
    alpha.regions = 0,
    color = "grey70",
    lwd = 0.5,
    layer.name = "Hex grid (R9)"
  ) + mapview::mapview(
    source_layer,
    layer.name = paste0("Source: ", display_name)
  )
  print(pre_map)
}

show_post_aggregation_map <- function(hex, out, source_layer, display_name) {
  if (!requireNamespace("mapview", quietly = TRUE)) {
    warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    return(invisible(NULL))
  }

  value_cols <- setdiff(names(out), "hex_id")
  value_col <- if (length(value_cols) > 0) value_cols[[1]] else NA_character_
  output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
  if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) {
    output_alpha <- 0.35
  }

  message("Opening post-aggregation mapview...")
  hex_after <- dplyr::left_join(hex, out, by = "hex_id")
  source_overlay <- mapview::mapview(
    source_layer,
    layer.name = paste0("Source: ", display_name)
  )

  if (!is.na(value_col) && nzchar(value_col)) {
    after_map <- mapview::mapview(
      hex_after,
      zcol = value_col,
      alpha.regions = output_alpha,
      layer.name = paste0("Aggregated: ", value_col)
    ) + source_overlay
  } else {
    after_map <- mapview::mapview(
      hex_after,
      alpha.regions = output_alpha,
      layer.name = "Aggregated hex output"
    ) + source_overlay
  }

  print(after_map)
}

run_single_layer <- function(layer_index) {
  home <- semi_manual_home()
  repo <- repo_root(home)

  show_mapview <- is_truthy(Sys.getenv("SHOW_MAPVIEW", "true"))
  force_mapview <- is_truthy(Sys.getenv("FORCE_MAPVIEW", "false"))
  do_mapview <- show_mapview && (interactive() || force_mapview)
  show_layer_summary <- is_truthy(Sys.getenv("SHOW_LAYER_SUMMARY", if (interactive()) "true" else "false"))
  preview_only <- is_truthy(Sys.getenv("LAYER_PREVIEW_ONLY", "false"))

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
  hex <- load_hex_grid(hex_source = hex_source, schema = schema, hex_table = hex_table, home = home, hex_file = hex_file, hex_layer = hex_layer)

  source_layer <- NULL
  if (show_layer_summary || do_mapview || preview_only) {
    source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
    source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex))

    if (show_layer_summary) {
      print_layer_diagnostics(source_layer)
    }

    if (do_mapview) {
      show_pre_aggregation_map(hex, source_layer, layer_row$display_name)
    }
  }

  if (preview_only) {
    message("LAYER_PREVIEW_ONLY=true -> skipping aggregation and CSV/log write for this layer.")
    return(invisible(
      list(
        status = "preview_only",
        layer_index = layer_index,
        layer_key = layer_row$layer_key,
        display_name = layer_row$display_name
      )
    ))
  }

  out <- aggregate_layer_to_hex(hex, layer_row)

  if (do_mapview) {
    if (is.null(source_layer)) {
      source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
      source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex))
    }
    show_post_aggregation_map(hex, out, source_layer, layer_row$display_name)
  }

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

  invisible(
    list(
      status = "ok",
      layer_index = layer_index,
      layer_key = layer_row$layer_key,
      output_csv = out_csv
    )
  )
}
