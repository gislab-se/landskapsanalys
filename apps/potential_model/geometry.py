from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


@st.cache_data(show_spinner=False)
def load_h3_display_geometries(path_str: str) -> dict[str, dict[str, Any]]:
    path = Path(path_str)
    data = json.loads(path.read_text(encoding="utf-8"))
    geometries: dict[str, dict[str, Any]] = {}
    for feature in data.get("features") or []:
        properties = feature.get("properties") or {}
        hex_id = properties.get("hex_id") or properties.get("h3_address")
        geometry = feature.get("geometry")
        if hex_id and geometry and geometry.get("coordinates"):
            geometries[str(hex_id)] = geometry
    return geometries


def geometry_for_hex(
    hex_id: str,
    display_geometries: dict[str, dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if not display_geometries:
        return None
    return display_geometries.get(str(hex_id))
