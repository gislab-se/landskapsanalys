run_split_area_share_layer <- function(layer_index, parent_run_order) {
  show_mapview <- is_truthy(Sys.getenv("SHOW_MAPVIEW", "true"))
  force_mapview <- is_truthy(Sys.getenv("FORCE_MAPVIEW", "false"))
  do_mapview <- show_mapview && (interactive() || force_mapview)
  show_layer_summary <- is_truthy(Sys.getenv("SHOW_LAYER_SUMMARY", if (interactive()) "true" else "false"))
  preview_only <- is_truthy(Sys.getenv("LAYER_PREVIEW_ONLY", "false"))
  run_aggregation <- is_truthy(Sys.getenv("RUN_AGGREGATION", "false"))
  if (preview_only) run_aggregation <- FALSE
  write_output <- is_truthy(Sys.getenv("WRITE_OUTPUT", "true"))
  metric_crs <- suppressWarnings(as.integer(Sys.getenv("METRIC_CRS", "25832")))
  if (is.na(metric_crs)) metric_crs <- 25832L
  output_alpha <- suppressWarnings(as.numeric(Sys.getenv("MAPVIEW_OUTPUT_ALPHA", "0.35")))
  if (is.na(output_alpha) || output_alpha <= 0 || output_alpha > 1) output_alpha <- 0.35

  home <- semi_manual_home()
  repo <- repo_root(home)

  layer_csv <- Sys.getenv(
    "GEOCONTEXT_LAYER_CSV",
    normalizePath(file.path(home, "config", "bornholm_r9_geocontext_layers.csv"), winslash = "/", mustWork = TRUE)
  )

  schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
  hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r9")
  hex_source <- Sys.getenv("HEX_SOURCE", "postgres")
  hex_file <- Sys.getenv("HEX_FILE", "")
  hex_layer <- Sys.getenv("HEX_LAYER", "")

  out_dir <- Sys.getenv(
    "GEOCONTEXT_LAYER_OUTPUT_DIR",
    normalizePath(file.path(repo, "data", "interim", "geocontext_r9", "layers"), winslash = "/", mustWork = FALSE)
  )
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

  layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
  layers$include <- as.logical(layers$include)
  layers <- layers[layers$include, , drop = FALSE]

  if (layer_index < 1 || layer_index > nrow(layers)) {
    stop("layer_index out of range. Valid: 1..", nrow(layers))
  }
  layer_row <- layers[layer_index, , drop = FALSE]

  split_rows <- read_subcategory_splits(home, parent_run_order = parent_run_order)
  if (nrow(split_rows) == 0) {
    stop("No active split rows found for step ", parent_run_order)
  }

  metric_family <- unique(split_rows$metric_family)
  if (length(metric_family) != 1 || !identical(metric_family, "area_share")) {
    stop("run_split_area_share_layer only supports area_share splits. Got: ", paste(metric_family, collapse = ", "))
  }

  split_field <- unique(split_rows$split_field)
  if (length(split_field) != 1) {
    stop("Expected exactly one split field, got: ", paste(split_field, collapse = ", "))
  }
  split_field <- split_field[1]
  child_rows <- collapse_split_children(split_rows)

  message(sprintf("Layer %d/%d: %s", layer_index, nrow(layers), layer_row$display_name))
  message("Hex source: ", hex_source, " | schema.table: ", schema, ".", hex_table)
  message("Split field: ", split_field)
  print(child_rows[, c("child_order", "child_key", "child_display_name", "child_output_column", "split_value_count", "split_values_label")])

  load_aggregator(home)
  hex <- load_hex_grid(
    hex_source = hex_source,
    schema = schema,
    hex_table = hex_table,
    home = home,
    hex_file = hex_file,
    hex_layer = hex_layer
  )

  source_layer <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
  source_layer <- prepare_source_layer(source_layer, sf::st_crs(hex))

  if (show_layer_summary) {
    print_layer_diagnostics(source_layer)
  }

  mapped_layer <- map_source_to_subcategories(source_layer, split_rows)
  value_counts <- mapped_layer %>%
    sf::st_drop_geometry() %>%
    dplyr::count(split_value_raw, child_display_name, sort = TRUE, name = "n_features")

  message("Source values and mapped child groups:")
  print(value_counts)

  unexpected <- unique(mapped_layer$split_value_raw[is.na(mapped_layer$child_output_column) & mapped_layer$split_value_raw != "(empty)"])
  if (length(unexpected) > 0) {
    warning(
      "Source layer contains values outside the selected split list: ",
      paste(unexpected, collapse = ", "),
      ". These remain visible only in the original total column."
    )
  }

  if (do_mapview) {
    if (!requireNamespace("mapview", quietly = TRUE)) {
      warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    } else {
      mapped_layer$preview_child <- ifelse(
        is.na(mapped_layer$child_display_name) | !nzchar(mapped_layer$child_display_name),
        paste0("(unmapped) ", mapped_layer$split_value_raw),
        mapped_layer$child_display_name
      )
      message("Opening pre-aggregation mapview (split child groups)...")
      pre_map <- mapview::mapview(
        hex,
        alpha.regions = 0,
        color = "grey70",
        lwd = 0.5,
        layer.name = "Hex grid (R9)"
      ) + mapview::mapview(
        mapped_layer,
        zcol = "preview_child",
        layer.name = paste0("Input split groups (", split_field, ")")
      )
      print(pre_map)
    }
  }

  if (!run_aggregation) {
    message("RUN_AGGREGATION=false -> stopped after input inspection and split review.")
    return(invisible(list(
      status = "preview_only",
      layer_index = layer_index,
      layer_key = layer_row$layer_key,
      display_name = layer_row$display_name
    )))
  }

  join_metric_column <- function(out_df, tmp_df, col_nm) {
    out_df <- dplyr::left_join(out_df, tmp_df, by = "hex_id")
    if (paste0(col_nm, ".x") %in% names(out_df) || paste0(col_nm, ".y") %in% names(out_df)) {
      out_df[[col_nm]] <- dplyr::coalesce(out_df[[paste0(col_nm, ".y")]], out_df[[paste0(col_nm, ".x")]], 0)
      out_df[[paste0(col_nm, ".x")]] <- NULL
      out_df[[paste0(col_nm, ".y")]] <- NULL
    } else {
      out_df[[col_nm]] <- dplyr::coalesce(out_df[[col_nm]], 0)
    }
    out_df
  }

  hex_m <- sf::st_transform(hex, metric_crs) %>% dplyr::select(hex_id)
  hex_area_m2 <- as.numeric(sf::st_area(sf::st_geometry(hex_m)))
  source_m <- sf::st_transform(mapped_layer, metric_crs) %>% dplyr::select(child_output_column)
  ix <- suppressWarnings(sf::st_intersection(source_m, hex_m))

  prefix <- layer_row$layer_key
  total_col <- paste0(prefix, "_area_share")
  out <- hex_m %>% sf::st_drop_geometry() %>% dplyr::transmute(hex_id, hex_area_m2 = hex_area_m2)
  out[[total_col]] <- 0
  for (col_nm in unique(child_rows$child_output_column)) {
    out[[col_nm]] <- 0
  }

  if (nrow(ix) > 0) {
    area_vals <- as.numeric(sf::st_area(sf::st_geometry(ix)))
    ag_total <- ix %>%
      sf::st_drop_geometry() %>%
      dplyr::mutate(area_m2 = area_vals) %>%
      dplyr::group_by(hex_id) %>%
      dplyr::summarise(area_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")
    ag_total <- dplyr::left_join(out[, c("hex_id", "hex_area_m2")], ag_total, by = "hex_id") %>%
      dplyr::mutate(
        area_m2 = dplyr::coalesce(area_m2, 0),
        area_share = ifelse(hex_area_m2 > 0, area_m2 / hex_area_m2, 0)
      )
    tmp_total <- ag_total[, c("hex_id", "area_share"), drop = FALSE]
    names(tmp_total)[2] <- total_col
    out <- join_metric_column(out, tmp_total, total_col)

    ag_child <- ix %>%
      sf::st_drop_geometry() %>%
      dplyr::mutate(area_m2 = area_vals) %>%
      dplyr::filter(!is.na(child_output_column) & nzchar(child_output_column)) %>%
      dplyr::group_by(hex_id, child_output_column) %>%
      dplyr::summarise(area_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")

    for (i in seq_len(nrow(child_rows))) {
      row_i <- child_rows[i, , drop = FALSE]
      col_nm <- row_i$child_output_column
      tmp <- ag_child[ag_child$child_output_column == col_nm, c("hex_id", "area_m2"), drop = FALSE]
      if (nrow(tmp) > 0) {
        tmp <- dplyr::left_join(out[, c("hex_id", "hex_area_m2")], tmp, by = "hex_id") %>%
          dplyr::mutate(
            area_m2 = dplyr::coalesce(area_m2, 0),
            area_share = ifelse(hex_area_m2 > 0, area_m2 / hex_area_m2, 0)
          ) %>%
          dplyr::select(hex_id, area_share)
      } else {
        tmp <- out[, c("hex_id"), drop = FALSE]
        tmp$area_share <- 0
      }
      names(tmp)[2] <- col_nm
      out <- join_metric_column(out, tmp, col_nm)
    }
  }

  out$hex_area_m2 <- NULL

  if (do_mapview) {
    if (!requireNamespace("mapview", quietly = TRUE)) {
      warning("SHOW_MAPVIEW is enabled, but package 'mapview' is not installed.")
    } else {
      hex_after <- dplyr::left_join(hex, out, by = "hex_id")
      message("Opening post-aggregation mapview (total share + split groups)...")
      post_map <- mapview::mapview(
        hex_after,
        zcol = total_col,
        alpha.regions = output_alpha,
        layer.name = paste0("Output: ", total_col)
      ) + mapview::mapview(
        mapped_layer,
        zcol = "preview_child",
        alpha.regions = 0.30,
        layer.name = paste0("Input split groups by ", split_field)
      )
      print(post_map)
    }
  }

  if (!write_output) {
    message("WRITE_OUTPUT=false -> aggregation completed, map shown, no CSV/log write.")
    return(invisible(list(
      status = "aggregated_not_written",
      layer_index = layer_index,
      layer_key = layer_row$layer_key,
      display_name = layer_row$display_name
    )))
  }

  file_base <- sprintf("%02d_%s", layer_index, layer_row$layer_key)
  out_csv <- file.path(out_dir, paste0(file_base, ".csv"))
  write.csv(out, out_csv, row.names = FALSE, na = "")

  log_path <- file.path(dirname(out_dir), "run_log.csv")
  log_row <- data.frame(
    run_ts = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    layer_index = layer_index,
    layer_key = layer_row$layer_key,
    display_name = layer_row$display_name,
    output_csv = out_csv,
    n_rows = nrow(out),
    n_cols = ncol(out),
    stringsAsFactors = FALSE
  )

  if (file.exists(log_path)) {
    old <- read.csv(log_path, stringsAsFactors = FALSE)
    old <- old[old$layer_index != layer_index, , drop = FALSE]
    log_df <- rbind(old, log_row)
  } else {
    log_df <- log_row
  }
  write.csv(log_df, log_path, row.names = FALSE, na = "")

  message("Wrote: ", out_csv)

  invisible(list(
    status = "ok",
    layer_index = layer_index,
    layer_key = layer_row$layer_key,
    output_csv = out_csv
  ))
}
