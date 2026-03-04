if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv", repos = "https://cloud.r-project.org")
}

renv::init(bare = TRUE)
renv::install(c("DBI", "RPostgres", "dotenv", "sf", "dplyr", "mapview", "testthat"))
renv::snapshot()
