suppressPackageStartupMessages({
  library(sf)
})

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
if (length(file_arg) > 0) {
  script_file <- normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
  script_dir <- dirname(script_file)
} else {
  script_dir <- normalizePath("databas/script", winslash = "/", mustWork = FALSE)
}

source(file.path(script_dir, "lib/geocontext_qgis_layers.R"))

qgz_path <- Sys.getenv("GEOCONTEXT_QGZ_PATH", "c:/gislab/QGS_BOL_geocontext.qgz")
project_root <- Sys.getenv("GISLAB_ROOT", "c:/gislab")
out_csv <- Sys.getenv(
  "GEOCONTEXT_SELECTION_CSV",
  file.path(script_dir, "config/bornholm_r8_geocontext_layers.csv")
)

layers <- write_geocontext_selection_template(
  out_csv = out_csv,
  qgz_path = qgz_path,
  project_root = project_root
)

message("Template row count: ", nrow(layers))
message("Next: review include/value_field/aggregation_type in ", out_csv)
