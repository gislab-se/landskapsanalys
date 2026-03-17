# Step 45: Jordart split into top five classes plus grouped remainder families
# Preview (recommended first):
#   Sys.setenv(SHOW_MAPVIEW = "true", SHOW_LAYER_SUMMARY = "true", RUN_AGGREGATION = "false")
#
# Aggregate and write output:
#   Sys.setenv(RUN_AGGREGATION = "true", WRITE_OUTPUT = "true")

args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_file <- if (length(file_arg) > 0) normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE) else normalizePath(".", winslash = "/", mustWork = FALSE)
script_dir <- dirname(script_file)
Sys.setenv(SEMI_MANUAL_R9_HOME = normalizePath(file.path(script_dir, ".."), winslash = "/", mustWork = TRUE))
source(file.path(script_dir, "..", "lib", "manual_layer_aggregation.R"))
source(file.path(script_dir, "..", "lib", "subcategory_splits.R"))
source(file.path(script_dir, "..", "lib", "split_area_share_layer.R"))
run_split_area_share_layer(layer_index = 45L, parent_run_order = 45L)
