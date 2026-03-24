suppressPackageStartupMessages({
  library(dplyr)
  library(purrr)
  library(readr)
  library(scales)
  library(sf)
  library(stringr)
  library(tibble)
})

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
analysis_id <- "bornholm_vindacceptans_stage1_v4_res9"
landscape_analysis_id <- Sys.getenv(
  "LANDSKAPSANALYS_ACCEPTANCE_LANDSCAPE_ID",
  unset = "landskapsanalys_v3_2_contourterrain68_res9"
)

out_dir <- file.path(repo_root, "docs/geocontext/acceptance_framework/data", analysis_id)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

raw_hex_csv <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv")
hex_gpkg <- file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_hex_44_combined.gpkg")
landscape_hex_gpkg <- file.path(
  repo_root,
  "docs/geocontext/model_comparisons/data",
  landscape_analysis_id,
  paste0(landscape_analysis_id, "_hex.gpkg")
)
layer_config_csv <- file.path(repo_root, "script/semi_manual_r9/config/bornholm_r9_geocontext_layers.csv")
source(file.path(repo_root, "script", "semi_manual_r9", "lib", "subcategory_splits.R"))

acceptance_gpkg <- file.path(out_dir, paste0(analysis_id, "_hex.gpkg"))
summary_csv <- file.path(out_dir, paste0(analysis_id, "_summary.csv"))
criteria_csv <- file.path(out_dir, paste0(analysis_id, "_criteria.csv"))
metadata_csv <- file.path(out_dir, paste0(analysis_id, "_metadata.csv"))

if (!file.exists(raw_hex_csv)) {
  stop("Raw hex CSV not found: ", raw_hex_csv)
}
if (!file.exists(hex_gpkg)) {
  stop("Hex GPKG not found: ", hex_gpkg)
}
if (!file.exists(landscape_hex_gpkg)) {
  stop("Landscape hex GPKG not found: ", landscape_hex_gpkg)
}
if (!file.exists(layer_config_csv)) {
  stop("Layer config CSV not found: ", layer_config_csv)
}

rescale_01 <- function(x, from_low, from_high) {
  ifelse(
    is.infinite(x),
    1,
    pmin(pmax((x - from_low) / (from_high - from_low), 0), 1)
  )
}

reverse_rescale_01 <- function(x, to_zero, to_full) {
  ifelse(
    is.infinite(x),
    0,
    pmin(pmax((to_full - x) / (to_full - to_zero), 0), 1)
  )
}

nearest_distance_m <- function(from_points, to_features) {
  if (nrow(to_features) == 0) {
    return(rep(Inf, nrow(from_points)))
  }
  idx <- st_nearest_feature(from_points, to_features)
  as.numeric(st_distance(from_points, to_features[idx, ], by_element = TRUE))
}

layer_config <- read.csv(layer_config_csv, stringsAsFactors = FALSE)

layer_path <- function(layer_key) {
  path <- layer_config$source_path[layer_config$layer_key == layer_key][1]
  if (is.na(path) || !nzchar(path)) {
    stop("Could not find source path for layer_key: ", layer_key)
  }
  path
}

read_layer <- function(layer_key, label = layer_key) {
  path <- layer_path(layer_key)
  if (!file.exists(path)) {
    stop("Layer source not found for ", layer_key, ": ", path)
  }
  message("Reading ", label, " ...")
  obj <- st_read(path, quiet = TRUE)
  obj <- suppressWarnings(st_zm(obj, drop = TRUE, what = "ZM"))
  obj <- st_make_valid(obj)
  st_transform(obj, 32633)
}

read_layer_safe <- function(layer_key, label = layer_key) {
  tryCatch(
    read_layer(layer_key, label = label),
    error = function(e) {
      message("Skipping ", label, " because it could not be read: ", conditionMessage(e))
      NULL
    }
  )
}

clip_sf_to_mask <- function(x, mask_sf) {
  if (is.null(x) || nrow(x) == 0) {
    return(x)
  }
  clipped <- suppressWarnings(st_intersection(st_make_valid(x), mask_sf))
  clipped <- clipped[!st_is_empty(clipped), ]
  clipped <- clipped[as.numeric(st_area(clipped)) > 0, ]
  st_make_valid(clipped)
}

keep_geom_only <- function(x, source_label) {
  if (is.null(x) || nrow(x) == 0) {
    return(NULL)
  }
  st_sf(
    tibble(source = rep(source_label, length(st_geometry(x)))),
    geometry = st_geometry(x),
    crs = st_crs(x)
  )
}

bind_sf <- function(x) {
  x <- purrr::compact(x)
  if (length(x) == 0) {
    return(st_as_sf(tibble(source = character()), geometry = st_sfc(crs = 32633)))
  }
  do.call(rbind, x)
}

scenario_definitions <- tribble(
  ~scenario_id, ~scenario_label, ~settlement_clearance_m, ~transport_large_clearance_m, ~transport_medium_clearance_m, ~aviation_bird_clearance_m, ~electrical_max_distance_m, ~coastal_zone_hard_stop, ~grid_weight, ~clearance_weight, ~landscape_weight, ~description,
  "high_acceptance", "Hog acceptans", 250, 75, 25, 0, 7000, FALSE, 0.35, 0.45, 0.20, "Largest potential establishment area with 250 m to settlement or fastboende proxies, 75 m to large roads, 25 m to medium roads, and the widest electrical connection distance.",
  "medium_acceptance", "Mellan acceptans", 300, 100, 50, 0, 5000, TRUE, 0.35, 0.45, 0.20, "Middle scenario used as the new stage-1 default for acceptance v4, with the 3 km coastal zone as a hard stop but without the bird-collision rule.",
  "low_acceptance", "Lag acceptans", 600, 175, 100, 2000, 3000, TRUE, 0.35, 0.45, 0.20, "Smallest potential establishment area with 600 m to settlement or fastboende proxies, 175 m to large roads, 100 m to medium roads, the 3 km coastal zone, bird-collision clearance, and a tighter electrical-feasibility limit."
)

cluster_pref <- c(
  "1" = 0.10,
  "2" = 1.00,
  "3" = 0.35,
  "4" = 0.50,
  "5" = 0.25
)

scenario_columns <- c("high_acceptance", "medium_acceptance", "low_acceptance")
scenario_label_map <- setNames(scenario_definitions$scenario_label, scenario_definitions$scenario_id)

class_from_score <- function(score, allowed) {
  classes <- rep("Exkluderad", length(score))
  allowed_idx <- which(allowed & !is.na(score))
  if (length(allowed_idx) == 0) {
    return(classes)
  }

  bin_labels <- c("Lag", "Medel", "Hog", "Mycket hog")
  bin_index <- dplyr::ntile(score[allowed_idx], 4)
  classes[allowed_idx] <- bin_labels[bin_index]
  classes
}

compose_reason <- function(
  settlement,
  transport,
  culture,
  protected,
  military,
  aviation_approach,
  strand,
  coastal_zone,
  aviation_bird,
  electrical
) {
  reasons <- c()
  if (isTRUE(settlement)) reasons <- c(reasons, "For nara bosattning eller bebyggelse")
  if (isTRUE(transport)) reasons <- c(reasons, "For nara transportinfrastruktur")
  if (isTRUE(culture)) reasons <- c(reasons, "For nara kulturmiljo")
  if (isTRUE(protected)) reasons <- c(reasons, "I skyddat omrade")
  if (isTRUE(military)) reasons <- c(reasons, "I militart omrade")
  if (isTRUE(aviation_approach)) reasons <- c(reasons, "I inflygningszon")
  if (isTRUE(strand)) reasons <- c(reasons, "I strandskydd")
  if (isTRUE(coastal_zone)) reasons <- c(reasons, "I 3 km kustzone")
  if (isTRUE(aviation_bird)) reasons <- c(reasons, "For nara fagelkollisionszon")
  if (isTRUE(electrical)) reasons <- c(reasons, "For langt fran elinfrastruktur")
  if (length(reasons) == 0) {
    "Ingen blockerande regel utloste"
  } else {
    paste(reasons, collapse = "; ")
  }
}

raw_df <- read.csv(raw_hex_csv, check.names = FALSE)

signal_cols <- setdiff(names(raw_df), "hex_id")
active_ids <- raw_df$hex_id[rowSums(raw_df[, signal_cols, drop = FALSE], na.rm = TRUE) > 0]

landmass_sf <- read_layer("prekvart_bornholm", "Bornholm landmass") |>
  select(geometry) |>
  st_make_valid()
landmass_mask <- st_sf(mask_id = "bornholm_landmass", geometry = st_union(landmass_sf))

hex_sf <- st_read(hex_gpkg, quiet = TRUE) |>
  filter(hex_id %in% active_ids) |>
  st_transform(32633) |>
  st_make_valid() |>
  clip_sf_to_mask(landmass_mask)

hex_centroids <- st_point_on_surface(hex_sf)

landscape_sf <- st_read(landscape_hex_gpkg, layer = landscape_analysis_id, quiet = TRUE) |>
  st_transform(32633) |>
  select(
    hex_id,
    F1, F2, F3, F4, F5,
    class_km,
    gc_contour_mean_slope_deg,
    gc_high_agri_plateau_proxy
  )

hex_accept <- hex_sf |>
  left_join(st_drop_geometry(landscape_sf), by = "hex_id") |>
  left_join(
    raw_df |>
      select(
        hex_id,
        fastboendebefolkningmapinfo_count,
        markblokke_2026_bornholm_area_share,
        strandbeskyttelse_miljostyrelsen_gds_mat2_strandbeskyttelse_merge_bor_32_area_share,
        protected_areas_fredede_omrader_miljostyrelsen_st_mp_arealdata_fredede_omr_121224_diss_bor_32_area_share,
        natura_2000_bird_protection_area_share,
        natura_2000_habitat_areas_dai_area_share,
        natura_2000_ramsar_area_share,
        natura_2000_specially_designated_land_areas_area_share,
        natur_vildt_reservat_area_share,
        militara_omraden_plst_area_share,
        aviation_approach_zones_tst_area_share,
        aviation_bird_collision_zones_tst_area_share,
        pdk_kulturhistoriskbevaringsvaerdi_vedtaget_wfs_area_share,
        valuable_cultural_environment_slks_area_share,
        cultural_and_historical_conservation_values_kulturhistoriske_bevaringsvardier_pdk_kulturhistoriskebevaringsvardier_bor_32_area_share,
        power_substation_osm_power_substation_edit_jf_1812_bor_33_count,
        high_voltage_line_osm_high_voltage_line_jf_181224_bor_length_m,
        underground_cable_osm_underground_cable_land_jf_181224_bor_length_m,
        windturbine_rated_power_kw_ens_vindkraftanlaeg_bol_33_count
      ),
    by = "hex_id"
  )

population_pts <- read_layer_safe("fastboendebefolkningmapinfo", "population points")
buildings_low <- read_layer("buildings_low_gd_v_buildings_low_bol_33", "buildings low")
buildings_high <- read_layer("buildings_high_gd_v_buildings_high_bol_33", "buildings high")
built_centre <- read_layer("built_centre_gd_v_bykerne_built_centre_bol_33", "built centre")
built_low_selection <- read_layer("built_low_gd_v_buildings_low_selection_by_bol_33", "built low selection")

settlement_sf <- bind_sf(list(
  keep_geom_only(population_pts, "population"),
  keep_geom_only(buildings_low, "buildings_low"),
  keep_geom_only(buildings_high, "buildings_high"),
  keep_geom_only(built_centre, "built_centre"),
  keep_geom_only(built_low_selection, "built_low_selection")
))

roads_all <- read_layer_safe("roads_simplified_gd_v_vej_road_merged_bol_33", "transport roads")
roads_medium <- if (!is.null(roads_all) && nrow(roads_all) > 0) subset_source_by_split(roads_all, "vejkategor", "medium", "derived_road_class") else NULL
roads_large <- if (!is.null(roads_all) && nrow(roads_all) > 0) subset_source_by_split(roads_all, "vejkategor", "large", "derived_road_class") else NULL
roads_medium_sf <- bind_sf(list(keep_geom_only(roads_medium, "roads_medium")))
roads_large_sf <- bind_sf(list(keep_geom_only(roads_large, "roads_large")))
transport_sf <- bind_sf(list(
  roads_medium_sf,
  roads_large_sf
))
if (nrow(transport_sf) == 0 && !is.null(roads_all) && nrow(roads_all) > 0) {
  transport_sf <- bind_sf(list(keep_geom_only(roads_all, "roads_all")))
}

culture_sf <- bind_sf(list(
  keep_geom_only(read_layer("pdk_kulturhistoriskbevaringsvaerdi_vedtaget_wfs", "adopted cultural preservation"), "culture_vedtaget"),
  keep_geom_only(read_layer("valuable_cultural_environment_slks", "valuable cultural environment"), "culture_valuable"),
  keep_geom_only(read_layer("cultural_and_historical_conservation_values_kulturhistoriske_bevaringsvardier_pdk_kulturhistoriskebevaringsvardier_bor_32", "cultural historical conservation"), "culture_conservation")
))

protected_sf <- bind_sf(list(
  keep_geom_only(read_layer("protected_areas_fredede_omrader_miljostyrelsen_st_mp_arealdata_fredede_omr_121224_diss_bor_32", "protected areas"), "protected_areas"),
  keep_geom_only(read_layer("natura_2000_specially_designated_land_areas", "natura designated land"), "natura_designated"),
  keep_geom_only(read_layer("natura_2000_bird_protection", "natura bird protection"), "natura_bird"),
  keep_geom_only(read_layer("natura_2000_habitat_areas_dai", "natura habitat areas"), "natura_habitat"),
  keep_geom_only(read_layer("natura_2000_ramsar", "natura ramsar"), "natura_ramsar"),
  keep_geom_only(read_layer("natur_vildt_reservat", "nature and wildlife reserve"), "natur_vildt_reservat")
))

military_sf <- read_layer("militara_omraden_plst", "military areas")
aviation_approach_sf <- read_layer("aviation_approach_zones_tst", "aviation approach zones")
aviation_bird_sf <- read_layer("aviation_bird_collision_zones_tst", "aviation bird collision zones")
strand_sf <- read_layer("strandbeskyttelse_miljostyrelsen_gds_mat2_strandbeskyttelse_merge_bor_32", "strand protection")
coastal_zone_sf <- read_layer("coastal_zone_kystnarhedszonen_3_km_miljoministeriet_plst_pdk_kystnaerhedszone_polygon_bor_32", "3 km coastal zone")
substation_sf <- read_layer("power_substation_osm_power_substation_edit_jf_1812_bor_33", "power substations")
hv_line_sf <- read_layer("high_voltage_line_osm_high_voltage_line_jf_181224_bor", "high-voltage lines")
cable_sf <- read_layer("underground_cable_osm_underground_cable_land_jf_181224_bor", "underground cables")
wind_sf <- read_layer("windturbine_rated_power_kw_ens_vindkraftanlaeg_bol_33", "existing wind turbines")

intersects_protected <- lengths(st_intersects(hex_accept, protected_sf)) > 0
intersects_culture <- lengths(st_intersects(hex_accept, culture_sf)) > 0
intersects_military <- lengths(st_intersects(hex_accept, military_sf)) > 0
intersects_aviation_approach <- lengths(st_intersects(hex_accept, aviation_approach_sf)) > 0
intersects_aviation_bird <- lengths(st_intersects(hex_accept, aviation_bird_sf)) > 0
intersects_strand <- lengths(st_intersects(hex_accept, strand_sf)) > 0
intersects_coastal_zone <- lengths(st_intersects(hex_accept, coastal_zone_sf)) > 0

hex_accept <- hex_accept |>
  mutate(
    dist_to_settlement_m = nearest_distance_m(hex_centroids, settlement_sf),
    dist_to_road_medium_m = nearest_distance_m(hex_centroids, roads_medium_sf),
    dist_to_road_large_m = nearest_distance_m(hex_centroids, roads_large_sf),
    dist_to_transport_m = pmin(dist_to_road_medium_m, dist_to_road_large_m, na.rm = TRUE),
    dist_to_culture_m = nearest_distance_m(hex_centroids, culture_sf),
    dist_to_protected_m = nearest_distance_m(hex_centroids, protected_sf),
    dist_to_aviation_bird_m = nearest_distance_m(hex_centroids, aviation_bird_sf),
    dist_to_hv_line_m = nearest_distance_m(hex_centroids, hv_line_sf),
    dist_to_substation_m = nearest_distance_m(hex_centroids, substation_sf),
    dist_to_cable_m = nearest_distance_m(hex_centroids, cable_sf),
    dist_to_existing_wind_m = nearest_distance_m(hex_centroids, wind_sf),
    dist_to_electrical_m = pmin(dist_to_hv_line_m, dist_to_substation_m, dist_to_cable_m, dist_to_existing_wind_m, na.rm = TRUE),
    hard_exclusion_protected = intersects_protected,
    hard_exclusion_culture = intersects_culture,
    hard_exclusion_military = intersects_military,
    hard_exclusion_aviation_approach = intersects_aviation_approach,
    hard_exclusion_aviation_bird = intersects_aviation_bird,
    hard_exclusion_strand = intersects_strand,
    hard_exclusion_coastal_zone = intersects_coastal_zone
  )

plateau_cap <- quantile(hex_accept$gc_high_agri_plateau_proxy, 0.95, na.rm = TRUE)
plateau_cap <- ifelse(is.na(plateau_cap) || plateau_cap <= 0, 1, plateau_cap)
slope_cap <- quantile(hex_accept$gc_contour_mean_slope_deg, 0.95, na.rm = TRUE)
slope_cap <- ifelse(is.na(slope_cap) || slope_cap <= 0, 1, slope_cap)

hex_accept <- hex_accept |>
  mutate(
    score_settlement_clearance = rescale_01(dist_to_settlement_m, 250, 4000),
    score_transport_clearance = rescale_01(dist_to_transport_m, 25, 1500),
    score_culture_clearance = rescale_01(dist_to_culture_m, 0, 1500),
    score_protected_edge_clearance = rescale_01(dist_to_protected_m, 0, 1500),
    score_aviation_bird_clearance = rescale_01(dist_to_aviation_bird_m, 0, 2000),
    score_electrical_feasibility = reverse_rescale_01(dist_to_electrical_m, 0, 7000),
    score_landscape_cluster = dplyr::recode(as.character(class_km), !!!cluster_pref, .default = 0.5) |> as.numeric(),
    score_landscape_plateau = pmin(gc_high_agri_plateau_proxy / plateau_cap, 1),
    score_landscape_open_terrain = 1 - pmin(gc_contour_mean_slope_deg / slope_cap, 1),
    score_grid_proximity = score_electrical_feasibility,
    score_clearance =
      (
        0.30 * score_settlement_clearance +
        0.15 * score_transport_clearance +
        0.20 * score_culture_clearance +
        0.20 * score_protected_edge_clearance
      ) / 0.85,
    score_clearance_with_bird =
      0.30 * score_settlement_clearance +
      0.15 * score_transport_clearance +
      0.20 * score_culture_clearance +
      0.20 * score_protected_edge_clearance +
      0.15 * score_aviation_bird_clearance,
    score_landscape =
      0.60 * score_landscape_cluster +
      0.25 * score_landscape_plateau +
      0.15 * score_landscape_open_terrain
  )

for (i in seq_len(nrow(scenario_definitions))) {
  scenario <- scenario_definitions[i, ]
  scenario_id <- scenario$scenario_id[[1]]

  settlement_conflict_col <- paste0("conflict_settlement_", scenario_id)
  transport_conflict_col <- paste0("conflict_transport_", scenario_id)
  culture_conflict_col <- paste0("conflict_culture_", scenario_id)
  coastal_conflict_col <- paste0("conflict_coastal_zone_", scenario_id)
  aviation_bird_conflict_col <- paste0("conflict_aviation_bird_", scenario_id)
  electrical_conflict_col <- paste0("conflict_electrical_", scenario_id)
  allowed_col <- paste0("allowed_for_wind_", scenario_id)
  score_col <- paste0("acceptance_score_", scenario_id)
  class_col <- paste0("acceptance_class_", scenario_id)
  reason_col <- paste0("exclusion_reason_", scenario_id)
  exclusion_count_col <- paste0("blocking_rule_count_", scenario_id)

  settlement_conflict_vec <- hex_accept$dist_to_settlement_m <= scenario$settlement_clearance_m[[1]]
  transport_conflict_vec <-
    hex_accept$dist_to_road_large_m <= scenario$transport_large_clearance_m[[1]] |
    hex_accept$dist_to_road_medium_m <= scenario$transport_medium_clearance_m[[1]]
  culture_conflict_vec <- hex_accept$hard_exclusion_culture
  coastal_conflict_vec <- if (isTRUE(scenario$coastal_zone_hard_stop[[1]])) hex_accept$hard_exclusion_coastal_zone else rep(FALSE, nrow(hex_accept))
  aviation_bird_conflict_vec <- if (scenario$aviation_bird_clearance_m[[1]] <= 0) rep(FALSE, nrow(hex_accept)) else hex_accept$dist_to_aviation_bird_m <= scenario$aviation_bird_clearance_m[[1]]
  electrical_conflict_vec <- hex_accept$dist_to_electrical_m > scenario$electrical_max_distance_m[[1]]

  blocking_rule_count <- settlement_conflict_vec +
    transport_conflict_vec +
    culture_conflict_vec +
    hex_accept$hard_exclusion_protected +
    hex_accept$hard_exclusion_military +
    hex_accept$hard_exclusion_aviation_approach +
    hex_accept$hard_exclusion_strand +
    coastal_conflict_vec +
    aviation_bird_conflict_vec +
    electrical_conflict_vec

  allowed_vec <- blocking_rule_count == 0
  clearance_score_vec <- if (scenario$aviation_bird_clearance_m[[1]] > 0) hex_accept$score_clearance_with_bird else hex_accept$score_clearance
  score_vec <- if_else(
    allowed_vec,
    100 * (
      scenario$grid_weight[[1]] * hex_accept$score_grid_proximity +
      scenario$clearance_weight[[1]] * clearance_score_vec +
      scenario$landscape_weight[[1]] * hex_accept$score_landscape
    ),
    0
  )

  reason_vec <- pmap_chr(
    list(
      settlement_conflict_vec,
      transport_conflict_vec,
      culture_conflict_vec,
      hex_accept$hard_exclusion_protected,
      hex_accept$hard_exclusion_military,
      hex_accept$hard_exclusion_aviation_approach,
      hex_accept$hard_exclusion_strand,
      coastal_conflict_vec,
      aviation_bird_conflict_vec,
      electrical_conflict_vec
    ),
    compose_reason
  )

  hex_accept[[settlement_conflict_col]] <- settlement_conflict_vec
  hex_accept[[transport_conflict_col]] <- transport_conflict_vec
  hex_accept[[culture_conflict_col]] <- culture_conflict_vec
  hex_accept[[coastal_conflict_col]] <- coastal_conflict_vec
  hex_accept[[aviation_bird_conflict_col]] <- aviation_bird_conflict_vec
  hex_accept[[electrical_conflict_col]] <- electrical_conflict_vec
  hex_accept[[exclusion_count_col]] <- blocking_rule_count
  hex_accept[[allowed_col]] <- allowed_vec
  hex_accept[[score_col]] <- score_vec
  hex_accept[[class_col]] <- class_from_score(score_vec, allowed_vec)
  hex_accept[[reason_col]] <- reason_vec
}

hex_accept <- hex_accept |>
  mutate(
    allowed_for_wind_stage1 = allowed_for_wind_medium_acceptance,
    acceptance_score_stage1 = acceptance_score_medium_acceptance,
    acceptance_class_stage1 = acceptance_class_medium_acceptance,
    exclusion_reason = exclusion_reason_medium_acceptance
  )

criteria_base <- tribble(
  ~criterion_type, ~criterion_name, ~threshold_or_rule, ~role_in_model, ~source_logic,
  "Hard exclusion", "Cultural environment", "Exclude on overlap", "No-go", "Cultural preservation, valuable cultural environment, cultural-historical conservation",
  "Hard exclusion", "Protected nature", "Exclude on overlap", "No-go", "Protected areas, Natura designated land, Natura bird protection, Natura habitat, Ramsar, natur/vildt-reservat",
  "Hard exclusion", "Military areas", "Exclude on overlap", "No-go", "Military areas (PLST)",
  "Hard exclusion", "Aviation approach", "Exclude on overlap", "No-go", "Aviation approach zones (TST)",
  "Hard exclusion", "Strand protection", "Exclude on overlap", "No-go", "Strandbeskyttelse (MST/GDS)",
  "Feasibility", "Electrical proximity ranking", "Higher score close to <= 7 km", "Positive feasibility", "Nearest selected electrical infrastructure",
  "Soft preference", "Settlement clearance", "Higher score beyond 4 km from all settlement features", "Negative avoidance", "Distance to population and all building proxies",
  "Soft preference", "Transport clearance", "Higher score beyond 1.5 km from selected transport corridors", "Negative avoidance", "Distance to medium and large roads",
  "Soft preference", "Protected-edge clearance", "Higher score beyond 1.5 km", "Negative avoidance", "Distance to protected-nature polygons",
  "Soft preference", "Culture clearance", "Higher score beyond 1.5 km", "Negative avoidance", "Distance to cultural polygons",
  "Landscape context", "Landscape cluster compatibility", "Cluster 2 highest preference; clusters 1,3,4,5 increasingly constrained", "Contextual weighting", "Landscape-analysis cluster class",
  "Landscape context", "High agricultural plateau", "Higher score for elevated open plateau-like settings", "Contextual weighting", "gc_high_agri_plateau_proxy from v3.2",
  "Landscape context", "Open terrain", "Higher score for lower contour-derived slope", "Contextual weighting", "gc_contour_mean_slope_deg from v3.2"
)

criteria_df <- purrr::map_dfr(seq_len(nrow(scenario_definitions)), function(i) {
  scenario <- scenario_definitions[i, ]
  scenario_id <- scenario$scenario_id[[1]]

  scenario_specific <- tribble(
    ~criterion_type, ~criterion_name, ~threshold_or_rule, ~role_in_model, ~source_logic,
    "Hard exclusion", "Settlement proximity", paste0("Exclude at <= ", scenario$settlement_clearance_m[[1]], " m from settlement, housing and fastboende proxies"), "No-go within scenario", "Fastboende points, buildings low/high, built centre, built low selection",
    "Distance conflict", "Large roads clearance", paste0("Exclude at <= ", scenario$transport_large_clearance_m[[1]], " m from large roads"), "No-go within scenario", "Roads simplified using derived large road class",
    "Distance conflict", "Medium roads clearance", paste0("Exclude at <= ", scenario$transport_medium_clearance_m[[1]], " m from medium roads"), "No-go within scenario", "Roads simplified using derived medium road class",
    "Feasibility", "Electrical connection distance", paste0("Require <= ", scenario$electrical_max_distance_m[[1]], " m to nearest selected electrical infrastructure"), "Keep candidate area", "Minimum distance to high-voltage line, substation, underground cable or existing wind turbine"
  )

  if (isTRUE(scenario$coastal_zone_hard_stop[[1]])) {
    scenario_specific <- bind_rows(
      scenario_specific,
      tribble(
        ~criterion_type, ~criterion_name, ~threshold_or_rule, ~role_in_model, ~source_logic,
        "Hard exclusion", "3 km coastal zone", "Exclude on overlap with Kystnaerhedszonen 3 km", "No-go within scenario", "Coastal zone - Kystnaerhedszonen 3 km (Miljoministeriet / PLST)"
      )
    )
  }

  if (scenario$aviation_bird_clearance_m[[1]] > 0) {
    scenario_specific <- bind_rows(
      scenario_specific,
      tribble(
        ~criterion_type, ~criterion_name, ~threshold_or_rule, ~role_in_model, ~source_logic,
        "Distance conflict", "Aviation bird-collision clearance", paste0("Exclude at <= ", scenario$aviation_bird_clearance_m[[1]], " m from aviation bird-collision zones"), "No-go within scenario", "Aviation bird-collision zones (TST)",
        "Soft preference", "Aviation bird-collision clearance", "Higher score beyond 2 km", "Negative avoidance", "Distance to aviation bird-collision zones"
      )
    )
  }

  bind_rows(scenario_specific, criteria_base) |>
    mutate(
      scenario_id = scenario_id,
      scenario_label = scenario$scenario_label[[1]]
    ) |>
    select(scenario_id, scenario_label, everything())
})

summary_df <- purrr::map_dfr(seq_len(nrow(scenario_definitions)), function(i) {
  scenario <- scenario_definitions[i, ]
  scenario_id <- scenario$scenario_id[[1]]

  settlement_conflict_col <- paste0("conflict_settlement_", scenario_id)
  transport_conflict_col <- paste0("conflict_transport_", scenario_id)
  culture_conflict_col <- paste0("conflict_culture_", scenario_id)
  coastal_conflict_col <- paste0("conflict_coastal_zone_", scenario_id)
  aviation_bird_conflict_col <- paste0("conflict_aviation_bird_", scenario_id)
  electrical_conflict_col <- paste0("conflict_electrical_", scenario_id)
  allowed_col <- paste0("allowed_for_wind_", scenario_id)
  score_col <- paste0("acceptance_score_", scenario_id)
  class_col <- paste0("acceptance_class_", scenario_id)

  tibble(
    scenario_id = scenario_id,
    scenario_label = scenario$scenario_label[[1]],
    metric = c(
      "analysis_id",
      "landscape_analysis_id",
      "n_hex",
      "n_allowed",
      "allowed_share",
      "n_excluded",
      "excluded_share",
      "mean_acceptance_score_allowed",
      "median_acceptance_score_allowed",
      "high_or_very_high_count",
      "excluded_settlement",
      "excluded_transport",
      "excluded_culture",
      "excluded_protected",
      "excluded_military",
      "excluded_aviation_approach",
      "excluded_aviation_bird",
      "excluded_strand",
      "excluded_coastal_zone",
      "excluded_electrical"
    ),
    value = as.character(c(
      analysis_id,
      landscape_analysis_id,
      nrow(hex_accept),
      sum(hex_accept[[allowed_col]], na.rm = TRUE),
      mean(hex_accept[[allowed_col]], na.rm = TRUE),
      sum(!hex_accept[[allowed_col]], na.rm = TRUE),
      mean(!hex_accept[[allowed_col]], na.rm = TRUE),
      mean(hex_accept[[score_col]][hex_accept[[allowed_col]]], na.rm = TRUE),
      median(hex_accept[[score_col]][hex_accept[[allowed_col]]], na.rm = TRUE),
      sum(hex_accept[[class_col]] %in% c("Hog", "Mycket hog"), na.rm = TRUE),
      sum(hex_accept[[settlement_conflict_col]], na.rm = TRUE),
      sum(hex_accept[[transport_conflict_col]], na.rm = TRUE),
      sum(hex_accept$hard_exclusion_culture, na.rm = TRUE),
      sum(hex_accept$hard_exclusion_protected, na.rm = TRUE),
      sum(hex_accept$hard_exclusion_military, na.rm = TRUE),
      sum(hex_accept$hard_exclusion_aviation_approach, na.rm = TRUE),
      sum(hex_accept[[aviation_bird_conflict_col]], na.rm = TRUE),
      sum(hex_accept$hard_exclusion_strand, na.rm = TRUE),
      sum(hex_accept[[coastal_conflict_col]], na.rm = TRUE),
      sum(hex_accept[[electrical_conflict_col]], na.rm = TRUE)
    ))
  )
})

metadata_df <- scenario_definitions |>
  transmute(
    analysis_id = analysis_id,
    landscape_analysis_id = landscape_analysis_id,
    scenario_id,
    scenario_label,
    description,
    blocking_logic = paste0(
      "Settlement <= ", settlement_clearance_m, " m around settlement, housing and fastboende proxies; large roads <= ", transport_large_clearance_m,
      " m; medium roads <= ", transport_medium_clearance_m, " m; ",
      ifelse(coastal_zone_hard_stop, "3 km coastal zone overlap active; ", "3 km coastal zone not active; "),
      "aviation bird <= ", aviation_bird_clearance_m,
      " m only where the scenario activates it; electrical must be <= ", electrical_max_distance_m,
      " m; cultural environment, protected nature, military, aviation approach and strand remain overlap-based hard exclusions."
    ),
    scoring_logic = paste0(
      "Acceptance score = ",
      scales::percent(grid_weight, accuracy = 1), " electrical proximity + ",
      scales::percent(clearance_weight, accuracy = 1), " clearance + ",
      scales::percent(landscape_weight, accuracy = 1), " landscape context; score is zeroed when any blocking rule is triggered."
    )
  )

hex_out <- hex_accept |>
  mutate(
    acceptance_score_stage1 = round(acceptance_score_stage1, 1),
    acceptance_score_high_acceptance = round(acceptance_score_high_acceptance, 1),
    acceptance_score_medium_acceptance = round(acceptance_score_medium_acceptance, 1),
    acceptance_score_low_acceptance = round(acceptance_score_low_acceptance, 1),
    dist_to_settlement_m = round(dist_to_settlement_m, 0),
    dist_to_road_medium_m = round(dist_to_road_medium_m, 0),
    dist_to_road_large_m = round(dist_to_road_large_m, 0),
    dist_to_transport_m = round(dist_to_transport_m, 0),
    dist_to_culture_m = round(dist_to_culture_m, 0),
    dist_to_protected_m = round(dist_to_protected_m, 0),
    dist_to_aviation_bird_m = round(dist_to_aviation_bird_m, 0),
    dist_to_electrical_m = round(dist_to_electrical_m, 0),
    dist_to_hv_line_m = round(dist_to_hv_line_m, 0),
    dist_to_substation_m = round(dist_to_substation_m, 0),
    dist_to_cable_m = round(dist_to_cable_m, 0),
    dist_to_existing_wind_m = round(dist_to_existing_wind_m, 0)
  )

st_write(hex_out, acceptance_gpkg, layer = analysis_id, delete_layer = TRUE, quiet = TRUE)
write.csv(summary_df, summary_csv, row.names = FALSE)
write.csv(criteria_df, criteria_csv, row.names = FALSE)
write.csv(metadata_df, metadata_csv, row.names = FALSE)

message("Wrote acceptance layer outputs to: ", out_dir)
