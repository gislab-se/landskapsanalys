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
analysis_id <- "landskapsanalys_39lager_res9"

Sys.setenv(
  LANDSKAPSANALYS_REPO_ROOT = repo_root,
  LANDSKAPSANALYS_ANALYSIS_ID = analysis_id,
  LANDSKAPSANALYS_ANALYSIS_SUBTITLE = "39 lager, R9",
  LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION = "landskapsanalys_26lager_res9",
  LANDSKAPSANALYS_CONFIG_CSV = file.path(
    repo_root,
    "script/landskapsanalys/config/landskapsanalys_39lager_res9_input_layers.csv"
  ),
  LANDSKAPSANALYS_OUT_DIR = file.path(
    repo_root,
    "data/interim/landskapsanalys_versions",
    analysis_id
  ),
  LANDSKAPSANALYS_SOURCE_MODEL_NOTE = paste(
    "26-lagersmodellen utokad med fler skyddade natur- och restriktionslager,",
    "built low selection samt tva manuella geologilager fran data/raw/manual_extra_layers.",
    "Jordart och Prekvart fors in som provisioriska parentlager och bor senare testas",
    "som subtype-splits for att undvika att full polygon-tackning misstolkas som analysignal."
  )
)

source(
  file.path(repo_root, "script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R"),
  local = FALSE
)