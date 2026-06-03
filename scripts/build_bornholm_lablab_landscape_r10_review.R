suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
})

sf_use_s2(FALSE)

repo_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
repo_path <- function(...) file.path(repo_root, ...)

area_crs <- 25833
source_gpkg <- repo_path("data", "processed", "landskapsanalys_bornholm.gpkg")
source_layer_env <- Sys.getenv("BORNHOLM_LABLAB_SOURCE_LAYER", unset = "")
h3_grid_path <- repo_path(
  "docs", "geocontext", "model_comparisons", "bornholm_v10_landscape_types",
  "map", "bornholm_v10_landscape_types_map_data.geojson"
)
out_dir <- repo_path("data", "processed", "bornholm", "lablab_landscape_h3")
out_gpkg <- file.path(out_dir, "bornholm_lablab_landscape_r10_review.gpkg")
app_geojson <- file.path(out_dir, "bornholm_lablab_landscape_r10_app.geojson")
summary_csv <- file.path(out_dir, "bornholm_lablab_landscape_r10_review_summary.csv")
readme_path <- file.path(out_dir, "README.md")

if (!file.exists(source_gpkg)) {
  stop("Missing source GeoPackage: ", source_gpkg)
}
if (!file.exists(h3_grid_path)) {
  stop("Missing Bornholm R10 H3 grid: ", h3_grid_path)
}

layers <- st_layers(source_gpkg)
source_layer <- if (nzchar(source_layer_env)) source_layer_env else layers$name[[1]]
if (!source_layer %in% layers$name) {
  stop("Source layer not found in GeoPackage: ", source_layer)
}

message("Reading source layer: ", source_layer)
source <- st_read(source_gpkg, layer = source_layer, quiet = TRUE) |>
  st_make_valid()

if (!"Name" %in% names(source)) {
  stop("Expected a landscape type column named 'Name'. Found: ", paste(names(source), collapse = ", "))
}

landscape_type_id <- function(value) {
  value_norm <- tolower(trimws(as.character(value)))
  dplyr::case_when(
    grepl("klippigt", value_norm) ~ "LT01",
    grepl("sandigt", value_norm) ~ "LT02",
    grepl("jordbruks", value_norm) & grepl("sprick", value_norm) ~ "LT03",
    grepl("skogs", value_norm) & grepl("sprick", value_norm) ~ "LT04",
    grepl("sl.tt|slatt", value_norm) & grepl("jordbruks", value_norm) ~ "LT05",
    TRUE ~ NA_character_
  )
}

landscape_type_name <- function(type_id) {
  dplyr::case_when(
    type_id == "LT01" ~ "Klippigt kustlandskap",
    type_id == "LT02" ~ "Sandigt kustlandskap",
    type_id == "LT03" ~ "Jordbruks- och sprickdalslandskap",
    type_id == "LT04" ~ "Skogs- och sprickdalslandskap",
    type_id == "LT05" ~ "Slätt- och jordbrukslandskap",
    TRUE ~ "Okänd landskapstyp"
  )
}

type_colors <- tibble::tibble(
  landscape_type_id = c("LT01", "LT02", "LT03", "LT04", "LT05"),
  qgis_fill = c("#10c83e", "#d96a3a", "#22aeca", "#4930d6", "#e583d4")
)

source_25833 <- source |>
  st_transform(area_crs)
source_25833$source_area_m2 <- as.numeric(st_area(source_25833))
source_25833 <- source_25833 |>
  mutate(
    source_landscape_name = as.character(Name),
    landscape_type_id = landscape_type_id(source_landscape_name),
    landscape_type_name = landscape_type_name(landscape_type_id),
    source_feature_id = row_number(),
    source_review_flag = if_else(is.na(landscape_type_id), "unknown_source_name", "")
  ) |>
  left_join(type_colors, by = "landscape_type_id") |>
  select(
    source_feature_id,
    source_landscape_name,
    landscape_type_id,
    landscape_type_name,
    source_area_m2,
    source_review_flag,
    qgis_fill
  )

unknown <- source_25833 |>
  st_drop_geometry() |>
  filter(is.na(landscape_type_id))
if (nrow(unknown) > 0) {
  warning("Unknown landscape type names: ", paste(unique(unknown$source_landscape_name), collapse = "; "))
}

source_types_25833 <- source_25833 |>
  filter(!is.na(landscape_type_id)) |>
  group_by(landscape_type_id, landscape_type_name, qgis_fill) |>
  summarise(
    source_feature_count = n(),
    source_area_m2 = sum(source_area_m2, na.rm = TRUE),
    .groups = "drop"
  ) |>
  st_make_valid() |>
  st_collection_extract("POLYGON", warn = FALSE) |>
  st_cast("MULTIPOLYGON", warn = FALSE)

message("Reading app-compatible Bornholm H3 R10 grid")
h3_grid_source <- st_read(h3_grid_path, quiet = TRUE) |>
  st_make_valid() |>
  st_transform(area_crs)
h3_grid <- h3_grid_source |>
  select(hex_id, geometry)
h3_grid$hex_area_m2 <- as.numeric(st_area(h3_grid))

message("Selecting R10 hexes intersecting source polygons")
source_union <- st_union(source_types_25833)
hit_index <- st_intersects(h3_grid, source_union, sparse = TRUE)
h3_candidates <- h3_grid[lengths(hit_index) > 0, c("hex_id", "hex_area_m2")]
if (nrow(h3_candidates) == 0) {
  stop("No R10 H3 cells intersect the LABLAB source polygons.")
}

message("Intersecting ", nrow(h3_candidates), " R10 cells with LABLAB polygons")
intersection <- suppressWarnings(
  st_intersection(
    h3_candidates,
    source_types_25833 |>
      select(landscape_type_id, landscape_type_name, qgis_fill, source_feature_count)
  )
)
intersection <- st_collection_extract(intersection, "POLYGON", warn = FALSE)
intersection <- intersection[!st_is_empty(intersection), ]

if (nrow(intersection) == 0) {
  stop("No classified intersections found.")
}

intersection$intersection_area_m2 <- as.numeric(st_area(intersection))
intersection_detail <- intersection |>
  filter(intersection_area_m2 > 0.01) |>
  mutate(intersection_area_km2 = intersection_area_m2 / 1e6)

by_type <- intersection_detail |>
  st_drop_geometry() |>
  group_by(hex_id, hex_area_m2, landscape_type_id, landscape_type_name, qgis_fill) |>
  summarise(
    classified_area_m2 = sum(intersection_area_m2, na.rm = TRUE),
    source_feature_count = max(source_feature_count, na.rm = TRUE),
    .groups = "drop"
  )

totals <- by_type |>
  group_by(hex_id, hex_area_m2) |>
  summarise(
    total_classified_area_m2 = sum(classified_area_m2, na.rm = TRUE),
    type_count = n_distinct(landscape_type_id),
    .groups = "drop"
  )

ranked <- by_type |>
  arrange(hex_id, desc(classified_area_m2), landscape_type_id) |>
  group_by(hex_id) |>
  mutate(
    dominance_rank = row_number(),
    second_area_m2 = dplyr::lead(classified_area_m2, default = 0),
    second_type_id = dplyr::lead(landscape_type_id, default = NA_character_)
  ) |>
  ungroup()

dominant <- ranked |>
  filter(dominance_rank == 1) |>
  left_join(totals, by = c("hex_id", "hex_area_m2")) |>
  mutate(
    h3_resolution = 10L,
    dominant_area_m2 = classified_area_m2,
    dominant_area_km2 = dominant_area_m2 / 1e6,
    dominant_area_share_pct = if_else(total_classified_area_m2 > 0, dominant_area_m2 / total_classified_area_m2 * 100, 0),
    classified_hex_share_pct = if_else(hex_area_m2 > 0, total_classified_area_m2 / hex_area_m2 * 100, 0),
    review_flag_tie = !is.na(second_type_id) & abs(dominant_area_m2 - second_area_m2) <= pmax(1, dominant_area_m2 * 0.01),
    review_flag_low_dominance = type_count > 1 & dominant_area_share_pct < 60,
    review_flag_low_hex_coverage = classified_hex_share_pct < 25,
    review_flag_overlap_possible = total_classified_area_m2 > hex_area_m2 * 1.05,
    review_flag = mapply(
      function(tie, low_dominance, low_hex_coverage, overlap_possible) {
        flags <- c(
          if (isTRUE(tie)) "tie_or_near_tie" else character(),
          if (isTRUE(low_dominance)) "low_dominant_share" else character(),
          if (isTRUE(low_hex_coverage)) "low_hex_coverage" else character(),
          if (isTRUE(overlap_possible)) "classified_area_gt_hex_area" else character()
        )
        paste(flags, collapse = ";")
      },
      review_flag_tie,
      review_flag_low_dominance,
      review_flag_low_hex_coverage,
      review_flag_overlap_possible,
      USE.NAMES = FALSE
    )
  ) |>
  select(
    hex_id,
    h3_resolution,
    landscape_type_id,
    landscape_type_name,
    qgis_fill,
    dominant_area_m2,
    dominant_area_km2,
    dominant_area_share_pct,
    total_classified_area_m2,
    classified_hex_share_pct,
    hex_area_m2,
    type_count,
    second_type_id,
    second_area_m2,
    review_flag,
    review_flag_tie,
    review_flag_low_dominance,
    review_flag_low_hex_coverage,
    review_flag_overlap_possible
  ) |>
  left_join(h3_candidates |> select(hex_id), by = "hex_id") |>
  st_as_sf(crs = area_crs)

intersection_detail <- intersection_detail |>
  select(
    hex_id,
    landscape_type_id,
    landscape_type_name,
    qgis_fill,
    source_feature_count,
    intersection_area_m2,
    intersection_area_km2,
    hex_area_m2
  )

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
write_gpkg <- TRUE
if (file.exists(out_gpkg)) {
  write_gpkg <- isTRUE(file.remove(out_gpkg))
  if (!write_gpkg) {
    warning("Could not overwrite review GeoPackage, probably because it is open in QGIS: ", out_gpkg)
  }
}
if (file.exists(app_geojson)) {
  invisible(file.remove(app_geojson))
}

legacy_context <- h3_grid_source |>
  st_drop_geometry() |>
  transmute(
    hex_id,
    class_k8,
    class_km = class_k8,
    F1,
    F2,
    F3,
    F4,
    F5,
    legacy_v10_type_id = v10_type_id,
    legacy_v10_type_name = v10_type_name,
    legacy_v10_confidence = v10_confidence
  )

app_landscape <- dominant |>
  left_join(legacy_context, by = "hex_id") |>
  mutate(
    v10_type_id = landscape_type_id,
    v10_type_name = landscape_type_name,
    v10_type_name_en = landscape_type_name,
    v10_confidence = if_else(nzchar(review_flag), paste0("LABLAB dominant; ", review_flag), "LABLAB dominant"),
    v10_rule = paste0(
      "Dominant LABLAB PDF-landskapstyp efter störst skärningsyta (",
      round(dominant_area_share_pct, 1),
      "% av klassad yta)."
    ),
    v10_rule_en = paste0(
      "Dominant LABLAB PDF landscape type by largest intersecting area (",
      round(dominant_area_share_pct, 1),
      "% of classified area)."
    ),
    landscape_type = landscape_type_name,
    landscape_source = "LABLAB PDF dominant R10"
  ) |>
  select(
    hex_id,
    h3_resolution,
    class_k8,
    class_km,
    F1,
    F2,
    F3,
    F4,
    F5,
    v10_type_id,
    v10_type_name,
    v10_type_name_en,
    v10_rule,
    v10_rule_en,
    v10_confidence,
    landscape_type_id,
    landscape_type_name,
    landscape_type,
    landscape_source,
    qgis_fill,
    dominant_area_m2,
    dominant_area_km2,
    dominant_area_share_pct,
    total_classified_area_m2,
    classified_hex_share_pct,
    hex_area_m2,
    type_count,
    second_type_id,
    second_area_m2,
    review_flag,
    review_flag_tie,
    review_flag_low_dominance,
    review_flag_low_hex_coverage,
    review_flag_overlap_possible,
    legacy_v10_type_id,
    legacy_v10_type_name,
    legacy_v10_confidence
  ) |>
  st_transform(4326)

if (write_gpkg) {
  message("Writing review GeoPackage: ", out_gpkg)
  st_write(source_25833, out_gpkg, layer = "lablab_polygons_25833", quiet = TRUE)
  st_write(source_types_25833, out_gpkg, layer = "lablab_type_polygons_25833", quiet = TRUE, append = TRUE)
  st_write(dominant, out_gpkg, layer = "h3_r10_dominant_landscape", quiet = TRUE, append = TRUE)
  st_write(intersection_detail, out_gpkg, layer = "h3_r10_landscape_intersections", quiet = TRUE, append = TRUE)
} else {
  message("Skipping review GeoPackage write because the existing file is locked: ", out_gpkg)
}

message("Writing app GeoJSON: ", app_geojson)
st_write(app_landscape, app_geojson, driver = "GeoJSON", quiet = TRUE)

summary <- bind_rows(
  tibble::tibble(metric = "source_gpkg", value = source_gpkg),
  tibble::tibble(metric = "source_layer", value = source_layer),
  tibble::tibble(metric = "source_crs", value = as.character(st_crs(source)$input)),
  tibble::tibble(metric = "processing_crs", value = paste0("EPSG:", area_crs)),
  tibble::tibble(metric = "source_features", value = as.character(nrow(source_25833))),
  tibble::tibble(metric = "source_landscape_types", value = as.character(nrow(source_types_25833))),
  tibble::tibble(metric = "h3_r10_candidate_hex", value = as.character(nrow(h3_candidates))),
  tibble::tibble(metric = "h3_r10_classified_hex", value = as.character(nrow(dominant))),
  tibble::tibble(metric = "app_geojson_hex", value = as.character(nrow(app_landscape))),
  tibble::tibble(metric = "dominant_review_flags", value = as.character(sum(nzchar(dominant$review_flag)))),
  tibble::tibble(metric = "output_gpkg", value = out_gpkg),
  tibble::tibble(metric = "app_geojson", value = app_geojson)
)
write.csv(summary, summary_csv, row.names = FALSE, fileEncoding = "UTF-8")

readme <- c(
  "# Bornholm LABLAB landscape H3 R10 review package",
  "",
  "Generated by `scripts/build_bornholm_lablab_landscape_r10_review.R`.",
  "",
  "## Source",
  "",
  paste0("- Source GeoPackage: `", source_gpkg, "`"),
  paste0("- Source layer: `", source_layer, "`"),
  paste0("- Source CRS read by sf: `", as.character(st_crs(source)$input), "`"),
  "- Processing CRS: `EPSG:25833`",
  "- H3 R10 grid source: `docs/geocontext/model_comparisons/bornholm_v10_landscape_types/map/bornholm_v10_landscape_types_map_data.geojson`",
  "",
  "## Output",
  "",
  paste0("- Review GeoPackage: `", out_gpkg, "`"),
  paste0("- App GeoJSON: `", app_geojson, "`"),
  "- Layer `lablab_polygons_25833`: source polygons transformed to `EPSG:25833` with type IDs.",
  "- Layer `lablab_type_polygons_25833`: source polygons dissolved by LABLAB landscape type.",
  "- Layer `h3_r10_dominant_landscape`: one dominant LABLAB landscape type per intersecting R10 hex.",
  "- Layer `h3_r10_landscape_intersections`: detailed polygon/hex intersections for QA.",
  paste0("- Summary CSV: `", summary_csv, "`"),
  "",
  "## Aggregation rule",
  "",
  "Each LABLAB polygon is intersected with the app-compatible Bornholm H3 R10 grid. If a hex intersects more than one LABLAB type, the type with the largest intersection area becomes the dominant type.",
  "",
  "The app GeoJSON uses LABLAB `landscape_type_id`/`landscape_type_name` as the public landscape type. The older v10 factor and cluster fields are retained only as internal compatibility fields for existing potential scoring.",
  "",
  "Important QA fields in `h3_r10_dominant_landscape`:",
  "",
  "- `dominant_area_m2`: area of the winning type inside the hex.",
  "- `dominant_area_share_pct`: winning type share of all classified LABLAB area inside the hex.",
  "- `classified_hex_share_pct`: classified LABLAB area as share of the full hex area.",
  "- `type_count`: number of LABLAB types present in the hex.",
  "- `review_flag`: flags ties/near-ties, low dominant share, low classified coverage, or possible overlaps.",
  "",
  "## QGIS review checklist",
  "",
  "1. Open `lablab_polygons_25833` and compare it against the original PDF/GIS-PDF.",
  "2. Open `h3_r10_dominant_landscape` and style by `landscape_type_id` or `qgis_fill`.",
  "3. Inspect rows where `review_flag` is not empty.",
  "4. Pay special attention to mixed coastal/edge hexes and the LT03/LT04 boundary.",
  "5. Do not wire this into the app until the R10 review layer has been checked in QGIS."
)
writeLines(readme, readme_path, useBytes = TRUE)

message("Wrote summary: ", summary_csv)
message("Wrote README: ", readme_path)
message("Wrote app GeoJSON: ", app_geojson)
