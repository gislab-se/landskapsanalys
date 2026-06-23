from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "exports" / "qgis_review" / "bornholm_landmask_xyz_review"


def _repo_path(path_value: str | None) -> Path:
    if not path_value:
        raise ValueError("Configured path is empty.")
    path = Path(str(path_value))
    return path if path.is_absolute() else ROOT / path


REGION = ROOT / "regions" / "bornholm" / "region.json"
REGION_CONFIG = json.loads(REGION.read_text(encoding="utf-8"))
LANDMASK = _repo_path((REGION_CONFIG.get("land_mask") or {}).get("display_geojson"))
DISPLAY_R9 = _repo_path((REGION_CONFIG.get("h3_display_geometries") or {}).get("9"))
DISPLAY_R8 = _repo_path((REGION_CONFIG.get("h3_display_geometries") or {}).get("8"))
DISPLAY_WITHOUT_LANDSCAPE = OUT_DIR.parent / "bornholm_r9_runtime_qa" / "bornholm_r9_display_without_landscape_app.geojson"
DISPLAY_WITHOUT_SCORE_SOCIAL = OUT_DIR.parent / "bornholm_r9_runtime_qa" / "bornholm_r9_display_without_score_social.geojson"
ANY_SOURCE_WITHOUT_DISPLAY = OUT_DIR.parent / "bornholm_r9_runtime_qa" / "bornholm_r9_any_source_rows_without_display.geojson"
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

OUTLINE = OUT_DIR / "bornholm_landmask_outline_wgs84.geojson"
VERTICES = OUT_DIR / "bornholm_landmask_vertices_wgs84.geojson"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def feature_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_geojson(path).get("features") or [])


def iter_polygon_rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if geom_type == "Polygon":
        return coords
    if geom_type == "MultiPolygon":
        rings: list[list[list[float]]] = []
        for polygon in coords:
            rings.extend(polygon)
        return rings
    return []


def build_outline_and_vertices() -> dict[str, int]:
    landmask = read_geojson(LANDMASK)
    outline_features: list[dict[str, Any]] = []
    vertex_features: list[dict[str, Any]] = []
    vertex_count = 0

    for feature_index, feature in enumerate(landmask.get("features") or [], start=1):
        geometry = feature.get("geometry") or {}
        for ring_index, ring in enumerate(iter_polygon_rings(geometry), start=1):
            if len(ring) < 2:
                continue
            ring_role = "outer" if ring_index == 1 else "inner"
            outline_features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": ring},
                    "properties": {
                        "mask_id": (feature.get("properties") or {}).get("mask_id", "bornholm_land"),
                        "feature_index": feature_index,
                        "ring_index": ring_index,
                        "ring_role": ring_role,
                        "vertex_count": len(ring),
                    },
                }
            )
            for vertex_index, coord in enumerate(ring, start=1):
                vertex_count += 1
                vertex_features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": coord},
                        "properties": {
                            "mask_id": (feature.get("properties") or {}).get("mask_id", "bornholm_land"),
                            "feature_index": feature_index,
                            "ring_index": ring_index,
                            "ring_role": ring_role,
                            "vertex_index": vertex_index,
                        },
                    }
                )

    write_json(OUTLINE, {"type": "FeatureCollection", "features": outline_features})
    write_json(VERTICES, {"type": "FeatureCollection", "features": vertex_features})
    return {"outline_features": len(outline_features), "vertex_features": vertex_count}


def write_index() -> None:
    rows = [
        {
            "sort_order": 10,
            "layer_name": "XYZ Tiles - OpenStreetMap",
            "path": "QGIS Browser > XYZ Tiles > OpenStreetMap",
            "role": "visual_basemap",
            "load": "manual",
            "style_hint": "Keep below all review layers.",
            "notes": "Use this or another XYZ basemap to inspect coastline alignment.",
        },
        {
            "sort_order": 20,
            "layer_name": "Bornholm landmask fill",
            "path": rel(LANDMASK),
            "role": "landmask_source",
            "load": "yes",
            "style_hint": "Transparent fill, bright outline.",
            "notes": "Current WGS84 landmask used as source for display clipping.",
        },
        {
            "sort_order": 30,
            "layer_name": "Bornholm landmask outline",
            "path": rel(OUTLINE),
            "role": "landmask_outline",
            "load": "yes",
            "style_hint": "No fill; 0.6-1.0 mm red or yellow line.",
            "notes": "Derived outline of the landmask, easier to compare against XYZ coastline.",
        },
        {
            "sort_order": 40,
            "layer_name": "Bornholm landmask vertices",
            "path": rel(VERTICES),
            "role": "landmask_vertices",
            "load": "optional",
            "style_hint": "Small points; use only when inspecting odd corners.",
            "notes": "Every landmask ring vertex as a point.",
        },
        {
            "sort_order": 50,
            "layer_name": "Active R9 display cells",
            "path": rel(DISPLAY_R9),
            "role": "active_display_contract",
            "load": "optional",
            "style_hint": "Transparent fill, thin gray outline.",
            "notes": "The current app candidate/display geometry at R9.",
        },
        {
            "sort_order": 60,
            "layer_name": "Active R8 display cells",
            "path": rel(DISPLAY_R8),
            "role": "active_display_contract",
            "load": "optional",
            "style_hint": "Transparent fill, thin blue outline.",
            "notes": "Default display level in the Bornholm app.",
        },
        {
            "sort_order": 70,
            "layer_name": "Display without landscape app",
            "path": rel(DISPLAY_WITHOUT_LANDSCAPE),
            "role": "gap_review",
            "load": "yes",
            "style_hint": "Pink fill or outline.",
            "notes": "Two display cells missing landscape app properties.",
        },
        {
            "sort_order": 80,
            "layer_name": "Display without score/social",
            "path": rel(DISPLAY_WITHOUT_SCORE_SOCIAL),
            "role": "gap_review",
            "load": "yes",
            "style_hint": "Purple fill or outline.",
            "notes": "One tiny display cell missing score/social rows.",
        },
        {
            "sort_order": 90,
            "layer_name": "Source rows outside display",
            "path": rel(ANY_SOURCE_WITHOUT_DISPLAY),
            "role": "source_extra_review",
            "load": "yes",
            "style_hint": "Brown transparent fill.",
            "notes": "24 source rows that are outside the active display geometry.",
        },
        {
            "sort_order": 100,
            "layer_name": "Strand protection",
            "path": rel(STRAND_PROTECTION),
            "role": "coastal_hard_constraint",
            "load": "yes",
            "style_hint": "Transparent fill, strong blue/green outline.",
            "notes": "Use after landmask comparison to inspect the known strandskydd issue.",
        },
        {
            "sort_order": 110,
            "layer_name": "Coastal zone 3 km",
            "path": rel(COASTAL_ZONE),
            "role": "coastal_soft_context",
            "load": "optional",
            "style_hint": "Transparent fill, dashed outline.",
            "notes": "Soft coastal context layer.",
        },
    ]
    write_csv(
        OUT_DIR / "qgis_landmask_xyz_review_index.csv",
        rows,
        ["sort_order", "layer_name", "path", "role", "load", "style_hint", "notes"],
    )


def write_readme(summary: dict[str, Any]) -> None:
    text = f"""# Bornholm Landmask XYZ Review

Created: {summary["created_at"]}

Purpose: compare the current Bornholm landmask against QGIS XYZ basemaps, especially OpenStreetMap, before changing the app candidate extent or strandskydd logic.

Load checklist:

- `qgis_landmask_xyz_review_index.csv`

Most important layers:

- `{rel(LANDMASK)}`
- `{rel(OUTLINE)}`
- `{rel(ANY_SOURCE_WITHOUT_DISPLAY)}`
- `{rel(DISPLAY_WITHOUT_LANDSCAPE)}`
- `{rel(DISPLAY_WITHOUT_SCORE_SOCIAL)}`

Suggested QGIS styling:

- Put XYZ Tiles/OpenStreetMap at the bottom.
- Landmask fill: transparent fill with a bright outline.
- Landmask outline: 0.6-1.0 mm red/yellow line.
- Source rows outside display: transparent brown fill.
- Display gaps: high-contrast pink/purple.

Review question:

Does the landmask follow the XYZ coastline closely enough for app use, or is it over-clipped/under-clipped near harbors, beaches, islets, and coastal industrial areas?
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    derived_counts = build_outline_and_vertices()
    write_index()
    summary = {
        "created_at": date.today().isoformat(),
        "region_id": "bornholm",
        "purpose": "Compare Bornholm landmask against QGIS XYZ basemaps.",
        "inputs": {
            "landmask": rel(LANDMASK),
            "display_r9": rel(DISPLAY_R9),
            "display_r8": rel(DISPLAY_R8),
            "display_without_landscape": rel(DISPLAY_WITHOUT_LANDSCAPE),
            "display_without_score_social": rel(DISPLAY_WITHOUT_SCORE_SOCIAL),
            "any_source_without_display": rel(ANY_SOURCE_WITHOUT_DISPLAY),
            "strand_protection": rel(STRAND_PROTECTION),
            "coastal_zone": rel(COASTAL_ZONE),
        },
        "outputs": {
            "outline": rel(OUTLINE),
            "vertices": rel(VERTICES),
            "index": rel(OUT_DIR / "qgis_landmask_xyz_review_index.csv"),
            "readme": rel(OUT_DIR / "README.md"),
        },
        "counts": {
            "landmask_features": feature_count(LANDMASK),
            "display_r9_features": feature_count(DISPLAY_R9),
            "display_r8_features": feature_count(DISPLAY_R8),
            "display_without_landscape_features": feature_count(DISPLAY_WITHOUT_LANDSCAPE),
            "display_without_score_social_features": feature_count(DISPLAY_WITHOUT_SCORE_SOCIAL),
            "source_rows_without_display_features": feature_count(ANY_SOURCE_WITHOUT_DISPLAY),
            **derived_counts,
        },
    }
    write_json(OUT_DIR / "landmask_xyz_review_summary.json", summary)
    write_readme(summary)
    print(f"Wrote Bornholm landmask XYZ review package: {rel(OUT_DIR)}")
    print(json.dumps(summary["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
