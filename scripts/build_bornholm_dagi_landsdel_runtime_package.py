from __future__ import annotations

import csv
import json
import math
import os
from datetime import date
from pathlib import Path
from typing import Any

import geopandas as gpd
import h3
from pyproj import Transformer
from shapely.geometry import Polygon, mapping
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
BASEMAP_DIR = Path(
    os.environ.get(
        "BORNHOLM_BASEMAP_DIR",
        r"D:\LABLAB_Energiforsk\Projekt SL01\Geodatakatalog_SL01\Utkommande_SL01\UT_Bornholm_SL01\Basmap_BOR",
    )
)

SOURCE_LANDMASK = BASEMAP_DIR / "DAGI_Landsdel_Scale10000_BOL_33.shp"
LANDSCAPE_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_lablab_landscape_r9.csv"
SCORE_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_establishment_placement_score_r9.csv"
SOCIAL_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_synthetic_social_acceptance_r9.csv"
CURRENT_R9_DISPLAY = ROOT / "exports" / "v2_multiregion" / "bornholm" / "h3_display_geometries" / "bornholm_h3_res_9_land_clipped.geojson"

OUT_ROOT = ROOT / "exports" / "v2_multiregion" / "bornholm"
LANDMASK_OUT = OUT_ROOT / "landmask" / "bornholm_dagi_landsdel_landmask_wgs84.geojson"
LANDMASK_OUTLINE_OUT = OUT_ROOT / "landmask" / "bornholm_dagi_landsdel_landmask_outline_wgs84.geojson"
DISPLAY_DIR = OUT_ROOT / "h3_display_geometries"
LANDSCAPE_APP_OUT = OUT_ROOT / "bornholm_lablab_landscape_r9_dagi_landsdel_app.geojson"
SUMMARY_OUT = OUT_ROOT / "bornholm_dagi_landsdel_runtime_summary.json"

DISPLAY_PATHS = {
    9: DISPLAY_DIR / "bornholm_h3_res_9_dagi_landsdel_land_clipped.geojson",
    8: DISPLAY_DIR / "bornholm_h3_res_8_dagi_landsdel_land_clipped.geojson",
    7: DISPLAY_DIR / "bornholm_h3_res_7_dagi_landsdel_land_clipped.geojson",
    6: DISPLAY_DIR / "bornholm_h3_res_6_dagi_landsdel_land_clipped.geojson",
}
DISPLAY_MASK_SIMPLIFY_TOLERANCE_M = 1.0

TO_25833 = Transformer.from_crs(4326, 25833, always_xy=True)
FROM_25833 = Transformer.from_crs(25833, 4326, always_xy=True)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean_geom(geom: Any) -> Any:
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        return geom
    return geom.buffer(0)


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_geojson(path: Path, features: list[dict[str, Any]]) -> None:
    write_json(path, {"type": "FeatureCollection", "features": features})


def csv_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hex_id = str(row.get("hex_id") or "").strip()
            if hex_id:
                rows[hex_id] = row
    return rows


def geojson_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for feature in read_geojson(path).get("features") or []:
        props = feature.get("properties") or {}
        value = str(props.get("hex_id") or props.get("h3_address") or "").strip()
        if value:
            ids.add(value)
    return ids


def typed_value(value: str) -> Any:
    text = str(value).strip()
    if text == "":
        return None
    if text == "True":
        return True
    if text == "False":
        return False
    try:
        number = float(text)
    except ValueError:
        return text
    if not math.isfinite(number):
        return text
    if "." not in text and "e" not in text.lower():
        try:
            return int(text)
        except ValueError:
            return number
    return number


def typed_props(row: dict[str, str]) -> dict[str, Any]:
    return {key: typed_value(value) for key, value in row.items()}


def h3_polygon_25833(hex_id: str) -> Any:
    ring = [(float(lng), float(lat)) for lat, lng in h3.cell_to_boundary(hex_id)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return transform(TO_25833.transform, Polygon(ring))


def clipped_h3_features(hex_ids: set[str], mask_25833: Any) -> dict[str, dict[str, Any]]:
    features: dict[str, dict[str, Any]] = {}
    for hex_id in sorted(hex_ids):
        full_hex = h3_polygon_25833(hex_id)
        clipped = clean_geom(full_hex.intersection(mask_25833))
        if clipped is None or clipped.is_empty:
            continue
        area_m2 = float(clipped.area)
        if area_m2 <= 1:
            continue
        geometry_4326 = transform(FROM_25833.transform, clipped)
        features[hex_id] = {
            "type": "Feature",
            "geometry": mapping(geometry_4326),
            "properties": {"hex_id": hex_id, "display_area_m2": area_m2},
        }
    return features


def parent_ids(hex_ids: set[str], resolution: int) -> set[str]:
    result: set[str] = set()
    for hex_id in hex_ids:
        current_resolution = h3.get_resolution(hex_id)
        if current_resolution == resolution:
            result.add(hex_id)
        elif current_resolution > resolution:
            result.add(h3.cell_to_parent(hex_id, resolution))
    return result


def load_landsdel_mask() -> tuple[Any, dict[str, Any]]:
    if not SOURCE_LANDMASK.exists():
        raise FileNotFoundError(f"DAGI Landsdel source not found: {SOURCE_LANDMASK}")
    source = gpd.read_file(SOURCE_LANDMASK)
    if "navn" in source.columns:
        selected = source[source["navn"].astype(str).str.lower() == "bornholm"].copy()
        if not selected.empty:
            source = selected
    metric = source.to_crs(25833)
    geom = clean_geom(unary_union(metric.geometry))
    metadata = {
        "source_path": str(SOURCE_LANDMASK),
        "source_crs": str(source.crs),
        "source_feature_count": int(len(source)),
        "mask_id": "bornholm_dagi_landsdel",
        "area_km2": float(geom.area / 1e6),
        "perimeter_km": float(geom.length / 1000),
    }
    return geom, metadata


def write_mask_outputs(mask_25833: Any, metadata: dict[str, Any]) -> None:
    mask_4326 = transform(FROM_25833.transform, mask_25833)
    write_geojson(
        LANDMASK_OUT,
        [
            {
                "type": "Feature",
                "geometry": mapping(mask_4326),
                "properties": {
                    "mask_id": metadata["mask_id"],
                    "source": "DAGI_Landsdel_Scale10000_BOL_33",
                    "source_path": metadata["source_path"],
                    "source_crs": metadata["source_crs"],
                    "area_km2": metadata["area_km2"],
                    "perimeter_km": metadata["perimeter_km"],
                    "created_at": date.today().isoformat(),
                },
            }
        ],
    )
    outline_4326 = transform(FROM_25833.transform, mask_25833.boundary)
    write_geojson(
        LANDMASK_OUTLINE_OUT,
        [
            {
                "type": "Feature",
                "geometry": mapping(outline_4326),
                "properties": {
                    "mask_id": metadata["mask_id"],
                    "source": "DAGI_Landsdel_Scale10000_BOL_33",
                    "source_crs": metadata["source_crs"],
                    "created_at": date.today().isoformat(),
                },
            }
        ],
    )


def build_landscape_app(display_r9: dict[str, dict[str, Any]], landscape_rows: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for hex_id in sorted(set(display_r9) & set(landscape_rows)):
        display_feature = display_r9[hex_id]
        props = typed_props(landscape_rows[hex_id])
        props["display_area_m2"] = display_feature["properties"]["display_area_m2"]
        props["landmask_source"] = "DAGI_Landsdel_Scale10000_BOL_33"
        features.append(
            {
                "type": "Feature",
                "geometry": display_feature["geometry"],
                "properties": props,
            }
        )
    return features


def main() -> None:
    mask_25833, mask_metadata = load_landsdel_mask()
    write_mask_outputs(mask_25833, mask_metadata)
    display_mask_25833 = clean_geom(mask_25833.simplify(DISPLAY_MASK_SIMPLIFY_TOLERANCE_M, preserve_topology=True))

    landscape_rows = csv_rows(LANDSCAPE_CSV)
    score_rows = csv_rows(SCORE_CSV)
    social_rows = csv_rows(SOCIAL_CSV)
    current_display_ids = geojson_ids(CURRENT_R9_DISPLAY)
    r9_source_universe = current_display_ids | set(landscape_rows) | set(score_rows) | set(social_rows)

    display_features_by_resolution: dict[int, dict[str, dict[str, Any]]] = {}
    for resolution, output_path in DISPLAY_PATHS.items():
        ids = r9_source_universe if resolution == 9 else parent_ids(r9_source_universe, resolution)
        display_features = clipped_h3_features(ids, display_mask_25833)
        display_features_by_resolution[resolution] = display_features
        write_geojson(output_path, list(display_features.values()))

    landscape_features = build_landscape_app(display_features_by_resolution[9], landscape_rows)
    write_geojson(LANDSCAPE_APP_OUT, landscape_features)

    display_r9_ids = set(display_features_by_resolution[9])
    summary = {
        "created_at": date.today().isoformat(),
        "region_id": "bornholm",
        "selected_landmask": "dagi_landsdel_bornholm",
        "landmask": {
            "source_path": str(SOURCE_LANDMASK),
            "source_crs": mask_metadata["source_crs"],
            "display_geojson": rel(LANDMASK_OUT),
            "outline_geojson": rel(LANDMASK_OUTLINE_OUT),
            "area_km2": mask_metadata["area_km2"],
            "perimeter_km": mask_metadata["perimeter_km"],
            "display_clip_simplify_tolerance_m": DISPLAY_MASK_SIMPLIFY_TOLERANCE_M,
            "display_clip_area_km2": float(display_mask_25833.area / 1e6),
            "display_clip_perimeter_km": float(display_mask_25833.length / 1000),
        },
        "source_universe": {
            "r9_source_universe_count": len(r9_source_universe),
            "current_r9_display_count": len(current_display_ids),
            "landscape_csv_rows": len(landscape_rows),
            "score_csv_rows": len(score_rows),
            "social_csv_rows": len(social_rows),
            "method": "Current R9 display IDs union landscape/score/social R9 rows; coarser displays use H3 parents of that R9 universe.",
        },
        "outputs": {
            "h3_display_geometries": {str(resolution): rel(path) for resolution, path in DISPLAY_PATHS.items()},
            "landscape_app_geojson": rel(LANDSCAPE_APP_OUT),
        },
        "counts": {
            "display_geometries": {
                str(resolution): len(display_features_by_resolution[resolution])
                for resolution in sorted(display_features_by_resolution)
            },
            "landscape_app_features": len(landscape_features),
            "display_without_landscape_csv": len(display_r9_ids - set(landscape_rows)),
            "display_without_score_csv": len(display_r9_ids - set(score_rows)),
            "display_without_social_csv": len(display_r9_ids - set(social_rows)),
            "landscape_csv_rows_outside_display": len(set(landscape_rows) - display_r9_ids),
            "score_csv_rows_outside_display": len(set(score_rows) - display_r9_ids),
            "social_csv_rows_outside_display": len(set(social_rows) - display_r9_ids),
        },
    }
    write_json(SUMMARY_OUT, summary)
    print(f"Wrote Bornholm DAGI Landsdel runtime package: {rel(OUT_ROOT)}")
    print(json.dumps(summary["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
