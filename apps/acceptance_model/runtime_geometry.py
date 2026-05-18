from __future__ import annotations

import hashlib
import os
import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from .layers import registry_path as active_registry_path
from .layers import repo_root


RUNTIME_RELATIVE_DIR = "docs/geocontext/acceptance_framework/data/prototype_runtime"
RENDER_SCRIPT = "script/acceptance/render_wind_acceptance_geometry_runtime.R"
REGISTRY_PATH = "apps/acceptance_model/registry.json"


def runtime_root() -> Path:
    root = repo_root() / RUNTIME_RELATIVE_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _runtime_revision_token() -> str:
    render_path = repo_root() / RENDER_SCRIPT
    registry_path = active_registry_path()
    return "|".join(
        [
            str(render_path),
            str(render_path.stat().st_mtime_ns if render_path.exists() else 0),
            str(registry_path),
            str(registry_path.stat().st_mtime_ns if registry_path.exists() else 0),
        ]
    )


def run_geometry_runtime(config_json: str) -> dict[str, Any]:
    return _run_geometry_runtime_cached(config_json, _runtime_revision_token())


@st.cache_data(show_spinner=False)
def _run_geometry_runtime_cached(config_json: str, revision_token: str) -> dict[str, Any]:
    render_path = repo_root() / RENDER_SCRIPT
    registry_path = active_registry_path()
    revision_token = "|".join(
        [
            config_json,
            revision_token,
        ]
    )
    cache_key = hashlib.sha1(revision_token.encode("utf-8")).hexdigest()[:16]
    run_dir = runtime_root() / cache_key
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "config.json"
    metadata_path = run_dir / "metadata.json"
    config_path.write_text(config_json, encoding="utf-8")

    if not metadata_path.exists():
        command = [
            "Rscript",
            str(repo_root() / RENDER_SCRIPT),
            str(config_path),
            str(run_dir),
        ]
        env = os.environ.copy()
        env["LANDSKAPSANALYS_REPO_ROOT"] = str(repo_root())
        env["ACCEPTANCE_REGISTRY_PATH"] = str(registry_path)
        result = subprocess.run(
            command,
            cwd=str(repo_root()),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip() or "R geometry render failed.")

    metadata = _load_json(metadata_path)

    raw_groups = metadata.get("groups") or {}
    if isinstance(raw_groups, list):
        raw_groups = {}

    groups: dict[str, dict[str, Any]] = {}
    for group_id, group_meta in raw_groups.items():
        if not isinstance(group_meta, dict) or "geojson_file" not in group_meta:
            continue
        group_file = run_dir / str(group_meta["geojson_file"])
        groups[group_id] = {
            **group_meta,
            "geojson": _load_json(group_file) if group_file.exists() else None,
        }

    raw_combined = metadata.get("combined") or None
    if isinstance(raw_combined, list):
        raw_combined = None

    combined = None
    if isinstance(raw_combined, dict) and "geojson_file" in raw_combined:
        combined_file = run_dir / str(raw_combined["geojson_file"])
        combined = {
            **raw_combined,
            "geojson": _load_json(combined_file) if combined_file.exists() else None,
        }

    return {
        "cache_key": cache_key,
        "groups": groups,
        "combined": combined,
    }
