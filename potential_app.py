from __future__ import annotations

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

from potential_model.geometry import load_h3_display_geometries  # noqa: E402
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
    critical_review_items,
    group_analysis_label,
    group_interpretation,
    group_label,
    hexagon_note_items,
    layer_label,
    layer_note,
    ui_text,
)


PAGE_TITLE = "Sol- och vindpotential"
VIEW_OPTIONS = ["Samlad potential", "Bygg solpotential", "Bygg vindpotential"]
ACTIVE_VIEW_KEY = "potential_active_view"
LEGACY_ACTIVE_VIEW_KEY = "active_view"
LEFT_VIEW_WIDGET_KEY = "potential_active_view_left"
MAIN_VIEW_WIDGET_KEY = "potential_active_view_main"
MAP_VIEW_RESET_TOKEN_KEY = "potential_map_view_reset_token"
LEFT_PANEL_OPEN_KEY = "potential_left_panel_open"
RIGHT_PANEL_OPEN_KEY = "potential_right_panel_open"
REGION_SELECT_KEY = "potential_selected_region_id"
WIND_LAYER_SELECTION_KEY = "wind_builder_selected_layers"
WIND_RUNTIME_OVERLAY_KEY = "wind_builder_runtime_overlay_enabled"
WIND_CONTROL_LANGUAGE = "sv"


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


def _valid_view(value: object) -> str:
    text = str(value)
    return text if text in VIEW_OPTIONS else VIEW_OPTIONS[0]


def _active_view() -> str:
    if ACTIVE_VIEW_KEY not in st.session_state and LEGACY_ACTIVE_VIEW_KEY in st.session_state:
        st.session_state[ACTIVE_VIEW_KEY] = _valid_view(st.session_state.get(LEGACY_ACTIVE_VIEW_KEY))
    st.session_state.setdefault(ACTIVE_VIEW_KEY, VIEW_OPTIONS[0])
    return _valid_view(st.session_state.get(ACTIVE_VIEW_KEY))


def _sync_active_view_from_widget(widget_key: str) -> None:
    st.session_state[ACTIVE_VIEW_KEY] = _valid_view(st.session_state.get(widget_key))


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
        if st.button("<" if left_open else ">", key="left_panel_edge_toggle", help="Visa/dölj kartlager"):
            _toggle_panel(LEFT_PANEL_OPEN_KEY)
            st.rerun()
    with right_toggle_col:
        st.markdown('<span id="right-panel-toggle-anchor"></span>', unsafe_allow_html=True)
        if st.button(">" if right_open else "<", key="right_panel_edge_toggle", help="Visa/dölj kontext"):
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
        st.sidebar.caption("Scenariomanifest saknas för vald region.")
        return {"scenario": None, "manifest": None}

    levels = scenario_manifest.get("scenario_levels") or []
    selected = None
    if levels:
        selected = st.sidebar.radio(
            "Scenario",
            options=levels,
            index=levels.index("medium") if "medium" in levels else 0,
            format_func=lambda value: {"low": "Låg", "medium": "Mellan", "high": "Hög"}.get(value, str(value)),
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
            panel.caption("Scenariomanifest saknas för vald region.")
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
                format_func=lambda value: {"low": "Låg", "medium": "Mellan", "high": "Hög"}.get(value, str(value)),
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

    with panel.expander("Region", expanded=True):
        region = _select_region(st)
    with panel.expander("Scenarier", expanded=True):
        scenario_state = _scenario_state(region, st)
    return region, scenario_state


def _metric_header(region: dict[str, Any], scenario_state: dict[str, Any], h3_resolution: int | None = None) -> None:
    st.title(PAGE_TITLE)
    st.caption("Regional v0 för scenarier, solpotential, vindpotential och landskapsanalys.")

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
            <div class="workspace-eyebrow">{region_label} · scenario {scenario_label} · H3 {h3_label}</div>
            <h1>{PAGE_TITLE}</h1>
          </div>
          <div class="workspace-pill">{region.get("nominal_scale", "TBD")} · {region.get("native_crs", "TBD")}</div>
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
        st.info("Solregler saknas för vald region.")
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
            help="Styr genomskinligheten för aktiva hexagonlager i kartan.",
        )


def _map_controls(region: dict[str, Any], key_prefix: str) -> tuple[int, float, bool, int]:
    rollup_col, info_col = st.columns([0.62, 0.38], gap="large")
    with rollup_col:
        h3_resolution = st.radio(
            "H3-rollup",
            options=_available_h3_resolutions(region),
            index=0,
            format_func=lambda value: _h3_option_label(region, value),
            horizontal=True,
            key=f"{key_prefix}_h3_resolution",
        )
    with info_col:
        st.markdown("[Learn more about H3 resolutions](https://h3geo.org/).")
    return int(h3_resolution), _current_opacity(key_prefix), True, _map_view_reset_token()


def _display_mode_control(key_prefix: str) -> str:
    return str(
        st.radio(
            "Visningsläge potential",
            options=["Hexagon", "Vektor", "Båda"],
            index=0,
            horizontal=True,
            key=f"{key_prefix}_display_mode",
            help="Vind kan visas som kandidatvektor från källhex och som H3-rollup. Solvektor kopplas in i senare datasteg.",
        )
    )


def _wants_hex(display_mode: str) -> bool:
    return display_mode in {"Hexagon", "Båda"}


def _wants_vector(display_mode: str) -> bool:
    return display_mode in {"Vektor", "Båda"}


def _map_control_values(region: dict[str, Any], key_prefix: str) -> tuple[int, float, bool, int]:
    available_resolutions = _available_h3_resolutions(region)
    stored_resolution = st.session_state.get(f"{key_prefix}_h3_resolution", available_resolutions[0])
    try:
        h3_resolution = int(stored_resolution)
    except Exception:
        h3_resolution = available_resolutions[0]
    if h3_resolution not in available_resolutions:
        h3_resolution = available_resolutions[0]
    return h3_resolution, _current_opacity(key_prefix), True, _map_view_reset_token()


def _map_panel_controls(region: dict[str, Any], key_prefix: str, panel: Any | None) -> tuple[int, float, bool, int]:
    if panel is None:
        return _map_control_values(region, key_prefix)

    with panel.expander("H3 resolution", expanded=True):
        h3_resolution = st.radio(
            "H3-rollup",
            options=_available_h3_resolutions(region),
            index=0,
            format_func=lambda value: _h3_option_label(region, value),
            horizontal=False,
            key=f"{key_prefix}_h3_resolution",
        )
        st.markdown("[Learn more about H3 resolutions](https://h3geo.org/).")
    return int(h3_resolution), _current_opacity(key_prefix), True, _map_view_reset_token()


def _display_mode_value(key_prefix: str) -> str:
    value = str(st.session_state.get(f"{key_prefix}_display_mode", "Hexagon"))
    return value if value in {"Hexagon", "Vektor", "BÃ¥da", "Båda"} else "Hexagon"


def _display_mode_panel(key_prefix: str, panel: Any | None) -> str:
    if panel is None:
        return _display_mode_value(key_prefix)
    with panel.expander("Potentialläge", expanded=False):
        return str(
            st.radio(
                "Potentialläge",
                options=["Hexagon", "Vektor", "Båda"],
                index=0,
                horizontal=True,
                key=f"{key_prefix}_display_mode",
                help="Vind kan visas som kandidatvektor från källhex och som H3-rollup. Solvektor kopplas in i senare datasteg.",
            )
        )


def _mode_wants_hex(display_mode: str) -> bool:
    return display_mode in {"Hexagon", "BÃ¥da", "Båda"}


def _mode_wants_vector(display_mode: str) -> bool:
    return display_mode in {"Vektor", "BÃ¥da", "Båda"}


def _vector_placeholder(layer_names: list[str]) -> None:
    if not layer_names:
        return
    names = ", ".join(layer_names)
    st.warning(
        f"Vektorlager är inte inkopplade ännu för: {names}. "
        "Den här vyn är reserverad för detaljerad vektorpotential som senare aggregeras till H3."
    )


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
        {"label": str(item.get("label", item.get("id", "Okänd"))), "color": str(item.get("color", "#999999"))}
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
    labels = ["≤ -2", "-1", "0", "1", "≥ 2"]
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
    _builder_slider("wind_builder", "settlement_distance_m", "Minsta avstånd till boende", 100.0, 3000.0, 50.0, defaults, "Större avstånd ger hårdare bebyggelsestraff.")
    _builder_slider("wind_builder", "road_distance_m", "Minsta avstånd till vägar", 50.0, 2000.0, 25.0, defaults, "Större avstånd ger hårdare transport-/bebyggelsestraff.")
    _builder_slider("wind_builder", "grid_max_distance_m", "Max avstånd till elinfrastruktur", 500.0, 15000.0, 250.0, defaults, "Större tillåtet avstånd gör fler lägen tekniskt möjliga.")
    _builder_slider("wind_builder", "protected_buffer_m", "Buffert skyddade områden", 0.0, 2000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar skyddade natur- och habitatlager.")
    _builder_slider("wind_builder", "coastal_buffer_m", "Buffert kust/strand", 0.0, 1000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar kustzon och strandskydd.")
    _builder_slider("wind_builder", "landscape_sensitivity_percent", "Landskapskänslighet", 0.0, 120.0, 5.0, defaults, "Viktar hur starkt landskapsrollerna ska bromsa vindpotentialen.")
    with st.expander("Avancerade restriktioner"):
        _builder_slider("wind_builder", "culture_buffer_m", "Buffert kulturmiljöer", 0.0, 1500.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar värdefulla kulturmiljöer.")
        _builder_slider("wind_builder", "aviation_approach_buffer_m", "Buffert inflygningszoner", 0.0, 3000.0, 100.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar flygplatsens inflygningszoner.")
        _builder_slider("wind_builder", "aviation_bird_distance_m", "Minsta avstånd fågelkollision", 0.0, 4000.0, 100.0, defaults, "0 stänger av gruppen. Högre värden ger distance-conflict mot fågelkollisionszoner.")
        _builder_slider("wind_builder", "military_buffer_m", "Buffert militära områden", 0.0, 2000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar militära områden.")
        st.dataframe(wind_acceptance_group_summary(), use_container_width=True, hide_index=True, height=220)


def _save_solar_potential(params: dict[str, float], resolution: int) -> None:
    st.session_state["saved_solar_potential"] = {
        "params": dict(params),
        "preview_resolution": int(resolution),
    }
    st.session_state["show_user_solar"] = True


def _save_wind_potential(
    ui_params: dict[str, float],
    resolution: int,
    layer_selection: dict[str, list[str]] | None = None,
) -> None:
    st.session_state["saved_wind_potential"] = {
        "ui_params": dict(ui_params),
        "preview_resolution": int(resolution),
        "layer_selection": normalize_group_layer_map(layer_selection or _selected_wind_layers()),
    }
    st.session_state["show_user_wind"] = True


def _saved_solar_params() -> dict[str, float] | None:
    saved = st.session_state.get("saved_solar_potential")
    if not isinstance(saved, dict):
        return None
    params = saved.get("params")
    return dict(params) if isinstance(params, dict) else None


def _saved_wind_params() -> dict[str, float] | None:
    saved = st.session_state.get("saved_wind_potential")
    if not isinstance(saved, dict):
        return None
    params = saved.get("ui_params")
    return dict(params) if isinstance(params, dict) else None


def _saved_wind_layer_selection() -> dict[str, list[str]] | None:
    saved = st.session_state.get("saved_wind_potential")
    if not isinstance(saved, dict):
        return None
    selection = saved.get("layer_selection")
    if not isinstance(selection, dict):
        return None
    return normalize_group_layer_map(selection)


def _set_active_view(view: str) -> None:
    st.session_state[ACTIVE_VIEW_KEY] = _valid_view(view)


def _render_layers(
    region: dict[str, Any],
    layers: list[dict[str, Any]],
    opacity: float,
    map_state_key: str | None = None,
    map_reset_token: int = 0,
    opacity_key_prefix: str | None = None,
) -> None:
    if not layers:
        st.info("Välj minst ett kartlager.")
        return
    map_html = build_layered_hex_map_html(
        layers,
        center=list(region.get("default_map_center", [55.14, 14.92])),
        zoom=int(region.get("default_zoom", 9)),
        bounds=region.get("default_map_bounds"),
        fill_opacity=opacity,
        map_state_key=map_state_key,
        map_reset_token=map_reset_token,
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
        help="Kör geometri-runtime och lägg till grupplager plus kombinerad acceptansyta i vektorvyn.",
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
                    "name": f"Källa: {layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label)} ({group_label})",
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
            "label": "källager",
            "geometry_family": "geometri",
            "feature_count": "objekt",
            "status": "status",
            "message": "notering",
        }
    )
    return output.sort_values(["regelgrupp", "källager"], ascending=[True, True]).reset_index(drop=True)


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


def _wind_runtime_layers(
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups, _, _ = load_acceptance_registry()
    runtime_cfg = _wind_runtime_config_json(ui_params, layer_selection=layer_selection)
    runtime = run_geometry_runtime(runtime_cfg)
    layers: list[dict[str, Any]] = []

    for group_id, group_meta in (runtime.get("groups") or {}).items():
        geojson = group_meta.get("geojson")
        if not geojson:
            continue
        group_label_text = GROUP_LABELS.get(group_id, groups[group_id].label if group_id in groups else group_id)
        if group_id in groups:
            group_label_text = group_label(groups[group_id], WIND_CONTROL_LANGUAGE, groups[group_id].label)
        group_color = _rgb_to_hex(groups[group_id].group_color) if group_id in groups else "#4d4d4d"
        opacity = _wind_group_opacity(group_id)
        layers.append(
            {
                "name": f"Grupp: {group_label_text}",
                "feature_collection": geojson,
                "fill_property": "fill",
                "legend_items": [],
                "legend_id": f"wind_runtime_group_{group_id}",
                "legend_title": "",
                "default_visible": False,
                "stroke_color": group_color,
                "fill_color": group_color,
                "stroke_opacity": max(min(opacity * 0.95, 1.0), 0.0),
                "fill_opacity": max(min(opacity * 0.32, 1.0), 0.0),
                "weight": 2.2,
                "point_radius": 6,
                "use_global_opacity": False,
            }
        )

    combined = runtime.get("combined") if isinstance(runtime.get("combined"), dict) else None
    if combined and combined.get("geojson"):
        layers.append(
            {
                "name": ui_text("combined_overlay_name", WIND_CONTROL_LANGUAGE),
                "feature_collection": combined["geojson"],
                "fill_property": "fill",
                "legend_items": [],
                "legend_id": "wind_runtime_combined",
                "legend_title": "",
                "default_visible": True,
                "stroke_color": "#c4322b",
                "fill_color": "#c4322b",
                "stroke_opacity": 0.72,
                "fill_opacity": 0.08,
                "weight": 1.5,
                "point_radius": 6,
                "use_global_opacity": False,
            }
        )

    meta = {
        "cache_key": runtime.get("cache_key"),
        "group_count": len(runtime.get("groups") or {}),
        "combined_land_share_pct": (combined or {}).get("land_share_pct"),
    }
    return layers, meta


def _wind_builder_summary_panel(
    frame: pd.DataFrame,
    source_frame: pd.DataFrame,
    ui_params: dict[str, float],
    selected_layers: dict[str, list[str]],
    h3_resolution: int,
    runtime_meta: dict[str, Any] | None = None,
    runtime_enabled: bool = False,
    runtime_error: str | None = None,
) -> None:
    proto_tab, review_tab, data_tab = st.tabs(["Prototyp", "Modellgranskning", "Datastatus"])
    with proto_tab:
        _potential_detail_panel("Osparad vindförhandsvisning", frame, "wind", h3_resolution)
        vector_stats = wind_candidate_summary(source_frame)
        st.metric(f"Kandidatytor R{WIND_SOURCE_RESOLUTION}", vector_stats["candidate_cells"])
        st.metric("Kandidatandel", f"{vector_stats['candidate_share']:.1f}%")
        if runtime_enabled:
            if runtime_error:
                st.warning(f"Geometri-runtime kunde inte köras: {runtime_error}")
            elif runtime_meta:
                left, right = st.columns(2)
                left.metric("Runtime-grupper", int(runtime_meta.get("group_count") or 0))
                land_share = runtime_meta.get("combined_land_share_pct")
                right.metric("Kombinerad landandel", "-" if land_share is None else f"{float(land_share):.1f}%")
                if runtime_meta.get("cache_key"):
                    st.caption(f"Runtime-cache: {runtime_meta['cache_key']}")
            else:
                st.caption("Geometri-runtime är påslagen men returnerade inga lager för nuvarande urval.")
        else:
            st.caption("Geometri-runtimeoverlay är avstängd.")
        with st.expander("Aktiva regelgrupper", expanded=False):
            st.dataframe(_wind_group_summary_frame(ui_params, layer_selection=selected_layers), use_container_width=True, hide_index=True, height=240)
        with st.expander("Aktiva vindparametrar"):
            st.json(ui_params)
        with st.expander("Migrerad regelgruppslogik"):
            st.dataframe(wind_acceptance_group_summary(), use_container_width=True, hide_index=True)

    with review_tab:
        st.subheader("Kritisk genomgång")
        for item in critical_review_items("sv"):
            st.write(f"- {item}")
        st.subheader("Hexagonsnot")
        for item in hexagon_note_items("sv"):
            st.write(f"- {item}")

    with data_tab:
        st.dataframe(_wind_source_status_frame(), use_container_width=True, hide_index=True, height=300)


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
    }


def _combined_summary(map_state: dict[str, Any], scenario_state: dict[str, Any]) -> None:
    st.subheader("Tolkning")
    st.caption(f"Scenario: {scenario_state.get('scenario') or '-'}")
    st.metric("Aktiva lager", len(map_state.get("layers") or []))
    st.metric("H3-rollup", f"R{map_state.get('resolution')}")

    for item in map_state.get("potential_frames") or []:
        frame = item["frame"]
        technology = item["technology"]
        score_col = f"{technology}_score"
        class_col = f"{technology}_class"
        high_share = float(frame[class_col].isin(["high", "very_high"]).mean() * 100.0) if not frame.empty else 0.0
        with st.expander(item["label"], expanded=True):
            left, right = st.columns(2)
            left.metric("Medelpoäng", f"{frame[score_col].mean():.1f}" if not frame.empty else "-")
            right.metric("Hög potential", f"{high_share:.1f}%")
            st.dataframe(potential_summary(frame, technology), use_container_width=True, hide_index=True)

    if map_state.get("landscape_active"):
        with st.expander("Landskapsanalys", expanded=False):
            st.write("v9-kluster, v10-landskapstyper och faktorlager visas med samma H3-rollup som potentiallagren.")


def _potential_detail_panel(label: str, frame: pd.DataFrame, technology: str, resolution: int) -> None:
    score_col = f"{technology}_score"
    class_col = f"{technology}_class"
    high_share = float(frame[class_col].isin(["high", "very_high"]).mean() * 100.0) if not frame.empty else 0.0
    st.subheader(label)
    st.metric("H3-rollup", f"R{resolution}")
    left, right = st.columns(2)
    left.metric("Medelpoäng", f"{frame[score_col].mean():.1f}" if not frame.empty else "-")
    right.metric("Hög potential", f"{high_share:.1f}%")
    with st.expander("Potentialklasser", expanded=True):
        st.dataframe(potential_summary(frame, technology), use_container_width=True, hide_index=True)
    with st.expander("Per landskapstyp", expanded=True):
        st.dataframe(potential_by_landscape(frame, technology), use_container_width=True, hide_index=True)


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


def _combined_layer_controls(
    panel: Any | None,
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    factors: list[str],
    saved_solar_params: dict[str, float] | None,
    saved_wind_ui_params: dict[str, float] | None,
) -> dict[str, Any]:
    if panel is None:
        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_control_values(region, "combined")
        selected_factor = str(st.session_state.get("combined_landscape_factor", factors[0] if factors else ""))
        if selected_factor not in factors and factors:
            selected_factor = factors[0]
        return {
            "h3_resolution": h3_resolution,
            "opacity": opacity,
            "preserve_map_view": preserve_map_view,
            "map_reset_token": map_reset_token,
            "display_mode": _display_mode_value("combined"),
            "show_default_solar": bool(st.session_state.get("show_default_solar", True)),
            "show_user_solar": bool(st.session_state.get("show_user_solar", False)),
            "show_default_wind": bool(st.session_state.get("show_default_wind", False)),
            "show_user_wind": bool(st.session_state.get("show_user_wind", False)),
            "show_v10": bool(st.session_state.get("show_landscape_v10", False)),
            "show_cluster": bool(st.session_state.get("show_landscape_cluster", False)),
            "show_factor": bool(st.session_state.get("show_landscape_factor", False)),
            "selected_factor": selected_factor,
        }

    h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "combined", panel)
    display_mode = _display_mode_panel("combined", panel)

    with panel.expander("Potential", expanded=True):
        show_default_solar = st.checkbox("Default solpotential", value=True, key="show_default_solar")
        show_user_solar = st.checkbox("Egen solpotential", value=False, key="show_user_solar")
        st.caption("Egen sol: sparad" if saved_solar_params is not None else "Egen sol: ej sparad")
        show_default_wind = st.checkbox("Default vindpotential", value=False, key="show_default_wind")
        show_user_wind = st.checkbox("Egen vindpotential", value=False, key="show_user_wind")
        st.caption("Egen vind: sparad" if saved_wind_ui_params is not None else "Egen vind: ej sparad")

    with panel.expander("Landskap", expanded=True):
        show_v10 = st.checkbox("v10 landskapstyper", value=False, key="show_landscape_v10")
        show_cluster = st.checkbox("v9 kluster K=8", value=False, key="show_landscape_cluster")
        show_factor = st.checkbox("v9 faktorlager", value=False, key="show_landscape_factor")
        selected_factor = st.selectbox(
            "Faktor",
            options=factors,
            index=0,
            format_func=lambda factor: f"{factor} - {factor_label(landscape_manifest, factor)}",
            disabled=not show_factor,
            key="combined_landscape_factor",
        )
    return {
        "h3_resolution": int(h3_resolution),
        "opacity": float(opacity),
        "preserve_map_view": bool(preserve_map_view),
        "map_reset_token": map_reset_token,
        "display_mode": display_mode,
        "show_default_solar": bool(show_default_solar),
        "show_user_solar": bool(show_user_solar),
        "show_default_wind": bool(show_default_wind),
        "show_user_wind": bool(show_user_wind),
        "show_v10": bool(show_v10),
        "show_cluster": bool(show_cluster),
        "show_factor": bool(show_factor),
        "selected_factor": str(selected_factor),
    }


def _combined_tab(
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

    h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "combined", left_panel)
    display_mode = _display_mode_panel("combined", left_panel)
    display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
    saved_solar_params = _saved_solar_params()
    saved_wind_ui_params = _saved_wind_params()
    saved_wind_layer_selection = _saved_wind_layer_selection()

    if left_panel is not None:
        with left_panel.expander("Potential", expanded=True):
            show_default_solar = st.checkbox("Default solpotential", value=True, key="show_default_solar")
            show_user_solar = st.checkbox("Egen solpotential", value=False, key="show_user_solar")
            st.caption("Egen sol: sparad" if saved_solar_params is not None else "Egen sol: ej sparad")
            show_default_wind = st.checkbox("Default vindpotential", value=False, key="show_default_wind")
            show_user_wind = st.checkbox("Egen vindpotential", value=False, key="show_user_wind")
            st.caption("Egen vind: sparad" if saved_wind_ui_params is not None else "Egen vind: ej sparad")
        with left_panel.expander("Landskap", expanded=True):
            show_v10 = st.checkbox("v10 landskapstyper", value=False, key="show_landscape_v10")
            show_cluster = st.checkbox("v9 kluster K=8", value=False, key="show_landscape_cluster")
            show_factor = st.checkbox("v9 faktorlager", value=False, key="show_landscape_factor")
            selected_factor = st.selectbox(
                "Faktor för v9 faktorlager",
                options=factors,
                index=0,
                format_func=lambda factor: f"{factor} - {factor_label(landscape_manifest, factor)}",
                disabled=not show_factor,
                key="combined_landscape_factor",
            )

    else:
        show_default_solar = bool(st.session_state.get("show_default_solar", True))
        show_user_solar = bool(st.session_state.get("show_user_solar", False))
        show_default_wind = bool(st.session_state.get("show_default_wind", False))
        show_user_wind = bool(st.session_state.get("show_user_wind", False))
        show_v10 = bool(st.session_state.get("show_landscape_v10", False))
        show_cluster = bool(st.session_state.get("show_landscape_cluster", False))
        show_factor = bool(st.session_state.get("show_landscape_factor", False))
        selected_factor = str(st.session_state.get("combined_landscape_factor", factors[0] if factors else ""))
        if selected_factor not in factors and factors:
            selected_factor = factors[0]

    layers: list[dict[str, Any]] = []
    potential_frames: list[dict[str, Any]] = []
    vector_placeholders: list[str] = []

    if show_user_solar and saved_solar_params is None:
        st.error("Egen solpotential saknas. Gå till Bygg solpotential och tryck Spara solpotential när du är nöjd.")
        st.button("Gå till Bygg solpotential", key="missing_solar_go_builder", on_click=_set_active_view, args=("Bygg solpotential",))

    if show_user_wind and saved_wind_ui_params is None:
        st.error("Egen vindpotential saknas. Gå till Bygg vindpotential och tryck Spara vindpotential när du är nöjd.")
        st.button("Gå till Bygg vindpotential", key="missing_wind_go_builder", on_click=_set_active_view, args=("Bygg vindpotential",))

    if show_default_solar:
        if _mode_wants_hex(display_mode):
            frame = _default_solar_frame(region, landscape_manifest, potential_manifest, solar_rules, h3_resolution)
            layers.append(_potential_layer(f"Default solpotential R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Default solpotential", "technology": "solar", "frame": frame})
        if _mode_wants_vector(display_mode):
            vector_placeholders.append("default solpotential")

    if show_user_solar and saved_solar_params is not None:
        if _mode_wants_hex(display_mode):
            frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, saved_solar_params)
            layers.append(_potential_layer(f"Egen solpotential R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Egen solpotential", "technology": "solar", "frame": frame})
        if _mode_wants_vector(display_mode):
            vector_placeholders.append("sparad egen solpotential")

    if show_default_wind:
        ui_params = _default_wind_params()
        default_layer_selection = normalize_group_layer_map(_default_wind_layer_selection())
        source_frame = _wind_source_frame(
            landscape_manifest,
            solar_rules,
            ui_params,
            group_layer_selection=default_layer_selection,
        )
        frame = _filter_frame_to_display_geometries(
            wind_acceptance_rollup_frame(source_frame, h3_resolution, _class_breaks(solar_rules)),
            display_geometry_path,
        )
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Default vindpotential R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        if _mode_wants_vector(display_mode):
            layers.extend(_wind_source_vector_layers(ui_params, layer_selection=default_layer_selection))
            layers.append(_wind_vector_layer("Default vindpotential vektor", source_frame, _h3_display_geometry_path(region, WIND_SOURCE_RESOLUTION), _solar_legend_items(solar_rules)))
        potential_frames.append({"label": "Default vindpotential", "technology": "wind", "frame": frame})

    if show_user_wind and saved_wind_ui_params is not None:
        user_layer_selection = normalize_group_layer_map(saved_wind_layer_selection or _selected_wind_layers())
        source_frame = _wind_source_frame(
            landscape_manifest,
            solar_rules,
            saved_wind_ui_params,
            group_layer_selection=user_layer_selection,
        )
        frame = _filter_frame_to_display_geometries(
            wind_acceptance_rollup_frame(source_frame, h3_resolution, _class_breaks(solar_rules)),
            display_geometry_path,
        )
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Egen vindpotential R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        if _mode_wants_vector(display_mode):
            layers.extend(_wind_source_vector_layers(saved_wind_ui_params, layer_selection=user_layer_selection))
            layers.append(_wind_vector_layer("Egen vindpotential vektor", source_frame, _h3_display_geometry_path(region, WIND_SOURCE_RESOLUTION), _solar_legend_items(solar_rules)))
        potential_frames.append({"label": "Egen vindpotential", "technology": "wind", "frame": frame})

    if show_v10 or show_cluster or show_factor:
        landscape_frame = _landscape_frame(region, landscape_manifest, h3_resolution)
        if show_v10:
            layers.append(_landscape_type_layer(f"v10 landskapstyper R{h3_resolution}", landscape_frame, landscape_manifest, display_geometry_path))
        if show_cluster:
            layers.append(_landscape_layer(f"v9 K=8 kluster R{h3_resolution}", landscape_frame, landscape_manifest, factors[0], display_geometry_path, "cluster"))
        if show_factor:
            layers.append(_landscape_layer(f"v9 {selected_factor}: {factor_label(landscape_manifest, selected_factor)} R{h3_resolution}", landscape_frame, landscape_manifest, selected_factor, display_geometry_path, "factor"))

    _vector_placeholder(vector_placeholders)
    _render_layers(
        region,
        layers,
        opacity,
        map_state_key=f"{region.get('region_id', 'region')}:combined" if preserve_map_view else None,
        map_reset_token=map_reset_token,
        opacity_key_prefix="combined",
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
        _data_method(region)


def _solar_builder_tab(
    region: dict[str, Any],
    context: dict[str, Any],
    left_panel: Any | None = None,
    right_panel: Any | None = None,
) -> None:
    landscape_manifest = context["landscape_manifest"]
    solar_rules = context["solar_rules"]
    defaults = _default_solar_params(solar_rules)
    if left_panel is not None or right_panel is not None:
        if left_panel is not None:
            with left_panel:
                st.header("Bygg solpotential")
                st.caption("Justera reglagen och spara när kartbilden är användbar.")
                if st.button("Återställ sol-default", key="reset_solar_builder"):
                    _reset_builder("solar_builder", defaults)
                _builder_slider("solar_builder", "base_score", "Basnivå", 30.0, 75.0, 1.0, defaults, "Startpoäng innan landskapsvillkor läggs till.")
                _builder_slider("solar_builder", "grid_access_bonus", "Infrastruktur/åtkomst-bonus", 0.0, 20.0, 1.0, defaults, "Proxy för hur mycket närhet till väg/elanslutning ska höja solpotentialen.")
                _builder_slider("solar_builder", "everyday_matrix_bonus", "Öppet vardagslandskap", 0.0, 30.0, 1.0, defaults, "Bonus för bredare vardags-/produktionslandskap.")
                _builder_slider("solar_builder", "coastal_penalty", "Kust- och låglandsstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential i kustnära och låglänta landskap.")
                _builder_slider("solar_builder", "terrain_penalty", "Terräng- och dalstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential där relief och sprickdalar dominerar.")
                _builder_slider("solar_builder", "protected_penalty", "Skog/habitat-straff", 0.0, 40.0, 1.0, defaults, "Sänker potential i skyddade skogs- och habitatmiljöer.")
                _builder_slider("solar_builder", "settlement_penalty", "Bosättningsstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential där bebyggelse och tät struktur dominerar.")
        params = _state_params("solar_builder", defaults)
        st.session_state["solar_builder_params"] = params
        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "solar_builder_preview", left_panel)
        display_mode = _display_mode_panel("solar_builder_preview", left_panel)
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, params)
        if _mode_wants_vector(display_mode):
            _vector_placeholder(["egen solpotential"])
        layers = []
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad solförhandsvisning R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(
            region,
            layers,
            opacity,
            map_state_key=f"{region.get('region_id', 'region')}:solar_builder" if preserve_map_view else None,
            map_reset_token=map_reset_token,
            opacity_key_prefix="solar_builder_preview",
        )
        summary_target = right_panel or st.container()
        with summary_target:
            _potential_detail_panel("Osparad solförhandsvisning", frame, "solar", h3_resolution)
            with st.expander("Aktiva solparametrar"):
                st.json(params)
            if st.button("Spara solpotential", type="primary", use_container_width=True):
                _save_solar_potential(params, h3_resolution)
                st.success("Solpotential sparad. Den kan nu togglas på i Samlad potential.")
        return

    st.subheader("Bygg solpotential")
    st.caption("Justera reglagen för att se hur mer eller mindre solpotential skapas i H3-ytan.")

    if st.button("Återställ sol-default", key="reset_solar_builder"):
        _reset_builder("solar_builder", defaults)

    control_col, map_col, info_col = st.columns([0.24, 0.50, 0.26], gap="large")
    with control_col:
        _builder_slider("solar_builder", "base_score", "Basnivå", 30.0, 75.0, 1.0, defaults, "Startpoäng innan landskapsvillkor läggs till.")
        _builder_slider("solar_builder", "grid_access_bonus", "Infrastruktur/åtkomst-bonus", 0.0, 20.0, 1.0, defaults, "Proxy för hur mycket närhet till väg/elanslutning ska höja solpotentialen.")
        _builder_slider("solar_builder", "everyday_matrix_bonus", "Öppet vardagslandskap", 0.0, 30.0, 1.0, defaults, "Bonus för bredare vardags-/produktionslandskap.")
        _builder_slider("solar_builder", "coastal_penalty", "Kust- och låglandsstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential i kustnära och låglänta landskap.")
        _builder_slider("solar_builder", "terrain_penalty", "Terräng- och dalstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential där relief och sprickdalar dominerar.")
        _builder_slider("solar_builder", "protected_penalty", "Skog/habitat-straff", 0.0, 40.0, 1.0, defaults, "Sänker potential i skyddade skogs- och habitatmiljöer.")
        _builder_slider("solar_builder", "settlement_penalty", "Bosättningsstraff", 0.0, 35.0, 1.0, defaults, "Sänker potential där bebyggelse och tät struktur dominerar.")

    params = _state_params("solar_builder", defaults)
    st.session_state["solar_builder_params"] = params
    with map_col:
        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_controls(region, "solar_builder_preview")
        display_mode = _display_mode_control("solar_builder_preview")
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, params)
        if _mode_wants_vector(display_mode):
            _vector_placeholder(["egen solpotential"])
        layers = []
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad solförhandsvisning R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(
            region,
            layers,
            opacity,
            map_state_key=f"{region.get('region_id', 'region')}:solar_builder" if preserve_map_view else None,
            map_reset_token=map_reset_token,
            opacity_key_prefix="solar_builder_preview",
        )
    with info_col:
        with st.container(border=True):
            _potential_detail_panel("Osparad solförhandsvisning", frame, "solar", h3_resolution)
            with st.expander("Aktiva solparametrar"):
                st.json(params)

    st.divider()
    if st.button("Spara solpotential", type="primary", use_container_width=True, key="save_solar_main_under_map"):
        _save_solar_potential(params, h3_resolution)
        st.success("Solpotential sparad. Den kan nu togglas på i Samlad potential.")


def _wind_builder_tab(
    region: dict[str, Any],
    context: dict[str, Any],
    left_panel: Any | None = None,
    right_panel: Any | None = None,
) -> None:
    landscape_manifest = context["landscape_manifest"]
    solar_rules = context["solar_rules"]
    selected_layers: dict[str, list[str]] = _selected_wind_layers()
    ui_params: dict[str, float] = _default_wind_params()
    controls_applied = False
    if left_panel is not None or right_panel is not None:
        if left_panel is not None:
            with left_panel:
                selected_layers, ui_params, controls_applied = _wind_group_controls("wind_builder_panel", language=WIND_CONTROL_LANGUAGE)
        runtime_overlay_enabled = True
        st.session_state["wind_builder_params"] = ui_params
        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "wind_builder_preview", left_panel)
        display_mode = _display_mode_panel("wind_builder_preview", left_panel)
        runtime_overlay_enabled = _mode_wants_vector(display_mode)
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        source_frame = _wind_source_frame(landscape_manifest, solar_rules, ui_params, group_layer_selection=selected_layers)
        frame = _filter_frame_to_display_geometries(
            wind_acceptance_rollup_frame(source_frame, h3_resolution, _class_breaks(solar_rules)),
            display_geometry_path,
        )
        runtime_meta: dict[str, Any] | None = None
        runtime_error: str | None = None
        layers = []
        if _mode_wants_vector(display_mode):
            layers.extend(_wind_source_vector_layers(ui_params, layer_selection=selected_layers))
            h3_vector_layer = _wind_vector_layer(
                "H3-kandidatytor (scoremodell)",
                source_frame,
                _h3_display_geometry_path(region, WIND_SOURCE_RESOLUTION),
                _solar_legend_items(solar_rules),
            )
            if runtime_overlay_enabled:
                h3_vector_layer["default_visible"] = False
            layers.append(h3_vector_layer)
            if runtime_overlay_enabled:
                with st.spinner("Kör geometri-runtime för vindlager..."):
                    try:
                        runtime_layers, runtime_meta = _wind_runtime_layers(ui_params, layer_selection=selected_layers)
                        layers.extend(runtime_layers)
                    except Exception as exc:
                        runtime_error = str(exc)
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad vindförhandsvisning R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(
            region,
            layers,
            opacity,
            map_state_key=f"{region.get('region_id', 'region')}:wind_builder" if preserve_map_view else None,
            map_reset_token=map_reset_token,
            opacity_key_prefix="wind_builder_preview",
        )
        save_col, _ = st.columns([0.34, 0.66], gap="small")
        with save_col:
            if st.button("Spara vindpotential", type="primary", use_container_width=True, key="wind_builder_save_under_map_panel"):
                _save_wind_potential(ui_params, h3_resolution, layer_selection=selected_layers)
                st.success("Vindpotential sparad. Den kan nu togglas på i Samlad potential.")
        summary_target = right_panel or st.container()
        with summary_target:
            _potential_detail_panel("Osparad vindförhandsvisning", frame, "wind", h3_resolution)
            vector_stats = wind_candidate_summary(source_frame)
            st.metric(f"Kandidatytor R{WIND_SOURCE_RESOLUTION}", vector_stats["candidate_cells"])
            st.metric("Kandidatandel", f"{vector_stats['candidate_share']:.1f}%")
            if controls_applied:
                st.caption(ui_text("controls_applied", WIND_CONTROL_LANGUAGE))
            if runtime_overlay_enabled:
                if runtime_error:
                    st.warning(f"Geometri-runtime kunde inte köras: {runtime_error}")
                elif runtime_meta:
                    left_metric, right_metric = st.columns(2)
                    left_metric.metric("Runtime-grupper", int(runtime_meta.get("group_count") or 0))
                    land_share = runtime_meta.get("combined_land_share_pct")
                    right_metric.metric("Kombinerad landandel", "-" if land_share is None else f"{float(land_share):.1f}%")
                    if runtime_meta.get("cache_key"):
                        st.caption(f"Runtime-cache: {runtime_meta['cache_key']}")
                else:
                    st.caption("Geometri-runtime är påslagen men returnerade inga lager för nuvarande urval.")
            else:
                st.caption("Geometri-runtimeoverlay är avstängd.")
            if runtime_overlay_enabled:
                st.caption("Potentiell etableringsyta = landmassa minus valda buffertregler.")
            with st.expander("Aktiva regelgrupper", expanded=False):
                st.dataframe(_wind_group_summary_frame(ui_params, layer_selection=selected_layers), use_container_width=True, hide_index=True, height=240)
            with st.expander("Aktiva vindparametrar"):
                st.json(ui_params)
            with st.expander("Migrerad regelgruppslogik"):
                st.dataframe(wind_acceptance_group_summary(), use_container_width=True, hide_index=True)
            with st.expander("Modellgranskning", expanded=False):
                st.markdown("**Kritisk genomgång**")
                for item in critical_review_items("sv"):
                    st.write(f"- {item}")
                st.markdown("**Hexagonsnot**")
                for item in hexagon_note_items("sv"):
                    st.write(f"- {item}")
            with st.expander("Datastatus vindlager", expanded=False):
                st.dataframe(_wind_source_status_frame(), use_container_width=True, hide_index=True, height=280)
        return

    st.subheader("Bygg vindpotential")

    control_col, map_col, info_col = st.columns([0.24, 0.50, 0.26], gap="large")
    with control_col:
        selected_layers, ui_params, controls_applied = _wind_group_controls("wind_builder_main", language=WIND_CONTROL_LANGUAGE)

    runtime_overlay_enabled = True
    st.session_state["wind_builder_params"] = ui_params
    with map_col:
        h3_resolution, opacity, preserve_map_view, map_reset_token = _map_controls(region, "wind_builder_preview")
        display_mode = _display_mode_control("wind_builder_preview")
        runtime_overlay_enabled = _mode_wants_vector(display_mode)
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        source_frame = _wind_source_frame(landscape_manifest, solar_rules, ui_params, group_layer_selection=selected_layers)
        frame = _filter_frame_to_display_geometries(
            wind_acceptance_rollup_frame(source_frame, h3_resolution, _class_breaks(solar_rules)),
            display_geometry_path,
        )
        runtime_meta: dict[str, Any] | None = None
        runtime_error: str | None = None
        layers = []
        if _mode_wants_vector(display_mode):
            layers.extend(_wind_source_vector_layers(ui_params, layer_selection=selected_layers))
            h3_vector_layer = _wind_vector_layer(
                "H3-kandidatytor (scoremodell)",
                source_frame,
                _h3_display_geometry_path(region, WIND_SOURCE_RESOLUTION),
                _solar_legend_items(solar_rules),
            )
            if runtime_overlay_enabled:
                h3_vector_layer["default_visible"] = False
            layers.append(h3_vector_layer)
            if runtime_overlay_enabled:
                with st.spinner("Kör geometri-runtime för vindlager..."):
                    try:
                        runtime_layers, runtime_meta = _wind_runtime_layers(ui_params, layer_selection=selected_layers)
                        layers.extend(runtime_layers)
                    except Exception as exc:
                        runtime_error = str(exc)
        if _mode_wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad vindförhandsvisning R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(
            region,
            layers,
            opacity,
            map_state_key=f"{region.get('region_id', 'region')}:wind_builder" if preserve_map_view else None,
            map_reset_token=map_reset_token,
            opacity_key_prefix="wind_builder_preview",
        )
        save_col, _ = st.columns([0.34, 0.66], gap="small")
        with save_col:
            if st.button("Spara vindpotential", type="primary", use_container_width=True, key="wind_builder_save_under_map_main"):
                _save_wind_potential(ui_params, h3_resolution, layer_selection=selected_layers)
                st.success("Vindpotential sparad. Den kan nu togglas på i Samlad potential.")
    with info_col:
        with st.container(border=True):
            _potential_detail_panel("Osparad vindförhandsvisning", frame, "wind", h3_resolution)
            vector_stats = wind_candidate_summary(source_frame)
            st.metric(f"Kandidatytor R{WIND_SOURCE_RESOLUTION}", vector_stats["candidate_cells"])
            st.metric("Kandidatandel", f"{vector_stats['candidate_share']:.1f}%")
            if controls_applied:
                st.caption(ui_text("controls_applied", WIND_CONTROL_LANGUAGE))
            if runtime_overlay_enabled:
                if runtime_error:
                    st.warning(f"Geometri-runtime kunde inte köras: {runtime_error}")
                elif runtime_meta:
                    left_metric, right_metric = st.columns(2)
                    left_metric.metric("Runtime-grupper", int(runtime_meta.get("group_count") or 0))
                    land_share = runtime_meta.get("combined_land_share_pct")
                    right_metric.metric("Kombinerad landandel", "-" if land_share is None else f"{float(land_share):.1f}%")
                    if runtime_meta.get("cache_key"):
                        st.caption(f"Runtime-cache: {runtime_meta['cache_key']}")
                else:
                    st.caption("Geometri-runtime är påslagen men returnerade inga lager för nuvarande urval.")
            else:
                st.caption("Geometri-runtimeoverlay är avstängd.")
            if runtime_overlay_enabled:
                st.caption("Potentiell etableringsyta = landmassa minus valda buffertregler.")
            with st.expander("Aktiva regelgrupper", expanded=False):
                st.dataframe(_wind_group_summary_frame(ui_params, layer_selection=selected_layers), use_container_width=True, hide_index=True, height=240)
            with st.expander("Aktiva vindparametrar"):
                st.json(ui_params)
            with st.expander("Migrerad regelgruppslogik"):
                st.dataframe(wind_acceptance_group_summary(), use_container_width=True, hide_index=True)
            with st.expander("Modellgranskning", expanded=False):
                st.markdown("**Kritisk genomgång**")
                for item in critical_review_items("sv"):
                    st.write(f"- {item}")
                st.markdown("**Hexagonsnot**")
                for item in hexagon_note_items("sv"):
                    st.write(f"- {item}")
            with st.expander("Datastatus vindlager", expanded=False):
                st.dataframe(_wind_source_status_frame(), use_container_width=True, hide_index=True, height=280)


def _view_selector(panel: Any | None = None) -> str:
    current_view = _active_view()
    widget_key = LEFT_VIEW_WIDGET_KEY if panel is not None else MAIN_VIEW_WIDGET_KEY
    if widget_key not in st.session_state or _valid_view(st.session_state.get(widget_key)) != current_view:
        st.session_state[widget_key] = current_view
    if panel is not None:
        with panel.expander("Vy", expanded=True):
            if hasattr(st, "segmented_control"):
                selected = st.segmented_control(
                    "Vy",
                    VIEW_OPTIONS,
                    key=widget_key,
                    label_visibility="collapsed",
                    on_change=_sync_active_view_from_widget,
                    args=(widget_key,),
                )
                selected_view = _valid_view(selected or current_view)
                st.session_state[ACTIVE_VIEW_KEY] = selected_view
                return selected_view
            selected_view = _valid_view(
                st.radio(
                    "Vy",
                    VIEW_OPTIONS,
                    horizontal=False,
                    key=widget_key,
                    label_visibility="collapsed",
                    on_change=_sync_active_view_from_widget,
                    args=(widget_key,),
                )
            )
            st.session_state[ACTIVE_VIEW_KEY] = selected_view
            return selected_view
    target = st
    if hasattr(st, "segmented_control"):
        selected = target.segmented_control(
            "Vy",
            VIEW_OPTIONS,
            key=widget_key,
            label_visibility="collapsed",
            on_change=_sync_active_view_from_widget,
            args=(widget_key,),
        )
        selected_view = _valid_view(selected or current_view)
        st.session_state[ACTIVE_VIEW_KEY] = selected_view
        return selected_view
    selected_view = _valid_view(
        target.radio(
            "Vy",
            VIEW_OPTIONS,
            horizontal=panel is None,
            key=widget_key,
            label_visibility="collapsed",
            on_change=_sync_active_view_from_widget,
            args=(widget_key,),
        )
    )
    st.session_state[ACTIVE_VIEW_KEY] = selected_view
    return selected_view


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")
    left_panel, main_panel, right_panel = _workspace_shell()
    region, scenario_state = _render_region_scenario_panel(left_panel)
    context = _load_context(region)

    view = _view_selector(left_panel) if left_panel is not None else None
    h3_resolution = int(st.session_state.get("combined_h3_resolution", region.get("default_h3_resolution", 9)))
    with main_panel:
        if view is None:
            view = _view_selector(None)
        _workspace_header(region, scenario_state, h3_resolution)

        if view == "Bygg solpotential":
            _solar_builder_tab(region, context, left_panel, right_panel)
        elif view == "Bygg vindpotential":
            _wind_builder_tab(region, context, left_panel, right_panel)
        else:
            _combined_tab(region, scenario_state, context, left_panel, right_panel)


if __name__ == "__main__":
    main()
