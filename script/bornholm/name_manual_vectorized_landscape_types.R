#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(tibble)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
input_gpkg <- Sys.getenv(
  "BORNHOLM_MANUAL_GPKG",
  "C:/gislab/data/ut_bornholm/landskapsanalys_bornholm.gpkg"
)
out_dir <- file.path(repo_root, "data/processed/bornholm/lablab_pdf_landscape/manual_vectorized")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

decision_csv <- Sys.getenv(
  "BORNHOLM_MANUAL_DECISIONS",
  file.path(out_dir, "manual_layer_review_decisions.csv")
)
out_gpkg <- file.path(out_dir, "landskapsanalys_bornholm_manual_layer_named.gpkg")

type_catalog <- tribble(
  ~landscape_type_id, ~landscape_type_name_sv,
  "LT01", "Klippigt kustlandskap",
  "LT02", "Sandigt kustlandskap",
  "LT03", "Jordbruksdominerat sprickdalslandskap",
  "LT04", "Skogskl\u00e4tt sprickdalslandskap",
  "LT05", "Sl\u00e4tt- och jordbrukslandskap"
)

write_decision_template <- function(layer_names = character()) {
  if (!length(layer_names)) {
    layer_names <- c(
      "LT01_klippigt_kustlandskap",
      "LT02_sandigt_kustlandskap",
      "LT03_jordbruksdominerat_sprickdalslandskap",
      "LT04_skogsklatt_sprickdalslandskap",
      "LT05_slatt_och_jordbrukslandskap"
    )
  }

  template <- tibble(
    include = TRUE,
    source_layer = layer_names,
    landscape_type_id = "",
    landscape_type_name_sv = "",
    type_part = "",
    needs_split = FALSE,
    review_note = ""
  )
  write.csv(template, decision_csv, row.names = FALSE, fileEncoding = "UTF-8")
  message("Wrote decision template: ", decision_csv)
}

if (!file.exists(input_gpkg)) {
  if (!file.exists(decision_csv)) {
    write_decision_template()
  }
  stop(
    "Manual QGIS GeoPackage not found: ", input_gpkg, "\n",
    "Create/review it in QGIS, or set BORNHOLM_MANUAL_GPKG to the reviewed GeoPackage.",
    call. = FALSE
  )
}

if (!file.exists(decision_csv)) {
  layers <- sf::st_layers(input_gpkg)$name
  write_decision_template(layers)
  stop(
    "Review decision CSV was missing, so a template was created from the GeoPackage layer names.\n",
    "Fill landscape_type_id/type_part/review_note and rerun.",
    call. = FALSE
  )
}

decisions <- read.csv(decision_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
required_cols <- c("source_layer", "landscape_type_id")
missing_cols <- setdiff(required_cols, names(decisions))
if (length(missing_cols)) {
  stop("Decision CSV missing required columns: ", paste(missing_cols, collapse = ", "), call. = FALSE)
}

if (!"include" %in% names(decisions)) decisions$include <- TRUE
include_flag <- tolower(trimws(as.character(decisions$include)))
decisions <- decisions[include_flag %in% c("true", "t", "1", "yes", "y"), , drop = FALSE]

decisions$source_layer <- trimws(decisions$source_layer)
decisions$landscape_type_id <- toupper(trimws(decisions$landscape_type_id))
if (!"type_part" %in% names(decisions)) decisions$type_part <- ""
if (!"review_note" %in% names(decisions)) decisions$review_note <- ""

if (any(!nzchar(decisions$source_layer))) {
  stop("Decision CSV has blank source_layer values.", call. = FALSE)
}
invalid_type <- setdiff(decisions$landscape_type_id, type_catalog$landscape_type_id)
if (length(invalid_type)) {
  stop("Decision CSV has invalid landscape_type_id values: ", paste(invalid_type, collapse = ", "), call. = FALSE)
}

decisions <- decisions |>
  select(source_layer, landscape_type_id, type_part, review_note, everything()) |>
  left_join(type_catalog, by = "landscape_type_id") |>
  mutate(
    type_part = ifelse(nzchar(type_part), type_part, landscape_type_id),
    assignment_method = "manual QGIS layer review decisions"
  )

available_layers <- sf::st_layers(input_gpkg)$name
missing_layers <- setdiff(decisions$source_layer, available_layers)
if (length(missing_layers)) {
  stop("Decision CSV references layers not found in GeoPackage: ", paste(missing_layers, collapse = ", "), call. = FALSE)
}

read_one_layer <- function(source_layer) {
  x <- st_read(input_gpkg, layer = source_layer, quiet = TRUE)
  if (is.na(st_crs(x))) {
    stop("Layer has no CRS and cannot be transformed safely: ", source_layer, call. = FALSE)
  }
  x |>
    st_make_valid() |>
    st_transform(25833) |>
    mutate(source_layer = source_layer, source_feature_id = row_number())
}

message("Reading reviewed manual source layers...")
parts <- bind_rows(lapply(decisions$source_layer, read_one_layer)) |>
  left_join(decisions, by = "source_layer")

parts$area_m2_calc <- as.numeric(st_area(parts))

message("Dissolving by landscape type and type part...")
by_type <- parts |>
  group_by(landscape_type_id, landscape_type_name_sv) |>
  summarise(
    n_source_layers = n_distinct(source_layer),
    n_source_polygons = n(),
    area_m2_calc = sum(area_m2_calc),
    assignment_method = "dissolved from manual_layer_parts",
    .groups = "drop"
  ) |>
  st_make_valid()

by_part <- parts |>
  group_by(landscape_type_id, landscape_type_name_sv, type_part) |>
  summarise(
    n_source_layers = n_distinct(source_layer),
    n_source_polygons = n(),
    area_m2_calc = sum(area_m2_calc),
    assignment_method = "dissolved from manual_layer_parts by type_part",
    .groups = "drop"
  ) |>
  st_make_valid()

summary <- parts |>
  st_drop_geometry() |>
  group_by(landscape_type_id, landscape_type_name_sv, type_part) |>
  summarise(
    source_layers = paste(unique(source_layer), collapse = "; "),
    n_polygons = n(),
    area_km2 = sum(area_m2_calc) / 1e6,
    review_notes = paste(unique(review_note[nzchar(review_note)]), collapse = "; "),
    .groups = "drop"
  ) |>
  arrange(landscape_type_id, type_part)

type_presence <- type_catalog |>
  left_join(
    summary |>
      group_by(landscape_type_id, landscape_type_name_sv) |>
      summarise(
        n_parts = n(),
        source_layers = paste(source_layers, collapse = "; "),
        n_polygons = sum(n_polygons),
        area_km2 = sum(area_km2),
        .groups = "drop"
      ),
    by = c("landscape_type_id", "landscape_type_name_sv")
  ) |>
  mutate(
    present_in_manual_layers = !is.na(n_polygons),
    n_parts = coalesce(n_parts, 0L),
    n_polygons = coalesce(n_polygons, 0L),
    area_km2 = coalesce(area_km2, 0),
    source_layers = coalesce(source_layers, "")
  )

if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(parts, out_gpkg, layer = "manual_layer_parts", quiet = TRUE)
st_write(by_part, out_gpkg, layer = "manual_layer_parts_dissolved", append = TRUE, quiet = TRUE)
st_write(by_type, out_gpkg, layer = "landscape_types_dissolved", append = TRUE, quiet = TRUE)

write.csv(decisions, file.path(out_dir, "manual_layer_mapping.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(summary, file.path(out_dir, "manual_layer_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(type_presence, file.path(out_dir, "type_presence.csv"), row.names = FALSE, fileEncoding = "UTF-8")

readme <- c(
  "# Bornholm manual vectorized LABLAB landscape types",
  "",
  paste0("- Source GeoPackage: `", input_gpkg, "`"),
  paste0("- Decision CSV: `", decision_csv, "`"),
  paste0("- Output GeoPackage: `", out_gpkg, "`"),
  "- Output CRS: `EPSG:25833`",
  "",
  "## Principle",
  "",
  "This script trusts the reviewed QGIS decision table, not raster colour guesses.",
  "Use it after manually reviewing/extracting the Bornholm LABLAB PDF landscape types.",
  "",
  "## Layers",
  "",
  "- `manual_layer_parts`: reviewed manual polygons with type names and source layer metadata.",
  "- `manual_layer_parts_dissolved`: dissolved by `type_part`.",
  "- `landscape_types_dissolved`: dissolved by `landscape_type_id`.",
  "- `type_presence.csv`: attribute-only check of which LT01-LT05 types are present.",
  "",
  "## Summary",
  "",
  paste(capture.output(print(as.data.frame(type_presence), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(readme), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", out_gpkg)
message("Wrote: ", file.path(out_dir, "manual_layer_mapping.csv"))
message("Wrote: ", file.path(out_dir, "type_presence.csv"))
