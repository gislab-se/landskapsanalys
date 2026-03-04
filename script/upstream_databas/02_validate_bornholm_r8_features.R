suppressPackageStartupMessages({
  library(DBI)
})

source("generell_databas_setup/R/db_connect.R")
source("script/lib/bornholm_features.R")

cfg <- get_pipeline_config()
con <- connect_pg(cfg$env_path)
on.exit(DBI::dbDisconnect(con), add = TRUE)

val <- validate_feature_tables(con, cfg$schema, cfg$hex_table, "bornholm_r8_features")
print(val)

summary_tbl <- DBI::dbGetQuery(con, sprintf(
  "SELECT table_name FROM information_schema.tables WHERE table_schema = '%s' AND table_name LIKE 'bornholm_r8_%%' ORDER BY table_name;",
  cfg$schema
))

print(summary_tbl)
