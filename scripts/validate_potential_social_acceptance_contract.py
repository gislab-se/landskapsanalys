from __future__ import annotations

import csv
import json
import py_compile
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from potential_model.manifests import load_linked_manifest, load_region, resolve_repo_path  # noqa: E402
from potential_model.social_acceptance import acceptance_feature_collection, acceptance_scenarios  # noqa: E402


ACCEPTANCE_COLUMNS = ("acceptance_low", "acceptance_medium", "acceptance_high")
EXPECTED_DATA_STATUS = "synthetic_test_data_not_research"
EXPECTED_SOURCE_RESOLUTION = 10
ROLLUP_RESOLUTIONS = (10, 9, 8, 7, 6)


@dataclass
class ContractReport:
    passes: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def check(self, condition: bool, success: str, failure: str) -> None:
        if condition:
            self.passes.append(success)
        else:
            self.failures.append(failure)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def emit(self) -> int:
        for message in self.passes:
            print(f"PASS {message}")
        for message in self.failures:
            print(f"FAIL {message}")
        return 1 if self.failures else 0


def _repo_path(value: str | None) -> Path | None:
    path = resolve_repo_path(value)
    return path if path is not None else None


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_source_hex_ids(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        str((feature.get("properties") or {}).get("hex_id") or (feature.get("properties") or {}).get("h3_address"))
        for feature in payload.get("features", [])
        if (feature.get("properties") or {}).get("hex_id") or (feature.get("properties") or {}).get("h3_address")
    }


def _decimal_places(text: str) -> int:
    clean = str(text).strip()
    if "." not in clean:
        return 0
    return len(clean.split(".", 1)[1])


def _check_manifest(report: ContractReport, manifest: dict[str, Any]) -> None:
    scenarios = acceptance_scenarios(manifest)
    labels = {scenario["id"]: scenario["label"] for scenario in scenarios}
    report.check(
        labels == {"low": "Låg acceptans", "medium": "Mellanacceptans", "high": "Hög acceptans"},
        "manifest labels use the expected Swedish acceptance scenario names.",
        f"manifest labels are {labels!r}, expected Låg/Mellan/Hög acceptans.",
    )
    report.check(
        bool(manifest.get("synthetic"))
        and str(manifest.get("status")) == "synthetic_test_data"
        and str(manifest.get("data_status")) == EXPECTED_DATA_STATUS,
        "manifest is clearly marked as synthetic test data, not research data.",
        "manifest is missing synthetic test-data markings.",
    )
    report.check(
        int(manifest.get("hex_resolution") or -1) == EXPECTED_SOURCE_RESOLUTION,
        "manifest source is H3 R10.",
        f"manifest source resolution is {manifest.get('hex_resolution')!r}, expected R10.",
    )


def _check_rows(report: ContractReport, rows: list[dict[str, str]], source_hex_ids: set[str]) -> None:
    row_hex_ids = [str(row.get("hex_id", "")).strip() for row in rows]
    unique_row_hex_ids = set(row_hex_ids)
    report.check(
        len(rows) == len(source_hex_ids) and unique_row_hex_ids == source_hex_ids,
        f"CSV has one row per source hex ({len(source_hex_ids)}).",
        (
            f"CSV/source mismatch: rows={len(rows)}, unique_csv_hex={len(unique_row_hex_ids)}, "
            f"source_hex={len(source_hex_ids)}."
        ),
    )

    bad_values: list[str] = []
    bad_decimals: list[str] = []
    bad_order: list[str] = []
    bad_status = 0
    bad_resolution = 0
    for row in rows:
        hex_id = str(row.get("hex_id", ""))
        if str(row.get("data_status")) != EXPECTED_DATA_STATUS:
            bad_status += 1
        try:
            if int(row.get("h3_resolution") or -1) != EXPECTED_SOURCE_RESOLUTION:
                bad_resolution += 1
        except Exception:
            bad_resolution += 1

        parsed: dict[str, float] = {}
        for column in ACCEPTANCE_COLUMNS:
            text = str(row.get(column, "")).strip()
            try:
                value = float(text)
            except Exception:
                bad_values.append(f"{hex_id}:{column}={text!r}")
                continue
            parsed[column] = value
            if not 0.0 <= value <= 1.0:
                bad_values.append(f"{hex_id}:{column}={text}")
            if _decimal_places(text) > 3:
                bad_decimals.append(f"{hex_id}:{column}={text}")
        if len(parsed) == 3 and not (
            parsed["acceptance_low"] <= parsed["acceptance_medium"] <= parsed["acceptance_high"]
        ):
            bad_order.append(hex_id)

    report.check(not bad_values, "all acceptance values are in [0, 1].", f"invalid values: {bad_values[:5]}")
    report.check(
        not bad_decimals,
        "all acceptance values use max three decimals.",
        f"values with too many decimals: {bad_decimals[:5]}",
    )
    report.check(
        not bad_order,
        "low <= medium <= high for every row.",
        f"scenario ordering failed for hex rows: {bad_order[:5]}",
    )
    report.check(
        bad_status == 0 and bad_resolution == 0,
        "every row is labelled synthetic test data at H3 R10.",
        f"{bad_status} rows have bad data_status and {bad_resolution} rows have bad h3_resolution.",
    )


def _check_rollups(report: ContractReport, region: dict[str, Any], manifest: dict[str, Any]) -> None:
    geometries = region.get("h3_display_geometries") or {}
    for resolution in ROLLUP_RESOLUTIONS:
        geometry_path = _repo_path(geometries.get(str(resolution)))
        if geometry_path is None or not geometry_path.exists():
            report.fail(f"H3 R{resolution} display geometry is missing: {geometry_path}")
            continue
        collection = acceptance_feature_collection(
            manifest,
            "medium",
            int(resolution),
            str(geometry_path),
        )
        features = collection.get("features", [])
        report.check(
            bool(features)
            and all(
                int((feature.get("properties") or {}).get("target_h3_resolution") or -1) == int(resolution)
                for feature in features
            ),
            f"R10 social acceptance can be displayed as H3 R{resolution}.",
            f"R10 social acceptance rollup to R{resolution} produced no valid map features.",
        )


def _check_app_compiles(report: ContractReport) -> None:
    for relative in ("potential_app.py", "apps/potential_model/social_acceptance.py"):
        path = ROOT / relative
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            report.fail(f"{relative} does not compile: {exc}")
        else:
            report.passes.append(f"{relative} compiles.")


def main() -> int:
    report = ContractReport()
    region = load_region("bornholm")
    manifest = load_linked_manifest(region, "social_acceptance_manifest")
    if not isinstance(manifest, dict):
        report.fail("Bornholm social_acceptance_manifest could not be loaded.")
        return report.emit()

    _check_manifest(report, manifest)
    source_path = _repo_path(str(manifest.get("source_hex_geojson") or ""))
    csv_path = _repo_path(str(manifest.get("acceptance_csv") or ""))
    report.check(bool(source_path and source_path.exists()), f"source hex GeoJSON exists: {source_path}", "source hex GeoJSON is missing.")
    report.check(bool(csv_path and csv_path.exists()), f"acceptance CSV exists: {csv_path}", "acceptance CSV is missing.")
    if not (source_path and source_path.exists() and csv_path and csv_path.exists()):
        return report.emit()

    _check_rows(report, _load_csv(csv_path), _load_source_hex_ids(source_path))
    _check_rollups(report, region, manifest)
    _check_app_compiles(report)
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
