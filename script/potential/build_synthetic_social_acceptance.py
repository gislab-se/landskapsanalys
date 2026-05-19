from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGION_IDS = ("bornholm", "trondelag")
SCENARIOS = ("low", "medium", "high")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(str(path_value))
    return path if path.is_absolute() else ROOT / path


def _linked_manifest(region: dict[str, Any], key: str) -> dict[str, Any]:
    path = _resolve(region.get(key))
    if path is None or not path.exists():
        raise FileNotFoundError(f"Missing {key}: {path}")
    manifest = _read_json(path)
    manifest["_manifest_path"] = str(path)
    return manifest


def _features(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError(f"GeoJSON has no feature list: {path}")
    return features


def _stable_unit(seed: int, hex_id: str, salt: str) -> float:
    payload = f"{seed}:{hex_id}:{salt}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64 - 1)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _percentile(values: list[float], pct: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return 0.0
    index = (len(clean) - 1) * _clip01(pct)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return clean[lower]
    weight = index - lower
    return clean[lower] * (1.0 - weight) + clean[upper] * weight


def _scale(value: float, low: float, high: float) -> float:
    if not math.isfinite(value) or abs(high - low) < 1e-9:
        return 0.5
    return _clip01((value - low) / (high - low))


def _numeric(properties: dict[str, Any], key: str) -> float | None:
    try:
        value = float(properties.get(key))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def _role_value(properties: dict[str, Any], refs: list[str]) -> float:
    values: list[float] = []
    for ref in refs:
        text = str(ref)
        if text.startswith("class_km:"):
            expected = text.split(":", 1)[1].strip()
            values.append(1.0 if str(properties.get("class_km", "")).strip() == expected else 0.0)
            continue
        value = _numeric(properties, text)
        if value is not None:
            values.append(value)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _role_refs(landscape_manifest: dict[str, Any], role: str) -> list[str]:
    refs = ((landscape_manifest.get("semantic_roles") or {}).get(role) or [])
    return [str(ref) for ref in refs]


def _signals(features: list[dict[str, Any]], landscape_manifest: dict[str, Any]) -> dict[str, dict[str, float]]:
    raw_by_role: dict[str, list[float]] = {
        "settlement": [],
        "coastal": [],
        "protected": [],
        "relief": [],
        "everyday": [],
    }
    refs = {
        "settlement": _role_refs(landscape_manifest, "settlement_built_structure"),
        "coastal": _role_refs(landscape_manifest, "coastal_lowland"),
        "protected": _role_refs(landscape_manifest, "protected_forest_habitat"),
        "relief": _role_refs(landscape_manifest, "steep_valley_relief"),
        "everyday": _role_refs(landscape_manifest, "mixed_everyday_matrix"),
    }
    raw_rows: list[tuple[str, dict[str, float]]] = []
    for feature in features:
        properties = dict(feature.get("properties") or {})
        hex_id = str(properties.get("hex_id") or properties.get("h3_address") or "")
        if not hex_id:
            continue
        role_values = {role: _role_value(properties, role_refs) for role, role_refs in refs.items()}
        raw_rows.append((hex_id, role_values))
        for role, value in role_values.items():
            raw_by_role[role].append(value)

    ranges = {
        role: (_percentile(values, 0.05), _percentile(values, 0.95))
        for role, values in raw_by_role.items()
    }
    scaled: dict[str, dict[str, float]] = {}
    for hex_id, role_values in raw_rows:
        scaled[hex_id] = {
            role: _scale(value, ranges[role][0], ranges[role][1])
            for role, value in role_values.items()
        }
    return scaled


def _acceptance_values(seed: int, hex_id: str, signal: dict[str, float]) -> dict[str, float]:
    settlement = signal.get("settlement", 0.5)
    coastal = signal.get("coastal", 0.5)
    protected = signal.get("protected", 0.5)
    relief = signal.get("relief", 0.5)
    everyday = signal.get("everyday", 0.5)

    nimby_pressure = 0.34 * settlement + 0.12 * protected + 0.09 * relief + 0.06 * coastal
    local_benefit = 0.15 * everyday + 0.09 * (1.0 - protected) + 0.08 * _stable_unit(seed, hex_id, "benefit")
    irregularity = (_stable_unit(seed, hex_id, "irrational") - 0.5) * 0.22
    self_interest = 0.16 if _stable_unit(seed, hex_id, "self-interest") > 0.88 else 0.0
    hard_opposition = -0.18 if _stable_unit(seed, hex_id, "hard-opposition") > 0.91 else 0.0

    medium = _clip01(0.54 - nimby_pressure + local_benefit + irregularity + self_interest + hard_opposition)
    low = _clip01(medium - 0.18 + (_stable_unit(seed, hex_id, "low") - 0.5) * 0.06)
    high = _clip01(medium + 0.20 + (_stable_unit(seed, hex_id, "high") - 0.5) * 0.06)
    return {
        "acceptance_low": round(low, 3),
        "acceptance_medium": round(medium, 3),
        "acceptance_high": round(high, 3),
    }


def _write_region(region_id: str) -> Path:
    region = _read_json(ROOT / "apps" / "potential_model" / "manifests" / "regions" / f"{region_id}.json")
    landscape_manifest = _linked_manifest(region, "landscape_manifest")
    acceptance_manifest = _linked_manifest(region, "social_acceptance_manifest")

    source_path = _resolve(acceptance_manifest.get("source_hex_geojson"))
    output_path = _resolve(acceptance_manifest.get("acceptance_csv"))
    if source_path is None or output_path is None:
        raise ValueError(f"{region_id}: social acceptance manifest is missing source/output paths")

    features = _features(source_path)
    signals = _signals(features, landscape_manifest)
    seed = int(acceptance_manifest.get("random_seed") or 20260519)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "hex_id",
        "h3_resolution",
        "acceptance_low",
        "acceptance_medium",
        "acceptance_high",
        "data_status",
        "method_version",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for hex_id in sorted(signals):
            row = {
                "hex_id": hex_id,
                "h3_resolution": int(acceptance_manifest.get("hex_resolution") or 0),
                **_acceptance_values(seed, hex_id, signals[hex_id]),
                "data_status": "synthetic_test_data_not_research",
                "method_version": str(acceptance_manifest.get("acceptance_id") or "synthetic_social_acceptance_v0"),
            }
            writer.writerow(row)
    return output_path


def main() -> int:
    for region_id in REGION_IDS:
        output_path = _write_region(region_id)
        print(f"{region_id}: wrote {output_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
