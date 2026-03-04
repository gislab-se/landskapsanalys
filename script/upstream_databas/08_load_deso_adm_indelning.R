suppressPackageStartupMessages({
  library(DBI)
  library(sf)
})

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep('^--file=', args_full, value = TRUE)
if (length(file_arg) > 0) {
  script_file <- normalizePath(sub('^--file=', '', file_arg[1]), winslash = '/', mustWork = TRUE)
  script_dir <- dirname(script_file)
  project_root <- normalizePath(file.path(script_dir, '..', '..'), winslash = '/', mustWork = TRUE)
} else {
  script_dir <- normalizePath('databas/script', winslash = '/', mustWork = FALSE)
  project_root <- normalizePath('.', winslash = '/', mustWork = FALSE)
}

db_connect_candidates <- c(
  file.path(project_root, 'databas/generell_databas_setup/R/db_connect.R'),
  file.path(project_root, 'generell_databas_setup/R/db_connect.R')
)
db_connect_path <- db_connect_candidates[file.exists(db_connect_candidates)][1]
if (is.na(db_connect_path) || !nzchar(db_connect_path)) {
  stop('Could not find db_connect.R. Tried: ', paste(db_connect_candidates, collapse = ' | '))
}
source(db_connect_path)

cfg_env <- Sys.getenv('PIPELINE_ENV_PATH', '.env')
schema <- Sys.getenv('ADM_SCHEMA', 'adm_indelning')
gpkg_path <- Sys.getenv('DESO_GPKG_PATH', 'C:/gislab/data/deso/DeSO_2025.gpkg')
table_name <- Sys.getenv('DESO_TABLE', 'deso_2025')

if (!file.exists(gpkg_path)) stop('Missing GeoPackage: ', gpkg_path)

con <- connect_pg(cfg_env)
on.exit(DBI::dbDisconnect(con), add = TRUE)

DBI::dbExecute(con, 'CREATE EXTENSION IF NOT EXISTS postgis')
DBI::dbExecute(con, sprintf('CREATE SCHEMA IF NOT EXISTS %s', DBI::dbQuoteIdentifier(con, schema)))
DBI::dbExecute(con, sprintf('DROP TABLE IF EXISTS %s.%s', DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, table_name)))

lyr <- sf::st_layers(gpkg_path)$name[1]
message('Reading layer: ', lyr)
deso <- sf::st_read(gpkg_path, layer = lyr, quiet = TRUE)
names(deso) <- tolower(names(deso))

required <- c('lanskod', 'kommunkod', 'kommunnamn')
missing <- setdiff(required, names(deso))
if (length(missing) > 0) stop('Missing required columns in DeSO: ', paste(missing, collapse = ', '))

sf::st_write(
  obj = deso,
  dsn = con,
  layer = DBI::Id(schema = schema, table = table_name),
  append = FALSE,
  quiet = TRUE
)

DBI::dbExecute(con, sprintf(
  'CREATE INDEX IF NOT EXISTS %s ON %s.%s USING GIST (sp_geometry)',
  DBI::dbQuoteIdentifier(con, paste0(table_name, '_geom_gix')),
  DBI::dbQuoteIdentifier(con, schema),
  DBI::dbQuoteIdentifier(con, table_name)
))

sql_deso_3006 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT objectid, objektidentitet, desokod, regsokod, lanskod,
          LPAD(CAST(kommunkod AS text), 4, '0') AS kommunkod,
          kommunnamn, version,
          ST_Transform(sp_geometry, 3006)::geometry(MultiPolygon, 3006) AS geom
   FROM %s.%s
   WHERE lanskod = '20'",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_deso_3006'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, table_name)
)
DBI::dbExecute(con, sql_deso_3006)

sql_deso_4326 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT objectid, objektidentitet, desokod, regsokod, lanskod,
          LPAD(CAST(kommunkod AS text), 4, '0') AS kommunkod,
          kommunnamn, version,
          ST_Transform(sp_geometry, 4326)::geometry(MultiPolygon, 4326) AS geom
   FROM %s.%s
   WHERE lanskod = '20'",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_deso_4326'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, table_name)
)
DBI::dbExecute(con, sql_deso_4326)

sql_lan_3006 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT 1::int AS id, '20'::text AS lanskod, 'Dalarna'::text AS lansnamn,
          ST_Multi(ST_UnaryUnion(ST_Collect(geom)))::geometry(MultiPolygon, 3006) AS geom
   FROM %s.%s",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_lan_3006'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_deso_3006')
)
DBI::dbExecute(con, sql_lan_3006)

sql_lan_4326 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT id, lanskod, lansnamn, ST_Transform(geom, 4326)::geometry(MultiPolygon, 4326) AS geom
   FROM %s.%s",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_lan_4326'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_lan_3006')
)
DBI::dbExecute(con, sql_lan_4326)

sql_kommun_3006 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT row_number() OVER (ORDER BY kommunkod) AS id,
          kommunkod, kommunnamn,
          ST_Multi(ST_UnaryUnion(ST_Collect(geom)))::geometry(MultiPolygon, 3006) AS geom
   FROM %s.%s
   GROUP BY kommunkod, kommunnamn",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommuner_3006'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_deso_3006')
)
DBI::dbExecute(con, sql_kommun_3006)

sql_kommun_4326 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT id, kommunkod, kommunnamn, ST_Transform(geom, 4326)::geometry(MultiPolygon, 4326) AS geom
   FROM %s.%s",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommuner_4326'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommuner_3006')
)
DBI::dbExecute(con, sql_kommun_4326)

sql_grp_3006 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   WITH base AS (
     SELECT kommunkod, kommunnamn, geom,
            CASE
              WHEN kommunkod IN ('2023','2039','2021') THEN 1
              WHEN kommunkod IN ('2031','2029','2026') THEN 2
              WHEN kommunkod IN ('2080','2081') THEN 3
              WHEN kommunkod IN ('2061','2085') THEN 4
              WHEN kommunkod IN ('2062','2034') THEN 5
              WHEN kommunkod IN ('2084','2083','2082') THEN 6
              ELSE NULL
            END AS kommungrupp_id
     FROM %s.%s
   )
   SELECT row_number() OVER (ORDER BY kommungrupp_id) AS id,
          kommungrupp_id,
          CASE
            WHEN kommungrupp_id = 1 THEN 'Kommungrupp 1: Malung-Salen, Alvdalen, Vansbro'
            WHEN kommungrupp_id = 2 THEN 'Kommungrupp 2: Rattvik, Leksand, Gagnef'
            WHEN kommungrupp_id = 3 THEN 'Kommungrupp 3: Falun, Borlange'
            WHEN kommungrupp_id = 4 THEN 'Kommungrupp 4: Smedjebacken, Ludvika'
            WHEN kommungrupp_id = 5 THEN 'Kommungrupp 5: Mora, Orsa'
            WHEN kommungrupp_id = 6 THEN 'Kommungrupp 6: Avesta, Hedemora, Sater'
            ELSE 'Okand'
          END AS kommungrupp_namn,
          string_agg(kommunnamn, ', ' ORDER BY kommunnamn) AS kommuner,
          ST_Multi(ST_UnaryUnion(ST_Collect(geom)))::geometry(MultiPolygon, 3006) AS geom
   FROM base
   WHERE kommungrupp_id IS NOT NULL
   GROUP BY kommungrupp_id",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommungrupper_3006'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommuner_3006')
)
DBI::dbExecute(con, sql_grp_3006)

sql_grp_4326 <- sprintf(
  "CREATE OR REPLACE VIEW %s.%s AS
   SELECT id, kommungrupp_id, kommungrupp_namn, kommuner,
          ST_Transform(geom, 4326)::geometry(MultiPolygon, 4326) AS geom
   FROM %s.%s",
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommungrupper_4326'),
  DBI::dbQuoteIdentifier(con, schema), DBI::dbQuoteIdentifier(con, 'v_dalarna_kommungrupper_3006')
)
DBI::dbExecute(con, sql_grp_4326)

cnt <- DBI::dbGetQuery(con, "
SELECT
  (SELECT COUNT(*) FROM adm_indelning.deso_2025) AS n_deso_total,
  (SELECT COUNT(*) FROM adm_indelning.v_dalarna_deso_3006) AS n_dalarna_deso,
  (SELECT COUNT(*) FROM adm_indelning.v_dalarna_kommuner_3006) AS n_kommuner,
  (SELECT COUNT(*) FROM adm_indelning.v_dalarna_kommungrupper_3006) AS n_kommungrupper
")
print(cnt)

message('Created adm_indelning DeSO table and views.')