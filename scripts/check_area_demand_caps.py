from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.potential_model.energy_modeling import (  # noqa: E402
    build_times_summary,
    calculate_area_demand,
    load_area_demand_bundle,
    load_energy_model_inputs,
    planning_scenarios,
    select_planning_mix,
)


EXPECTED = {
    "wind": {"low": 8.35, "mid": 37.04, "high": 100.00},
    "solar": {"low": 8.62, "mid": 14.18, "high": 28.57},
}


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _technology_to_times_map(scenario_manifest: dict) -> dict[str, str]:
    area_cfg = (((scenario_manifest or {}).get("energy_model") or {}).get("area_demand") or {})
    mapping = area_cfg.get("times_technology_map") or {}
    return {
        str((rule or {}).get("energy_key")): str(times_tech)
        for times_tech, rule in mapping.items()
        if (rule or {}).get("energy_key")
    }


def _first_factor(area_frame, energy_key: str) -> float:
    values = area_frame.loc[area_frame["energy_key"].astype(str) == energy_key, "km2_per_twh"].dropna()
    if values.empty:
        raise AssertionError(f"Missing km2_per_twh for {energy_key}")
    return float(values.iloc[0])


def _assert_close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(round(float(actual), 2), expected, abs_tol=0.01):
        raise AssertionError(f"{label}: expected {expected:.2f}, got {actual:.6f}")


def check_manifest(path: Path) -> None:
    manifest = _load_manifest(path)
    area_bundle = load_area_demand_bundle(manifest, ROOT)
    scenario_table = area_bundle.scenario_table
    for energy_key, expected_values in EXPECTED.items():
        row = scenario_table[scenario_table["energy_key"].astype(str) == energy_key]
        if row.empty:
            raise AssertionError(f"{path.name}: missing scenario row for {energy_key}")
        row = row.iloc[0]
        _assert_close(float(row["low_km2_per_twh"]), expected_values["low"], f"{path.name} {energy_key} low")
        _assert_close(float(row["mid_km2_per_twh"]), expected_values["mid"], f"{path.name} {energy_key} mid")
        _assert_close(float(row["high_km2_per_twh"]), expected_values["high"], f"{path.name} {energy_key} high")
    wind_row = scenario_table[scenario_table["energy_key"].astype(str) == "wind"].iloc[0]
    if float(wind_row["raw_high_km2_per_twh"]) <= float(wind_row["high_km2_per_twh"]):
        raise AssertionError(f"{path.name}: wind high does not show raw value above capped value")
    if "high_km2_per_twh" not in str(wind_row.get("cap_note", "")):
        raise AssertionError(f"{path.name}: wind high cap note is missing")

    inputs = load_energy_model_inputs(manifest, ROOT)
    _, mix = build_times_summary(inputs.times_rows)
    planning_options = planning_scenarios(manifest)
    high_planning = next((item for item in planning_options if str(item.get("id")) == "high"), planning_options[-1])
    selected_mix = select_planning_mix(mix, high_planning)
    technology_to_times = _technology_to_times_map(manifest)
    mid_area = calculate_area_demand(selected_mix, area_bundle, "mid", technology_to_times)
    high_area = calculate_area_demand(selected_mix, area_bundle, "high", technology_to_times)
    _assert_close(_first_factor(mid_area, "wind"), EXPECTED["wind"]["mid"], f"{path.name} high energy + mid intensity")
    _assert_close(_first_factor(high_area, "wind"), EXPECTED["wind"]["high"], f"{path.name} high energy + high intensity")
    if math.isclose(
        float(mid_area.loc[mid_area["energy_key"].astype(str) == "wind", "area_need_km2"].sum()),
        float(high_area.loc[high_area["energy_key"].astype(str) == "wind", "area_need_km2"].sum()),
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise AssertionError(f"{path.name}: wind area need did not change when land intensity changed")
    print(f"OK {path.name}")


def main() -> int:
    manifests = [
        ROOT / "apps/potential_model/manifests/scenarios/bornholm_scenarios_placeholder.json",
        ROOT / "apps/potential_model/manifests/scenarios/trondelag_scenarios_placeholder.json",
    ]
    for path in manifests:
        check_manifest(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
