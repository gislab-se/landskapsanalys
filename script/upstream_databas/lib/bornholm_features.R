get_pipeline_config <- function() {
  list(
    env_path = Sys.getenv("PIPELINE_ENV_PATH", ".env"),
    schema = Sys.getenv("PIPELINE_SCHEMA", "h3"),
    hex_table = Sys.getenv("HEX_TABLE", "bornholm_r8"),
    wind_layer = Sys.getenv("WIND_LAYER", "vindkraftanlaeg_historisk_indevaerende"),
    tab_pop = Sys.getenv("TAB_POP_PATH", ""),
    tab_curves = Sys.getenv("TAB_CURVES_PATH", ""),
    shp_nat = Sys.getenv("SHP_NAT_PATH", ""),
    gpkg_wind = Sys.getenv("GPKG_WIND_PATH", "")
  )
}

validate_input_files <- function(cfg) {
  named_paths <- c(
    tab_pop = cfg$tab_pop,
    tab_curves = cfg$tab_curves,
    shp_nat = cfg$shp_nat,
    gpkg_wind = cfg$gpkg_wind
  )

  missing_cfg <- names(named_paths)[named_paths == ""]
  if (length(missing_cfg) > 0) {
    stop("Missing required path env vars: ", paste(missing_cfg, collapse = ", "))
  }

  missing_files <- names(named_paths)[!file.exists(named_paths)]
  if (length(missing_files) > 0) {
    stop("Configured files do not exist: ", paste(missing_files, collapse = ", "))
  }
}

load_hex_grid <- function(con, schema, table) {
  sf::st_read(
    con,
    query = sprintf("SELECT h3 AS hex_id, geometry FROM %s.%s", schema, table),
    quiet = TRUE
  )
}

drop_z <- function(x) sf::st_zm(x, drop = TRUE, what = "ZM")

build_population <- function(hex, tab_pop) {
  pop <- sf::st_read(tab_pop, quiet = TRUE) |> drop_z() |> sf::st_transform(sf::st_crs(hex))

  if (!("Person" %in% names(pop))) {
    stop("Population file is missing expected column 'Person'.")
  }

  hits <- sf::st_intersects(hex, pop)
  persons <- vapply(
    hits,
    function(idx) if (length(idx) == 0) 0 else sum(pop$Person[idx], na.rm = TRUE),
    numeric(1)
  )

  hex |>
    sf::st_drop_geometry() |>
    dplyr::transmute(
      hex_id,
      persons = persons,
      persons_log = log1p(persons)
    )
}

build_elevation <- function(hex, tab_curves) {
  curves <- sf::st_read(tab_curves, quiet = TRUE) |> drop_z() |> sf::st_transform(sf::st_crs(hex))

  candidates <- c("Elevation", "ELEVATION", "elevation", "KOTE", "kote", "Hojde", "HOJDE", "height", "HEIGHT")
  elev_col <- candidates[candidates %in% names(curves)][1]

  if (is.na(elev_col)) {
    stop("Contours file is missing any recognized elevation column.")
  }

  hits <- sf::st_intersects(hex, curves)
  elev <- curves[[elev_col]]

  stats <- lapply(hits, function(idx) {
    if (length(idx) == 0) {
      return(c(min = NA_real_, max = NA_real_, mean = NA_real_))
    }
    vals <- elev[idx]
    c(min = min(vals, na.rm = TRUE), max = max(vals, na.rm = TRUE), mean = mean(vals, na.rm = TRUE))
  })

  m <- do.call(rbind, stats)

  hex |>
    sf::st_drop_geometry() |>
    dplyr::transmute(
      hex_id,
      elev_min = m[, "min"],
      elev_max = m[, "max"],
      elev_mean = m[, "mean"],
      relief = ifelse(is.na(elev_max - elev_min), 0, elev_max - elev_min)
    )
}

build_protected_share <- function(hex, shp_nat) {
  nat <- sf::st_read(shp_nat, quiet = TRUE) |> drop_z() |> sf::st_make_valid()

  nat_utm <- sf::st_transform(nat, 25832)
  hex_utm <- sf::st_transform(hex, 25832)
  nat_utm <- sf::st_crop(nat_utm, sf::st_bbox(hex_utm))

  ix <- suppressWarnings(sf::st_intersection(nat_utm, hex_utm |> dplyr::select(hex_id)))
  area_vals <- as.numeric(sf::st_area(sf::st_geometry(ix)))

  area_by_hex <- ix |>
    sf::st_drop_geometry() |>
    dplyr::mutate(area_m2 = area_vals) |>
    dplyr::group_by(hex_id) |>
    dplyr::summarise(protected_m2 = sum(area_m2), .groups = "drop")

  hex_area_m2 <- as.numeric(sf::st_area(sf::st_geometry(hex_utm)))

  hex_utm |>
    sf::st_drop_geometry() |>
    dplyr::left_join(area_by_hex, by = "hex_id") |>
    dplyr::mutate(
      protected_m2 = ifelse(is.na(protected_m2), 0, protected_m2),
      protected_share = protected_m2 / hex_area_m2
    ) |>
    dplyr::select(hex_id, protected_share)
}

build_wind <- function(hex, gpkg_wind, wind_layer) {
  hex_utm <- sf::st_transform(hex, 25832)
  hex_cent <- sf::st_centroid(sf::st_geometry(hex_utm))

  wind_utm <- sf::st_read(gpkg_wind, layer = wind_layer, quiet = TRUE) |>
    sf::st_zm(drop = TRUE) |>
    sf::st_transform(sf::st_crs(hex_utm)) |>
    sf::st_crop(sf::st_bbox(hex_utm))

  if (nrow(wind_utm) == 0) {
    stop("Wind layer has zero points after crop; check WIND_LAYER and source data.")
  }

  nearest_idx <- sf::st_nearest_feature(hex_cent, wind_utm)
  dist_m <- as.numeric(sf::st_distance(hex_cent, wind_utm[nearest_idx, ], by_element = TRUE))

  hits <- sf::st_intersects(hex_utm, wind_utm)
  n_turbines <- lengths(hits)

  hex_utm |>
    sf::st_drop_geometry() |>
    dplyr::transmute(
      hex_id,
      n_turbines = n_turbines,
      dist_to_nearest_turbine_m = dist_m,
      dist_turbine_log = log1p(dist_m)
    )
}

build_feature_matrix <- function(hex, hex_prot, hex_wind, hex_pop, hex_elev) {
  hex |>
    sf::st_drop_geometry() |>
    dplyr::select(hex_id) |>
    dplyr::left_join(hex_prot, by = "hex_id") |>
    dplyr::left_join(hex_wind, by = "hex_id") |>
    dplyr::left_join(hex_pop, by = "hex_id") |>
    dplyr::left_join(hex_elev, by = "hex_id") |>
    dplyr::mutate(
      protected_share = ifelse(is.na(protected_share), 0, protected_share),
      dist_turbine_log = ifelse(is.na(dist_turbine_log), NA_real_, dist_turbine_log)
    ) |>
    dplyr::select(hex_id, protected_share, dist_turbine_log, persons_log, relief)
}

write_tbl <- function(con, schema, table, df) {
  DBI::dbWriteTable(con, DBI::Id(schema = schema, table = table), df, overwrite = TRUE)
  DBI::dbExecute(con, sprintf("CREATE INDEX IF NOT EXISTS %s_hex_id_idx ON %s.%s(hex_id);", table, schema, table))
}

validate_feature_tables <- function(con, schema = "h3", hex_table = "bornholm_r8", feature_table = "bornholm_r8_features") {
  n_hex <- DBI::dbGetQuery(con, sprintf("SELECT COUNT(*) AS n FROM %s.%s;", schema, hex_table))$n[[1]]
  n_feat <- DBI::dbGetQuery(con, sprintf("SELECT COUNT(*) AS n FROM %s.%s;", schema, feature_table))$n[[1]]

  if (!isTRUE(n_hex == n_feat)) {
    stop(sprintf("Row count mismatch: %s.%s=%s vs %s.%s=%s", schema, hex_table, n_hex, schema, feature_table, n_feat))
  }

  missing_hex <- DBI::dbGetQuery(con, sprintf(
    "SELECT COUNT(*) AS n FROM %s.%s h LEFT JOIN %s.%s f ON h.h3 = f.hex_id WHERE f.hex_id IS NULL;",
    schema, hex_table, schema, feature_table
  ))$n[[1]]

  if (!isTRUE(missing_hex == 0)) {
    stop(sprintf("Validation failed: %s hex IDs missing in %s.%s", missing_hex, schema, feature_table))
  }

  invisible(list(n_hex = n_hex, n_feat = n_feat, missing_hex = missing_hex))
}
