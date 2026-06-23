from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import h3


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "exports" / "qgis_review" / "bornholm_r9_runtime_qa"

REGION = ROOT / "regions" / "bornholm" / "region.json"


def _manifest_path(path_value: str | None) -> Path:
    if not path_value:
        raise ValueError("Manifest path is empty.")
    path = Path(str(path_value))
    return path if path.is_absolute() else ROOT / path


REGION_CONFIG = json.loads(REGION.read_text(encoding="utf-8"))
LANDSCAPE_MANIFEST = _manifest_path(REGION_CONFIG.get("landscape_manifest"))
LANDSCAPE_CONFIG = json.loads(LANDSCAPE_MANIFEST.read_text(encoding="utf-8"))
SCORE_MANIFEST = _manifest_path((REGION_CONFIG.get("establishment_placement_score") or {}).get("manifest"))
SCORE_CONFIG = json.loads(SCORE_MANIFEST.read_text(encoding="utf-8"))
SOCIAL_MANIFEST = _manifest_path(REGION_CONFIG.get("social_acceptance_manifest"))
SOCIAL_CONFIG = json.loads(SOCIAL_MANIFEST.read_text(encoding="utf-8"))

DISPLAY_PATHS = {
    int(resolution): _manifest_path(path)
    for resolution, path in (REGION_CONFIG.get("h3_display_geometries") or {}).items()
}

LANDSCAPE_APP = _manifest_path(LANDSCAPE_CONFIG.get("landscape_geojson"))
LANDSCAPE_CSV = _manifest_path(LANDSCAPE_CONFIG.get("landscape_csv"))
SCORE_CSV = _manifest_path(SCORE_CONFIG.get("path") or (REGION_CONFIG.get("establishment_placement_score") or {}).get("path"))
SOCIAL_CSV = _manifest_path(SOCIAL_CONFIG.get("acceptance_csv"))

STRAND_PROTECTION = (
    ROOT
    / "docs"
    / "geocontext"
    / "acceptance_framework"
    / "data"
    / "prototype_assets"
    / "source_geojson"
    / "strand_protection.geojson"
)
COASTAL_ZONE = (
    ROOT
    / "docs"
    / "geocontext"
    / "acceptance_framework"
    / "data"
    / "prototype_assets"
    / "source_geojson"
    / "coastal_zone_3km.geojson"
)

DISPLAY_WITHOUT_LANDSCAPE = OUT_DIR / "bornholm_r9_display_without_landscape_app.geojson"
DISPLAY_WITHOUT_SCORE_SOCIAL = OUT_DIR / "bornholm_r9_display_without_score_social.geojson"
LANDSCAPE_ROWS_WITHOUT_DISPLAY = OUT_DIR / "bornholm_r9_landscape_csv_rows_without_display.geojson"
SCORE_ROWS_WITHOUT_DISPLAY = OUT_DIR / "bornholm_r9_score_rows_without_display.geojson"
SOCIAL_ROWS_WITHOUT_DISPLAY = OUT_DIR / "bornholm_r9_social_rows_without_display.geojson"
ANY_SOURCE_ROWS_WITHOUT_DISPLAY = OUT_DIR / "bornholm_r9_any_source_rows_without_display.geojson"

LANDSCAPE_FIELDS = [
    "landscape_type_id",
    "landscape_type_name",
    "class_km",
    "dominant_area_share_pct",
    "classified_hex_share_pct",
    "strandbeskyddelse_andel",
    "kustnara_zon_andel",
    "review_flag",
]
SCORE_FIELDS = [
    "wind_eligible",
    "solar_eligible",
    "wind_hard_stop",
    "solar_hard_stop",
    "wind_establishment_placement_score",
    "solar_establishment_placement_score",
    "wind_hard_stop_reasons",
    "solar_hard_stop_reasons",
    "wind_exclusion_reason",
    "solar_exclusion_reason",
    "coastal_hard_distance_m",
    "coastal_zone_distance_m",
]
SOCIAL_FIELDS = ["acceptance_low", "acceptance_medium", "acceptance_high"]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_geojson(path: Path) -> dict[str, Any]:
    return load_json(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_geojson(path: Path, features: list[dict[str, Any]]) -> None:
    write_json(path, {"type": "FeatureCollection", "features": features})


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hex_id = str(row.get("hex_id") or "").strip()
            if hex_id:
                rows[hex_id] = row
    return rows


def hex_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("hex_id") or props.get("h3_address") or "").strip()


def geojson_features_by_id(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for feature in load_geojson(path).get("features") or []:
        value = hex_id(feature)
        if value:
            result[value] = feature
    return result


def h3_parent_or_self(hex_value: str, resolution: int) -> str:
    if h3.get_resolution(hex_value) == resolution:
        return hex_value
    return h3.cell_to_parent(hex_value, resolution)


def h3_polygon(hex_value: str) -> dict[str, Any]:
    ring = [[float(lng), float(lat)] for lat, lng in h3.cell_to_boundary(hex_value)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def h3_center(hex_value: str) -> tuple[float, float]:
    lat, lng = h3.cell_to_latlng(hex_value)
    return float(lat), float(lng)


def take_fields(row: dict[str, Any] | None, fields: Iterable[str], prefix: str) -> dict[str, Any]:
    if not row:
        return {}
    return {f"{prefix}_{field}": row.get(field, "") for field in fields}


def display_review_feature(
    feature: dict[str, Any],
    issue: str,
    landscape_rows: dict[str, dict[str, str]],
    score_rows: dict[str, dict[str, str]],
    social_rows: dict[str, dict[str, str]],
    landscape_app_ids: set[str],
) -> dict[str, Any]:
    value = hex_id(feature)
    lat, lng = h3_center(value)
    props = dict(feature.get("properties") or {})
    props.update(
        {
            "review_issue": issue,
            "hex_id": value,
            "h3_resolution": h3.get_resolution(value),
            "center_lat": lat,
            "center_lng": lng,
            "in_landscape_app": value in landscape_app_ids,
            "in_landscape_csv": value in landscape_rows,
            "in_score_csv": value in score_rows,
            "in_social_csv": value in social_rows,
        }
    )
    props.update(take_fields(landscape_rows.get(value), LANDSCAPE_FIELDS, "landscape"))
    props.update(take_fields(score_rows.get(value), SCORE_FIELDS, "score"))
    props.update(take_fields(social_rows.get(value), SOCIAL_FIELDS, "social"))
    return {"type": "Feature", "geometry": feature.get("geometry"), "properties": props}


def source_review_feature(
    hex_value: str,
    issue: str,
    landscape_rows: dict[str, dict[str, str]],
    score_rows: dict[str, dict[str, str]],
    social_rows: dict[str, dict[str, str]],
    display_ids: set[str],
    source_name: str,
) -> dict[str, Any]:
    lat, lng = h3_center(hex_value)
    props: dict[str, Any] = {
        "review_issue": issue,
        "source_name": source_name,
        "hex_id": hex_value,
        "h3_resolution": h3.get_resolution(hex_value),
        "center_lat": lat,
        "center_lng": lng,
        "in_display_r9": hex_value in display_ids,
        "in_landscape_csv": hex_value in landscape_rows,
        "in_score_csv": hex_value in score_rows,
        "in_social_csv": hex_value in social_rows,
    }
    props.update(take_fields(landscape_rows.get(hex_value), LANDSCAPE_FIELDS, "landscape"))
    props.update(take_fields(score_rows.get(hex_value), SCORE_FIELDS, "score"))
    props.update(take_fields(social_rows.get(hex_value), SOCIAL_FIELDS, "social"))
    return {"type": "Feature", "geometry": h3_polygon(hex_value), "properties": props}


def summarize_ids(values: Iterable[str], limit: int = 40) -> str:
    ordered = sorted(values)
    if len(ordered) <= limit:
        return ";".join(ordered)
    return ";".join(ordered[:limit]) + f";...(+{len(ordered) - limit})"


def coverage_row(
    source_name: str,
    source_path: Path,
    display_ids: set[str],
    source_ids: set[str],
) -> dict[str, Any]:
    display_missing = display_ids - source_ids
    source_extra = source_ids - display_ids
    return {
        "source_name": source_name,
        "source_path": rel(source_path),
        "display_count": len(display_ids),
        "source_count": len(source_ids),
        "overlap_count": len(display_ids & source_ids),
        "display_missing_count": len(display_missing),
        "source_extra_count": len(source_extra),
        "display_missing_ids": summarize_ids(display_missing),
        "source_extra_ids": summarize_ids(source_extra),
    }


def rollup_row(
    source_name: str,
    source_path: Path,
    resolution: int,
    display_ids: set[str],
    source_ids: set[str],
) -> dict[str, Any]:
    source_parent_ids = {h3_parent_or_self(value, resolution) for value in source_ids}
    display_missing = display_ids - source_parent_ids
    source_extra = source_parent_ids - display_ids
    return {
        "source_name": source_name,
        "source_path": rel(source_path),
        "display_resolution": resolution,
        "display_count": len(display_ids),
        "source_parent_count": len(source_parent_ids),
        "overlap_count": len(display_ids & source_parent_ids),
        "display_missing_count": len(display_missing),
        "source_extra_count": len(source_extra),
        "display_missing_ids": summarize_ids(display_missing),
        "source_extra_ids": summarize_ids(source_extra),
    }


def qgis_index_rows(paths: dict[str, Path]) -> list[dict[str, Any]]:
    rows = [
        {
            "sort_order": 10,
            "layer_name": "Bornholm R9 active display geometry",
            "path": rel(DISPLAY_PATHS[9]),
            "role": "base_display",
            "load": "yes",
            "notes": "Land-clipped display geometry used by the V2 app at R9.",
        },
        {
            "sort_order": 20,
            "layer_name": "Bornholm LABLAB landscape app layer",
            "path": rel(LANDSCAPE_APP),
            "role": "active_landscape",
            "load": "yes",
            "notes": "Current R9 landscape app GeoJSON, already clipped to the app display contract.",
        },
        {
            "sort_order": 30,
            "layer_name": "Display cells without landscape app properties",
            "path": rel(paths["display_without_landscape"]),
            "role": "gap_review",
            "load": "yes",
            "notes": "R9 display cells missing from the current landscape app GeoJSON.",
        },
        {
            "sort_order": 40,
            "layer_name": "Display cells without score or social rows",
            "path": rel(paths["display_without_score_social"]),
            "role": "gap_review",
            "load": "yes",
            "notes": "R9 display cells missing from establishment score and/or social acceptance tables.",
        },
        {
            "sort_order": 50,
            "layer_name": "Landscape CSV rows outside R9 display",
            "path": rel(paths["landscape_rows_without_display"]),
            "role": "source_extra_review",
            "load": "yes",
            "notes": "Full H3 polygons generated from landscape CSV rows that are outside the clipped display geometry.",
        },
        {
            "sort_order": 60,
            "layer_name": "Score rows outside R9 display",
            "path": rel(paths["score_rows_without_display"]),
            "role": "source_extra_review",
            "load": "yes",
            "notes": "Full H3 polygons generated from score rows outside the clipped display geometry.",
        },
        {
            "sort_order": 70,
            "layer_name": "Social rows outside R9 display",
            "path": rel(paths["social_rows_without_display"]),
            "role": "source_extra_review",
            "load": "yes",
            "notes": "Full H3 polygons generated from social rows outside the clipped display geometry.",
        },
        {
            "sort_order": 80,
            "layer_name": "Any source row outside R9 display",
            "path": rel(paths["any_source_rows_without_display"]),
            "role": "source_extra_review",
            "load": "optional",
            "notes": "Union of landscape, score, and social rows outside display, with presence flags.",
        },
        {
            "sort_order": 90,
            "layer_name": "Strand protection",
            "path": rel(STRAND_PROTECTION),
            "role": "coastal_hard_constraint",
            "load": "yes",
            "notes": "Current acceptance source GeoJSON for strand_protection.",
        },
        {
            "sort_order": 100,
            "layer_name": "Coastal zone 3 km",
            "path": rel(COASTAL_ZONE),
            "role": "coastal_soft_context",
            "load": "yes",
            "notes": "Current acceptance source GeoJSON for coastal_zone_3km.",
        },
    ]
    return rows


def write_readme(summary: dict[str, Any]) -> None:
    text = f"""# Bornholm R9 Runtime QA Package

Created: {summary["created_at"]}

This package is a focused QGIS review aid for the Bornholm R9 app contract. It compares the active R9 display geometry against:

- LABLAB landscape app GeoJSON
- LABLAB landscape CSV source table
- establishment placement score CSV
- synthetic social acceptance CSV
- strand_protection and coastal_zone_3km source GeoJSON layers

Recommended QGIS load order is in `qgis_review_index.csv`.

Key counts:

- R9 display cells: {summary["counts"]["display_r9"]}
- landscape app cells: {summary["counts"]["landscape_app"]}
- landscape CSV rows: {summary["counts"]["landscape_csv"]}
- score CSV rows: {summary["counts"]["score_csv"]}
- social CSV rows: {summary["counts"]["social_csv"]}
- display cells missing landscape app properties: {summary["counts"]["display_without_landscape_app"]}
- display cells missing score or social rows: {summary["counts"]["display_without_score_or_social"]}
- source rows outside display union: {summary["counts"]["any_source_rows_without_display"]}

Review focus:

1. Load `bornholm_r9_display_without_landscape_app.geojson` and `bornholm_r9_display_without_score_social.geojson` on top of the R9 display geometry.
2. Load `strand_protection.geojson` and `coastal_zone_3km.geojson`.
3. Check whether the display gaps and outside-display source rows line up with shore slivers, offshore trims, or a true source/projection issue.
4. Do not patch Bornholm by forcing parity with Trondelag. If there is a Bornholm-specific issue, fix the regional data flow.
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    region = load_json(REGION)
    display_features = geojson_features_by_id(DISPLAY_PATHS[9])
    display_ids = set(display_features)
    landscape_app_features = geojson_features_by_id(LANDSCAPE_APP)
    landscape_app_ids = set(landscape_app_features)
    landscape_rows = read_csv_rows(LANDSCAPE_CSV)
    score_rows = read_csv_rows(SCORE_CSV)
    social_rows = read_csv_rows(SOCIAL_CSV)

    display_without_landscape_ids = display_ids - landscape_app_ids
    display_without_score_social_ids = {
        value for value in display_ids if value not in score_rows or value not in social_rows
    }
    landscape_extra_ids = set(landscape_rows) - display_ids
    score_extra_ids = set(score_rows) - display_ids
    social_extra_ids = set(social_rows) - display_ids
    any_source_extra_ids = landscape_extra_ids | score_extra_ids | social_extra_ids

    display_without_landscape = [
        display_review_feature(
            display_features[value],
            "display_without_landscape_app_properties",
            landscape_rows,
            score_rows,
            social_rows,
            landscape_app_ids,
        )
        for value in sorted(display_without_landscape_ids)
    ]
    display_without_score_social = [
        display_review_feature(
            display_features[value],
            "display_without_score_or_social_rows",
            landscape_rows,
            score_rows,
            social_rows,
            landscape_app_ids,
        )
        for value in sorted(display_without_score_social_ids)
    ]
    landscape_extra_features = [
        source_review_feature(
            value,
            "landscape_csv_row_without_display_geometry",
            landscape_rows,
            score_rows,
            social_rows,
            display_ids,
            "landscape_csv",
        )
        for value in sorted(landscape_extra_ids)
    ]
    score_extra_features = [
        source_review_feature(
            value,
            "score_row_without_display_geometry",
            landscape_rows,
            score_rows,
            social_rows,
            display_ids,
            "score_csv",
        )
        for value in sorted(score_extra_ids)
    ]
    social_extra_features = [
        source_review_feature(
            value,
            "social_row_without_display_geometry",
            landscape_rows,
            score_rows,
            social_rows,
            display_ids,
            "social_csv",
        )
        for value in sorted(social_extra_ids)
    ]
    any_source_extra_features = [
        source_review_feature(
            value,
            "any_source_row_without_display_geometry",
            landscape_rows,
            score_rows,
            social_rows,
            display_ids,
            "source_union",
        )
        for value in sorted(any_source_extra_ids)
    ]

    write_geojson(DISPLAY_WITHOUT_LANDSCAPE, display_without_landscape)
    write_geojson(DISPLAY_WITHOUT_SCORE_SOCIAL, display_without_score_social)
    write_geojson(LANDSCAPE_ROWS_WITHOUT_DISPLAY, landscape_extra_features)
    write_geojson(SCORE_ROWS_WITHOUT_DISPLAY, score_extra_features)
    write_geojson(SOCIAL_ROWS_WITHOUT_DISPLAY, social_extra_features)
    write_geojson(ANY_SOURCE_ROWS_WITHOUT_DISPLAY, any_source_extra_features)

    coverage_sources = {
        "landscape_app_geojson": (LANDSCAPE_APP, landscape_app_ids),
        "landscape_csv": (LANDSCAPE_CSV, set(landscape_rows)),
        "score_csv": (SCORE_CSV, set(score_rows)),
        "social_csv": (SOCIAL_CSV, set(social_rows)),
    }
    coverage_rows = [
        coverage_row(name, source_path, display_ids, source_ids)
        for name, (source_path, source_ids) in coverage_sources.items()
    ]
    write_csv(
        OUT_DIR / "runtime_id_coverage.csv",
        coverage_rows,
        [
            "source_name",
            "source_path",
            "display_count",
            "source_count",
            "overlap_count",
            "display_missing_count",
            "source_extra_count",
            "display_missing_ids",
            "source_extra_ids",
        ],
    )

    display_by_resolution = {resolution: set(geojson_features_by_id(path)) for resolution, path in DISPLAY_PATHS.items()}
    rollup_rows = [
        rollup_row(name, source_path, resolution, display_by_resolution[resolution], source_ids)
        for name, (source_path, source_ids) in coverage_sources.items()
        for resolution in sorted(DISPLAY_PATHS, reverse=True)
    ]
    write_csv(
        OUT_DIR / "rollup_coverage.csv",
        rollup_rows,
        [
            "source_name",
            "source_path",
            "display_resolution",
            "display_count",
            "source_parent_count",
            "overlap_count",
            "display_missing_count",
            "source_extra_count",
            "display_missing_ids",
            "source_extra_ids",
        ],
    )

    display_only_rows: list[dict[str, Any]] = []
    for value in sorted(display_without_landscape_ids | display_without_score_social_ids):
        lat, lng = h3_center(value)
        feature = display_features[value]
        display_only_rows.append(
            {
                "hex_id": value,
                "display_area_m2": (feature.get("properties") or {}).get("display_area_m2", ""),
                "center_lat": lat,
                "center_lng": lng,
                "in_landscape_app": value in landscape_app_ids,
                "in_landscape_csv": value in landscape_rows,
                "in_score_csv": value in score_rows,
                "in_social_csv": value in social_rows,
                "wind_hard_stop": score_rows.get(value, {}).get("wind_hard_stop", ""),
                "solar_hard_stop": score_rows.get(value, {}).get("solar_hard_stop", ""),
                "wind_hard_stop_reasons": score_rows.get(value, {}).get("wind_hard_stop_reasons", ""),
                "solar_hard_stop_reasons": score_rows.get(value, {}).get("solar_hard_stop_reasons", ""),
                "coastal_hard_distance_m": score_rows.get(value, {}).get("coastal_hard_distance_m", ""),
                "coastal_zone_distance_m": score_rows.get(value, {}).get("coastal_zone_distance_m", ""),
            }
        )
    write_csv(
        OUT_DIR / "display_only_cells.csv",
        display_only_rows,
        [
            "hex_id",
            "display_area_m2",
            "center_lat",
            "center_lng",
            "in_landscape_app",
            "in_landscape_csv",
            "in_score_csv",
            "in_social_csv",
            "wind_hard_stop",
            "solar_hard_stop",
            "wind_hard_stop_reasons",
            "solar_hard_stop_reasons",
            "coastal_hard_distance_m",
            "coastal_zone_distance_m",
        ],
    )

    source_extra_rows: list[dict[str, Any]] = []
    for value in sorted(any_source_extra_ids):
        lat, lng = h3_center(value)
        source_extra_rows.append(
            {
                "hex_id": value,
                "center_lat": lat,
                "center_lng": lng,
                "in_landscape_csv": value in landscape_rows,
                "in_score_csv": value in score_rows,
                "in_social_csv": value in social_rows,
                "landscape_type_id": landscape_rows.get(value, {}).get("landscape_type_id", ""),
                "landscape_type_name": landscape_rows.get(value, {}).get("landscape_type_name", ""),
                "class_km": landscape_rows.get(value, {}).get("class_km", ""),
                "wind_hard_stop": score_rows.get(value, {}).get("wind_hard_stop", ""),
                "solar_hard_stop": score_rows.get(value, {}).get("solar_hard_stop", ""),
                "wind_hard_stop_reasons": score_rows.get(value, {}).get("wind_hard_stop_reasons", ""),
                "solar_hard_stop_reasons": score_rows.get(value, {}).get("solar_hard_stop_reasons", ""),
                "coastal_hard_distance_m": score_rows.get(value, {}).get("coastal_hard_distance_m", ""),
                "coastal_zone_distance_m": score_rows.get(value, {}).get("coastal_zone_distance_m", ""),
            }
        )
    write_csv(
        OUT_DIR / "source_rows_without_display.csv",
        source_extra_rows,
        [
            "hex_id",
            "center_lat",
            "center_lng",
            "in_landscape_csv",
            "in_score_csv",
            "in_social_csv",
            "landscape_type_id",
            "landscape_type_name",
            "class_km",
            "wind_hard_stop",
            "solar_hard_stop",
            "wind_hard_stop_reasons",
            "solar_hard_stop_reasons",
            "coastal_hard_distance_m",
            "coastal_zone_distance_m",
        ],
    )

    output_paths = {
        "display_without_landscape": DISPLAY_WITHOUT_LANDSCAPE,
        "display_without_score_social": DISPLAY_WITHOUT_SCORE_SOCIAL,
        "landscape_rows_without_display": LANDSCAPE_ROWS_WITHOUT_DISPLAY,
        "score_rows_without_display": SCORE_ROWS_WITHOUT_DISPLAY,
        "social_rows_without_display": SOCIAL_ROWS_WITHOUT_DISPLAY,
        "any_source_rows_without_display": ANY_SOURCE_ROWS_WITHOUT_DISPLAY,
    }
    write_csv(
        OUT_DIR / "qgis_review_index.csv",
        qgis_index_rows(output_paths),
        ["sort_order", "layer_name", "path", "role", "load", "notes"],
    )

    summary = {
        "created_at": date.today().isoformat(),
        "region_id": "bornholm",
        "native_crs": region.get("native_crs"),
        "runtime_intent": "Review Bornholm R9 display/source alignment before changing strandskydd or coastal logic.",
        "inputs": {
            "region": rel(REGION),
            "display_r9": rel(DISPLAY_PATHS[9]),
            "landscape_app": rel(LANDSCAPE_APP),
            "landscape_csv": rel(LANDSCAPE_CSV),
            "landscape_manifest": rel(LANDSCAPE_MANIFEST),
            "score_csv": rel(SCORE_CSV),
            "score_manifest": rel(SCORE_MANIFEST),
            "social_csv": rel(SOCIAL_CSV),
            "social_manifest": rel(SOCIAL_MANIFEST),
            "strand_protection": rel(STRAND_PROTECTION),
            "coastal_zone_3km": rel(COASTAL_ZONE),
        },
        "outputs": {name: rel(path) for name, path in output_paths.items()},
        "counts": {
            "display_r9": len(display_ids),
            "landscape_app": len(landscape_app_ids),
            "landscape_csv": len(landscape_rows),
            "score_csv": len(score_rows),
            "social_csv": len(social_rows),
            "display_without_landscape_app": len(display_without_landscape_ids),
            "display_without_score_or_social": len(display_without_score_social_ids),
            "landscape_csv_rows_without_display": len(landscape_extra_ids),
            "score_rows_without_display": len(score_extra_ids),
            "social_rows_without_display": len(social_extra_ids),
            "any_source_rows_without_display": len(any_source_extra_ids),
        },
        "display_gap_ids": {
            "without_landscape_app": sorted(display_without_landscape_ids),
            "without_score_or_social": sorted(display_without_score_social_ids),
        },
        "source_extra_ids": {
            "landscape_csv": sorted(landscape_extra_ids),
            "score_csv": sorted(score_extra_ids),
            "social_csv": sorted(social_extra_ids),
            "any_source_union": sorted(any_source_extra_ids),
        },
        "interpretation": [
            "The current app display contract is land-clipped R9 geometry.",
            "Rows outside that display contract should be reviewed as source/runtime alignment, not automatically added to the app.",
            "The strand_protection layer should be visually checked against the gap layers before changing coastal hard-stop behavior.",
        ],
    }
    write_json(OUT_DIR / "runtime_contract_summary.json", summary)
    write_readme(summary)

    print(f"Wrote Bornholm R9 QA package: {rel(OUT_DIR)}")
    print(json.dumps(summary["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
