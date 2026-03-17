slugify_text <- function(x) {
  y <- tolower(trimws(iconv(as.character(x), from = "", to = "ASCII//TRANSLIT")))
  y[is.na(y) | !nzchar(y)] <- "unknown"
  y <- gsub("[^a-z0-9]+", "_", y)
  y <- gsub("^_+|_+$", "", y)
  y <- gsub("_+", "_", y)
  ifelse(nchar(y) == 0, "unknown", y)
}

read_subcategory_splits <- function(home, parent_run_order = NULL, active_only = TRUE) {
  cfg_path <- file.path(home, "config", "bornholm_r9_subcategory_splits.csv")
  if (!file.exists(cfg_path)) {
    stop("Missing subcategory split config: ", cfg_path)
  }

  splits <- read.csv(cfg_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
  if (!"child_output_column" %in% names(splits)) {
    splits$child_output_column <- mapply(
      derive_child_output_column,
      parent_layer_key = splits$parent_layer_key,
      metric_family = splits$metric_family,
      split_value = splits$split_value,
      USE.NAMES = FALSE
    )
  }
  if (!"input_filter_mode" %in% names(splits)) {
    splits$input_filter_mode <- "field_equals"
  }

  splits$active <- tolower(trimws(as.character(splits$active))) %in% c("true", "1", "yes", "y")
  splits$render_under_parent <- tolower(trimws(as.character(splits$render_under_parent))) %in% c("true", "1", "yes", "y")
  splits$parent_run_order <- suppressWarnings(as.integer(splits$parent_run_order))
  splits$child_order <- suppressWarnings(as.integer(splits$child_order))
  splits$split_value_slug <- slugify_text(splits$split_value)

  if (active_only) {
    splits <- splits[splits$active, , drop = FALSE]
  }
  if (!is.null(parent_run_order)) {
    splits <- splits[splits$parent_run_order == as.integer(parent_run_order), , drop = FALSE]
  }
  if (nrow(splits) == 0) {
    return(splits)
  }

  splits[order(splits$parent_run_order, splits$child_order, splits$child_key, splits$split_value), , drop = FALSE]
}

collapse_split_children <- function(split_rows) {
  if (nrow(split_rows) == 0) {
    split_rows$split_value_count <- integer(0)
    split_rows$split_values_label <- character(0)
    return(split_rows)
  }

  split_rows <- split_rows[order(split_rows$parent_run_order, split_rows$child_order, split_rows$child_key, split_rows$split_value), , drop = FALSE]
  child_id <- paste(split_rows$parent_run_order, split_rows$child_key, split_rows$child_output_column, sep = "||")
  keep <- !duplicated(child_id)
  children <- split_rows[keep, , drop = FALSE]
  child_ids <- child_id[keep]

  children$split_value_count <- vapply(child_ids, function(id) {
    sum(child_id == id)
  }, integer(1))
  children$split_values_label <- vapply(child_ids, function(id) {
    paste(unique(split_rows$split_value[child_id == id]), collapse = " | ")
  }, character(1))

  children
}

derive_child_output_column <- function(parent_layer_key, metric_family, split_value) {
  suffix <- slugify_text(split_value)
  prefix <- switch(
    metric_family,
    length_m = paste0(parent_layer_key, "_length_m_"),
    area_share = paste0(parent_layer_key, "_area_share_"),
    count = paste0(parent_layer_key, "_count_"),
    sum = paste0(parent_layer_key, "_sum_"),
    m = paste0(parent_layer_key, "_m_"),
    stop("Unsupported metric_family for split column derivation: ", metric_family)
  )
  paste0(prefix, suffix)
}

normalize_text_ascii <- function(x) {
  tolower(trimws(iconv(as.character(x), from = "", to = "ASCII//TRANSLIT")))
}

classify_road_class <- function(x) {
  y <- normalize_text_ascii(x)
  out <- rep("other", length(y))
  out[grepl("stor|motor|major|primary", y)] <- "large"
  out[grepl("mellem|mellan|medium|secondary", y)] <- "medium"
  out[grepl("lille|small|minor|local|residential", y)] <- "small"
  out
}

compute_split_match_key <- function(values, input_filter_mode = "field_equals") {
  modes <- unique(ifelse(is.na(input_filter_mode) | !nzchar(input_filter_mode), "field_equals", input_filter_mode))
  if (length(modes) != 1) {
    stop("Expected exactly one input_filter_mode, got: ", paste(modes, collapse = ", "))
  }

  mode <- modes[1]
  if (identical(mode, "field_equals")) {
    return(slugify_text(values))
  }
  if (identical(mode, "derived_road_class")) {
    return(slugify_text(classify_road_class(values)))
  }

  stop("Unsupported input_filter_mode: ", mode)
}

map_source_to_subcategories <- function(source_layer, split_rows) {
  if (nrow(split_rows) == 0) {
    stop("No split rows provided for source-to-subcategory mapping.")
  }

  split_field <- unique(split_rows$split_field)
  if (length(split_field) != 1) {
    stop("Expected exactly one split field, got: ", paste(split_field, collapse = ", "))
  }
  split_field <- split_field[1]

  if (!split_field %in% names(source_layer)) {
    stop("Split field not found in source layer: ", split_field)
  }

  mode <- unique(ifelse(is.na(split_rows$input_filter_mode) | !nzchar(split_rows$input_filter_mode), "field_equals", split_rows$input_filter_mode))
  if (length(mode) != 1) {
    stop("Expected exactly one input_filter_mode for mapping, got: ", paste(mode, collapse = ", "))
  }
  mode <- mode[1]

  source_layer$split_value_raw <- trimws(as.character(source_layer[[split_field]]))
  source_layer$split_value_raw[is.na(source_layer$split_value_raw) | !nzchar(source_layer$split_value_raw)] <- "(empty)"
  source_layer$split_value_key <- compute_split_match_key(source_layer[[split_field]], mode)

  split_rows$split_value_key <- compute_split_match_key(split_rows$split_value, mode)
  lookup <- unique(split_rows[, c("split_value_key", "child_key", "child_display_name", "child_output_column"), drop = FALSE])

  dup_keys <- unique(lookup$split_value_key[duplicated(lookup$split_value_key)])
  if (length(dup_keys) > 0) {
    for (key_i in dup_keys) {
      rows_i <- lookup[lookup$split_value_key == key_i, , drop = FALSE]
      signature_i <- unique(paste(rows_i$child_key, rows_i$child_output_column, sep = "||"))
      if (length(signature_i) > 1) {
        stop("Conflicting child mappings for split value key: ", key_i)
      }
    }
    lookup <- lookup[!duplicated(lookup$split_value_key), , drop = FALSE]
  }

  idx <- match(source_layer$split_value_key, lookup$split_value_key)
  source_layer$child_key <- lookup$child_key[idx]
  source_layer$child_display_name <- lookup$child_display_name[idx]
  source_layer$child_output_column <- lookup$child_output_column[idx]

  source_layer
}

subset_source_by_child <- function(source_layer, split_rows, child_key = NULL, child_output_column = NULL) {
  if ((is.null(child_key) || !nzchar(child_key)) && (is.null(child_output_column) || !nzchar(child_output_column))) {
    stop("Provide child_key or child_output_column when subsetting by child.")
  }

  mapped_layer <- map_source_to_subcategories(source_layer, split_rows)
  keep <- rep(FALSE, nrow(mapped_layer))

  if (!is.null(child_key) && nzchar(child_key)) {
    keep <- keep | (!is.na(mapped_layer$child_key) & mapped_layer$child_key == child_key)
  }
  if (!is.null(child_output_column) && nzchar(child_output_column)) {
    keep <- keep | (!is.na(mapped_layer$child_output_column) & mapped_layer$child_output_column == child_output_column)
  }

  mapped_layer[keep, , drop = FALSE]
}

subset_source_by_split <- function(source_layer, split_field, split_value, input_filter_mode = "field_equals") {
  mode <- ifelse(is.na(input_filter_mode) | !nzchar(input_filter_mode), "field_equals", input_filter_mode)

  if (identical(mode, "field_equals")) {
    if (!split_field %in% names(source_layer)) {
      stop("Split field not found in source layer: ", split_field)
    }
    raw_vals <- trimws(as.character(source_layer[[split_field]]))
    keep <- !is.na(raw_vals) & slugify_text(raw_vals) == slugify_text(split_value)
    return(source_layer[keep, , drop = FALSE])
  }

  if (identical(mode, "derived_road_class")) {
    if (!split_field %in% names(source_layer)) {
      stop("Road classification field not found in source layer: ", split_field)
    }
    road_class <- classify_road_class(source_layer[[split_field]])
    keep <- !is.na(road_class) & slugify_text(road_class) == slugify_text(split_value)
    return(source_layer[keep, , drop = FALSE])
  }

  stop("Unsupported input_filter_mode: ", mode)
}
