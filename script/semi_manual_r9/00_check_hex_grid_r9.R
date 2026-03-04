suppressPackageStartupMessages({
  library(DBI)
})

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)) else normalizePath("script/semi_manual_r9", winslash = "/", mustWork = FALSE)
repo_root <- normalizePath(file.path(script_dir, "..", ".."), winslash = "/", mustWork = FALSE)

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

schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r9")

db_connect_path <- find_db_connect(repo_root)
if (is.na(db_connect_path) || !nzchar(db_connect_path)) {
  stop("db_connect.R not found. Cannot check postgres hex table.")
}
source(db_connect_path)

cfg_env <- Sys.getenv("PIPELINE_ENV_PATH", ".env")
con <- connect_pg(cfg_env)
on.exit(DBI::dbDisconnect(con), add = TRUE)

exists_q <- sprintf("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='%s' AND table_name='%s') AS ok", schema, hex_table)
ok <- DBI::dbGetQuery(con, exists_q)$ok[[1]]
if (!isTRUE(ok)) {
  stop("Missing hex table in Postgres: ", schema, ".", hex_table, "\nCreate it before running layer scripts.")
}

n_q <- sprintf("SELECT COUNT(*) AS n FROM %s.%s", schema, hex_table)
n <- DBI::dbGetQuery(con, n_q)$n[[1]]
message("Hex grid ready: ", schema, ".", hex_table, " | rows=", n)
message("Next: run scripts in script/semi_manual_r9/layers/ one-by-one.")
