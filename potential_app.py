from __future__ import annotations

from collections import deque
import h3
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parent
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from potential_model.geometry import geometry_for_hex, load_h3_display_geometries  # noqa: E402
from potential_model.landscape import (  # noqa: E402
    CLUSTER_COLORS,
    FACTOR_STOPS,
    V10_TYPE_COLORS,
    cluster_summary,
    factor_columns,
    factor_label,
    feature_collection_for_frame,
    landscape_source_resolution,
    landscape_type_feature_collection_for_frame,
    landscape_frame_for_resolution,
    load_cluster_profile,
    load_factor_scores,
    load_run_summary,
)
from potential_model.manifests import (  # noqa: E402
    list_regions,
    load_linked_manifest,
    read_manifest,
    resolve_repo_path,
)
from potential_model.map_rendering import build_layered_hex_map_html  # noqa: E402
from potential_model.potential import (  # noqa: E402
    potential_by_landscape,
    potential_feature_collection,
    potential_summary,
    rollup_frame_for_entry,
    rollup_potential_frame,
    solar_capacity_frame,
    solar_capacity_summary,
)
from potential_model.wind_acceptance import (  # noqa: E402
    GROUP_LABELS,
    GROUP_PARAM_MAP,
    SOURCE_RESOLUTION as WIND_SOURCE_RESOLUTION,
    WIND_GROUP_LAYER_DEFAULTS,
    normalize_group_layer_map,
    runtime_combined_hex_frame,
    wind_acceptance_group_summary,
    wind_acceptance_potential_frame,
    wind_acceptance_rollup_frame,
    wind_candidate_summary,
    wind_vector_feature_collection,
)
from acceptance_model.layers import (  # noqa: E402
    layer_status_table as acceptance_layer_status_table,
    load_registry as load_acceptance_registry,
    ordered_groups,
    ordered_layers,
    source_geojson_for_layer,
)
from acceptance_model.runtime_geometry import run_geometry_runtime  # noqa: E402
from acceptance_model.i18n import (  # noqa: E402
    group_analysis_label,
    group_interpretation,
    group_label,
    layer_label,
    layer_note,
    ui_text,
)


PAGE_TITLE = "Sol- och vindpotential"
MAP_VIEW_RESET_TOKEN_KEY = "potential_map_view_reset_token"
LEFT_PANEL_OPEN_KEY = "potential_left_panel_open"
RIGHT_PANEL_OPEN_KEY = "potential_right_panel_open"
REGION_SELECT_KEY = "potential_selected_region_id"
WIND_LAYER_SELECTION_KEY = "wind_builder_selected_layers"
WIND_RUNTIME_OVERLAY_KEY = "wind_builder_runtime_overlay_enabled"
WIND_CONTROL_LANGUAGE = "sv"
WIND_POLYGON_HEX_RESOLUTION = 10

WIND_SHARE_CLASS_SPECS: list[dict[str, Any]] = [
    {"id": "share_0", "label": "0%", "max_pct": 0.0, "legend_label": "0%", "base_color": "#d7301f", "core_color": "#7f0000"},
    {"id": "share_1", "label": ">0-5%", "max_pct": 5.0, "legend_label": "<=5%", "base_color": "#ef6548", "core_color": "#b30000"},
    {"id": "share_2", "label": ">5-10%", "max_pct": 10.0, "legend_label": None, "base_color": "#f16913", "core_color": "#d7301f"},
    {"id": "share_3", "label": ">10-15%", "max_pct": 15.0, "legend_label": None, "base_color": "#fd8d3c", "core_color": "#e6550d"},
    {"id": "share_4", "label": ">15-25%", "max_pct": 25.0, "legend_label": "~25%", "base_color": "#fdae61", "core_color": "#f16913"},
    {"id": "share_5", "label": ">25-35%", "max_pct": 35.0, "legend_label": None, "base_color": "#fecc5c", "core_color": "#fd8d3c"},
    {"id": "share_6", "label": ">35-50%", "max_pct": 50.0, "legend_label": "~50%", "base_color": "#fff7a3", "core_color": "#fecc5c"},
    {"id": "share_7", "label": ">50-65%", "max_pct": 65.0, "legend_label": None, "base_color": "#d9ef8b", "core_color": "#ffff66"},
    {"id": "share_8", "label": ">65-80%", "max_pct": 80.0, "legend_label": None, "base_color": "#a6d96a", "core_color": "#66bd63"},
    {"id": "share_9", "label": ">80-100%", "max_pct": 100.0, "legend_label": "100%", "base_color": "#66bd63", "core_color": "#006d2c"},
]


def _map_view_reset_token() -> int:
    try:
        return int(st.session_state.get(MAP_VIEW_RESET_TOKEN_KEY, 0))
    except Exception:
        return 0


def _request_browser_map_view_reset() -> None:
    st.session_state[MAP_VIEW_RESET_TOKEN_KEY] = _map_view_reset_token() + 1


def _init_panel_state() -> None:
    st.session_state.setdefault(LEFT_PANEL_OPEN_KEY, True)
    st.session_state.setdefault(RIGHT_PANEL_OPEN_KEY, True)


def _toggle_panel(key: str) -> None:
    st.session_state[key] = not bool(st.session_state.get(key, True))


def _panel_shell() -> tuple[Any | None, Any | None]:
    _init_panel_state()
    left_open = bool(st.session_state.get(LEFT_PANEL_OPEN_KEY, True))
    right_open = bool(st.session_state.get(RIGHT_PANEL_OPEN_KEY, True))
    left_width = "min(20rem, 28vw)"
    right_width = "min(20rem, 28vw)"
    left_padding = f"calc({left_width} + 1.25rem)" if left_open else "1.5rem"
    right_padding = f"calc({right_width} + 1.25rem)" if right_open else "1.5rem"
    left_toggle_left = f"calc({left_width} + 0.45rem)" if left_open else "0.65rem"
    right_toggle_right = f"calc({right_width} + 0.45rem)" if right_open else "0.65rem"

    panel_css = f"""
        <style>
        div[data-testid="stAppViewContainer"] section.main .block-container,
        div[data-testid="stAppViewContainer"] .main .block-container {{
          max-width: none;
          padding-left: {left_padding};
          padding-right: {right_padding};
          padding-top: 0.7rem;
        }}
        div[data-testid="column"]:has(#left-panel-content-anchor) {{
          position: fixed !important;
          top: 0;
          left: 0;
          bottom: 0;
          width: {left_width} !important;
          min-width: {left_width} !important;
          max-width: {left_width} !important;
          flex: 0 0 {left_width} !important;
          z-index: 999;
          overflow-y: auto;
          overflow-x: hidden;
          background: rgb(244, 246, 249);
          border-right: 1px solid rgba(49, 51, 63, 0.16);
          padding: 3.3rem 1.05rem 2rem 1.05rem !important;
        }}
        div[data-testid="column"]:has(#right-panel-content-anchor) {{
          position: fixed !important;
          top: 0;
          right: 0;
          bottom: 0;
          width: {right_width} !important;
          min-width: {right_width} !important;
          max-width: {right_width} !important;
          flex: 0 0 {right_width} !important;
          z-index: 999;
          overflow-y: auto;
          overflow-x: hidden;
          background: rgb(244, 246, 249);
          border-left: 1px solid rgba(49, 51, 63, 0.16);
          padding: 3.3rem 1.05rem 2rem 1.05rem !important;
        }}
        div[data-testid="column"]:has(#left-panel-content-anchor) #left-panel-content-anchor,
        div[data-testid="column"]:has(#right-panel-content-anchor) #right-panel-content-anchor {{
          display: none;
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor),
        div[data-testid="column"]:has(#right-panel-toggle-anchor) {{
          min-width: 1.75rem !important;
          width: 1.75rem !important;
          max-width: 1.75rem !important;
          flex: 0 0 1.75rem !important;
          padding-left: 0 !important;
          padding-right: 0 !important;
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor) div[data-testid="stButton"],
        div[data-testid="column"]:has(#right-panel-toggle-anchor) div[data-testid="stButton"] {{
          position: fixed;
          top: 0.65rem;
          z-index: 1001;
          width: 1.75rem;
          margin: 0 !important;
          padding: 0 !important;
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor) div[data-testid="stButton"] {{
          left: {left_toggle_left};
        }}
        div[data-testid="column"]:has(#right-panel-toggle-anchor) div[data-testid="stButton"] {{
          right: {right_toggle_right};
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor) div[data-testid="stButton"] button,
        div[data-testid="column"]:has(#right-panel-toggle-anchor) div[data-testid="stButton"] button {{
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 1.75rem;
          min-width: 1.75rem;
          height: 1.75rem;
          min-height: 1.75rem;
          padding: 0;
          border: 0;
          border-radius: 0.25rem;
          background: rgba(255, 255, 255, 0.72);
          box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
          color: rgba(49, 51, 63, 0.68);
          font-size: 1rem;
          font-weight: 700;
          line-height: 1;
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor) div[data-testid="stButton"] button:hover,
        div[data-testid="column"]:has(#right-panel-toggle-anchor) div[data-testid="stButton"] button:hover {{
          background: rgba(255, 255, 255, 0.95);
          color: rgba(49, 51, 63, 0.9);
        }}
        div[data-testid="column"]:has(#left-panel-toggle-anchor) div[data-testid="stButton"] p,
        div[data-testid="column"]:has(#right-panel-toggle-anchor) div[data-testid="stButton"] p {{
          margin: 0;
          line-height: 1;
        }}
        .workspace-header {{
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: 1rem;
          margin: 0.1rem 0 0.45rem 0;
        }}
        .workspace-header h1 {{
          font-size: 1.42rem;
          line-height: 1.15;
          margin: 0;
        }}
        .workspace-eyebrow {{
          color: rgba(49, 51, 63, 0.68);
          font-size: 0.86rem;
          margin-bottom: 0.25rem;
        }}
        .workspace-pill {{
          border: 1px solid rgba(49, 51, 63, 0.16);
          border-radius: 8px;
          padding: 0.45rem 0.65rem;
          background: rgba(255, 255, 255, 0.72);
          color: rgba(49, 51, 63, 0.78);
          font-size: 0.86rem;
          white-space: nowrap;
        }}
        div[data-testid="stIFrame"] {{
          max-width: min(1320px, 100%);
          margin-left: auto !important;
          margin-right: auto !important;
          border: 1px solid rgba(49, 51, 63, 0.18);
          border-radius: 6px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
          background: #fff;
        }}
        div[data-testid="stIFrame"] iframe {{
          width: 100% !important;
        }}
        </style>
        """
    st.markdown(panel_css, unsafe_allow_html=True)

    left_col, left_toggle_col, right_toggle_col, right_col = st.columns([1, 0.05, 0.05, 1], gap="small")
    with left_toggle_col:
        st.markdown('<span id="left-panel-toggle-anchor"></span>', unsafe_allow_html=True)
        if st.button("<" if left_open else ">", key="left_panel_edge_toggle", help="Visa/dÃ¶lj kartlager"):
            _toggle_panel(LEFT_PANEL_OPEN_KEY)
            st.rerun()
    with right_toggle_col:
        st.markdown('<span id="right-panel-toggle-anchor"></span>', unsafe_allow_html=True)
        if st.button(">" if right_open else "<", key="right_panel_edge_toggle", help="Visa/dÃ¶lj kontext"):
            _toggle_panel(RIGHT_PANEL_OPEN_KEY)
            st.rerun()

    left_panel = None
    right_panel = None
    if left_open:
        with left_col:
            st.markdown('<span id="left-panel-content-anchor"></span>', unsafe_allow_html=True)
            left_panel = st.container()
    if right_open:
        with right_col:
            st.markdown('<span id="right-panel-content-anchor"></span>', unsafe_allow_html=True)
            right_panel = st.container()
    return left_panel, right_panel


def _workspace_shell() -> tuple[Any | None, Any, Any | None]:
    _init_panel_state()
    right_open = bool(st.session_state.get(RIGHT_PANEL_OPEN_KEY, True))
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] section.main .block-container,
        div[data-testid="stAppViewContainer"] .main .block-container {
          max-width: none;
          padding: 0.75rem 0.9rem 1rem 0.9rem;
        }
        .workspace-header {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: 1rem;
          margin: 0.1rem 0 0.45rem 0;
        }
        .workspace-header h1 {
          font-size: 1.42rem;
          line-height: 1.15;
          margin: 0;
        }
        .workspace-eyebrow {
          color: rgba(49, 51, 63, 0.68);
          font-size: 0.86rem;
          margin-bottom: 0.25rem;
        }
        .workspace-pill {
          border: 1px solid rgba(49, 51, 63, 0.16);
          border-radius: 8px;
          padding: 0.45rem 0.65rem;
          background: rgba(255, 255, 255, 0.72);
          color: rgba(49, 51, 63, 0.78);
          font-size: 0.86rem;
          white-space: nowrap;
        }
        div[data-testid="stIFrame"] {
          max-width: 100%;
          margin-left: auto !important;
          margin-right: auto !important;
          border: 1px solid rgba(49, 51, 63, 0.18);
          border-radius: 6px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
          background: #fff;
        }
        div[data-testid="stIFrame"] iframe {
          width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    right_width = 0.26 if right_open else 0.035
    main_col, right_col = st.columns([1.0, right_width], gap="small")
    left_panel = st.sidebar

    right_panel = None
    with right_col:
        st.markdown('<span id="right-panel-toggle-anchor"></span>', unsafe_allow_html=True)
        if st.button(">" if right_open else "<", key="right_panel_edge_toggle", help="Visa/dolj kontext"):
            _toggle_panel(RIGHT_PANEL_OPEN_KEY)
            st.rerun()
        if right_open:
            right_panel = st.container(border=True)
            with right_panel:
                st.markdown('<span id="right-panel-content-anchor"></span>', unsafe_allow_html=True)

    return left_panel, main_col, right_panel


def _region_choice_label(region: dict[str, Any]) -> str:
    status = str(region.get("status", "planned"))
    suffix = "" if status == "active" else " (planerad)"
    return f"{region.get('display_name', region.get('region_id'))}{suffix}"


def _region_options() -> dict[str, dict[str, Any]]:
    regions = list_regions()
    if not regions:
        st.error("Inga regionmanifest hittades.")
        st.stop()
    options = {str(region["region_id"]): region for region in regions}
    default_id = "bornholm" if "bornholm" in options else next(iter(options))
    if st.session_state.get(REGION_SELECT_KEY) not in options:
        st.session_state[REGION_SELECT_KEY] = default_id
    return options


def _select_region(panel: Any | None = None) -> dict[str, Any]:
    options = _region_options()
    selected_id = str(st.session_state.get(REGION_SELECT_KEY))
    if panel is None:
        return options[selected_id]

    selected_id = panel.selectbox(
        "Region",
        options=list(options),
        key=REGION_SELECT_KEY,
        format_func=lambda region_id: _region_choice_label(options[region_id]),
    )
    return options[selected_id]


def _read_optional_manifest(path_value: object) -> dict[str, Any] | None:
    path = resolve_repo_path(str(path_value)) if path_value else None
    if path is None or not path.exists():
        return None
    return read_manifest(str(path))


def _scenario_sidebar(region: dict[str, Any]) -> dict[str, Any]:
    scenario_manifest = load_linked_manifest(region, "scenario_manifest")
    st.sidebar.divider()
    st.sidebar.header("Scenarier")

    if scenario_manifest is None:
        st.sidebar.caption("Scenariomanifest saknas fÃ¶r vald region.")
        return {"scenario": None, "manifest": None}

    levels = scenario_manifest.get("scenario_levels") or []
    selected = None
    if levels:
        selected = st.sidebar.radio(
            "Scenario",
            options=levels,
            index=levels.index("medium") if "medium" in levels else 0,
            format_func=lambda value: {"low": "LÃ¥g", "medium": "Mellan", "high": "HÃ¶g"}.get(value, str(value)),
        )
    st.sidebar.caption(f"Scenario-set: {scenario_manifest.get('scenario_set_id', '-')}")
    st.sidebar.caption(f"Lager: {len(scenario_manifest.get('layers') or [])}")
    if not scenario_manifest.get("layers"):
        st.sidebar.caption("Scenariofiler kopplas in senare.")
    return {"scenario": selected, "manifest": scenario_manifest}


def _scenario_state(region: dict[str, Any], panel: Any | None = None) -> dict[str, Any]:
    scenario_manifest = load_linked_manifest(region, "scenario_manifest")
    if scenario_manifest is None:
        if panel is not None:
            panel.caption("Scenariomanifest saknas fÃ¶r vald region.")
        return {"scenario": None, "manifest": None}

    levels = scenario_manifest.get("scenario_levels") or []
    selected = None
    if levels:
        scenario_key = f"potential_scenario_{region.get('region_id', 'region')}"
        default_level = "medium" if "medium" in levels else levels[0]
        if st.session_state.get(scenario_key) not in levels:
            st.session_state[scenario_key] = default_level
        if panel is None:
            selected = st.session_state.get(scenario_key)
        else:
            selected = panel.radio(
                "Scenario",
                options=levels,
                key=scenario_key,
                format_func=lambda value: {"low": "LÃ¥g", "medium": "Mellan", "high": "HÃ¶g"}.get(value, str(value)),
            )
    if panel is not None:
        panel.caption(f"Scenario-set: {scenario_manifest.get('scenario_set_id', '-')}")
        panel.caption(f"Lager: {len(scenario_manifest.get('layers') or [])}")
        if not scenario_manifest.get("layers"):
            panel.caption("Scenariofiler kopplas in senare.")
    return {"scenario": selected, "manifest": scenario_manifest}


def _render_region_scenario_panel(panel: Any | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if panel is None:
        region = _select_region(None)
        return region, _scenario_state(region, None)

    with panel.expander("Region", expanded=False):
        region = _select_region(st)
    with panel.expander("Scenarier", expanded=False):
        scenario_state = _scenario_state(region, st)
    return region, scenario_state


def _metric_header(region: dict[str, Any], scenario_state: dict[str, Any], h3_resolution: int | None = None) -> None:
    st.title(PAGE_TITLE)
    st.caption("Regional v0 fÃ¶r scenarier, solpotential, vindpotential och landskapsanalys.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Region", str(region.get("display_name", region.get("region_id"))))
    c2.metric("Scenario", str(scenario_state.get("scenario") or "-"))
    c3.metric("Skala", str(region.get("nominal_scale", "TBD")))
    c4.metric("CRS", str(region.get("native_crs", "TBD")))
    shown_resolution = h3_resolution or region.get("default_h3_resolution")
    c5.metric("H3", "TBD" if shown_resolution in {None, ""} else f"R{shown_resolution}")


def _workspace_header(region: dict[str, Any], scenario_state: dict[str, Any], h3_resolution: int | None = None) -> None:
    shown_resolution = h3_resolution or region.get("default_h3_resolution")
    h3_label = "TBD" if shown_resolution in {None, ""} else f"R{shown_resolution}"
    region_label = str(region.get("display_name", region.get("region_id")))
    scenario_label = str(scenario_state.get("scenario") or "-")
    st.markdown(
        f"""
        <div class="workspace-header">
          <div>
            <div class="workspace-eyebrow">{region_label} Â· scenario {scenario_label} Â· H3 {h3_label}</div>
            <h1>{PAGE_TITLE}</h1>
          </div>
          <div class="workspace-pill">{region.get("nominal_scale", "TBD")} Â· {region.get("native_crs", "TBD")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _load_context(region: dict[str, Any]) -> dict[str, Any]:
    landscape_manifest = load_linked_manifest(region, "landscape_manifest")
    potential_manifest = load_linked_manifest(region, "potential_manifest")
    if landscape_manifest is None or potential_manifest is None:
        st.info("Vald region saknar landskaps- eller potentialmanifest.")
        st.stop()

    rules = potential_manifest.get("rules") or {}
    solar_rules = _read_optional_manifest(rules.get("solar"))
    wind_rules = _read_optional_manifest(rules.get("wind"))
    if solar_rules is None:
        st.info("Solregler saknas fÃ¶r vald region.")
        st.stop()

    return {
        "landscape_manifest": landscape_manifest,
        "potential_manifest": potential_manifest,
        "solar_rules": solar_rules,
        "wind_rules": wind_rules,
    }


def _available_h3_resolutions(region: dict[str, Any]) -> list[int]:
    values = [int(value) for value in region.get("available_h3_resolutions", [])]
    return sorted(values, reverse=True) or [int(region.get("default_h3_resolution", 9))]


def _preferred_h3_resolution(region: dict[str, Any], preferred: int = 9) -> int:
    available = _available_h3_resolutions(region)
    return int(preferred) if int(preferred) in available else int(available[0])


def _h3_display_geometry_path(region: dict[str, Any], resolution: int) -> str | None:
    geometry_paths = region.get("h3_display_geometries") or {}
    path_value = geometry_paths.get(str(resolution))
    path = resolve_repo_path(path_value) if path_value else None
    if path is None or not path.exists():
        return None
    return str(path)


def _h3_option_label(region: dict[str, Any], resolution: int) -> str:
    display_geometry_path = _h3_display_geometry_path(region, resolution)
    if display_geometry_path:
        return f"R{resolution} ({len(load_h3_display_geometries(display_geometry_path))} landceller)"
    return f"R{resolution}"


def _opacity_key(key_prefix: str) -> str:
    return f"{key_prefix}_hex_opacity"


def _current_opacity(key_prefix: str) -> float:
    try:
        opacity = float(st.session_state.get(_opacity_key(key_prefix), 0.78))
    except Exception:
        opacity = 0.78
    return max(0.15, min(1.0, opacity))


def _render_opacity_control(key_prefix: str) -> None:
    control_left, control_center, control_right = st.columns([0.22, 0.56, 0.22], gap="small")
    with control_center:
        st.slider(
            "Opacitet hexlager",
            min_value=0.15,
            max_value=1.0,
            value=0.78,
            step=0.05,
            key=_opacity_key(key_prefix),
            help="Styr genomskinligheten fÃ¶r aktiva hexagonlager i kartan.",
        )


def _map_panel_controls(region: dict[str, Any], key_prefix: str, panel: Any | None = None) -> tuple[int, float, bool, int]:
    available = _available_h3_resolutions(region)
    state_key = f"{key_prefix}_h3_resolution"
    preferred = _preferred_h3_resolution(region, 9)
    try:
        current_value = int(st.session_state.get(state_key, preferred))
    except Exception:
        current_value = preferred
    if current_value not in available:
        current_value = preferred
    st.session_state[state_key] = current_value

    if panel is not None:
        with panel.expander("H3 resolution", expanded=True):
            h3_resolution = st.radio(
                "H3-rollup",
                options=available,
                index=available.index(current_value),
                format_func=lambda value: _h3_option_label(region, value),
                horizontal=False,
                key=state_key,
            )
            st.markdown("[Learn more about H3 resolutions](https://h3geo.org/).")
    else:
        h3_resolution = current_value

    return int(h3_resolution), _current_opacity(key_prefix), True, _map_view_reset_token()


def _filter_frame_to_display_geometries(frame: pd.DataFrame, display_geometry_path: str | None) -> pd.DataFrame:
    if not display_geometry_path or "hex_id" not in frame.columns:
        return frame
    visible_hex_ids = set(load_h3_display_geometries(display_geometry_path))
    return frame[frame["hex_id"].astype(str).isin(visible_hex_ids)].copy()


def _class_breaks(solar_rules: dict[str, Any]) -> list[dict[str, Any]]:
    return list((solar_rules.get("score_model") or {}).get("class_breaks") or [])


def _solar_rollup_entry(potential_manifest: dict[str, Any], resolution: int) -> dict[str, Any] | None:
    for entry in potential_manifest.get("h3_rollups") or []:
        if entry.get("technology") == "solar" and int(entry.get("h3_resolution", -1)) == int(resolution):
            return entry
    return None


def _default_solar_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    potential_manifest: dict[str, Any],
    solar_rules: dict[str, Any],
    resolution: int,
) -> pd.DataFrame:
    source_resolution = landscape_source_resolution(landscape_manifest)
    entry = _solar_rollup_entry(potential_manifest, resolution)
    if entry is not None and int(entry.get("source_resolution", -1)) == source_resolution:
        frame = rollup_frame_for_entry(entry)
    else:
        frame = rollup_potential_frame(
            solar_capacity_frame(landscape_manifest, solar_rules),
            resolution,
            _class_breaks(solar_rules),
            "solar",
            source_resolution=source_resolution,
        )
    return _filter_frame_to_display_geometries(frame, _h3_display_geometry_path(region, resolution))


def _custom_solar_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    solar_rules: dict[str, Any],
    resolution: int,
    params: dict[str, float],
) -> pd.DataFrame:
    rules = _solar_rules_from_params(solar_rules, params)
    base = solar_capacity_frame(landscape_manifest, rules)
    frame = rollup_potential_frame(base, resolution, _class_breaks(rules), "solar", source_resolution=landscape_source_resolution(landscape_manifest))
    return _filter_frame_to_display_geometries(frame, _h3_display_geometry_path(region, resolution))


def _wind_source_frame(
    landscape_manifest: dict[str, Any],
    solar_rules: dict[str, Any],
    ui_params: dict[str, float],
    group_layer_selection: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    return wind_acceptance_potential_frame(
        landscape_manifest,
        _class_breaks(solar_rules),
        _wind_score_params_from_ui(ui_params),
        ui_params,
        group_layer_map=group_layer_selection,
    )


def _wind_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    solar_rules: dict[str, Any],
    resolution: int,
    ui_params: dict[str, float],
    group_layer_selection: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    base = _wind_source_frame(landscape_manifest, solar_rules, ui_params, group_layer_selection=group_layer_selection)
    frame = wind_acceptance_rollup_frame(base, resolution, _class_breaks(solar_rules))
    return _filter_frame_to_display_geometries(frame, _h3_display_geometry_path(region, resolution))


def _landscape_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    resolution: int,
) -> pd.DataFrame:
    frame = landscape_frame_for_resolution(landscape_manifest, resolution)
    return _filter_frame_to_display_geometries(frame, _h3_display_geometry_path(region, resolution))


def _solar_legend_items(solar_rules: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"label": str(item.get("label", item.get("id", "OkÃ¤nd"))), "color": str(item.get("color", "#999999"))}
        for item in _class_breaks(solar_rules)
    ]


def _cluster_legend_items(landscape_manifest: dict[str, Any]) -> list[dict[str, str]]:
    labels = landscape_manifest.get("cluster_labels") or {}

    def sort_key(value: str) -> int:
        return int(value) if str(value).isdigit() else 999

    return [
        {"label": f"{key} - {labels[key]}", "color": CLUSTER_COLORS.get(str(key), "#999999")}
        for key in sorted(labels, key=sort_key)
    ]


def _landscape_type_legend_items(landscape_manifest: dict[str, Any]) -> list[dict[str, str]]:
    labels = landscape_manifest.get("landscape_type_labels") or {}
    colors = landscape_manifest.get("landscape_type_colors") or V10_TYPE_COLORS
    return [{"label": f"{key} - {labels.get(key, key)}", "color": colors.get(key, "#999999")} for key in sorted(colors)]


def _factor_legend_items() -> list[dict[str, str]]:
    labels = ["â‰¤ -2", "-1", "0", "1", "â‰¥ 2"]
    return [{"label": label, "color": color} for label, (_, color) in zip(labels, FACTOR_STOPS)]


def _default_solar_params(solar_rules: dict[str, Any]) -> dict[str, float]:
    score_model = solar_rules.get("score_model") or {}
    cluster_terms = {term.get("cluster_ref"): float(term.get("weight", 0)) for term in score_model.get("cluster_terms") or []}
    role_terms = {term.get("role"): float(term.get("weight", 0)) for term in score_model.get("role_terms") or []}
    return {
        "base_score": float(score_model.get("base_score", 55)),
        "grid_access_bonus": 0.0,
        "everyday_matrix_bonus": max(cluster_terms.get("class_km:3", 0.0), cluster_terms.get("class_km:6", 0.0), cluster_terms.get("class_km:2", 15.0)),
        "coastal_penalty": abs(role_terms.get("coastal_lowland", -12.0)),
        "terrain_penalty": abs(role_terms.get("steep_valley_relief", -12.0)),
        "protected_penalty": abs(role_terms.get("protected_forest_habitat", -18.0)),
        "settlement_penalty": abs(role_terms.get("settlement_built_structure", -10.0)),
    }


def _solar_rules_from_params(solar_rules: dict[str, Any], params: dict[str, float]) -> dict[str, Any]:
    rules = read_manifest(str(resolve_repo_path(solar_rules.get("_manifest_path")))) if solar_rules.get("_manifest_path") else solar_rules.copy()
    rules = {
        **rules,
        "score_model": {
            **(rules.get("score_model") or {}),
            "cluster_terms": [dict(item) for item in (rules.get("score_model") or {}).get("cluster_terms") or []],
            "role_terms": [dict(item) for item in (rules.get("score_model") or {}).get("role_terms") or []],
        },
    }
    score_model = rules["score_model"]
    score_model["base_score"] = float(params.get("base_score", 55.0)) + float(params.get("grid_access_bonus", 0.0))
    for term in score_model.get("cluster_terms") or []:
        if term.get("cluster_ref") in {"class_km:2", "class_km:3", "class_km:6"}:
            term["weight"] = float(params.get("everyday_matrix_bonus", term.get("weight", 15.0)))
    role_weight_map = {
        "coastal_lowland": -float(params.get("coastal_penalty", 12.0)),
        "steep_valley_relief": -float(params.get("terrain_penalty", 12.0)),
        "protected_forest_habitat": -float(params.get("protected_penalty", 18.0)),
        "settlement_built_structure": -float(params.get("settlement_penalty", 10.0)),
    }
    for term in score_model.get("role_terms") or []:
        role = term.get("role")
        if role in role_weight_map:
            term["weight"] = role_weight_map[role]
    return rules


def _default_wind_params() -> dict[str, float]:
    return {
        "settlement_distance_m": 100.0,
        "road_distance_m": 100.0,
        "grid_max_distance_m": 2000.0,
        "protected_buffer_m": 0.0,
        "coastal_buffer_m": 0.0,
        "culture_buffer_m": 0.0,
        "aviation_approach_buffer_m": 0.0,
        "aviation_bird_distance_m": 0.0,
        "military_buffer_m": 0.0,
        "landscape_sensitivity_percent": 60.0,
    }


def _wind_score_params_from_ui(ui_params: dict[str, float]) -> dict[str, float]:
    return {
        "base_score": 55.0,
        "everyday_matrix_bonus": 12.0,
        "infrastructure_bonus": min(float(ui_params["grid_max_distance_m"]) / 15000.0, 1.0) * 18.0,
        "settlement_penalty": min(float(ui_params["settlement_distance_m"]) / 3000.0, 1.0) * 35.0,
        "road_penalty": min(float(ui_params["road_distance_m"]) / 2000.0, 1.0) * 12.0,
        "protected_penalty": 10.0 + min(float(ui_params["protected_buffer_m"]) / 2000.0, 1.0) * 25.0,
        "coastal_penalty": 8.0 + min(float(ui_params["coastal_buffer_m"]) / 1000.0, 1.0) * 18.0,
        "terrain_penalty": 10.0,
        "landscape_sensitivity": max(0.0, min(2.0, float(ui_params["landscape_sensitivity_percent"]) / 60.0)),
        "factor_positive_cap": 2.0,
    }


def _state_params(prefix: str, defaults: dict[str, float]) -> dict[str, float]:
    params: dict[str, float] = {}
    for key, value in defaults.items():
        params[key] = float(st.session_state.get(f"{prefix}_{key}", value))
    return params


def _prime_solar_builder_state(defaults: dict[str, float], saved_params: dict[str, float] | None = None) -> None:
    source = saved_params or {}
    for key, value in defaults.items():
        seeded = float(source.get(key, value)) if isinstance(source, dict) else float(value)
        st.session_state.setdefault(f"solar_builder_{key}", seeded)


def _builder_slider(prefix: str, key: str, label: str, min_value: float, max_value: float, step: float, defaults: dict[str, float], help_text: str) -> None:
    st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        step=step,
        value=float(st.session_state.get(f"{prefix}_{key}", defaults[key])),
        key=f"{prefix}_{key}",
        help=help_text,
    )


def _reset_builder(prefix: str, defaults: dict[str, float]) -> None:
    for key, value in defaults.items():
        st.session_state[f"{prefix}_{key}"] = value
    st.rerun()


def _wind_builder_controls(defaults: dict[str, float]) -> None:
    _builder_slider("wind_builder", "settlement_distance_m", "Minsta avstÃ¥nd till boende", 100.0, 3000.0, 50.0, defaults, "StÃ¶rre avstÃ¥nd ger hÃ¥rdare bebyggelsestraff.")
    _builder_slider("wind_builder", "road_distance_m", "Minsta avstÃ¥nd till vÃ¤gar", 50.0, 2000.0, 25.0, defaults, "StÃ¶rre avstÃ¥nd ger hÃ¥rdare transport-/bebyggelsestraff.")
    _builder_slider("wind_builder", "grid_max_distance_m", "Max avstÃ¥nd till elinfrastruktur", 500.0, 15000.0, 250.0, defaults, "StÃ¶rre tillÃ¥tet avstÃ¥nd gÃ¶r fler lÃ¤gen tekniskt mÃ¶jliga.")
    _builder_slider("wind_builder", "protected_buffer_m", "Buffert skyddade omrÃ¥den", 0.0, 2000.0, 50.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden hard-excludar skyddade natur- och habitatlager.")
    _builder_slider("wind_builder", "coastal_buffer_m", "Buffert kust/strand", 0.0, 1000.0, 50.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden hard-excludar kustzon och strandskydd.")
    _builder_slider("wind_builder", "landscape_sensitivity_percent", "LandskapskÃ¤nslighet", 0.0, 120.0, 5.0, defaults, "Viktar hur starkt landskapsrollerna ska bromsa vindpotentialen.")
    with st.expander("Avancerade restriktioner"):
        _builder_slider("wind_builder", "culture_buffer_m", "Buffert kulturmiljÃ¶er", 0.0, 1500.0, 50.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden hard-excludar vÃ¤rdefulla kulturmiljÃ¶er.")
        _builder_slider("wind_builder", "aviation_approach_buffer_m", "Buffert inflygningszoner", 0.0, 3000.0, 100.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden hard-excludar flygplatsens inflygningszoner.")
        _builder_slider("wind_builder", "aviation_bird_distance_m", "Minsta avstÃ¥nd fÃ¥gelkollision", 0.0, 4000.0, 100.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden ger distance-conflict mot fÃ¥gelkollisionszoner.")
        _builder_slider("wind_builder", "military_buffer_m", "Buffert militÃ¤ra omrÃ¥den", 0.0, 2000.0, 50.0, defaults, "0 stÃ¤nger av gruppen. HÃ¶gre vÃ¤rden hard-excludar militÃ¤ra omrÃ¥den.")
        st.dataframe(wind_acceptance_group_summary(), use_container_width=True, hide_index=True, height=220)


def _save_solar_potential(params: dict[str, float], resolution: int) -> None:
    st.session_state["saved_solar_potential"] = {
        "params": dict(params),
        "preview_resolution": int(resolution),
    }
    st.session_state["show_user_solar"] = True


def _saved_solar_params() -> dict[str, float] | None:
    saved = st.session_state.get("saved_solar_potential")
    if not isinstance(saved, dict):
        return None
    params = saved.get("params")
    return dict(params) if isinstance(params, dict) else None


def _render_layers(
    region: dict[str, Any],
    layers: list[dict[str, Any]],
    opacity: float,
    map_state_key: str | None = None,
    map_reset_token: int = 0,
    opacity_key_prefix: str | None = None,
    note_title: str = "Samlad potential",
    note_body: str = "Aktiva lager styrs i appen och kan Ã¤ven slÃ¥s av/pÃ¥ i kartkontrollen.",
) -> None:
    if not layers:
        st.info("VÃ¤lj minst ett kartlager.")
        return
    map_html = build_layered_hex_map_html(
        layers,
        center=list(region.get("default_map_center", [55.14, 14.92])),
        zoom=int(region.get("default_zoom", 9)),
        bounds=region.get("default_map_bounds"),
        fill_opacity=opacity,
        map_state_key=map_state_key,
        map_reset_token=map_reset_token,
        note_title=note_title,
        note_body=note_body,
    )
    map_left, map_center, map_right = st.columns([0.04, 0.92, 0.04], gap="small")
    with map_center:
        components.html(map_html, height=820)
        if opacity_key_prefix:
            _render_opacity_control(opacity_key_prefix)


def _potential_layer(
    name: str,
    frame: pd.DataFrame,
    technology: str,
    display_geometry_path: str | None,
    legend_items: list[dict[str, str]],
) -> dict[str, Any]:
    land_frame = _filter_frame_to_display_geometries(frame, display_geometry_path)
    return {
        "name": name,
        "feature_collection": potential_feature_collection(land_frame, technology, None),
        "fill_property": "fill",
        "legend_items": legend_items,
        "legend_id": "potential_classes",
        "legend_title": "Potentialklasser",
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
    }


def _solar_polygon_feature_collection(
    frame: pd.DataFrame,
    display_geometry_path: str | None,
    label: str,
) -> dict[str, Any] | None:
    if frame.empty:
        return None
    selected = frame[frame["solar_class"].astype(str).isin(["high", "very_high"])].copy()
    if selected.empty:
        return None
    display_geometries = load_h3_display_geometries(display_geometry_path) if display_geometry_path else {}
    multipolygon_parts: list[Any] = []
    for row in selected.itertuples(index=False):
        geometry = geometry_for_hex(str(row.hex_id), display_geometries)
        if geometry is None:
            continue
        geometry_type = str(geometry.get("type", ""))
        coordinates = geometry.get("coordinates") or []
        if geometry_type == "Polygon" and coordinates:
            multipolygon_parts.append(coordinates)
        elif geometry_type == "MultiPolygon" and coordinates:
            multipolygon_parts.extend(coordinates)
    if not multipolygon_parts:
        return None

    selected_share = (len(selected) / len(frame)) * 100.0
    popup = (
        f"<strong>{label}</strong><br>"
        f"Hex med hÃ¶g/ mycket hÃ¶g solpotential: {len(selected)}<br>"
        f"Andel av visad yta: {selected_share:.1f}%<br>"
        f"MedelpoÃ¤ng i polygonlagret: {float(selected['solar_score'].mean()):.1f}"
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": multipolygon_parts},
                "properties": {"fill": "#d97706", "popup": popup},
            }
        ],
    }


def _solar_polygon_layer(
    name: str,
    frame: pd.DataFrame,
    display_geometry_path: str | None,
    stroke_color: str = "#d97706",
    fill_color: str = "#d97706",
) -> dict[str, Any] | None:
    feature_collection = _solar_polygon_feature_collection(frame, display_geometry_path, name)
    if feature_collection is None:
        return None
    return {
        "name": name,
        "feature_collection": feature_collection,
        "fill_property": "fill",
        "legend_items": [],
        "legend_id": f"solar_polygon_{name.lower().replace(' ', '_')}",
        "legend_title": "",
        "default_visible": True,
        "stroke_color": stroke_color,
        "fill_color": fill_color,
        "stroke_opacity": 0.74,
        "fill_opacity": 0.08,
        "weight": 1.6,
        "point_radius": 6,
        "dash_array": "6 4",
        "use_global_opacity": False,
        "z_index": 430,
    }


def _wind_vector_layer(
    name: str,
    source_frame: pd.DataFrame,
    display_geometry_path: str | None,
    legend_items: list[dict[str, str]],
) -> dict[str, Any]:
    land_frame = _filter_frame_to_display_geometries(source_frame, display_geometry_path)
    return {
        "name": name,
        "feature_collection": wind_vector_feature_collection(land_frame, None, only_potential_area=True),
        "fill_property": "fill",
        "legend_items": legend_items,
        "legend_id": "potential_classes",
        "legend_title": "Potentialklasser",
        "default_visible": True,
    }


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(int(value) for value in rgb)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = str(value).strip().lstrip("#")
    if len(color) != 6:
        return (153, 153, 153)
    return tuple(int(color[idx : idx + 2], 16) for idx in (0, 2, 4))


def _mix_hex_colors(left: str, right: str, amount: float) -> str:
    amount = max(0.0, min(1.0, float(amount)))
    left_rgb = _hex_to_rgb(left)
    right_rgb = _hex_to_rgb(right)
    mixed = tuple(int(round(left_rgb[idx] + ((right_rgb[idx] - left_rgb[idx]) * amount))) for idx in range(3))
    return _rgb_to_hex(mixed)


def _default_wind_layer_selection() -> dict[str, list[str]]:
    return {group_id: list(layer_ids) for group_id, layer_ids in WIND_GROUP_LAYER_DEFAULTS.items()}


def _selected_wind_layers() -> dict[str, list[str]]:
    raw = st.session_state.get(WIND_LAYER_SELECTION_KEY)
    if not isinstance(raw, dict):
        selected = normalize_group_layer_map(_default_wind_layer_selection())
        st.session_state[WIND_LAYER_SELECTION_KEY] = selected
        return selected
    selected = normalize_group_layer_map(raw)
    st.session_state[WIND_LAYER_SELECTION_KEY] = selected
    return selected


def _wind_runtime_overlays_enabled() -> bool:
    st.session_state[WIND_RUNTIME_OVERLAY_KEY] = True
    return True


def _wind_control_key(prefix: str, item_id: str) -> str:
    return f"wind_control__{prefix}__{item_id}"


def _init_wind_control_state() -> None:
    groups, layers, _ = load_acceptance_registry()
    st.session_state[WIND_RUNTIME_OVERLAY_KEY] = True
    for group in groups.values():
        st.session_state.setdefault(_wind_control_key("analysis", group.id), int(group.analysis_default_m))
        st.session_state.setdefault(_wind_control_key("blend", group.id), int(group.blend_default))
    for layer in layers.values():
        st.session_state.setdefault(_wind_control_key("layer", layer.id), False)


def _prime_wind_builder_state(
    saved_ui_params: dict[str, float] | None = None,
    saved_layer_selection: dict[str, list[str]] | None = None,
) -> None:
    _init_wind_control_state()
    selected = normalize_group_layer_map(saved_layer_selection or {})
    for group in ordered_groups():
        param_key = GROUP_PARAM_MAP.get(group.id)
        if param_key and isinstance(saved_ui_params, dict) and param_key in saved_ui_params:
            st.session_state.setdefault(
                _wind_control_key("analysis", group.id),
                int(round(float(saved_ui_params[param_key]))),
            )
    for layer in ordered_layers():
        st.session_state.setdefault(
            _wind_control_key("layer", layer.id),
            bool(layer.id in selected.get(layer.group_id, [])),
        )


def _wind_layer_status_lookup(registry_meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    status_df = acceptance_layer_status_table(registry_meta)
    if status_df.empty:
        return {}
    return {str(row["layer_id"]): row.to_dict() for _, row in status_df.iterrows()}


def _wind_blend_value(group_id: str) -> int:
    try:
        value = int(st.session_state.get(_wind_control_key("blend", group_id), 50))
    except Exception:
        value = 50
    return max(0, min(100, value))


def _wind_source_opacity(group_id: str) -> float:
    return max(0.0, 1.0 - (_wind_blend_value(group_id) / 100.0))


def _wind_group_opacity(group_id: str) -> float:
    return max(0.0, min(1.0, _wind_blend_value(group_id) / 100.0))


def _wind_group_controls(
    widget_prefix: str,
    language: str = WIND_CONTROL_LANGUAGE,
) -> tuple[dict[str, list[str]], dict[str, float], bool]:
    _init_wind_control_state()
    groups, layers, registry_meta = load_acceptance_registry()
    availability = _wind_layer_status_lookup(registry_meta)
    selected: dict[str, list[str]] = {group.id: [] for group in ordered_groups()}

    st.header(ui_text("groups_header", language))
    st.caption(ui_text("groups_caption", language))
    with st.form(f"{widget_prefix}_group_controls", clear_on_submit=False):
        st.caption(ui_text("apply_hint", language))
        for group in ordered_groups():
            with st.expander(group_label(group, language, group.label), expanded=group.id in {"settlement", "transport", "electrical"}):
                st.caption(group_interpretation(group, language, group.interpretation))
                st.slider(
                    group_analysis_label(group, language, group.analysis_label),
                    min_value=int(group.analysis_min_m),
                    max_value=int(group.analysis_max_m),
                    step=int(group.analysis_step_m),
                    key=_wind_control_key("analysis", group.id),
                    help=ui_text("analysis_slider_help", language),
                )
                st.slider(
                    ui_text("display_blend", language),
                    min_value=0,
                    max_value=100,
                    step=5,
                    key=_wind_control_key("blend", group.id),
                    help=ui_text("display_blend_help", language),
                )
                for layer in [item for item in ordered_layers() if item.group_id == group.id]:
                    status = availability.get(layer.id, {})
                    ready = (
                        bool(status.get("geojson_ready"))
                        and bool(status.get("source_exists"))
                        and int(status.get("feature_count", 0) or 0) > 0
                        and str(status.get("status", "")) == "ok"
                    )
                    message = str(status.get("message", "") or layer_note(layer, language, layer.note) or "")
                    checked = st.checkbox(
                        layer_label(layer, language, layer.label),
                        key=_wind_control_key("layer", layer.id),
                        disabled=not ready,
                        help=message,
                    )
                    if checked and ready:
                        selected[group.id].append(layer.id)
                if not selected[group.id]:
                    st.caption(ui_text("group_inactive", language))
        applied = st.form_submit_button(ui_text("apply_changes", language), type="primary", use_container_width=True)

    normalized = normalize_group_layer_map(selected)
    st.session_state[WIND_LAYER_SELECTION_KEY] = normalized

    ui_params = _default_wind_params()
    for group in ordered_groups():
        param_key = GROUP_PARAM_MAP.get(group.id)
        if not param_key:
            continue
        ui_params[param_key] = float(st.session_state.get(_wind_control_key("analysis", group.id), group.analysis_default_m))
    return normalized, ui_params, bool(applied)


def _wind_runtime_overlay_control() -> bool:
    st.session_state.setdefault(WIND_RUNTIME_OVERLAY_KEY, True)
    st.checkbox(
        "Visa potentiell etableringsyta (geometri)",
        key=WIND_RUNTIME_OVERLAY_KEY,
        help="KÃ¶r geometri-runtime och lÃ¤gg till grupplager plus kombinerad acceptansyta i vektorvyn.",
    )
    return _wind_runtime_overlays_enabled()


def _wind_layer_selector_controls(widget_prefix: str) -> None:
    groups, layers, _ = load_acceptance_registry()
    selected_layers = _selected_wind_layers()
    with st.expander("Kallager per regelgrupp", expanded=False):
        st.caption("Valj vilka vindlager som ska anvandas och klicka Anvand andringar.")
        with st.form(f"{widget_prefix}_wind_layer_selector", clear_on_submit=False):
            draft_layers: dict[str, list[str]] = {}
            for group_id, default_layer_ids in WIND_GROUP_LAYER_DEFAULTS.items():
                label = GROUP_LABELS.get(group_id, groups[group_id].label if group_id in groups else group_id)
                st.markdown(f"**{label}**")
                options = [layer_id for layer_id in default_layer_ids if layer_id in layers]
                selected_default = [layer_id for layer_id in selected_layers.get(group_id, []) if layer_id in options]
                draft_layers[group_id] = st.multiselect(
                    f"Lager ({len(selected_default)} valda)",
                    options=options,
                    default=selected_default,
                    format_func=lambda layer_id: layers[layer_id].label,
                    key=f"{widget_prefix}_wind_layers_{group_id}",
                )
            applied = st.form_submit_button("Anvand andringar", type="primary", use_container_width=True)
        if applied:
            st.session_state[WIND_LAYER_SELECTION_KEY] = normalize_group_layer_map(draft_layers)
            st.success("Vindlager uppdaterade.")


def _wind_active_group_ids(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> list[str]:
    _ = ui_params
    selected = normalize_group_layer_map(layer_selection or _selected_wind_layers())
    active: list[str] = []
    for group_id, layer_ids in selected.items():
        if not layer_ids:
            continue
        active.append(group_id)
    return active


def _wind_source_vector_layers(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    _ = ui_params
    groups, layers, registry_meta = load_acceptance_registry()
    selected = normalize_group_layer_map(layer_selection or _selected_wind_layers())
    map_layers: list[dict[str, Any]] = []
    for group_id in _wind_active_group_ids(ui_params, layer_selection=selected):
        group_label = GROUP_LABELS.get(group_id, groups[group_id].label if group_id in groups else group_id)
        for layer_id in selected.get(group_id, []):
            layer_spec = layers.get(layer_id)
            if layer_spec is None:
                continue
            geojson = source_geojson_for_layer(registry_meta, layer_id)
            if not geojson:
                continue
            source_color = _rgb_to_hex(layer_spec.source_color)
            source_opacity = _wind_source_opacity(group_id)
            map_layers.append(
                {
                    "name": f"KÃ¤lla: {layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label)} ({group_label})",
                    "feature_collection": geojson,
                    "fill_property": "fill",
                    "legend_items": [],
                    "legend_id": f"wind_source_{layer_id}",
                    "legend_title": "",
                    "default_visible": False,
                    "stroke_color": source_color,
                    "fill_color": source_color,
                    "stroke_opacity": max(min(source_opacity, 1.0), 0.0),
                    "fill_opacity": max(min(source_opacity * 0.28, 1.0), 0.0),
                    "weight": 2.0,
                    "point_radius": int(layer_spec.point_radius),
                    "use_global_opacity": False,
                }
            )
    return map_layers


def _wind_share_class_spec(area_share_pct: float) -> dict[str, Any]:
    share_value = max(0.0, min(100.0, float(area_share_pct)))
    for spec in WIND_SHARE_CLASS_SPECS:
        if share_value <= float(spec["max_pct"]):
            return spec
    return WIND_SHARE_CLASS_SPECS[-1]


def _wind_share_legend_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for spec in WIND_SHARE_CLASS_SPECS:
        if not spec.get("legend_label"):
            continue
        items.append({"label": str(spec["legend_label"]), "color": str(spec["base_color"])})
    return items


def _wind_polygon_source_layers(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    groups, layers, registry_meta = load_acceptance_registry()
    selected = normalize_group_layer_map(layer_selection or _selected_wind_layers())
    map_layers: list[dict[str, Any]] = []
    for group_id in _wind_active_group_ids(ui_params, layer_selection=selected):
        opacity = _wind_source_opacity(group_id)
        group_meta = groups.get(group_id)
        translated_group_label = GROUP_LABELS.get(group_id, group_meta.label if group_meta is not None else group_id)
        if group_meta is not None:
            translated_group_label = group_label(group_meta, WIND_CONTROL_LANGUAGE, group_meta.label)
        for layer_id in selected.get(group_id, []):
            layer_spec = layers.get(layer_id)
            if layer_spec is None:
                continue
            geojson = source_geojson_for_layer(registry_meta, layer_id)
            if geojson is None:
                continue
            map_layers.append(
                {
                    "name": f"KÃ¤lla: {layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label)} ({translated_group_label})",
                    "feature_collection": geojson,
                    "fill_property": "fill",
                    "legend_items": [],
                    "legend_id": f"wind_polygon_source_{layer_id}",
                    "legend_title": "",
                    "default_visible": False,
                    "stroke_color": _rgb_to_hex(layer_spec.source_color),
                    "fill_color": _rgb_to_hex(layer_spec.source_color),
                    "stroke_opacity": max(min(opacity, 1.0), 0.0),
                    "fill_opacity": max(min(opacity * 0.28, 1.0), 0.0),
                    "weight": 2.0,
                    "point_radius": int(layer_spec.point_radius),
                    "use_global_opacity": False,
                }
            )
    return map_layers


def _wind_polygon_group_layers(runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
    groups, _, _ = load_acceptance_registry()
    map_layers: list[dict[str, Any]] = []
    for group in ordered_groups():
        runtime_group = (runtime_result.get("groups") or {}).get(group.id)
        if runtime_group is None or runtime_group.get("geojson") is None:
            continue
        opacity = _wind_group_opacity(group.id)
        map_layers.append(
            {
                "name": f"Buffert: {group_label(groups[group.id], WIND_CONTROL_LANGUAGE, groups[group.id].label)}",
                "feature_collection": runtime_group["geojson"],
                "fill_property": "fill",
                "legend_items": [],
                "legend_id": f"wind_polygon_buffer_{group.id}",
                "legend_title": "",
                "default_visible": False,
                "stroke_color": _rgb_to_hex(groups[group.id].group_color),
                "fill_color": _rgb_to_hex(groups[group.id].group_color),
                "stroke_opacity": max(min(opacity * 0.95, 1.0), 0.0),
                "fill_opacity": max(min(opacity * 0.32, 1.0), 0.0),
                "weight": 2.2,
                "point_radius": 6,
                "use_global_opacity": False,
            }
        )
    return map_layers


def _wind_polygon_combined_layer(runtime_result: dict[str, Any]) -> dict[str, Any] | None:
    combined = runtime_result.get("combined")
    if not isinstance(combined, dict) or combined.get("geojson") is None:
        return None
    return {
        "name": "Potentiell etableringsyta",
        "feature_collection": combined["geojson"],
        "fill_property": "fill",
        "legend_items": [],
        "legend_id": "wind_polygon_combined",
        "legend_title": "",
        "default_visible": True,
        "stroke_color": "#c4322b",
        "fill_color": "#c4322b",
        "stroke_opacity": 0.78,
        "fill_opacity": 0.08,
        "weight": 1.8,
        "point_radius": 6,
        "dash_array": "7 5",
        "use_global_opacity": False,
        "z_index": 440,
    }


def _wind_polygon_group_summary_frame(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]],
    runtime_result: dict[str, Any],
) -> pd.DataFrame:
    groups, layers, _ = load_acceptance_registry()
    selected = normalize_group_layer_map(layer_selection)
    rows: list[dict[str, Any]] = []
    for group in ordered_groups():
        selected_layer_ids = selected.get(group.id, [])
        selected_labels = [
            layer_label(layers[layer_id], WIND_CONTROL_LANGUAGE, layers[layer_id].label)
            for layer_id in selected_layer_ids
            if layer_id in layers
        ]
        runtime_group = (runtime_result.get("groups") or {}).get(group.id)
        threshold_key = GROUP_PARAM_MAP.get(group.id)
        threshold_value = float(ui_params.get(threshold_key, group.analysis_default_m)) if threshold_key else 0.0
        land_share = runtime_group.get("land_share_pct") if isinstance(runtime_group, dict) else None
        rows.append(
            {
                "Regelgrupp": group_label(groups[group.id], WIND_CONTROL_LANGUAGE, groups[group.id].label),
                "KÃ¤llager": ", ".join(selected_labels) if selected_labels else "-",
                "AvstÃ¥nd m": int(round(threshold_value)),
                "Buffert synlig": bool(runtime_group and runtime_group.get("geojson")),
                "Landandel": "-" if land_share is None else f"{float(land_share):.1f}%",
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _wind_r10_neighbor_map(display_geometry_path: str) -> dict[str, list[str]]:
    land_hexes = set(load_h3_display_geometries(display_geometry_path))
    neighbor_map: dict[str, list[str]] = {}
    for hex_id in land_hexes:
        neighbor_map[str(hex_id)] = [str(neighbor) for neighbor in h3.grid_disk(str(hex_id), 1) if str(neighbor) != str(hex_id)]
    return neighbor_map


def _wind_runtime_hex_core_scores(frame: pd.DataFrame, neighbor_map: dict[str, list[str]]) -> pd.DataFrame:
    if frame.empty:
        return frame

    work = frame.copy()
    class_lookup = {str(row.hex_id): int(row.share_class_index) for row in work[["hex_id", "share_class_index"]].itertuples(index=False)}
    zone_id_lookup: dict[str, str] = {}
    zone_size_lookup: dict[str, int] = {}
    core_distance_lookup: dict[str, int] = {}
    core_score_lookup: dict[str, float] = {}
    rank_lookup_global: dict[str, int] = {}

    visited: set[str] = set()
    zone_counter = 0

    for hex_id in work["hex_id"].astype(str):
        if hex_id in visited:
            continue
        class_index = class_lookup.get(hex_id)
        if class_index is None:
            continue

        queue: deque[str] = deque([hex_id])
        component: list[str] = []
        visited.add(hex_id)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in neighbor_map.get(current, []):
                if neighbor in visited:
                    continue
                if class_lookup.get(neighbor) != class_index:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)

        component_set = set(component)
        boundary = [cell for cell in component if any(neighbor not in component_set for neighbor in neighbor_map.get(cell, []))]
        if not boundary:
            boundary = list(component)

        distance_lookup = {cell: None for cell in component}
        frontier: deque[str] = deque()
        for cell in boundary:
            distance_lookup[cell] = 0
            frontier.append(cell)

        while frontier:
            current = frontier.popleft()
            current_distance = int(distance_lookup[current] or 0)
            for neighbor in neighbor_map.get(current, []):
                if neighbor not in component_set:
                    continue
                if distance_lookup[neighbor] is not None:
                    continue
                distance_lookup[neighbor] = current_distance + 1
                frontier.append(neighbor)

        max_distance = max(int(distance_lookup[cell] or 0) for cell in component) if component else 0
        ranked_cells = sorted(component, key=lambda cell: (-int(distance_lookup[cell] or 0), cell))
        rank_lookup = {cell: idx + 1 for idx, cell in enumerate(ranked_cells)}
        zone_id = f"class_{class_index}_{zone_counter}"
        zone_counter += 1

        for cell in component:
            distance_value = int(distance_lookup[cell] or 0)
            core_value = 0.0 if max_distance <= 0 else float(distance_value) / float(max_distance)
            zone_id_lookup[cell] = zone_id
            zone_size_lookup[cell] = int(len(component))
            core_distance_lookup[cell] = distance_value
            core_score_lookup[cell] = round(core_value, 3)
            rank_lookup_global[cell] = int(rank_lookup[cell])

    work["zone_id"] = work["hex_id"].astype(str).map(zone_id_lookup).fillna("")
    work["zone_size"] = work["hex_id"].astype(str).map(zone_size_lookup).fillna(0).astype(int)
    work["core_distance"] = work["hex_id"].astype(str).map(core_distance_lookup).fillna(0).astype(int)
    work["core_score"] = work["hex_id"].astype(str).map(core_score_lookup).fillna(0.0).astype(float)
    work["center_mass_rank"] = work["hex_id"].astype(str).map(rank_lookup_global).fillna(1).astype(int)

    return work


def _wind_runtime_hex_color(area_share_pct: float, core_score: float) -> str:
    class_spec = _wind_share_class_spec(area_share_pct)
    if float(area_share_pct) <= 0.0:
        intensity = max(0.0, min(1.0, float(core_score))) ** 0.85
    elif float(area_share_pct) >= 80.0:
        intensity = max(0.0, min(1.0, float(core_score))) ** 0.85
    else:
        intensity = (max(0.0, min(1.0, float(core_score))) ** 0.85) * 0.55
    return _mix_hex_colors(str(class_spec["base_color"]), str(class_spec["core_color"]), intensity)


@st.cache_data(show_spinner=False)
def _build_wind_runtime_hex_layer_data(
    combined_geojson_json: str,
    display_geometry_path: str,
) -> pd.DataFrame:
    combined_geojson = json.loads(combined_geojson_json)
    raw_share = runtime_combined_hex_frame(combined_geojson, WIND_POLYGON_HEX_RESOLUTION, [])
    display_geometries = load_h3_display_geometries(display_geometry_path)
    frame = pd.DataFrame({"hex_id": list(display_geometries.keys())})
    if not raw_share.empty and "hex_id" in raw_share.columns:
        frame = frame.merge(
            raw_share[["hex_id", "wind_score"]].rename(columns={"wind_score": "potential_area_share_pct"}),
            on="hex_id",
            how="left",
        )
    frame["potential_area_share_pct"] = frame["potential_area_share_pct"].fillna(0.0).astype(float).clip(lower=0.0, upper=100.0)
    frame["potential_area_share"] = frame["potential_area_share_pct"].div(100.0).round(4)

    class_specs = []
    for share_value in frame["potential_area_share_pct"]:
        class_spec = _wind_share_class_spec(float(share_value))
        class_specs.append((class_spec["id"], class_spec["label"], WIND_SHARE_CLASS_SPECS.index(class_spec)))
    frame["share_class_id"] = [item[0] for item in class_specs]
    frame["share_class_label"] = [item[1] for item in class_specs]
    frame["share_class_index"] = [item[2] for item in class_specs]

    frame = _wind_runtime_hex_core_scores(frame, _wind_r10_neighbor_map(display_geometry_path))
    frame["fill"] = [
        _wind_runtime_hex_color(share_value, core_value)
        for share_value, core_value in zip(frame["potential_area_share_pct"], frame["core_score"])
    ]
    frame["stroke"] = frame["fill"].map(lambda value: _mix_hex_colors(str(value), "#3a3a3a", 0.28))
    return frame.sort_values("hex_id").reset_index(drop=True)


def _wind_runtime_hex_layer_frame(region: dict[str, Any], runtime_result: dict[str, Any]) -> pd.DataFrame:
    combined = runtime_result.get("combined")
    if not isinstance(combined, dict) or combined.get("geojson") is None:
        return pd.DataFrame()
    display_geometry_path = _h3_display_geometry_path(region, WIND_POLYGON_HEX_RESOLUTION)
    if not display_geometry_path:
        return pd.DataFrame()
    return _build_wind_runtime_hex_layer_data(
        json.dumps(combined["geojson"], sort_keys=True, ensure_ascii=False),
        display_geometry_path,
    )


def _wind_runtime_hex_feature_collection(frame: pd.DataFrame, display_geometry_path: str) -> dict[str, Any]:
    display_geometries = load_h3_display_geometries(display_geometry_path)
    features: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        geometry = display_geometries.get(str(row.hex_id))
        if geometry is None:
            continue
        popup = (
            f"<strong>R10 potentialandel</strong><br>"
            f"Hex: {row.hex_id}<br>"
            f"Potentialandel: {float(row.potential_area_share_pct):.1f}%<br>"
            f"Klass: {row.share_class_label}<br>"
            f"KÃ¤rnscore: {float(row.core_score):.2f}<br>"
            f"KÃ¤rnrank i zon: {int(row.center_mass_rank)} av {int(row.zone_size)}"
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": str(row.hex_id),
                    "fill": str(row.fill),
                    "stroke": str(row.stroke),
                    "popup": popup,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _wind_runtime_hex_layer(region: dict[str, Any], runtime_result: dict[str, Any]) -> dict[str, Any] | None:
    display_geometry_path = _h3_display_geometry_path(region, WIND_POLYGON_HEX_RESOLUTION)
    if not display_geometry_path:
        return None
    frame = _wind_runtime_hex_layer_frame(region, runtime_result)
    if frame.empty:
        return None
    return {
        "name": f"R{WIND_POLYGON_HEX_RESOLUTION} potentialandel",
        "feature_collection": _wind_runtime_hex_feature_collection(frame, display_geometry_path),
        "fill_property": "fill",
        "stroke_property": "stroke",
        "legend_items": _wind_share_legend_items(),
        "legend_id": "wind_polygon_hex_share",
        "legend_title": f"R{WIND_POLYGON_HEX_RESOLUTION} potentialandel",
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
        "point_radius": 4,
        "z_index": 410,
    }


def _wind_polygon_preview_state(
    region: dict[str, Any],
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]],
) -> dict[str, Any]:
    runtime_error: str | None = None
    runtime_result: dict[str, Any] = {"groups": {}, "combined": None, "cache_key": None}
    try:
        runtime_result = _wind_runtime_result(ui_params, layer_selection=layer_selection)
    except Exception as exc:
        runtime_error = str(exc)

    layers: list[dict[str, Any]] = []
    hex_layer = None if runtime_error else _wind_runtime_hex_layer(region, runtime_result)
    combined_layer = None if runtime_error else _wind_polygon_combined_layer(runtime_result)
    if hex_layer is not None:
        layers.append(hex_layer)
    if combined_layer is not None:
        layers.append(combined_layer)
    layers.extend(_wind_polygon_source_layers(ui_params, layer_selection=layer_selection))
    if not runtime_error:
        layers.extend(_wind_polygon_group_layers(runtime_result))

    return {
        "layers": layers,
        "runtime_error": runtime_error,
        "runtime_result": runtime_result,
        "active_source_count": sum(len(layer_ids) for layer_ids in normalize_group_layer_map(layer_selection).values()),
        "active_group_count": len(runtime_result.get("groups") or {}),
        "combined_land_share_pct": (runtime_result.get("combined") or {}).get("land_share_pct"),
        "hex_layer_available": bool(hex_layer is not None),
    }


def _wind_polygon_summary_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    runtime_result: dict[str, Any],
) -> pd.DataFrame:
    frame = _wind_runtime_hex_layer_frame(region, runtime_result).copy()
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "hex_id",
                "potential_area_share_pct",
                "share_class_id",
                "share_class_label",
                "fill",
                "wind_score",
                "wind_class",
                "wind_class_label",
                "wind_color",
                "class_km",
                "landscape_type",
            ]
        )

    frame["wind_score"] = frame["potential_area_share_pct"].astype(float)
    frame["wind_class"] = frame["share_class_id"].astype(str)
    frame["wind_class_label"] = frame["share_class_label"].astype(str)
    frame["wind_color"] = frame["fill"].astype(str)

    landscape = _landscape_frame(region, landscape_manifest, WIND_POLYGON_HEX_RESOLUTION)
    context_cols = [column for column in ["hex_id", "class_km", "landscape_type"] if column in landscape.columns]
    if context_cols:
        context = landscape[context_cols].drop_duplicates(subset=["hex_id"])
        frame = frame.merge(context, on="hex_id", how="left")

    if "class_km" not in frame.columns:
        frame["class_km"] = ""
    else:
        frame["class_km"] = frame["class_km"].fillna("").astype(str)
    if "landscape_type" not in frame.columns:
        frame["landscape_type"] = ""
    else:
        frame["landscape_type"] = frame["landscape_type"].fillna("").astype(str)

    return frame.sort_values("hex_id").reset_index(drop=True)


def _wind_group_summary_frame(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    groups, _, _ = load_acceptance_registry()
    selected = normalize_group_layer_map(layer_selection or _selected_wind_layers())
    rows: list[dict[str, Any]] = []
    for group_id, layer_ids in WIND_GROUP_LAYER_DEFAULTS.items():
        threshold_key = GROUP_PARAM_MAP.get(group_id)
        threshold_value = float(ui_params.get(threshold_key, 0.0)) if threshold_key else 0.0
        selected_layer_count = len(selected.get(group_id, []))
        active = selected_layer_count > 0
        rows.append(
            {
                "regelgrupp": GROUP_LABELS.get(group_id, groups[group_id].label if group_id in groups else group_id),
                "analystyp": str(groups[group_id].analysis_kind) if group_id in groups else "-",
                "aktiv": bool(active),
                "troskel_m": "-" if threshold_key is None else int(round(threshold_value)),
                "valda_kallager": int(selected_layer_count),
                "kallager_total": int(len(layer_ids)),
            }
        )
    return pd.DataFrame(rows)


def _wind_source_status_frame() -> pd.DataFrame:
    groups, _, registry_meta = load_acceptance_registry()
    status_df = acceptance_layer_status_table(registry_meta).copy()
    if status_df.empty:
        return status_df

    status_df["group_id"] = status_df["group"].map(
        lambda label: next((group_id for group_id, spec in groups.items() if spec.label == label), label)
    )
    status_df["regelgrupp"] = status_df["group_id"].map(lambda value: GROUP_LABELS.get(str(value), str(value)))
    status_df["klar"] = (
        status_df["geojson_ready"].astype(bool)
        & status_df["source_exists"].astype(bool)
        & status_df["status"].astype(str).eq("ok")
    )
    output = status_df[
        ["regelgrupp", "label", "geometry_family", "feature_count", "status", "klar", "message"]
    ].rename(
        columns={
            "label": "kÃ¤llager",
            "geometry_family": "geometri",
            "feature_count": "objekt",
            "status": "status",
            "message": "notering",
        }
    )
    return output.sort_values(["regelgrupp", "kÃ¤llager"], ascending=[True, True]).reset_index(drop=True)


def _wind_runtime_config_json(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> str:
    selected = normalize_group_layer_map(layer_selection or _selected_wind_layers())
    groups_payload: dict[str, dict[str, Any]] = {}
    for group_id, layer_ids in selected.items():
        if not layer_ids:
            continue
        threshold_key = GROUP_PARAM_MAP.get(group_id)
        threshold_value = float(ui_params.get(threshold_key, 0.0)) if threshold_key else 0.0
        groups_payload[group_id] = {
            "active_layer_ids": list(layer_ids),
            "analysis_value_m": int(round(threshold_value)),
        }
    return json.dumps({"groups": groups_payload}, sort_keys=True, ensure_ascii=False)


def _wind_runtime_result(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    runtime_cfg = _wind_runtime_config_json(ui_params, layer_selection=layer_selection)
    return run_geometry_runtime(runtime_cfg)


def _landscape_layer(
    name: str,
    frame: pd.DataFrame,
    manifest: dict[str, Any],
    factor: str,
    display_geometry_path: str | None,
    mode: str,
) -> dict[str, Any]:
    land_frame = _filter_frame_to_display_geometries(frame, display_geometry_path)
    return {
        "name": name,
        "feature_collection": feature_collection_for_frame(manifest, land_frame, factor, None),
        "fill_property": "factor_fill" if mode == "factor" else "cluster_fill",
        "legend_items": _factor_legend_items() if mode == "factor" else _cluster_legend_items(manifest),
        "legend_id": f"landscape_{mode}_{factor}",
        "legend_title": name,
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
    }


def _landscape_type_layer(
    name: str,
    frame: pd.DataFrame,
    manifest: dict[str, Any],
    display_geometry_path: str | None,
) -> dict[str, Any]:
    land_frame = _filter_frame_to_display_geometries(frame, display_geometry_path)
    return {
        "name": name,
        "feature_collection": landscape_type_feature_collection_for_frame(manifest, land_frame, None),
        "fill_property": "landscape_type_fill",
        "legend_items": _landscape_type_legend_items(manifest),
        "legend_id": "landscape_v10_types",
        "legend_title": name,
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
    }


def _combined_summary(map_state: dict[str, Any], scenario_state: dict[str, Any]) -> None:
    def _wind_share_summary(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["klass", "klass_label", "hexagoner", "medelandel"])
        work = frame.copy()
        work["potential_area_share_pct"] = pd.to_numeric(work["potential_area_share_pct"], errors="coerce").fillna(0.0)
        work["share_class_index"] = pd.to_numeric(work.get("share_class_index"), errors="coerce").fillna(999).astype(int)
        work["share_class_id"] = work["share_class_id"].astype(str)
        work["share_class_label"] = work["share_class_label"].astype(str)
        return (
            work.groupby(["share_class_index", "share_class_id", "share_class_label"], as_index=False)
            .agg(hexagoner=("hex_id", "count"), medelandel=("potential_area_share_pct", "mean"))
            .sort_values(["share_class_index", "medelandel"])
            .assign(medelandel=lambda data: data["medelandel"].round(1))
            .rename(columns={"share_class_id": "klass", "share_class_label": "klass_label"})
            [["klass", "klass_label", "hexagoner", "medelandel"]]
        )

    def _metric_value_text(frame: pd.DataFrame, score_col: str, template: str) -> str:
        if frame.empty:
            return "-"
        value = float(frame[score_col].mean())
        try:
            return template.format(value=value)
        except Exception:
            return f"{value:.1f}"

    def _high_share_pct(frame: pd.DataFrame, class_col: str, high_classes: list[str] | tuple[str, ...] | None) -> float:
        if frame.empty:
            return 0.0
        target_classes = [str(value) for value in (high_classes or ["high", "very_high"])]
        return float(frame[class_col].astype(str).isin(target_classes).mean() * 100.0)

    st.subheader("Tolkning")
    st.caption(f"Scenario: {scenario_state.get('scenario') or '-'}")
    st.metric("Aktiva lager", len(map_state.get("layers") or []))
    st.metric("H3-rollup", f"R{map_state.get('resolution')}")

    for item in map_state.get("potential_frames") or []:
        frame = item["frame"]
        technology = item["technology"]
        score_col = f"{technology}_score"
        class_col = f"{technology}_class"
        high_share = _high_share_pct(frame, class_col, item.get("high_classes"))
        mean_label = str(item.get("mean_label", "MedelpoÃ¤ng"))
        mean_format = str(item.get("mean_format", "{value:.1f}"))
        high_label = str(item.get("high_label", "HÃ¶g potential"))
        with st.expander(item["label"], expanded=True):
            left, right = st.columns(2)
            left.metric(mean_label, _metric_value_text(frame, score_col, mean_format))
            right.metric(high_label, f"{high_share:.1f}%")
            item_resolution = item.get("resolution")
            if item_resolution is not None:
                st.caption(f"H3-rollup: R{int(item_resolution)}")
            if item.get("summary_mode") == "wind_share":
                summary_frame = _wind_share_summary(frame)
            else:
                summary_frame = potential_summary(frame, technology)
            st.dataframe(summary_frame, use_container_width=True, hide_index=True)

    if map_state.get("landscape_active"):
        with st.expander("Landskapsanalys", expanded=False):
            st.write("v9-kluster, v10-landskapstyper och faktorlager visas med samma H3-rollup som potentiallagren.")


def _data_method(region: dict[str, Any]) -> None:
    with st.expander("Data och metod"):
        rows = []
        for key, label in [
            ("scenario_manifest", "Scenarier"),
            ("landscape_manifest", "Landskapsanalys"),
            ("potential_manifest", "Potential"),
        ]:
            path = resolve_repo_path(region.get(key))
            rows.append(
                {
                    "manifest": label,
                    "path": str(path) if path is not None else "",
                    "exists": bool(path and path.exists()),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.json(region)


def _unified_workspace_tab(
    region: dict[str, Any],
    scenario_state: dict[str, Any],
    context: dict[str, Any],
    left_panel: Any | None = None,
    right_panel: Any | None = None,
) -> None:
    landscape_manifest = context["landscape_manifest"]
    potential_manifest = context["potential_manifest"]
    solar_rules = context["solar_rules"]
    factors = factor_columns(landscape_manifest, load_factor_scores(landscape_manifest))

    saved_solar_params = _saved_solar_params()
    solar_defaults = _default_solar_params(solar_rules)
    _prime_solar_builder_state(solar_defaults, saved_solar_params)
    _prime_wind_builder_state(_default_wind_params(), _selected_wind_layers())
    h3_resolution = int(st.session_state.get("combined_h3_resolution", _preferred_h3_resolution(region, 9)))
    opacity = _current_opacity("combined")
    preserve_map_view = True
    map_reset_token = _map_view_reset_token()

    st.session_state.setdefault("show_default_solar", False)
    st.session_state.setdefault("show_user_solar", False)
    st.session_state.setdefault("show_default_wind", False)
    st.session_state.setdefault("show_user_wind", True)
    st.session_state.setdefault("show_landscape_v10", True)
    st.session_state.setdefault("show_landscape_cluster", False)
    st.session_state.setdefault("show_landscape_factor", False)

    show_default_solar = bool(st.session_state.get("show_default_solar"))
    show_user_solar = bool(st.session_state.get("show_user_solar"))
    show_default_wind = bool(st.session_state.get("show_default_wind"))
    show_user_wind = bool(st.session_state.get("show_user_wind"))
    show_v10 = bool(st.session_state.get("show_landscape_v10"))
    show_cluster = bool(st.session_state.get("show_landscape_cluster", False))
    show_factor = bool(st.session_state.get("show_landscape_factor", False))
    selected_factor = str(st.session_state.get("combined_landscape_factor", factors[0] if factors else ""))
    if selected_factor not in factors and factors:
        selected_factor = factors[0]

    wind_selected_layers = _selected_wind_layers()
    wind_ui_params = _default_wind_params()
    wind_controls_applied = False

    if left_panel is not None:
        with left_panel.expander("Landskap", expanded=True):
            show_v10 = st.checkbox("v10 landskapstyper", value=show_v10, key="show_landscape_v10")
            show_cluster = st.checkbox("v9 kluster K=8", value=show_cluster, key="show_landscape_cluster")
            show_factor = st.checkbox("v9 faktorlager", value=show_factor, key="show_landscape_factor")
            selected_factor = st.selectbox(
                "Faktor",
                options=factors,
                index=factors.index(selected_factor) if selected_factor in factors else 0,
                format_func=lambda factor: f"{factor} - {factor_label(landscape_manifest, factor)}",
                disabled=not show_factor,
                key="combined_landscape_factor",
            )

        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "combined", left_panel)

        with left_panel.expander("Potential", expanded=True):
            st.caption("VÃ¤lj vilka lagerfamiljer som ska visas i kartan.")
            show_user_wind = st.checkbox("Egen vindpotential", value=show_user_wind, key="show_user_wind")
            show_default_wind = st.checkbox("Default vindpotential", value=show_default_wind, key="show_default_wind")
            show_user_solar = st.checkbox("Egen solpotential", value=show_user_solar, key="show_user_solar")
            show_default_solar = st.checkbox("Default solpotential", value=show_default_solar, key="show_default_solar")

        with left_panel.expander("Vindpotential", expanded=True):
            st.caption("Bygg vindpotential direkt i samma vy. Kartan visar alltid bÃ¥de den kombinerade polygonen och R10-hexlagret.")
            st.caption("Separat sparning behÃ¶vs inte lÃ¤ngre i den hÃ¤r arbetsvyn.")
            wind_selected_layers, wind_ui_params, wind_controls_applied = _wind_group_controls("wind_unified", language=WIND_CONTROL_LANGUAGE)

        with left_panel.expander("Solpotential", expanded=False):
            st.caption("Bygg solpotential direkt i samma vy. Kartan visar alltid bÃ¥de hexlager och ett sammanhÃ¤ngande polygonlager.")
            if st.button("Ã…terstÃ¤ll sol-default", key="reset_solar_builder_unified"):
                _reset_builder("solar_builder", solar_defaults)
            _builder_slider("solar_builder", "base_score", "BasnivÃ¥", 30.0, 75.0, 1.0, solar_defaults, "StartpoÃ¤ng innan landskapsvillkor lÃ¤ggs till.")
            _builder_slider("solar_builder", "grid_access_bonus", "Infrastruktur/Ã¥tkomst-bonus", 0.0, 20.0, 1.0, solar_defaults, "Proxy fÃ¶r hur mycket nÃ¤rhet till vÃ¤g/elanslutning ska hÃ¶ja solpotentialen.")
            _builder_slider("solar_builder", "everyday_matrix_bonus", "Ã–ppet vardagslandskap", 0.0, 30.0, 1.0, solar_defaults, "Bonus fÃ¶r bredare vardags-/produktionslandskap.")
            _builder_slider("solar_builder", "coastal_penalty", "Kust- och lÃ¥glandsstraff", 0.0, 35.0, 1.0, solar_defaults, "SÃ¤nker potential i kustnÃ¤ra och lÃ¥glÃ¤nta landskap.")
            _builder_slider("solar_builder", "terrain_penalty", "TerrÃ¤ng- och dalstraff", 0.0, 35.0, 1.0, solar_defaults, "SÃ¤nker potential dÃ¤r relief och sprickdalar dominerar.")
            _builder_slider("solar_builder", "protected_penalty", "Skog/habitat-straff", 0.0, 40.0, 1.0, solar_defaults, "SÃ¤nker potential i skyddade skogs- och habitatmiljÃ¶er.")
            _builder_slider("solar_builder", "settlement_penalty", "BosÃ¤ttningsstraff", 0.0, 35.0, 1.0, solar_defaults, "SÃ¤nker potential dÃ¤r bebyggelse och tÃ¤t struktur dominerar.")
            if st.button("Spara solpotential", type="primary", use_container_width=True, key="save_solar_unified"):
                _save_solar_potential(_state_params("solar_builder", solar_defaults), h3_resolution)
                st.success("Solpotential sparad.")

    display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
    solar_params = _state_params("solar_builder", solar_defaults)
    st.session_state["solar_builder_params"] = solar_params
    st.session_state["wind_builder_params"] = wind_ui_params

    layers: list[dict[str, Any]] = []
    potential_frames: list[dict[str, Any]] = []
    unified_notes: list[str] = []

    if show_default_solar:
        default_solar_frame = _default_solar_frame(region, landscape_manifest, potential_manifest, solar_rules, h3_resolution)
        layers.append(_potential_layer(f"Default solpotential R{h3_resolution}", default_solar_frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
        default_solar_polygon = _solar_polygon_layer("Default solyta", default_solar_frame, display_geometry_path, stroke_color="#d97706", fill_color="#d97706")
        if default_solar_polygon is not None:
            layers.append(default_solar_polygon)
        potential_frames.append({"label": "Default solpotential", "technology": "solar", "frame": default_solar_frame, "resolution": h3_resolution})

    if show_user_solar:
        user_solar_frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, solar_params)
        layers.append(_potential_layer(f"Egen solpotential R{h3_resolution}", user_solar_frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
        user_solar_polygon = _solar_polygon_layer("Egen solyta", user_solar_frame, display_geometry_path, stroke_color="#b45309", fill_color="#b45309")
        if user_solar_polygon is not None:
            layers.append(user_solar_polygon)
        potential_frames.append({"label": "Egen solpotential", "technology": "solar", "frame": user_solar_frame, "resolution": h3_resolution})
        unified_notes.append("Solpolygonlagret byggs frÃ¥n de hex som klassas som hÃ¶g eller mycket hÃ¶g solpotential i aktuell H3-upplÃ¶sning.")

    if show_default_wind:
        default_wind_params = _default_wind_params()
        default_layer_selection = normalize_group_layer_map(_default_wind_layer_selection())
        default_wind_source_frame = _wind_source_frame(
            landscape_manifest,
            solar_rules,
            default_wind_params,
            group_layer_selection=default_layer_selection,
        )
        default_wind_frame = _filter_frame_to_display_geometries(
            wind_acceptance_rollup_frame(default_wind_source_frame, h3_resolution, _class_breaks(solar_rules)),
            display_geometry_path,
        )
        layers.append(_potential_layer(f"Default vindpotential R{h3_resolution}", default_wind_frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        layers.append(
            _wind_vector_layer(
                "Default vindpotential vektor",
                default_wind_source_frame,
                _h3_display_geometry_path(region, WIND_SOURCE_RESOLUTION),
                _solar_legend_items(solar_rules),
            )
        )
        potential_frames.append({"label": "Default vindpotential", "technology": "wind", "frame": default_wind_frame, "resolution": h3_resolution})

    custom_wind_preview_state: dict[str, Any] | None = None
    if show_user_wind:
        custom_wind_preview_state = _wind_polygon_preview_state(region, wind_ui_params, wind_selected_layers)
        layers.extend(custom_wind_preview_state["layers"])
        if custom_wind_preview_state["runtime_error"]:
            unified_notes.append(f"Vindruntime kunde inte kÃ¶ras: {custom_wind_preview_state['runtime_error']}")
        else:
            custom_wind_summary = _wind_polygon_summary_frame(region, landscape_manifest, custom_wind_preview_state["runtime_result"])
            potential_frames.append(
                {
                    "label": "Egen vindpotential",
                    "technology": "wind",
                    "frame": custom_wind_summary,
                    "resolution": WIND_POLYGON_HEX_RESOLUTION,
                    "high_classes": ["share_8", "share_9"],
                    "mean_label": "Medelandel",
                    "mean_format": "{value:.1f}%",
                    "high_label": "Andel >65%",
                    "summary_mode": "wind_share",
                }
            )
            unified_notes.append("Vindpotentialen visar bÃ¥de den kombinerade etableringspolygonen och R10-hex med potentialandel frÃ¥n samma geometri.")

    if show_v10 or show_cluster or show_factor:
        landscape_frame = _landscape_frame(region, landscape_manifest, h3_resolution)
        if show_v10:
            layers.append(_landscape_type_layer(f"v10 landskapstyper R{h3_resolution}", landscape_frame, landscape_manifest, display_geometry_path))
        if show_cluster:
            layers.append(_landscape_layer(f"v9 K=8 kluster R{h3_resolution}", landscape_frame, landscape_manifest, factors[0], display_geometry_path, "cluster"))
        if show_factor:
            layers.append(_landscape_layer(f"v9 {selected_factor}: {factor_label(landscape_manifest, selected_factor)} R{h3_resolution}", landscape_frame, landscape_manifest, selected_factor, display_geometry_path, "factor"))

    _render_layers(
        region,
        layers,
        opacity,
        map_state_key=f"{region.get('region_id', 'region')}:workspace" if preserve_map_view else None,
        map_reset_token=map_reset_token,
        opacity_key_prefix="combined",
        note_title="Gemensam potentialvy",
        note_body="Kartan visar bÃ¥de polygoner och hexagoner frÃ¥n samma potentialbyggen. Lager kan slÃ¥s av/pÃ¥ i kartkontrollen.",
    )

    summary_target = right_panel or st.container()
    with summary_target:
        _combined_summary(
            {
                "layers": layers,
                "potential_frames": potential_frames,
                "resolution": h3_resolution,
                "landscape_active": bool(show_v10 or show_cluster or show_factor),
            },
            scenario_state,
        )
        with st.expander("Byggstatus", expanded=False):
            if show_user_solar:
                st.metric("Aktiv solfÃ¶rhandsvisning", "PÃ¥")
                st.caption("Solbygget visas som hexlager plus ett polygonlager som summerar hÃ¶g och mycket hÃ¶g solpotential.")
            if show_user_wind and custom_wind_preview_state is not None:
                left_metric, right_metric = st.columns(2)
                left_metric.metric("Vind: aktiva kÃ¤llager", int(custom_wind_preview_state["active_source_count"]))
                right_metric.metric("Vind: buffertgrupper", int(custom_wind_preview_state["active_group_count"]))
                combined_share = custom_wind_preview_state["combined_land_share_pct"]
                st.metric("Vind: potentiell landandel", "-" if combined_share is None else f"{float(combined_share):.1f}%")
                if wind_controls_applied:
                    st.caption(ui_text("controls_applied", WIND_CONTROL_LANGUAGE))
            for note in unified_notes:
                st.caption(note)
        _data_method(region)


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")
    left_panel, main_panel, right_panel = _workspace_shell()
    region, scenario_state = _render_region_scenario_panel(left_panel)
    context = _load_context(region)

    st.session_state.setdefault("combined_h3_resolution", _preferred_h3_resolution(region, 9))
    h3_resolution = int(st.session_state.get("combined_h3_resolution", _preferred_h3_resolution(region, 9)))
    with main_panel:
        _workspace_header(region, scenario_state, h3_resolution)
        _unified_workspace_tab(region, scenario_state, context, left_panel, right_panel)


if __name__ == "__main__":
    main()


