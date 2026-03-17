suppressPackageStartupMessages({
  library(dplyr)
})

source("script/semi_manual_r9/lib/manual_layer_aggregation.R")
source("script/semi_manual_r9/lib/subcategory_splits.R")

args <- commandArgs(trailingOnly = TRUE)
step_no <- suppressWarnings(as.integer(if (length(args) >= 1) args[1] else Sys.getenv("STEP_RUN_ORDER", "")))
run_order_guard_csv <- file.path("script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
run_order_guard <- if (file.exists(run_order_guard_csv)) read.csv(run_order_guard_csv, stringsAsFactors = FALSE) else data.frame(run_order = 44)
max_step <- suppressWarnings(max(as.integer(run_order_guard$run_order), na.rm = TRUE))
if (!is.finite(max_step)) max_step <- 44
if (is.na(step_no) || step_no < 1 || step_no > max_step) {
  stop(sprintf("Provide run step number 1..%d as argument, e.g. Rscript .../render_step_subcategory_artifacts.R 17", max_step))
}

home <- semi_manual_home()
repo <- repo_root(home)
split_rows <- read_subcategory_splits(home, parent_run_order = step_no)
split_rows <- split_rows[split_rows$render_under_parent, , drop = FALSE]
if (nrow(split_rows) == 0) {
  message("No renderable subcategories configured for step ", step_no)
  quit(save = "no", status = 0)
}
child_rows <- collapse_split_children(split_rows)

run_order_csv <- file.path(repo, "script", "semi_manual_r9", "config", "bornholm_r9_run_order.csv")
layer_csv <- file.path(home, "config", "bornholm_r9_geocontext_layers.csv")
run_order <- read.csv(run_order_csv, stringsAsFactors = FALSE)
run_row <- run_order[run_order$run_order == step_no, , drop = FALSE]
if (nrow(run_row) != 1) {
  stop("Could not resolve run step in mapping: ", step_no)
}

layers <- read.csv(layer_csv, stringsAsFactors = FALSE)
layers$include <- as.logical(layers$include)
layers <- layers[layers$include, , drop = FALSE]
orig_idx <- as.integer(run_row$original_layer_index)
layer_row <- layers[orig_idx, , drop = FALSE]

fig_dir <- file.path(repo, "docs", "geocontext", "figures")
review_dir <- file.path(repo, "docs", "geocontext", "review")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(review_dir, recursive = TRUE, showWarnings = FALSE)

png_script <- file.path(repo, "script", "semi_manual_r9", "report", "render_step_overview_png.R")
html_script <- file.path(repo, "script", "semi_manual_r9", "report", "render_step_review_html.R")

quote_ps <- function(x) {
  paste0("'", gsub("'", "''", x, fixed = TRUE), "'")
}

run_renderer <- function(script_path, step_no, env_vars) {
  split_env <- strsplit(env_vars, "=", fixed = TRUE)
  env_names <- vapply(split_env, `[`, character(1), 1)
  env_values <- vapply(split_env, function(x) paste(x[-1], collapse = "="), character(1))
  env_cmd <- paste(
    sprintf("$env:%s=%s", env_names, vapply(env_values, quote_ps, character(1))),
    collapse = "; "
  )
  ps_cmd <- paste0(
    "$ErrorActionPreference='Stop'; ",
    env_cmd,
    "; & Rscript ",
    quote_ps(script_path),
    " ",
    step_no
  )
  out <- system2(
    "powershell",
    c("-NoProfile", "-Command", ps_cmd),
    stdout = TRUE,
    stderr = TRUE
  )
  status <- attr(out, "status")
  if (is.null(status)) status <- 0
  if (status != 0) {
    stop(
      "Renderer failed for step ", step_no, " using ", basename(script_path), "\n",
      paste(out, collapse = "\n")
    )
  }
  invisible(out)
}

for (i in seq_len(nrow(child_rows))) {
  child_row <- child_rows[i, , drop = FALSE]
  png_path <- file.path(fig_dir, sprintf("layer%02d_%s_overview.png", step_no, child_row$child_key))
  html_path <- file.path(review_dir, sprintf("layer%02d_%s_review.html", step_no, child_row$child_key))
  child_title <- sprintf("Steg %02d: %s", step_no, child_row$child_display_name)
  child_subtitle <- paste0(
    "Underkategori av ", layer_row$display_name,
    " (", child_row$child_output_column, ")"
  )

  common_env <- c(
    paste0("VALUE_COL=", child_row$child_output_column),
    paste0("SUBCATEGORY_CHILD_KEY=", child_row$child_key),
    paste0("INPUT_LAYER_NAME=Input: ", child_row$child_display_name),
    paste0("OUTPUT_LAYER_NAME=Output: ", child_row$child_output_column)
  )

  run_renderer(
    png_script,
    step_no,
    c(
      common_env,
      paste0("OUTPUT_PATH=", png_path),
      paste0("PLOT_TITLE=", child_title),
      paste0("PLOT_SUBTITLE=", child_subtitle)
    )
  )

  run_renderer(
    html_script,
    step_no,
    c(
      common_env,
      paste0("OUTPUT_PATH=", html_path)
    )
  )

  message("Rendered subcategory artifacts: ", child_row$child_key)
}
