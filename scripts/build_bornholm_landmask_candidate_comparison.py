from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import h3
from pyproj import Transformer
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "exports" / "qgis_review" / "bornholm_landmask_candidate_comparison"

BASEMAP_DIR = Path(
    os.environ.get(
        "BORNHOLM_BASEMAP_DIR",
        r"D:\LABLAB_Energiforsk\Projekt SL01\Geodatakatalog_SL01\Utkommande_SL01\UT_Bornholm_SL01\Basmap_BOR",
    )
)

OLD_LANDMASK = ROOT / "docs" / "geocontext" / "potential_framework" / "data" / "bornholm_landmask" / "bornholm_landmask_wgs84.geojson"
CURRENT_R9_DISPLAY = ROOT / "exports" / "v2_multiregion" / "bornholm" / "h3_display_geometries" / "bornholm_h3_res_9_land_clipped.geojson"
LANDSCAPE_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_lablab_landscape_r9.csv"
SCORE_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_establishment_placement_score_r9.csv"
SOCIAL_CSV = ROOT / "exports" / "v2_multiregion" / "bornholm" / "bornholm_synthetic_social_acceptance_r9.csv"

CANDIDATES = [
    {
        "id": "dagi_kommunind_bornholm",
        "label": "DAGI KommunIND Bornholm",
        "path": BASEMAP_DIR / "DAGI_KommunIND_Scale10000_BOL_33.shp",
        "filter_column": "navn",
        "filter_value": "Bornholm",
        "note": "Municipality boundary filtered to navn=Bornholm. Source declares EPSG:25832.",
    },
    {
        "id": "dagi_landsdel_bornholm",
        "label": "DAGI Landsdel Bornholm",
        "path": BASEMAP_DIR / "DAGI_Landsdel_Scale10000_BOL_33.shp",
        "filter_column": "navn",
        "filter_value": "Bornholm",
        "note": "Single Bornholm landsdel polygon. Source declares EPSG:25833.",
    },
]

REFERENCE_LINES = [
    {
        "id": "gdv_kyst_coast_line",
        "label": "GD-V Kyst Coast Line",
        "path": BASEMAP_DIR / "GD-V_Kyst-Coast-Line_BOL_33.shp",
        "note": "Coastline reference only; line geometry is not used directly as a landmask.",
    }
]

TO_25833 = Transformer.from_crs(4326, 25833, always_xy=True)
FROM_25833 = Transformer.from_crs(25833, 4326, always_xy=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def clean_geom(geom: Any) -> Any:
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        return geom
    return geom.buffer(0)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_geojson_features(path: Path, features: list[dict[str, Any]]) -> None:
    write_json(path, {"type": "FeatureCollection", "features": features})


def write_single_geom(path: Path, geom_25833: Any, props: dict[str, Any]) -> int:
    if geom_25833 is None or geom_25833.is_empty:
        write_geojson_features(path, [])
        return 0
    geom_4326 = transform(FROM_25833.transform, clean_geom(geom_25833))
    write_geojson_features(
        path,
        [
            {
                "type": "Feature",
                "geometry": mapping(geom_4326),
                "properties": props,
            }
        ],
    )
    return 1


def geom_ring_counts(geom: Any) -> dict[str, int]:
    if geom is None or geom.is_empty:
        return {"polygon_parts": 0, "interior_rings": 0}
    polygons = []
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    return {
        "polygon_parts": len(polygons),
        "interior_rings": sum(len(poly.interiors) for poly in polygons),
    }


def load_old_mask() -> Any:
    old = gpd.read_file(OLD_LANDMASK).to_crs(25833)
    return clean_geom(unary_union(old.geometry))


def load_candidate(spec: dict[str, Any]) -> tuple[gpd.GeoDataFrame, Any]:
    path = Path(spec["path"])
    gdf = gpd.read_file(path)
    if spec.get("filter_column") and spec.get("filter_value") and spec["filter_column"] in gdf.columns:
        value = str(spec["filter_value"]).lower()
        gdf = gdf[gdf[spec["filter_column"]].astype(str).str.lower() == value].copy()
    if gdf.empty:
        raise ValueError(f"No candidate features after filter: {spec['id']}")
    metric = gdf.to_crs(25833)
    geom = clean_geom(unary_union(metric.geometry))
    return gdf, geom


def load_reference_line(spec: dict[str, Any]) -> Path | None:
    path = Path(spec["path"])
    if not path.exists():
        return None
    gdf = gpd.read_file(path).to_crs(4326)
    out_path = OUT_DIR / f"reference_{spec['id']}_wgs84.geojson"
    gdf.to_file(out_path, driver="GeoJSON")
    return out_path


def load_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def geojson_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for feature in load_geojson(path).get("features") or []:
        props = feature.get("properties") or {}
        value = str(props.get("hex_id") or props.get("h3_address") or "").strip()
        if value:
            ids.add(value)
    return ids


def csv_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            value = str(row.get("hex_id") or "").strip()
            if value:
                ids.add(value)
    return ids


def h3_polygon_25833(hex_id: str) -> Any:
    ring = [(float(lng), float(lat)) for lat, lng in h3.cell_to_boundary(hex_id)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return transform(TO_25833.transform, Polygon(ring))


def clipped_h3_features(hex_ids: set[str], mask_25833: Any) -> dict[str, dict[str, Any]]:
    features: dict[str, dict[str, Any]] = {}
    for hex_id in sorted(hex_ids):
        try:
            full_hex = h3_polygon_25833(hex_id)
        except Exception:
            continue
        clipped = clean_geom(full_hex.intersection(mask_25833))
        if clipped is None or clipped.is_empty:
            continue
        area_m2 = float(clipped.area)
        if area_m2 <= 1:
            continue
        clipped_4326 = transform(FROM_25833.transform, clipped)
        features[hex_id] = {
            "type": "Feature",
            "geometry": mapping(clipped_4326),
            "properties": {
                "hex_id": hex_id,
                "display_area_m2": area_m2,
            },
        }
    return features


def copy_features_by_id(source_path: Path, ids: set[str], review_issue: str) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for feature in load_geojson(source_path).get("features") or []:
        props = feature.get("properties") or {}
        value = str(props.get("hex_id") or props.get("h3_address") or "").strip()
        if value not in ids:
            continue
        new_props = dict(props)
        new_props["review_issue"] = review_issue
        feature["properties"] = new_props
        features.append(feature)
    return features


def add_review_props(features: list[dict[str, Any]], review_issue: str, candidate_id: str) -> list[dict[str, Any]]:
    result = []
    for feature in features:
        props = dict(feature.get("properties") or {})
        props["review_issue"] = review_issue
        props["candidate_id"] = candidate_id
        result.append({"type": "Feature", "geometry": feature.get("geometry"), "properties": props})
    return result


def build_candidate_package(
    spec: dict[str, Any],
    old_geom: Any,
    current_display_ids: set[str],
    source_universe_ids: set[str],
    current_extra_source_ids: set[str],
) -> dict[str, Any]:
    raw_gdf, candidate_geom = load_candidate(spec)
    candidate_id = str(spec["id"])
    source_crs = str(raw_gdf.crs)

    candidate_path = OUT_DIR / f"{candidate_id}_landmask_wgs84.geojson"
    outline_path = OUT_DIR / f"{candidate_id}_outline_wgs84.geojson"
    new_only_path = OUT_DIR / f"{candidate_id}_new_only_vs_old.geojson"
    old_only_path = OUT_DIR / f"{candidate_id}_old_only_vs_candidate.geojson"
    display_path = OUT_DIR / f"{candidate_id}_r9_display_from_source_universe.geojson"
    added_path = OUT_DIR / f"{candidate_id}_r9_added_vs_current_display.geojson"
    removed_path = OUT_DIR / f"{candidate_id}_r9_removed_vs_current_display.geojson"
    source_extra_inside_path = OUT_DIR / f"{candidate_id}_current_source_extras_now_inside.geojson"

    write_single_geom(
        candidate_path,
        candidate_geom,
        {
            "mask_id": candidate_id,
            "label": spec["label"],
            "source_path": rel(Path(spec["path"])),
            "source_crs": source_crs,
            "note": spec["note"],
            "area_km2": candidate_geom.area / 1e6,
        },
    )

    boundary = candidate_geom.boundary
    write_single_geom(
        outline_path,
        boundary,
        {
            "mask_id": candidate_id,
            "label": f"{spec['label']} outline",
            "source_path": rel(Path(spec["path"])),
            "source_crs": source_crs,
        },
    )

    new_only = clean_geom(candidate_geom.difference(old_geom))
    old_only = clean_geom(old_geom.difference(candidate_geom))
    overlap = clean_geom(old_geom.intersection(candidate_geom))
    write_single_geom(new_only_path, new_only, {"candidate_id": candidate_id, "review_issue": "candidate_land_not_in_old_mask"})
    write_single_geom(old_only_path, old_only, {"candidate_id": candidate_id, "review_issue": "old_mask_land_not_in_candidate"})

    candidate_display = clipped_h3_features(source_universe_ids, candidate_geom)
    candidate_display_ids = set(candidate_display)
    write_geojson_features(display_path, add_review_props(list(candidate_display.values()), "candidate_r9_display_from_source_universe", candidate_id))

    added_ids = candidate_display_ids - current_display_ids
    removed_ids = current_display_ids - candidate_display_ids
    source_extra_inside_ids = current_extra_source_ids & candidate_display_ids
    write_geojson_features(added_path, add_review_props([candidate_display[value] for value in sorted(added_ids)], "candidate_r9_added_vs_current_display", candidate_id))
    write_geojson_features(removed_path, copy_features_by_id(CURRENT_R9_DISPLAY, removed_ids, "current_r9_removed_by_candidate"))
    write_geojson_features(
        source_extra_inside_path,
        add_review_props([candidate_display[value] for value in sorted(source_extra_inside_ids)], "current_source_extra_inside_candidate_mask", candidate_id),
    )

    ring_counts = geom_ring_counts(candidate_geom)
    old_ring_counts = geom_ring_counts(old_geom)
    return {
        "candidate_id": candidate_id,
        "label": spec["label"],
        "source_path": rel(Path(spec["path"])),
        "source_exists": Path(spec["path"]).exists(),
        "source_crs": source_crs,
        "source_features_all": len(raw_gdf),
        "candidate_area_km2": round(candidate_geom.area / 1e6, 6),
        "candidate_perimeter_km": round(candidate_geom.length / 1000, 6),
        "old_area_km2": round(old_geom.area / 1e6, 6),
        "old_perimeter_km": round(old_geom.length / 1000, 6),
        "overlap_km2": round((overlap.area if overlap else 0.0) / 1e6, 6),
        "candidate_new_only_km2": round((new_only.area if new_only else 0.0) / 1e6, 6),
        "old_only_km2": round((old_only.area if old_only else 0.0) / 1e6, 6),
        "candidate_polygon_parts": ring_counts["polygon_parts"],
        "candidate_interior_rings": ring_counts["interior_rings"],
        "old_polygon_parts": old_ring_counts["polygon_parts"],
        "old_interior_rings": old_ring_counts["interior_rings"],
        "current_r9_display_count": len(current_display_ids),
        "candidate_r9_display_count": len(candidate_display_ids),
        "r9_added_vs_current_count": len(added_ids),
        "r9_removed_vs_current_count": len(removed_ids),
        "current_source_extras_now_inside_count": len(source_extra_inside_ids),
        "candidate_landmask": rel(candidate_path),
        "candidate_outline": rel(outline_path),
        "candidate_new_only_vs_old": rel(new_only_path),
        "old_only_vs_candidate": rel(old_only_path),
        "candidate_r9_display": rel(display_path),
        "candidate_r9_added_vs_current": rel(added_path),
        "candidate_r9_removed_vs_current": rel(removed_path),
        "current_source_extras_now_inside": rel(source_extra_inside_path),
        "note": spec["note"],
    }


def write_index(metrics: list[dict[str, Any]], reference_outputs: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = [
        {
            "sort_order": 10,
            "layer_name": "XYZ Tiles - Google Satellite or OSM",
            "path": "QGIS Browser > XYZ Tiles",
            "role": "basemap",
            "load": "manual",
            "style_hint": "Keep below all vector layers.",
            "notes": "Use the same basemap you used to spot the old-mask mismatch.",
        },
        {
            "sort_order": 20,
            "layer_name": "Old Prekvart landmask",
            "path": rel(OLD_LANDMASK),
            "role": "old_mask",
            "load": "yes",
            "style_hint": "Transparent fill, thin black or red outline.",
            "notes": "Current app/helper mask; known to have poor coastline alignment and interior rings.",
        },
        {
            "sort_order": 30,
            "layer_name": "Current R9 display",
            "path": rel(CURRENT_R9_DISPLAY),
            "role": "current_display",
            "load": "optional",
            "style_hint": "Transparent fill, thin gray outline.",
            "notes": "Current app display geometry derived from old mask.",
        },
    ]
    sort_order = 100
    for metric in metrics:
        label = metric["label"]
        for suffix, role, load, style, notes in [
            ("candidate_landmask", "candidate_mask", "yes", "Transparent fill, strong green outline.", "Candidate replacement mask."),
            ("candidate_outline", "candidate_outline", "yes", "No fill; 0.6-1.0 mm yellow/green line.", "Candidate boundary outline."),
            ("candidate_new_only_vs_old", "difference", "yes", "Green transparent fill.", "Area in candidate mask but not old mask."),
            ("old_only_vs_candidate", "difference", "yes", "Red transparent fill.", "Area in old mask but not candidate mask."),
            ("candidate_r9_added_vs_current", "r9_impact", "yes", "Green transparent fill.", "R9 source-universe cells added by candidate mask."),
            ("candidate_r9_removed_vs_current", "r9_impact", "yes", "Red transparent fill.", "Current R9 display cells removed by candidate mask."),
            ("current_source_extras_now_inside", "r9_impact", "yes", "Blue transparent fill.", "Current 24 source-extra rows that become inside candidate mask."),
            ("candidate_r9_display", "candidate_display", "optional", "Transparent fill, thin green outline.", "Candidate R9 display from existing source universe."),
        ]:
            rows.append(
                {
                    "sort_order": sort_order,
                    "layer_name": f"{label} - {suffix}",
                    "path": metric[suffix],
                    "role": role,
                    "load": load,
                    "style_hint": style,
                    "notes": notes,
                }
            )
            sort_order += 10
    for output in reference_outputs:
        rows.append(
            {
                "sort_order": sort_order,
                "layer_name": output["label"],
                "path": output["path"],
                "role": "reference",
                "load": "yes",
                "style_hint": "Thin bright cyan line.",
                "notes": output["note"],
            }
        )
        sort_order += 10
    write_csv(
        OUT_DIR / "qgis_candidate_comparison_index.csv",
        rows,
        ["sort_order", "layer_name", "path", "role", "load", "style_hint", "notes"],
    )


def write_readme(metrics: list[dict[str, Any]]) -> None:
    lines = [
        "# Bornholm Landmask Candidate Comparison",
        "",
        "Purpose: compare the current Prekvart-derived app landmask against better Bornholm boundary candidates before changing runtime data.",
        "",
        "Load checklist:",
        "",
        "- `qgis_candidate_comparison_index.csv`",
        "",
        "Candidate summary:",
        "",
    ]
    for metric in metrics:
        lines.extend(
            [
                f"## {metric['label']}",
                "",
                f"- Source: `{metric['source_path']}`",
                f"- Source CRS reported by file: `{metric['source_crs']}`",
                f"- Candidate area: {metric['candidate_area_km2']} km2",
                f"- Old-mask area: {metric['old_area_km2']} km2",
                f"- Candidate new-only area: {metric['candidate_new_only_km2']} km2",
                f"- Old-only area: {metric['old_only_km2']} km2",
                f"- Candidate interior rings: {metric['candidate_interior_rings']}",
                f"- Old-mask interior rings: {metric['old_interior_rings']}",
                f"- Candidate R9 display cells from existing source universe: {metric['candidate_r9_display_count']}",
                f"- Added vs current R9 display: {metric['r9_added_vs_current_count']}",
                f"- Removed vs current R9 display: {metric['r9_removed_vs_current_count']}",
                f"- Current source-extra cells now inside candidate: {metric['current_source_extras_now_inside_count']}",
                "",
            ]
        )
    lines.extend(
        [
            "Interpretation note:",
            "",
            "The candidate R9 display is built only from the existing Bornholm R9 source universe: current display IDs plus landscape/score/social rows. It is enough to measure runtime impact, but it is not a full fresh H3 coverage of every possible land cell.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old_geom = load_old_mask()
    current_display_ids = geojson_ids(CURRENT_R9_DISPLAY)
    landscape_ids = csv_ids(LANDSCAPE_CSV)
    score_ids = csv_ids(SCORE_CSV)
    social_ids = csv_ids(SOCIAL_CSV)
    source_universe_ids = current_display_ids | landscape_ids | score_ids | social_ids
    current_extra_source_ids = (landscape_ids | score_ids | social_ids) - current_display_ids

    metrics: list[dict[str, Any]] = []
    for spec in CANDIDATES:
        if not Path(spec["path"]).exists():
            print(f"Skipping missing candidate: {spec['id']} -> {spec['path']}")
            continue
        metrics.append(
            build_candidate_package(
                spec,
                old_geom,
                current_display_ids,
                source_universe_ids,
                current_extra_source_ids,
            )
        )

    reference_outputs: list[dict[str, Any]] = []
    for spec in REFERENCE_LINES:
        out_path = load_reference_line(spec)
        if out_path is not None:
            reference_outputs.append({"label": spec["label"], "path": rel(out_path), "note": spec["note"]})

    write_csv(
        OUT_DIR / "candidate_metrics.csv",
        metrics,
        [
            "candidate_id",
            "label",
            "source_path",
            "source_exists",
            "source_crs",
            "source_features_all",
            "candidate_area_km2",
            "candidate_perimeter_km",
            "old_area_km2",
            "old_perimeter_km",
            "overlap_km2",
            "candidate_new_only_km2",
            "old_only_km2",
            "candidate_polygon_parts",
            "candidate_interior_rings",
            "old_polygon_parts",
            "old_interior_rings",
            "current_r9_display_count",
            "candidate_r9_display_count",
            "r9_added_vs_current_count",
            "r9_removed_vs_current_count",
            "current_source_extras_now_inside_count",
            "candidate_landmask",
            "candidate_outline",
            "candidate_new_only_vs_old",
            "old_only_vs_candidate",
            "candidate_r9_display",
            "candidate_r9_added_vs_current",
            "candidate_r9_removed_vs_current",
            "current_source_extras_now_inside",
            "note",
        ],
    )
    write_index(metrics, reference_outputs)
    write_readme(metrics)
    write_json(
        OUT_DIR / "candidate_comparison_summary.json",
        {
            "source_universe_note": "Current display IDs union landscape/score/social R9 rows.",
            "current_r9_display_count": len(current_display_ids),
            "landscape_csv_count": len(landscape_ids),
            "score_csv_count": len(score_ids),
            "social_csv_count": len(social_ids),
            "source_universe_count": len(source_universe_ids),
            "current_source_extra_count": len(current_extra_source_ids),
            "candidate_count": len(metrics),
            "metrics": metrics,
            "reference_outputs": reference_outputs,
        },
    )
    print(f"Wrote Bornholm candidate comparison package: {rel(OUT_DIR)}")
    for metric in metrics:
        print(
            f"{metric['candidate_id']}: area={metric['candidate_area_km2']} km2, "
            f"R9 display={metric['candidate_r9_display_count']}, "
            f"added={metric['r9_added_vs_current_count']}, "
            f"removed={metric['r9_removed_vs_current_count']}, "
            f"source_extras_inside={metric['current_source_extras_now_inside_count']}"
        )


if __name__ == "__main__":
    main()
