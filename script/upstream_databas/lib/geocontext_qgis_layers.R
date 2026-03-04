suppressPackageStartupMessages({
  library(xml2)
  library(dplyr)
  library(sf)
})

slugify <- function(x) {
  y <- tolower(iconv(x, from = "", to = "ASCII//TRANSLIT"))
  y <- gsub("[^a-z0-9]+", "_", y)
  y <- gsub("^_+|_+$", "", y)
  y <- gsub("_+", "_", y)
  ifelse(nchar(y) == 0, "layer", y)
}

parse_datasource <- function(datasource) {
  parts <- strsplit(datasource, "\\|", fixed = FALSE)[[1]]
  source_path <- parts[1]
  layer_name <- ""
  if (length(parts) > 1) {
    layer_part <- parts[grepl("^layername=", parts)]
    if (length(layer_part) > 0) {
      layer_name <- sub("^layername=", "", layer_part[1])
    }
  }
  list(source_path = source_path, layer_name = layer_name)
}

resolve_source_path <- function(path_raw, project_root, qgz_dir) {
  if (grepl("^[A-Za-z]:[/\\\\]", path_raw)) {
    return(normalizePath(path_raw, winslash = "/", mustWork = FALSE))
  }
  if (startsWith(path_raw, "./")) {
    rel <- sub("^\\./", "", path_raw)
    return(normalizePath(file.path(project_root, rel), winslash = "/", mustWork = FALSE))
  }
  normalizePath(file.path(qgz_dir, path_raw), winslash = "/", mustWork = FALSE)
}

extract_geocontext_layers_from_qgz <- function(
    qgz_path = "c:/gislab/QGS_BOL_geocontext.qgz",
    project_root = "c:/gislab") {
  if (!file.exists(qgz_path)) {
    stop("QGZ file not found: ", qgz_path)
  }

  tmp_dir <- tempfile("qgz_extract_")
  dir.create(tmp_dir, recursive = TRUE, showWarnings = FALSE)
  on.exit(unlink(tmp_dir, recursive = TRUE, force = TRUE), add = TRUE)

  qgs_files <- unzip(qgz_path, exdir = tmp_dir)
  qgs_files <- qgs_files[grepl("\\.qgs$", qgs_files, ignore.case = TRUE)]
  if (length(qgs_files) == 0) {
    stop("No .qgs found inside: ", qgz_path)
  }
  qgs_path <- qgs_files[1]
  qgz_dir <- dirname(qgz_path)

  doc <- read_xml(qgs_path)

  geocontext_nodes <- xml_find_all(
    doc,
    "//layer-tree-group[@name='Geocontext']//layer-tree-layer"
  )

  if (length(geocontext_nodes) == 0) {
    stop("No layers found under group 'Geocontext' in project.")
  }

  layer_ids <- xml_attr(geocontext_nodes, "id")
  layer_ids <- layer_ids[!is.na(layer_ids)]

  out <- lapply(layer_ids, function(layer_id) {
    map_node <- xml_find_first(
      doc,
      sprintf("//projectlayers/maplayer[id='%s']", layer_id)
    )
    if (inherits(map_node, "xml_missing")) {
      return(NULL)
    }

    display_name <- xml_text(xml_find_first(map_node, "layername"))
    provider <- xml_text(xml_find_first(map_node, "provider"))
    datasource <- xml_text(xml_find_first(map_node, "datasource"))
    geometry <- xml_text(xml_find_first(map_node, "geometry"))

    ds <- parse_datasource(datasource)
    source_path <- resolve_source_path(ds$source_path, project_root, qgz_dir)

    data.frame(
      include = TRUE,
      layer_key = slugify(display_name),
      display_name = display_name,
      source_path = source_path,
      layer_name = ds$layer_name,
      provider = provider,
      geometry = geometry,
      value_field = "",
      aggregation_type = "auto",
      notes = "",
      stringsAsFactors = FALSE
    )
  })

  out <- bind_rows(out)
  out <- out %>% distinct(layer_key, .keep_all = TRUE)
  out
}

write_geocontext_selection_template <- function(
    out_csv = "databas/script/config/bornholm_r8_geocontext_layers.csv",
    qgz_path = "c:/gislab/QGS_BOL_geocontext.qgz",
    project_root = "c:/gislab") {
  layers <- extract_geocontext_layers_from_qgz(
    qgz_path = qgz_path,
    project_root = project_root
  )
  dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
  write.csv(layers, out_csv, row.names = FALSE, na = "")
  message("Wrote selection template: ", normalizePath(out_csv, winslash = "/", mustWork = FALSE))
  invisible(layers)
}

read_layer_sf <- function(source_path, layer_name = "", quiet = TRUE) {
  if (!file.exists(source_path)) {
    stop("Layer source path does not exist: ", source_path)
  }
  if (!is.na(layer_name) && nzchar(layer_name)) {
    sf::st_read(source_path, layer = layer_name, quiet = quiet)
  } else {
    sf::st_read(source_path, quiet = quiet)
  }
}

aggregate_layer_to_hex <- function(hex_sf, layer_row, metric_crs = 25832) {
  lyr <- read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE)
  if (nrow(lyr) == 0) {
    warning("Skipping empty layer: ", layer_row$display_name)
    return(hex_sf %>% st_drop_geometry() %>% transmute(hex_id, !!paste0(layer_row$layer_key, "_empty") := TRUE))
  }

  lyr <- sf::st_zm(lyr, drop = TRUE, what = "ZM")
  lyr <- sf::st_make_valid(lyr)
  lyr <- sf::st_transform(lyr, sf::st_crs(hex_sf))

  gtypes <- as.character(sf::st_geometry_type(lyr, by_geometry = TRUE))
  gtypes <- unique(gtypes[!is.na(gtypes)])
  is_point <- any(grepl("POINT", gtypes))
  is_line <- any(grepl("LINESTRING", gtypes))
  is_poly <- any(grepl("POLYGON", gtypes))

  key <- layer_row$layer_key

  if (is_point) {
    hits <- sf::st_intersects(hex_sf, lyr)
    n_pts <- lengths(hits)
    out <- hex_sf %>%
      st_drop_geometry() %>%
      transmute(hex_id, !!paste0(key, "_count") := n_pts)

    if (!is.na(layer_row$value_field) && nzchar(layer_row$value_field) && layer_row$value_field %in% names(lyr)) {
      vals <- lyr[[layer_row$value_field]]
      if (is.numeric(vals)) {
        sums <- vapply(hits, function(idx) {
          if (length(idx) == 0) return(0)
          sum(vals[idx], na.rm = TRUE)
        }, numeric(1))
        out[[paste0(key, "_sum")]] <- sums
      }
    }
    return(out)
  }

  if (is_line) {
    hex_m <- sf::st_transform(hex_sf, metric_crs) %>% select(hex_id)
    lyr_m <- sf::st_transform(lyr, metric_crs)
    ix <- suppressWarnings(sf::st_intersection(lyr_m, hex_m))
    if (nrow(ix) == 0) {
      return(hex_sf %>% st_drop_geometry() %>% transmute(hex_id, !!paste0(key, "_length_m") := 0))
    }
    lens <- as.numeric(sf::st_length(sf::st_geometry(ix)))
    ag <- ix %>%
      st_drop_geometry() %>%
      mutate(len_m = lens) %>%
      group_by(hex_id) %>%
      summarise(len_m = sum(len_m, na.rm = TRUE), .groups = "drop")
    return(
      hex_sf %>%
        st_drop_geometry() %>%
        left_join(ag, by = "hex_id") %>%
        mutate(len_m = ifelse(is.na(len_m), 0, len_m)) %>%
        transmute(hex_id, !!paste0(key, "_length_m") := len_m)
    )
  }

  if (is_poly) {
    hex_m <- sf::st_transform(hex_sf, metric_crs) %>% select(hex_id)
    lyr_m <- sf::st_transform(lyr, metric_crs)
    ix <- suppressWarnings(sf::st_intersection(lyr_m, hex_m))
    if (nrow(ix) == 0) {
      return(hex_sf %>% st_drop_geometry() %>% transmute(hex_id, !!paste0(key, "_area_share") := 0))
    }
    area_vals <- as.numeric(sf::st_area(sf::st_geometry(ix)))
    ag <- ix %>%
      st_drop_geometry() %>%
      mutate(area_m2 = area_vals) %>%
      group_by(hex_id) %>%
      summarise(area_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")
    hex_area <- as.numeric(sf::st_area(sf::st_geometry(hex_m)))
    out <- hex_m %>%
      st_drop_geometry() %>%
      mutate(hex_area_m2 = hex_area) %>%
      left_join(ag, by = "hex_id") %>%
      mutate(
        area_m2 = ifelse(is.na(area_m2), 0, area_m2),
        area_share = ifelse(hex_area_m2 > 0, area_m2 / hex_area_m2, 0)
      ) %>%
      transmute(hex_id, !!paste0(key, "_area_share") := area_share)
    return(out)
  }

  warning("Unsupported geometry type in layer: ", layer_row$display_name, " (", paste(gtypes, collapse = ","), ")")
  hex_sf %>% st_drop_geometry() %>% transmute(hex_id)
}
