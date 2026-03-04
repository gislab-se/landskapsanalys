suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(DBI)
})

sf::sf_use_s2(FALSE)

`%||%` <- function(a, b) if (!is.null(a) && nzchar(a)) a else b

semi_manual_home <- function() {
  h <- Sys.getenv("SEMI_MANUAL_R9_HOME", "")
  if (nzchar(h) && dir.exists(h)) {
    return(normalizePath(h, winslash = "/", mustWork = TRUE))
  }
  normalizePath("script/semi_manual_r9", winslash = "/", mustWork = FALSE)
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

run_single_layer <- function(layer_index) {
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
  hex <- load_hex_grid(hex_source = hex_source, schema = schema, hex_table = hex_table, home = home, hex_file = hex_file, hex_layer = hex_layer)

  out <- aggregate_layer_to_hex(hex, layer_row)

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
