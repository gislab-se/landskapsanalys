suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(tidyr)
  library(stringr)
  library(purrr)
  library(psych)
  library(cluster)
  library(FNN)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
analysis_id <- "landskapsanalys_v2_baseline58_res9"

Sys.setenv(
  LANDSKAPSANALYS_REPO_ROOT = repo_root,
  LANDSKAPSANALYS_ANALYSIS_ID = analysis_id,
  LANDSKAPSANALYS_ANALYSIS_SUBTITLE = "v2 baseline, 58 lager, R9",
  LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION = "landskapsanalys_58lager_geologi_restriktioner_res9",
  LANDSKAPSANALYS_CONFIG_CSV = file.path(
    repo_root,
    "script/landskapsanalys/config/landskapsanalys_v2_baseline58_res9_input_layers.csv"
  ),
  LANDSKAPSANALYS_OUT_DIR = file.path(
    repo_root,
    "data/interim/landskapsanalys_versions",
    analysis_id
  ),
  LANDSKAPSANALYS_SOURCE_MODEL_NOTE = paste(
    "V2-sparet startar fran den frysta 58-lagersmodellen.",
    "Detta ar baselinekorningen for metodforbattringar i landskapskaraktarsmodellen,",
    "innan upplosningsbyte eller acceptanslogik testas."
  )
)

source(
  file.path(repo_root, "script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R"),
  local = FALSE
)

