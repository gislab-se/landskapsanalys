suppressPackageStartupMessages({
  library(dplyr)
  library(sf)
  library(terra)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
analysis_id <- "landskapsanalys_v3_2_contourterrain68_res9"
out_dir <- file.path(
  repo_root,
  "docs/geocontext/model_comparisons/data",
  analysis_id
)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
if (!dir.exists(out_dir)) {
  stop("Could not create output directory: ", out_dir)
}

base_input_csv <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv")
base_config_csv <- file.path(
  repo_root,
  "script/landskapsanalys/config/landskapsanalys_v2_1_geomweight58_res9_input_layers.csv"
)
hex_gpkg <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_hex_44_combined.gpkg")
contour_shp <- "C:/gislab/data/dataraw/SL01_from_usb/Geodatakatalog_SL01/Utkommande_SL01/UT_Bornholm_SL01/Basmap_BOR/DHM_hoejdekurver-topolines-250_BOR+_33.shp"

augmented_input_csv <- file.path(out_dir, paste0(analysis_id, "_raw_augmented.csv"))
augmented_config_csv <- file.path(out_dir, paste0(analysis_id, "_input_layers.csv"))
terrain_hex_gpkg <- file.path(out_dir, paste0(analysis_id, "_terrain_hex.gpkg"))
dem_tif <- file.path(out_dir, paste0(analysis_id, "_contour_dem_25m.tif"))
slope_tif <- file.path(out_dir, paste0(analysis_id, "_contour_slope_deg_25m.tif"))
valley_tif <- file.path(out_dir, paste0(analysis_id, "_contour_valley_depth_25m.tif"))

if (!file.exists(contour_shp)) {
  stop("Contour source not found: ", contour_shp)
}

raw_df <- read.csv(base_input_csv, check.names = FALSE)
config_df <- read.csv(base_config_csv, stringsAsFactors = FALSE)

relief_breaks <- c(5, 12.5)
height_breaks <- c(50, 95)

raw_df <- raw_df |>
  mutate(
    dhm_relief_flat_band = as.numeric(dhm_hoejdekurver_relief_m > 0 & dhm_hoejdekurver_relief_m <= relief_breaks[[1]]),
    dhm_relief_rolling_band = as.numeric(dhm_hoejdekurver_relief_m > relief_breaks[[1]] & dhm_hoejdekurver_relief_m <= relief_breaks[[2]]),
    dhm_relief_strong_band = as.numeric(dhm_hoejdekurver_relief_m > relief_breaks[[2]]),
    dhm_highest_point_low_band = as.numeric(dhm_hoejdekurver_highest_point_m > 0 & dhm_hoejdekurver_highest_point_m <= height_breaks[[1]]),
    dhm_highest_point_mid_band = as.numeric(dhm_hoejdekurver_highest_point_m > height_breaks[[1]] & dhm_hoejdekurver_highest_point_m <= height_breaks[[2]]),
    dhm_highest_point_high_band = as.numeric(dhm_hoejdekurver_highest_point_m > height_breaks[[2]])
  )

terrain_band_config <- tibble::tribble(
  ~gc_name, ~source_name, ~display_name, ~geometry_type, ~theme, ~selection_note,
  "gc_relief_flat_band", "dhm_relief_flat_band", "Relief band: flat to weak", "Continuous metric", "Topography", "Derived in v3.1 from relief values <= 5 m per hex to separate the flattest terrain from rolling and rugged inland.",
  "gc_relief_rolling_band", "dhm_relief_rolling_band", "Relief band: rolling", "Continuous metric", "Topography", "Derived in v3.1 from relief values 5-12.5 m per hex to represent intermediate rolling terrain.",
  "gc_relief_strong_band", "dhm_relief_strong_band", "Relief band: strong", "Continuous metric", "Topography", "Derived in v3.1 from relief values > 12.5 m per hex to emphasize the most rugged terrain.",
  "gc_highest_point_low_band", "dhm_highest_point_low_band", "Elevation band: low", "Continuous metric", "Topography", "Derived in v3.1 from highest contour value <= 50 m per hex to strengthen lowland and coastal settings.",
  "gc_highest_point_mid_band", "dhm_highest_point_mid_band", "Elevation band: mid", "Continuous metric", "Topography", "Derived in v3.1 from highest contour value 50-95 m per hex to strengthen intermediate plateau and inland levels.",
  "gc_highest_point_high_band", "dhm_highest_point_high_band", "Elevation band: high", "Continuous metric", "Topography", "Derived in v3.1 from highest contour value > 95 m per hex to strengthen the highest inland terrain."
)

message("Reading contour lines and active hex mask...")
hex_sf <- st_read(hex_gpkg, quiet = TRUE)
active_ids <- raw_df$hex_id[rowSums(raw_df[, setdiff(names(raw_df), "hex_id"), drop = FALSE], na.rm = TRUE) > 0]
hex_land <- hex_sf |>
  filter(hex_id %in% active_ids) |>
  st_transform(32633)

contours <- vect(contour_shp)
contours <- project(contours, "EPSG:32633")
contour_points <- as.points(contours)

land_mask <- vect(hex_land)
r_template <- rast(ext(land_mask), resolution = 25, crs = crs(contours))
r_template <- crop(r_template, land_mask)

message("Interpolating contour-derived DEM...")
dem <- interpIDW(r_template, contour_points, field = "hoejde", radius = 250)
dem <- mask(dem, land_mask)
writeRaster(dem, dem_tif, overwrite = TRUE)

message("Deriving slope and local valley depth...")
slope_deg <- terrain(dem, v = "slope", unit = "degrees", neighbors = 8)
local_mean <- focal(
  dem,
  w = matrix(1, nrow = 21, ncol = 21),
  fun = mean,
  na.rm = TRUE,
  fillvalue = NA
)
valley_depth <- ifel(local_mean > dem, local_mean - dem, 0)

writeRaster(slope_deg, slope_tif, overwrite = TRUE)
writeRaster(valley_depth, valley_tif, overwrite = TRUE)

message("Aggregating contour-derived terrain metrics to hex...")
hex_vect <- vect(hex_land)
elevation_mean <- extract(dem, hex_vect, fun = mean, na.rm = TRUE, ID = FALSE)[, 1]
slope_mean <- extract(slope_deg, hex_vect, fun = mean, na.rm = TRUE, ID = FALSE)[, 1]
valley_depth_max <- extract(valley_depth, hex_vect, fun = max, na.rm = TRUE, ID = FALSE)[, 1]

terrain_hex <- hex_land |>
  mutate(
    dem_contour_mean_elevation_m = elevation_mean,
    dem_contour_mean_slope_deg = slope_mean,
    dem_contour_valley_depth_max_m = valley_depth_max
  ) |>
  st_drop_geometry() |>
  select(
    hex_id,
    dem_contour_mean_elevation_m,
    dem_contour_mean_slope_deg,
    dem_contour_valley_depth_max_m
  )

agri_q90 <- quantile(raw_df$markblokke_2026_bornholm_area_share[raw_df$markblokke_2026_bornholm_area_share > 0], 0.9, na.rm = TRUE)
plateau_df <- raw_df |>
  left_join(terrain_hex, by = "hex_id") |>
  mutate(
    agri_signal = pmin(markblokke_2026_bornholm_area_share / agri_q90, 1),
    elevation_signal = pmin(pmax((dem_contour_mean_elevation_m - 45) / 55, 0), 1),
    low_slope_signal = 1 - pmin(pmax((dem_contour_mean_slope_deg - 4) / 8, 0), 1),
    dem_high_agri_plateau_proxy = agri_signal * sqrt(pmax(elevation_signal * low_slope_signal, 0))
  ) |>
  select(hex_id, dem_high_agri_plateau_proxy)

raw_df <- raw_df |>
  left_join(terrain_hex, by = "hex_id") |>
  left_join(plateau_df, by = "hex_id")

terrain_config <- tibble::tribble(
  ~gc_name, ~source_name, ~display_name, ~geometry_type, ~theme, ~selection_note,
  "gc_contour_mean_elevation_m", "dem_contour_mean_elevation_m", "Contour-derived mean elevation", "Continuous metric", "Topography", "Derived in v3.2 by interpolating a pseudo-DEM from original contour lines and aggregating mean elevation per hex.",
  "gc_contour_mean_slope_deg", "dem_contour_mean_slope_deg", "Contour-derived mean slope", "Continuous metric", "Topography", "Derived in v3.2 from the contour-interpolated pseudo-DEM to separate flatter plateau surfaces from steeper terrain.",
  "gc_contour_valley_depth_max_m", "dem_contour_valley_depth_max_m", "Contour-derived valley depth (local max)", "Continuous metric", "Topography", "Derived in v3.2 as local focal-mean minus DEM, summarized as the maximum valley-depth signal per hex to emphasize incised terrain and likely valley structure.",
  "gc_high_agri_plateau_proxy", "dem_high_agri_plateau_proxy", "High agricultural plateau proxy", "Continuous metric", "Land use", "Derived in v3.2 from agricultural share, contour-derived mean elevation and low contour-derived slope to strengthen elevated open farmland and plateau-like terrain."
)

config_augmented <- bind_rows(config_df, terrain_band_config, terrain_config)

write.csv(raw_df, augmented_input_csv, row.names = FALSE)
write.csv(config_augmented, augmented_config_csv, row.names = FALSE)
st_write(
  hex_land |>
    left_join(terrain_hex, by = "hex_id") |>
    left_join(plateau_df, by = "hex_id"),
  terrain_hex_gpkg,
  layer = analysis_id,
  delete_layer = TRUE,
  quiet = TRUE
)

Sys.setenv(
  LANDSKAPSANALYS_REPO_ROOT = repo_root,
  LANDSKAPSANALYS_ANALYSIS_ID = analysis_id,
  LANDSKAPSANALYS_ANALYSIS_SUBTITLE = "v3.2 contour-derived terrain surface + terrain bands, 68 lager, R9",
  LANDSKAPSANALYS_ARCHIVED_PREVIOUS_VERSION = "landskapsanalys_v3_1_terrainbands64_res9",
  LANDSKAPSANALYS_INPUT_CSV = augmented_input_csv,
  LANDSKAPSANALYS_CONFIG_CSV = augmented_config_csv,
  LANDSKAPSANALYS_OUT_DIR = out_dir,
  LANDSKAPSANALYS_WEIGHT_STRATEGY = "geometry_balanced_q99",
  LANDSKAPSANALYS_WEIGHT_QUANTILE = "0.99",
  LANDSKAPSANALYS_THEME_BALANCE_MODE = "within_geometry",
  LANDSKAPSANALYS_THEME_WEIGHT_SPEC = "Land use=1.60",
  LANDSKAPSANALYS_GEOMETRY_WEIGHT_SPEC = "Continuous metric=1.20",
  LANDSKAPSANALYS_LAYER_WEIGHT_SPEC = paste(
    "gc_agricultural_land_share=1.40;",
    "gc_relief_m=1.05;",
    "gc_highest_point_m=1.05;",
    "gc_contour_mean_elevation_m=1.10;",
    "gc_contour_mean_slope_deg=1.15;",
    "gc_contour_valley_depth_max_m=1.25;",
    "gc_high_agri_plateau_proxy=1.35"
  ),
  LANDSKAPSANALYS_WEIGHT_RESCALE_MODE = "n_input_layers",
  LANDSKAPSANALYS_WEIGHT_DESCRIPTION = paste(
    "Per-layer robust q99 scaling, theme-balanced aggregation within each geometry type,",
    "moderate agricultural-land priority, mild continuous-metric uplift,",
    "six terrain bands from relief and absolute height, and four contour-derived terrain metrics from an interpolated pseudo-DEM."
  ),
  LANDSKAPSANALYS_SOURCE_MODEL_NOTE = paste(
    "V3.2 bygger vidare pa v3.1 men lagger till en contour-derived terrain surface fran originalkurvorna.",
    "Syftet ar att gora plataytor, lutning och lokalt incisionerade dalgangar tydligare utan att lata den nuvarande modellen vila enbart pa relief och highest-point per hex."
  )
)

source(
  file.path(repo_root, "script/landskapsanalys/03_build_bornholm_r9_landskapsanalys_17lager_res9.R"),
  local = FALSE
)
