from __future__ import annotations

import json
import logging
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

import acceptance_model.layers as acceptance_layers  # noqa: E402
from acceptance_model import runtime_geometry  # noqa: E402
from apps.potential_model.manifests import load_region  # noqa: E402
from apps.potential_model.region_status import load_region_context  # noqa: E402
import potential_app as app  # noqa: E402


OUT_ROOT = ROOT / "exports" / "v3_migration"
EXAMPLE_CSV = OUT_ROOT / "potential_dynamic_buffer_examples.csv"
EXAMPLE_JSON = OUT_ROOT / "potential_dynamic_buffer_examples.json"
REGIONS = ["bornholm", "trondelag"]
BASE_ROAD_DISTANCE_M = 300.0
CHANGED_ROAD_DISTANCE_M = 400.0


def _force_acceptance_registry(region_id: str) -> None:
    registry_name = "registry_trondelag.json" if region_id == "trondelag" else "registry_bornholm.json"
    path = ROOT / "apps" / "acceptance_model" / registry_name
    if not path.exists():
        path = ROOT / "apps" / "acceptance_model" / "registry.json"
    acceptance_layers.registry_path = lambda path=path: path
    runtime_geometry.active_registry_path = lambda path=path: path


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")


def _display_resolution(region: dict[str, Any]) -> int:
    region_id = str(region.get("region_id", "") or "").lower()
    if region_id == "bornholm":
        return 8
    if region_id == "trondelag":
        return 7
    return int(region.get("default_display_h3_resolution") or region.get("default_h3_resolution") or 8)


def _build_wind_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    analysis_resolution: int,
    road_distance_m: float,
) -> pd.DataFrame:
    selected = app.normalize_group_layer_map(app._reference_default_wind_layer_selection())
    params = app._reference_default_wind_params()
    params["road_distance_m"] = float(road_distance_m)
    preview = app._wind_polygon_preview_state(
        region,
        params,
        selected,
        int(analysis_resolution),
        False,
        family_key=f"dynamic_road_{region.get('region_id')}_{int(road_distance_m)}",
        control_name=app.WIND_POTENTIAL_HEX_LABEL,
    )
    if preview.get("runtime_error"):
        raise RuntimeError(str(preview["runtime_error"]))
    return app._wind_polygon_summary_frame(region, landscape_manifest, preview["runtime_result"], int(analysis_resolution))


def _build_solar_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    analysis_resolution: int,
    road_buffer_m: float,
) -> pd.DataFrame:
    config = dict(app.DEFAULT_SOLAR_APPLIED_CONFIG)
    config["road_buffer_m"] = float(road_buffer_m)
    filter_configs = app._solar_active_filter_configs(config)
    population_buffer_m = (
        float(config.get("population_buffer_m", 500.0) or 0.0)
        if bool(config.get("large_population_active", False))
        else 0.0
    )
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


def _establishment_frame_for_road(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    analysis_resolution: int,
    display_resolution: int,
    road_distance_m: float,
) -> pd.DataFrame:
    wind = _build_wind_frame(region, landscape_manifest, analysis_resolution, road_distance_m)
    solar = _build_solar_frame(region, landscape_manifest, analysis_resolution, road_distance_m)
    return app._combined_potential_establishment_frame(
        region,
        wind,
        solar,
        pd.DataFrame(),
        pd.DataFrame(),
        int(display_resolution),
        int(analysis_resolution),
    )


def _class_counts(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty or "establishment_class" not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame["establishment_class"].astype(str).value_counts().to_dict().items()}


def _compare_region(region_id: str) -> dict[str, Any]:
    st.session_state.clear()
    _force_acceptance_registry(region_id)
    region = load_region(region_id)
    context = load_region_context(region)
    landscape_manifest = context.get("landscape_manifest")
    if not isinstance(landscape_manifest, dict):
        raise RuntimeError(f"{region_id}: missing landscape manifest")

    analysis_resolution = app._analysis_h3_resolution(region)
    display_resolution = _display_resolution(region)
    base = _establishment_frame_for_road(
        region,
        landscape_manifest,
        int(analysis_resolution),
        int(display_resolution),
        BASE_ROAD_DISTANCE_M,
    )
    changed = _establishment_frame_for_road(
        region,
        landscape_manifest,
        int(analysis_resolution),
        int(display_resolution),
        CHANGED_ROAD_DISTANCE_M,
    )

    compare_columns = [
        "hex_id",
        "establishment_class",
        "wind_suitable",
        "solar_suitable",
        "wind_potential_score",
        "solar_potential_score",
        "wind_potential_area_km2",
        "solar_potential_area_km2",
    ]
    before = base[[column for column in compare_columns if column in base.columns]].copy()
    after = changed[[column for column in compare_columns if column in changed.columns]].copy()
    joined = before.merge(after, on="hex_id", how="outer", suffixes=("_before", "_after"))
    for technology in ["wind", "solar"]:
        for suffix in ["before", "after"]:
            suitable_col = f"{technology}_suitable_{suffix}"
            if suitable_col in joined.columns:
                joined[suitable_col] = joined[suitable_col].map(lambda value: False if pd.isna(value) else bool(value))
            for measure in ["potential_score", "potential_area_km2"]:
                col = f"{technology}_{measure}_{suffix}"
                if col in joined.columns:
                    joined[col] = pd.to_numeric(joined[col], errors="coerce").fillna(0.0)
    for suffix in ["before", "after"]:
        class_col = f"establishment_class_{suffix}"
        if class_col in joined.columns:
            joined[class_col] = joined[class_col].fillna("not_suitable").astype(str)

    changed_mask = (
        joined["establishment_class_before"].ne(joined["establishment_class_after"])
        | joined["wind_suitable_before"].ne(joined["wind_suitable_after"])
        | joined["solar_suitable_before"].ne(joined["solar_suitable_after"])
    )
    deltas = joined.loc[changed_mask].copy()
    deltas["wind_area_delta_km2"] = deltas["wind_potential_area_km2_after"] - deltas["wind_potential_area_km2_before"]
    deltas["solar_area_delta_km2"] = deltas["solar_potential_area_km2_after"] - deltas["solar_potential_area_km2_before"]
    deltas["class_changed"] = deltas["establishment_class_before"].ne(deltas["establishment_class_after"])
    deltas["wind_suitable_changed"] = deltas["wind_suitable_before"].ne(deltas["wind_suitable_after"])
    deltas["solar_suitable_changed"] = deltas["solar_suitable_before"].ne(deltas["solar_suitable_after"])
    deltas["region_id"] = region_id
    deltas["display_h3_resolution"] = int(display_resolution)
    deltas["analysis_h3_resolution"] = int(analysis_resolution)
    deltas["road_distance_m_before"] = BASE_ROAD_DISTANCE_M
    deltas["road_distance_m_after"] = CHANGED_ROAD_DISTANCE_M

    priority = {
        "wind_and_solar": 0,
        "wind_only": 1,
        "solar_only": 2,
        "not_suitable": 3,
    }
    deltas["_priority_before"] = deltas["establishment_class_before"].map(priority).fillna(99)
    deltas["_priority_after"] = deltas["establishment_class_after"].map(priority).fillna(99)
    examples = (
        deltas.sort_values(
            [
                "class_changed",
                "wind_suitable_changed",
                "solar_suitable_changed",
                "_priority_before",
                "_priority_after",
                "hex_id",
            ],
            ascending=[False, False, False, True, True, True],
        )
        .drop(columns=["_priority_before", "_priority_after"], errors="ignore")
        .head(5)
        .reset_index(drop=True)
    )
    return {
        "region_id": region_id,
        "analysis_h3_resolution": int(analysis_resolution),
        "display_h3_resolution": int(display_resolution),
        "road_distance_m_before": BASE_ROAD_DISTANCE_M,
        "road_distance_m_after": CHANGED_ROAD_DISTANCE_M,
        "class_counts_before": _class_counts(base),
        "class_counts_after": _class_counts(changed),
        "changed_hex_count": int(len(deltas)),
        "class_changed_hex_count": int(deltas["class_changed"].sum()) if not deltas.empty else 0,
        "wind_suitable_changed_hex_count": int(deltas["wind_suitable_changed"].sum()) if not deltas.empty else 0,
        "solar_suitable_changed_hex_count": int(deltas["solar_suitable_changed"].sum()) if not deltas.empty else 0,
        "examples": examples.to_dict(orient="records"),
    }


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    region_results = []
    rows: list[dict[str, Any]] = []
    for region_id in REGIONS:
        result = _compare_region(region_id)
        region_results.append(result)
        rows.extend(result["examples"])

    example_frame = pd.DataFrame(rows)
    if not example_frame.empty:
        column_order = [
            "region_id",
            "hex_id",
            "analysis_h3_resolution",
            "display_h3_resolution",
            "road_distance_m_before",
            "road_distance_m_after",
            "establishment_class_before",
            "establishment_class_after",
            "wind_suitable_before",
            "wind_suitable_after",
            "solar_suitable_before",
            "solar_suitable_after",
            "wind_potential_score_before",
            "wind_potential_score_after",
            "wind_potential_area_km2_before",
            "wind_potential_area_km2_after",
            "wind_area_delta_km2",
            "solar_potential_score_before",
            "solar_potential_score_after",
            "solar_potential_area_km2_before",
            "solar_potential_area_km2_after",
            "solar_area_delta_km2",
            "class_changed",
            "wind_suitable_changed",
            "solar_suitable_changed",
        ]
        example_frame = example_frame[[column for column in column_order if column in example_frame.columns]]
    example_frame.to_csv(EXAMPLE_CSV, index=False)
    _write_json(
        EXAMPLE_JSON,
        {
            "schema_name": "v2_potential_dynamic_buffer_examples",
            "schema_version": "2026-06-10",
            "description": "V2 runtime comparison where both wind road_distance_m and solar road_buffer_m change from 300 m to 400 m.",
            "regions": region_results,
            "csv": str(EXAMPLE_CSV.relative_to(ROOT)),
        },
    )
    print(json.dumps({"regions": region_results, "csv": str(EXAMPLE_CSV)}, ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
