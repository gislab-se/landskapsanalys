suppressPackageStartupMessages({
  library(dplyr)
  library(tibble)
})

repo_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
repo_path <- function(...) file.path(repo_root, ...)

analysis_id <- "landskapsanalys_v3_2_contourterrain68_res9"
data_dir <- repo_path("docs", "geocontext", "model_comparisons", "data", analysis_id)
out_dir <- repo_path("docs", "geocontext", "exports", "bornholm_ivl_r9_variables")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

context_csv <- file.path(data_dir, paste0(analysis_id, "_points_with_context.csv"))
raw_csv <- file.path(data_dir, paste0(analysis_id, "_raw_augmented.csv"))
factor_scores_csv <- file.path(data_dir, paste0(analysis_id, "_factor_scores.csv"))
run_summary_csv <- file.path(data_dir, paste0(analysis_id, "_run_summary.csv"))

out_csv <- file.path(out_dir, "bornholm_ivl_r9_variables.csv")
out_codebook <- file.path(out_dir, "bornholm_ivl_r9_variables_codebook.csv")
out_summary <- file.path(out_dir, "bornholm_ivl_r9_variables_summary.csv")
out_excluded <- file.path(out_dir, "bornholm_ivl_r9_excluded_variables.csv")
out_notes <- file.path(out_dir, "bornholm_ivl_r9_variable_selection_notes.md")

stop_if_missing <- function(paths) {
  missing <- paths[!file.exists(paths)]
  if (length(missing) > 0) {
    stop("Missing required input files:\n", paste(missing, collapse = "\n"), call. = FALSE)
  }
}

require_columns <- function(frame, columns, frame_name) {
  missing <- setdiff(columns, names(frame))
  if (length(missing) > 0) {
    stop(
      "Missing expected columns in ", frame_name, ":\n",
      paste(missing, collapse = "\n"),
      call. = FALSE
    )
  }
}

rel_path <- function(path) {
  normalized <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(
    paste0("^", gsub("([\\^$.|?*+(){}\\[\\]\\\\])", "\\\\\\1", repo_root), "/?"),
    "",
    normalized
  )
}

stop_if_missing(c(context_csv, raw_csv, factor_scores_csv, run_summary_csv))

message("Reading R9 model inputs")
context <- read.csv(context_csv, stringsAsFactors = FALSE, check.names = FALSE)
raw <- read.csv(raw_csv, stringsAsFactors = FALSE, check.names = FALSE)
factor_scores <- read.csv(factor_scores_csv, stringsAsFactors = FALSE, check.names = FALSE)
run_summary <- read.csv(run_summary_csv, stringsAsFactors = FALSE, check.names = FALSE)

context_required <- c(
  "hex_id",
  "east",
  "north",
  "gc_fastboende_count",
  "gc_roads_medium_length_m",
  "gc_roads_large_length_m",
  "gc_built_centre_share",
  "gc_built_low_selection_share",
  "gc_industry_business_share",
  "gc_agricultural_land_share",
  "gc_forest_share",
  "gc_fredskov_share",
  "gc_lake_share",
  "gc_wetland_share",
  "gc_river_length_m",
  "gc_protected_watercourses_length_m",
  "gc_coastline_length_m",
  "gc_coastal_zone_share",
  "gc_sand_dune_share",
  "gc_ecology_connectivity_share",
  "gc_protected_areas_share",
  "gc_natura_habitat_areas_share",
  "gc_natura_bird_protection_share",
  "gc_strand_protection_share",
  "gc_cultural_historical_conservation_share",
  "gc_valuable_cultural_environment_share",
  "gc_military_areas_share",
  "gc_aviation_approach_share",
  "gc_relief_m",
  "gc_highest_point_m",
  "gc_contour_mean_elevation_m",
  "gc_contour_mean_slope_deg",
  "gc_contour_valley_depth_max_m",
  "mean_gc_agricultural_land_share_k100",
  "std_gc_agricultural_land_share_k100",
  "mean_gc_forest_share_k100",
  "std_gc_forest_share_k100",
  "mean_gc_fastboende_count_k100",
  "std_gc_fastboende_count_k100",
  "mean_gc_relief_m_k100",
  "std_gc_relief_m_k100",
  "mean_gc_coastal_zone_share_k100"
)

raw_required <- c(
  "hex_id",
  "roads_simplified_gd_v_vej_road_merged_bol_33_length_m_total",
  "high_voltage_line_osm_high_voltage_line_jf_181224_bor_length_m",
  "windturbine_rated_power_kw_ens_vindkraftanlaeg_bol_33_count",
  "solarparks_point_pdk_kpr_v_solcellspark_centroid_bor_32_count",
  "power_substation_osm_power_substation_edit_jf_1812_bor_33_count"
)

require_columns(context, context_required, rel_path(context_csv))
require_columns(raw, raw_required, rel_path(raw_csv))
require_columns(factor_scores, c("hex_id", "F1", "F2", "F3", "F4", "F5", "class_km"), rel_path(factor_scores_csv))

cluster_labels <- c(
  "1" = "Tätorts- och verksamhetskärnor",
  "2" = "Vardagslandskap med blandad bakgrundskaraktär",
  "3" = "Flygsands- och låglänta kuststråk",
  "4" = "Brant relief och dalpräglat inland",
  "5" = "Skogligt skyddsinland och habitatkärnor"
)

factor_labels <- c(
  factor_f1_aeolian_low_coast = "Flygsands- och låglänta kustmiljöer",
  factor_f2_relief_valley_terrain = "Brant relief och sprickdalspräglad terräng",
  factor_f3_forest_protected_habitat = "Skogligt skyddsinland och habitatkärnor",
  factor_f4_settlement_built_structure = "Bosättning och byggd struktur",
  factor_f5_marine_sand_gravel_coast = "Marina sand- och gruskuster"
)

context_selected <- context |>
  transmute(
    hex_id = as.character(hex_id),
    centroid_east_m = east,
    centroid_north_m = north,
    population_count = gc_fastboende_count,
    road_major_length_m = gc_roads_medium_length_m + gc_roads_large_length_m,
    built_centre_share = gc_built_centre_share,
    low_density_built_share = gc_built_low_selection_share,
    industry_business_share = gc_industry_business_share,
    agricultural_land_share = gc_agricultural_land_share,
    forest_share = gc_forest_share,
    protected_forest_share = gc_fredskov_share,
    lake_share = gc_lake_share,
    wetland_share = gc_wetland_share,
    river_length_m = gc_river_length_m,
    protected_watercourse_length_m = gc_protected_watercourses_length_m,
    coastline_length_m = gc_coastline_length_m,
    coastal_zone_share = gc_coastal_zone_share,
    sand_dune_share = gc_sand_dune_share,
    ecology_connectivity_share = gc_ecology_connectivity_share,
    protected_area_share = gc_protected_areas_share,
    natura_habitat_share = gc_natura_habitat_areas_share,
    natura_bird_protection_share = gc_natura_bird_protection_share,
    strand_protection_share = gc_strand_protection_share,
    cultural_historical_conservation_share = gc_cultural_historical_conservation_share,
    valuable_cultural_environment_share = gc_valuable_cultural_environment_share,
    military_area_share = gc_military_areas_share,
    aviation_approach_share = gc_aviation_approach_share,
    relief_m = gc_relief_m,
    highest_point_m = gc_highest_point_m,
    contour_mean_elevation_m = gc_contour_mean_elevation_m,
    contour_mean_slope_deg = gc_contour_mean_slope_deg,
    contour_valley_depth_max_m = gc_contour_valley_depth_max_m,
    context_k100_mean_agricultural_land_share = mean_gc_agricultural_land_share_k100,
    context_k100_std_agricultural_land_share = std_gc_agricultural_land_share_k100,
    context_k100_mean_forest_share = mean_gc_forest_share_k100,
    context_k100_std_forest_share = std_gc_forest_share_k100,
    context_k100_mean_population_count = mean_gc_fastboende_count_k100,
    context_k100_std_population_count = std_gc_fastboende_count_k100,
    context_k100_mean_relief_m = mean_gc_relief_m_k100,
    context_k100_std_relief_m = std_gc_relief_m_k100,
    context_k100_mean_coastal_zone_share = mean_gc_coastal_zone_share_k100
  )

raw_selected <- raw |>
  transmute(
    hex_id = as.character(hex_id),
    road_total_length_m = roads_simplified_gd_v_vej_road_merged_bol_33_length_m_total,
    high_voltage_line_length_m = high_voltage_line_osm_high_voltage_line_jf_181224_bor_length_m,
    wind_turbine_count = windturbine_rated_power_kw_ens_vindkraftanlaeg_bol_33_count,
    solarpark_count = solarparks_point_pdk_kpr_v_solcellspark_centroid_bor_32_count,
    power_substation_count = power_substation_osm_power_substation_edit_jf_1812_bor_33_count
  )

message("Building reduced IVL export")
export_frame <- factor_scores |>
  mutate(
    hex_id = as.character(hex_id),
    h3_resolution = 9L,
    landscape_cluster_v32 = as.integer(class_km),
    landscape_cluster_label = unname(cluster_labels[as.character(class_km)]),
    factor_f1_aeolian_low_coast = F1,
    factor_f2_relief_valley_terrain = F2,
    factor_f3_forest_protected_habitat = F3,
    factor_f4_settlement_built_structure = F4,
    factor_f5_marine_sand_gravel_coast = F5
  ) |>
  select(
    hex_id,
    h3_resolution,
    landscape_cluster_v32,
    landscape_cluster_label,
    factor_f1_aeolian_low_coast,
    factor_f2_relief_valley_terrain,
    factor_f3_forest_protected_habitat,
    factor_f4_settlement_built_structure,
    factor_f5_marine_sand_gravel_coast
  ) |>
  left_join(context_selected, by = "hex_id") |>
  left_join(raw_selected, by = "hex_id") |>
  relocate(centroid_east_m, centroid_north_m, .after = h3_resolution)

factor_columns <- names(factor_labels)
factor_values <- as.matrix(export_frame[, factor_columns, drop = FALSE])
dominant_idx <- max.col(factor_values, ties.method = "first")
dominant_score <- factor_values[cbind(seq_len(nrow(factor_values)), dominant_idx)]
export_frame$dominant_positive_factor <- ifelse(
  dominant_score > 0,
  names(factor_labels)[dominant_idx],
  NA_character_
)
export_frame$dominant_positive_factor_label <- ifelse(
  dominant_score > 0,
  unname(factor_labels[dominant_idx]),
  NA_character_
)
export_frame$dominant_positive_factor_score <- ifelse(dominant_score > 0, dominant_score, NA_real_)

export_frame <- export_frame |>
  relocate(
    dominant_positive_factor,
    dominant_positive_factor_label,
    dominant_positive_factor_score,
    .after = factor_f5_marine_sand_gravel_coast
  )

codebook <- tribble(
  ~column, ~group, ~description_sv, ~unit, ~source_file, ~source_column, ~interpretation_note,
  "hex_id", "Nyckel", "H3-cellens id på resolution 9.", "id", rel_path(factor_scores_csv), "hex_id", "Unik radnyckel.",
  "h3_resolution", "Nyckel", "H3-upplösning för raden.", "H3 resolution", "derived", "constant 9", "Alla rader är R9.",
  "centroid_east_m", "Geometri", "Hexagonens modellcentroid, östlig koordinat.", "meter", rel_path(context_csv), "east", "Koordinaterna kommer från modellens punktrepresentation, EPSG:25832.",
  "centroid_north_m", "Geometri", "Hexagonens modellcentroid, nordlig koordinat.", "meter", rel_path(context_csv), "north", "Koordinaterna kommer från modellens punktrepresentation, EPSG:25832.",
  "landscape_cluster_v32", "Landskapsmodell", "Klusterklass från v3.2/v4-landskapsmodellen.", "klass", rel_path(factor_scores_csv), "class_km", "Fem kluster baserade på faktorpoäng.",
  "landscape_cluster_label", "Landskapsmodell", "Tolkad svensk klusteretikett.", "text", "derived", "class_km", "Etiketter hämtade från v3.2/v4-rapportens tolkning.",
  "factor_f1_aeolian_low_coast", "Landskapsmodell", "Faktorpoäng: flygsands- och låglänta kustmiljöer.", "standardiserad faktorpoäng", rel_path(factor_scores_csv), "F1", "Högre värden betyder starkare uttryck av faktorn.",
  "factor_f2_relief_valley_terrain", "Landskapsmodell", "Faktorpoäng: brant relief och sprickdalspräglad terräng.", "standardiserad faktorpoäng", rel_path(factor_scores_csv), "F2", "Högre värden betyder starkare uttryck av faktorn.",
  "factor_f3_forest_protected_habitat", "Landskapsmodell", "Faktorpoäng: skogligt skyddsinland och habitatkärnor.", "standardiserad faktorpoäng", rel_path(factor_scores_csv), "F3", "Högre värden betyder starkare uttryck av faktorn.",
  "factor_f4_settlement_built_structure", "Landskapsmodell", "Faktorpoäng: bosättning och byggd struktur.", "standardiserad faktorpoäng", rel_path(factor_scores_csv), "F4", "Högre värden betyder starkare uttryck av faktorn.",
  "factor_f5_marine_sand_gravel_coast", "Landskapsmodell", "Faktorpoäng: marina sand- och gruskuster.", "standardiserad faktorpoäng", rel_path(factor_scores_csv), "F5", "Högre värden betyder starkare uttryck av faktorn.",
  "dominant_positive_factor", "Landskapsmodell", "Den faktor som har högst positiv faktorpoäng i hexagonen.", "text", "derived", "factor_*", "Tom om ingen faktorpoäng är positiv.",
  "dominant_positive_factor_label", "Landskapsmodell", "Svensk etikett för dominant positiv faktor.", "text", "derived", "factor_*", "Snabbtolkning, inte en egen modellklass.",
  "dominant_positive_factor_score", "Landskapsmodell", "Poängen för dominant positiv faktor.", "standardiserad faktorpoäng", "derived", "factor_*", "Kan användas för att se hur tydlig dominansen är.",
  "population_count", "Bebyggelse och tillgänglighet", "Antal fastboendepunkter i hexagonen.", "antal", rel_path(context_csv), "gc_fastboende_count", "Lokal R9-variabel.",
  "road_major_length_m", "Bebyggelse och tillgänglighet", "Sammanlagd längd av medelstora och stora vägar i hexagonen.", "meter", rel_path(context_csv), "gc_roads_medium_length_m + gc_roads_large_length_m", "Fångar större tillgänglighetsstruktur.",
  "built_centre_share", "Bebyggelse och tillgänglighet", "Andel av hexagonen som utgör bebyggelsecentrum.", "andel 0-1", rel_path(context_csv), "gc_built_centre_share", "Lokal R9-variabel.",
  "low_density_built_share", "Bebyggelse och tillgänglighet", "Andel låg eller gles bebyggelse enligt urvalslager.", "andel 0-1", rel_path(context_csv), "gc_built_low_selection_share", "Lokal R9-variabel.",
  "industry_business_share", "Bebyggelse och tillgänglighet", "Andel verksamhets- eller industriområde.", "andel 0-1", rel_path(context_csv), "gc_industry_business_share", "Lokal R9-variabel.",
  "agricultural_land_share", "Markanvändning", "Andel jordbruksmark/markblokke.", "andel 0-1", rel_path(context_csv), "gc_agricultural_land_share", "Lokal R9-variabel.",
  "forest_share", "Natur och vegetation", "Andel skog.", "andel 0-1", rel_path(context_csv), "gc_forest_share", "Lokal R9-variabel.",
  "protected_forest_share", "Natur och vegetation", "Andel fredskov/skyddad skog.", "andel 0-1", rel_path(context_csv), "gc_fredskov_share", "Lokal R9-variabel.",
  "lake_share", "Vatten och kust", "Andel sjö.", "andel 0-1", rel_path(context_csv), "gc_lake_share", "Lokal R9-variabel.",
  "wetland_share", "Vatten och kust", "Andel våtmark.", "andel 0-1", rel_path(context_csv), "gc_wetland_share", "Lokal R9-variabel.",
  "river_length_m", "Vatten och kust", "Längd vattendrag i hexagonen.", "meter", rel_path(context_csv), "gc_river_length_m", "Lokal R9-variabel.",
  "protected_watercourse_length_m", "Vatten och kust", "Längd skyddade vattendrag i hexagonen.", "meter", rel_path(context_csv), "gc_protected_watercourses_length_m", "Lokal R9-variabel.",
  "coastline_length_m", "Vatten och kust", "Kustlinjelängd i hexagonen.", "meter", rel_path(context_csv), "gc_coastline_length_m", "Lokal R9-variabel.",
  "coastal_zone_share", "Vatten och kust", "Andel som ligger inom kustnära zon.", "andel 0-1", rel_path(context_csv), "gc_coastal_zone_share", "Lokal R9-variabel.",
  "sand_dune_share", "Vatten och kust", "Andel sanddyn/flygsandsmiljö.", "andel 0-1", rel_path(context_csv), "gc_sand_dune_share", "Lokal R9-variabel.",
  "ecology_connectivity_share", "Natur och skydd", "Andel ekologisk förbindelse.", "andel 0-1", rel_path(context_csv), "gc_ecology_connectivity_share", "Lokal R9-variabel.",
  "protected_area_share", "Natur och skydd", "Andel skyddat område.", "andel 0-1", rel_path(context_csv), "gc_protected_areas_share", "Lokal R9-variabel.",
  "natura_habitat_share", "Natur och skydd", "Andel Natura 2000 habitatområde.", "andel 0-1", rel_path(context_csv), "gc_natura_habitat_areas_share", "Lokal R9-variabel.",
  "natura_bird_protection_share", "Natur och skydd", "Andel Natura 2000 fågelskyddsområde.", "andel 0-1", rel_path(context_csv), "gc_natura_bird_protection_share", "Lokal R9-variabel.",
  "strand_protection_share", "Planering och restriktion", "Andel strandbeskyddelse/strandskyddszon.", "andel 0-1", rel_path(context_csv), "gc_strand_protection_share", "Lokal R9-variabel.",
  "cultural_historical_conservation_share", "Kulturmiljö", "Andel kulturhistoriskt bevarandevärde.", "andel 0-1", rel_path(context_csv), "gc_cultural_historical_conservation_share", "Lokal R9-variabel.",
  "valuable_cultural_environment_share", "Kulturmiljö", "Andel värdefull kulturmiljö.", "andel 0-1", rel_path(context_csv), "gc_valuable_cultural_environment_share", "Lokal R9-variabel.",
  "military_area_share", "Planering och restriktion", "Andel militärt område.", "andel 0-1", rel_path(context_csv), "gc_military_areas_share", "Lokal R9-variabel.",
  "aviation_approach_share", "Planering och restriktion", "Andel inflygningszon/luftfartsrestriktion.", "andel 0-1", rel_path(context_csv), "gc_aviation_approach_share", "Lokal R9-variabel.",
  "relief_m", "Topografi", "Relief/höjdskillnad i hexagonen.", "meter", rel_path(context_csv), "gc_relief_m", "Lokal R9-variabel.",
  "highest_point_m", "Topografi", "Högsta höjdkurvs-/höjdvärde i hexagonen.", "meter", rel_path(context_csv), "gc_highest_point_m", "Lokal R9-variabel.",
  "contour_mean_elevation_m", "Topografi", "Konturhärledd medelhöjd.", "meter", rel_path(context_csv), "gc_contour_mean_elevation_m", "Lokal R9-variabel.",
  "contour_mean_slope_deg", "Topografi", "Konturhärledd medellutning.", "grader", rel_path(context_csv), "gc_contour_mean_slope_deg", "Lokal R9-variabel.",
  "contour_valley_depth_max_m", "Topografi", "Konturhärledd maximal lokal daldjupssignal.", "meter", rel_path(context_csv), "gc_contour_valley_depth_max_m", "Lokal R9-variabel.",
  "context_k100_mean_agricultural_land_share", "Omgivningskontext", "Genomsnittlig jordbruksandel i modellens k100-omgivning.", "andel 0-1", rel_path(context_csv), "mean_gc_agricultural_land_share_k100", "`mean` betyder genomsnittlig omgivningskaraktär, inte lokal hexandel.",
  "context_k100_std_agricultural_land_share", "Omgivningskontext", "Variation i jordbruksandel i modellens k100-omgivning.", "andel 0-1", rel_path(context_csv), "std_gc_agricultural_land_share_k100", "`std` betyder omgivningens heterogenitet; högre värden antyder mer blandad övergångszon.",
  "context_k100_mean_forest_share", "Omgivningskontext", "Genomsnittlig skogsandel i modellens k100-omgivning.", "andel 0-1", rel_path(context_csv), "mean_gc_forest_share_k100", "`mean` betyder genomsnittlig omgivningskaraktär, inte lokal hexandel.",
  "context_k100_std_forest_share", "Omgivningskontext", "Variation i skogsandel i modellens k100-omgivning.", "andel 0-1", rel_path(context_csv), "std_gc_forest_share_k100", "`std` betyder omgivningens heterogenitet; högre värden antyder mer blandad övergångszon.",
  "context_k100_mean_population_count", "Omgivningskontext", "Genomsnittligt fastboendeantal i modellens k100-omgivning.", "antal", rel_path(context_csv), "mean_gc_fastboende_count_k100", "`mean` beskriver omgivande bosättningsintensitet.",
  "context_k100_std_population_count", "Omgivningskontext", "Variation i fastboendeantal i modellens k100-omgivning.", "antal", rel_path(context_csv), "std_gc_fastboende_count_k100", "`std` beskriver hur jämn eller ojämn bosättningsstrukturen är runt hexagonen.",
  "context_k100_mean_relief_m", "Omgivningskontext", "Genomsnittlig relief i modellens k100-omgivning.", "meter", rel_path(context_csv), "mean_gc_relief_m_k100", "`mean` beskriver omgivande topografisk karaktär.",
  "context_k100_std_relief_m", "Omgivningskontext", "Variation i relief i modellens k100-omgivning.", "meter", rel_path(context_csv), "std_gc_relief_m_k100", "`std` beskriver om omgivningen är topografiskt homogen eller kontrastfylld.",
  "context_k100_mean_coastal_zone_share", "Omgivningskontext", "Genomsnittlig kustzonsandel i modellens k100-omgivning.", "andel 0-1", rel_path(context_csv), "mean_gc_coastal_zone_share_k100", "Behålls för att fånga bredare kustprägel runt hexagonen.",
  "road_total_length_m", "Bebyggelse och tillgänglighet", "Total väglängd i hexagonen.", "meter", rel_path(raw_csv), "roads_simplified_gd_v_vej_road_merged_bol_33_length_m_total", "Lokal R9-variabel från råmatrisen.",
  "high_voltage_line_length_m", "Energiinfrastruktur", "Längd högspänningsledning i hexagonen.", "meter", rel_path(raw_csv), "high_voltage_line_osm_high_voltage_line_jf_181224_bor_length_m", "Observerad infrastruktur, inte potentialmodell.",
  "wind_turbine_count", "Energiinfrastruktur", "Antal befintliga vindkraftverkspunkter i hexagonen.", "antal", rel_path(raw_csv), "windturbine_rated_power_kw_ens_vindkraftanlaeg_bol_33_count", "Observerad infrastruktur, inte acceptansdata.",
  "solarpark_count", "Energiinfrastruktur", "Antal befintliga solparksobjekt i hexagonen.", "antal", rel_path(raw_csv), "solarparks_point_pdk_kpr_v_solcellspark_centroid_bor_32_count", "Observerad infrastruktur, inte potentialmodell.",
  "power_substation_count", "Energiinfrastruktur", "Antal elstationer i hexagonen.", "antal", rel_path(raw_csv), "power_substation_osm_power_substation_edit_jf_1812_bor_33_count", "Observerad infrastruktur."
) |>
  mutate(
    included_for_ivl = case_when(
      group == "Omgivningskontext" ~ "Behålls sparsamt för att beskriva landskapets närmiljö och heterogenitet.",
      group == "Landskapsmodell" ~ "Ger kompakt sammanfattning av många GIS-lager.",
      TRUE ~ "Direkt begriplig GIS-/geografivariabel som kan relateras till acceptanssvar."
    )
  )

missing_codebook <- setdiff(names(export_frame), codebook$column)
if (length(missing_codebook) > 0) {
  stop("Codebook is missing columns:\n", paste(missing_codebook, collapse = "\n"), call. = FALSE)
}
codebook <- codebook |> filter(column %in% names(export_frame))
codebook <- codebook[match(names(export_frame), codebook$column), ]

excluded <- tribble(
  ~category, ~examples, ~reason,
  "Acceptansdata", "acceptance_low, acceptance_medium, acceptance_high", "Exkluderas eftersom IVL själva ska samla in och analysera acceptans.",
  "R10-export och R10-derived parentfält", "bornholm_res10_hex_variables.csv, h3_parent_res9", "Exkluderas eftersom leveransen nu ska vara R9 och ha färre rader.",
  "Dubbla areaenheter", "*_area_m2, *_area_km2 när motsvarande *_share finns", "Andelar är lättare att jämföra mellan hexagoner; m2/km2 tas bara med om de är den enda relevanta enheten.",
  "Full kontextmatris", "mean_*_k10/k50/k250/k1000, std_*_k10/k50/k250/k1000", "För många och för modellnära variabler. Endast ett litet k100-urval behålls.",
  "Interna vikter och diagnostik", "total_raw, total_base, weight_*", "Bra för metodrevision men svårtolkat som externt forskningsunderlag.",
  "Detaljerade geologi-subtyper", "många jordart_* och prekvart_* delklasser", "Mestadels sammanfattade genom faktorer och ett fåtal mer direkta kust-/sandvariabler.",
  "Genererade potentialvariabler", "solar potential area, high_potential_share", "Hålls utanför för att skilja observerad GIS-kontext från senare potential- eller scenarioantaganden."
)

summary <- tibble(
  metric = c(
    "analysis_id",
    "rows",
    "columns",
    "unique_hex_id",
    "duplicate_hex_id",
    "source_model_n_hex",
    "excluded_zero_signal_hex",
    "missing_context_rows",
    "missing_raw_rows",
    "acceptance_columns_in_export",
    "context_mean_std_columns_in_export"
  ),
  value = as.character(c(
    analysis_id,
    nrow(export_frame),
    ncol(export_frame),
    length(unique(export_frame$hex_id)),
    anyDuplicated(export_frame$hex_id),
    run_summary$value[match("n_hex", run_summary$metric)],
    run_summary$value[match("excluded_zero_signal_hex", run_summary$metric)],
    sum(is.na(export_frame$centroid_east_m)),
    sum(is.na(export_frame$road_total_length_m)),
    sum(grepl("acceptance", names(export_frame), ignore.case = TRUE)),
    sum(grepl("^context_k100_(mean|std)_", names(export_frame)))
  ))
)

notes <- c(
  "# Bornholm IVL R9 variable selection",
  "",
  "Den här exporten är en smalare R9-version av Bornholms landskapsanalys, avsedd som GIS-/geografiunderlag till IVL:s acceptansundersökning.",
  "",
  "## Urvalsprinciper",
  "",
  "- Raderna är aktiva H3 R9-hexagoner från `landskapsanalys_v3_2_contourterrain68_res9`.",
  "- Acceptansvariabler är exkluderade eftersom IVL ska undersöka acceptans.",
  "- Area i m2/km2 är bortvald när en jämförbar `share`-variabel finns.",
  "- Fullständig kontextmatris och interna vikter är bortvalda för att filen ska vara begriplig externt.",
  "- Ett litet urval `mean`/`std` behålls eftersom omgivningskaraktär och heterogenitet kan vara analytiskt intressant för acceptans.",
  "",
  "## Hur `mean` och `std` ska läsas",
  "",
  "`mean` beskriver genomsnittlig omgivningskontext runt hexagonen, till exempel genomsnittlig skogsandel i modellens k100-omgivning. Det är alltså inte samma sak som hexagonens lokala skogsandel.",
  "",
  "`std` beskriver variation eller heterogenitet i samma omgivning. Ett högt `std` betyder ofta att hexagonen ligger i en blandad zon eller övergångszon, medan lågt `std` antyder en mer homogen omgivning.",
  "",
  "`k100` är modellens k100-omgivning från landskapsanalysen. Den ska läsas som en modellbaserad närmiljöskala, inte som 100 meter eller exakt 100 hexagoner.",
  "",
  "## Filer",
  "",
  paste0("- CSV: `", rel_path(out_csv), "`"),
  paste0("- Kodbok: `", rel_path(out_codebook), "`"),
  paste0("- Exkluderingslista: `", rel_path(out_excluded), "`"),
  paste0("- Summering: `", rel_path(out_summary), "`")
)

message("Writing IVL export files")
write.csv(export_frame, out_csv, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(codebook, out_codebook, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(summary, out_summary, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(excluded, out_excluded, row.names = FALSE, fileEncoding = "UTF-8")
writeLines(notes, out_notes, useBytes = TRUE)

message("Wrote ", nrow(export_frame), " rows and ", ncol(export_frame), " columns to ", out_csv)
