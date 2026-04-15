from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def package_root() -> Path:
    return Path(__file__).resolve().parent


def manifests_root() -> Path:
    return package_root() / "manifests"


def resolve_repo_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    return repo_root() / path


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=64)
def read_manifest(path_str: str) -> dict[str, Any]:
    return _read_json(Path(path_str))


def list_region_manifest_paths() -> list[Path]:
    region_dir = manifests_root() / "regions"
    if not region_dir.exists():
        return []
    return sorted(region_dir.glob("*.json"))


def list_regions() -> list[dict[str, Any]]:
    regions: list[dict[str, Any]] = []
    for path in list_region_manifest_paths():
        manifest = read_manifest(str(path))
        manifest["_manifest_path"] = str(path)
        regions.append(manifest)
    return regions


def load_region(region_id: str) -> dict[str, Any]:
    path = manifests_root() / "regions" / f"{region_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Region manifest not found: {path}")
    manifest = read_manifest(str(path)).copy()
    manifest["_manifest_path"] = str(path)
    return manifest


def load_linked_manifest(region: dict[str, Any], key: str) -> dict[str, Any] | None:
    path = resolve_repo_path(region.get(key))
    if path is None or not path.exists():
        return None
    manifest = read_manifest(str(path)).copy()
    manifest["_manifest_path"] = str(path)
    return manifest

