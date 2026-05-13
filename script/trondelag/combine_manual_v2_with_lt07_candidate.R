#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
out_dir <- file.path(repo_root, "data/processed/trondelag/manual_vectorized_v2")
manual_gpkg <- file.path(out_dir, "landskapsanalys_trondelag_manual_layer_named_v2.gpkg")
lt07_gpkg <- file.path(out_dir, "trondelag_lt07_candidate_from_clean_class.gpkg")
out_gpkg <- file.path(out_dir, "landskapsanalys_trondelag_manual_v2_with_lt07_candidate.gpkg")

manual_parts <- st_read(manual_gpkg, layer = "manual_layer_parts", quiet = TRUE) |>
  st_transform(25832) |>
  mutate(review_needed = as.logical(review_needed))

lt07 <- st_read(lt07_gpkg, layer = "lt07_candidate", quiet = TRUE) |>
  st_transform(25832) |>
  mutate(
    source_layer = "lt07_candidate_from_clean_class",
    source_feature_id = row_number(),
    type_part = "LT07_CANDIDATE",
    review_note = "candidate added because LT07 was absent from manual source layers",
    assignment_method = "clean class raster candidate",
    review_needed = TRUE
  )

common_cols <- c(
  "source_layer",
  "source_feature_id",
  "landscape_type_id",
  "landscape_type_name_sv",
  "type_part",
  "review_note",
  "assignment_method",
  "review_needed",
  "area_m2_calc"
)

manual_keep <- manual_parts |>
  mutate(area_m2_calc = as.numeric(st_area(manual_parts))) |>
  select(any_of(common_cols))

lt07_keep <- lt07 |>
  mutate(area_m2_calc = as.numeric(st_area(lt07))) |>
  select(any_of(common_cols))

combined_parts <- bind_rows(manual_keep, lt07_keep) |>
  st_make_valid()

by_part <- combined_parts |>
  group_by(landscape_type_id, landscape_type_name_sv, type_part, review_needed) |>
  summarise(
    source_layers = paste(unique(source_layer), collapse = "; "),
    n_source_polygons = n(),
    area_m2_calc = sum(area_m2_calc),
    .groups = "drop"
  ) |>
  st_make_valid()

by_type <- combined_parts |>
  group_by(landscape_type_id, landscape_type_name_sv) |>
  summarise(
    source_layers = paste(unique(source_layer), collapse = "; "),
    n_parts = n_distinct(type_part),
    n_source_polygons = n(),
    any_review_needed = any(review_needed),
    area_m2_calc = sum(area_m2_calc),
    .groups = "drop"
  ) |>
  st_make_valid()

summary <- by_part |>
  st_drop_geometry() |>
  mutate(area_km2 = area_m2_calc / 1e6) |>
  select(landscape_type_id, landscape_type_name_sv, type_part, source_layers, n_source_polygons, area_km2, review_needed) |>
  arrange(landscape_type_id, type_part)

if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(combined_parts, out_gpkg, layer = "parts_with_lt07_candidate", quiet = TRUE)
st_write(by_part, out_gpkg, layer = "parts_dissolved_with_lt07_candidate", append = TRUE, quiet = TRUE)
st_write(by_type, out_gpkg, layer = "landscape_types_9_dissolved", append = TRUE, quiet = TRUE)
write.csv(summary, file.path(out_dir, "manual_v2_with_lt07_candidate_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

message("Wrote: ", out_gpkg)
message("Types: ", nrow(st_drop_geometry(by_type)))
message("Parts: ", nrow(st_drop_geometry(by_part)))
