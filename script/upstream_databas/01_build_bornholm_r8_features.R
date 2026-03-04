suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(DBI)
})

sf::sf_use_s2(FALSE)

source("generell_databas_setup/R/db_connect.R")
source("script/lib/bornholm_features.R")

cfg <- get_pipeline_config()
con <- connect_pg(cfg$env_path)
on.exit(DBI::dbDisconnect(con), add = TRUE)

validate_input_files(cfg)
DBI::dbExecute(con, sprintf("CREATE SCHEMA IF NOT EXISTS %s;", cfg$schema))

message("Loading hex grid...")
hex <- load_hex_grid(con, cfg$schema, cfg$hex_table)

message("Building population features...")
hex_pop <- build_population(hex, cfg$tab_pop)

message("Building elevation features...")
hex_elev <- build_elevation(hex, cfg$tab_curves)

message("Building protected-share features...")
hex_prot <- build_protected_share(hex, cfg$shp_nat)

message("Building wind features...")
hex_wind <- build_wind(hex, cfg$gpkg_wind, cfg$wind_layer)

message("Building joined feature matrix...")
hex_features <- build_feature_matrix(hex, hex_prot, hex_wind, hex_pop, hex_elev)

message("Writing feature tables to PostGIS...")
write_tbl(con, cfg$schema, "bornholm_r8_pop", hex_pop)
write_tbl(con, cfg$schema, "bornholm_r8_elev", hex_elev)
write_tbl(con, cfg$schema, "bornholm_r8_protected", hex_prot)
write_tbl(con, cfg$schema, "bornholm_r8_wind", hex_wind)
write_tbl(con, cfg$schema, "bornholm_r8_features", hex_features)

val <- validate_feature_tables(con, cfg$schema, cfg$hex_table, "bornholm_r8_features")
message("Validation OK. Hex rows: ", val$n_hex, ", Feature rows: ", val$n_feat)
