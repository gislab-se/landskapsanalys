#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(openxlsx)
  library(readr)
})

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || all(is.na(x))) y else x
}

root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
args <- commandArgs(trailingOnly = TRUE)
output_path <- if (length(args) >= 1) args[[1]] else "docs/POTENTIAL_APP_SOURCE_LAYERS_2026-05-22.xlsx"
output_path <- normalizePath(output_path, winslash = "/", mustWork = FALSE)

read_registry <- function(path) {
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

read_assets <- function(path) {
  if (!file.exists(path)) {
    return(tibble::tibble())
  }
  readr::read_csv(path, show_col_types = FALSE, locale = readr::locale(encoding = "UTF-8"))
}

asset_value <- function(asset, column, default = NA_character_) {
  if (!column %in% names(asset) || nrow(asset) == 0) {
    return(default)
  }
  value <- asset[[column]][[1]]
  if (is.null(value) || is.na(value)) default else as.character(value)
}

format_filter <- function(layer) {
  field <- layer$filter_field %||% ""
  value <- layer$filter_value %||% ""
  mode <- layer$filter_mode %||% ""
  value <- paste(as.character(unlist(value)), collapse = ", ")
  parts <- c(
    if (nzchar(field)) paste0("field=", field) else character(),
    if (nzchar(mode)) paste0("mode=", mode) else character(),
    if (nzchar(value)) paste0("value=", value) else character()
  )
  paste(parts, collapse = "; ")
}

analysis_definition <- function(kind) {
  switch(
    as.character(kind),
    distance_conflict = "Too close to this source is treated as a conflict and normally uses a minimum-clearance distance/buffer.",
    proximity_feasibility = "Too far from this source is treated as less feasible and normally uses a maximum connection distance.",
    hard_exclusion = "This source is treated as an exclusion/no-go layer, optionally with a buffer.",
    "Other or not defined."
  )
}

source_layer_rows <- function(region_name, registry_path, asset_manifest_path) {
  registry <- read_registry(registry_path)
  assets <- read_assets(asset_manifest_path)
  groups <- registry$groups
  names(groups) <- vapply(groups, function(x) x$id %||% "", character(1))
  asset_ids <- if ("layer_id" %in% names(assets)) as.character(assets$layer_id) else character()

  rows <- lapply(registry$layers, function(layer) {
    group <- groups[[layer$group_id %||% ""]] %||% list()
    asset <- assets[asset_ids == (layer$id %||% ""), , drop = FALSE]
    if (nrow(asset) == 0) {
      asset <- assets[FALSE, , drop = FALSE]
    }
    data.frame(
      region = region_name,
      layer_name = enc2utf8(layer$label %||% ""),
      category_id = layer$group_id %||% "",
      category_label = enc2utf8(group$label %||% ""),
      category_definition = enc2utf8(group$interpretation %||% ""),
      analysis_type = group$analysis_kind %||% "",
      analysis_definition = analysis_definition(group$analysis_kind %||% ""),
      analysis_label = enc2utf8(group$analysis_label %||% ""),
      layer_id = layer$id %||% "",
      source_key = layer$layer_key %||% "",
      filter = format_filter(layer),
      geometry_family = asset_value(asset, "geometry_family"),
      feature_count = suppressWarnings(as.numeric(asset_value(asset, "feature_count", NA_character_))),
      source_exists = asset_value(asset, "source_exists"),
      asset_status = asset_value(asset, "status"),
      source_path = enc2utf8(asset_value(asset, "source_path")),
      app_geojson_path = enc2utf8(asset_value(asset, "geojson_path")),
      distance_table_path = enc2utf8(asset_value(asset, "distance_path")),
      analysis_rds_path = enc2utf8(asset_value(asset, "analysis_rds_path")),
      registry_note = enc2utf8(layer$note %||% ""),
      asset_message = enc2utf8(asset_value(asset, "message")),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })
  do.call(rbind, rows)
}

group_rows <- function(region_name, registry_path) {
  registry <- read_registry(registry_path)
  rows <- lapply(registry$groups, function(group) {
    data.frame(
      region = region_name,
      category_id = group$id %||% "",
      category_label = enc2utf8(group$label %||% ""),
      analysis_type = group$analysis_kind %||% "",
      analysis_definition = analysis_definition(group$analysis_kind %||% ""),
      analysis_label = enc2utf8(group$analysis_label %||% ""),
      analysis_min_m = group$analysis_min_m %||% NA,
      analysis_max_m = group$analysis_max_m %||% NA,
      analysis_step_m = group$analysis_step_m %||% NA,
      analysis_default_m = group$analysis_default_m %||% NA,
      blend_default = group$blend_default %||% NA,
      category_definition = enc2utf8(group$interpretation %||% ""),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  })
  do.call(rbind, rows)
}

bornholm_registry <- "apps/acceptance_model/registry.json"
trondelag_registry <- "apps/acceptance_model/registry_trondelag.json"
bornholm_assets <- "docs/geocontext/acceptance_framework/data/prototype_assets/asset_manifest.csv"
trondelag_assets <- "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/asset_manifest.csv"
trondelag_candidates_path <- "Trondelag/projects/trondelag/config/potential_app_layer_candidates.csv"

source_layers <- rbind(
  source_layer_rows("Bornholm", bornholm_registry, bornholm_assets),
  source_layer_rows("Trondelag", trondelag_registry, trondelag_assets)
)

group_definitions <- rbind(
  group_rows("Bornholm", bornholm_registry),
  group_rows("Trondelag", trondelag_registry)
)

category_definitions <- unique(group_definitions[, c(
  "region", "category_id", "category_label", "analysis_type", "analysis_definition", "category_definition"
)])

trondelag_candidates <- readr::read_csv(
  trondelag_candidates_path,
  show_col_types = FALSE,
  locale = readr::locale(encoding = "UTF-8")
)
trondelag_candidates <- data.frame(
  region = "Trondelag",
  source_scope = "candidate catalog; not necessarily wired in app",
  trondelag_candidates,
  check.names = FALSE
)

metadata <- data.frame(
  field = c(
    "generated_at",
    "root",
    "output",
    "bornholm_registry",
    "trondelag_registry",
    "bornholm_asset_manifest",
    "trondelag_asset_manifest",
    "trondelag_candidate_catalog",
    "note"
  ),
  value = c(
    format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"),
    root,
    output_path,
    bornholm_registry,
    trondelag_registry,
    bornholm_assets,
    trondelag_assets,
    trondelag_candidates_path,
    "Source layers are the app-wired source layers from the acceptance registries. Trondelag candidates are broader source candidates and may not be visible in the app."
  ),
  stringsAsFactors = FALSE
)

wb <- openxlsx::createWorkbook()

add_table_sheet <- function(wb, sheet_name, data) {
  openxlsx::addWorksheet(wb, sheet_name)
  openxlsx::writeDataTable(wb, sheet_name, data, tableStyle = "TableStyleMedium2")
  openxlsx::freezePane(wb, sheet_name, firstRow = TRUE)
  widths <- pmin(pmax(vapply(data, function(col) {
    max(nchar(as.character(col), type = "width", allowNA = FALSE), na.rm = TRUE)
  }, numeric(1)), nchar(names(data), type = "width") + 2), 70)
  widths[!is.finite(widths)] <- 12
  openxlsx::setColWidths(wb, sheet_name, cols = seq_along(data), widths = widths)
}

add_table_sheet(wb, "source_layers", source_layers)
add_table_sheet(wb, "category_definitions", category_definitions)
add_table_sheet(wb, "group_definitions", group_definitions)
add_table_sheet(wb, "trondelag_candidates", trondelag_candidates)
add_table_sheet(wb, "metadata", metadata)

dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
openxlsx::saveWorkbook(wb, output_path, overwrite = TRUE)

cat(output_path, "\n")
