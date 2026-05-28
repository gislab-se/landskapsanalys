needed_packages <- c("dplyr", "sf", "mapview", "htmlwidgets")
missing_packages <- needed_packages[!vapply(needed_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop(
    "Missing R package(s): ", paste(missing_packages, collapse = ", "),
    "\nInstall with install.packages(c('dplyr', 'sf', 'mapview', 'htmlwidgets')) and rerun.",
    call. = FALSE
  )
}

suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
})

# Usage from the repository root:
#   Rscript scripts/render_bornholm_ivl_r9_mapviews.R
#
# Optional portable usage:
#   Rscript render_bornholm_ivl_r9_mapviews.R path/to/bornholm_ivl_r9_variables.csv path/to/hex.gpkg path/to/output_dir

repo_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
repo_path <- function(...) file.path(repo_root, ...)

args <- commandArgs(trailingOnly = TRUE)
csv_path <- if (length(args) >= 1) args[[1]] else repo_path(
  "docs", "geocontext", "exports", "bornholm_ivl_r9_variables",
  "bornholm_ivl_r9_variables.csv"
)
hex_gpkg <- if (length(args) >= 2) args[[2]] else repo_path(
  "docs", "geocontext", "model_comparisons", "data",
  "landskapsanalys_v3_2_contourterrain68_res9",
  "landskapsanalys_v3_2_contourterrain68_res9_hex.gpkg"
)
out_dir <- if (length(args) >= 3) args[[3]] else file.path(dirname(csv_path), "mapview")

csv_path <- normalizePath(csv_path, winslash = "/", mustWork = TRUE)
hex_gpkg <- normalizePath(hex_gpkg, winslash = "/", mustWork = TRUE)
out_dir <- normalizePath(out_dir, winslash = "/", mustWork = FALSE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

message("Reading IVL CSV: ", csv_path)
ivl <- read.csv(csv_path, stringsAsFactors = FALSE, check.names = FALSE)
ivl$hex_id <- as.character(ivl$hex_id)

message("Reading R9 hex geometry: ", hex_gpkg)
hex_layer <- sf::st_layers(hex_gpkg)$name[[1]]
hex <- sf::st_read(hex_gpkg, layer = hex_layer, quiet = TRUE) |>
  dplyr::select(hex_id) |>
  dplyr::mutate(hex_id = as.character(hex_id))

map_data <- hex |>
  dplyr::inner_join(ivl, by = "hex_id")

if (nrow(map_data) == 0) {
  stop("No matching hex_id values between geometry and CSV.", call. = FALSE)
}

if (!identical(sf::st_crs(map_data)$epsg, 4326L)) {
  map_data <- sf::st_transform(map_data, 4326)
}

message("Joined rows: ", nrow(map_data), " | CSV rows: ", nrow(ivl))

mapview::mapviewOptions(
  fgb = FALSE,
  legend = TRUE,
  homebutton = TRUE
)

palette_factor <- colorRampPalette(c("#2166ac", "#f7f7f7", "#b2182b"))(11)
palette_share <- colorRampPalette(c("#f7fcf5", "#74c476", "#00441b"))(9)
palette_water <- colorRampPalette(c("#f7fbff", "#6baed6", "#08306b"))(9)
palette_topography <- colorRampPalette(c("#ffffcc", "#fd8d3c", "#800026"))(9)
palette_context <- colorRampPalette(c("#f7f7f7", "#bdbdbd", "#252525"))(9)
palette_infra <- colorRampPalette(c("#ffffe5", "#fd8d3c", "#7f0000"))(9)

layer_groups <- list(
  "01_landscape_model" = list(
    title = "Landscape model",
    palette = palette_factor,
    layers = c(
      landscape_cluster_label = "Landscape cluster",
      dominant_positive_factor_label = "Dominant positive factor",
      dominant_positive_factor_score = "Dominant factor score",
      factor_f1_aeolian_low_coast = "F1 Aeolian / low coast",
      factor_f2_relief_valley_terrain = "F2 Relief / valley terrain",
      factor_f3_forest_protected_habitat = "F3 Forest / protected habitat",
      factor_f4_settlement_built_structure = "F4 Settlement / built structure",
      factor_f5_marine_sand_gravel_coast = "F5 Marine sand / gravel coast"
    )
  ),
  "02_settlement_access" = list(
    title = "Settlement and access",
    palette = palette_infra,
    layers = c(
      population_count = "Permanent population count",
      road_total_length_m = "Total road length",
      road_major_length_m = "Major road length",
      built_centre_share = "Built centre share",
      low_density_built_share = "Low density built share",
      industry_business_share = "Industry / business share"
    )
  ),
  "03_land_use_nature" = list(
    title = "Land use, nature and protection",
    palette = palette_share,
    layers = c(
      agricultural_land_share = "Agricultural land share",
      forest_share = "Forest share",
      protected_forest_share = "Protected forest share",
      ecology_connectivity_share = "Ecological connectivity share",
      protected_area_share = "Protected area share",
      natura_habitat_share = "Natura habitat share",
      natura_bird_protection_share = "Natura bird protection share"
    )
  ),
  "04_water_coast" = list(
    title = "Water and coast",
    palette = palette_water,
    layers = c(
      lake_share = "Lake share",
      wetland_share = "Wetland share",
      river_length_m = "River length",
      protected_watercourse_length_m = "Protected watercourse length",
      coastline_length_m = "Coastline length",
      coastal_zone_share = "Coastal zone share",
      sand_dune_share = "Sand dune share",
      strand_protection_share = "Strand protection share"
    )
  ),
  "05_culture_restrictions_energy" = list(
    title = "Culture, restrictions and energy infrastructure",
    palette = palette_infra,
    layers = c(
      cultural_historical_conservation_share = "Cultural historical conservation share",
      valuable_cultural_environment_share = "Valuable cultural environment share",
      military_area_share = "Military area share",
      aviation_approach_share = "Aviation approach share",
      high_voltage_line_length_m = "High voltage line length",
      wind_turbine_count = "Wind turbine count",
      solarpark_count = "Solar park count",
      power_substation_count = "Power substation count"
    )
  ),
  "06_topography_context" = list(
    title = "Topography and selected context variables",
    palette = palette_topography,
    layers = c(
      relief_m = "Relief",
      highest_point_m = "Highest point",
      contour_mean_elevation_m = "Contour mean elevation",
      contour_mean_slope_deg = "Contour mean slope",
      contour_valley_depth_max_m = "Contour valley depth max",
      context_k100_mean_agricultural_land_share = "k100 mean agricultural share",
      context_k100_std_agricultural_land_share = "k100 std agricultural share",
      context_k100_mean_forest_share = "k100 mean forest share",
      context_k100_std_forest_share = "k100 std forest share",
      context_k100_mean_population_count = "k100 mean population count",
      context_k100_std_population_count = "k100 std population count",
      context_k100_mean_relief_m = "k100 mean relief",
      context_k100_std_relief_m = "k100 std relief",
      context_k100_mean_coastal_zone_share = "k100 mean coastal zone share"
    )
  )
)

make_layer <- function(data, column, label, palette) {
  popup_cols <- unique(c("hex_id", "landscape_cluster_label", column))
  layer_data <- data[, popup_cols, drop = FALSE]

  if (is.character(layer_data[[column]])) {
    layer_data[[column]] <- factor(layer_data[[column]])
  }

  mapview::mapview(
    layer_data,
    zcol = column,
    layer.name = label,
    col.regions = palette,
    alpha.regions = 0.72,
    color = "#555555",
    lwd = 0.15,
    legend = TRUE
  )
}

save_group_map <- function(group_id, group_def) {
  layers <- group_def$layers
  layers <- layers[names(layers) %in% names(map_data)]
  if (length(layers) == 0) {
    warning("No available columns for map group: ", group_id)
    return(NULL)
  }

  message("Rendering ", group_id, " (", length(layers), " layers)")
  maps <- Map(
    function(column, label) make_layer(map_data, column, label, group_def$palette),
    names(layers),
    unname(layers)
  )
  combined <- if (length(maps) == 1) maps[[1]] else Reduce(`+`, maps)
  widget <- mapview:::mapview2leaflet(combined)

  out_file <- file.path(out_dir, paste0(group_id, ".html"))
  htmlwidgets::saveWidget(
    widget,
    file = out_file,
    selfcontained = FALSE,
    title = paste("Bornholm IVL R9 -", group_def$title)
  )
  out_file
}

out_files <- Map(save_group_map, names(layer_groups), layer_groups)
out_files <- unlist(out_files, use.names = FALSE)

index_path <- file.path(out_dir, "index.html")
links <- paste0(
  "<li><a href=\"", basename(out_files), "\">",
  tools::file_path_sans_ext(basename(out_files)),
  "</a></li>"
)
index_html <- c(
  "<!doctype html>",
  "<html>",
  "<head><meta charset=\"utf-8\"><title>Bornholm IVL R9 mapview maps</title></head>",
  "<body>",
  "<h1>Bornholm IVL R9 mapview maps</h1>",
  "<p>Each HTML file contains several toggleable layers. Open one file and use the layer control in the map.</p>",
  "<ul>",
  links,
  "</ul>",
  "<p>Source CSV: bornholm_ivl_r9_variables.csv. Geometry: landskapsanalys_v3_2_contourterrain68_res9_hex.gpkg.</p>",
  "</body>",
  "</html>"
)
writeLines(index_html, index_path, useBytes = TRUE)

message("Wrote map index: ", index_path)
message("Done.")
