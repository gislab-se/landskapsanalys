from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import h3


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "exports" / "qgis_review" / "landscape_baselayers"

TRONDELAG_LABLAB = ROOT / "docs/geocontext/potential_framework/data/trondelag_lablab_landscape_h3_r7/trondelag_lablab_landskapsanalys_h3_r7.geojson"
TRONDELAG_DISPLAY_R7 = ROOT / "docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/hex.geojson"
TRONDELAG_DISPLAY_R6 = ROOT / "docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r6_rollup.geojson"
TRONDELAG_DISPLAY_R5 = ROOT / "docs/geocontext/potential_framework/data/trondelag_r7_app_bundle/h3/trondelag_landscape_h3_r5_rollup.geojson"

BORNHOLM_LABLAB_R9 = ROOT / "exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9_app.geojson"
BORNHOLM_LABLAB_R9_CSV = ROOT / "exports/v2_multiregion/bornholm/bornholm_lablab_landscape_r9.csv"
BORNHOLM_DISPLAY_R9 = ROOT / "exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_9_land_clipped.geojson"
BORNHOLM_DISPLAY_R8 = ROOT / "exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_8_land_clipped.geojson"
BORNHOLM_DISPLAY_R7 = ROOT / "exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_7_land_clipped.geojson"
BORNHOLM_DISPLAY_R6 = ROOT / "exports/v2_multiregion/bornholm/h3_display_geometries/bornholm_h3_res_6_land_clipped.geojson"

SKARABORG_CROP = ROOT / "artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_map_crop.png"
SKARABORG_FIRSTPASS_TIF = ROOT / "artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_firstpass_epsg3006.tif"
SKARABORG_PREVIEW = ROOT / "artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_firstpass_preview.png"
SKARABORG_GCPS = ROOT / "docs/georef/skaraborg_e20_initial_gcps.csv"
SKARABORG_RESIDUALS = ROOT / "artifacts/skaraborg_landscape_georef/e20_regional_landscape_types_initial_gcp_residuals.csv"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_geojson(path: Path, features: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )


def hex_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("hex_id") or props.get("h3_address") or "")


def geojson_ids(path: Path) -> set[str]:
    return {hex_id(feature) for feature in load_geojson(path).get("features") or [] if hex_id(feature)}


def add_review_props(feature: dict[str, Any], **props: Any) -> dict[str, Any]:
    clone = json.loads(json.dumps(feature, ensure_ascii=False))
    clone_props = dict(clone.get("properties") or {})
    clone_props.update(props)
    clone["properties"] = clone_props
    return clone


def h3_polygon(hex_value: str) -> dict[str, Any]:
    ring = [[float(lng), float(lat)] for lat, lng in h3.cell_to_boundary(hex_value)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def feature_counts(path: Path, field: str = "landscape_type_id") -> Counter[str]:
    counter: Counter[str] = Counter()
    for feature in load_geojson(path).get("features") or []:
        props = feature.get("properties") or {}
        value = props.get(field) or props.get("v10_type_id") or props.get("class_km")
        counter[str(value)] += 1
    return counter


def write_counter_csv(path: Path, counter: Counter[str], label_map: dict[str, str] | None = None) -> None:
    label_map = label_map or {}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["type_id", "type_name", "feature_count"])
        writer.writeheader()
        for type_id in sorted(counter):
            writer.writerow(
                {
                    "type_id": type_id,
                    "type_name": label_map.get(type_id, ""),
                    "feature_count": counter[type_id],
                }
            )


def load_bornholm_csv_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with BORNHOLM_LABLAB_R9_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hex_value = str(row.get("hex_id") or "")
            if hex_value:
                rows[hex_value] = row
    return rows


def write_audit_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "region_id",
        "layer_id",
        "path",
        "exists",
        "feature_count",
        "h3_resolution_counts",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def h3_resolution_counts(path: Path) -> str:
    counter: Counter[str] = Counter()
    for feature in load_geojson(path).get("features") or []:
        value = hex_id(feature)
        if not value:
            continue
        try:
            counter[str(h3.get_resolution(value))] += 1
        except Exception:
            counter["invalid"] += 1
    return "; ".join(f"R{key}={value}" for key, value in sorted(counter.items()))


def feature_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(load_geojson(path).get("features") or [])


def build_trondelag() -> dict[str, Any]:
    display_ids = geojson_ids(TRONDELAG_DISPLAY_R7)
    lablab = load_geojson(TRONDELAG_LABLAB)
    app_features: list[dict[str, Any]] = []
    outside_features: list[dict[str, Any]] = []

    for feature in lablab.get("features") or []:
        value = hex_id(feature)
        if value in display_ids:
            app_features.append(add_review_props(feature, review_scope="current_app_extent"))
        else:
            outside_features.append(add_review_props(feature, review_scope="outside_current_app_extent"))

    app_path = OUT_DIR / "trondelag_lablab_r7_current_app_extent.geojson"
    outside_path = OUT_DIR / "trondelag_lablab_r7_outside_current_app_extent.geojson"
    write_geojson(app_path, app_features)
    write_geojson(outside_path, outside_features)

    labels = {
        "LT01": "Ytterkustlandskap",
        "LT02": "Fjordlandskap",
        "LT03": "Fjordnära jordbrukslandskap",
        "LT04": "Fjällnära skogslandskap",
        "LT05": "Dalgångslandskap",
        "LT06": "Lågfjällslandskap",
        "LT07": "Högfjällslandskap",
        "LT08": "Sjö- och våtmarkslandskap",
        "LT09": "Vidsträckt fjällandskap",
    }
    write_counter_csv(OUT_DIR / "trondelag_lablab_r7_current_app_extent_type_counts.csv", feature_counts(app_path), labels)
    write_counter_csv(OUT_DIR / "trondelag_lablab_r7_outside_current_app_extent_type_counts.csv", feature_counts(outside_path), labels)

    rollups: dict[str, dict[str, int]] = {}
    lablab_ids = geojson_ids(TRONDELAG_LABLAB)
    for resolution, display_path in [(7, TRONDELAG_DISPLAY_R7), (6, TRONDELAG_DISPLAY_R6), (5, TRONDELAG_DISPLAY_R5)]:
        display = geojson_ids(display_path)
        lablab_rollup = {h3.cell_to_parent(value, resolution) for value in lablab_ids}
        rollups[f"R{resolution}"] = {
            "display": len(display),
            "lablab_rollup": len(lablab_rollup),
            "overlap": len(display & lablab_rollup),
            "display_missing": len(display - lablab_rollup),
            "lablab_extra": len(lablab_rollup - display),
        }

    return {
        "current_app_extent": rel(app_path),
        "outside_current_app_extent": rel(outside_path),
        "current_app_features": len(app_features),
        "outside_app_features": len(outside_features),
        "rollup_coverage": rollups,
    }


def build_bornholm() -> dict[str, Any]:
    display_r9 = load_geojson(BORNHOLM_DISPLAY_R9)
    landscape_ids = geojson_ids(BORNHOLM_LABLAB_R9)
    display_ids = {hex_id(feature) for feature in display_r9.get("features") or [] if hex_id(feature)}
    csv_rows = load_bornholm_csv_rows()

    display_without_landscape = [
        add_review_props(feature, review_issue="display_without_landscape_properties")
        for feature in display_r9.get("features") or []
        if hex_id(feature) in display_ids - landscape_ids
    ]
    landscape_without_display: list[dict[str, Any]] = []
    for hex_value in sorted(set(csv_rows) - display_ids):
        row = csv_rows[hex_value]
        landscape_without_display.append(
            {
                "type": "Feature",
                "geometry": h3_polygon(hex_value),
                "properties": {
                    "hex_id": hex_value,
                    "review_issue": "landscape_row_without_display_geometry",
                    "landscape_type_id": row.get("landscape_type_id", ""),
                    "landscape_type_name": row.get("landscape_type_name", ""),
                    "class_km": row.get("class_km", ""),
                    "dominant_area_share_pct": row.get("dominant_area_share_pct", ""),
                    "classified_hex_share_pct": row.get("classified_hex_share_pct", ""),
                    "review_flag": row.get("review_flag", ""),
                },
            }
        )

    display_gap_path = OUT_DIR / "bornholm_lablab_r9_display_without_landscape.geojson"
    landscape_extra_path = OUT_DIR / "bornholm_lablab_r9_landscape_without_display.geojson"
    write_geojson(display_gap_path, display_without_landscape)
    write_geojson(landscape_extra_path, landscape_without_display)

    labels = {
        "LT01": "Klippigt kustlandskap",
        "LT02": "Sandigt kustlandskap",
        "LT03": "Jordbruks- och sprickdalslandskap",
        "LT04": "Skogs- och sprickdalslandskap",
        "LT05": "Slätt- och jordbrukslandskap",
    }
    write_counter_csv(OUT_DIR / "bornholm_lablab_r9_type_counts.csv", feature_counts(BORNHOLM_LABLAB_R9), labels)

    coverage: dict[str, dict[str, int]] = {}
    for resolution, display_path in [(9, BORNHOLM_DISPLAY_R9), (8, BORNHOLM_DISPLAY_R8), (7, BORNHOLM_DISPLAY_R7), (6, BORNHOLM_DISPLAY_R6)]:
        display = geojson_ids(display_path)
        landscape_rollup = {h3.cell_to_parent(value, resolution) for value in landscape_ids}
        coverage[f"R{resolution}"] = {
            "display": len(display),
            "landscape_rollup": len(landscape_rollup),
            "overlap": len(display & landscape_rollup),
            "display_missing": len(display - landscape_rollup),
            "landscape_extra": len(landscape_rollup - display),
        }

    return {
        "display_without_landscape": rel(display_gap_path),
        "landscape_without_display": rel(landscape_extra_path),
        "display_without_landscape_count": len(display_without_landscape),
        "landscape_without_display_count": len(landscape_without_display),
        "coverage": coverage,
    }


def build_review_index(trondelag: dict[str, Any], bornholm: dict[str, Any]) -> None:
    rows = [
        {
            "region_id": "trondelag",
            "qgis_layer": "LABLAB R7 clipped to current app extent",
            "path": trondelag["current_app_extent"],
            "status": "qgis_reviewed_default_source",
            "review_note": "QGIS-reviewed app-default source; covers the 13,735 current Trondelag display cells.",
        },
        {
            "region_id": "trondelag",
            "qgis_layer": "LABLAB R7 outside current app extent",
            "path": trondelag["outside_current_app_extent"],
            "status": "extent_review",
            "review_note": "These cells are in the LABLAB layer but outside the current offshore-trimmed app display extent.",
        },
        {
            "region_id": "bornholm",
            "qgis_layer": "LABLAB R9 app layer",
            "path": rel(BORNHOLM_LABLAB_R9),
            "status": "active_v2_landscape_candidate_with_small_geometry_mismatch",
            "review_note": "Already linked by regions/bornholm/region.json. Review together with the two QA layers below.",
        },
        {
            "region_id": "bornholm",
            "qgis_layer": "Display cells without landscape properties",
            "path": bornholm["display_without_landscape"],
            "status": "qa_issue",
            "review_note": "Display cells present in R9 geometry but absent from the app landscape GeoJSON.",
        },
        {
            "region_id": "bornholm",
            "qgis_layer": "Landscape rows without display geometry",
            "path": bornholm["landscape_without_display"],
            "status": "qa_issue",
            "review_note": "R9 landscape CSV rows outside the land-clipped display geometry.",
        },
        {
            "region_id": "skaraborg",
            "qgis_layer": "E20 first-pass georeferenced raster",
            "path": rel(SKARABORG_FIRSTPASS_TIF),
            "status": "orientation_only_not_app_ready",
            "review_note": "Use only as a tracing/reference backdrop until GCP residuals are improved or original GIS is obtained.",
        },
        {
            "region_id": "skaraborg",
            "qgis_layer": "E20 cropped source map image",
            "path": rel(SKARABORG_CROP),
            "status": "source_reference",
            "review_note": "Open beside the georeferenced raster when refining GCPs.",
        },
    ]
    index_path = OUT_DIR / "qgis_review_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["region_id", "qgis_layer", "path", "status", "review_note"])
        writer.writeheader()
        writer.writerows(rows)


def build_baselayer_audit(trondelag: dict[str, Any], bornholm: dict[str, Any]) -> None:
    rows = [
        {
            "region_id": "trondelag",
            "layer_id": "current_app_display_r7",
            "path": rel(TRONDELAG_DISPLAY_R7),
            "exists": TRONDELAG_DISPLAY_R7.exists(),
            "feature_count": feature_count(TRONDELAG_DISPLAY_R7),
            "h3_resolution_counts": h3_resolution_counts(TRONDELAG_DISPLAY_R7),
            "notes": "Current app calculation/display extent; must remain R7/R6/R5 only.",
        },
        {
            "region_id": "trondelag",
            "layer_id": "lablab_r7_current_app_extent",
            "path": trondelag["current_app_extent"],
            "exists": True,
            "feature_count": trondelag["current_app_features"],
            "h3_resolution_counts": h3_resolution_counts(ROOT / trondelag["current_app_extent"]),
            "notes": "QGIS-reviewed app default landscape basis after LT09/gap review.",
        },
        {
            "region_id": "bornholm",
            "layer_id": "display_r9",
            "path": rel(BORNHOLM_DISPLAY_R9),
            "exists": BORNHOLM_DISPLAY_R9.exists(),
            "feature_count": feature_count(BORNHOLM_DISPLAY_R9),
            "h3_resolution_counts": h3_resolution_counts(BORNHOLM_DISPLAY_R9),
            "notes": "R9 land-clipped display geometry has two cells not present in app landscape GeoJSON.",
        },
        {
            "region_id": "bornholm",
            "layer_id": "lablab_r9_app",
            "path": rel(BORNHOLM_LABLAB_R9),
            "exists": BORNHOLM_LABLAB_R9.exists(),
            "feature_count": feature_count(BORNHOLM_LABLAB_R9),
            "h3_resolution_counts": h3_resolution_counts(BORNHOLM_LABLAB_R9),
            "notes": "Already active landscape manifest; QA mismatch is small but real.",
        },
        {
            "region_id": "skaraborg",
            "layer_id": "e20_firstpass_georef_raster",
            "path": rel(SKARABORG_FIRSTPASS_TIF),
            "exists": SKARABORG_FIRSTPASS_TIF.exists(),
            "feature_count": "",
            "h3_resolution_counts": "",
            "notes": "Raster only; no H3/display geometry or potential calculation basis yet.",
        },
    ]
    write_audit_rows(OUT_DIR / "calculation_baselayer_audit.csv", rows)


def write_summary(trondelag: dict[str, Any], bornholm: dict[str, Any]) -> None:
    summary = {
        "generated_by": "scripts/build_landscape_qgis_review_package.py",
        "trondelag": trondelag,
        "bornholm": bornholm,
        "skaraborg": {
            "crop": rel(SKARABORG_CROP),
            "firstpass_tif": rel(SKARABORG_FIRSTPASS_TIF),
            "preview": rel(SKARABORG_PREVIEW),
            "gcps": rel(SKARABORG_GCPS),
            "residuals": rel(SKARABORG_RESIDUALS),
            "status": "orientation_only_not_app_ready",
        },
    }
    (OUT_DIR / "review_package_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = f"""# Landscape Baselayer QGIS Review Package

Generated by `scripts/build_landscape_qgis_review_package.py`.

Open `qgis_review_index.csv` first. It lists the layers to load in QGIS and the review role for each file.

## Trondelag

- QGIS-reviewed default source: `{trondelag["current_app_extent"]}`
- Extra LABLAB cells outside current app extent: `{trondelag["outside_current_app_extent"]}`
- Type counts: `trondelag_lablab_r7_current_app_extent_type_counts.csv`

The clipped default source covers the current 13,735 R7 app display cells. The full LABLAB layer has 18,530 R7 cells, so the extra layer is useful for any later audit of whether the app extent should remain offshore-trimmed.

Decision: keep the current offshore-trimmed app extent for runtime. Use the outside-extent layer only as review/reference material unless a later extent-expansion audit says otherwise.

## Bornholm

- Active V2 LABLAB R9 layer: `{rel(BORNHOLM_LABLAB_R9)}`
- Display cells without landscape properties: `{bornholm["display_without_landscape"]}`
- Landscape rows without display geometry: `{bornholm["landscape_without_display"]}`
- Type counts: `bornholm_lablab_r9_type_counts.csv`

This is the suspected problem area: the R9 display geometry and the LABLAB landscape export are close, but not identical.

## Skaraborg

- First-pass georeferenced raster: `{rel(SKARABORG_FIRSTPASS_TIF)}`
- Cropped source image: `{rel(SKARABORG_CROP)}`
- GCP table: `{rel(SKARABORG_GCPS)}`
- Residuals: `{rel(SKARABORG_RESIDUALS)}`

This is only an orientation/tracing source. It is not app-ready until the georeference is improved or original GIS is obtained.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trondelag = build_trondelag()
    bornholm = build_bornholm()
    build_review_index(trondelag, bornholm)
    build_baselayer_audit(trondelag, bornholm)
    write_summary(trondelag, bornholm)
    print(f"Wrote QGIS review package to {rel(OUT_DIR)}")
    print(f"Trondelag current app extent features: {trondelag['current_app_features']}")
    print(f"Bornholm display-without-landscape cells: {bornholm['display_without_landscape_count']}")
    print(f"Bornholm landscape-without-display rows: {bornholm['landscape_without_display_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
