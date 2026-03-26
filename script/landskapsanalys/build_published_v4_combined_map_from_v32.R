suppressPackageStartupMessages({
  library(sf)
  library(dplyr)
  library(tidyr)
  library(stringr)
  library(purrr)
  library(leaflet)
  library(htmlwidgets)
  library(htmltools)
})

repo_root <- "C:/gislab/landskapsanalys"
analysis_id <- "landskapsanalys_v3_2_contourterrain68_res9"
data_dir <- file.path(repo_root, "docs/geocontext/model_comparisons/data", analysis_id)
output_dir <- file.path(repo_root, "docs/geocontext/published_report")
output_html <- file.path(output_dir, "landskapsanalys_v4_combined_map.html")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

indicator_catalog <- read.csv(
  file.path(data_dir, paste0(analysis_id, "_indicator_catalog.csv")),
  stringsAsFactors = FALSE
)
hex <- st_read(
  file.path(data_dir, paste0(analysis_id, "_hex.gpkg")),
  layer = analysis_id,
  quiet = TRUE
)
hex_wgs84 <- st_transform(hex, 4326)
loadings_df <- read.csv(
  file.path(data_dir, paste0(analysis_id, "_factor_loadings.csv")),
  stringsAsFactors = FALSE
)
raw_geocontext <- read.csv(
  file.path(repo_root, "data/interim/geocontext_r9/bornholm_r9_geocontext_raw_manual.csv"),
  stringsAsFactors = FALSE
)
raw_augmented <- read.csv(
  file.path(data_dir, paste0(analysis_id, "_raw_augmented.csv")),
  stringsAsFactors = FALSE
)
points_with_context_scores <- read.csv(
  file.path(data_dir, paste0(analysis_id, "_points_with_context_and_scores.csv")),
  stringsAsFactors = FALSE
)

factor_cols <- grep("^F[0-9]+$", names(hex_wgs84), value = TRUE)

display_mainland_cols <- intersect(
  c(
    "dhm_hoejdekurver_highest_point_m",
    "dhm_hoejdekurver_relief_m",
    "markblokke_2026_bornholm_area_share",
    "forest_gd_v_skov_forest_bol_33_area_share",
    "fredskov_miljostyrelsen_gds_mat2_fredskov_bor_32_area_share",
    "wetland_gd_v_vaadomr_wetland_bol_33_area_share",
    "lake_gd_v_soe_lake_bol_33_area_share",
    "roads_simplified_gd_v_vej_road_merged_bol_33_length_m_total",
    "fastboendebefolkningmapinfo_count",
    "buildings_low_gd_v_buildings_low_bol_33_area_share",
    "buildings_high_gd_v_buildings_high_bol_33_area_share",
    "built_centre_gd_v_bykerne_built_centre_bol_33_area_share",
    "built_low_gd_v_buildings_low_selection_by_bol_33_area_share",
    "industry_business_gd_v_erhverv_business_industry_bol_33_area_share",
    "jordart_25000_v7_1_area_share",
    "prekvart_bornholm_area_share"
  ),
  names(raw_geocontext)
)

display_lookup <- raw_geocontext |>
  transmute(
    hex_id,
    mainland_display = rowSums(across(all_of(display_mainland_cols), ~ dplyr::coalesce(as.numeric(.x), 0))) > 0
  )

hex_wgs84_display <- hex_wgs84 |>
  left_join(display_lookup, by = "hex_id") |>
  mutate(mainland_display = if_else(is.na(mainland_display), FALSE, mainland_display)) |>
  filter(mainland_display)

display_bbox <- st_bbox(hex_wgs84_display)

factor_labels <- c(
  F1 = "Flygsands- och laglanta kustmiljoer",
  F2 = "Brant relief och sprickdalspraglad terrang",
  F3 = "Skogligt skyddsinland och habitatkarnor",
  F4 = "Bosattning och byggd struktur",
  F5 = "Marina sand- och gruskuster"
)

factor_explanations <- c(
  F1 = "Fangar sandiga och laglanta kustmiljoer.",
  F2 = "Fangar brant relief, lutning och dalinslag.",
  F3 = "Fangar skogligt skyddsinland och habitatkarnor.",
  F4 = "Fangar bosattning, vagar och byggd struktur.",
  F5 = "Fangar marina sand- och gruskuster."
)

cluster_labels <- c(
  "1" = "Tatorts- och verksamhetskarnor",
  "2" = "Vardagslandskap med blandad bakgrundskaraktar",
  "3" = "Flygsands- och laglanta kuststrak",
  "4" = "Brant relief och dalpraglat inland",
  "5" = "Skogligt skyddsinland och habitatkarnor"
)

cluster_explanations <- c(
  "1" = "Byggd struktur, befolkning och verksamhet ar starkast har.",
  "2" = "Ons breda bakgrundslandskap utan tydlig specialisering.",
  "3" = "Sandiga och laglanta kuststrak med svag skogs- och bosattningssignal.",
  "4" = "Brant och terrangkontrasterat inland med tydliga dalinslag.",
  "5" = "Skogligt skyddsinland med tydliga habitatkarnor."
)

class_palette <- c(
  "1" = "#6E7C91",
  "2" = "#D8C97A",
  "3" = "#D5B08A",
  "4" = "#8B6B45",
  "5" = "#5B7F4A",
  "6" = "#6C5B7B",
  "7" = "#F8B195",
  "8" = "#80B1D3",
  "9" = "#B3DE69",
  "10" = "#BC80BD"
)

cluster_display_label <- function(k) {
  k_chr <- as.character(k)
  paste(k_chr, dplyr::coalesce(unname(cluster_labels[k_chr]), paste("Kluster", k_chr)))
}

format_popup_number <- function(x, digits = 1) {
  if (length(x) == 0 || is.na(x)) {
    return("NA")
  }
  format(
    round(as.numeric(x), digits = digits),
    trim = TRUE,
    scientific = FALSE,
    big.mark = " ",
    nsmall = digits
  )
}

format_signed <- function(x) {
  ifelse(is.na(x), "NA", sprintf("%+.3f", x))
}

indicator_lookup <- setNames(indicator_catalog$display_name, indicator_catalog$gc_name)
source_lookup <- setNames(indicator_catalog$source_name, indicator_catalog$gc_name)
geometry_lookup <- setNames(indicator_catalog$geometry_type, indicator_catalog$gc_name)

format_layer_value <- function(value, gc_name) {
  value_num <- suppressWarnings(as.numeric(value))
  if (length(value_num) == 0 || is.na(value_num)) {
    return("NA")
  }

  source_name <- dplyr::coalesce(unname(source_lookup[gc_name]), gc_name)
  geometry_type <- dplyr::coalesce(unname(geometry_lookup[gc_name]), "")
  name_probe <- paste(gc_name, source_name)

  if (geometry_type == "Polygon area share" || grepl("(_area_share$|_share$)", source_name)) {
    return(paste0(format_popup_number(value_num * 100, 1), "%"))
  }
  if (geometry_type == "Point count" || grepl("count$", gc_name)) {
    return(format_popup_number(value_num, 0))
  }
  if (grepl("slope_deg", name_probe)) {
    return(paste0(format_popup_number(value_num, 1), " deg"))
  }
  if (geometry_type == "Line length" || grepl("_length_m($|_)", source_name) || grepl("_length_m($|_)", gc_name)) {
    return(paste0(format_popup_number(value_num, 0), " m"))
  }
  if (grepl("band|proxy", name_probe)) {
    return(format_popup_number(value_num, 2))
  }
  if (geometry_type == "Continuous metric" || grepl("(_m$|relief|highest_point|elevation|valley_depth)", name_probe)) {
    return(paste0(format_popup_number(value_num, 1), " m"))
  }

  format_popup_number(value_num, 2)
}

series_from_variable <- function(variable) {
  variable |>
    str_replace("^(mean_|std_)", "") |>
    str_remove("_k[0-9]+$")
}

pretty_variable <- function(variable) {
  stat_type <- ifelse(str_detect(variable, "^mean_"), "medel", "std")
  series <- series_from_variable(variable)
  k <- str_extract(variable, "(?<=_k)[0-9]+$")
  series_label <- dplyr::coalesce(unname(indicator_lookup[series]), series)
  paste0(series_label, " (", stat_type, ", k=", k, ")")
}

factor_label <- function(f) dplyr::coalesce(unname(factor_labels[f]), f)

factor_limit_robust <- hex_wgs84 |>
  st_drop_geometry() |>
  select(all_of(factor_cols)) |>
  unlist(use.names = FALSE) |>
  abs() |>
  quantile(0.995, na.rm = TRUE) |>
  unname()

factor_pal <- colorNumeric(
  palette = c("#2166AC", "#F7F7F7", "#B2182B"),
  domain = c(-factor_limit_robust, factor_limit_robust),
  na.color = "transparent"
)

class_vals <- sort(unique(as.character(hex_wgs84_display$class_km)))
cluster_pal <- colorFactor(unname(class_palette[class_vals]), domain = class_vals)

factor_top_loadings_lookup <- purrr::map(factor_cols, function(f) {
  loadings_df |>
    transmute(
      variable_label = pretty_variable(variable),
      loading = .data[[f]],
      abs_loading = abs(.data[[f]])
    ) |>
    arrange(desc(abs_loading)) |>
    slice_head(n = 5)
}) |>
  purrr::set_names(factor_cols)

factor_top_loadings_html_lookup <- purrr::imap_chr(factor_top_loadings_lookup, function(tbl, f) {
  items <- paste0(
    "<li><strong>", htmltools::htmlEscape(tbl$variable_label), "</strong>: ",
    format_signed(tbl$loading), "</li>",
    collapse = ""
  )
  paste0(
    "<div style='margin-top:8px;'><strong>Topp 5 laddningar:</strong>",
    "<ol style='margin:6px 0 0 18px;padding:0;'>",
    items,
    "</ol></div>"
  )
})

raw_augmented$hex_id <- as.character(raw_augmented$hex_id)
points_with_context_scores$hex_id <- as.character(points_with_context_scores$hex_id)

layer_context_variable_lookup <- purrr::set_names(
  purrr::map(indicator_catalog$gc_name, function(gc_name) {
    vars <- loadings_df$variable[
      grepl(paste0("^(mean_|std_)", gc_name, "_k[0-9]+$"), loadings_df$variable)
    ]
    vars[vars %in% names(points_with_context_scores)]
  }),
  indicator_catalog$gc_name
)

layer_context_weight_lookup <- purrr::imap(
  layer_context_variable_lookup,
  function(vars, gc_name) {
    if (length(vars) == 0) {
      return(numeric(0))
    }
    vapply(vars, function(variable_name) {
      loading_row <- loadings_df[loadings_df$variable == variable_name, factor_cols, drop = FALSE]
      if (nrow(loading_row) == 0) {
        return(0)
      }
      sum(abs(as.numeric(loading_row[1, factor_cols, drop = TRUE])), na.rm = TRUE)
    }, numeric(1))
  }
)

layer_contribution_df <- tibble::tibble(hex_id = points_with_context_scores$hex_id)
for (gc_name in indicator_catalog$gc_name) {
  vars <- layer_context_variable_lookup[[gc_name]]
  weights <- layer_context_weight_lookup[[gc_name]]

  if (length(vars) == 0) {
    layer_contribution_df[[gc_name]] <- NA_real_
  } else {
    contribution <- rep(0, nrow(points_with_context_scores))
    for (i in seq_along(vars)) {
      contribution <- contribution + abs(suppressWarnings(as.numeric(points_with_context_scores[[vars[i]]]))) * weights[i]
    }
    layer_contribution_df[[gc_name]] <- contribution
  }
}

display_hex_ids <- unique(as.character(hex_wgs84_display$hex_id))
layer_popup_lookup <- purrr::set_names(
  purrr::map_chr(display_hex_ids, function(current_hex_id) {
    raw_idx <- match(current_hex_id, raw_augmented$hex_id)
    contribution_idx <- match(current_hex_id, layer_contribution_df$hex_id)

    if (is.na(raw_idx)) {
      return("")
    }

    raw_row <- raw_augmented[raw_idx, , drop = FALSE]
    layer_tbl <- indicator_catalog |>
      transmute(
        gc_name,
        display_name,
        source_name,
        raw_value = purrr::map_dbl(source_name, function(source_name) {
          if (!source_name %in% names(raw_row)) {
            return(NA_real_)
          }
          suppressWarnings(as.numeric(raw_row[[source_name]][1]))
        }),
        contribution = purrr::map_dbl(gc_name, function(gc_name) {
          if (is.na(contribution_idx) || !gc_name %in% names(layer_contribution_df)) {
            return(NA_real_)
          }
          suppressWarnings(as.numeric(layer_contribution_df[[gc_name]][contribution_idx]))
        })
      ) |>
      filter(!is.na(raw_value), abs(raw_value) > 1e-9) |>
      arrange(desc(tidyr::replace_na(contribution, -Inf)), desc(abs(raw_value))) |>
      slice_head(n = 5)

    if (nrow(layer_tbl) == 0) {
      return("")
    }

    items <- paste0(
      "<li><strong>",
      htmltools::htmlEscape(dplyr::coalesce(layer_tbl$display_name, layer_tbl$gc_name)),
      "</strong>: ",
      htmltools::htmlEscape(vapply(seq_len(nrow(layer_tbl)), function(i) {
        format_layer_value(layer_tbl$raw_value[i], layer_tbl$gc_name[i])
      }, character(1))),
      "</li>",
      collapse = ""
    )

    paste0(
      "<div style='margin-top:8px;'><strong>Topplager i detta hex:</strong>",
      "<ol style='margin:6px 0 0 18px;padding:0;'>",
      items,
      "</ol></div>"
    )
  }),
  display_hex_ids
)

layer_popup_html <- function(hex_id) {
  popup_html <- layer_popup_lookup[[as.character(hex_id)]]
  if (length(popup_html) == 0 || is.na(popup_html)) {
    return("")
  }
  popup_html
}

factor_popup_html <- function(f, hex_id, score, class_km) {
  paste0(
    "<div style='min-width:320px;'>",
    "<div style='font-weight:700;margin-bottom:6px;'>", htmltools::htmlEscape(factor_label(f)), "</div>",
    "<div style='margin-bottom:8px;'>", htmltools::htmlEscape(unname(factor_explanations[f])), "</div>",
    "<div><strong>Hex:</strong> ", htmltools::htmlEscape(as.character(hex_id)),
    "<br><strong>Kluster:</strong> ", htmltools::htmlEscape(cluster_display_label(class_km)),
    "<br><strong>Score:</strong> ", format_signed(score), "</div>",
    factor_top_loadings_html_lookup[[f]],
    "</div>"
  )
}

cluster_popup_html <- function(class_km, hex_id) {
  paste0(
    "<div style='min-width:320px;'>",
    "<div style='font-weight:700;margin-bottom:6px;'>", htmltools::htmlEscape(cluster_display_label(class_km)), "</div>",
    "<div style='margin-bottom:8px;'>", htmltools::htmlEscape(unname(cluster_explanations[as.character(class_km)])), "</div>",
    "<div><strong>Hex:</strong> ", htmltools::htmlEscape(as.character(hex_id)),
    "<br><strong>Typ:</strong> ", htmltools::htmlEscape(cluster_display_label(class_km)), "</div>",
    layer_popup_html(hex_id),
    "</div>"
  )
}

cluster_layer_data <- hex_wgs84_display |>
  transmute(
    hex_id,
    class_km = as.character(class_km),
    fill_color = cluster_pal(as.character(class_km)),
    popup_html = purrr::map2_chr(class_km, hex_id, cluster_popup_html)
  )

factor_layer_data_lookup <- setNames(vector("list", length(factor_cols)), factor_cols)

for (f in factor_cols) {
  clipped_values <- pmax(pmin(hex_wgs84_display[[f]], factor_limit_robust), -factor_limit_robust)
  factor_layer_data_lookup[[f]] <- hex_wgs84_display |>
    transmute(
      hex_id,
      class_km = as.character(class_km),
      fill_color = factor_pal(clipped_values),
      popup_html = vapply(
        seq_len(nrow(hex_wgs84_display)),
        function(i) factor_popup_html(
          f = f,
          hex_id = hex_wgs84_display$hex_id[i],
          score = hex_wgs84_display[[f]][i],
          class_km = hex_wgs84_display$class_km[i]
        ),
        character(1)
      )
    )
}

mode_options <- c(
  list(list(value = "cluster", label = "Kluster")),
  lapply(factor_cols, function(f) {
    list(value = f, label = factor_label(f))
  })
)

cluster_legend_items <- lapply(class_vals, function(k) {
  list(color = unname(cluster_pal(k)), label = cluster_display_label(k))
})

factor_label_lookup <- as.list(stats::setNames(factor_label(factor_cols), factor_cols))
factor_gradient <- paste0(
  "linear-gradient(to right, ",
  paste(factor_pal(seq(-factor_limit_robust, factor_limit_robust, length.out = 7)), collapse = ", "),
  ")"
)

widget <- leaflet(options = leafletOptions(zoomSnap = 0.25)) |>
  addProviderTiles("Esri.WorldImagery", group = "Satellitbild") |>
  addProviderTiles("CartoDB.Positron", group = "Ljus baskarta")

widget <- widget |>
  addPolygons(
    data = cluster_layer_data,
    group = "mode_cluster",
    fillColor = ~fill_color,
    fillOpacity = 0.68,
    color = "#4A4A4A",
    opacity = 0.54,
    weight = 0.25,
    popup = ~popup_html,
    popupOptions = popupOptions(maxWidth = 460)
  )

for (f in factor_cols) {
  widget <- widget |>
    addPolygons(
      data = factor_layer_data_lookup[[f]],
      group = paste0("mode_", f),
      fillColor = ~fill_color,
      fillOpacity = 0.68,
      color = "#555555",
      opacity = 0.30,
      weight = 0.15,
      popup = ~popup_html,
      popupOptions = popupOptions(maxWidth = 460)
    )
}

widget <- widget |>
  hideGroup(paste0("mode_", factor_cols)) |>
  addLayersControl(
    baseGroups = c("Satellitbild", "Ljus baskarta"),
    options = layersControlOptions(collapsed = FALSE, autoZIndex = FALSE)
  ) |>
  addScaleBar(position = "bottomleft") |>
  fitBounds(
    lng1 = unname(display_bbox["xmin"]),
    lat1 = unname(display_bbox["ymin"]),
    lng2 = unname(display_bbox["xmax"]),
    lat2 = unname(display_bbox["ymax"])
  )

widget <- htmlwidgets::onRender(
  widget,
  "
function(el, x, data) {
  var map = this;
  var currentMode = data.defaultMode || 'cluster';
  var legendEl = null;
  var opacityControl = L.control({position: 'topright'});
  var modeControl = L.control({position: 'topleft'});
  var legendControl = L.control({position: 'bottomright'});

  function collectPolygonLayers(layer, bag) {
    if (!layer) {
      return;
    }
    if (layer.feature && layer.feature.properties && layer.feature.properties.hex_id && typeof layer.setStyle === 'function') {
      bag.push(layer);
      return;
    }
    if (typeof layer.eachLayer === 'function') {
      layer.eachLayer(function(child) {
        collectPolygonLayers(child, bag);
      });
    }
  }

  function activeGroup() {
    return map.layerManager.getLayerGroup(data.groupLookup[currentMode], true);
  }

  function activePolygonLayers() {
    var layers = [];
    collectPolygonLayers(activeGroup(), layers);
    return layers;
  }

  function applyStyleToActiveGroup(fill) {
    var group = activeGroup();
    var style = styleFor(fill);
    if (!group) {
      return;
    }
    if (typeof group.setStyle === 'function') {
      group.setStyle(style);
      return;
    }
    activePolygonLayers().forEach(function(layer) {
      layer.setStyle(style);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\\\"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isClusterMode(mode) {
    return mode === 'cluster';
  }

  function currentFillValue() {
    var slider = document.getElementById('combined-opacity-slider');
    return slider ? Number(slider.value) : Number(data.baseFill);
  }

  function toggleGroups() {
    Object.keys(data.groupLookup).forEach(function(modeKey) {
      var groupName = data.groupLookup[modeKey];
      var layer = map.layerManager.getLayerGroup(groupName, true);
      if (!layer) {
        return;
      }
      if (modeKey === currentMode) {
        if (!map.hasLayer(layer)) {
          map.addLayer(layer);
        }
      } else if (map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });
  }

  function styleFor(fill) {
    var isCluster = isClusterMode(currentMode);
    var stroke = isCluster
      ? Math.max(0.12, Math.min(0.85, fill * 0.8))
      : Math.max(0.10, Math.min(0.8, fill * 0.45));
    return {
      fillOpacity: fill,
      color: isCluster ? data.clusterStrokeColor : data.factorStrokeColor,
      opacity: stroke,
      weight: isCluster ? data.clusterWeight : data.factorWeight
    };
  }

  function updateModeLabel() {
    var label = document.getElementById('combined-mode-value');
    if (!label) {
      return;
    }
    label.textContent = isClusterMode(currentMode)
      ? data.clusterLegendTitle
      : (data.factorLabelLookup[currentMode] || currentMode);
  }

  function clusterLegendHtml() {
    var items = data.clusterLegendItems.map(function(item) {
      return '<div style=\"display:flex;align-items:flex-start;gap:8px;margin-top:6px;\">' +
        '<span style=\"display:inline-block;width:12px;height:12px;border-radius:2px;background:' + item.color + ';border:1px solid rgba(0,0,0,0.22);margin-top:3px;\"></span>' +
        '<span>' + escapeHtml(item.label) + '</span>' +
        '</div>';
    }).join('');

    return '<div style=\"font-weight:600;margin-bottom:6px;\">' +
      escapeHtml(data.clusterLegendTitle) +
      '</div>' + items;
  }

  function factorLegendHtml() {
    var label = data.factorLabelLookup[currentMode] || currentMode;
    return '<div style=\"font-weight:600;margin-bottom:6px;\">' +
      escapeHtml(data.factorLegendTitle + ' - ' + label) +
      '</div>' +
      '<div style=\"height:12px;border-radius:999px;background:' + data.factorLegendGradient + ';border:1px solid rgba(0,0,0,0.18);\"></div>' +
      '<div style=\"display:flex;justify-content:space-between;font-size:12px;margin-top:4px;gap:8px;\">' +
      '<span>-' + escapeHtml(data.factorLimitLabel) + '</span>' +
      '<span>0</span>' +
      '<span>+' + escapeHtml(data.factorLimitLabel) + '</span>' +
      '</div>';
  }

  function updateLegend() {
    if (!legendEl) {
      return;
    }
    legendEl.innerHTML = isClusterMode(currentMode) ? clusterLegendHtml() : factorLegendHtml();
  }

  function applyMode() {
    var fill = currentFillValue();
    toggleGroups();
    applyStyleToActiveGroup(fill);
    updateModeLabel();
    updateLegend();
  }

  opacityControl.onAdd = function() {
    var div = L.DomUtil.create('div', 'combined-opacity-control leaflet-bar');
    div.style.background = 'rgba(255,255,255,0.94)';
    div.style.padding = '10px 12px';
    div.style.borderRadius = '8px';
    div.style.boxShadow = '0 1px 6px rgba(0,0,0,0.22)';
    div.style.minWidth = '190px';
    div.style.marginTop = '48px';
    div.innerHTML = '<div style=\"font-weight:600;margin-bottom:6px;\">' + escapeHtml(data.opacityControlTitle) + '</div>' +
      '<input id=\"combined-opacity-slider\" type=\"range\" min=\"0.05\" max=\"1.00\" step=\"0.05\" value=\"' + data.baseFill + '\" style=\"width:100%;\">' +
      '<div id=\"combined-opacity-value\" style=\"margin-top:4px;font-size:12px;\">' + Math.round(data.baseFill * 100) + '%</div>';
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    return div;
  };

  modeControl.onAdd = function() {
    var div = L.DomUtil.create('div', 'combined-mode-control leaflet-bar');
    var optionsHtml = data.modeOptions.map(function(option) {
      var checked = option.value === currentMode ? ' checked' : '';
      return '<label style=\"display:flex;align-items:flex-start;gap:8px;margin-top:6px;cursor:pointer;\">' +
        '<input type=\"radio\" name=\"combined-mode\" value=\"' + escapeHtml(option.value) + '\"' + checked + ' style=\"margin-top:2px;\">' +
        '<span>' + escapeHtml(option.label) + '</span></label>';
    }).join('');
    div.style.background = 'rgba(255,255,255,0.94)';
    div.style.padding = '10px 12px';
    div.style.borderRadius = '8px';
    div.style.boxShadow = '0 1px 6px rgba(0,0,0,0.22)';
    div.style.minWidth = '230px';
    div.innerHTML = '<div style=\"font-weight:600;margin-bottom:6px;\">' + escapeHtml(data.modeControlTitle) + '</div>' +
      optionsHtml +
      '<div id=\"combined-mode-value\" style=\"margin-top:6px;font-size:12px;color:#555;\"></div>';
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    return div;
  };

  legendControl.onAdd = function() {
    var div = L.DomUtil.create('div', 'combined-legend-control leaflet-bar');
    div.style.background = 'rgba(255,255,255,0.94)';
    div.style.padding = '10px 12px';
    div.style.borderRadius = '8px';
    div.style.boxShadow = '0 1px 6px rgba(0,0,0,0.22)';
    div.style.minWidth = '190px';
    legendEl = div;
    updateLegend();
    return div;
  };

  opacityControl.addTo(map);
  modeControl.addTo(map);
  legendControl.addTo(map);

  var slider = document.getElementById('combined-opacity-slider');
  if (slider) {
    slider.addEventListener('input', function(evt) {
      var fill = Number(evt.target.value);
      applyStyleToActiveGroup(fill);
      var label = document.getElementById('combined-opacity-value');
      if (label) {
        label.textContent = Math.round(fill * 100) + '%';
      }
    });
  }

  var radios = document.querySelectorAll('input[name=\"combined-mode\"]');
  if (radios && radios.length) {
    radios.forEach(function(radio) {
      radio.addEventListener('change', function(evt) {
        currentMode = evt.target.value;
        applyMode();
      });
    });
  }

  applyMode();
}
",
  data = list(
    defaultMode = "cluster",
    baseFill = 0.68,
    modeControlTitle = "Karttema",
    opacityControlTitle = "Kartlagrens opacitet",
    clusterLegendTitle = "Kluster",
    factorLegendTitle = "Faktorscore",
    factorLegendGradient = factor_gradient,
    factorLimitLabel = format_popup_number(abs(factor_limit_robust), 1),
    modeOptions = mode_options,
    groupLookup = c(cluster = "mode_cluster", stats::setNames(paste0("mode_", factor_cols), factor_cols)),
    clusterLegendItems = cluster_legend_items,
    factorLabelLookup = factor_label_lookup,
    clusterStrokeColor = "#4A4A4A",
    factorStrokeColor = "#555555",
    clusterWeight = 0.25,
    factorWeight = 0.15
  )
)

htmlwidgets::saveWidget(
  widget,
  output_html,
  selfcontained = FALSE,
  title = "Samlad kluster- och faktorkarta Landskapsanalys Bornholm"
)
