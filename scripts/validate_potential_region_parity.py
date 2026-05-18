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


def _region_workspace_contract(region_id: str) -> dict[str, Any]:
    st.session_state.clear()
    st.session_state[app.REGION_SELECT_KEY] = region_id
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
    wind_selection = app.normalize_group_layer_map(WIND_TEST_SELECTION)
    wind_params = app._default_wind_params()
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

    solar_population_buffer_m = 250.0
    solar_large = app._solar_large_scale_frame(
        region,
        landscape_manifest,
        analysis_resolution,
        solar_population_buffer_m,
        None,
        [],
        False,
        [],
    )
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
    all_layers = [*wind_preview_layers, *establishment_layers]
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
        "solar_potential_rows": len(solar_potential),
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
        result["solar_potential_rows"] > 0,
        f"{region_id}: active solar layer produces solar potential rows.",
        f"{region_id}: active solar layer produced no solar potential rows.",
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
    if region_id == "trondelag":
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
