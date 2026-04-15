from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import h3
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_DIR = REPO_ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from potential_model.manifests import load_region, load_linked_manifest, read_manifest, resolve_repo_path  # noqa: E402
from potential_model.potential import solar_capacity_frame  # noqa: E402


OUT_DIR = REPO_ROOT / "docs/geocontext/potential_framework/data/bornholm_solar_potential_v0/h3_rollups"
SOURCE_RESOLUTION = 9
TARGET_RESOLUTIONS = [9, 8, 7, 6]


def _score_breaks(solar_rules: dict[str, Any]) -> list[dict[str, Any]]:
    return list((solar_rules.get("score_model") or {}).get("class_breaks") or [])


def _class_for_score(score: float, breaks: list[dict[str, Any]]) -> dict[str, Any]:
    for item in breaks:
        lower = float(item.get("min", 0))
        upper = float(item.get("max", 100))
        if lower <= score < upper or (score == 100 and upper == 100):
            return item
    return breaks[-1] if breaks else {"id": "unknown", "label": "Unknown", "color": "#999999"}


def _mode_or_first(values: pd.Series) -> Any:
    mode = values.mode(dropna=True)
    if not mode.empty:
        return mode.iloc[0]
    non_null = values.dropna()
    return non_null.iloc[0] if not non_null.empty else None


def _write_summary(frame: pd.DataFrame, path: Path) -> None:
    summary = (
        frame.groupby(["solar_class", "solar_class_label"], as_index=False)
        .agg(
            hexagoner=("hex_id", "count"),
            medelpoang=("solar_score", "mean"),
            min_poang=("solar_score", "min"),
            max_poang=("solar_score", "max"),
        )
        .sort_values("medelpoang")
    )
    summary["medelpoang"] = summary["medelpoang"].round(2)
    summary["min_poang"] = summary["min_poang"].round(2)
    summary["max_poang"] = summary["max_poang"].round(2)
    summary.to_csv(path, index=False, encoding="utf-8")


def _rollup(frame: pd.DataFrame, target_resolution: int, breaks: list[dict[str, Any]]) -> pd.DataFrame:
    if target_resolution == SOURCE_RESOLUTION:
        out = frame.copy()
        out["h3_resolution"] = SOURCE_RESOLUTION
        out["source_resolution"] = SOURCE_RESOLUTION
        out["source_child_count"] = 1
        out["high_potential_share"] = out["solar_class"].isin(["high", "very_high"]).astype(float)
        return out[
            [
                "hex_id",
                "h3_resolution",
                "source_resolution",
                "source_child_count",
                "solar_score",
                "solar_class",
                "solar_class_label",
                "solar_color",
                "high_potential_share",
                "class_km",
                "landscape_type",
            ]
        ]

    work = frame.copy()
    work["hex_id"] = work["hex_id"].astype(str).map(lambda value: h3.cell_to_parent(value, target_resolution))
    work["is_high_potential"] = work["solar_class"].isin(["high", "very_high"]).astype(float)
    grouped = (
        work.groupby("hex_id", as_index=False)
        .agg(
            source_child_count=("solar_score", "count"),
            solar_score=("solar_score", "mean"),
            high_potential_share=("is_high_potential", "mean"),
            class_km=("class_km", _mode_or_first),
            landscape_type=("landscape_type", _mode_or_first),
        )
        .sort_values("hex_id")
    )
    grouped["solar_score"] = grouped["solar_score"].round(1)
    grouped["high_potential_share"] = grouped["high_potential_share"].round(3)
    class_rows = [_class_for_score(float(score), breaks) for score in grouped["solar_score"]]
    grouped["solar_class"] = [str(item.get("id", "unknown")) for item in class_rows]
    grouped["solar_class_label"] = [str(item.get("label", item.get("id", "unknown"))) for item in class_rows]
    grouped["solar_color"] = [str(item.get("color", "#999999")) for item in class_rows]
    grouped["h3_resolution"] = target_resolution
    grouped["source_resolution"] = SOURCE_RESOLUTION
    return grouped[
        [
            "hex_id",
            "h3_resolution",
            "source_resolution",
            "source_child_count",
            "solar_score",
            "solar_class",
            "solar_class_label",
            "solar_color",
            "high_potential_share",
            "class_km",
            "landscape_type",
        ]
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    region = load_region("bornholm")
    landscape_manifest = load_linked_manifest(region, "landscape_manifest")
    potential_manifest = load_linked_manifest(region, "potential_manifest")
    if landscape_manifest is None or potential_manifest is None:
        raise RuntimeError("Bornholm landscape and potential manifests are required.")

    solar_rule_path = resolve_repo_path((potential_manifest.get("rules") or {}).get("solar"))
    if solar_rule_path is None or not solar_rule_path.exists():
        raise RuntimeError("Bornholm solar rules manifest is missing.")
    solar_rules = read_manifest(str(solar_rule_path))
    breaks = _score_breaks(solar_rules)

    base = solar_capacity_frame(landscape_manifest, solar_rules)
    manifest_rows: list[dict[str, Any]] = []

    for target_resolution in TARGET_RESOLUTIONS:
        rolled = _rollup(base, target_resolution, breaks)
        if target_resolution == SOURCE_RESOLUTION:
            name = f"bornholm_solar_potential_res_{target_resolution}.csv"
            summary_name = f"bornholm_solar_potential_res_{target_resolution}_summary.csv"
        else:
            name = f"bornholm_solar_potential_res_{target_resolution}_rollup_from_res_{SOURCE_RESOLUTION}.csv"
            summary_name = f"bornholm_solar_potential_res_{target_resolution}_rollup_from_res_{SOURCE_RESOLUTION}_summary.csv"
        path = OUT_DIR / name
        summary_path = OUT_DIR / summary_name
        rolled.to_csv(path, index=False, encoding="utf-8")
        _write_summary(rolled, summary_path)
        manifest_rows.append(
            {
                "technology": "solar",
                "h3_resolution": target_resolution,
                "source_resolution": SOURCE_RESOLUTION,
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "summary_path": str(summary_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "feature_count": int(len(rolled)),
            }
        )
        print(f"Wrote R{target_resolution}: {len(rolled)} rows -> {path}")

    manifest_path = OUT_DIR / "bornholm_solar_potential_v0_h3_rollups_manifest.json"
    manifest_path.write_text(json.dumps(manifest_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote rollup manifest -> {manifest_path}")


if __name__ == "__main__":
    main()

