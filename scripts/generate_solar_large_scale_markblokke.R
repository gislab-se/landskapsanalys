library(sf)

sf_use_s2(FALSE)

outdir <- "docs/geocontext/potential_framework/data/bornholm_solar_large_scale_markblokke"
aggdir <- file.path(outdir, "h3_r10_area_share")
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
dir.create(aggdir, recursive = TRUE, showWarnings = FALSE)

land <- st_read(
  "docs/geocontext/potential_framework/data/bornholm_landmask/bornholm_landmask_wgs84.geojson",
  quiet = TRUE
)
land25832 <- st_union(st_transform(st_make_valid(land), 25832))
filter_wkt <- st_as_text(st_as_sfc(st_bbox(land25832)))

mark <- st_read(
  "C:/gislab/data/dataraw/jordbruksmark/Markblokke_2026.shp",
  wkt_filter = filter_wkt,
  quiet = TRUE
)
mark <- st_make_valid(mark)
mark <- st_intersection(mark, land25832)
mark <- st_collection_extract(mark, "POLYGON", warn = FALSE)
mark <- mark[!st_is_empty(mark), ]
mark <- st_sf(markblok_id = seq_len(nrow(mark)), geometry = st_geometry(mark), crs = st_crs(mark))

pop <- st_read(
  "docs/geocontext/acceptance_framework/data/prototype_assets/source_geojson/population_points.geojson",
  quiet = TRUE
)
pop25832 <- st_transform(pop, 25832)

grid <- st_read(
  "C:/gislab/regional-landscape-pipeline/outputs/bornholm/bornholm_v1_higher_h3_local_sprickdal/grid/bornholm_v1_higher_h3_local_sprickdal_hex_res10.gpkg",
  quiet = TRUE
)
grid <- st_transform(st_make_valid(grid[, "hex_id"]), 25832)
grid$hex_area_m2 <- as.numeric(st_area(grid))

write_one <- function(dist) {
  work <- mark
  if (dist > 0) {
    # population_points.geojson is already a dissolved 100 m display buffer.
    # The UI slider is the total distance from population, so only add the
    # distance above that 100 m base before clipping Markblokke.
    extra_buffer_m <- max(0, dist - 100)
    if (extra_buffer_m > 0) {
      buf <- st_union(st_buffer(pop25832, extra_buffer_m))
    } else {
      buf <- st_union(st_geometry(pop25832))
    }
    work <- suppressWarnings(st_difference(work, buf))
    work <- st_collection_extract(work, "POLYGON", warn = FALSE)
    work <- work[!st_is_empty(work), ]
  }

  agg_out <- file.path(
    aggdir,
    sprintf("markblokke_bornholm_outside_population_%03dm_h3_r10_area_share.csv", dist)
  )
  if (dist == 0 && file.exists(agg_out)) {
    agg <- read.csv(agg_out, stringsAsFactors = FALSE)
  } else if (dist == 0 && nrow(work) > 0) {
    work_union <- st_sf(group = 1L, geometry = st_union(st_geometry(work)), crs = st_crs(work))
    candidate_grid <- st_filter(grid, work_union, .predicate = st_intersects)
    if (nrow(candidate_grid) > 0) {
      parts <- suppressWarnings(st_intersection(candidate_grid, work_union))
      parts$potential_area_m2 <- as.numeric(st_area(parts))
      agg <- aggregate(
        parts$potential_area_m2,
        by = list(hex_id = parts$hex_id, hex_area_m2 = parts$hex_area_m2),
        FUN = sum
      )
      names(agg)[names(agg) == "x"] <- "potential_area_m2"
      agg$potential_area_km2 <- agg$potential_area_m2 / 1000000
      agg$potential_area_share_pct <- pmin(
        100,
        pmax(0, agg$potential_area_m2 / agg$hex_area_m2 * 100)
      )
      agg <- agg[agg$potential_area_m2 > 0, ]
    } else {
      agg <- data.frame(
        hex_id = character(),
        hex_area_m2 = numeric(),
        potential_area_m2 = numeric(),
        potential_area_km2 = numeric(),
        potential_area_share_pct = numeric()
      )
    }
  } else {
    agg <- data.frame(
      hex_id = character(),
      hex_area_m2 = numeric(),
      potential_area_m2 = numeric(),
      potential_area_km2 = numeric(),
      potential_area_share_pct = numeric()
    )
  }
  if (dist == 0) {
    write.csv(agg, agg_out, row.names = FALSE)
    agg_size <- file.info(agg_out)$size
  } else {
    agg_size <- NA
  }

  work <- st_transform(work, 4326)
  work$source <- "Markblokke 2026"
  work$buffer_m <- dist

  out <- file.path(
    outdir,
    sprintf("markblokke_bornholm_outside_population_%03dm.geojson", dist)
  )
  st_write(work, out, driver = "GeoJSON", delete_dsn = TRUE, quiet = TRUE)
  cat(dist, nrow(work), nrow(agg), file.info(out)$size, agg_size, "\n")
}

for (dist in c(0, seq(100, 500, by = 25))) {
  write_one(dist)
}
