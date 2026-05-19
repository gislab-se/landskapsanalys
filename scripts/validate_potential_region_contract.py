from __future__ import annotations

import csv
import contextlib
from io import StringIO
import json
import logging
import math
import os
import re
import sys
import importlib.util
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("STREAMLIT_LOG_LEVEL", "error")
logging.getLogger("streamlit").setLevel(logging.ERROR)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.potential_model.manifests import (  # noqa: E402
    load_linked_manifest,
    load_region,
    resolve_repo_path,
)
from apps.potential_model.region_status import load_region_context  # noqa: E402


EXPECTED_TRONDELAG_RESOLUTIONS = [7, 6, 5]
EXPECTED_TRONDELAG_COUNTS = {7: 13735, 6: 2163, 5: 365}
EXPECTED_SYNTHETIC_ACCEPTANCE_RESOLUTIONS = {"bornholm": 10, "trondelag": 7}
EXPECTED_SYNTHETIC_ACCEPTANCE_ROLLUP_RESOLUTIONS = {"bornholm": [8], "trondelag": [6, 5]}
SYNTHETIC_ACCEPTANCE_COLUMNS = ["acceptance_low", "acceptance_medium", "acceptance_high"]
REQUIRED_LANDSCAPE_FIELDS = ["hex_id", "class_km", "F1", "F2", "F3", "F4", "F5"]
LANDSCAPE_DISPLAY_FIELDS = [
    "landscape_type",
    "landscape_type_id",
    "landscape_type_name",
    "v10_type_id",
    "v10_type_name",
]


class ContractReport:
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
        print("Potential App region contract")
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


def _as_int_list(values: Any) -> list[int]:
    result: list[int] = []
    for value in values or []:
        try:
            result.append(int(value))
        except Exception:
            continue
    return result


def _path_from_manifest(manifest: dict[str, Any], key: str) -> Path | None:
    value = manifest.get(key)
    return resolve_repo_path(str(value)) if value else None


@lru_cache(maxsize=16)
def _load_geojson(path_str: str) -> dict[str, Any]:
    with Path(path_str).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _geojson_features(path: Path) -> list[dict[str, Any]]:
    data = _load_geojson(str(path))
    features = data.get("features")
    return features if isinstance(features, list) else []


def _feature_count(path: Path) -> int:
    return len(_geojson_features(path))


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _decimal_places(text: str) -> int:
    value = str(text).strip()
    if "." not in value:
        return 0
    return len(value.split(".", 1)[1].rstrip("0"))


def _properties(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(feature.get("properties") or {}) for feature in features]


def _is_numeric(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except Exception:
        return False
    return math.isfinite(number)


def _path_looks_pdf_or_raw(path_value: str | None, path: Path | None) -> bool:
    text = f"{path_value or ''} {str(path) if path else ''}".lower()
    return any(marker in text for marker in ["pdf", ".tif", ".tiff", ".gpkg"])


def check_bornholm_runtime(report: ContractReport) -> None:
    bornholm = load_region("bornholm")
    context = load_region_context(bornholm)
    if context.get("runtime_ready"):
        report.pass_("Bornholm remains runtime_ready.")
        return
    blockers = context.get("missing_data") or []
    report.fail(f"Bornholm is no longer runtime_ready: {json.dumps(blockers, ensure_ascii=False)}")


def check_default_region(report: ContractReport) -> None:
    source_path = ROOT / "potential_app.py"
    source = source_path.read_text(encoding="utf-8")
    match = re.search(r"DEFAULT_REGION_ID\s*=\s*['\"]([^'\"]+)['\"]", source)
    if not match:
        report.fail("potential_app.py has no DEFAULT_REGION_ID constant.")
        return
    default_region = match.group(1)
    report.check(
        default_region == "trondelag",
        'DEFAULT_REGION_ID is "trondelag".',
        f'DEFAULT_REGION_ID is "{default_region}", expected "trondelag".',
    )
    report.check(
        "DEFAULT_REGION_ID if DEFAULT_REGION_ID in options" in source,
        "_region_options() uses DEFAULT_REGION_ID before fallback regions.",
        "_region_options() does not appear to prefer DEFAULT_REGION_ID before Bornholm fallback.",
    )


def check_h3_session_state_sanitizer(report: ContractReport, region: dict[str, Any]) -> None:
    import streamlit as st  # noqa: WPS433
    import potential_app as app  # noqa: WPS433

    state_key = "combined_h3_resolution"
    original = st.session_state.get(state_key)
    try:
        st.session_state[state_key] = "R10"
        resolved = app._session_h3_resolution(region, state_key, 7)
        report.check(
            resolved == 7 and st.session_state.get(state_key) == 7,
            'Stale H3 state "R10" is sanitized to Trondelag R7.',
            f'Stale H3 state "R10" resolved to {resolved!r} with session value {st.session_state.get(state_key)!r}, expected 7.',
        )
        st.session_state[state_key] = "not-a-resolution"
        resolved = app._session_h3_resolution(region, state_key, 7)
        report.check(
            resolved == 7 and st.session_state.get(state_key) == 7,
            "Malformed H3 session state falls back to Trondelag R7.",
            f"Malformed H3 session state resolved to {resolved!r} with session value {st.session_state.get(state_key)!r}, expected 7.",
        )
    finally:
        if original is None:
            st.session_state.pop(state_key, None)
        else:
            st.session_state[state_key] = original


def check_region_switch_resets_to_light_default(report: ContractReport) -> None:
    import streamlit as st  # noqa: WPS433
    import potential_app as app  # noqa: WPS433

    bornholm = load_region("bornholm")
    trondelag = load_region("trondelag")
    options = {"bornholm": bornholm, "trondelag": trondelag}
    original_state = dict(st.session_state)
    try:
        st.session_state.clear()
        st.session_state[app.APP_LANGUAGE_KEY] = "sv"
        st.session_state[app.REGION_SELECT_KEY] = "bornholm"
        app._reset_session_for_region(bornholm)
        st.session_state["combined_h3_resolution"] = 10
        st.session_state["combined_h3_display_mode"] = "zoom_family"
        st.session_state["show_landscape_v10"] = True
        st.session_state["show_social_acceptance"] = True
        st.session_state[app.SOLAR_APPLIED_CONFIG_KEY] = {"large_scale_active": False}
        st.session_state["potential_scenario_bornholm"] = "high"

        st.session_state[app.REGION_SELECT_KEY] = "trondelag"
        app._sync_region_selection_state(options)
        report.check(
            st.session_state.get(app.ACTIVE_REGION_KEY) == "trondelag"
            and st.session_state.get("combined_h3_resolution") == 7
            and st.session_state.get("combined_h3_display_mode") == "selected"
            and st.session_state.get("show_landscape_v10") is False
            and st.session_state.get("show_social_acceptance") is False
            and st.session_state.get("show_user_solar") is True
            and "potential_scenario_bornholm" not in st.session_state,
            "Region switch to Trondelag resets to the light default state.",
            "Region switch to Trondelag did not reset stale Bornholm controls to light defaults.",
        )

        st.session_state["combined_h3_resolution"] = 7
        st.session_state["show_landscape_factor"] = True
        st.session_state["show_social_acceptance"] = True
        st.session_state["potential_scenario_trondelag"] = "low"
        st.session_state[app.REGION_SELECT_KEY] = "bornholm"
        app._sync_region_selection_state(options)
        report.check(
            st.session_state.get(app.ACTIVE_REGION_KEY) == "bornholm"
            and st.session_state.get("combined_h3_resolution") == 8
            and st.session_state.get("combined_h3_display_mode") == "selected"
            and st.session_state.get("show_landscape_factor") is False
            and st.session_state.get("show_social_acceptance") is False
            and "potential_scenario_trondelag" not in st.session_state,
            "Switching back to Bornholm also opens a fresh light default state.",
            "Switching back to Bornholm kept stale Trondelag controls instead of light defaults.",
        )
    finally:
        st.session_state.clear()
        for key, value in original_state.items():
            st.session_state[key] = value


def check_synthetic_social_acceptance(report: ContractReport, region_id: str) -> None:
    from apps.potential_model.social_acceptance import acceptance_feature_collection  # noqa: WPS433

    region = load_region(region_id)
    manifest = load_linked_manifest(region, "social_acceptance_manifest")
    expected_resolution = EXPECTED_SYNTHETIC_ACCEPTANCE_RESOLUTIONS[region_id]
    if not isinstance(manifest, dict):
        report.fail(f"{region_id}: social_acceptance_manifest could not be loaded.")
        return

    source_path = _path_from_manifest(manifest, "source_hex_geojson")
    csv_path = _path_from_manifest(manifest, "acceptance_csv")
    report.check(
        bool(manifest.get("synthetic")) and str(manifest.get("status")) == "synthetic_test_data",
        f"{region_id}: social acceptance manifest is marked synthetic test data.",
        f"{region_id}: social acceptance manifest is not clearly marked synthetic test data.",
    )
    report.check(
        int(manifest.get("hex_resolution") or -1) == expected_resolution,
        f"{region_id}: synthetic acceptance uses H3 R{expected_resolution}.",
        f"{region_id}: synthetic acceptance resolution is {manifest.get('hex_resolution')!r}, expected R{expected_resolution}.",
    )
    if source_path is None or not source_path.exists():
        report.fail(f"{region_id}: synthetic acceptance source hex GeoJSON is missing: {source_path}")
        return
    if csv_path is None or not csv_path.exists():
        report.fail(f"{region_id}: synthetic acceptance CSV is missing: {csv_path}")
        return

    rows = _csv_rows(csv_path)
    source_count = _feature_count(source_path)
    report.check(
        len(rows) == source_count,
        f"{region_id}: synthetic acceptance has one row for every source hex ({source_count}).",
        f"{region_id}: synthetic acceptance has {len(rows)} rows, expected {source_count} source hex rows.",
    )

    scenario_ids = [str(scenario.get("id")) for scenario in manifest.get("scenarios") or [] if isinstance(scenario, dict)]
    report.check(
        scenario_ids == ["low", "medium", "high"],
        f"{region_id}: synthetic acceptance exposes low/medium/high scenarios.",
        f"{region_id}: synthetic acceptance scenarios are {scenario_ids}, expected low/medium/high.",
    )

    bad_values: list[str] = []
    bad_decimals: list[str] = []
    bad_order: list[str] = []
    bad_status = 0
    bad_resolution = 0
    for row in rows:
        if str(row.get("data_status")) != "synthetic_test_data_not_research":
            bad_status += 1
        if int(row.get("h3_resolution") or -1) != expected_resolution:
            bad_resolution += 1
        parsed: dict[str, float] = {}
        for column in SYNTHETIC_ACCEPTANCE_COLUMNS:
            text = str(row.get(column, "")).strip()
            try:
                value = float(text)
            except Exception:
                bad_values.append(f"{row.get('hex_id')}:{column}={text!r}")
                continue
            parsed[column] = value
            if not 0.0 <= value <= 1.0:
                bad_values.append(f"{row.get('hex_id')}:{column}={text}")
            if _decimal_places(text) > 3:
                bad_decimals.append(f"{row.get('hex_id')}:{column}={text}")
        if len(parsed) == 3 and not (
            parsed["acceptance_low"] <= parsed["acceptance_medium"] <= parsed["acceptance_high"]
        ):
            bad_order.append(str(row.get("hex_id")))

    report.check(
        not bad_values,
        f"{region_id}: all synthetic acceptance values are in [0, 1].",
        f"{region_id}: invalid synthetic acceptance values: {bad_values[:5]}",
    )
    report.check(
        not bad_decimals,
        f"{region_id}: all synthetic acceptance values use max three decimals.",
        f"{region_id}: synthetic acceptance values exceed three decimals: {bad_decimals[:5]}",
    )
    report.check(
        not bad_order,
        f"{region_id}: low <= medium <= high for every synthetic acceptance row.",
        f"{region_id}: scenario ordering failed for hex rows: {bad_order[:5]}",
    )
    report.check(
        bad_status == 0 and bad_resolution == 0,
        f"{region_id}: every synthetic acceptance row is labelled test data at the expected resolution.",
        f"{region_id}: {bad_status} rows have bad data_status and {bad_resolution} rows have bad resolution.",
    )

    for rollup_resolution in EXPECTED_SYNTHETIC_ACCEPTANCE_ROLLUP_RESOLUTIONS[region_id]:
        rollup_geometry_value = (region.get("h3_display_geometries") or {}).get(str(rollup_resolution))
        rollup_geometry_path = resolve_repo_path(str(rollup_geometry_value)) if rollup_geometry_value else None
        if rollup_geometry_path is None or not rollup_geometry_path.exists():
            report.fail(f"{region_id}: rollup geometry R{rollup_resolution} is missing: {rollup_geometry_value!r}")
            return
        rollup_collection = acceptance_feature_collection(
            manifest,
            "medium",
            rollup_resolution,
            str(rollup_geometry_path),
        )
        rollup_features = rollup_collection.get("features") if isinstance(rollup_collection, dict) else []
        rollup_props = [dict(feature.get("properties") or {}) for feature in rollup_features or []]
        bad_rollup_values = [
            str(props.get("hex_id"))
            for props in rollup_props
            if not 0.0 <= float(props.get("acceptance_value", -1.0)) <= 1.0
        ]
        report.check(
            0 < len(rollup_props) < source_count,
            f"{region_id}: synthetic acceptance rolls up from R{expected_resolution} to R{rollup_resolution}.",
            f"{region_id}: synthetic acceptance rollup produced {len(rollup_props)} features from {source_count} source rows.",
        )
        report.check(
            all(int(props.get("target_h3_resolution") or -1) == rollup_resolution for props in rollup_props)
            and any(int(props.get("source_hex_count") or 0) > 1 for props in rollup_props)
            and not bad_rollup_values,
            f"{region_id}: rollup features keep target resolution, child counts and values in [0, 1] for R{rollup_resolution}.",
            f"{region_id}: invalid rollup features for R{rollup_resolution}: {bad_rollup_values[:5]}",
        )


def check_map_auto_resolution(report: ContractReport) -> None:
    source = (ROOT / "apps/potential_model/map_rendering.py").read_text(encoding="utf-8")
    report.check(
        "desiredResolution = 5;" in source and "scaleMeters >= 100000" in source,
        "Zoom-adaptive H3 display can select R5 for coarse Trondelag map scale.",
        "Zoom-adaptive H3 display has no R5 scale threshold, so Trondelag would only use two auto-rollup levels.",
    )


def check_trondelag_region(report: ContractReport, region: dict[str, Any]) -> None:
    report.check(
        str(region.get("native_crs")) == "EPSG:25832",
        "Trondelag native_crs is EPSG:25832.",
        f"Trondelag native_crs is {region.get('native_crs')!r}, expected EPSG:25832.",
    )
    available = _as_int_list(region.get("available_h3_resolutions"))
    report.check(
        available == EXPECTED_TRONDELAG_RESOLUTIONS,
        "Trondelag exposes exactly R7/R6/R5.",
        f"Trondelag available_h3_resolutions is {available}, expected {EXPECTED_TRONDELAG_RESOLUTIONS}.",
    )
    report.check(
        8 not in available and 9 not in available,
        "Trondelag does not expose R8/R9.",
        f"Trondelag exposes forbidden app resolutions: {[value for value in available if value in {8, 9}]}.",
    )
    report.check(
        int(region.get("default_h3_resolution") or -1) == 7,
        "Trondelag default_h3_resolution is R7.",
        f"Trondelag default_h3_resolution is {region.get('default_h3_resolution')!r}, expected 7.",
    )
    report.check(
        int(region.get("default_display_h3_resolution") or -1) == 7,
        "Trondelag default_display_h3_resolution is R7.",
        f"Trondelag default_display_h3_resolution is {region.get('default_display_h3_resolution')!r}, expected 7.",
    )

    counts = region.get("h3_display_geometry_counts") or {}
    geometries = region.get("h3_display_geometries") or {}
    for resolution, expected_count in EXPECTED_TRONDELAG_COUNTS.items():
        count_value = counts.get(str(resolution))
        report.check(
            int(count_value or -1) == expected_count,
            f"Manifest count for Trondelag R{resolution} is {expected_count}.",
            f"Manifest count for Trondelag R{resolution} is {count_value!r}, expected {expected_count}.",
        )
        path_value = geometries.get(str(resolution))
        path = resolve_repo_path(str(path_value)) if path_value else None
        report.check(
            bool(path and path.exists()),
            f"Trondelag R{resolution} display geometry exists: {path}.",
            f"Trondelag R{resolution} display geometry is missing: {path_value!r} -> {path}.",
        )
        if path and path.exists():
            actual_count = _feature_count(path)
            report.check(
                actual_count == expected_count,
                f"Trondelag R{resolution} display geometry has {actual_count} features.",
                f"Trondelag R{resolution} display geometry has {actual_count} features, expected {expected_count}: {path}.",
            )


def check_landscape_manifest(report: ContractReport, manifest: dict[str, Any] | None) -> None:
    if not isinstance(manifest, dict):
        report.fail("Trondelag landscape manifest could not be loaded.")
        return

    report.check(
        _as_int_list(manifest.get("available_h3_resolutions")) == EXPECTED_TRONDELAG_RESOLUTIONS,
        "Trondelag landscape manifest exposes R7/R6/R5.",
        f"Trondelag landscape manifest exposes {_as_int_list(manifest.get('available_h3_resolutions'))}, expected {EXPECTED_TRONDELAG_RESOLUTIONS}.",
    )
    report.check(
        int(manifest.get("default_h3_resolution") or -1) == 7
        and int(manifest.get("source_h3_resolution") or -1) == 7,
        "Trondelag landscape source/default H3 resolution is R7.",
        f"Trondelag landscape source/default H3 is source={manifest.get('source_h3_resolution')!r}, default={manifest.get('default_h3_resolution')!r}; expected 7.",
    )
    report.check(
        manifest.get("pdf_landscape_geojson") in {None, ""},
        "Trondelag PDF landscape path is not active.",
        f"Trondelag pdf_landscape_geojson is active: {manifest.get('pdf_landscape_geojson')!r}.",
    )

    landscape_path = _path_from_manifest(manifest, "landscape_geojson")
    factor_path = _path_from_manifest(manifest, "factor_scores")
    for key, path in [("landscape_geojson", landscape_path), ("factor_scores", factor_path)]:
        value = manifest.get(key)
        report.check(
            bool(path and path.exists()),
            f"{key} exists: {path}.",
            f"{key} is missing or unresolved: {value!r} -> {path}.",
        )
        report.check(
            not _path_looks_pdf_or_raw(str(value) if value else None, path),
            f"{key} is not a PDF/raw GIS path.",
            f"{key} points to a PDF/raw GIS path instead of app bundle data: {value!r}.",
        )

    if not landscape_path or not landscape_path.exists():
        return
    features = _geojson_features(landscape_path)
    rows = _properties(features)
    if not rows:
        report.fail(f"Trondelag landscape_geojson contains no features: {landscape_path}.")
        return
    field_names = set().union(*(row.keys() for row in rows[: min(len(rows), 100)]))
    missing_fields = [field for field in REQUIRED_LANDSCAPE_FIELDS if field not in field_names]
    report.check(
        not missing_fields,
        "Trondelag landscape data contains hex_id, class_km and F1-F5.",
        f"Trondelag landscape data is missing required fields: {missing_fields}.",
    )
    report.check(
        any(field in field_names for field in LANDSCAPE_DISPLAY_FIELDS),
        "Trondelag landscape data contains a landscape type display field.",
        f"Trondelag landscape data lacks a landscape type display field; checked {LANDSCAPE_DISPLAY_FIELDS}.",
    )

    for factor in ["F1", "F2", "F3", "F4", "F5"]:
        bad_values = [
            row.get(factor)
            for row in rows
            if factor in row and row.get(factor) is not None and not _is_numeric(row.get(factor))
        ]
        report.check(
            not bad_values,
            f"{factor} values are numeric.",
            f"{factor} contains non-numeric values; first examples: {bad_values[:5]}.",
        )

    if factor_path and factor_path.exists() and factor_path != landscape_path:
        factor_features = _geojson_features(factor_path) if factor_path.suffix.lower() in {".geojson", ".json"} else []
        if factor_features:
            factor_rows = _properties(factor_features)
            factor_fields = set().union(*(row.keys() for row in factor_rows[: min(len(factor_rows), 100)]))
            missing_factor_fields = [field for field in ["hex_id", "F1", "F2", "F3", "F4", "F5"] if field not in factor_fields]
            report.check(
                not missing_factor_fields,
                "Separate factor_scores file contains hex_id and F1-F5.",
                f"Separate factor_scores file is missing fields: {missing_factor_fields}.",
            )


def check_scenario_placeholder(report: ContractReport, scenario: dict[str, Any] | None) -> None:
    if not isinstance(scenario, dict):
        report.fail("Trondelag scenario manifest could not be loaded.")
        return
    report.check(
        scenario.get("status") == "placeholder",
        "Trondelag scenario manifest is explicitly marked placeholder.",
        f"Trondelag scenario status is {scenario.get('status')!r}, expected placeholder.",
    )
    text = json.dumps(scenario, ensure_ascii=False).lower()
    report.check(
        "bornholm" in text and "placeholder" in text,
        "Trondelag scenario manifest documents the Bornholm placeholder.",
        "Trondelag scenario manifest does not clearly document the Bornholm placeholder.",
    )
    report.check(
        "eml" in text or "norwegian" in text or "norsk" in text,
        "Trondelag scenario manifest names the future regional data source handoff.",
        "Trondelag scenario manifest does not mention EML/Norwegian replacement data.",
    )
    energy_model = scenario.get("energy_model") or {}
    duckdb_path = resolve_repo_path(((energy_model.get("duckdb") or {}).get("path")))
    area_demand_path = resolve_repo_path(((energy_model.get("area_demand") or {}).get("path")))
    report.check(
        bool(duckdb_path and duckdb_path.exists()),
        f"Trondelag placeholder DuckDB exists: {duckdb_path}.",
        f"Trondelag placeholder DuckDB is missing: {duckdb_path}.",
    )
    report.check(
        bool(area_demand_path and area_demand_path.exists()),
        f"Trondelag placeholder AreaDemand exists: {area_demand_path}.",
        f"Trondelag placeholder AreaDemand is missing: {area_demand_path}.",
    )
    report.check(
        importlib.util.find_spec("duckdb") is not None,
        "Python dependency duckdb is installed for energy-model runtime.",
        "Python dependency duckdb is missing; energy-model UI cannot create the proposed establishment area.",
    )
    report.check(
        importlib.util.find_spec("openpyxl") is not None,
        "Python dependency openpyxl is installed for AreaDemand runtime.",
        "Python dependency openpyxl is missing; AreaDemand.xlsx cannot be read by the energy-model UI.",
    )


def check_trondelag_runtime(report: ContractReport, region: dict[str, Any]) -> None:
    context = load_region_context(region)
    if context.get("runtime_ready"):
        report.pass_('load_region_context("trondelag") returns runtime_ready=True.')
        return
    blockers = context.get("missing_data") or []
    report.fail(f'load_region_context("trondelag") is not runtime_ready: {json.dumps(blockers, ensure_ascii=False)}')


def main() -> int:
    report = ContractReport()
    with contextlib.redirect_stderr(StringIO()):
        check_bornholm_runtime(report)
        check_default_region(report)

        trondelag = load_region("trondelag")
        landscape = load_linked_manifest(trondelag, "landscape_manifest")
        scenario = load_linked_manifest(trondelag, "scenario_manifest")

        check_h3_session_state_sanitizer(report, trondelag)
        check_region_switch_resets_to_light_default(report)
        check_trondelag_region(report, trondelag)
        check_map_auto_resolution(report)
        check_landscape_manifest(report, landscape)
        check_scenario_placeholder(report, scenario)
        check_synthetic_social_acceptance(report, "bornholm")
        check_synthetic_social_acceptance(report, "trondelag")
        check_trondelag_runtime(report, trondelag)
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
