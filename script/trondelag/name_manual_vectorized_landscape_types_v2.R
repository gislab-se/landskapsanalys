#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(tibble)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
input_gpkg <- "C:/gislab/data/ut_trondelag/landskapsanalys_trondelag.gpkg"
out_dir <- file.path(repo_root, "data/processed/trondelag/manual_vectorized_v2")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_gpkg <- file.path(out_dir, "landskapsanalys_trondelag_manual_layer_named_v2.gpkg")

type_catalog <- tribble(
  ~landscape_type_id, ~landscape_type_name_sv,
  "LT01", "Kustsl\u00e4ttslandskap",
  "LT02", "Fjordlandskap",
  "LT03", "Fjordn\u00e4ra jordbrukslandskap",
  "LT04", "Fj\u00e4lln\u00e4ra skogslandskap",
  "LT05", "Dalg\u00e5ngslandskap",
  "LT06", "L\u00e5gfj\u00e4llslandskap",
  "LT07", "H\u00f6gfj\u00e4llslandskap",
  "LT08", "Sj\u00f6- och v\u00e5tmarkslandskap",
  "LT09", "Vidstr\u00e4ckt fj\u00e4llandskap"
)

# This mapping uses the reviewed manual extraction layers as the source of truth.
# LT09 is intentionally split into two source layers/parts.
layer_map <- tribble(
  ~source_layer,              ~landscape_type_id, ~type_part, ~review_note,
  "vectorized5",              "LT01",             NA,         "manual extraction layer",
  "vectorized4",              "LT02",             NA,         "manual extraction layer",
  "vectorized3",              "LT03",             NA,         "manual extraction layer",
  "vectorized2",              "LT04",             NA,         "manual extraction layer",
  "dalgangslandskap",         "LT05",             NA,         "manual extraction layer",
  "1",                        "LT06",             NA,         "manual extraction layer",
  "vidstrackt_fjallandskap",  "LT08",             NA,         "manual extraction layer; layer name is kept as source metadata",
  "vectorized6",              "LT09",             "LT09_A",   "manual extraction layer; one of two LT09 parts",
  "vectorized",               "LT09",             "LT09_B",   "manual extraction layer; southeast/bottom LT09 part"
) |>
  left_join(type_catalog, by = "landscape_type_id")

read_one_layer <- function(source_layer) {
  st_read(input_gpkg, layer = source_layer, quiet = TRUE) |>
    st_make_valid() |>
    st_transform(25832) |>
    mutate(source_layer = source_layer, source_feature_id = row_number())
}

message("Reading manual source layers...")
parts <- bind_rows(lapply(layer_map$source_layer, read_one_layer)) |>
  left_join(layer_map, by = "source_layer") |>
  mutate(
    type_part = ifelse(is.na(type_part), landscape_type_id, type_part),
    assignment_method = "manual layer mapping v2",
    review_needed = FALSE
  )

parts$area_m2_calc <- as.numeric(st_area(parts))

message("Dissolving by landscape type and by LT09 parts...")
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

write.csv(layer_map, file.path(out_dir, "manual_layer_mapping_v2.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(summary, file.path(out_dir, "manual_layer_summary_v2.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(type_presence, file.path(out_dir, "type_presence_v2.csv"), row.names = FALSE, fileEncoding = "UTF-8")

readme <- c(
  "# Trondelag manual vectorized landscape types - v2",
  "",
  paste0("- Source GeoPackage: `", input_gpkg, "`"),
  paste0("- Output GeoPackage: `", out_gpkg, "`"),
  "",
  "## Principle",
  "",
  "This version trusts the reviewed manual extraction layers, not the earlier raster-majority assignment.",
  "LT09 is kept as two separate source parts: `LT09_A` from `vectorized6` and `LT09_B` from `vectorized`.",
  "",
  "## Layers",
  "",
  "- `manual_layer_parts`: original manual polygons with type names and source layer metadata.",
  "- `manual_layer_parts_dissolved`: dissolved by `type_part`, so LT09 remains split into A and B.",
  "- `landscape_types_dissolved`: dissolved by `landscape_type_id`, so LT09 becomes one type.",
  "- `type_presence_v2.csv`: attribute-only check of which LT01-LT09 types are present in the manual source layers.",
  "",
  "## Important QA",
  "",
  "LT07/Högfjällslandskap is listed in the type presence check. If it is absent, it was not present as a separate manual extraction layer in the input GeoPackage and should be extracted/reviewed separately rather than copied from another type.",
  "",
  "## Summary",
  "",
  paste(capture.output(print(as.data.frame(type_presence), row.names = FALSE)), collapse = "\n")
)
writeLines(enc2utf8(readme), file.path(out_dir, "README.md"), useBytes = TRUE)

message("Wrote: ", out_gpkg)
message("Wrote: ", file.path(out_dir, "manual_layer_mapping_v2.csv"))
message("Wrote: ", file.path(out_dir, "type_presence_v2.csv"))
