from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "apps" / "acceptance_model" / "registry_bornholm.json"
WORKING_CRS = "EPSG:25833"
WEB_CRS = "EPSG:4326"


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_source_config(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["layer_key"]: row for row in rows}


def slugify_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def classify_road_class(value: Any) -> str:
    text = slugify_text(value)
    if re.search(r"stor|motor|major|primary", text):
        return "large"
    if re.search(r"mellem|mellan|medium|secondary", text):
        return "medium"
    if re.search(r"lille|small|minor|local|residential", text):
        return "small"
    return "other"


def apply_registry_filter(gdf: gpd.GeoDataFrame, spec: dict[str, Any]) -> gpd.GeoDataFrame:
    field = str(spec.get("filter_field") or "")
    value = str(spec.get("filter_value") or "")
    mode = str(spec.get("filter_mode") or "field_equals")
    if not field or not value:
        return gdf
    if field not in gdf.columns:
        raise KeyError(f"Filter field not found: {field}")

    if mode == "derived_road_class":
        keep = gdf[field].map(classify_road_class).map(slugify_text) == slugify_text(value)
        return gdf.loc[keep].copy()
    if mode == "field_equals":
        keep = gdf[field].map(slugify_text) == slugify_text(value)
        return gdf.loc[keep].copy()
    if mode == "field_in":
        values = {slugify_text(item) for item in str(value).split("|") if str(item).strip()}
        keep = gdf[field].map(slugify_text).isin(values)
        return gdf.loc[keep].copy()
    raise ValueError(f"Unsupported filter mode: {mode}")


def read_vector(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.empty:
        return gdf
    gdf = gdf.loc[gdf.geometry.notna()].copy()
    if gdf.crs is None:
        gdf = gdf.set_crs(WORKING_CRS, allow_override=True)
    gdf = gdf.to_crs(WORKING_CRS)
    gdf.geometry = gdf.geometry.map(lambda geom: make_valid(geom) if geom is not None else geom)
    return gdf.loc[~gdf.geometry.is_empty].copy()


def clip_to_landmask(gdf: gpd.GeoDataFrame, landmask: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    clipped = gpd.clip(gdf, landmask, keep_geom_type=False)
    if clipped.empty:
        return clipped
    clipped = clipped.loc[clipped.geometry.notna()].copy()
    clipped.geometry = clipped.geometry.map(lambda geom: make_valid(geom) if geom is not None else geom)
    return clipped.loc[~clipped.geometry.is_empty].copy()


def geometry_family(gdf: gpd.GeoDataFrame) -> str:
    if gdf.empty:
        return "empty"
    types = {str(value).upper() for value in gdf.geometry.geom_type.dropna().unique()}
    if types and all("POINT" in value for value in types):
        return "point"
    if types and all("LINE" in value for value in types):
        return "line"
    return "polygon"


def nearest_distance(centroids: list[BaseGeometry], source_geoms: list[BaseGeometry]) -> list[float]:
    if not source_geoms:
        return [math.inf for _ in centroids]
    tree = STRtree(source_geoms)
    distances: list[float] = []
    for geom in centroids:
        nearest_idx = tree.nearest(geom)
        if nearest_idx is None:
            distances.append(math.inf)
            continue
        distances.append(float(geom.distance(source_geoms[int(nearest_idx)])))
    return distances


def intersects_any(hex_geoms: list[BaseGeometry], source_geoms: list[BaseGeometry]) -> list[bool]:
    if not source_geoms:
        return [False for _ in hex_geoms]
    tree = STRtree(source_geoms)
    return [len(tree.query(geom, predicate="intersects")) > 0 for geom in hex_geoms]


def export_source_geojson(
    source: gpd.GeoDataFrame,
    spec: dict[str, Any],
    family: str,
    path: Path,
) -> None:
    display = source.copy()
    if family != "point":
        display.geometry = display.geometry.simplify(20, preserve_topology=True)
        display = display.loc[~display.geometry.is_empty].copy()
    display = gpd.GeoDataFrame(
        {
            "layer_id": [spec["id"]] * len(display),
            "label": [spec["label"]] * len(display),
            "tooltip_title": [f"Source layer: {spec['label']}"] * len(display),
            "tooltip_body": [
                f"{spec.get('note', '')}<br>Clipped to Bornholm DAGI Landsdel landmass."
            ]
            * len(display),
        },
        geometry=display.geometry,
        crs=source.crs,
    ).to_crs(WEB_CRS)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    display.to_file(path, driver="GeoJSON")


def write_distance_table(
    hex_ids: pd.Series,
    hex_geoms: list[BaseGeometry],
    centroids: list[BaseGeometry],
    source: gpd.GeoDataFrame,
    path: Path,
) -> None:
    source_geoms = [geom for geom in source.geometry if geom is not None and not geom.is_empty]
    distances = nearest_distance(centroids, source_geoms)
    intersections = intersects_any(hex_geoms, source_geoms)
    frame = pd.DataFrame(
        {
            "hex_id": hex_ids.astype(str).tolist(),
            "distance_m": [round(value, 1) if math.isfinite(value) else value for value in distances],
            "intersects": intersections,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def main() -> int:
    registry = read_registry()
    source_config = read_source_config(ROOT / registry["source_config_csv"])
    asset_dir = ROOT / registry["asset_dir"]
    source_dir = asset_dir / "source_geojson"
    distance_dir = asset_dir / "distance_tables"
    analysis_dir = asset_dir / "analysis_rds"
    source_dir.mkdir(parents=True, exist_ok=True)
    distance_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    landmask_path = Path(registry["landmask_source_path"])
    landmask = read_vector(landmask_path)
    landmask_union = gpd.GeoDataFrame(
        {"mask_id": [registry.get("landmask_label", "Bornholm landmask")]},
        geometry=[landmask.union_all()],
        crs=WORKING_CRS,
    )

    hex_path = ROOT / registry["hex_gpkg"]
    hexes = read_vector(hex_path)
    if "hex_id" not in hexes.columns:
        raise KeyError(f"Hex source is missing hex_id: {hex_path}")
    hexes = hexes[["hex_id", "geometry"]].copy()
    hexes["hex_id"] = hexes["hex_id"].astype(str)
    hex_geoms = list(hexes.geometry)
    centroids = list(hexes.representative_point())

    rows: list[dict[str, Any]] = []
    for spec in registry["layers"]:
        layer_id = spec["id"]
        layer_key = spec["layer_key"]
        print(f"Exporting {layer_id} ...", flush=True)

        source_row = source_config.get(layer_key, {})
        source_path = Path(str(source_row.get("source_path", "")))
        base_row = {
            "layer_id": layer_id,
            "layer_key": layer_key,
            "label": spec["label"],
            "group_id": spec["group_id"],
            "source_path": source_path.as_posix() if str(source_path) else "",
            "source_exists": source_path.exists(),
            "geometry_family": "",
            "feature_count": 0,
            "geojson_path": "",
            "distance_path": "",
            "analysis_rds_path": "",
            "analysis_base_buffer_m": 0,
            "status": "missing_source",
            "message": "Source path missing or unreadable.",
        }

        if not source_path.exists():
            rows.append(base_row)
            continue

        try:
            source = read_vector(source_path)
            source = apply_registry_filter(source, spec)
            source = clip_to_landmask(source, landmask_union)
            if source.empty:
                base_row.update(
                    {
                        "source_exists": True,
                        "geometry_family": "empty",
                        "status": "empty_after_filter",
                        "message": "Source layer contains no features after filtering and DAGI landmask clipping.",
                    }
                )
                rows.append(base_row)
                continue

            family = geometry_family(source)
            geojson_path = source_dir / f"{layer_id}.geojson"
            distance_path = distance_dir / f"{layer_id}.csv"
            export_source_geojson(source, spec, family, geojson_path)
            write_distance_table(hexes["hex_id"], hex_geoms, centroids, source, distance_path)

            base_row.update(
                {
                    "source_exists": True,
                    "geometry_family": family,
                    "feature_count": int(len(source)),
                    "geojson_path": repo_rel(geojson_path),
                    "distance_path": repo_rel(distance_path),
                    "status": "ok",
                    "message": "",
                }
            )
            rows.append(base_row)
        except Exception as exc:
            base_row.update({"source_exists": True, "status": "read_error", "message": str(exc)})
            rows.append(base_row)

    manifest_path = asset_dir / "asset_manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    print(f"Wrote asset manifest: {repo_rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
