suppressPackageStartupMessages({
  library(dplyr)
  library(jsonlite)
  library(sf)
  library(tibble)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript render_wind_acceptance_geometry_runtime.R <config_json> <output_dir>")
}

config_path <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
output_dir <- normalizePath(args[[2]], winslash = "/", mustWork = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

repo_root <- Sys.getenv("LANDSKAPSANALYS_REPO_ROOT", unset = "C:/gislab/landskapsanalys")
registry_path <- Sys.getenv(
  "ACCEPTANCE_REGISTRY_PATH",
  unset = file.path(repo_root, "apps", "acceptance_model", "registry.json")
)
source(file.path(repo_root, "script", "semi_manual_r9", "lib", "subcategory_splits.R"))
registry <- jsonlite::fromJSON(registry_path, simplifyVector = TRUE)
config <- jsonlite::fromJSON(config_path, simplifyVector = TRUE)
layer_config <- read.csv(file.path(repo_root, registry$source_config_csv), stringsAsFactors = FALSE)
asset_manifest_path <- file.path(repo_root, registry$asset_dir, "asset_manifest.csv")
asset_manifest <- if (file.exists(asset_manifest_path)) read.csv(asset_manifest_path, stringsAsFactors = FALSE) else data.frame()
working_epsg <- if (!is.null(registry$native_crs_epsg)) as.integer(registry$native_crs_epsg[[1]]) else 32633L
landmask_label <- if (!is.null(registry$landmask_label)) as.character(registry$landmask_label[[1]]) else "Bornholm landmass"
landmask_asset_candidates <- c(
  file.path(repo_root, registry$asset_dir, "landmask", "bornholm_landmass.rds"),
  file.path(repo_root, registry$asset_dir, "landmask", "bornholm_landmask.rds")
)

layer_path <- function(layer_key) {
  path <- layer_config$source_path[layer_config$layer_key == layer_key][1]
  if (is.na(path) || !nzchar(path) || !file.exists(path)) {
    stop("Layer source not found for layer_key: ", layer_key)
  }
  path
}

manifest_row_for_layer <- function(layer_id) {
  if (!nrow(asset_manifest)) {
    return(NULL)
  }
  rows <- asset_manifest[asset_manifest$layer_id == layer_id, , drop = FALSE]
  if (!nrow(rows)) {
    return(NULL)
  }
  rows[1, , drop = FALSE]
}

empty_sfc <- function() {
  st_sfc(crs = working_epsg)
}

repair_sfc <- function(geom, grid_size = 0.1) {
  geom_sfc <- if (inherits(geom, "sfc")) geom else st_sfc(geom, crs = working_epsg)
  if (length(geom_sfc) == 0) {
    return(empty_sfc())
  }

  valid_idx <- suppressWarnings(st_is_valid(geom_sfc))
  valid_idx[is.na(valid_idx)] <- FALSE
  if (all(valid_idx)) {
    return(geom_sfc)
  }

  geom_fixed <- geom_sfc
  if (any(!valid_idx)) {
    geom_fixed[!valid_idx] <- suppressWarnings(lwgeom::lwgeom_make_valid(geom_fixed[!valid_idx]))
  }

  valid_idx2 <- suppressWarnings(st_is_valid(geom_fixed))
  valid_idx2[is.na(valid_idx2)] <- FALSE
  if (all(valid_idx2)) {
    return(geom_fixed)
  }

  geom_retry <- st_set_precision(geom_fixed[!valid_idx2], grid_size)
  geom_retry <- lwgeom::st_snap_to_grid(geom_retry, size = grid_size)
  geom_fixed[!valid_idx2] <- suppressWarnings(lwgeom::lwgeom_make_valid(geom_retry))
  geom_fixed
}

repair_sf <- function(x, grid_size = 0.1) {
  if (nrow(x) == 0) {
    return(x)
  }
  st_geometry(x) <- repair_sfc(st_geometry(x), grid_size = grid_size)
  x
}

extract_polygonal <- function(geom) {
  geom_sfc <- repair_sfc(geom)
  if (length(geom_sfc) == 0) {
    return(empty_sfc())
  }
  geom_types <- as.character(st_geometry_type(geom_sfc, by_geometry = TRUE))
  keep_idx <- geom_types %in% c("POLYGON", "MULTIPOLYGON")
  if (any(keep_idx)) {
    return(repair_sfc(geom_sfc[keep_idx]))
  }
  extracted <- suppressWarnings(st_collection_extract(geom_sfc, "POLYGON"))
  if (length(extracted) > 0) {
    return(repair_sfc(extracted))
  }
  empty_sfc()
}

single_feature_polygonal <- function(geom) {
  polygonal_geom <- extract_polygonal(geom)
  if (length(polygonal_geom) == 0) {
    return(empty_sfc())
  }
  repair_sfc(st_union(polygonal_geom))
}

load_landmask <- function() {
  landmask_asset_path <- landmask_asset_candidates[file.exists(landmask_asset_candidates)][1]
  if (!is.na(landmask_asset_path) && nzchar(landmask_asset_path) && file.exists(landmask_asset_path)) {
    landmask_sf <- readRDS(landmask_asset_path)
    landmask_sf <- st_transform(landmask_sf, working_epsg)
    landmask_sf <- repair_sf(landmask_sf)
    landmask_sf <- landmask_sf[!st_is_empty(landmask_sf), ]
    if (nrow(landmask_sf) > 0) {
      return(st_sf(mask_id = landmask_label, geometry = repair_sfc(st_union(st_geometry(landmask_sf)))))
    }
  }

  landmask_key <- registry$landmask_layer_key[[1]]
  landmask_path <- layer_path(landmask_key)
  if (is.na(landmask_path) || !file.exists(landmask_path)) {
    stop("Landmask source not found for layer_key: ", landmask_key)
  }

  landmask_sf <- st_read(landmask_path, quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
  if (is.na(st_crs(landmask_sf))) {
    st_crs(landmask_sf) <- working_epsg
  }
  landmask_sf <- repair_sf(landmask_sf)
  landmask_sf <- st_transform(landmask_sf, working_epsg)
  landmask_union <- repair_sfc(st_union(st_geometry(landmask_sf)))
  st_sf(mask_id = landmask_label, geometry = landmask_union)
}

landmask_sf <- load_landmask()
landmask_geom <- st_geometry(landmask_sf)
landmask_area_m2 <- as.numeric(st_area(st_union(landmask_geom)))

geometry_land_share_pct <- function(geom) {
  geom_sfc <- repair_sfc(geom)
  if (length(geom_sfc) == 0) {
    return(0)
  }
  geom_union <- tryCatch(clip_geom_to_landmass(st_union(geom_sfc)), error = function(e) NULL)
  if (is.null(geom_union)) {
    return(0)
  }
  area_value <- suppressWarnings(as.numeric(st_area(geom_union)))
  if (length(area_value) == 0 || is.na(area_value)) {
    return(0)
  }
  round(area_value / landmask_area_m2 * 100, 1)
}

clip_geom_to_landmass <- function(geom) {
  geom_try1 <- repair_sfc(geom, grid_size = 0.1)
  landmask_try1 <- repair_sfc(landmask_geom, grid_size = 0.1)
  clipped <- tryCatch(
    suppressWarnings(st_intersection(geom_try1, landmask_try1)),
    error = function(e1) {
      geom_try2 <- repair_sfc(geom, grid_size = 1)
      landmask_try2 <- repair_sfc(landmask_geom, grid_size = 1)
      suppressWarnings(st_intersection(geom_try2, landmask_try2))
    }
  )
  repair_sfc(clipped, grid_size = 0.1)
}

clip_to_landmass <- function(x) {
  if (nrow(x) == 0) {
    return(x)
  }
  clipped_geom <- clip_geom_to_landmass(st_geometry(x))
  if (length(clipped_geom) == 0) {
    return(x[FALSE, , drop = FALSE])
  }
  st_sf(feature_id = seq_along(clipped_geom), geometry = clipped_geom)
}

apply_registry_filter <- function(source_sf, layer_row) {
  if (!"filter_field" %in% names(layer_row) || !"filter_value" %in% names(layer_row)) {
    return(source_sf)
  }

  filter_field <- as.character(layer_row$filter_field[[1]])
  filter_value <- unlist(layer_row$filter_value[[1]], use.names = FALSE)
  filter_mode <- if ("filter_mode" %in% names(layer_row)) as.character(layer_row$filter_mode[[1]]) else "field_equals"

  if (is.na(filter_field) || !nzchar(filter_field) || length(filter_value) == 0 || all(is.na(filter_value) | !nzchar(filter_value))) {
    return(source_sf)
  }

  subset_source_by_split(
    source_layer = source_sf,
    split_field = filter_field,
    split_value = filter_value,
    input_filter_mode = filter_mode
  )
}

read_layer_input <- function(layer_id) {
  manifest_row <- manifest_row_for_layer(layer_id)
  if (!is.null(manifest_row) && "analysis_rds_path" %in% names(manifest_row)) {
    analysis_rel <- manifest_row$analysis_rds_path[[1]]
    analysis_abs <- file.path(repo_root, analysis_rel)
    if (!is.na(analysis_rel) && nzchar(analysis_rel) && file.exists(analysis_abs)) {
      obj <- readRDS(analysis_abs)
      obj <- st_transform(obj, working_epsg)
      obj <- repair_sf(obj)
      obj <- obj[!st_is_empty(obj), ]
      base_buffer_m <- if ("analysis_base_buffer_m" %in% names(manifest_row)) suppressWarnings(as.numeric(manifest_row$analysis_base_buffer_m[[1]])) else 0
      if (is.na(base_buffer_m)) {
        base_buffer_m <- 0
      }
      return(list(sf = obj, base_buffer_m = base_buffer_m, already_clipped = TRUE))
    }
  }

  layer_row <- registry$layers[registry$layers$id == layer_id, ]
  if (nrow(layer_row) == 0) {
    stop("Layer id not found in registry: ", layer_id)
  }

  obj <- st_read(layer_path(layer_row$layer_key[[1]]), quiet = TRUE) |>
    suppressWarnings(st_zm(drop = TRUE, what = "ZM"))
  if (is.na(st_crs(obj))) {
    st_crs(obj) <- working_epsg
  }
  obj <- repair_sf(obj)
  obj <- st_transform(obj, working_epsg)
  obj <- apply_registry_filter(obj, layer_row)
  obj <- clip_to_landmass(obj)
  obj <- repair_sf(obj)
  obj <- obj[!st_is_empty(obj), ]
  list(sf = obj, base_buffer_m = 0, already_clipped = FALSE)
}

simplify_for_export <- function(x) {
  if (nrow(x) == 0) {
    return(x)
  }
  x <- repair_sf(x)
  x <- st_simplify(x, dTolerance = 20, preserveTopology = TRUE)
  st_transform(x, 4326)
}

combine_geometries <- function(items) {
  if (length(items) == 0) {
    return(empty_sfc())
  }
  geom_parts <- lapply(items, function(item) {
    if (inherits(item, "sf")) {
      extract_polygonal(st_geometry(item))
    } else {
      extract_polygonal(item)
    }
  })
  geom_parts <- Filter(function(item) length(item) > 0, geom_parts)
  if (length(geom_parts) == 0) {
    return(empty_sfc())
  }
  geom_vec <- do.call(c, geom_parts)
  single_feature_polygonal(geom_vec)
}

intersection_reduce <- function(geoms) {
  if (length(geoms) == 0) {
    return(empty_sfc())
  }

  out <- repair_sfc(geoms[[1]])
  if (length(geoms) == 1) {
    return(out)
  }

  for (i in 2:length(geoms)) {
    next_geom <- repair_sfc(geoms[[i]])
    out <- suppressWarnings(st_intersection(out, next_geom))
    out <- repair_sfc(out)
    if (length(out) == 0) {
      return(empty_sfc())
    }
  }
  out
}

prepare_layer_geometry <- function(layer_sf, analysis_kind, analysis_value_m, base_buffer_m = 0, already_clipped = FALSE, clip_to_landmass = TRUE) {
  layer_geom <- repair_sfc(st_union(st_geometry(layer_sf)))
  if (clip_to_landmass && !already_clipped) {
    layer_geom <- clip_geom_to_landmass(layer_geom)
  }
  if (length(layer_geom) == 0) {
    return(empty_sfc())
  }

  if (analysis_kind == "proximity_feasibility") {
    buffer_distance_m <- analysis_value_m
  } else {
    buffer_distance_m <- max(0, analysis_value_m - base_buffer_m)
  }

  if (buffer_distance_m > 0) {
    buffered_geom <- st_buffer(layer_geom, dist = buffer_distance_m, nQuadSegs = 4)
    if (clip_to_landmass) {
      return(extract_polygonal(clip_geom_to_landmass(buffered_geom)))
    }
    return(extract_polygonal(buffered_geom))
  }

  if (already_clipped || !clip_to_landmass) {
    return(extract_polygonal(layer_geom))
  }

  extract_polygonal(clip_geom_to_landmass(layer_geom))
}

config_groups <- config$groups
if (is.null(config_groups) || length(config_groups) == 0) {
  jsonlite::write_json(list(groups = list(), combined = NULL), file.path(output_dir, "metadata.json"), auto_unbox = TRUE, pretty = TRUE)
  quit(save = "no")
}

rendered_groups <- list()
meta_groups <- list()
active_group_ids <- c()

for (group_id in names(config_groups)) {
  group_cfg <- config_groups[[group_id]]
  active_layer_ids <- as.character(group_cfg$active_layer_ids)
  if (length(active_layer_ids) == 0) {
    next
  }

  group_row <- registry$groups[registry$groups$id == group_id, ]
  if (nrow(group_row) == 0) {
    next
  }

  analysis_kind <- group_row$analysis_kind[[1]]
  analysis_value_m <- as.numeric(group_cfg$analysis_value_m[[1]])
  analysis_value_m <- ifelse(is.na(analysis_value_m), 0, analysis_value_m)

  layer_buffers <- list()
  layer_labels <- c()
  for (layer_id in active_layer_ids) {
    layer_row <- registry$layers[registry$layers$id == layer_id, ]
    layer_input <- read_layer_input(layer_id)
    layer_sf <- layer_input$sf
    if (nrow(layer_sf) == 0) {
      next
    }
    layer_labels <- c(layer_labels, layer_row$label[[1]])

    buffered_geom <- prepare_layer_geometry(
      layer_sf = layer_sf,
      analysis_kind = analysis_kind,
      analysis_value_m = analysis_value_m,
      base_buffer_m = layer_input$base_buffer_m,
      already_clipped = layer_input$already_clipped,
      clip_to_landmass = group_id != "aviation_approach"
    )
    if (length(buffered_geom) == 0) {
      next
    }
    layer_buffers[[length(layer_buffers) + 1]] <- buffered_geom
  }

  if (length(layer_buffers) == 0) {
    next
  }

  group_geom <- single_feature_polygonal(combine_geometries(layer_buffers))
  role <- ifelse(analysis_kind == "proximity_feasibility", "feasible", "conflict")
  land_share_pct <- geometry_land_share_pct(group_geom)
  group_sf <- st_sf(
    tibble(
      group_id = group_id,
      group_label = group_row$label[[1]],
      role = role,
      analysis_kind = analysis_kind,
      analysis_value_m = analysis_value_m,
      land_share_pct = land_share_pct,
      selected_sources = paste(layer_labels, collapse = ", "),
      tooltip_title = paste0("Group layer: ", group_row$label[[1]]),
      tooltip_body = paste0(
        "Selected sources: ", paste(layer_labels, collapse = ", "),
        "<br>Analysis kind: ", analysis_kind,
        "<br>Threshold: ", analysis_value_m, " m",
        "<br>Geometry role: ", role,
        "<br>Land share on map: ", land_share_pct, "%",
        ifelse(group_id == "aviation_approach", "<br>Display buffer is not clipped at coastline.", paste0("<br>Clipped to ", landmask_label, "."))
      )
    ),
    geometry = group_geom
  )

  group_file <- paste0("group_", group_id, ".geojson")
  export_sf <- simplify_for_export(group_sf)
  if (file.exists(file.path(output_dir, group_file))) {
    unlink(file.path(output_dir, group_file))
  }
  st_write(export_sf, file.path(output_dir, group_file), driver = "GeoJSON", delete_dsn = TRUE, quiet = TRUE)

  rendered_groups[[group_id]] <- group_sf
  meta_groups[[group_id]] <- list(
    label = group_row$label[[1]],
    analysis_kind = analysis_kind,
    role = role,
    geojson_file = group_file,
    selected_sources = unname(layer_labels),
    analysis_value_m = unname(analysis_value_m),
    land_share_pct = unname(land_share_pct)
  )
  active_group_ids <- c(active_group_ids, group_id)
}

combined_meta <- NULL
if (length(active_group_ids) > 0) {
  conflict_ids <- active_group_ids[vapply(active_group_ids, function(id) rendered_groups[[id]]$role[[1]] == "conflict", logical(1))]
  feasible_ids <- active_group_ids[vapply(active_group_ids, function(id) rendered_groups[[id]]$role[[1]] == "feasible", logical(1))]

  conflict_geom <- NULL
  if (length(conflict_ids) > 0) {
    conflict_geom <- combine_geometries(rendered_groups[conflict_ids])
  }

  combined_geom <- NULL
  combined_label <- NULL
  combined_semantics <- NULL

  if (length(feasible_ids) > 0) {
    feasible_geom <- single_feature_polygonal(intersection_reduce(lapply(rendered_groups[feasible_ids], function(x) st_geometry(x))))
    combined_geom <- feasible_geom
    combined_label <- "Combined acceptance layer"
    combined_semantics <- "combined_acceptance"
    if (!is.null(conflict_geom) && length(conflict_geom) > 0) {
      combined_geom <- single_feature_polygonal(suppressWarnings(st_difference(feasible_geom, conflict_geom)))
    }
  } else if (length(conflict_ids) > 0) {
    combined_geom <- single_feature_polygonal(suppressWarnings(st_difference(landmask_geom, conflict_geom)))
    combined_label <- "Combined acceptance layer"
    combined_semantics <- "combined_acceptance"
  }

  if (!is.null(combined_geom) && length(combined_geom) > 0) {
    combined_land_share_pct <- geometry_land_share_pct(combined_geom)
    combined_sf <- st_sf(
      tibble(
        label = combined_label,
        semantics = combined_semantics,
        land_share_pct = combined_land_share_pct,
        active_groups = paste(active_group_ids, collapse = ", "),
        tooltip_title = combined_label,
        tooltip_body = paste0(
          "Active groups: ", paste(active_group_ids, collapse = ", "),
          "<br>Semantics: ", combined_semantics,
          "<br>Land share on map: ", combined_land_share_pct, "%",
          "<br>Clipped to ", landmask_label, "."
        )
      ),
      geometry = single_feature_polygonal(combined_geom)
    )

    combined_file <- "combined.geojson"
    export_sf <- simplify_for_export(combined_sf)
    if (file.exists(file.path(output_dir, combined_file))) {
      unlink(file.path(output_dir, combined_file))
    }
    st_write(export_sf, file.path(output_dir, combined_file), driver = "GeoJSON", delete_dsn = TRUE, quiet = TRUE)
    combined_meta <- list(
      label = combined_label,
      semantics = combined_semantics,
      geojson_file = combined_file,
      land_share_pct = combined_land_share_pct
    )
  }
}

metadata <- list(groups = meta_groups, combined = combined_meta)
jsonlite::write_json(metadata, file.path(output_dir, "metadata.json"), auto_unbox = TRUE, pretty = TRUE)
