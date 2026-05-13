#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
})

sf::sf_use_s2(FALSE)

repo_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
in_gpkg <- file.path(
  repo_root,
  "data/processed/trondelag/manual_vectorized_v2/landskapsanalys_trondelag_manual_v2_with_lt07_candidate.gpkg"
)
out_dir <- file.path(repo_root, "data/processed/trondelag/manual_vectorized_v2")
out_gpkg <- file.path(out_dir, "landskapsanalys_trondelag_confirmed_lt09_split.gpkg")

parts <- st_read(in_gpkg, layer = "parts_with_lt07_candidate", quiet = TRUE) |>
  mutate(
    lt09_split_confirmed = landscape_type_id == "LT09",
    qa_note = case_when(
      landscape_type_id == "LT09" & type_part == "LT09_A" ~ "confirmed Vidsträckt fjällandskap part A",
      landscape_type_id == "LT09" & type_part == "LT09_B" ~ "confirmed Vidsträckt fjällandskap part B",
      landscape_type_id == "LT07" ~ "candidate; review because LT07 was absent as manual source layer",
      TRUE ~ "manual source layer"
    )
  )

parts_by_part <- parts |>
  group_by(landscape_type_id, landscape_type_name_sv, type_part, review_needed, lt09_split_confirmed, qa_note) |>
  summarise(
    source_layers = paste(unique(source_layer), collapse = "; "),
    n_source_polygons = n(),
    area_m2_calc = sum(area_m2_calc),
    .groups = "drop"
  ) |>
  st_make_valid()

types_dissolved <- parts |>
  group_by(landscape_type_id, landscape_type_name_sv) |>
  summarise(
    n_parts = n_distinct(type_part),
    source_layers = paste(unique(source_layer), collapse = "; "),
    n_source_polygons = n(),
    any_review_needed = any(review_needed),
    area_m2_calc = sum(area_m2_calc),
    .groups = "drop"
  ) |>
  st_make_valid()

summary <- parts_by_part |>
  st_drop_geometry() |>
  mutate(area_km2 = area_m2_calc / 1e6) |>
  select(landscape_type_id, landscape_type_name_sv, type_part, source_layers, n_source_polygons, area_km2, review_needed, lt09_split_confirmed, qa_note) |>
  arrange(landscape_type_id, type_part)

if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(parts, out_gpkg, layer = "parts", quiet = TRUE)
st_write(parts_by_part, out_gpkg, layer = "parts_by_type_part", append = TRUE, quiet = TRUE)
st_write(types_dissolved, out_gpkg, layer = "types_dissolved", append = TRUE, quiet = TRUE)
write.csv(summary, file.path(out_dir, "confirmed_lt09_split_summary.csv"), row.names = FALSE, fileEncoding = "UTF-8")

message("Wrote: ", out_gpkg)
message("Wrote: ", file.path(out_dir, "confirmed_lt09_split_summary.csv"))
