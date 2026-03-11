suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
})

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")

metric_crs <- suppressWarnings(as.integer(Sys.getenv("SPLIT_AUDIT_METRIC_CRS", "25832")))
if (is.na(metric_crs) || metric_crs <= 0) {
  metric_crs <- 25832
}

is_bool_string <- function(x) {
  tolower(trimws(as.character(x))) %in% c("true", "1", "yes", "y")
}

clean_text <- function(x) {
  x <- trimws(as.character(x))
  x[x %in% c("", "NA", "NULL", "<NA>")] <- NA_character_
  x
}

field_semantic_pattern <- paste(
  c(
    "kategori", "klasse", "class", "type", "mb_type", "navn", "name", "operator", "ref$",
    "bred", "width", "kw", "power", "effekt", "kapac", "rotor", "hoejd", "height",
    "netvaerk", "network", "vandloeb", "water", "natyp", "natur", "anvendelse",
    "faldret", "synlig", "route", "ferry", "habitat", "bird", "ramsar", "reservat",
    "zone", "funktion", "formaal", "use"
  ),
  collapse = "|"
)

field_metadata_pattern <- paste(
  c(
    "^fid$", "^id$", "_id$", "^gid$", "objectid", "globalid", "uuid", "shape_", "^h3$", "^hex_",
    "gmlid", "lokalid", "registrer", "registre", "registreri", "forret", "plannoe", "plansted",
    "vertikal", "applik", "virkning", "kommentar", "aendr", "sagsbeh", "vedlige", "indsam",
    "godkend", "ksstatus", "^status$", "statuskode", "oprind", "geometriop", "service", "specifik",
    "created", "updated", "dato", "date", "timestamp", "minim"
  ),
  collapse = "|"
)

is_semantic_field <- function(field_name) {
  grepl(field_semantic_pattern, tolower(field_name))
}

looks_like_metadata_field <- function(field_name) {
  grepl(field_metadata_pattern, tolower(field_name))
}

metric_family_from_geom <- function(geom_kind) {
  if (geom_kind == "line") return("length_m")
  if (geom_kind == "polygon") return("area_m2")
  "count"
}

detect_geom_kind <- function(layer_sf) {
  gtypes <- unique(as.character(sf::st_geometry_type(layer_sf, by_geometry = TRUE)))
  if (any(grepl("POINT", gtypes))) return("point")
  if (any(grepl("LINESTRING", gtypes))) return("line")
  if (any(grepl("POLYGON", gtypes))) return("polygon")
  "other"
}

build_metric_vector <- function(layer_sf, geom_kind) {
  if (geom_kind == "line") {
    return(as.numeric(sf::st_length(layer_sf)))
  }
  if (geom_kind == "polygon") {
    return(as.numeric(sf::st_area(layer_sf)))
  }
  rep(1, nrow(layer_sf))
}

format_num <- function(x) {
  format(round(as.numeric(x), 2), trim = TRUE, scientific = FALSE)
}

make_numeric_bins <- function(vals_num, n_bins = 3L) {
  vals_ok <- vals_num[is.finite(vals_num)]
  if (length(vals_ok) < 6) {
    return(NULL)
  }

  brks <- unique(as.numeric(stats::quantile(vals_ok, probs = seq(0, 1, length.out = n_bins + 1), na.rm = TRUE, names = FALSE, type = 7)))
  if (length(brks) < 4) {
    return(NULL)
  }

  labels <- vapply(seq_len(length(brks) - 1), function(i) {
    paste0(format_num(brks[i]), "-", format_num(brks[i + 1]))
  }, character(1))

  bins <- cut(vals_num, breaks = brks, include.lowest = TRUE, labels = labels)
  if (length(unique(as.character(bins[!is.na(bins)]))) < 3) {
    return(NULL)
  }

  as.character(bins)
}

profile_field <- function(values, field_name) {
  if (looks_like_metadata_field(field_name)) {
    return(NULL)
  }

  semantic_field <- is_semantic_field(field_name)
  if (!semantic_field) {
    return(NULL)
  }

  if (is.logical(values)) {
    vals <- ifelse(is.na(values), NA_character_, ifelse(values, "TRUE", "FALSE"))
    uniq <- sort(unique(vals[!is.na(vals)]))
    if (length(uniq) < 2) return(NULL)
    return(list(field_type = "logical", values = vals, n_categories = length(uniq)))
  }

  if (is.factor(values) || is.character(values)) {
    vals <- clean_text(values)
    uniq <- sort(unique(vals[!is.na(vals)]))
    if (length(uniq) < 2 || length(uniq) > 8) return(NULL)
    return(list(field_type = "categorical", values = vals, n_categories = length(uniq)))
  }

  if (is.numeric(values) || is.integer(values)) {
    vals_num <- suppressWarnings(as.numeric(values))
    uniq_num <- sort(unique(vals_num[is.finite(vals_num)]))
    if (length(uniq_num) >= 2 && length(uniq_num) <= 8) {
      vals_chr <- ifelse(is.finite(vals_num), format(vals_num, trim = TRUE, scientific = FALSE), NA_character_)
      return(list(field_type = "numeric_group", values = vals_chr, n_categories = length(uniq_num)))
    }

    bins <- make_numeric_bins(vals_num, n_bins = 3L)
    if (!is.null(bins)) {
      uniq_bins <- sort(unique(bins[!is.na(bins)]))
      return(list(field_type = "numeric_binned", values = bins, n_categories = length(uniq_bins)))
    }
  }

  NULL
}

summarise_candidate <- function(run_row, layer_row, field_name, prof, metric_vec) {
  vals <- prof$values
  keep <- !is.na(vals)
  vals <- vals[keep]
  metric_vec <- metric_vec[keep]

  if (length(vals) == 0) {
    return(NULL)
  }

  metric_tbl <- tapply(metric_vec, vals, sum, na.rm = TRUE)
  metric_tbl <- sort(metric_tbl, decreasing = TRUE)

  metric_total <- sum(metric_tbl, na.rm = TRUE)
  if (!is.finite(metric_total) || metric_total <= 0) {
    return(NULL)
  }

  metric_share <- metric_tbl / metric_total
  dominant_share <- unname(metric_share[1])
  second_share <- if (length(metric_share) >= 2) unname(metric_share[2]) else 0
  significant_n <- sum(metric_share >= 0.05, na.rm = TRUE)

  score <- 0L
  if (prof$n_categories >= 2 && prof$n_categories <= 4) score <- score + 2L
  if (prof$n_categories >= 5 && prof$n_categories <= 6) score <- score + 1L
  if (significant_n >= 2) score <- score + 2L
  if (dominant_share <= 0.85) score <- score + 1L
  if (prof$field_type %in% c("categorical", "logical", "numeric_binned")) score <- score + 1L

  suggestion <- score >= 4L
  top_names <- names(metric_share)[seq_len(min(3, length(metric_share)))]
  top_values <- paste(
    sprintf("%s (%.1f%%)", top_names, 100 * metric_share[top_names]),
    collapse = "; "
  )

  data.frame(
    run_order = as.integer(run_row$run_order),
    original_layer_index = as.integer(run_row$original_layer_index),
    layer_key = layer_row$layer_key,
    display_name = layer_row$display_name,
    field_name = field_name,
    field_type = prof$field_type,
    n_categories = prof$n_categories,
    dominant_share = round(dominant_share, 4),
    second_share = round(second_share, 4),
    significant_categories = as.integer(significant_n),
    score = as.integer(score),
    suggested_split = suggestion,
    metric_family = metric_family_from_geom(run_row$geom_kind),
    top_values = top_values,
    stringsAsFactors = FALSE
  )
}

top_value_rows <- function(run_row, layer_row, field_name, prof, metric_vec) {
  vals <- prof$values
  keep <- !is.na(vals)
  vals <- vals[keep]
  metric_vec <- metric_vec[keep]
  if (length(vals) == 0) {
    return(NULL)
  }

  count_tbl <- table(vals)
  metric_tbl <- tapply(metric_vec, vals, sum, na.rm = TRUE)
  metric_tbl <- sort(metric_tbl, decreasing = TRUE)
  metric_total <- sum(metric_tbl, na.rm = TRUE)
  if (!is.finite(metric_total) || metric_total <= 0) {
    return(NULL)
  }

  top_names <- names(metric_tbl)[seq_len(min(8, length(metric_tbl)))]
  data.frame(
    run_order = as.integer(run_row$run_order),
    layer_key = layer_row$layer_key,
    display_name = layer_row$display_name,
    field_name = field_name,
    field_value = top_names,
    feature_count = as.integer(count_tbl[top_names]),
    metric_value = as.numeric(metric_tbl[top_names]),
    metric_share = round(as.numeric(metric_tbl[top_names]) / metric_total, 4),
    stringsAsFactors = FALSE
  )
}

home <- semi_manual_home()
repo <- repo_root(home)
load_aggregator(home)

run_order_csv <- file.path(repo, "script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")

run_order <- read.csv(run_order_csv, stringsAsFactors = FALSE)
layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- is_bool_string(layers$include)
layers <- layers[layers$include, , drop = FALSE]

schema <- Sys.getenv("PIPELINE_SCHEMA", "h3")
hex_table <- Sys.getenv("HEX_TABLE", "bornholm_r9")
hex_source <- Sys.getenv("HEX_SOURCE", "postgres")
hex_file <- Sys.getenv("HEX_FILE", "")
hex_layer <- Sys.getenv("HEX_LAYER", "")

hex <- load_hex_grid(
  hex_source = hex_source,
  schema = schema,
  hex_table = hex_table,
  home = home,
  hex_file = hex_file,
  hex_layer = hex_layer
)

hex_bbox_metric <- sf::st_as_sfc(sf::st_bbox(sf::st_transform(hex, metric_crs)))

candidate_rows <- list()
detail_rows <- list()
candidate_i <- 1L
detail_i <- 1L

for (i in seq_len(nrow(run_order))) {
  run_row <- run_order[i, , drop = FALSE]
  orig_idx <- as.integer(run_row$original_layer_index)
  if (!is.finite(orig_idx) || orig_idx < 1 || orig_idx > nrow(layers)) {
    next
  }

  layer_row <- layers[orig_idx, , drop = FALSE]
  message(sprintf("Auditing step %02d: %s", as.integer(run_row$run_order), layer_row$display_name))

  layer_sf <- tryCatch(
    read_layer_sf(layer_row$source_path, layer_row$layer_name, quiet = TRUE),
    error = function(e) {
      warning("Failed to read layer: ", layer_row$display_name, " | ", conditionMessage(e))
      NULL
    }
  )
  if (is.null(layer_sf) || nrow(layer_sf) == 0) {
    next
  }

  layer_sf <- tryCatch(sf::st_zm(layer_sf, drop = TRUE, what = "ZM"), error = function(e) layer_sf)
  layer_sf <- tryCatch(sf::st_make_valid(layer_sf), error = function(e) layer_sf)
  layer_sf <- tryCatch(sf::st_transform(layer_sf, metric_crs), error = function(e) NULL)
  if (is.null(layer_sf) || nrow(layer_sf) == 0) {
    next
  }

  keep_bbox <- tryCatch(lengths(sf::st_intersects(layer_sf, hex_bbox_metric)) > 0, error = function(e) rep(TRUE, nrow(layer_sf)))
  layer_sf <- layer_sf[keep_bbox, , drop = FALSE]
  if (nrow(layer_sf) == 0) {
    next
  }

  geom_kind <- detect_geom_kind(layer_sf)
  run_row$geom_kind <- geom_kind
  if (geom_kind == "other") {
    next
  }

  metric_vec <- build_metric_vector(layer_sf, geom_kind)
  attr_df <- sf::st_drop_geometry(layer_sf)
  if (ncol(attr_df) == 0) {
    next
  }

  for (field_name in names(attr_df)) {
    prof <- profile_field(attr_df[[field_name]], field_name)
    if (is.null(prof)) {
      next
    }

    cand <- summarise_candidate(run_row, layer_row, field_name, prof, metric_vec)
    det <- top_value_rows(run_row, layer_row, field_name, prof, metric_vec)
    if (!is.null(cand)) {
      candidate_rows[[candidate_i]] <- cand
      candidate_i <- candidate_i + 1L
    }
    if (!is.null(det)) {
      detail_rows[[detail_i]] <- det
      detail_i <- detail_i + 1L
    }
  }
}

candidate_df <- if (length(candidate_rows) > 0) bind_rows(candidate_rows) else data.frame()
detail_df <- if (length(detail_rows) > 0) bind_rows(detail_rows) else data.frame()

if (nrow(candidate_df) > 0) {
  candidate_df <- candidate_df %>%
    arrange(desc(suggested_split), desc(score), run_order, field_name)
}

out_dir <- file.path(repo, "data", "interim", "geocontext_r9", "split_audit")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

candidate_csv <- file.path(out_dir, "bornholm_r9_split_field_candidates.csv")
detail_csv <- file.path(out_dir, "bornholm_r9_split_field_value_summary.csv")

write.csv(candidate_df, candidate_csv, row.names = FALSE, na = "")
write.csv(detail_df, detail_csv, row.names = FALSE, na = "")

message("Wrote candidates: ", candidate_csv)
message("Wrote details: ", detail_csv)

if (nrow(candidate_df) > 0) {
  message("Top suggested splits:")
  print(utils::head(candidate_df[candidate_df$suggested_split, c(
    "run_order", "display_name", "field_name", "field_type", "n_categories", "score", "top_values"
  )], 20))
} else {
  message("No candidate split fields found with current heuristics.")
}