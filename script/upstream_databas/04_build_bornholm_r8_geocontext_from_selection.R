suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(DBI)
})

sf::sf_use_s2(FALSE)

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
if (length(file_arg) > 0) {
  script_file <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
  script_dir <- dirname(script_file)
  project_root <- normalizePath(file.path(script_dir, "..", ".."), winslash = "/", mustWork = TRUE)
} else {
  script_dir <- normalizePath("databas/script", winslash = "/", mustWork = FALSE)
  project_root <- normalizePath(".", winslash = "/", mustWork = FALSE)
}

db_connect_candidates <- c(
  file.path(project_root, "databas/generell_databas_setup/R/db_connect.R"),
  file.path(project_root, "generell_databas_setup/R/db_connect.R"),
  file.path(project_root, "speedlocal_bornholm/R/db_connect.R")
)
db_connect_path <- db_connect_candidates[file.exists(db_connect_candidates)][1]
if (is.na(db_connect_path) || !nzchar(db_connect_path)) {
  stop("Could not find db_connect.R. Tried: ", paste(db_connect_candidates, collapse = " | "))
}

source(db_connect_path)
source(file.path(script_dir, "lib/geocontext_qgis_layers.R"))

cfg_env <- Sys.getenv("PIPELINE_ENV_PATH", ".env")
schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r8")
selection_csv <- Sys.getenv(
  "GEOCONTEXT_SELECTION_CSV",
  file.path(script_dir, "config/bornholm_r8_geocontext_layers.csv")
)
out_table <- Sys.getenv("GEOCONTEXT_OUT_TABLE", "bornholm_r8_geocontext_raw")

if (!file.exists(selection_csv)) {
  message("Selection CSV not found, generating from QGIS project...")
  source(file.path(script_dir, "03_prepare_bornholm_r8_geocontext_selection.R"))
}

if (!file.exists(selection_csv)) {
  stop("Selection CSV still missing: ", selection_csv)
}

sel <- read.csv(selection_csv, stringsAsFactors = FALSE)
if (!("include" %in% names(sel))) {
  stop("Selection CSV is missing required column: include")
}

sel$include <- as.logical(sel$include)
sel <- sel[sel$include, , drop = FALSE]
if (nrow(sel) == 0) {
  stop("No layers selected (include=TRUE) in: ", selection_csv)
}

con <- connect_pg(cfg_env)
on.exit(DBI::dbDisconnect(con), add = TRUE)

message("Loading hex grid: ", schema, ".", hex_table)
hex <- sf::st_read(
  con,
  query = sprintf("SELECT h3 AS hex_id, geometry FROM %s.%s", schema, hex_table),
  quiet = TRUE
)

if (nrow(hex) == 0) {
  stop("Hex table is empty: ", schema, ".", hex_table)
}

message("Aggregating ", nrow(sel), " selected layers...")
features <- hex %>% st_drop_geometry() %>% select(hex_id)

for (i in seq_len(nrow(sel))) {
  r <- sel[i, , drop = FALSE]
  message(sprintf("[%d/%d] %s", i, nrow(sel), r$display_name))
  part <- tryCatch(
    aggregate_layer_to_hex(hex, r),
    error = function(e) {
      warning("Failed to aggregate layer: ", r$display_name, " | ", conditionMessage(e))
      hex %>% st_drop_geometry() %>% select(hex_id)
    }
  )
  features <- features %>% left_join(part, by = "hex_id")
}

message("Writing table: ", schema, ".", out_table)
DBI::dbWriteTable(con, DBI::Id(schema = schema, table = out_table), features, overwrite = TRUE)
DBI::dbExecute(
  con,
  sprintf("CREATE INDEX IF NOT EXISTS %s_hex_id_idx ON %s.%s(hex_id);", out_table, schema, out_table)
)

n_hex <- DBI::dbGetQuery(con, sprintf("SELECT COUNT(*) AS n FROM %s.%s", schema, hex_table))$n[[1]]
n_out <- DBI::dbGetQuery(con, sprintf("SELECT COUNT(*) AS n FROM %s.%s", schema, out_table))$n[[1]]

if (!isTRUE(n_hex == n_out)) {
  stop(sprintf("Row mismatch: %s.%s=%s vs %s.%s=%s", schema, hex_table, n_hex, schema, out_table, n_out))
}

message("Done. Rows: ", n_out, " | Columns: ", ncol(features))
