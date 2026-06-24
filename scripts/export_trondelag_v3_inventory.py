from __future__ import annotations

import csv
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

try:
    from shapely import force_2d
except Exception:  # pragma: no cover
    force_2d = None


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "exports" / "v3_geojson" / "trondelag"
GEOJSON_DIR = OUT_DIR / "geojson"
SIMPLIFIED_DIR = OUT_DIR / "geojson_simplified"

REGION_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "regions" / "trondelag.json"
LANDSCAPE_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "landscape" / "trondelag_lablab_landscape_r7.json"
POTENTIAL_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "potential" / "trondelag_potential_placeholder.json"
WIND_RULES_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "potential" / "trondelag_wind_rules_placeholder.json"
SOLAR_RULES_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "potential" / "trondelag_solar_rules_placeholder.json"
SCENARIO_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "scenarios" / "trondelag_scenarios_placeholder.json"
SOCIAL_MANIFEST = REPO_ROOT / "apps" / "potential_model" / "manifests" / "social_acceptance" / "trondelag_synthetic_acceptance_v0.json"
ACCEPTANCE_REGISTRY = REPO_ROOT / "apps" / "acceptance_model" / "registry_trondelag.json"
CANDIDATE_CSV = REPO_ROOT / "Trondelag" / "projects" / "trondelag" / "config" / "potential_app_layer_candidates.csv"
ACCEPTANCE_ASSET_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "geocontext"
    / "acceptance_framework"
    / "data"
    / "trondelag_prototype_assets"
    / "asset_manifest.csv"
)

CANDIDATE_TO_APP_IDS = {
    "TRL_POPULATION_250M_CENTROIDS": ["population_points"],
    "TRL_DENSELY_POPULATED_AREAS": ["built_centre"],
    "TRL_HOLIDAY_HOUSES_CENTROIDS": ["built_low_selection"],
    "TRL_ROADS_ALL": ["roads_medium", "roads_large"],
    "TRL_TRANSMISSION_NETWORK": ["high_voltage_lines"],
    "TRL_UNDERWATER_CABLE": ["underground_cables"],
    "TRL_WIND_TURBINES": ["existing_wind_turbines"],
    "TRL_NATURE_PROTECTION_AREAS": ["protected_areas"],
    "TRL_CULTURAL_HERITAGE": ["cultural_preservation"],
    "TRL_CULTURAL_LANDSCAPES": ["valuable_cultural_environment"],
    "TRL_REINDEER_GRAZING_MERGED": ["reindeer_grazing_merged"],
    "TRL_REINDEER_MIGRATION_ROUTES": ["reindeer_migration_routes"],
}

CATALOG_FIELDS = [
    "layer_id",
    "v2_app_layer_id",
    "v2_source_layer_id",
    "label_sv_no",
    "label_en",
    "v2_group",
    "v3_parameter_group",
    "data_source",
    "source_path",
    "source_layer_name",
    "workspace_source_path",
    "source_in_workspace",
    "crs",
    "export_crs",
    "geometry",
    "feature_count",
    "h3_resolution",
    "data_status",
    "show_in_v3",
    "export_status",
    "export_path",
    "simplified_export_path",
    "distance_table_path",
    "analysis_kind",
    "default_visibility_v2",
    "notes",
]

GROUP_TO_V3 = {
    "settlement": "settlement_population",
    "transport": "transport_infrastructure",
    "infrastructure": "transport_infrastructure",
    "electrical": "grid_connection",
    "energy_potential": "energy_potential_inputs",
    "protected": "protected_nature",
    "nature_protection": "protected_nature",
    "culture": "cultural_environment",
    "land_use": "land_use_markdekke",
    "reindeer": "reindeer_husbandry",
    "terrain_context": "base_context",
    "coastal": "coastal_water_context",
    "aviation_approach": "aviation_restrictions",
    "aviation_bird": "aviation_restrictions",
    "military": "military_restrictions",
    "landscape": "landscape_restrictions",
    "potential": "potential",
    "scenario": "scenario",
    "social_acceptance": "social_acceptance",
    "ui_control": "ui_controls",
}


@dataclass
class ExportInfo:
    status: str = "not_exported"
    export_path: str = ""
    simplified_export_path: str = ""
    feature_count: int | str = ""
    geometry: str = ""
    export_crs: str = ""


def rel(path: Path | str | None) -> str:
    if not path:
        return ""
    path = Path(path)
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def repo_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fix_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text or ("Ã" not in text and "Â" not in text):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except Exception:
        return text
    bad_before = text.count("Ã") + text.count("Â")
    bad_after = repaired.count("Ã") + repaired.count("Â")
    return repaired if bad_after < bad_before else text


def bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "ja"}:
        return "true"
    if text in {"false", "0", "no", "nej"}:
        return "false"
    return str(value or "")


def as_int(value: Any) -> int | str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return ""


def coordinate_bounds(path: Path) -> tuple[float, float, float, float] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    xs: list[float] = []
    ys: list[float] = []

    def walk(coords: Any) -> None:
        if not isinstance(coords, list):
            return
        if coords and isinstance(coords[0], (int, float)) and len(coords) >= 2:
            xs.append(float(coords[0]))
            ys.append(float(coords[1]))
            return
        for item in coords:
            walk(item)

    for feature in data.get("features") or []:
        geometry = feature.get("geometry") or {}
        walk(geometry.get("coordinates"))
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def looks_like_lonlat(path: Path) -> bool:
    bounds = coordinate_bounds(path)
    if bounds is None:
        return True
    minx, miny, maxx, maxy = bounds
    return -180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90


def read_geojson_as_gdf(path: Path, source_crs: str = "") -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        if looks_like_lonlat(path):
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        elif source_crs:
            gdf = gdf.set_crs(source_crs, allow_override=True)
    if gdf.crs is not None and str(gdf.crs).upper() not in {"EPSG:4326", "WGS84"}:
        gdf = gdf.to_crs("EPSG:4326")
    if force_2d is not None and "geometry" in gdf:
        gdf["geometry"] = gdf.geometry.apply(lambda geom: force_2d(geom) if geom is not None else None)
    return gdf


def geometry_summary(gdf: gpd.GeoDataFrame) -> str:
    if gdf.empty:
        return ""
    types = sorted(str(value) for value in gdf.geometry.geom_type.dropna().unique())
    return ";".join(types)


def write_geojson(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    gdf.to_file(out_path, driver="GeoJSON")


def export_geojson(
    source_path: Path | None,
    out_name: str,
    source_crs: str = "",
    simplify_if_heavy: bool = True,
    simplify_tolerance_deg: float = 0.00035,
) -> ExportInfo:
    if source_path is None or not source_path.exists():
        return ExportInfo(status="missing_source")
    out_path = GEOJSON_DIR / out_name
    try:
        gdf = read_geojson_as_gdf(source_path, source_crs=source_crs)
        write_geojson(gdf, out_path)
    except Exception as exc:
        return ExportInfo(status=f"export_failed: {exc}")

    simplified_rel = ""
    if simplify_if_heavy and not gdf.empty and source_path.stat().st_size > 8_000_000:
        geom_types = set(str(value) for value in gdf.geometry.geom_type.dropna().unique())
        if not geom_types.issubset({"Point", "MultiPoint"}):
            try:
                simplified = gdf.copy()
                simplified["geometry"] = simplified.geometry.simplify(simplify_tolerance_deg, preserve_topology=True)
                simplified_path = SIMPLIFIED_DIR / out_name
                write_geojson(simplified, simplified_path)
                simplified_rel = rel(simplified_path)
            except Exception:
                simplified_rel = ""

    return ExportInfo(
        status="exported",
        export_path=rel(out_path),
        simplified_export_path=simplified_rel,
        feature_count=int(len(gdf)),
        geometry=geometry_summary(gdf),
        export_crs="EPSG:4326",
    )


def rounded_coords(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return [rounded_coords(item, digits=digits) for item in value]
    return value


def write_lite_geojson(source_rel_path: str, out_name: str, keep_properties: list[str]) -> str:
    if not source_rel_path:
        return ""
    source_path = REPO_ROOT / source_rel_path
    if not source_path.exists():
        return ""
    data = json.loads(source_path.read_text(encoding="utf-8"))
    keep = set(keep_properties)
    features: list[dict[str, Any]] = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        slim_props = {key: props.get(key) for key in keep_properties if key in props}
        geometry = feature.get("geometry") or {}
        slim_geometry = dict(geometry)
        if "coordinates" in slim_geometry:
            slim_geometry["coordinates"] = rounded_coords(slim_geometry["coordinates"])
        features.append({"type": "Feature", "properties": slim_props, "geometry": slim_geometry})
    out_path = SIMPLIFIED_DIR / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return rel(out_path)


def attach_lite_export(info: ExportInfo, out_name: str, keep_properties: list[str], min_bytes: int = 8_000_000) -> ExportInfo:
    if not info.export_path:
        return info
    source_path = REPO_ROOT / info.export_path
    if not source_path.exists() or source_path.stat().st_size <= min_bytes:
        return info
    lite_path = write_lite_geojson(info.export_path, out_name, keep_properties)
    if lite_path:
        info.simplified_export_path = lite_path
    return info


def export_social_acceptance_geojson(social_manifest: dict[str, Any], out_name: str) -> ExportInfo:
    hex_path = repo_path(social_manifest.get("hex_geometry_path"))
    csv_path = repo_path(social_manifest.get("acceptance_csv"))
    if hex_path is None or csv_path is None or not hex_path.exists() or not csv_path.exists():
        return ExportInfo(status="missing_source")
    try:
        with hex_path.open("r", encoding="utf-8") as handle:
            hex_data = json.load(handle)
        acceptance = pd.read_csv(csv_path)
        acceptance_map = {
            str(row["hex_id"]): {
                key: (None if (isinstance(value, float) and math.isnan(value)) else value)
                for key, value in row.items()
                if key != "hex_id"
            }
            for row in acceptance.to_dict(orient="records")
            if "hex_id" in row
        }
        features = []
        for feature in hex_data.get("features") or []:
            props = dict(feature.get("properties") or {})
            hex_id = str(props.get("hex_id") or props.get("h3_address") or "")
            if hex_id in acceptance_map:
                props.update(acceptance_map[hex_id])
            new_feature = dict(feature)
            new_feature["properties"] = props
            features.append(new_feature)
        out_path = GEOJSON_DIR / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
            encoding="utf-8",
        )
        gdf = read_geojson_as_gdf(out_path, source_crs="EPSG:4326")
        write_geojson(gdf, out_path)
        return ExportInfo(
            status="exported_joined_csv_to_h3",
            export_path=rel(out_path),
            feature_count=len(gdf),
            geometry=geometry_summary(gdf),
            export_crs="EPSG:4326",
        )
    except Exception as exc:
        return ExportInfo(status=f"export_failed: {exc}")


def row(**kwargs: Any) -> dict[str, Any]:
    base = {field: "" for field in CATALOG_FIELDS}
    base.update(kwargs)
    for key in ("label_sv_no", "label_en", "v2_group", "data_source", "notes", "source_layer_name"):
        base[key] = fix_text(base.get(key))
    return base


def add_export_info(base: dict[str, Any], info: ExportInfo) -> dict[str, Any]:
    if info.feature_count != "" and base.get("feature_count", "") in {"", None}:
        base["feature_count"] = info.feature_count
    if info.geometry:
        base["geometry"] = info.geometry
    if info.export_crs:
        base["export_crs"] = info.export_crs
    base["export_status"] = info.status
    base["export_path"] = info.export_path
    base["simplified_export_path"] = info.simplified_export_path
    return base


def data_source_from_path(path_value: str) -> str:
    if not path_value:
        return ""
    clean = path_value.split("|", 1)[0]
    return Path(clean).stem


def normalized_source_path(path_value: str) -> str:
    if not path_value:
        return ""
    value = str(path_value).split("|", 1)[0].strip().replace("\\", "/")
    return value.lower()


def source_exists_in_workspace(path_value: str) -> tuple[str, str]:
    if not path_value:
        return "false", ""
    first_path = path_value.split("|", 1)[0]
    path = repo_path(first_path)
    if path and path.exists() and REPO_ROOT.resolve() in path.resolve().parents:
        return "true", rel(path)
    return "false", ""


def v3_visibility_for_candidate(candidate: dict[str, Any]) -> str:
    role = str(candidate.get("role", "") or "")
    priority = str(candidate.get("priority", "") or "")
    default = bool_text(candidate.get("default_visibility"))
    if role == "qa_only" or priority == "low":
        return "hide_qa_or_backlog"
    if default == "true":
        return "show_optional_context"
    if priority == "high":
        return "show_optional_advanced"
    return "hide_until_selected"


def candidate_status(candidate: dict[str, Any]) -> str:
    role = str(candidate.get("role", "") or "")
    notes = str(candidate.get("notes", "") or "").lower()
    source_path = str(candidate.get("source_path", "") or "").lower()
    if "filegdb" in notes or ".gdb" in source_path or "osaker" in notes or "uncertain" in notes:
        return "real_data_unverified_or_needs_extraction"
    if role == "qa_only":
        return "real_data_qa_only"
    return "real_data_external_source"


def app_layer_visibility(group_id: str, layer_id: str) -> str:
    if layer_id == "population_points":
        return "analysis_default_source_show_optional"
    if group_id in {"settlement", "transport", "electrical", "culture", "protected", "land_use", "reindeer"}:
        return "analysis_source_hidden_by_default"
    return "hide_until_wired"


def load_csv_dicts(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_catalog() -> list[dict[str, Any]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    SIMPLIFIED_DIR.mkdir(parents=True, exist_ok=True)

    region = load_json(REGION_MANIFEST)
    landscape = load_json(LANDSCAPE_MANIFEST)
    geocontext_manifest_path = repo_path(landscape.get("data_driven_geocontext_manifest"))
    geocontext_landscape = (
        load_json(geocontext_manifest_path)
        if geocontext_manifest_path and geocontext_manifest_path.exists()
        else {}
    )
    potential = load_json(POTENTIAL_MANIFEST)
    wind_rules = load_json(WIND_RULES_MANIFEST)
    solar_rules = load_json(SOLAR_RULES_MANIFEST)
    scenario = load_json(SCENARIO_MANIFEST)
    social = load_json(SOCIAL_MANIFEST)
    registry = load_json(ACCEPTANCE_REGISTRY)
    asset_manifest = pd.read_csv(ACCEPTANCE_ASSET_MANIFEST)
    asset_by_app_id = {str(row["layer_id"]): row for _, row in asset_manifest.iterrows()}
    asset_by_layer_key: dict[str, list[pd.Series]] = {}
    asset_by_source_path: dict[str, list[pd.Series]] = {}
    for _, asset_row in asset_manifest.iterrows():
        asset_by_layer_key.setdefault(str(asset_row["layer_key"]), []).append(asset_row)
        source_key = normalized_source_path(str(asset_row.get("source_path", "") or ""))
        if source_key:
            asset_by_source_path.setdefault(source_key, []).append(asset_row)

    rows: list[dict[str, Any]] = []

    # Region/H3 and landscape manifest layers.
    for res, source in sorted((region.get("h3_display_geometries") or {}).items(), key=lambda item: int(item[0])):
        source_path = repo_path(source)
        export = export_geojson(source_path, f"trondelag_h3_display_r{res}.geojson", simplify_if_heavy=False)
        export = attach_lite_export(
            export,
            f"trondelag_h3_display_r{res}_lite.geojson",
            ["hex_id", "h3_address", "source_h3_resolution", "target_h3_resolution"],
        )
        rows.append(
            add_export_info(
                row(
                    layer_id=f"region_h3_display_r{res}",
                    label_sv_no=f"Trondelag H3-visningsgeometri R{res}",
                    v2_group="regionmanifest",
                    v3_parameter_group="base_context",
                    data_source="region manifest h3_display_geometries",
                    source_path=str(source),
                    workspace_source_path=rel(source_path) if source_path and source_path.exists() else "",
                    source_in_workspace=str(bool(source_path and source_path.exists())).lower(),
                    crs=region.get("web_crs", "EPSG:4326"),
                    h3_resolution=res,
                    data_status="derived_h3_display_geometry",
                    show_in_v3="show_runtime_display_geometry",
                    notes="R7 is the interactive Trondelag source level; R6/R5 are lightweight rollups.",
                ),
                export,
            )
        )

    landscape_source = repo_path(landscape.get("landscape_geojson"))
    lablab_export = export_geojson(
        landscape_source,
        "trondelag_lablab_landscape_types_r7_app_extent.geojson",
        simplify_if_heavy=False,
    )
    lablab_export = attach_lite_export(
        lablab_export,
        "trondelag_lablab_landscape_types_r7_app_extent_lite.geojson",
        [
            "hex_id",
            "landscape_type_id",
            "landscape_type_name_sv",
            "v10_type_id",
            "v10_type_name",
            "assignment_method",
            "review_scope",
            "class_km",
        ],
    )
    rows.append(
        add_export_info(
            row(
                layer_id="lablab_landscape_types_r7_app_extent",
                label_sv_no=fix_text(landscape.get("display_name", "Trondelag LABLAB landskapstyper R7")),
                v2_group="landskapsmanifest",
                v3_parameter_group="landscape_restrictions",
                data_source="QGIS-reviewed LABLAB PDF-derived H3 layer",
                source_path=str(landscape.get("landscape_geojson") or ""),
                workspace_source_path=rel(landscape_source) if landscape_source and landscape_source.exists() else "",
                source_in_workspace=str(bool(landscape_source and landscape_source.exists())).lower(),
                crs=landscape.get("web_crs", "EPSG:4326"),
                h3_resolution=landscape.get("source_h3_resolution", 7),
                data_status=landscape.get("data_status", "reviewed_pdf_derived_app_extent"),
                show_in_v3="show_default_after_qgis_review",
                notes="QGIS-reviewed LABLAB landscape-type basis clipped to the current 13,735-cell offshore-trimmed app extent. The full LABLAB extent remains reference material until a separate extent-expansion audit.",
            ),
            lablab_export,
        )
    )

    geocontext_source = repo_path(geocontext_landscape.get("landscape_geojson"))
    geocontext_export = export_geojson(
        geocontext_source,
        "trondelag_landscape_geocontext_r7.geojson",
        simplify_if_heavy=False,
    )
    geocontext_export = attach_lite_export(
        geocontext_export,
        "trondelag_landscape_geocontext_r7_lite.geojson",
        ["hex_id", "landscape_type_id", "landscape_type_name", "color", "source_h3_resolution", "target_h3_resolution"],
    )
    for layer_id, label, visibility, notes in [
        (
            "landscape_geocontext_types_r7",
            "V2 geocontext-landskapstyper R7",
            "hide_from_v3_standard",
            "V2 data-driven geocontext cluster/type layer. V3 core config says LABLAB should be the landscape basis, not this as standard decision support.",
        ),
        (
            "landscape_geocontext_structures_r7",
            "V2 landskapsstrukturer R7",
            "hide_from_v3_standard",
            "Computed from the same R7 bundle as method/backlog context.",
        ),
        (
            "landscape_geocontext_factors_r7",
            "V2 landskapsfaktorer R7",
            "hide_from_v3_standard",
            "Factor scores are method/debug context; not recommended as standard V3 decision layer.",
        ),
    ]:
        rows.append(
            add_export_info(
                row(
                    layer_id=layer_id,
                    label_sv_no=label,
                    v2_group="landskapsmanifest",
                    v3_parameter_group="landscape_restrictions",
                    data_source="trondelag_r7_app_bundle",
                    source_path=str(geocontext_landscape.get("landscape_geojson") or ""),
                    workspace_source_path=rel(geocontext_source) if geocontext_source and geocontext_source.exists() else "",
                    source_in_workspace=str(bool(geocontext_source and geocontext_source.exists())).lower(),
                    crs=geocontext_landscape.get("web_crs", "EPSG:4326"),
                    h3_resolution=geocontext_landscape.get("source_h3_resolution", 7),
                    data_status="derived_data_driven_geocontext",
                    show_in_v3=visibility,
                    notes=notes,
                ),
                geocontext_export,
            )
        )

    social_export = export_social_acceptance_geojson(social, "trondelag_social_acceptance_synthetic_r7.geojson")
    social_export = attach_lite_export(
        social_export,
        "trondelag_social_acceptance_synthetic_r7_lite.geojson",
        ["hex_id", "h3_resolution", "acceptance_low", "acceptance_medium", "acceptance_high", "data_status", "method_version"],
    )
    rows.append(
        add_export_info(
            row(
                layer_id="social_acceptance_synthetic_r7",
                label_sv_no=fix_text(social.get("display_name", "Trondelag syntetisk social acceptans v0")),
                v2_group="social_acceptance_manifest",
                v3_parameter_group="social_acceptance",
                data_source="synthetic social acceptance CSV joined to R7 H3 geometry",
                source_path=str(social.get("acceptance_csv") or ""),
                workspace_source_path=rel(repo_path(social.get("acceptance_csv"))) if repo_path(social.get("acceptance_csv")) else "",
                source_in_workspace=str(bool(repo_path(social.get("acceptance_csv")) and repo_path(social.get("acceptance_csv")).exists())).lower(),
                crs="EPSG:4326",
                h3_resolution=social.get("hex_resolution", 7),
                data_status="synthetic_test_data",
                show_in_v3="show_optional_hidden_by_default",
                notes="Synthetic UI/integration data only, not IVL research data.",
            ),
            social_export,
        )
    )

    # Placeholder manifests and dynamic V2 logical map layers.
    logical_layers = [
        ("potential_manifest_placeholder", potential.get("display_name"), "potentialmanifest", "potential", POTENTIAL_MANIFEST, "placeholder", "hide_until_regional_model_exists"),
        ("wind_rules_placeholder", wind_rules.get("model_id"), "potentialmanifest:wind_rules", "potential", WIND_RULES_MANIFEST, "placeholder", "hide_until_regional_model_exists"),
        ("solar_rules_placeholder", solar_rules.get("model_id"), "potentialmanifest:solar_rules", "potential", SOLAR_RULES_MANIFEST, "placeholder", "hide_until_regional_model_exists"),
        ("energy_scenario_placeholder", scenario.get("scenario_set_id"), "scenario_manifest", "scenario", SCENARIO_MANIFEST, "placeholder", "hide_until_norwegian_energy_inputs_exist"),
        ("potential_establishment_area", "Potentiell etableringsyta", "ui_dynamic_layer", "potential", None, "derived_runtime_layer", "show_default_core"),
        ("scenario_placement", "Scenariofördelning i etableringshex", "ui_dynamic_layer", "scenario", None, "derived_runtime_layer", "show_default_core"),
        ("outside_potential_need", "Ytbehov utanför landskapets potential", "ui_dynamic_layer", "scenario", None, "derived_runtime_layer", "show_default_core"),
        ("wind_potential", "Landskapspotential Vind", "ui_dynamic_layer", "potential", None, "derived_runtime_layer", "show_optional_advanced"),
        ("solar_potential", "Landskapspotential Sol", "ui_dynamic_layer", "potential", None, "derived_runtime_layer", "show_optional_advanced"),
        ("small_scale_solar_roof_proxy", "Småskalig anläggning på tak", "ui_dynamic_layer", "potential", None, "derived_runtime_proxy", "show_optional_advanced"),
        ("population_points_runtime_buffers", "Befolkningsbuffertar från 250 m rutproxy", "ui_dynamic_buffer_cache", "settlement_population", None, "generated_runtime_cache", "hide_generated_cache"),
    ]
    for layer_id, label, v2_group, v3_group, manifest_path, status, visibility in logical_layers:
        rows.append(
            row(
                layer_id=layer_id,
                label_sv_no=label,
                v2_group=v2_group,
                v3_parameter_group=v3_group,
                data_source=manifest_path.name if manifest_path else "computed in potential_app.py",
                source_path=rel(manifest_path) if manifest_path else "",
                workspace_source_path=rel(manifest_path) if manifest_path else "",
                source_in_workspace=str(bool(manifest_path and manifest_path.exists())).lower(),
                crs=region.get("native_crs", "EPSG:25832") if "buffer" in layer_id else "",
                h3_resolution=region.get("default_h3_resolution", 7) if "scenario" in layer_id or "potential" in layer_id else "",
                data_status=status,
                show_in_v3=visibility,
                export_status="not_exported_runtime_or_manifest",
                notes="Runtime/manifest layer; V3 should rebuild from parameter contracts rather than static GeoJSON." if manifest_path is None else "Manifest only; no regional vector layer is present.",
            )
        )

    # App-wired acceptance/controller source layers.
    registry_groups = {item["id"]: item for item in registry.get("groups", [])}
    for item in registry.get("layers", []):
        app_id = str(item["id"])
        group_id = str(item["group_id"])
        asset_row = asset_by_app_id.get(app_id)
        asset_source_path = ""
        geojson_path = ""
        distance_path = ""
        feature_count = ""
        geometry_family = ""
        source_layer_key = str(item.get("layer_key") or "")
        if asset_row is not None:
            asset_source_path = str(asset_row.get("source_path", "") or "")
            geojson_path = str(asset_row.get("geojson_path", "") or "")
            distance_path = str(asset_row.get("distance_path", "") or "")
            feature_count = as_int(asset_row.get("feature_count", ""))
            geometry_family = str(asset_row.get("geometry_family", "") or "")
        source_geojson = repo_path(geojson_path)
        export = export_geojson(source_geojson, f"source_{app_id}.geojson", source_crs="EPSG:4326")
        if export.feature_count == "" and feature_count != "":
            export.feature_count = feature_count
        if not export.geometry and geometry_family:
            export.geometry = geometry_family
        data_status = "real_data"
        if app_id == "population_points":
            data_status = "proxy_from_real_population_grid"
        elif "synthetic" in str(item.get("note", "")).lower():
            data_status = "synthetic"
        rows.append(
            add_export_info(
                row(
                    layer_id=app_id,
                    v2_app_layer_id=app_id,
                    v2_source_layer_id=source_layer_key,
                    label_sv_no=item.get("label", ""),
                    v2_group=f"acceptance_registry:{group_id}",
                    v3_parameter_group=GROUP_TO_V3.get(group_id, group_id),
                    data_source=data_source_from_path(asset_source_path),
                    source_path=asset_source_path,
                    workspace_source_path=rel(source_geojson) if source_geojson and source_geojson.exists() else "",
                    source_in_workspace=str(bool(source_geojson and source_geojson.exists())).lower(),
                    crs="EPSG:4326",
                    geometry=geometry_family,
                    feature_count=feature_count,
                    data_status=data_status,
                    show_in_v3=app_layer_visibility(group_id, app_id),
                    distance_table_path=distance_path,
                    analysis_kind=str(registry_groups.get(group_id, {}).get("analysis_kind", "")),
                    default_visibility_v2="analysis-default" if app_id == "population_points" else "hidden-source-layer",
                    notes=item.get("note", ""),
                ),
                export,
            )
        )

    # Broader Trondelag candidate catalog.
    for candidate in load_csv_dicts(CANDIDATE_CSV):
        candidate_id = str(candidate.get("layer_id", ""))
        source_key_matches = [asset_by_app_id[app_id] for app_id in CANDIDATE_TO_APP_IDS.get(candidate_id, []) if app_id in asset_by_app_id]
        source_key_matches = source_key_matches or asset_by_layer_key.get(candidate_id)
        if not source_key_matches:
            # Candidate layer_id is TRL_* while app assets use layer_key.
            source_key_matches = asset_by_layer_key.get(str(candidate.get("source_layer_name", "")))
        key_matches = asset_by_layer_key.get(str(candidate.get("layer_key", ""))) if candidate.get("layer_key") else None
        source_key_matches = key_matches or source_key_matches
        if not source_key_matches:
            source_key_matches = asset_by_source_path.get(normalized_source_path(str(candidate.get("source_path", ""))))

        layer_key = ""
        app_ids = []
        export_paths = []
        simplified_paths = []
        distance_paths = []
        if not source_key_matches:
            for key, matches in asset_by_layer_key.items():
                if key and key.lower() in str(candidate.get("notes", "")).lower():
                    source_key_matches = matches
                    break
        if source_key_matches:
            layer_key = str(source_key_matches[0].get("layer_key", "") or "")
            app_ids = [str(match.get("layer_id", "")) for match in source_key_matches]
            distance_paths = [str(match.get("distance_path", "")) for match in source_key_matches if str(match.get("distance_path", ""))]
            for match in source_key_matches:
                geojson_rel = str(match.get("geojson_path", "") or "")
                if geojson_rel:
                    source_geojson = repo_path(geojson_rel)
                    info = export_geojson(source_geojson, f"source_{match.get('layer_id')}.geojson", source_crs="EPSG:4326")
                    if info.export_path:
                        export_paths.append(info.export_path)
                    if info.simplified_export_path:
                        simplified_paths.append(info.simplified_export_path)

        in_workspace, workspace_path = source_exists_in_workspace(str(candidate.get("source_path", "")))
        notes = str(candidate.get("notes", "") or "")
        if app_ids:
            notes = f"{notes} Appkopplad som: {', '.join(app_ids)}."
        rows.append(
            row(
                layer_id=str(candidate.get("layer_id", "")),
                v2_app_layer_id=";".join(app_ids),
                v2_source_layer_id=layer_key,
                label_sv_no=candidate.get("display_name_sv", ""),
                label_en=candidate.get("display_name_en", ""),
                v2_group=f"candidate:{candidate.get('controller_group', '')}",
                v3_parameter_group=GROUP_TO_V3.get(str(candidate.get("controller_group", "")), str(candidate.get("controller_group", ""))),
                data_source=data_source_from_path(str(candidate.get("source_path", ""))),
                source_path=str(candidate.get("source_path", "")),
                source_layer_name=str(candidate.get("source_layer_name", "")),
                workspace_source_path=workspace_path,
                source_in_workspace=in_workspace,
                crs=str(candidate.get("crs", "")),
                export_crs="EPSG:4326" if export_paths else "",
                geometry=str(candidate.get("geometry_type", "")),
                feature_count=";".join(str(as_int(match.get("feature_count", ""))) for match in (source_key_matches or [])) if source_key_matches else "",
                h3_resolution="",
                data_status=candidate_status(candidate),
                show_in_v3=v3_visibility_for_candidate(candidate),
                export_status="exported_via_app_asset" if export_paths else "not_exported_external_source_missing_from_workspace",
                export_path=";".join(dict.fromkeys(export_paths)),
                simplified_export_path=";".join(dict.fromkeys(simplified_paths)),
                distance_table_path=";".join(dict.fromkeys(distance_paths)),
                analysis_kind=str(candidate.get("role", "")),
                default_visibility_v2=bool_text(candidate.get("default_visibility")),
                notes=notes,
            )
        )

    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    found = len(rows)
    exported = sum(1 for item in rows if str(item.get("export_status", "")).startswith("exported") or item.get("export_path"))
    missing_sources = [
        item["layer_id"]
        for item in rows
        if item.get("source_path")
        and not item.get("export_path")
        and item.get("source_in_workspace") != "true"
        and str(item.get("export_status", "")).startswith("not_exported_external")
    ]
    uncertain = [
        item["layer_id"]
        for item in rows
        if any(token in str(item.get("data_status", "")) for token in ["experimental", "unverified", "placeholder", "synthetic"])
    ]
    return {
        "found_layers": found,
        "exported_layers": exported,
        "missing_source_layers": missing_sources,
        "uncertain_or_experimental_layers": uncertain,
    }


def write_catalog(rows: list[dict[str, Any]]) -> None:
    csv_path = OUT_DIR / "v3_layer_catalog_trondelag.csv"
    json_path = OUT_DIR / "v3_layer_catalog_trondelag.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_parameter_mapping(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    registry = load_json(ACCEPTANCE_REGISTRY)
    groups = {item["id"]: item for item in registry.get("groups", [])}
    layers_by_group: dict[str, list[str]] = {}
    for item in registry.get("layers", []):
        layers_by_group.setdefault(str(item["group_id"]), []).append(str(item["id"]))

    mapping = {
        "schema_version": "v3-trondelag-parameter-mapping/v0.1",
        "region_id": "trondelag",
        "source_inventory": {
            "catalog_csv": "v3_layer_catalog_trondelag.csv",
            "catalog_json": "v3_layer_catalog_trondelag.json",
            **summary,
        },
        "h3_policy": {
            "native_crs": "EPSG:25832",
            "web_export_crs": "EPSG:4326",
            "expose_h3_resolutions": [7, 6, 5],
            "default_h3_resolution": 7,
            "do_not_expose": [8, 9],
            "reason": "V2 Trondelag light runtime is offshore-trimmed R7 with R6/R5 rollups. Earlier R8 has 89312 hexes and R9 has 625387 hexes; they are too large and are not required for the interactive app.",
        },
        "parameter_groups": [
            {
                "id": "settlement_population",
                "label_sv_no": "Befolkning och bebyggelse",
                "v2_groups": ["settlement"],
                "analysis_kind": groups.get("settlement", {}).get("analysis_kind"),
                "default_layers": ["population_points"],
                "optional_layers": ["built_centre", "built_low_selection"],
                "buffer_control": {"min_m": 100, "max_m": 3000, "step_m": 50, "default_m": 100},
                "status": "proxy_default",
                "note": "Use the dissolved 250 m population-grid cell proxy. Be explicit that it is not individual population points.",
            },
            {
                "id": "transport_infrastructure",
                "label_sv_no": "Vägar, järnväg och transport",
                "v2_groups": ["transport", "infrastructure"],
                "analysis_kind": groups.get("transport", {}).get("analysis_kind"),
                "default_layers": ["roads_medium", "roads_large"],
                "optional_layers": ["TRL_RAILWAY", "TRL_EUROPEAN_ROADS", "TRL_COUNTY_ROADS", "TRL_HURTIGRUTEN_FERRY_ROUTE"],
                "buffer_control": {"min_m": 100, "max_m": 2000, "step_m": 25, "default_m": 100},
                "status": "roads_wired_railway_backlog",
                "note": "Roads are wired and exported as filtered N500 sublayers; railway is found in V2 candidate catalog but lacks a repo asset.",
            },
            {
                "id": "grid_connection",
                "label_sv_no": "Elinfrastruktur och nätanslutning",
                "v2_groups": ["electrical", "energy_potential"],
                "analysis_kind": groups.get("electrical", {}).get("analysis_kind"),
                "default_layers": ["high_voltage_lines", "underground_cables"],
                "optional_layers": ["existing_wind_turbines", "TRL_HYDROPOWER_PLANTS", "TRL_DAM_POINTS"],
                "distance_control": {"min_m": 500, "max_m": 15000, "step_m": 250, "default_m": 2000},
                "status": "wired_no_substations",
                "note": "Transmission lines use the verified UTM32 NVE source. Substations remain a missing source.",
            },
            {
                "id": "protected_nature",
                "label_sv_no": "Skyddad natur",
                "v2_groups": ["protected", "nature_protection"],
                "analysis_kind": groups.get("protected", {}).get("analysis_kind"),
                "default_layers": ["protected_areas"],
                "optional_layers": ["TRL_PROTECTED_WATERCOURSES", "TRL_WATER_PROTECTION", "TRL_N2000_NATURE_OVERVIEW"],
                "buffer_control": {"min_m": 0, "max_m": 2000, "step_m": 50, "default_m": 0},
                "status": "partly_wired",
                "note": "Naturvern is wired. Protected watercourses and water protection are high-priority next-step sources.",
            },
            {
                "id": "cultural_environment",
                "label_sv_no": "Kulturmiljö och kulturlandskap",
                "v2_groups": ["culture"],
                "analysis_kind": groups.get("culture", {}).get("analysis_kind"),
                "default_layers": ["cultural_preservation", "valuable_cultural_environment"],
                "optional_layers": ["TRL_SELECTED_AGRI_CULTURAL_LANDSCAPES"],
                "buffer_control": {"min_m": 0, "max_m": 1500, "step_m": 50, "default_m": 0},
                "status": "wired",
                "note": "Keep merged NW cultural heritage as QA to avoid double counting.",
            },
            {
                "id": "land_use_markdekke",
                "label_sv_no": "Markanvändning / markdekke",
                "v2_groups": ["land_use", "terrain_context"],
                "analysis_kind": groups.get("land_use", {}).get("analysis_kind"),
                "default_layers": ["forest_land_cover"],
                "optional_layers": ["TRL_WATER_AREAS", "TRL_LAND_MASK", "TRL_COASTLINE", "TRL_RIVER_NETWORK"],
                "buffer_control": {"min_m": 0, "max_m": 1000, "step_m": 50, "default_m": 0},
                "status": "forest_wired_context_backlog",
                "note": "Forest is intentionally separate from protected nature.",
            },
            {
                "id": "reindeer_husbandry",
                "label_sv_no": "Rennäring / reindrift",
                "v2_groups": ["reindeer"],
                "analysis_kind": groups.get("reindeer", {}).get("analysis_kind"),
                "default_layers": ["reindeer_grazing_merged"],
                "optional_layers": ["reindeer_migration_routes", "TRL_REINDEER_RESTRICTION_AREAS", "TRL_REINDEER_DISTRICTS"],
                "buffer_control": {"min_m": 0, "max_m": 5000, "step_m": 100, "default_m": 0},
                "status": "trondelag_specific_wired",
                "note": "No Bornholm equivalent. Keep this as a documented regional V3 deviation.",
            },
            {
                "id": "landscape_restrictions",
                "label_sv_no": "Landskapsrestriktioner",
                "v2_groups": ["landscape"],
                "default_layers": ["lablab_landscape_types_r7_app_extent"],
                "optional_layers": ["landscape_geocontext_types_r7", "landscape_geocontext_factors_r7"],
                "status": "qgis_reviewed_default",
                "note": "Use the QGIS-reviewed LABLAB R7 app-extent layer as the default. The data-driven geocontext layers remain method/debug context.",
            },
            {
                "id": "social_acceptance",
                "label_sv_no": "Social acceptans",
                "v2_groups": ["social_acceptance"],
                "default_layers": [],
                "optional_layers": ["social_acceptance_synthetic_r7"],
                "status": "synthetic_placeholder",
                "note": "Keep optional and clearly labelled as synthetic until real acceptance data exists.",
            },
        ],
        "reusable_v2_methods_for_v3": [
            "apps/potential_model/manifests.py: region-linked manifests and repo path resolution",
            "apps/potential_model/geometry.py: H3 display geometry loading and geometry_for_hex fallback",
            "apps/acceptance_model/layers.py: registry-driven groups/layers, asset manifest checks, source_geojson_for_layer and distance_table_for_layer",
            "apps/potential_model/wind_acceptance.py: normalize_group_layer_map, group distance merging, distance_conflict/proximity_feasibility/hard_exclusion acceptance functions",
            "script/acceptance/build_trondelag_population_250m_cell_proxy.R and render_trondelag_population_buffer.R: polygon proxy and dissolved buffer approach for Trondelag population",
            "script/acceptance/export_trondelag_*_assets.R pattern: source-to-GeoJSON, distance table and registry asset generation",
        ],
        "avoid_or_replace_in_v3": [
            "Bornholm TIMES/AreaDemand placeholder for Trondelag scenarios",
            "Trondelag R8/R9 exposure in the interactive app",
            "Unreviewed PDF-derived landscape polygons/rasters as final truth",
            "Hardcoded Bornholm/UTM33 assumptions for Trondelag buffers and distances",
            "Showing H3 buffer overlays for Trondelag population in the user-facing app",
            "Double counting QA/merged cultural or nature layers alongside primary sources",
        ],
        "trondelag_only_deviations": [
            "Native CRS EPSG:25832",
            "H3 display levels R7/R6/R5",
            "Reindeer husbandry controller",
            "250 m population-grid centroid proxy with dissolved polygon buffers",
            "Norwegian N500/NEA/NVE/RA/Landbruksdirektoratet source stack",
        ],
    }
    (OUT_DIR / "v3_parameter_mapping_suggestion.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def write_readme(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    missing = summary["missing_source_layers"]
    uncertain = summary["uncertain_or_experimental_layers"]
    export_paths = sorted(
        {
            path
            for item in rows
            for path in str(item.get("export_path") or "").split(";")
            if path
        }
    )
    text = f"""# Trondelag V2 to V3 Layer Inventory

Generated by `scripts/export_trondelag_v3_inventory.py`.

## Deliverables

- `v3_layer_catalog_trondelag.csv`
- `v3_layer_catalog_trondelag.json`
- `v3_parameter_mapping_suggestion.json`
- `geojson/` with V3-friendly EPSG:4326 exports
- `geojson_simplified/` with simplified display variants for heavy vector layers where created

## Summary

- Found layers/catalog rows: {summary['found_layers']}
- Exported layers: {summary['exported_layers']}
- Missing external source-only layers: {len(missing)}
- Uncertain, placeholder, synthetic or experimental layers: {len(uncertain)}

## H3 Policy

Trondelag should expose H3 R7, R6 and R5 only. R7 is the app-ready offshore-trimmed source level with 13,735 hexes; R6 has 2,163 hexes and R5 has 365 hexes. Earlier R8 and R9 products are intentionally not exposed: R8 has 89,312 hexes and the R9 minimal package has 625,387 hexes, which is too heavy for the current light interactive runtime.

All Trondelag distance, buffer and area geometry should use `EPSG:25832`. The exported GeoJSON files are `EPSG:4326` for web/V3 exchange.

## Important Layer Findings

- Railway is found as `TRL_RAILWAY` in the V2 candidate catalog, but it has no repo-local app asset yet.
- Reindeer husbandry is wired in V2 through `reindeer_grazing_merged` and `reindeer_migration_routes`; restriction areas and districts remain external/unverified FileGDB sources.
- Nature is partly wired: `protected_areas` is exported; protected watercourses and water protection are high-priority external candidates.
- Culture is wired through `cultural_preservation` and `valuable_cultural_environment`; merged/selected alternatives should stay QA/backlog until verified.
- Roads are exported as `roads_medium` and `roads_large`, derived from N500 `vegkategor`.
- Electrical infrastructure is exported through `high_voltage_lines`, `underground_cables` and `existing_wind_turbines`; substations are still missing.

## Data Status Rules

- `real_data`: source comes from a real regional GIS layer and has a repo-local V2 asset.
- `proxy_from_real_population_grid`: real population grid source, represented as a 250 m dissolved polygon proxy; not individual population points.
- `reviewed_pdf_derived_app_extent`: QGIS-reviewed LABLAB landscape work clipped to the current app extent.
- `experimental_pdf_derived`: PDF-derived LABLAB landscape work that has not passed QGIS review.
- `synthetic_test_data`: UI/integration placeholder, not research data.
- `placeholder`: manifest/model exists to keep the V2 UI running, but regional data is missing.
- `real_data_unverified_or_needs_extraction`: real external source listed, but not app-ready in this workspace.

## Recommended V3 Mapping

Use `v3_parameter_mapping_suggestion.json` as the first contract draft. The short version:

- `settlement_population`: population 250 m proxy default; tettsted and holiday-house centroids optional.
- `transport_infrastructure`: roads wired; railway and ferry/coastal transport backlog.
- `grid_connection`: transmission and underwater cables default; existing wind turbines optional; substations missing.
- `protected_nature`: Naturvern wired; protected watercourses and water protection next.
- `cultural_environment`: RA cultural heritage and NEA cultural landscapes wired.
- `land_use_markdekke`: forest wired as its own controller, separate from protected nature.
- `reindeer_husbandry`: Trondelag-specific controller; keep as a documented regional deviation.
- `landscape_restrictions`: QGIS-reviewed LABLAB R7 app-extent landscape types as default; data-driven geocontext stays optional method/debug context.
- `social_acceptance`: optional synthetic layer only until real data exists.

## V2 Code To Reuse

- `apps/potential_model/manifests.py` for region-linked manifest loading and path resolution.
- `apps/potential_model/geometry.py` for H3 display geometry lookup/fallback.
- `apps/acceptance_model/layers.py` for registry-driven groups, source layer specs, asset manifest checks and source GeoJSON loading.
- `apps/potential_model/wind_acceptance.py` for group-layer normalization, distance table rollup, and distance/proximity/hard-exclusion logic.
- `script/acceptance/build_trondelag_population_250m_cell_proxy.R` and `script/acceptance/render_trondelag_population_buffer.R` for the Trondelag population proxy and dissolved polygon-buffer behavior.
- `script/acceptance/export_trondelag_*_assets.R` as the reusable export pattern for V3 source assets and distance tables.

## V2 Code/Data To Avoid Or Replace

- Do not carry over Bornholm TIMES/AreaDemand as Trondelag scenario truth.
- Do not expose Trondelag R8/R9 in the interactive app.
- Do not use PDF-derived Trondelag landscape outputs as final data before review.
- Do not show Trondelag population buffers as H3 overlays in the user-facing app.
- Do not hardcode Bornholm CRS assumptions in Trondelag geometry work.
- Do not score QA/merged duplicate sources alongside primary culture/nature layers.

## Exported GeoJSON

{chr(10).join(f'- `{path}`' for path in export_paths)}

## Missing Source Layers

{chr(10).join(f'- `{layer_id}`' for layer_id in missing[:80])}

## Uncertain Or Experimental Layers

{chr(10).join(f'- `{layer_id}`' for layer_id in uncertain[:120])}
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    rows = build_catalog()
    rows.sort(key=lambda item: (str(item.get("v2_group", "")), str(item.get("layer_id", ""))))
    summary = summarize(rows)
    write_catalog(rows)
    write_parameter_mapping(rows, summary)
    write_readme(rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
