library(testthat)

source("script/lib/bornholm_features.R")

test_that("build_feature_matrix keeps one row per hex", {
  hex <- sf::st_sf(
    hex_id = c("a", "b"),
    geometry = sf::st_sfc(sf::st_point(c(0, 0)), sf::st_point(c(1, 1)), crs = 4326)
  )

  hex_prot <- data.frame(hex_id = c("a", "b"), protected_share = c(0.1, 0.2))
  hex_wind <- data.frame(hex_id = c("a", "b"), dist_turbine_log = c(1, 2))
  hex_pop <- data.frame(hex_id = c("a", "b"), persons_log = c(3, 4))
  hex_elev <- data.frame(hex_id = c("a", "b"), relief = c(5, 6))

  out <- build_feature_matrix(hex, hex_prot, hex_wind, hex_pop, hex_elev)

  expect_equal(nrow(out), 2)
  expect_true(all(c("hex_id", "protected_share", "dist_turbine_log", "persons_log", "relief") %in% names(out)))
})
