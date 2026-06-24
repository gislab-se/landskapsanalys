from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PATH = (
    "D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01/Utkommande_SL01/"
    "UT_Trondelag_SL01/UTM 32/TFylke_Popu_250m_Centroid.shp"
)
SOURCE_PATH = Path(os.environ.get("TRONDELAG_POPULATION_250M_CENTROID_SHP", DEFAULT_SOURCE_PATH))
OUTPUT_PATH = (
    ROOT
    / "docs/geocontext/acceptance_framework/data/trondelag_prototype_assets/population_tables/"
    / "trondelag_population_250m_h3_r8.csv"
)
TARGET_RESOLUTION = 8
POPULATION_COLUMN = "poptot"


def main() -> int:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing Trondelag population source: {SOURCE_PATH}")
    source = gpd.read_file(SOURCE_PATH)
    if POPULATION_COLUMN not in source.columns:
        raise ValueError(f"Missing population column {POPULATION_COLUMN!r} in {SOURCE_PATH}")
    source = source.to_crs(4326)
    points = source.geometry
    work = pd.DataFrame(
        {
            "hex_id": [
                h3.latlng_to_cell(float(point.y), float(point.x), TARGET_RESOLUTION)
                if point is not None and not point.is_empty
                else None
                for point in points
            ],
            "population": pd.to_numeric(source[POPULATION_COLUMN], errors="coerce").fillna(0.0).clip(lower=0.0),
        }
    )
    work = work.dropna(subset=["hex_id"])
    out = (
        work.groupby("hex_id", as_index=False)
        .agg(population=("population", "sum"), source_cell_count=("hex_id", "size"))
        .sort_values("hex_id")
        .reset_index(drop=True)
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(out)} H3 R{TARGET_RESOLUTION} rows to {OUTPUT_PATH}")
    print(f"Total population: {out['population'].sum():.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
