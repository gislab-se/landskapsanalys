from __future__ import annotations

import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "apps") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps"))

os.environ.setdefault("STREAMLIT_LOG_LEVEL", "error")
logging.getLogger("streamlit").setLevel(logging.ERROR)

import streamlit as st  # noqa: E402

import potential_app as app  # noqa: E402
import acceptance_model.layers as acceptance_layers  # noqa: E402
from acceptance_model import runtime_geometry  # noqa: E402
from apps.potential_model.manifests import load_region  # noqa: E402
from apps.potential_model.region_status import load_region_context  # noqa: E402


OUT_ROOT = ROOT / "exports" / "v3_migration" / "potential_runtime_full_frames"
REGIONS = ["bornholm", "trondelag", "vara"]


def _force_acceptance_registry(region_id: str) -> None:
    registry_name = "registry_trondelag.json" if region_id == "trondelag" else "registry_bornholm.json"
    path = ROOT / "apps" / "acceptance_model" / registry_name
    if not path.exists():
        path = ROOT / "apps" / "acceptance_model" / "registry.json"
    acceptance_layers.registry_path = lambda path=path: path
    runtime_geometry.active_registry_path = lambda path=path: path


def _recommended_display_resolution(region: dict[str, Any]) -> int | None:
    region_id = str(region.get("region_id", "") or "").lower()
    if region_id == "bornholm":
        return 8
    if region_id == "trondelag":
        return 7
    value = region.get("default_display_h3_resolution") or region.get("default_h3_resolution")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")


def _technology_frame_from_v2(
    frame: pd.DataFrame,
    technology: str,
    source_resolution: int,
    display_resolution: int,
    data_status: str,
    source_ref: str,
) -> pd.DataFrame:
    normalized = app._potential_establishment_source_frame(
        frame,
        technology,
        int(display_resolution),
        int(source_resolution),
        coarse_filter_intersection_blocks=(technology == "solar" and int(display_resolution) <= 7),
    )
    if normalized.empty:
        return pd.DataFrame(
            columns=[
                "hex_id",
                "technology_id",
                "suitable",
                "potential_score_pct",
                "potential_area_km2",
                "source_h3_resolution",
                "display_h3_resolution",
                "data_status",
                "source_ref",
            ]
        )
    result = pd.DataFrame(
        {
            "hex_id": normalized["hex_id"].astype(str),
            "technology_id": technology,
            "suitable": normalized[f"{technology}_suitable"].astype(bool),
            "potential_score_pct": pd.to_numeric(
                normalized[f"{technology}_potential_score"],
                errors="coerce",
            ).fillna(0.0),
            "potential_area_km2": pd.to_numeric(
                normalized[f"{technology}_potential_area_km2"],
                errors="coerce",
            ).fillna(0.0),
            "source_h3_resolution": int(source_resolution),
            "display_h3_resolution": int(display_resolution),
            "data_status": data_status,
            "source_ref": source_ref,
        }
    )
    return result.sort_values(["technology_id", "hex_id"]).reset_index(drop=True)


def _build_default_wind_frame(region: dict[str, Any], landscape_manifest: dict[str, Any], analysis_resolution: int) -> pd.DataFrame:
    selected = app.normalize_group_layer_map(app._default_wind_layer_selection())
    params = app._default_wind_params()
    preview = app._wind_polygon_preview_state(
        region,
        params,
        selected,
        int(analysis_resolution),
        False,
        family_key=f"v3_export_{region.get('region_id')}_wind",
        control_name=app.WIND_POTENTIAL_HEX_LABEL,
    )
    if preview.get("runtime_error"):
        raise RuntimeError(str(preview["runtime_error"]))
    return app._wind_polygon_summary_frame(region, landscape_manifest, preview["runtime_result"], int(analysis_resolution))


def _build_default_solar_frame(region: dict[str, Any], landscape_manifest: dict[str, Any], analysis_resolution: int) -> pd.DataFrame:
    config = dict(app.DEFAULT_SOLAR_APPLIED_CONFIG)
    filter_configs = app._solar_active_filter_configs(config)
    population_buffer_m = float(config.get("population_buffer_m", 500.0) or 0.0) if bool(config.get("large_population_active", False)) else 0.0
    protected_layer_ids = list(config.get("large_protected_layer_ids", []))
    protected_buffer_m = float(config.get("protected_buffer_m", 0.0) or 0.0) if protected_layer_ids else None
    large = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        int(analysis_resolution),
        population_buffer_m,
        protected_buffer_m,
        protected_layer_ids,
        bool(config.get("large_unfiltered_land_active", False)),
        filter_configs,
    )
    return app._combined_solar_hex_frame(
        region,
        landscape_manifest,
        int(analysis_resolution),
        pd.DataFrame(),
        large,
    )


def _class_counts(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty or "establishment_class" not in frame.columns:
        return {}
    counts = frame["establishment_class"].astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _export_region(region_id: str) -> dict[str, Any]:
    st.session_state.clear()
    _force_acceptance_registry(region_id)
    region = load_region(region_id)
    context = load_region_context(region)
    out_dir = OUT_ROOT / region_id
    out_dir.mkdir(parents=True, exist_ok=True)

    display_resolution = _recommended_display_resolution(region)
    if not context.get("runtime_ready") or display_resolution is None:
        manifest = {
            "region_id": region_id,
            "data_status": "missing",
            "reason": context.get("missing_data") or "Region has no runtime-ready V2 potential inputs.",
            "recommended_display_h3_resolution": display_resolution,
        }
        _write_json(out_dir / "manifest.json", manifest)
        return manifest

    app._ensure_default_start_state(region, force=True)
    landscape_manifest = context["landscape_manifest"]
    analysis_resolution = int(app._analysis_h3_resolution(region))
    display_geometry_path = app._h3_display_geometry_path(region, int(display_resolution))
    if not display_geometry_path:
        raise RuntimeError(f"{region_id}: missing display geometry for R{display_resolution}")

    wind_source = _build_default_wind_frame(region, landscape_manifest, analysis_resolution)
    solar_source = _build_default_solar_frame(region, landscape_manifest, analysis_resolution)

    data_status = "proxy" if region_id == "trondelag" else "ok"
    wind_frame = _technology_frame_from_v2(
        wind_source,
        "wind",
        analysis_resolution,
        int(display_resolution),
        data_status,
        f"v2_default_wind_r{analysis_resolution}",
    )
    solar_frame = _technology_frame_from_v2(
        solar_source,
        "solar",
        analysis_resolution,
        int(display_resolution),
        data_status,
        f"v2_default_solar_r{analysis_resolution}",
    )
    establishment = app._combined_potential_establishment_frame(
        region,
        wind_source,
        solar_source,
        pd.DataFrame(),
        pd.DataFrame(),
        int(display_resolution),
        analysis_resolution,
    )
    feature_collection = app._combined_establishment_feature_collection(
        establishment,
        display_geometry_path,
        int(display_resolution),
    )

    wind_source.to_csv(out_dir / f"wind_potential_source_r{analysis_resolution}.csv", index=False)
    solar_source.to_csv(out_dir / f"solar_potential_source_r{analysis_resolution}.csv", index=False)
    wind_frame.to_csv(out_dir / f"wind_technology_potential_frame_r{display_resolution}.csv", index=False)
    solar_frame.to_csv(out_dir / f"solar_technology_potential_frame_r{display_resolution}.csv", index=False)
    establishment.to_csv(out_dir / f"potential_establishment_frame_r{display_resolution}.csv", index=False)
    _write_json(out_dir / f"potential_establishment_area_r{display_resolution}.geojson", feature_collection)

    manifest = {
        "region_id": region_id,
        "data_status": data_status,
        "native_crs": region.get("native_crs"),
        "render_crs": region.get("web_crs", "EPSG:4326"),
        "analysis_h3_resolution": analysis_resolution,
        "recommended_display_h3_resolution": int(display_resolution),
        "available_h3_resolutions": region.get("available_h3_resolutions", []),
        "display_geometry_path": str(Path(display_geometry_path).relative_to(ROOT)),
        "output_files": {
            "wind_potential_source": f"wind_potential_source_r{analysis_resolution}.csv",
            "solar_potential_source": f"solar_potential_source_r{analysis_resolution}.csv",
            "wind_technology_potential_frame": f"wind_technology_potential_frame_r{display_resolution}.csv",
            "solar_technology_potential_frame": f"solar_technology_potential_frame_r{display_resolution}.csv",
            "potential_establishment_frame": f"potential_establishment_frame_r{display_resolution}.csv",
            "potential_establishment_area_geojson": f"potential_establishment_area_r{display_resolution}.geojson",
        },
        "counts": {
            "wind_source_rows": int(len(wind_source)),
            "solar_source_rows": int(len(solar_source)),
            "wind_display_rows": int(len(wind_frame)),
            "solar_display_rows": int(len(solar_frame)),
            "establishment_rows": int(len(establishment)),
            "establishment_features": int(len(feature_collection.get("features") or [])),
            "establishment_class_counts": _class_counts(establishment),
        },
        "notes": [
            "Scenario allocation and outside-LP are intentionally omitted.",
            "Join wind_technology_potential_frame and solar_technology_potential_frame on hex_id, or consume the ready GeoJSON layer.",
        ],
    }
    if region_id == "bornholm":
        manifest["notes"].append("Bornholm uses R10 as analysis/source and R8 as recommended web display.")
    if region_id == "trondelag":
        manifest["notes"].append("Trondelag is locked to R7/R6/R5; R8/R9 are not exposed.")
        manifest["notes"].append("Population/settlement inputs are proxy/modelled where active.")
    _write_json(out_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifests = []
    failures: list[str] = []
    for region_id in REGIONS:
        try:
            manifests.append(_export_region(region_id))
        except Exception as exc:
            failures.append(f"{region_id}: {exc}")
    index = {
        "schema_name": "v2_potential_runtime_full_frame_export",
        "schema_version": "2026-06-10",
        "regions": manifests,
        "failures": failures,
    }
    _write_json(OUT_ROOT / "index.json", index)
    print(json.dumps(index, indent=2, ensure_ascii=False, default=_json_default))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
