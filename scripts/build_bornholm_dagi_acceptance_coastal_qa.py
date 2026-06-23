from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import make_valid


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "exports" / "qgis_review" / "bornholm_dagi_acceptance_coastal_qa"
OLD_ASSETS = ROOT / "docs" / "geocontext" / "acceptance_framework" / "data" / "prototype_assets"
NEW_REGISTRY = ROOT / "apps" / "acceptance_model" / "registry_bornholm.json"
LANDMASK_WGS84 = (
    ROOT
    / "exports"
    / "v2_multiregion"
    / "bornholm"
    / "landmask"
    / "bornholm_dagi_landsdel_landmask_wgs84.geojson"
)
WORKING_CRS = "EPSG:25833"
WEB_CRS = "EPSG:4326"
QA_LAYERS = ["strand_protection", "coastal_zone_3km"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_source_config(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["layer_key"]: row for row in csv.DictReader(handle)}


def read_vector(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    gdf = gdf.loc[gdf.geometry.notna()].copy()
    if gdf.crs is None:
        gdf = gdf.set_crs(WORKING_CRS, allow_override=True)
    gdf = gdf.to_crs(WORKING_CRS)
    gdf.geometry = gdf.geometry.map(lambda geom: make_valid(geom) if geom is not None else geom)
    return gdf.loc[~gdf.geometry.is_empty].copy()


def export_wgs84(gdf: gpd.GeoDataFrame, path: Path) -> None:
    if path.exists():
        path.unlink()
    gdf.to_crs(WEB_CRS).to_file(path, driver="GeoJSON")


def copy_if_exists(source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return True


def distance_compare(layer_id: str, new_assets: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    old_path = OLD_ASSETS / "distance_tables" / f"{layer_id}.csv"
    new_path = new_assets / "distance_tables" / f"{layer_id}.csv"
    old = pd.read_csv(old_path) if old_path.exists() else pd.DataFrame(columns=["hex_id", "distance_m", "intersects"])
    new = pd.read_csv(new_path) if new_path.exists() else pd.DataFrame(columns=["hex_id", "distance_m", "intersects"])
    old = old.rename(columns={"distance_m": "old_distance_m", "intersects": "old_intersects"})
    new = new.rename(columns={"distance_m": "new_distance_m", "intersects": "new_intersects"})
    joined = new.merge(old[["hex_id", "old_distance_m", "old_intersects"]], on="hex_id", how="left")
    joined["old_intersects"] = joined["old_intersects"].fillna(False).astype(bool)
    joined["new_intersects"] = joined["new_intersects"].fillna(False).astype(bool)
    joined["changed_intersection"] = joined["old_intersects"] != joined["new_intersects"]
    summary = {
        "layer_id": layer_id,
        "new_hex_rows": int(len(new)),
        "old_rows_matching_new_hexes": int(joined["old_distance_m"].notna().sum()),
        "old_intersecting_hexes": int(joined["old_intersects"].sum()),
        "new_intersecting_hexes": int(joined["new_intersects"].sum()),
        "changed_intersection_hexes": int(joined["changed_intersection"].sum()),
        "old_zero_distance_hexes": int((pd.to_numeric(joined["old_distance_m"], errors="coerce") == 0).sum()),
        "new_zero_distance_hexes": int((pd.to_numeric(joined["new_distance_m"], errors="coerce") == 0).sum()),
    }
    return joined, summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = read_json(NEW_REGISTRY)
    source_config = read_source_config(ROOT / registry["source_config_csv"])
    new_assets = ROOT / registry["asset_dir"]
    landmask = read_vector(Path(registry["landmask_source_path"]))
    landmask_union = gpd.GeoDataFrame({"name": ["DAGI Landsdel landmask"]}, geometry=[landmask.union_all()], crs=WORKING_CRS)

    index_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, Any]] = []

    if copy_if_exists(LANDMASK_WGS84, OUT_DIR / "bornholm_dagi_landsdel_landmask_wgs84.geojson"):
        index_rows.append(
            {
                "layer": "landmask",
                "file": "bornholm_dagi_landsdel_landmask_wgs84.geojson",
                "meaning": "Active DAGI Landsdel landmask used for the refreshed Bornholm app extent.",
            }
        )

    layer_specs = {item["id"]: item for item in registry["layers"]}
    for layer_id in QA_LAYERS:
        spec = layer_specs[layer_id]
        source_path = Path(source_config[spec["layer_key"]]["source_path"])
        raw = read_vector(source_path)
        clipped = gpd.clip(raw, landmask_union, keep_geom_type=False)
        clipped = clipped.loc[clipped.geometry.notna()].copy()
        clipped.geometry = clipped.geometry.map(lambda geom: make_valid(geom) if geom is not None else geom)
        clipped = clipped.loc[~clipped.geometry.is_empty].copy()

        raw_file = OUT_DIR / f"{layer_id}_raw_source_wgs84.geojson"
        clipped_file = OUT_DIR / f"{layer_id}_exact_dagi_clip_wgs84.geojson"
        export_wgs84(raw, raw_file)
        export_wgs84(clipped, clipped_file)
        index_rows.extend(
            [
                {
                    "layer": layer_id,
                    "file": raw_file.name,
                    "meaning": "Original LABLAB source layer transformed to WGS84, not clipped.",
                },
                {
                    "layer": layer_id,
                    "file": clipped_file.name,
                    "meaning": "Exact source clipped to the DAGI Landsdel landmask, without display simplification.",
                },
            ]
        )

        old_copy = OUT_DIR / f"{layer_id}_old_prekvart_clip_display.geojson"
        new_copy = OUT_DIR / f"{layer_id}_new_dagi_clip_display.geojson"
        if copy_if_exists(OLD_ASSETS / "source_geojson" / f"{layer_id}.geojson", old_copy):
            index_rows.append(
                {
                    "layer": layer_id,
                    "file": old_copy.name,
                    "meaning": "Legacy app display layer clipped to the old Prekvart-derived landmask.",
                }
            )
        if copy_if_exists(new_assets / "source_geojson" / f"{layer_id}.geojson", new_copy):
            index_rows.append(
                {
                    "layer": layer_id,
                    "file": new_copy.name,
                    "meaning": "New app display layer clipped to DAGI Landsdel and simplified for web display.",
                }
            )

        compare, summary = distance_compare(layer_id, new_assets)
        compare_file = OUT_DIR / f"{layer_id}_distance_compare_by_hex.csv"
        compare.to_csv(compare_file, index=False)
        summary_rows.append(summary)
        index_rows.append(
            {
                "layer": layer_id,
                "file": compare_file.name,
                "meaning": "Per-hex old/new distance and intersection comparison for the active DAGI app hexes.",
            }
        )

    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "distance_compare_summary.csv", index=False)
    pd.DataFrame(index_rows).to_csv(OUT_DIR / "qgis_review_index.csv", index=False)
    print(f"Wrote QGIS QA package: {rel(OUT_DIR)}")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
