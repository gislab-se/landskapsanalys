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
analysis_id <- "landskapsanalys_v2_1_geomweight58_res9"

Sys.setenv(
  LANDSKAPSANALYS_REPO_ROOT = repo_root,
  LANDSKAPSANALYS_ANALYSIS_ID = analysis_id,
  LANDSKAPSANALYS_ANALYSIS_SUBTITLE = "v2.1 geometry-balanced weighting, 58 lager, R9",
  LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION = "landskapsanalys_v2_baseline58_res9",
  LANDSKAPSANALYS_CONFIG_CSV = file.path(
    repo_root,
    "script/landskapsanalys/config/landskapsanalys_v2_1_geomweight58_res9_input_layers.csv"
  ),
  LANDSKAPSANALYS_OUT_DIR = file.path(
    repo_root,
    "data/interim/landskapsanalys_versions",
    analysis_id
  ),
  LANDSKAPSANALYS_WEIGHT_STRATEGY = "geometry_balanced_q99",
  LANDSKAPSANALYS_WEIGHT_QUANTILE = "0.99",
  LANDSKAPSANALYS_WEIGHT_RESCALE_MODE = "n_input_layers",
  LANDSKAPSANALYS_WEIGHT_DESCRIPTION = paste(
    "Per-layer robust q99 scaling, equal weighting across geometry types,",
    "and rescaling by active layer count to express neighborhood growth in layer-equivalent context mass."
  ),
  LANDSKAPSANALYS_SOURCE_MODEL_NOTE = paste(
    "V2.1 bygger vidare pa den frysta v2-baslinen och testar en ny context weighting-logik.",
    "Målet ar att minska bias mellan polygoner, linjer, punkter och kontinuerliga matt",
    "utan att anpassa faktor- eller klusterstegen annu."
  )
)

source(
  file.path(repo_root, "script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R"),
  local = FALSE
)

