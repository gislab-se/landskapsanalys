suppressPackageStartupMessages({
  library(dplyr)
  library(h3jsr)
  library(sf)
})

sf_use_s2(FALSE)

args <- commandArgs(trailingOnly = FALSE)
file_arg <- "--file="
script_arg <- args[grepl(file_arg, args)]
if (length(script_arg) > 0) {
  script_path <- normalizePath(sub(file_arg, "", script_arg[[1]]), winslash = "/", mustWork = TRUE)
  repo_root <- normalizePath(file.path(dirname(script_path), "..", ".."), winslash = "/", mustWork = TRUE)
} else {
  repo_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
}

land_source <- file.path(repo_root, "data/raw/manual_extra_layers/shape format/Prekvart_Bornholm.shp")
out_dir <- file.path(repo_root, "docs/geocontext/potential_framework/data/bornholm_landmask")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rollups <- list(
  "9" = "docs/geocontext/potential_framework/data/bornholm_solar_potential_v0/h3_rollups/bornholm_solar_potential_res_9.csv",
  "8" = "docs/geocontext/potential_framework/data/bornholm_solar_potential_v0/h3_rollups/bornholm_solar_potential_res_8_rollup_from_res_9.csv",
  "7" = "docs/geocontext/potential_framework/data/bornholm_solar_potential_v0/h3_rollups/bornholm_solar_potential_res_7_rollup_from_res_9.csv",
  "6" = "docs/geocontext/potential_framework/data/bornholm_solar_potential_v0/h3_rollups/bornholm_solar_potential_res_6_rollup_from_res_9.csv"
)

read_land_mask <- function(path) {
  land <- st_read(path, quiet = TRUE) |>
    st_make_valid() |>
    st_union() |>
    st_as_sf()

  st_transform(land, 25832) |>
    mutate(mask_id = "bornholm_land")
}

build_clipped_hex <- function(hex_ids, land) {
  hex <- cell_to_polygon(hex_ids, simple = FALSE) |>
    rename(hex_id = h3_address) |>
    select(hex_id, geometry) |>
    st_make_valid() |>
    st_transform(25832)

  clipped <- suppressWarnings(st_intersection(hex, select(land, mask_id))) |>
    st_collection_extract("POLYGON", warn = FALSE) |>
    st_make_valid()

  if (nrow(clipped) == 0) {
    return(clipped)
  }

  clipped |>
    mutate(display_area_m2 = as.numeric(st_area(geometry))) |>
    filter(display_area_m2 > 1) |>
    select(hex_id, display_area_m2, geometry) |>
    st_transform(4326)
}

land <- read_land_mask(land_source)
land_path <- file.path(out_dir, "bornholm_landmask_wgs84.geojson")
st_write(st_transform(land, 4326), land_path, delete_dsn = TRUE, quiet = TRUE)
message("Wrote land mask: ", land_path)

for (resolution in names(rollups)) {
  source_path <- file.path(repo_root, rollups[[resolution]])
  source <- read.csv(source_path, colClasses = c(hex_id = "character"))
  clipped <- build_clipped_hex(unique(source$hex_id), land)

  out_path <- file.path(out_dir, paste0("bornholm_h3_res_", resolution, "_land_clipped.geojson"))
  st_write(clipped, out_path, delete_dsn = TRUE, quiet = TRUE)
  message("Wrote R", resolution, ": ", nrow(clipped), " clipped geometries -> ", out_path)
}
