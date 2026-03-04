args_full <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_full, value = TRUE)
script_dir <- if (length(file_arg) > 0) dirname(normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)) else normalizePath("script/semi_manual_r9", winslash = "/", mustWork = FALSE)
repo_root <- normalizePath(file.path(script_dir, "..", ".."), winslash = "/", mustWork = FALSE)

layers_dir <- Sys.getenv(
  "GEOCONTEXT_LAYER_OUTPUT_DIR",
  normalizePath(file.path(repo_root, "data", "interim", "geocontext_r9", "layers"), winslash = "/", mustWork = FALSE)
)
out_csv <- Sys.getenv(
  "GEOCONTEXT_MERGED_OUTPUT_CSV",
  normalizePath(file.path(repo_root, "data", "interim", "geocontext_r9", "bornholm_r9_geocontext_raw_manual.csv"), winslash = "/", mustWork = FALSE)
)

files <- list.files(layers_dir, pattern = "\\.csv$", full.names = TRUE)
if (length(files) == 0) {
  stop("No layer CSV files found in ", layers_dir)
}

files <- sort(files)
merged <- NULL
for (f in files) {
  df <- read.csv(f, stringsAsFactors = FALSE)
  if (!"hex_id" %in% names(df)) {
    stop("File missing hex_id: ", f)
  }
  if (is.null(merged)) {
    merged <- df
  } else {
    merged <- merge(merged, df, by = "hex_id", all = TRUE)
  }
}

dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
write.csv(merged, out_csv, row.names = FALSE, na = "")

message("Merged files: ", length(files))
message("Rows: ", nrow(merged), " | Cols: ", ncol(merged))
message("Wrote: ", out_csv)
