from __future__ import annotations

import importlib.util
import logging
import math
import os
import sys
import warnings
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "apps") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps"))

os.environ.setdefault("STREAMLIT_LOG_LEVEL", "error")
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

import streamlit as st  # noqa: E402

import potential_app as app  # noqa: E402
import acceptance_model.layers as acceptance_layers  # noqa: E402
from acceptance_model import runtime_geometry  # noqa: E402
from potential_model.energy_modeling import (  # noqa: E402
    calculate_area_demand,
    load_area_demand_bundle,
    load_energy_model_inputs,
    planning_scenario_label,
    planning_scenarios,
    scenario_display_label,
    select_planning_mix,
    build_times_summary,
)
from potential_model.manifests import load_linked_manifest, load_region  # noqa: E402
from potential_model.region_status import load_region_context  # noqa: E402


runtime_geometry.RUNTIME_RELATIVE_DIR = "artifacts/potential_region_parity/prototype_runtime"

WIND_TEST_SELECTION = {
    group_id: []
    for group_id in app.WIND_GROUP_LAYER_DEFAULTS
}
WIND_TEST_SELECTION[app.WIND_SETTLEMENT_GROUP_ID] = [app.WIND_POPULATION_SOURCE_LAYER_ID]
ROAD_TEST_LAYER_ID = "roads_large"
PROTECTED_TEST_LAYER_ID = "protected_areas"
CULTURE_TEST_LAYER_IDS = ["cultural_preservation", "valuable_cultural_environment"]
REINDEER_TEST_LAYER_IDS = ["reindeer_grazing_merged", "reindeer_migration_routes"]
ELECTRICAL_TEST_LAYER_IDS = ["high_voltage_lines", "underground_cables", "existing_wind_turbines"]
BORNHOLM_ELECTRICAL_TEST_LAYER_IDS = ["high_voltage_lines", "underground_cables", "power_substations", "existing_wind_turbines"]
SOLAR_ROAD_BUFFER_M = 100.0
WIND_ROAD_BUFFER_M = 1000.0
ELECTRICAL_MAX_DISTANCE_M = 2000.0
PROTECTED_BUFFER_M = 0.0
CULTURE_BUFFER_M = 0.0
REINDEER_BUFFER_M = 0.0
WIND_TEST_SELECTION[app.SOLAR_ROAD_GROUP_ID] = [ROAD_TEST_LAYER_ID]
WIND_TEST_SELECTION[app.SOLAR_PROTECTED_GROUP_ID] = [PROTECTED_TEST_LAYER_ID]
WIND_TEST_SELECTION[app.WIND_CULTURE_GROUP_ID] = CULTURE_TEST_LAYER_IDS
WIND_TEST_SELECTION[app.WIND_REINDEER_GROUP_ID] = REINDEER_TEST_LAYER_IDS


def _electrical_test_layer_ids(region_id: str) -> list[str]:
    if str(region_id).lower() == "bornholm":
        return list(BORNHOLM_ELECTRICAL_TEST_LAYER_IDS)
    return list(ELECTRICAL_TEST_LAYER_IDS)


def _force_acceptance_registry(region_id: str) -> None:
    registry_name = "registry_trondelag.json" if str(region_id).lower() == "trondelag" else "registry.json"
    path = ROOT / "apps" / "acceptance_model" / registry_name
    acceptance_layers.registry_path = lambda path=path: path
    runtime_geometry.active_registry_path = lambda path=path: path


class ParityReport:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.failures: list[str] = []

    def pass_(self, message: str) -> None:
        self.passes.append(message)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def check(self, condition: bool, pass_message: str, fail_message: str) -> None:
        if condition:
            self.pass_(pass_message)
        else:
            self.fail(fail_message)

    def emit(self) -> int:
        print("Potential App Bornholm parity")
        print("=" * 29)
        if self.failures:
            print("\nBLOCKERS")
            for idx, message in enumerate(self.failures, start=1):
                print(f"{idx}. FAIL {message}")
        else:
            print("\nBLOCKERS")
            print("None")
        print("\nCHECKS")
        for message in self.passes:
            print(f"- PASS {message}")
        status = "FAIL" if self.failures else "PASS"
        print(f"\nRESULT: {status} ({len(self.passes)} passed, {len(self.failures)} blocker(s))")
        return 1 if self.failures else 0


def _require_dependencies(report: ParityReport) -> bool:
    ok = True
    for package in ["duckdb", "openpyxl"]:
        installed = importlib.util.find_spec(package) is not None
        report.check(
            installed,
            f"{package} is installed.",
            f"{package} is missing; the energy-model proposal path cannot run.",
        )
        ok = ok and installed
    return ok


def _technology_to_times_map(scenario_manifest: dict[str, Any]) -> dict[str, str]:
    duckdb_cfg = (((scenario_manifest.get("energy_model") or {}).get("duckdb") or {}).get("technology_map") or {})
    return {str(key): str(value) for key, value in duckdb_cfg.items()}


def _energy_state(region: dict[str, Any], scenario_manifest: dict[str, Any], h3_resolution: int) -> dict[str, Any]:
    inputs = load_energy_model_inputs(scenario_manifest, ROOT)
    area_bundle = load_area_demand_bundle(scenario_manifest, ROOT)
    _, mix = build_times_summary(inputs.times_rows)
    planning_options = planning_scenarios(scenario_manifest)
    planning = next(
        (item for item in planning_options if str(item.get("id")) == "medium"),
        planning_options[0],
    )
    selected_mix = app._balance_wind_solar_mix(select_planning_mix(mix, planning), 50.0)
    area_scenario = str(planning.get("area_demand_scenario", "mid") or "mid")
    area_demand = calculate_area_demand(
        selected_mix,
        area_bundle,
        area_scenario,
        _technology_to_times_map(scenario_manifest),
    )
    wind_row = area_demand[area_demand["energy_key"].astype(str) == "wind"]
    solar_row = area_demand[area_demand["energy_key"].astype(str) == "solar"]

    def sum_col(frame: pd.DataFrame, column: str) -> float:
        return float(pd.to_numeric(frame.get(column, pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()) if not frame.empty else 0.0

    def first_col(frame: pd.DataFrame, column: str) -> float:
        values = pd.to_numeric(frame.get(column, pd.Series(dtype=float)), errors="coerce").dropna()
        return float(values.iloc[0]) if not values.empty else math.nan

    source_scenario = str(planning.get("source_scenario", "") or "")
    return {
        "available": True,
        "scenario": str(planning.get("id", "medium")),
        "scenario_label": planning_scenario_label(planning),
        "source_scenario": source_scenario,
        "source_scenario_label": scenario_display_label(source_scenario, inputs.scenario_descriptions) if source_scenario else "-",
        "source_year": int(planning.get("planning_year", 2050) or 2050),
        "energy_scale": float(planning.get("energy_scale", 1.0) or 1.0),
        "area_scenario_id": area_scenario,
        "area_scenario_label": app._area_scenario_label(area_scenario),
        "placement_mode": "auto",
        "show_proposal": True,
        "area_demand": area_demand,
        "wind_share_pct": 50.0,
        "solar_share_pct": 50.0,
        "wind_area_need_km2": sum_col(wind_row, "area_need_km2"),
        "wind_km2_per_twh": first_col(wind_row, "km2_per_twh"),
        "solar_area_need_km2": sum_col(solar_row, "area_need_km2"),
        "solar_km2_per_twh": first_col(solar_row, "km2_per_twh"),
        "wind_twh": sum_col(wind_row, "twh"),
        "solar_twh": sum_col(solar_row, "twh"),
        "hex_area_km2": float(app.h3_hex_area_km2(int(h3_resolution))),
        "h3_resolution": int(h3_resolution),
        "auto_min_potential_share_pct": float(((scenario_manifest.get("energy_model") or {}).get("planning") or {}).get("auto_min_potential_share_pct", 65.0)),
        "source_status": inputs.source_status,
    }


def _feature_count(layer: dict[str, Any] | None) -> int:
    if not isinstance(layer, dict):
        return 0
    features = ((layer.get("feature_collection") or {}).get("features") or [])
    return len(features) if isinstance(features, list) else 0


def _establishment_class_change_count(before: pd.DataFrame, after: pd.DataFrame) -> int:
    if before.empty or after.empty:
        return 0
    required = {"hex_id", "establishment_class"}
    if not required.issubset(before.columns) or not required.issubset(after.columns):
        return 0
    merged = before[["hex_id", "establishment_class"]].merge(
        after[["hex_id", "establishment_class"]],
        on="hex_id",
        how="inner",
        suffixes=("_before", "_after"),
    )
    if merged.empty:
        return 0
    return int(
        (
            merged["establishment_class_before"].astype(str)
            != merged["establishment_class_after"].astype(str)
        ).sum()
    )


def _solar_area_km2(frame: pd.DataFrame) -> float:
    return float(
        pd.to_numeric(frame.get("potential_area_km2", pd.Series(dtype=float)), errors="coerce")
        .fillna(0.0)
        .sum()
    )


def _road_ui_layer_contract(layers: list[dict[str, Any]]) -> dict[str, Any]:
    solar_sources: list[dict[str, Any]] = []
    wind_sources: list[dict[str, Any]] = []
    solar_buffers: list[dict[str, Any]] = []
    wind_buffers: list[dict[str, Any]] = []
    for layer in layers:
        source_id = str(layer.get("source_layer_id", "") or "")
        buffer_id = str(layer.get("buffer_layer_id", "") or "")
        name = str(layer.get("name", "") or "")
        if source_id.startswith(f"solar:{app.SOLAR_ROAD_GROUP_ID}:"):
            solar_sources.append(layer)
        if source_id == f"wind:{ROAD_TEST_LAYER_ID}" or source_id.startswith(f"wind:{ROAD_TEST_LAYER_ID}:"):
            wind_sources.append(layer)
        if buffer_id.startswith(f"solar:{app.SOLAR_ROAD_GROUP_ID}:buffer:"):
            solar_buffers.append(layer)
        if buffer_id.startswith(f"wind:{app.SOLAR_ROAD_GROUP_ID}:buffer:"):
            wind_buffers.append(layer)
        elif name.startswith("Vindbuffert:") and app.SOLAR_ROAD_GROUP_ID in buffer_id:
            wind_buffers.append(layer)
    road_layers = [*solar_sources, *wind_sources, *solar_buffers, *wind_buffers]
    road_names = [str(layer.get("name", "") or "") for layer in road_layers]
    road_ids = [
        str(layer.get("source_layer_id", "") or layer.get("buffer_layer_id", "") or layer.get("name", "") or "")
        for layer in road_layers
    ]
    return {
        "solar_source_count": len(solar_sources),
        "wind_source_count": len(wind_sources),
        "solar_buffer_count": len(solar_buffers),
        "wind_buffer_count": len(wind_buffers),
        "solar_source_features": sum(_feature_count(layer) for layer in solar_sources),
        "wind_source_features": sum(_feature_count(layer) for layer in wind_sources),
        "solar_buffer_features": sum(_feature_count(layer) for layer in solar_buffers),
        "wind_buffer_features": sum(_feature_count(layer) for layer in wind_buffers),
        "road_layer_names": road_names,
        "road_layer_ids": road_ids,
        "road_layer_names_are_distinct": len(road_names) == len(set(road_names)),
        "road_layer_ids_are_distinct": len(road_ids) == len(set(road_ids)),
        "solar_buffer_ids": [str(layer.get("buffer_layer_id", "") or "") for layer in solar_buffers],
        "wind_buffer_ids": [str(layer.get("buffer_layer_id", "") or "") for layer in wind_buffers],
    }


def _region_workspace_contract(region_id: str) -> dict[str, Any]:
    st.session_state.clear()
    st.session_state[app.REGION_SELECT_KEY] = region_id
    _force_acceptance_registry(region_id)
    region = load_region(region_id)
    context = load_region_context(region)
    landscape_manifest = context["landscape_manifest"]
    scenario_manifest = context["scenario_manifest"]
    if not context.get("runtime_ready"):
        raise RuntimeError(f"{region_id} is not runtime_ready: {context.get('missing_data')}")
    if not isinstance(landscape_manifest, dict) or not isinstance(scenario_manifest, dict):
        raise RuntimeError(f"{region_id} is missing linked landscape/scenario manifests.")

    display_resolution = int(region.get("default_display_h3_resolution") or region.get("default_h3_resolution") or 8)
    display_resolution = app._preferred_h3_resolution(region, display_resolution)
    analysis_resolution = app._analysis_h3_resolution(region)
    analysis_hex_area_km2 = float(app.h3_hex_area_km2(analysis_resolution))
    display_geometry_path = app._h3_display_geometry_path(region, display_resolution)
    analysis_display_geometry_path = app._h3_display_geometry_path(region, analysis_resolution)

    energy_state = _energy_state(region, scenario_manifest, analysis_resolution)
    electrical_layer_ids = _electrical_test_layer_ids(region_id)
    wind_selection = app.normalize_group_layer_map(WIND_TEST_SELECTION)
    wind_selection[app.SOLAR_ELECTRICAL_GROUP_ID] = electrical_layer_ids
    if region_id != "trondelag":
        wind_selection[app.WIND_REINDEER_GROUP_ID] = []
    wind_params = app._default_wind_params()
    road_param_key = app.GROUP_PARAM_MAP.get(app.SOLAR_ROAD_GROUP_ID)
    if road_param_key:
        wind_params[road_param_key] = WIND_ROAD_BUFFER_M
    electrical_param_key = app.GROUP_PARAM_MAP.get(app.SOLAR_ELECTRICAL_GROUP_ID)
    if electrical_param_key:
        wind_params[electrical_param_key] = ELECTRICAL_MAX_DISTANCE_M
    wind_preview = app._wind_polygon_preview_state(
        region,
        wind_params,
        wind_selection,
        display_resolution,
        False,
        family_key=f"parity_{region_id}_wind",
        control_name=app.WIND_POTENTIAL_HEX_LABEL,
    )
    if wind_preview["runtime_error"]:
        raise RuntimeError(f"{region_id} wind runtime failed: {wind_preview['runtime_error']}")
    wind_preview_layers = list(wind_preview["layers"])
    if region_id == "trondelag" and energy_state.get("available"):
        wind_preview_layers = [
            layer
            for layer in wind_preview_layers
            if str(layer.get("source_layer_id", "") or "").startswith("wind:")
            or str(layer.get("buffer_layer_id", "") or "").startswith("wind:")
        ]
    wind_potential = app._wind_polygon_summary_frame(
        region,
        landscape_manifest,
        wind_preview["runtime_result"],
        analysis_resolution,
    )
    wind_runtime_groups = (wind_preview.get("runtime_result") or {}).get("groups") or {}
    wind_has_transport_rule = app.SOLAR_ROAD_GROUP_ID in wind_runtime_groups
    wind_has_protected_rule = app.SOLAR_PROTECTED_GROUP_ID in wind_runtime_groups
    wind_has_culture_rule = app.WIND_CULTURE_GROUP_ID in wind_runtime_groups
    wind_has_reindeer_rule = app.WIND_REINDEER_GROUP_ID in wind_runtime_groups
    wind_has_electrical_rule = app.SOLAR_ELECTRICAL_GROUP_ID in wind_runtime_groups

    solar_population_buffer_m = 250.0
    solar_road_filter_configs = [
        {
            "group_id": app.SOLAR_ROAD_GROUP_ID,
            "layer_ids": [ROAD_TEST_LAYER_ID],
            "buffer_m": SOLAR_ROAD_BUFFER_M,
            "label": "Vägar",
        }
    ]
    solar_large = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        solar_population_buffer_m,
        None,
        [],
        False,
        solar_road_filter_configs,
    )
    solar_road_source_layers = app._solar_filter_source_layers(app.SOLAR_ROAD_GROUP_ID, [ROAD_TEST_LAYER_ID])
    solar_road_buffer_layer = app._solar_filter_buffer_layer(app.SOLAR_ROAD_GROUP_ID, SOLAR_ROAD_BUFFER_M, [ROAD_TEST_LAYER_ID])
    solar_road_buffer_features = _feature_count(solar_road_buffer_layer)
    solar_road_source_features = sum(
        _feature_count(layer)
        for layer in solar_road_source_layers
    )
    solar_has_road_filter_effect = pd.to_numeric(
        solar_large.get("protected_buffer_share_pct", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0).gt(0.0).any()
    solar_large_without_road = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        solar_population_buffer_m,
        None,
        [],
        False,
        [],
    )
    solar_road_area_reduction_km2 = max(0.0, _solar_area_km2(solar_large_without_road) - _solar_area_km2(solar_large))
    solar_unfiltered_no_population = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        [],
    )
    solar_electrical_filter_configs = [
        {
            "group_id": app.SOLAR_ELECTRICAL_GROUP_ID,
            "layer_ids": electrical_layer_ids,
            "buffer_m": ELECTRICAL_MAX_DISTANCE_M,
            "label": "Elinfrastruktur",
            "effect": "feasibility",
        }
    ]
    solar_electrical = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        solar_electrical_filter_configs,
    )
    solar_without_electrical = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        [],
    )
    solar_electrical_area_m2 = float(
        pd.to_numeric(solar_electrical.get("potential_area_m2", pd.Series(dtype=float)), errors="coerce")
        .fillna(0.0)
        .sum()
    )
    solar_without_electrical_area_m2 = float(
        pd.to_numeric(solar_without_electrical.get("potential_area_m2", pd.Series(dtype=float)), errors="coerce")
        .fillna(0.0)
        .sum()
    )
    solar_has_electrical_feasibility_effect = (
        solar_electrical_area_m2 > 0.0
        and solar_without_electrical_area_m2 > 0.0
        and solar_electrical_area_m2 < solar_without_electrical_area_m2
    )
    solar_electrical_source_layers = app._solar_filter_source_layers(app.SOLAR_ELECTRICAL_GROUP_ID, electrical_layer_ids)
    solar_electrical_buffer_layer = app._solar_filter_buffer_layer(app.SOLAR_ELECTRICAL_GROUP_ID, ELECTRICAL_MAX_DISTANCE_M, electrical_layer_ids)
    solar_electrical_source_features = sum(
        _feature_count(layer)
        for layer in solar_electrical_source_layers
    )
    solar_electrical_buffer_features = _feature_count(solar_electrical_buffer_layer)
    solar_protected_filter_configs = [
        {
            "group_id": app.SOLAR_PROTECTED_GROUP_ID,
            "layer_ids": [PROTECTED_TEST_LAYER_ID],
            "buffer_m": PROTECTED_BUFFER_M,
            "label": "Skyddad natur",
        }
    ]
    solar_protected = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        solar_protected_filter_configs,
    )
    solar_protected_area_reduction_km2 = max(0.0, _solar_area_km2(solar_unfiltered_no_population) - _solar_area_km2(solar_protected))
    solar_has_protected_filter_effect = pd.to_numeric(
        solar_protected.get("protected_buffer_share_pct", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0).gt(0.0).any()
    solar_protected_source_layers = app._solar_protected_source_layers([PROTECTED_TEST_LAYER_ID])
    solar_protected_buffer_layer = app._solar_protected_buffer_layer(PROTECTED_BUFFER_M, [PROTECTED_TEST_LAYER_ID])
    solar_protected_source_features = sum(
        _feature_count(layer)
        for layer in solar_protected_source_layers
    )
    solar_protected_buffer_features = _feature_count(solar_protected_buffer_layer)
    solar_culture_filter_configs = [
        {
            "group_id": app.SOLAR_CULTURE_GROUP_ID,
            "layer_ids": CULTURE_TEST_LAYER_IDS,
            "buffer_m": CULTURE_BUFFER_M,
            "label": "Kulturmiljö",
        }
    ]
    solar_culture = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        solar_culture_filter_configs,
    )
    solar_culture_area_reduction_km2 = max(0.0, _solar_area_km2(solar_unfiltered_no_population) - _solar_area_km2(solar_culture))
    solar_has_culture_filter_effect = pd.to_numeric(
        solar_culture.get("protected_buffer_share_pct", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0).gt(0.0).any()
    solar_culture_source_layers = app._solar_filter_source_layers(app.SOLAR_CULTURE_GROUP_ID, CULTURE_TEST_LAYER_IDS)
    solar_culture_buffer_layer = app._solar_filter_buffer_layer(app.SOLAR_CULTURE_GROUP_ID, CULTURE_BUFFER_M, CULTURE_TEST_LAYER_IDS)
    solar_culture_source_features = sum(
        _feature_count(layer)
        for layer in solar_culture_source_layers
    )
    solar_culture_buffer_features = _feature_count(solar_culture_buffer_layer)
    solar_reindeer_filter_configs = [
        {
            "group_id": app.SOLAR_REINDEER_GROUP_ID,
            "layer_ids": REINDEER_TEST_LAYER_IDS,
            "buffer_m": REINDEER_BUFFER_M,
            "label": "Rennäring / reindrift",
        }
    ]
    solar_reindeer = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        0.0,
        None,
        [],
        False,
        solar_reindeer_filter_configs,
    )
    solar_has_reindeer_filter_effect = pd.to_numeric(
        solar_reindeer.get("protected_buffer_share_pct", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0).gt(0.0).any()
    solar_reindeer_source_layers = app._solar_filter_source_layers(app.SOLAR_REINDEER_GROUP_ID, REINDEER_TEST_LAYER_IDS)
    solar_reindeer_buffer_layer = app._solar_filter_buffer_layer(app.SOLAR_REINDEER_GROUP_ID, REINDEER_BUFFER_M, REINDEER_TEST_LAYER_IDS)
    solar_reindeer_source_features = sum(
        _feature_count(layer)
        for layer in solar_reindeer_source_layers
    )
    solar_reindeer_buffer_features = _feature_count(solar_reindeer_buffer_layer)
    solar_potential = app._combined_solar_hex_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        pd.DataFrame(),
        solar_large,
    )
    solar_proposal, solar_stats = app._solar_establishment_frame(
        pd.DataFrame(),
        solar_large,
        float(energy_state.get("solar_area_need_km2", 0.0) or 0.0),
        float(energy_state.get("solar_twh", 0.0) or 0.0),
        float(energy_state.get("solar_km2_per_twh", math.nan) or math.nan),
        analysis_hex_area_km2,
    )
    solar_proposal, solar_stats = app._expand_solar_area_outside_lp(
        solar_potential,
        solar_proposal,
        solar_stats,
        analysis_display_geometry_path,
        analysis_hex_area_km2,
        float(energy_state.get("solar_twh", 0.0) or 0.0),
        float(energy_state.get("solar_area_need_km2", 0.0) or 0.0),
        float(energy_state.get("solar_km2_per_twh", math.nan) or math.nan),
    )

    wind_proposal, wind_stats = app.allocate_wind_area_from_core_hexes(
        wind_potential,
        float(energy_state.get("wind_area_need_km2", 0.0) or 0.0),
        analysis_hex_area_km2,
        float(energy_state.get("auto_min_potential_share_pct", 65.0) or 65.0),
    )
    wind_proposal, wind_stats = app._expand_wind_area_outside_et(
        wind_potential,
        wind_proposal,
        wind_stats,
        analysis_display_geometry_path,
        analysis_hex_area_km2,
    )
    wind_factor = float(energy_state.get("wind_km2_per_twh", math.nan) or math.nan)
    wind_twh_need = float(energy_state.get("wind_twh", 0.0) or 0.0)
    wind_area_need = float(energy_state.get("wind_area_need_km2", 0.0) or 0.0)
    if not wind_proposal.empty:
        if wind_factor > 0 and math.isfinite(wind_factor):
            wind_proposal["allocated_twh"] = wind_proposal["allocated_area_km2"].astype(float) / wind_factor
        elif wind_area_need > 0:
            wind_proposal["allocated_twh"] = wind_twh_need * wind_proposal["allocated_area_km2"].astype(float) / wind_area_need
        else:
            wind_proposal["allocated_twh"] = 0.0
        wind_proposal["allocated_gwh"] = wind_proposal["allocated_twh"].astype(float) * 1000.0

    solar_potential_without_road = app._combined_solar_hex_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        pd.DataFrame(),
        solar_large_without_road,
    )
    solar_proposal_without_road, solar_stats_without_road = app._solar_establishment_frame(
        pd.DataFrame(),
        solar_large_without_road,
        float(energy_state.get("solar_area_need_km2", 0.0) or 0.0),
        float(energy_state.get("solar_twh", 0.0) or 0.0),
        float(energy_state.get("solar_km2_per_twh", math.nan) or math.nan),
        analysis_hex_area_km2,
    )
    solar_proposal_without_road, solar_stats_without_road = app._expand_solar_area_outside_lp(
        solar_potential_without_road,
        solar_proposal_without_road,
        solar_stats_without_road,
        analysis_display_geometry_path,
        analysis_hex_area_km2,
        float(energy_state.get("solar_twh", 0.0) or 0.0),
        float(energy_state.get("solar_area_need_km2", 0.0) or 0.0),
        float(energy_state.get("solar_km2_per_twh", math.nan) or math.nan),
    )
    establishment_without_solar_road = app._combined_potential_establishment_frame(
        region,
        wind_potential,
        solar_potential_without_road,
        wind_proposal,
        solar_proposal_without_road,
        analysis_resolution,
        analysis_resolution,
    )
    establishment_with_solar_road = app._combined_potential_establishment_frame(
        region,
        wind_potential,
        solar_potential,
        wind_proposal,
        solar_proposal,
        analysis_resolution,
        analysis_resolution,
    )
    solar_road_establishment_class_changes = _establishment_class_change_count(
        establishment_without_solar_road,
        establishment_with_solar_road,
    )

    establishment_layers = app._combined_potential_establishment_family_layers(
        region,
        wind_potential,
        solar_potential,
        wind_proposal,
        solar_proposal,
        display_resolution,
        False,
        analysis_resolution,
    )
    road_ui_layers = [
        *wind_preview_layers,
        *solar_road_source_layers,
        *([solar_road_buffer_layer] if solar_road_buffer_layer is not None else []),
    ]
    all_layers = app._dedupe_layers([*road_ui_layers, *establishment_layers])
    road_ui_contract = _road_ui_layer_contract(app._dedupe_layers(road_ui_layers))
    establishment_layer = next(
        (
            layer
            for layer in establishment_layers
            if str(layer.get("name", "")).startswith(app.COMBINED_ESTABLISHMENT_LAYER_LABEL)
        ),
        None,
    )
    return {
        "region_id": region_id,
        "display_resolution": display_resolution,
        "analysis_resolution": analysis_resolution,
        "wind_potential_rows": len(wind_potential),
        "wind_has_transport_rule": bool(wind_has_transport_rule),
        "wind_has_protected_rule": bool(wind_has_protected_rule),
        "wind_has_culture_rule": bool(wind_has_culture_rule),
        "wind_has_reindeer_rule": bool(wind_has_reindeer_rule),
        "wind_has_electrical_rule": bool(wind_has_electrical_rule),
        "solar_potential_rows": len(solar_potential),
        "solar_has_road_filter_effect": bool(solar_has_road_filter_effect),
        "solar_road_establishment_class_changes": int(solar_road_establishment_class_changes),
        "solar_road_area_reduction_km2": float(solar_road_area_reduction_km2),
        "solar_has_protected_filter_effect": bool(solar_has_protected_filter_effect),
        "solar_has_culture_filter_effect": bool(solar_has_culture_filter_effect),
        "solar_has_reindeer_filter_effect": bool(solar_has_reindeer_filter_effect),
        "solar_protected_area_reduction_km2": float(solar_protected_area_reduction_km2),
        "solar_culture_area_reduction_km2": float(solar_culture_area_reduction_km2),
        "solar_has_electrical_feasibility_effect": bool(solar_has_electrical_feasibility_effect),
        "solar_road_source_features": int(solar_road_source_features),
        "solar_road_buffer_features": int(solar_road_buffer_features),
        "solar_protected_source_features": int(solar_protected_source_features),
        "solar_protected_buffer_features": int(solar_protected_buffer_features),
        "solar_culture_source_features": int(solar_culture_source_features),
        "solar_culture_buffer_features": int(solar_culture_buffer_features),
        "solar_reindeer_source_features": int(solar_reindeer_source_features),
        "solar_reindeer_buffer_features": int(solar_reindeer_buffer_features),
        "solar_electrical_source_features": int(solar_electrical_source_features),
        "solar_electrical_buffer_features": int(solar_electrical_buffer_features),
        "solar_electrical_area_m2": solar_electrical_area_m2,
        "solar_without_electrical_area_m2": solar_without_electrical_area_m2,
        "wind_road_buffer_m": WIND_ROAD_BUFFER_M,
        "solar_road_buffer_m": SOLAR_ROAD_BUFFER_M,
        "road_ui_contract": road_ui_contract,
        "wind_proposal_rows": len(wind_proposal),
        "solar_proposal_rows": len(solar_proposal),
        "layer_names": [str(layer.get("name")) for layer in all_layers],
        "establishment_layer": establishment_layer,
        "establishment_features": len(((establishment_layer or {}).get("feature_collection") or {}).get("features") or []),
        "wind_preview_layers": [str(layer.get("name")) for layer in wind_preview_layers],
        "display_geometry_path": display_geometry_path,
    }


def _check_region_contract(report: ParityReport, result: dict[str, Any], reference: dict[str, Any] | None = None) -> None:
    region_id = str(result["region_id"])
    report.check(
        result["wind_potential_rows"] > 0,
        f"{region_id}: active wind layer produces wind potential rows.",
        f"{region_id}: active wind layer produced no wind potential rows.",
    )
    report.check(
        bool(result.get("wind_has_transport_rule", False)),
        f"{region_id}: wind road/transport layer participates in the potential calculation.",
        f"{region_id}: wind road/transport layer did not produce a transport distance rule.",
    )
    report.check(
        bool(result.get("wind_has_protected_rule", False)),
        f"{region_id}: wind protected-nature layer participates in the potential calculation.",
        f"{region_id}: wind protected-nature layer did not produce a protected rule.",
    )
    report.check(
        bool(result.get("wind_has_culture_rule", False)),
        f"{region_id}: wind culture layer participates in the potential calculation.",
        f"{region_id}: wind culture layer did not produce a culture rule.",
    )
    report.check(
        bool(result.get("wind_has_electrical_rule", False)),
        f"{region_id}: wind electrical-infrastructure layer participates as proximity feasibility.",
        f"{region_id}: wind electrical-infrastructure layer did not produce an electrical rule.",
    )
    report.check(
        result["solar_potential_rows"] > 0,
        f"{region_id}: active solar layer produces solar potential rows.",
        f"{region_id}: active solar layer produced no solar potential rows.",
    )
    report.check(
        bool(result.get("solar_has_road_filter_effect", False)),
        f"{region_id}: solar road filter removes or buffers candidate area.",
        f"{region_id}: solar road filter had no measurable area effect.",
    )
    report.check(
        float(result.get("solar_road_area_reduction_km2", 0.0) or 0.0) > 0.0,
        f"{region_id}: solar road filter reduces the right-panel candidate area.",
        f"{region_id}: solar road filter did not reduce candidate area shown in the right panel.",
    )
    report.check(
        int(result.get("solar_road_establishment_class_changes", 0) or 0) > 0,
        f"{region_id}: solar road filter changes the shared establishment area.",
        f"{region_id}: solar road filter did not change establishment classes.",
    )
    report.check(
        bool(result.get("solar_has_protected_filter_effect", False)),
        f"{region_id}: solar protected-nature filter removes or buffers candidate area.",
        f"{region_id}: solar protected-nature filter had no measurable area effect.",
    )
    report.check(
        float(result.get("solar_protected_area_reduction_km2", 0.0) or 0.0) > 0.0,
        f"{region_id}: solar protected-nature filter reduces the right-panel candidate area.",
        f"{region_id}: solar protected-nature filter did not reduce candidate area shown in the right panel.",
    )
    report.check(
        bool(result.get("solar_has_culture_filter_effect", False)),
        f"{region_id}: solar culture filter removes or buffers candidate area.",
        f"{region_id}: solar culture filter had no measurable area effect.",
    )
    report.check(
        float(result.get("solar_culture_area_reduction_km2", 0.0) or 0.0) > 0.0,
        f"{region_id}: solar culture filter reduces the right-panel candidate area.",
        f"{region_id}: solar culture filter did not reduce candidate area shown in the right panel.",
    )
    report.check(
        bool(result.get("solar_has_electrical_feasibility_effect", False)),
        f"{region_id}: solar electrical layer limits candidate area to near-grid locations.",
        (
            f"{region_id}: solar electrical near-grid rule had no measurable feasibility effect "
            f"(with={result.get('solar_electrical_area_m2')}, without={result.get('solar_without_electrical_area_m2')})."
        ),
    )
    report.check(
        int(result.get("solar_road_source_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the road source layer.",
        f"{region_id}: solar UI cannot render the road source layer.",
    )
    report.check(
        int(result.get("solar_road_buffer_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the road buffer layer.",
        f"{region_id}: solar UI cannot render the road buffer layer.",
    )
    report.check(
        int(result.get("solar_protected_source_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the protected-nature source layer.",
        f"{region_id}: solar UI cannot render the protected-nature source layer.",
    )
    report.check(
        int(result.get("solar_protected_buffer_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the protected-nature buffer layer.",
        f"{region_id}: solar UI cannot render the protected-nature buffer layer.",
    )
    report.check(
        int(result.get("solar_culture_source_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the culture source layer.",
        f"{region_id}: solar UI cannot render the culture source layer.",
    )
    report.check(
        int(result.get("solar_culture_buffer_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the culture buffer layer.",
        f"{region_id}: solar UI cannot render the culture buffer layer.",
    )
    report.check(
        int(result.get("solar_electrical_source_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the electrical source layer.",
        f"{region_id}: solar UI cannot render the electrical source layer.",
    )
    report.check(
        int(result.get("solar_electrical_buffer_features", 0) or 0) > 0,
        f"{region_id}: solar UI can render the near-grid feasibility layer.",
        f"{region_id}: solar UI cannot render the near-grid feasibility layer.",
    )
    road_ui = result.get("road_ui_contract") or {}
    report.check(
        int(road_ui.get("solar_source_count", 0) or 0) >= 1 and int(road_ui.get("wind_source_count", 0) or 0) >= 1,
        f"{region_id}: road UI exposes separate solar and wind source layers.",
        f"{region_id}: road UI lacks separate solar/wind source layers; road layers={road_ui.get('road_layer_names')}.",
    )
    report.check(
        int(road_ui.get("solar_buffer_count", 0) or 0) >= 1 and int(road_ui.get("wind_buffer_count", 0) or 0) >= 1,
        f"{region_id}: road UI exposes separate solar and wind buffer layers.",
        f"{region_id}: road UI lacks separate solar/wind buffer layers; road layers={road_ui.get('road_layer_names')}.",
    )
    report.check(
        int(road_ui.get("solar_source_features", 0) or 0) > 0 and int(road_ui.get("wind_source_features", 0) or 0) > 0,
        f"{region_id}: solar and wind road source layers both have renderable features.",
        f"{region_id}: one road source context has no features; road contract={road_ui}.",
    )
    report.check(
        int(road_ui.get("solar_buffer_features", 0) or 0) > 0 and int(road_ui.get("wind_buffer_features", 0) or 0) > 0,
        f"{region_id}: solar and wind road buffer layers both have renderable features.",
        f"{region_id}: one road buffer context has no features; road contract={road_ui}.",
    )
    report.check(
        bool(road_ui.get("road_layer_names_are_distinct")) and bool(road_ui.get("road_layer_ids_are_distinct")),
        f"{region_id}: solar/wind road layer names and ids stay distinct.",
        f"{region_id}: solar/wind road layers collapse or duplicate; road contract={road_ui}.",
    )
    report.check(
        float(result.get("wind_road_buffer_m", 0.0) or 0.0) != float(result.get("solar_road_buffer_m", 0.0) or 0.0),
        f"{region_id}: parity fixture uses different wind and solar road buffers.",
        f"{region_id}: parity fixture did not create different wind/solar road buffer settings.",
    )
    report.pass_(
        f"{region_id}: energy proposal path executed "
        f"(wind rows {result['wind_proposal_rows']}, solar rows {result['solar_proposal_rows']})."
    )
    report.check(
        any(name.startswith(app.COMBINED_ESTABLISHMENT_LAYER_LABEL) for name in result["layer_names"]),
        f"{region_id}: map layer list contains {app.COMBINED_ESTABLISHMENT_LAYER_LABEL}.",
        f"{region_id}: map layer list lacks {app.COMBINED_ESTABLISHMENT_LAYER_LABEL}; layers={result['layer_names']}.",
    )
    report.check(
        bool((result.get("establishment_layer") or {}).get("default_visible", False)),
        f"{region_id}: {app.COMBINED_ESTABLISHMENT_LAYER_LABEL} is visible by default.",
        f"{region_id}: {app.COMBINED_ESTABLISHMENT_LAYER_LABEL} is not visible by default.",
    )
    report.check(
        int(result.get("establishment_features", 0) or 0) > 0,
        f"{region_id}: establishment layer has renderable features.",
        f"{region_id}: establishment layer has no renderable features.",
    )
    if reference is not None:
        reference_has_establishment = any(name.startswith(app.COMBINED_ESTABLISHMENT_LAYER_LABEL) for name in reference["layer_names"])
        current_has_establishment = any(name.startswith(app.COMBINED_ESTABLISHMENT_LAYER_LABEL) for name in result["layer_names"])
        report.check(
            reference_has_establishment and current_has_establishment,
            f"{region_id}: matches Bornholm by producing the shared establishment layer.",
            f"{region_id}: does not match Bornholm shared establishment behavior.",
        )
        report.check(
            bool(reference.get("wind_has_transport_rule")) == bool(result.get("wind_has_transport_rule")),
            f"{region_id}: matches Bornholm wind-road participation.",
            f"{region_id}: wind-road participation differs from Bornholm.",
        )
        report.check(
            bool(reference.get("solar_has_road_filter_effect")) == bool(result.get("solar_has_road_filter_effect")),
            f"{region_id}: matches Bornholm solar-road filter behavior.",
            f"{region_id}: solar-road filter behavior differs from Bornholm.",
        )
        report.check(
            float(reference.get("solar_road_area_reduction_km2", 0.0) or 0.0) > 0.0
            and float(result.get("solar_road_area_reduction_km2", 0.0) or 0.0) > 0.0,
            f"{region_id}: matches Bornholm by reducing right-panel solar candidate area with roads.",
            f"{region_id}: solar-road candidate-area reduction differs from Bornholm.",
        )
        report.check(
            int(reference.get("solar_road_establishment_class_changes", 0) or 0) > 0
            and int(result.get("solar_road_establishment_class_changes", 0) or 0) > 0,
            f"{region_id}: matches Bornholm by letting solar roads change establishment classes.",
            (
                f"{region_id}: solar-road establishment behavior differs from Bornholm; "
                f"Bornholm changes={reference.get('solar_road_establishment_class_changes')}, "
                f"current changes={result.get('solar_road_establishment_class_changes')}."
            ),
        )
        report.check(
            bool(reference.get("wind_has_protected_rule")) == bool(result.get("wind_has_protected_rule")),
            f"{region_id}: matches Bornholm wind protected-nature participation.",
            f"{region_id}: wind protected-nature participation differs from Bornholm.",
        )
        report.check(
            bool(reference.get("wind_has_culture_rule")) == bool(result.get("wind_has_culture_rule")),
            f"{region_id}: matches Bornholm wind culture participation.",
            f"{region_id}: wind culture participation differs from Bornholm.",
        )
        report.check(
            bool(reference.get("wind_has_electrical_rule")) == bool(result.get("wind_has_electrical_rule")),
            f"{region_id}: matches Bornholm wind electrical proximity participation.",
            f"{region_id}: wind electrical proximity participation differs from Bornholm.",
        )
        report.check(
            bool(reference.get("solar_has_protected_filter_effect")) == bool(result.get("solar_has_protected_filter_effect")),
            f"{region_id}: matches Bornholm solar protected-nature filter behavior.",
            f"{region_id}: solar protected-nature filter behavior differs from Bornholm.",
        )
        report.check(
            float(reference.get("solar_protected_area_reduction_km2", 0.0) or 0.0) > 0.0
            and float(result.get("solar_protected_area_reduction_km2", 0.0) or 0.0) > 0.0,
            f"{region_id}: matches Bornholm by reducing right-panel solar candidate area with protected nature.",
            f"{region_id}: solar protected-nature candidate-area reduction differs from Bornholm.",
        )
        report.check(
            bool(reference.get("solar_has_culture_filter_effect")) == bool(result.get("solar_has_culture_filter_effect")),
            f"{region_id}: matches Bornholm solar culture filter behavior.",
            f"{region_id}: solar culture filter behavior differs from Bornholm.",
        )
        report.check(
            bool(reference.get("solar_has_electrical_feasibility_effect")) == bool(result.get("solar_has_electrical_feasibility_effect")),
            f"{region_id}: matches Bornholm solar near-grid feasibility behavior.",
            f"{region_id}: solar near-grid feasibility behavior differs from Bornholm.",
        )
        reference_road_ui = reference.get("road_ui_contract") or {}
        report.check(
            int(reference_road_ui.get("solar_source_count", 0) or 0) >= 1
            and int(reference_road_ui.get("wind_source_count", 0) or 0) >= 1
            and int(road_ui.get("solar_source_count", 0) or 0) >= 1
            and int(road_ui.get("wind_source_count", 0) or 0) >= 1,
            f"{region_id}: matches Bornholm by keeping solar and wind road source contexts visible.",
            f"{region_id}: differs from Bornholm road source context behavior; Bornholm={reference_road_ui}, current={road_ui}.",
        )
        report.check(
            int(reference_road_ui.get("solar_buffer_count", 0) or 0) >= 1
            and int(reference_road_ui.get("wind_buffer_count", 0) or 0) >= 1
            and int(road_ui.get("solar_buffer_count", 0) or 0) >= 1
            and int(road_ui.get("wind_buffer_count", 0) or 0) >= 1,
            f"{region_id}: matches Bornholm by keeping separate solar and wind road buffers.",
            f"{region_id}: differs from Bornholm road buffer context behavior; Bornholm={reference_road_ui}, current={road_ui}.",
        )
    if region_id == "trondelag":
        report.check(
            bool(result.get("wind_has_reindeer_rule", False)),
            "trondelag: wind reindeer-husbandry layer participates in the potential calculation.",
            "trondelag: wind reindeer-husbandry layer did not produce a reindeer rule.",
        )
        report.check(
            bool(result.get("solar_has_reindeer_filter_effect", False)),
            "trondelag: solar reindeer-husbandry filter removes or buffers candidate area.",
            "trondelag: solar reindeer-husbandry filter had no measurable area effect.",
        )
        report.check(
            int(result.get("solar_reindeer_source_features", 0) or 0) > 0,
            "trondelag: solar UI can render the reindeer-husbandry source layer.",
            "trondelag: solar UI cannot render the reindeer-husbandry source layer.",
        )
        report.check(
            int(result.get("solar_reindeer_buffer_features", 0) or 0) > 0,
            "trondelag: solar UI can render the reindeer-husbandry buffer layer.",
            "trondelag: solar UI cannot render the reindeer-husbandry buffer layer.",
        )
        report.check(
            result["display_resolution"] == 7 and result["analysis_resolution"] == 7,
            "trondelag: establishment parity runs in R7 light mode.",
            f"trondelag: expected display/analysis R7, got display R{result['display_resolution']} analysis R{result['analysis_resolution']}.",
        )
        report.check(
            app.WIND_POTENTIAL_HEX_LABEL not in result["wind_preview_layers"],
            "trondelag: separate wind hex preview is hidden when establishment layer is available.",
            f"trondelag: separate wind hex preview is still visible: {result['wind_preview_layers']}.",
        )


def main() -> int:
    report = ParityReport()
    if not _require_dependencies(report):
        return report.emit()

    try:
        bornholm = _region_workspace_contract("bornholm")
        report.pass_("Bornholm reference flow was built first.")
        _check_region_contract(report, bornholm)
    except Exception as exc:
        report.fail(f"Bornholm reference flow failed: {exc}")
        return report.emit()

    try:
        trondelag = _region_workspace_contract("trondelag")
        report.pass_("Trondelag flow was built after Bornholm reference.")
        _check_region_contract(report, trondelag, reference=bornholm)
    except Exception as exc:
        report.fail(f"Trondelag parity flow failed: {exc}")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
