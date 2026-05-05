from __future__ import annotations

from collections import deque
from io import StringIO
import h3
import json
import math
import os
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
import potential_model.landscape as landscape_model  # noqa: E402
from potential_model.manifests import (  # noqa: E402
    list_regions,
    load_linked_manifest,
    read_manifest,
    resolve_repo_path,
)
from potential_model.map_rendering import build_layered_hex_map_html  # noqa: E402
from potential_model.energy_modeling import (  # noqa: E402
    AREA_SCENARIO_LABELS,
    AREA_SCENARIO_ORDER,
    allocate_wind_area_from_core_hexes,
    build_times_summary,
    calculate_area_demand,
    h3_hex_area_km2,
    load_area_demand_bundle,
    load_energy_model_inputs,
    planning_scenario_label,
    planning_scenarios,
    scenario_display_label,
    select_planning_mix,
)
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


CLUSTER_COLORS = landscape_model.CLUSTER_COLORS
FACTOR_STOPS = landscape_model.FACTOR_STOPS
cluster_summary = landscape_model.cluster_summary
factor_columns = landscape_model.factor_columns
factor_label = landscape_model.factor_label
feature_collection_for_frame = landscape_model.feature_collection_for_frame
landscape_frame_for_resolution = landscape_model.landscape_frame_for_resolution
landscape_source_resolution = landscape_model.landscape_source_resolution
landscape_type_feature_collection_for_frame = landscape_model.landscape_type_feature_collection_for_frame
load_cluster_profile = landscape_model.load_cluster_profile
load_factor_scores = landscape_model.load_factor_scores
load_run_summary = landscape_model.load_run_summary


def landscape_type_display_colors(manifest: dict[str, Any] | None = None) -> dict[str, str]:
    color_func = getattr(landscape_model, "landscape_type_display_colors", None)
    if callable(color_func):
        return color_func(manifest)

    # Backward compatibility for deployments where potential_app.py is newer than landscape.py.
    colors = dict(getattr(landscape_model, "V10_TYPE_COLORS", {}))
    if not manifest:
        return colors

    manifest_colors = manifest.get("landscape_type_colors") or {}
    manifest_labels = manifest.get("landscape_type_labels") or {}
    for key, value in manifest_colors.items():
        colors.setdefault(str(key), str(value))
    for key in manifest_labels:
        colors.setdefault(str(key), "#999999")
    return colors


PAGE_TITLE = "Sol- och vindpotential"
MAP_VIEW_RESET_TOKEN_KEY = "potential_map_view_reset_token"
LEFT_PANEL_OPEN_KEY = "potential_left_panel_open"
RIGHT_PANEL_OPEN_KEY = "potential_right_panel_open"
REGION_SELECT_KEY = "potential_selected_region_id"
WIND_LAYER_SELECTION_KEY = "wind_builder_selected_layers"
WIND_RUNTIME_OVERLAY_KEY = "wind_builder_runtime_overlay_enabled"
SOLAR_APPLIED_CONFIG_KEY = "solar_applied_config"
WIND_CONTROL_LANGUAGE = "sv"
WIND_RUNTIME_BASE_RESOLUTION = 10
WIND_LANDSCAPE_POTENTIAL_LABEL = "Landskapspotential Vind"
WIND_POTENTIAL_POLYGON_LABEL = "Landskapspotential Vind polygon"
WIND_POTENTIAL_HEX_LABEL = "Landskapspotential Vind hexagon"
WIND_ESTABLISHMENT_LAYER_LABEL = "Potentiell etableringsyta Vind"
COMBINED_ESTABLISHMENT_LAYER_LABEL = "Potentiell etableringsyta"
SOLAR_LANDSCAPE_POTENTIAL_LABEL = "Landskapspotential Sol"
SOLAR_SMALL_SCALE_LABEL = "Småskalig anläggning på tak"
SOLAR_LARGE_SCALE_LABEL = "Storskalig anläggning på land"
SOLAR_POTENTIAL_POLYGON_LABEL = "Landskapspotential Sol polygon"
SOLAR_POTENTIAL_HEX_LABEL = "Landskapspotential Sol hexagon"
SOLAR_ESTABLISHMENT_LAYER_LABEL = "Potentiell etableringsyta Sol"
OUTSIDE_LP_NEED_LAYER_LABEL = "Ytbehov utanför landskapets potential"
SOLAR_POPULATION_SOURCE_LABEL = "Källa: Befolkningspunkter"
SOLAR_POPULATION_BUFFER_LABEL = "Buffert: Befolkningspunkter"
SOLAR_PROTECTED_SOURCE_LABEL = "Källa: Skyddade områden"
SOLAR_PROTECTED_BUFFER_LABEL = "Buffert: Skyddade områden"
WIND_POPULATION_SOURCE_LAYER_ID = "population_points"
SOLAR_PROTECTED_GROUP_ID = "protected"
SOLAR_PROTECTED_LAYER_IDS = tuple(WIND_GROUP_LAYER_DEFAULTS.get(SOLAR_PROTECTED_GROUP_ID, []))
ENERGY_PROPOSAL_LAYER_LABEL = WIND_ESTABLISHMENT_LAYER_LABEL
OUTSIDE_LP_NEED_CHILD_RESOLUTION_OFFSET = 1
WIND_AUTO_RESOLUTION_MIN_ZOOM: dict[int, int] = {10: 11, 9: 9, 8: 7, 7: 5, 6: 0}
REGIONAL_PIPELINE_ROOT = Path(os.environ.get("REGIONAL_LANDSCAPE_PIPELINE_ROOT", r"C:\gislab\regional-landscape-pipeline"))
SOLAR_V1_POPULATION_LAYER_PATH = (
    REGIONAL_PIPELINE_ROOT
    / "outputs"
    / "bornholm"
    / "bornholm_v1_higher_h3_local_sprickdal"
    / "layers"
    / "01_fastboendebefolkningmapinfo.csv"
)
SOLAR_V1_POPULATION_COUNT_COLUMN = "fastboendebefolkningmapinfo_count"
SOLAR_LARGE_SCALE_POLYGON_DIR = (
    ROOT
    / "docs"
    / "geocontext"
    / "potential_framework"
    / "data"
    / "bornholm_solar_large_scale_markblokke"
)
SOLAR_LARGE_SCALE_H3_R10_AREA_PATH = (
    SOLAR_LARGE_SCALE_POLYGON_DIR
    / "h3_r10_area_share"
    / "markblokke_bornholm_outside_population_000m_h3_r10_area_share.csv"
)
EML_PROVIDER_URL = "https://energymodellinglab.com/"
IVL_PROVIDER_URL = "https://www.ivl.se/"
WIND_SHARE_CLASS_SPECS: list[dict[str, Any]] = [
    {"id": "share_0", "label": "0%", "max_pct": 0.0, "legend_label": "0%", "base_color": "#d7301f", "core_color": "#7f0000"},
    {"id": "share_1", "label": ">0-5%", "max_pct": 5.0, "legend_label": "<=5%", "base_color": "#ef4444", "core_color": "#991b1b"},
    {"id": "share_2", "label": ">5-10%", "max_pct": 10.0, "legend_label": None, "base_color": "#f87171", "core_color": "#b91c1c"},
    {"id": "share_3", "label": ">10-15%", "max_pct": 15.0, "legend_label": None, "base_color": "#fecaca", "core_color": "#ef4444"},
    {"id": "share_4", "label": ">15-25%", "max_pct": 25.0, "legend_label": "~25%", "base_color": "#dbeafe", "core_color": "#93c5fd"},
    {"id": "share_5", "label": ">25-35%", "max_pct": 35.0, "legend_label": None, "base_color": "#bfdbfe", "core_color": "#60a5fa"},
    {"id": "share_6", "label": ">35-50%", "max_pct": 50.0, "legend_label": "~50%", "base_color": "#93c5fd", "core_color": "#3b82f6"},
    {"id": "share_7", "label": ">50-65%", "max_pct": 65.0, "legend_label": None, "base_color": "#60a5fa", "core_color": "#2563eb"},
    {"id": "share_8", "label": ">65-80%", "max_pct": 80.0, "legend_label": None, "base_color": "#2563eb", "core_color": "#1d4ed8"},
    {"id": "share_9", "label": ">80-100%", "max_pct": 100.0, "legend_label": "100%", "base_color": "#1d4ed8", "core_color": "#1e3a8a"},
]
ESTABLISHMENT_CLASS_SPECS: dict[str, dict[str, str]] = {
    "not_suitable": {"label": "Inte lämplig", "color": "#991b1b", "stroke": "#fee2e2"},
    "wind_only": {"label": "Endast vind", "color": "#2563eb", "stroke": "#dbeafe"},
    "solar_only": {"label": "Endast sol", "color": "#facc15", "stroke": "#fef3c7"},
    "wind_and_solar": {"label": "Vind och sol", "color": "#15803d", "stroke": "#dcfce7"},
}
SOLAR_CONTROL_GROUPS: list[dict[str, Any]] = [
    {
        "id": "open_landscape",
        "label": "Robusta öppna landskap",
        "caption": "Plus för öppna, jämna och storskaliga produktionslandskap.",
        "params": ["everyday_matrix_bonus"],
    },
    {
        "id": "grid",
        "label": "Elinfrastruktur",
        "caption": "Plus för teknisk logik nära elnät och transformatorstationer.",
        "params": ["grid_access_bonus"],
    },
    {
        "id": "settlement",
        "label": "Bebyggelse och rekreation",
        "caption": "Minus där bebyggelse, tät struktur och vardagslandskap ökar konflikt.",
        "params": ["settlement_penalty", "population_buffer_m"],
    },
    {
        "id": "protected",
        "label": "Skyddad natur och habitat",
        "caption": "Minus för skog, habitatkärnor och skyddade naturmiljöer.",
        "params": ["protected_penalty"],
    },
    {
        "id": "coast",
        "label": "Kust och öppna strandmiljöer",
        "caption": "Minus för kustnära landskap där solparker kan få visuell kontakt med kustlinjen.",
        "params": ["coastal_penalty"],
    },
    {
        "id": "terrain",
        "label": "Terräng, dalar och utsikt",
        "caption": "Minus för relief, sprickdalar, sluttningar och visuellt känsliga lägen.",
        "params": ["terrain_penalty"],
    },
]
SOLAR_PARAM_CONTROLS: dict[str, dict[str, Any]] = {
    "base_score": {
        "label": "Basnivå",
        "min": 30.0,
        "max": 75.0,
        "step": 1.0,
        "help": "Startpoäng innan landskapsvillkor läggs till.",
    },
    "grid_access_bonus": {
        "label": "Elanslutningslogik",
        "min": 0.0,
        "max": 20.0,
        "step": 1.0,
        "help": "Förberedd lagerbaserad kontroll för närhet till elnät och transformatorstationer.",
    },
    "everyday_matrix_bonus": {
        "label": "Öppet produktionslandskap",
        "min": 0.0,
        "max": 30.0,
        "step": 1.0,
        "help": "Förberedd kontroll för öppna produktionslandskap som kan bära storskalig sol.",
    },
    "coastal_penalty": {
        "label": "Buffert kust/strand",
        "min": 0.0,
        "max": 35.0,
        "step": 1.0,
        "help": "Förberedd lagerbaserad kontroll för kustzon och strandskydd.",
    },
    "terrain_penalty": {
        "label": "Terrängavgränsning",
        "min": 0.0,
        "max": 35.0,
        "step": 1.0,
        "help": "Förberedd kontroll för relief, sprickdalar och visuellt känsliga lägen.",
    },
    "protected_penalty": {
        "label": "Buffert skyddad natur",
        "min": 0.0,
        "max": 40.0,
        "step": 1.0,
        "help": "Förberedd lagerbaserad kontroll för skyddade områden, skog och habitat.",
    },
    "settlement_penalty": {
        "label": "Bebyggelseavgränsning",
        "min": 0.0,
        "max": 35.0,
        "step": 1.0,
        "help": "Förberedd lagerbaserad kontroll för bebyggelse och tät struktur.",
    },
    "population_buffer_m": {
        "label": "Avstånd till befolkning",
        "min": 100.0,
        "max": 500.0,
        "step": 25.0,
        "help": "Totalt avstånd från befolkningspunkter. Källan är redan en 100 m visningsbuffert, så appen lägger bara till avståndet över 100 m.",
    },
}


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
        region_id = region.get("region_id", "region")
        scenario_key = f"potential_scenario_{region_id}"
        energy_scenario_key = f"energy_model_planning_scenario_{region_id}"
        default_level = "medium" if "medium" in levels else levels[0]
        energy_scenario = st.session_state.get(energy_scenario_key)
        if panel is None and energy_scenario in levels:
            st.session_state[scenario_key] = energy_scenario
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


@st.cache_data(show_spinner=False)
def _cached_energy_inputs(manifest_json: str, root_str: str) -> tuple[pd.DataFrame, dict[str, str], str]:
    manifest = json.loads(manifest_json)
    inputs = load_energy_model_inputs(manifest, Path(root_str))
    return inputs.times_rows, inputs.scenario_descriptions, inputs.source_status


@st.cache_data(show_spinner=False)
def _cached_area_demand(manifest_json: str, root_str: str) -> dict[str, Any]:
    manifest = json.loads(manifest_json)
    bundle = load_area_demand_bundle(manifest, Path(root_str))
    return {
        "factors_by_scenario": bundle.factors_by_scenario,
        "scenario_table": bundle.scenario_table,
        "observation_table": bundle.observation_table,
        "warning_table": bundle.warning_table,
        "local_reference_table": bundle.local_reference_table,
        "references": bundle.references,
        "rules_text": bundle.rules_text,
        "source_path": bundle.source_path,
    }


def _energy_model_manifest_json(scenario_manifest: dict[str, Any] | None) -> str:
    return json.dumps(scenario_manifest or {}, sort_keys=True, ensure_ascii=False)


def _technology_to_times_map(scenario_manifest: dict[str, Any] | None) -> dict[str, str]:
    area_cfg = (((scenario_manifest or {}).get("energy_model") or {}).get("area_demand") or {})
    mapping = area_cfg.get("times_technology_map") or {}
    result: dict[str, str] = {}
    for times_tech, rule in mapping.items():
        energy_key = str((rule or {}).get("energy_key", "")).strip()
        if energy_key:
            result[energy_key] = str(times_tech)
    return result or {"wind": "NRG_WIN", "solar": "NRG_SOL"}


def _area_scenario_label(scenario_id: str) -> str:
    labels = {"low": "Låg", "mid": "Mellan", "high": "Hög"}
    return labels.get(str(scenario_id), AREA_SCENARIO_LABELS.get(str(scenario_id), str(scenario_id)))


def _energy_key_label(energy_key: str) -> str:
    return {"wind": "Vind", "solar": "Sol"}.get(str(energy_key), str(energy_key))


def _energy_mix_share(mix: pd.DataFrame, energy_key: str) -> float:
    if mix.empty or "energy_key" not in mix.columns or "value_twh" not in mix.columns:
        return 0.0
    values = pd.to_numeric(
        mix.loc[mix["energy_key"].astype(str) == str(energy_key), "value_twh"],
        errors="coerce",
    ).fillna(0.0)
    return float(values.sum())


def _balance_wind_solar_mix(mix: pd.DataFrame, solar_share_pct: float) -> pd.DataFrame:
    adjusted = mix.copy()
    if adjusted.empty or "energy_key" not in adjusted.columns or "value_twh" not in adjusted.columns:
        return adjusted

    solar_share = max(0.0, min(100.0, float(solar_share_pct))) / 100.0
    wind_twh = _energy_mix_share(adjusted, "wind")
    solar_twh = _energy_mix_share(adjusted, "solar")
    total_twh = wind_twh + solar_twh
    if total_twh <= 0:
        return adjusted

    targets = {"solar": total_twh * solar_share, "wind": total_twh * (1.0 - solar_share)}
    for energy_key, target_twh in targets.items():
        mask = adjusted["energy_key"].astype(str) == energy_key
        current_twh = float(pd.to_numeric(adjusted.loc[mask, "value_twh"], errors="coerce").fillna(0.0).sum())
        if not mask.any():
            new_row = {
                "scenario": adjusted["scenario"].iloc[0] if "scenario" in adjusted.columns and not adjusted.empty else "",
                "year": adjusted["year"].iloc[0] if "year" in adjusted.columns and not adjusted.empty else "",
                "energy_key": energy_key,
                "value_twh": target_twh,
            }
            adjusted = pd.concat([adjusted, pd.DataFrame([new_row])], ignore_index=True, sort=False)
        elif current_twh > 0:
            adjusted.loc[mask, "value_twh"] = pd.to_numeric(adjusted.loc[mask, "value_twh"], errors="coerce").fillna(0.0) * (target_twh / current_twh)
        else:
            first_idx = adjusted.index[mask][0]
            adjusted.loc[mask, "value_twh"] = 0.0
            adjusted.loc[first_idx, "value_twh"] = target_twh
    return adjusted.reset_index(drop=True)


def _render_hex_area_card(
    area_by_scenario: dict[str, float],
    hex_area: float,
    selected_scenario: str,
    scenario_order: list[str] | tuple[str, ...] | None = None,
    label_func: Any | None = None,
) -> None:
    scenario_order = list(scenario_order or AREA_SCENARIO_ORDER)
    label_func = label_func or _area_scenario_label
    max_area = max([0.0, *[float(value or 0.0) for value in area_by_scenario.values()]])
    max_hex = max(1, int(math.ceil(max_area / max(hex_area, 1e-9))))
    symbol_scale = max(1, int(math.ceil(max_hex / 54)))
    rows: list[str] = []
    for scenario_id in scenario_order:
        area = float(area_by_scenario.get(scenario_id, 0.0) or 0.0)
        needed_hex = int(math.ceil(area / max(hex_area, 1e-9))) if area > 0 else 0
        symbols = max(1, int(math.ceil(needed_hex / symbol_scale))) if needed_hex else 0
        active = scenario_id == selected_scenario
        color = "#1f7a3f" if active else "#9ca3af"
        bg = "rgba(31,122,63,0.08)" if active else "rgba(255,255,255,0.55)"
        hexes = "".join(
            f"<span style='display:inline-block;width:0.58rem;height:0.52rem;margin:0.035rem;background:{color};clip-path:polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%);'></span>"
            for _ in range(min(symbols, 54))
        )
        if symbols > 54:
            hexes += "<span style='font-size:0.72rem;color:#6b7280;margin-left:0.2rem;'>+</span>"
        rows.append(
            "<div style='padding:0.45rem 0.5rem;border:1px solid rgba(49,51,63,0.14);"
            f"background:{bg};border-radius:6px;margin:0.32rem 0;'>"
            f"<div style='display:flex;justify-content:space-between;gap:0.5rem;font-size:0.82rem;font-weight:650;'>"
            f"<span>{label_func(scenario_id)}</span><span>{area:.2f} km²</span></div>"
            f"<div style='font-size:0.75rem;color:#6b7280;margin:0.1rem 0 0.25rem;'>~{needed_hex} hex</div>"
            f"<div style='line-height:0.55rem;'>{hexes}</div>"
            "</div>"
        )
    st.markdown(
        "<div style='font-size:0.82rem;font-weight:650;margin-bottom:0.25rem;'>Area demand som hex</div>"
        + "".join(rows)
        + f"<div style='font-size:0.74rem;color:#6b7280;margin-top:0.3rem;'>1 symbol ≈ {symbol_scale} hex i vald H3-upplösning.</div>",
        unsafe_allow_html=True,
    )


def _render_energy_modeling_panel(
    region: dict[str, Any],
    scenario_state: dict[str, Any],
    h3_resolution: int,
    panel: Any,
) -> dict[str, Any]:
    scenario_manifest = scenario_state.get("manifest")
    if not scenario_manifest or not (scenario_manifest.get("energy_model") or {}):
        with panel.expander("Scenarier", expanded=False):
            return _scenario_state(region, st) | {"available": False}

    manifest_json = _energy_model_manifest_json(scenario_manifest)
    state: dict[str, Any] = {"available": False, "manifest": scenario_manifest}
    try:
        times_rows, scenario_descriptions, source_status = _cached_energy_inputs(manifest_json, str(ROOT))
        area_payload = _cached_area_demand(manifest_json, str(ROOT))
    except Exception as exc:
        panel.warning(f"Energimodellering kunde inte laddas: {exc}")
        panel.caption("Kontrollera DuckDB/AreaDemand-sökvägar, schema i manifestet och Pythonpaketen duckdb/openpyxl.")
        return state

    scenario_totals, mix = build_times_summary(times_rows)
    if not scenario_totals:
        panel.warning("DuckDB gav inga konfigurerade vind-/solrader.")
        return state

    planning_options = planning_scenarios(scenario_manifest)
    planning_by_id = {str(option.get("id")): option for option in planning_options if option.get("id")}
    planning_ids = [str(option.get("id")) for option in planning_options if option.get("id")]
    if not planning_ids:
        panel.warning("Manifestet saknar planeringsscenarier.")
        return state

    planning_cfg = ((scenario_manifest.get("energy_model") or {}).get("planning") or {})
    region_id = region.get("region_id", "region")
    scenario_key = f"energy_model_planning_scenario_{region_id}"
    potential_scenario_key = f"potential_scenario_{region_id}"
    default_planning_id = str(
        st.session_state.get(scenario_key)
        or st.session_state.get(potential_scenario_key)
        or scenario_state.get("scenario")
        or planning_cfg.get("default_scenario")
        or "medium"
    )
    if default_planning_id not in planning_by_id:
        default_planning_id = planning_ids[0]
    if st.session_state.get(scenario_key) not in planning_ids:
        st.session_state[scenario_key] = default_planning_id
    planning_id = panel.selectbox(
        "Framtidsscenario",
        options=planning_ids,
        key=scenario_key,
        format_func=lambda value: planning_scenario_label(planning_by_id.get(str(value), {"id": value})),
    )
    scenario_levels = scenario_manifest.get("scenario_levels") or []
    if str(planning_id) in scenario_levels:
        st.session_state[potential_scenario_key] = str(planning_id)
    selected_planning = planning_by_id[str(planning_id)]
    selected_planning_label = planning_scenario_label(selected_planning)
    source_scenario = str(selected_planning.get("source_scenario", "")).strip()
    planning_year = int(selected_planning.get("planning_year", planning_cfg.get("planning_year", 2050)) or 2050)
    energy_scale = float(selected_planning.get("energy_scale", 1.0) or 1.0)
    area_scenario_id = str(selected_planning.get("area_demand_scenario", "mid") or "mid")
    if area_scenario_id not in AREA_SCENARIO_ORDER:
        area_scenario_id = "mid"
    source_label = scenario_display_label(source_scenario, scenario_descriptions) if source_scenario else "-"

    panel.caption(
        f"Markintensitet: {_area_scenario_label(area_scenario_id)} · "
        f"modellkälla: {source_label}, {planning_year}, skala {energy_scale:g}x"
    )

    placement_key = f"energy_model_placement_{region.get('region_id', 'region')}"
    placement_mode = panel.radio(
        "Placering",
        options=["auto", "manual"],
        key=placement_key,
        format_func=lambda value: {"auto": "Placera automatiskt", "manual": "Placera själv"}.get(value, value),
    )
    if placement_mode == "manual":
        panel.info("Självplacering är förberedd som arbetsläge. Första robusta steg blir klicka för att lägga till/ta bort hex; drag-and-drop kräver ett separat kartinteraktionssteg.")

    selected_mix = select_planning_mix(mix, selected_planning)
    if selected_mix.empty:
        panel.warning(
            f"Planeringsscenariot pekar på {source_scenario or '-'} {planning_year}, men de raderna finns inte i DuckDB."
        )
        return state

    native_wind_twh = _energy_mix_share(selected_mix, "wind")
    native_solar_twh = _energy_mix_share(selected_mix, "solar")
    native_total_twh = native_wind_twh + native_solar_twh
    native_solar_share_pct = (native_solar_twh / native_total_twh * 100.0) if native_total_twh > 0 else 50.0
    mix_key = f"energy_model_mix_solar_share_{region.get('region_id', 'region')}"
    mix_default_key = f"{mix_key}_default_50_applied"
    if not bool(st.session_state.get(mix_default_key, False)):
        st.session_state[mix_key] = 50
        st.session_state[mix_default_key] = True
    st.session_state.setdefault(mix_key, 50)
    solar_share_pct = float(
        panel.slider(
            "Energimix",
            min_value=0,
            max_value=100,
            step=5,
            key=mix_key,
            format="%d%% sol",
            help=(
                "Balans mellan sol och vind i valt framtidsscenario. "
                "När solandelen ökar minskar vindandelen med samma totalenergi, och tvärtom."
            ),
        )
    )
    wind_share_pct = 100.0 - solar_share_pct
    selected_mix = _balance_wind_solar_mix(selected_mix, solar_share_pct)
    panel.caption(
        f"Energimix: {wind_share_pct:.0f}% vind / {solar_share_pct:.0f}% sol. "
        f"Ursprunglig TIMES-mix: {100.0 - native_solar_share_pct:.0f}% vind / {native_solar_share_pct:.0f}% sol."
    )

    technology_to_times = _technology_to_times_map(scenario_manifest)
    area_bundle_obj = type(
        "AreaBundleShim",
        (),
        {"factors_by_scenario": area_payload["factors_by_scenario"]},
    )()
    area_demand = calculate_area_demand(selected_mix, area_bundle_obj, str(area_scenario_id), technology_to_times)
    area_demand["Teknik"] = area_demand["energy_key"].map(_energy_key_label)
    hex_area = h3_hex_area_km2(int(h3_resolution))

    planning = ((scenario_manifest.get("energy_model") or {}).get("planning") or {})
    primary_technology = str(planning.get("primary_technology", "wind"))
    primary_row = area_demand[area_demand["energy_key"].astype(str) == primary_technology]
    primary_area_need = float(primary_row["area_need_km2"].fillna(0.0).sum()) if not primary_row.empty else 0.0
    primary_twh = float(primary_row["twh"].fillna(0.0).sum()) if not primary_row.empty else 0.0
    primary_factor = float(primary_row["km2_per_twh"].dropna().iloc[0]) if not primary_row["km2_per_twh"].dropna().empty else math.nan
    solar_row = area_demand[area_demand["energy_key"].astype(str) == "solar"]
    wind_row = area_demand[area_demand["energy_key"].astype(str) == "wind"]
    solar_area_need = float(solar_row["area_need_km2"].fillna(0.0).sum()) if not solar_row.empty else 0.0
    solar_twh = float(solar_row["twh"].fillna(0.0).sum()) if not solar_row.empty else 0.0
    solar_factor = float(solar_row["km2_per_twh"].dropna().iloc[0]) if not solar_row.empty and not solar_row["km2_per_twh"].dropna().empty else math.nan
    wind_area_need = float(wind_row["area_need_km2"].fillna(0.0).sum()) if not wind_row.empty else 0.0
    wind_twh = float(wind_row["twh"].fillna(0.0).sum()) if not wind_row.empty else 0.0
    wind_factor = float(wind_row["km2_per_twh"].dropna().iloc[0]) if not wind_row.empty and not wind_row["km2_per_twh"].dropna().empty else math.nan

    metric_cols = panel.columns(4)
    metric_cols[0].metric("Vind", f"{wind_twh:.2f} TWh")
    metric_cols[1].metric("Sol", f"{solar_twh:.2f} TWh")
    metric_cols[2].metric("Vindyta", f"{wind_area_need:.2f} km²")
    metric_cols[3].metric("Solyta", f"{solar_area_need:.2f} km²")

    planning_area_by_scenario: dict[str, float] = {}
    for scenario_option in planning_options:
        option_id = str(scenario_option.get("id"))
        option_mix = _balance_wind_solar_mix(select_planning_mix(mix, scenario_option), solar_share_pct)
        option_area_scenario = str(scenario_option.get("area_demand_scenario", "mid") or "mid")
        if option_area_scenario not in AREA_SCENARIO_ORDER:
            option_area_scenario = "mid"
        scenario_frame = calculate_area_demand(option_mix, area_bundle_obj, option_area_scenario, technology_to_times)
        row = scenario_frame[scenario_frame["energy_key"].astype(str) == primary_technology]
        planning_area_by_scenario[option_id] = float(row["area_need_km2"].fillna(0.0).sum()) if not row.empty else 0.0
    with panel.container(border=True):
        _render_hex_area_card(
            planning_area_by_scenario,
            hex_area,
            str(planning_id),
            scenario_order=planning_ids,
            label_func=lambda value: planning_scenario_label(planning_by_id.get(str(value), {"id": value})),
        )

    show_key = f"energy_model_show_proposal_{region.get('region_id', 'region')}"
    show_proposal = panel.checkbox("Visa föreslagen etableringsyta", value=True, key=show_key)

    with panel.expander("Beräkning och datakvalitet", expanded=False):
        calc_df = area_demand[["Teknik", "twh", "km2_per_twh", "area_need_km2"]].rename(
            columns={"twh": "TWh", "km2_per_twh": "km²/TWh", "area_need_km2": "km²"}
        )
        st.dataframe(calc_df.round(3), width="stretch", hide_index=True)
        st.caption(source_status)
        st.caption(f"AreaDemand: {area_payload.get('source_path', '-')}")
        local_reference_table = pd.DataFrame(area_payload.get("local_reference_table", pd.DataFrame()))
        if not local_reference_table.empty:
            st.caption(
                "Nedre Bornholm-sektionen i AreaDemand.xlsx läses som lokal referens. "
                "Den visas för transparens men styr inte scenarierna förrän manifestet väljer den som faktor."
            )
            st.dataframe(local_reference_table.round(4), width="stretch", hide_index=True, height=180)
        warning_table = pd.DataFrame(area_payload.get("warning_table", pd.DataFrame()))
        if not warning_table.empty:
            st.warning("AreaDemand innehåller outliers som har exkluderats från scenariofaktorer.")
            st.dataframe(warning_table, width="stretch", hide_index=True, height=180)
        scenario_table = pd.DataFrame(area_payload.get("scenario_table", pd.DataFrame()))
        if not scenario_table.empty:
            st.dataframe(scenario_table.round(3), width="stretch", hide_index=True)

    state.update(
        {
            "available": True,
            "scenario": str(planning_id),
            "scenario_label": selected_planning_label,
            "source_scenario": source_scenario,
            "source_scenario_label": source_label,
            "source_year": int(planning_year),
            "energy_scale": energy_scale,
            "area_scenario_id": str(area_scenario_id),
            "area_scenario_label": _area_scenario_label(str(area_scenario_id)),
            "placement_mode": str(placement_mode),
            "show_proposal": bool(show_proposal),
            "area_demand": area_demand,
            "primary_technology": primary_technology,
            "primary_area_need_km2": primary_area_need,
            "primary_twh": primary_twh,
            "primary_km2_per_twh": primary_factor,
            "wind_share_pct": wind_share_pct,
            "solar_share_pct": solar_share_pct,
            "native_wind_share_pct": 100.0 - native_solar_share_pct,
            "native_solar_share_pct": native_solar_share_pct,
            "wind_area_need_km2": wind_area_need,
            "wind_km2_per_twh": wind_factor,
            "solar_area_need_km2": solar_area_need,
            "solar_km2_per_twh": solar_factor,
            "wind_twh": wind_twh,
            "solar_twh": solar_twh,
            "hex_area_km2": hex_area,
            "auto_min_potential_share_pct": float(planning.get("auto_min_potential_share_pct", 65.0)),
            "source_status": source_status,
            "area_warnings": pd.DataFrame(area_payload.get("warning_table", pd.DataFrame())),
        }
    )
    return state


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
    st.caption(f"Regional v0 för scenarier, {SOLAR_LANDSCAPE_POTENTIAL_LABEL}, {WIND_LANDSCAPE_POTENTIAL_LABEL} och landskapsanalys.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Region", str(region.get("display_name", region.get("region_id"))))
    c2.metric("Scenario", str(scenario_state.get("scenario") or "-"))
    c3.metric("Nominell skala", str(region.get("nominal_scale", "TBD")))
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
          <div class="workspace-pill">CRS: {region.get("native_crs", "TBD")}</div>
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


def _preferred_h3_resolution(region: dict[str, Any], preferred: int = 10) -> int:
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
    return f"{key_prefix}_vector_opacity"


def _current_opacity(key_prefix: str) -> float:
    try:
        opacity = float(st.session_state.get(_opacity_key(key_prefix), 0.78))
    except Exception:
        opacity = 0.78
    return max(0.15, min(1.0, opacity))


def _hex_opacity_key(key_prefix: str, opacity_key: str) -> str:
    safe_key = "".join(ch if ch.isalnum() else "_" for ch in str(opacity_key))
    return f"{key_prefix}_hex_opacity_{safe_key}"


def _hex_opacity_value(key_prefix: str, opacity_key: str, default: float = 0.78) -> float:
    try:
        opacity = float(st.session_state.get(_hex_opacity_key(key_prefix, opacity_key), default))
    except Exception:
        opacity = default
    return max(0.15, min(1.0, opacity))


def _render_opacity_control(key_prefix: str) -> None:
    control_left, control_center, control_right = st.columns([0.22, 0.56, 0.22], gap="small")
    with control_center:
        st.slider(
            "Opacitet polygoner och linjer",
            min_value=0.15,
            max_value=1.0,
            value=0.78,
            step=0.05,
            key=_opacity_key(key_prefix),
            help="Styr genomskinligheten för aktiva polygon- och linjelager i kartan.",
        )


def _hex_opacity_controls(layers: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for layer in layers:
        if str(layer.get("layer_kind", "")) != "hex":
            continue
        if layer.get("default_visible") is False:
            continue
        family_key = str(layer.get("opacity_family") or layer.get("control_name") or layer.get("name"))
        if family_key in families:
            continue
        families[family_key] = {
            "key": family_key,
            "label": str(layer.get("opacity_label") or layer.get("control_name") or layer.get("name")),
            "default": float(layer.get("fill_opacity", 0.78) or 0.78),
        }

    if not families:
        return []

    st.caption("Opacitet hexlager")
    for family in families.values():
        st.slider(
            family["label"],
            min_value=0.15,
            max_value=1.0,
            value=max(0.15, min(1.0, family["default"])),
            step=0.05,
            key=_hex_opacity_key(key_prefix, family["key"]),
            help=f"Styr opaciteten för hexlagret {family['label']}.",
        )
    return list(families.values())


def _apply_layer_opacity_state(layers: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    adjusted_layers: list[dict[str, Any]] = []
    for layer in layers:
        spec = dict(layer)
        if str(spec.get("layer_kind", "")) == "hex":
            family_key = str(spec.get("opacity_family") or spec.get("control_name") or spec.get("name"))
            spec["fill_opacity"] = _hex_opacity_value(key_prefix, family_key, float(spec.get("fill_opacity", 0.78) or 0.78))
        adjusted_layers.append(spec)
    return adjusted_layers


def _layer_control_rows(layers: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    rows_by_control: dict[str, dict[str, Any]] = {}
    for layer in layers:
        control_name = str(layer.get("control_name") or layer.get("name") or "Lager")
        kind = str(layer.get("layer_kind") or "lager")
        resolution = layer.get("auto_resolution")
        row = rows_by_control.setdefault(
            control_name,
            {
                "lager": control_name,
                "typ": "Hex" if kind == "hex" else "Polygon/linje" if kind == "vector" else kind.title(),
                "visning": "",
                "opacitet": "",
            },
        )
        if kind == "hex":
            family_key = str(layer.get("opacity_family") or control_name)
            row["opacitet"] = f"{_hex_opacity_value(key_prefix, family_key, float(layer.get('fill_opacity', 0.78) or 0.78)):.2f}"
        elif not row["opacitet"]:
            row["opacitet"] = f"{_current_opacity(key_prefix):.2f}"
        if resolution is not None:
            values = str(row["visning"]).split(", ") if row["visning"] else []
            label = f"R{int(resolution)}"
            if label not in values:
                values.append(label)
            row["visning"] = ", ".join(values)
        elif not row["visning"]:
            row["visning"] = "Direkt"
    return list(rows_by_control.values())


def _count_enabled(*values: bool) -> int:
    return sum(1 for value in values if bool(value))


def _solar_control_selected_protected_layer_ids(config: dict[str, Any]) -> list[str]:
    raw_ids = config.get("large_protected_layer_ids")
    if isinstance(raw_ids, (list, tuple, set)):
        requested = [str(layer_id) for layer_id in raw_ids]
    elif bool(config.get("large_protected_active", False)):
        requested = list(_solar_available_protected_layer_ids())
    else:
        requested = []
    return list(_solar_available_protected_layer_ids(requested))


def _solar_large_scale_is_active(
    markblokke_active: bool,
    population_active: bool,
    protected_layer_ids: list[str] | tuple[str, ...],
) -> bool:
    return bool(markblokke_active or population_active or protected_layer_ids)


def _solar_protected_layer_control_key(layer_id: str) -> str:
    return f"solar_draft_protected_layer__{layer_id}"


def _initial_solar_config_from_session() -> dict[str, Any]:
    selected_protected_ids = [
        layer_id
        for layer_id in SOLAR_PROTECTED_LAYER_IDS
        if bool(st.session_state.get(_solar_protected_layer_control_key(layer_id), False))
    ]
    legacy_large_active = bool(st.session_state.get("show_user_solar", False)) or bool(
        st.session_state.get("solar_large_scale_active", False)
    )
    large_markblokke_active = bool(st.session_state.get("solar_large_markblokke_active", legacy_large_active))
    large_population_active = bool(st.session_state.get("solar_large_population_active", False))
    large_scale_active = _solar_large_scale_is_active(
        large_markblokke_active,
        large_population_active,
        selected_protected_ids,
    )
    return {
        "small_population_active": bool(st.session_state.get("show_solar_v1", False))
        and bool(st.session_state.get("solar_small_population_active", True)),
        "large_markblokke_active": large_markblokke_active,
        "large_scale_active": large_scale_active,
        "large_population_active": large_population_active,
        "large_protected_layer_ids": selected_protected_ids,
        "large_protected_active": bool(selected_protected_ids),
        "panel_area_m2_per_person": float(st.session_state.get("solar_v1_area_m2_per_person", 10.0) or 10.0),
        "population_buffer_m": float(st.session_state.get("solar_builder_population_buffer_m", 250.0) or 250.0),
        "protected_buffer_m": float(st.session_state.get("solar_builder_protected_buffer_m", 0.0) or 0.0),
    }


def _solar_config_from_session() -> dict[str, Any]:
    config = st.session_state.get(SOLAR_APPLIED_CONFIG_KEY)
    if not isinstance(config, dict):
        config = _initial_solar_config_from_session()
        st.session_state[SOLAR_APPLIED_CONFIG_KEY] = dict(config)
    protected_layer_ids = _solar_control_selected_protected_layer_ids(config)
    legacy_large_active = bool(config.get("large_scale_active", config.get("large_population_active", False)))
    large_markblokke_active = bool(config.get("large_markblokke_active", legacy_large_active))
    large_population_active = bool(config.get("large_population_active", False))
    large_scale_active = _solar_large_scale_is_active(
        large_markblokke_active,
        large_population_active,
        protected_layer_ids,
    )
    return {
        "small_population_active": bool(config.get("small_population_active", False)),
        "large_markblokke_active": large_markblokke_active,
        "large_scale_active": large_scale_active,
        "large_population_active": large_population_active,
        "large_protected_layer_ids": protected_layer_ids,
        "large_protected_active": bool(protected_layer_ids),
        "panel_area_m2_per_person": float(config.get("panel_area_m2_per_person", 10.0) or 0.0),
        "population_buffer_m": float(config.get("population_buffer_m", 250.0) or 250.0),
        "protected_buffer_m": float(config.get("protected_buffer_m", 0.0) or 0.0),
    }


def _prime_solar_draft_state(config: dict[str, Any]) -> None:
    protected_layer_ids = set(_solar_control_selected_protected_layer_ids(config))
    st.session_state.setdefault("solar_draft_small_population_active", bool(config.get("small_population_active", False)))
    st.session_state.setdefault("solar_draft_large_markblokke_active", bool(config.get("large_markblokke_active", False)))
    st.session_state.setdefault("solar_draft_large_population_active", bool(config.get("large_population_active", False)))
    st.session_state.setdefault("solar_draft_area_m2_per_person", float(config.get("panel_area_m2_per_person", 10.0) or 10.0))
    st.session_state.setdefault("solar_draft_population_buffer_m", float(config.get("population_buffer_m", 250.0) or 250.0))
    st.session_state.setdefault("solar_draft_protected_buffer_m", float(config.get("protected_buffer_m", 0.0) or 0.0))
    for layer_id in SOLAR_PROTECTED_LAYER_IDS:
        st.session_state.setdefault(_solar_protected_layer_control_key(layer_id), layer_id in protected_layer_ids)


def _solar_draft_config_from_session() -> dict[str, Any]:
    large_markblokke_active = bool(st.session_state.get("solar_draft_large_markblokke_active", False))
    large_population_active = bool(st.session_state.get("solar_draft_large_population_active", False))
    protected_layer_ids = [
        layer_id
        for layer_id in SOLAR_PROTECTED_LAYER_IDS
        if bool(st.session_state.get(_solar_protected_layer_control_key(layer_id), False))
    ]
    return {
        "small_population_active": bool(st.session_state.get("solar_draft_small_population_active", False)),
        "large_markblokke_active": large_markblokke_active,
        "large_scale_active": _solar_large_scale_is_active(
            large_markblokke_active,
            large_population_active,
            protected_layer_ids,
        ),
        "large_population_active": large_population_active,
        "large_protected_layer_ids": protected_layer_ids,
        "large_protected_active": bool(protected_layer_ids),
        "panel_area_m2_per_person": float(st.session_state.get("solar_draft_area_m2_per_person", 10.0) or 0.0),
        "population_buffer_m": float(st.session_state.get("solar_draft_population_buffer_m", 250.0) or 250.0),
        "protected_buffer_m": float(st.session_state.get("solar_draft_protected_buffer_m", 0.0) or 0.0),
    }


def _map_panel_controls(region: dict[str, Any], key_prefix: str, panel: Any | None = None) -> tuple[int, bool, float, bool, int]:
    available = _available_h3_resolutions(region)
    state_key = f"{key_prefix}_h3_resolution"
    lock_state_key = f"{key_prefix}_lock_h3_resolution"
    preferred = _preferred_h3_resolution(region, 10)
    try:
        current_value = int(st.session_state.get(state_key, preferred))
    except Exception:
        current_value = preferred
    if current_value not in available:
        current_value = preferred
    st.session_state[state_key] = current_value
    st.session_state.setdefault(lock_state_key, False)

    if panel is not None:
        with panel.expander("H3 resolution", expanded=False):
            h3_resolution = st.radio(
                "H3-rollup",
                options=available,
                index=available.index(current_value),
                format_func=lambda value: _h3_option_label(region, value),
                horizontal=False,
                key=state_key,
            )
            lock_resolution = st.checkbox(
                "Lås vald upplösning",
                value=bool(st.session_state.get(lock_state_key, False)),
                key=lock_state_key,
                help="När avstängd får kartan visa grövre aggregat vid utzoomning. När påslagen visas alltid exakt vald upplösning.",
            )
            st.markdown("[Learn more about H3 resolutions](https://h3geo.org/).")
            if st.button("Återställ kartvy", key=f"{key_prefix}_reset_map_view"):
                _request_browser_map_view_reset()
                st.rerun()
    else:
        h3_resolution = current_value
        lock_resolution = bool(st.session_state.get(lock_state_key, False))

    return int(h3_resolution), bool(lock_resolution), _current_opacity(key_prefix), True, _map_view_reset_token()


def _filter_frame_to_display_geometries(frame: pd.DataFrame, display_geometry_path: str | None) -> pd.DataFrame:
    if not display_geometry_path or "hex_id" not in frame.columns:
        return frame
    visible_hex_ids = set(load_h3_display_geometries(display_geometry_path))
    return frame[frame["hex_id"].astype(str).isin(visible_hex_ids)].copy()


def _display_family_resolutions(region: dict[str, Any], preferred_resolution: int) -> list[int]:
    preferred = int(preferred_resolution)
    available = [value for value in _available_h3_resolutions(region) if int(value) <= preferred]
    return available or [preferred]


def _hex_display_rule(region: dict[str, Any], selected_resolution: int, lock_resolution: bool) -> dict[str, str]:
    selected = int(selected_resolution)
    family_resolutions = _display_family_resolutions(region, selected)
    min_resolution = min(int(value) for value in family_resolutions) if family_resolutions else selected
    if bool(lock_resolution):
        return {
            "selected_label": f"R{selected}",
            "display_label": f"R{selected}",
            "mode_label": "Låst",
            "caption": f"Alla aktiva hexlager visas låsta i R{selected}.",
            "item_note": f"Hexvisning låst till R{selected}.",
        }
    if min_resolution == selected:
        return {
            "selected_label": f"R{selected}",
            "display_label": f"R{selected}",
            "mode_label": "Fast",
            "caption": f"Aktiva hexlager visas i R{selected}.",
            "item_note": f"Hexvisning i R{selected}.",
        }
    return {
        "selected_label": f"R{selected}",
        "display_label": f"R{selected} till R{min_resolution}",
        "mode_label": "Zoomanpassad",
        "caption": (
            f"Aktiva hexlager visas i R{selected} nära kartan, och aggregeras stegvis till R{min_resolution} när du zoomar ut."
        ),
        "item_note": f"Hexvisning zoomanpassas från R{selected} till R{min_resolution}.",
    }


def _hex_family_layers(
    region: dict[str, Any],
    selected_resolution: int,
    lock_resolution: bool,
    family_key: str,
    control_name: str,
    build_layer: Any,
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for resolution in _display_family_resolutions(region, int(selected_resolution)):
        layer = build_layer(int(resolution))
        if layer is None:
            continue
        layer["name"] = f"{control_name} R{int(resolution)}"
        layer["control_name"] = control_name
        layer["auto_resolution_group"] = str(family_key)
        layer["auto_resolution"] = int(resolution)
        layer["selected_resolution"] = int(selected_resolution)
        layer["lock_selected_resolution"] = bool(lock_resolution)
        layers.append(layer)
    return layers


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
    display_rules = _solar_rules_with_display_palette(solar_rules)
    source_resolution = landscape_source_resolution(landscape_manifest)
    entry = _solar_rollup_entry(potential_manifest, resolution)
    if entry is not None and int(entry.get("source_resolution", -1)) == source_resolution:
        frame = rollup_frame_for_entry(entry)
        class_colors = {
            str(item.get("id")): str(item.get("color", "#999999"))
            for item in _class_breaks(display_rules)
        }
        if "solar_class" in frame.columns:
            frame = frame.copy()
            frame["solar_color"] = frame["solar_class"].astype(str).map(class_colors).fillna(frame.get("solar_color", "#999999"))
    else:
        frame = rollup_potential_frame(
            solar_capacity_frame(landscape_manifest, display_rules),
            resolution,
            _class_breaks(display_rules),
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


def _solar_v1_class(area_m2: float) -> dict[str, str]:
    value = max(0.0, float(area_m2 or 0.0))
    if value <= 0:
        return {"id": "none", "label": "0 m2", "color": "#991b1b"}
    if value <= 25:
        return {"id": "very_low", "label": ">0-25 m2", "color": "#f87171"}
    if value <= 100:
        return {"id": "low", "label": "25-100 m2", "color": "#fef08a"}
    if value <= 250:
        return {"id": "medium", "label": "100-250 m2", "color": "#fde047"}
    if value <= 1000:
        return {"id": "high", "label": "250-1 000 m2", "color": "#facc15"}
    return {"id": "very_high", "label": ">1 000 m2", "color": "#ca8a04"}


def _solar_v1_legend_items() -> list[dict[str, str]]:
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for value in [0, 10, 50, 150, 500, 1500]:
        item = _solar_v1_class(float(value))
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        items.append({"label": item["label"], "color": item["color"]})
    return items


@st.cache_data(show_spinner=False)
def _population_count_frame_for_resolution(path_str: str, target_resolution: int) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame(columns=["hex_id", "population"])
    raw = pd.read_csv(path)
    if "hex_id" not in raw.columns or SOLAR_V1_POPULATION_COUNT_COLUMN not in raw.columns:
        return pd.DataFrame(columns=["hex_id", "population"])

    work = raw[["hex_id", SOLAR_V1_POPULATION_COUNT_COLUMN]].copy()
    work["hex_id"] = work["hex_id"].astype(str)
    work["population"] = pd.to_numeric(work[SOLAR_V1_POPULATION_COUNT_COLUMN], errors="coerce").fillna(0.0).clip(lower=0.0)
    work = work[["hex_id", "population"]]
    source_resolutions: list[int] = []
    for value in work["hex_id"].dropna().astype(str).head(250):
        try:
            source_resolutions.append(int(h3.get_resolution(value)))
        except Exception:
            continue
    if not source_resolutions:
        return pd.DataFrame(columns=["hex_id", "population"])
    source_resolution = int(pd.Series(source_resolutions).mode().iloc[0])
    target_resolution = int(target_resolution)

    if target_resolution == source_resolution:
        return work.groupby("hex_id", as_index=False)["population"].sum()
    if target_resolution < source_resolution:
        out = work.copy()
        out["hex_id"] = out["hex_id"].map(lambda value: h3.cell_to_parent(str(value), target_resolution))
        return out.groupby("hex_id", as_index=False)["population"].sum()

    rows: list[dict[str, Any]] = []
    for row in work.itertuples(index=False):
        try:
            children = sorted(h3.cell_to_children(str(row.hex_id), target_resolution))
        except Exception:
            children = []
        if not children:
            continue
        population_share = float(row.population) / float(len(children))
        rows.extend({"hex_id": str(child), "population": population_share} for child in children)
    if not rows:
        return pd.DataFrame(columns=["hex_id", "population"])
    return pd.DataFrame(rows).groupby("hex_id", as_index=False)["population"].sum()


def _solar_v1_population_source_status() -> str:
    if SOLAR_V1_POPULATION_LAYER_PATH.exists():
        return (
            f"Befolkningsunderlag: {SOLAR_V1_POPULATION_LAYER_PATH} "
            "(regional-landscape-pipeline, H3 R10)."
        )
    return (
        f"Befolkningsunderlag saknas: {SOLAR_V1_POPULATION_LAYER_PATH}. "
        "Sätt REGIONAL_LANDSCAPE_PIPELINE_ROOT om regional-landscape-pipeline ligger på annan plats."
    )


def _solar_v1_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    resolution: int,
    panel_area_m2_per_person: float,
) -> pd.DataFrame:
    columns = [
        "hex_id",
        "class_km",
        "landscape_type",
        "population",
        "solar_v1_area_m2",
        "solar_v1_area_km2",
        "solar_v1_score",
        "solar_v1_class",
        "solar_v1_class_label",
        "solar_v1_color",
    ]
    resolution = int(resolution)
    display_geometry_path = _h3_display_geometry_path(region, resolution)
    landscape = _landscape_frame(region, landscape_manifest, resolution)
    if landscape.empty:
        return pd.DataFrame(columns=columns)
    population = _population_count_frame_for_resolution(str(SOLAR_V1_POPULATION_LAYER_PATH), resolution)
    frame = landscape[["hex_id", "class_km", "landscape_type"]].copy()
    frame = frame.merge(population, on="hex_id", how="left")
    frame["population"] = pd.to_numeric(frame["population"], errors="coerce").fillna(0.0).clip(lower=0.0)
    frame["solar_v1_area_m2"] = frame["population"] * max(0.0, float(panel_area_m2_per_person or 0.0))
    frame["solar_v1_area_km2"] = frame["solar_v1_area_m2"] / 1_000_000.0
    max_area = float(frame["solar_v1_area_m2"].max() or 0.0)
    if max_area > 0:
        frame["solar_v1_score"] = (frame["solar_v1_area_m2"].map(math.log1p) / math.log1p(max_area) * 100.0).clip(lower=0.0, upper=100.0).round(1)
    else:
        frame["solar_v1_score"] = 0.0
    classes = [_solar_v1_class(float(value)) for value in frame["solar_v1_area_m2"]]
    frame["solar_v1_class"] = [item["id"] for item in classes]
    frame["solar_v1_class_label"] = [item["label"] for item in classes]
    frame["solar_v1_color"] = [item["color"] for item in classes]
    return _filter_frame_to_display_geometries(frame, display_geometry_path).reindex(columns=columns)


@st.cache_data(show_spinner=False)
def _solar_v1_feature_collection(frame_json: str, display_geometry_path: str | None) -> dict[str, Any]:
    frame = pd.read_json(StringIO(frame_json), orient="records")
    if frame.empty:
        return {"type": "FeatureCollection", "features": []}
    display_geometries = load_h3_display_geometries(display_geometry_path) if display_geometry_path else None
    features: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        hex_id = str(row.hex_id)
        geometry = geometry_for_hex(hex_id, display_geometries)
        if geometry is None and display_geometry_path:
            continue
        if geometry is None:
            try:
                ring = [[float(lng), float(lat)] for lat, lng in h3.cell_to_boundary(hex_id)]
            except Exception:
                continue
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            geometry = {"type": "Polygon", "coordinates": [ring]}
        if not geometry.get("coordinates"):
            continue
        population = float(getattr(row, "population", 0.0) or 0.0)
        area_m2 = float(getattr(row, "solar_v1_area_m2", 0.0) or 0.0)
        popup = (
            f"<strong>{hex_id}</strong><br>"
            f"{SOLAR_SMALL_SCALE_LABEL}: {area_m2:.0f} m2<br>"
            f"Befolkning i hex: {population:.1f}<br>"
            f"Landskapstyp: {int(row.class_km)} - {row.landscape_type}"
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": hex_id,
                    "score": float(getattr(row, "solar_v1_score", 0.0) or 0.0),
                    "class": str(getattr(row, "solar_v1_class", "none")),
                    "class_label": str(getattr(row, "solar_v1_class_label", "0 m2")),
                    "fill": str(getattr(row, "solar_v1_color", "#991b1b")),
                    "popup": popup,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _solar_v1_layer(
    name: str,
    frame: pd.DataFrame,
    display_geometry_path: str | None,
) -> dict[str, Any]:
    if frame.empty:
        map_frame = pd.DataFrame(
            columns=[
                "hex_id",
                "class_km",
                "landscape_type",
                "population",
                "solar_v1_area_m2",
                "solar_v1_score",
                "solar_v1_class",
                "solar_v1_class_label",
                "solar_v1_color",
            ]
        )
    else:
        map_frame = frame[
            [
                "hex_id",
                "class_km",
                "landscape_type",
                "population",
                "solar_v1_area_m2",
                "solar_v1_score",
                "solar_v1_class",
                "solar_v1_class_label",
                "solar_v1_color",
            ]
        ].copy()
    return {
        "name": name,
        "feature_collection": _solar_v1_feature_collection(map_frame.to_json(orient="records", force_ascii=False), display_geometry_path),
        "fill_property": "fill",
        "legend_items": _solar_v1_legend_items(),
        "legend_id": "solar_v1_area",
        "legend_title": "Småskalig solyta",
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
        "layer_kind": "hex",
        "opacity_family": name,
        "opacity_label": name,
    }


def _solar_score_class(score: float) -> dict[str, str]:
    value = max(0.0, min(100.0, float(score or 0.0)))
    if value <= 0:
        return {"id": "none", "label": "0%", "color": "#991b1b"}
    if value < 25:
        return {"id": "low", "label": "0-25%", "color": "#f87171"}
    if value < 50:
        return {"id": "medium_low", "label": "25-50%", "color": "#fef08a"}
    if value < 75:
        return {"id": "medium_high", "label": "50-75%", "color": "#facc15"}
    return {"id": "high", "label": "75-100%", "color": "#ca8a04"}


def _solar_score_legend_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in [0, 10, 35, 60, 90]:
        item = _solar_score_class(float(value))
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        items.append({"label": item["label"], "color": item["color"]})
    return items


def _h3_edge_length_m(resolution: int) -> float:
    try:
        return float(h3.average_hexagon_edge_length(int(resolution), unit="m"))
    except Exception:
        return 75.0


def _population_buffer_ring_count(resolution: int, buffer_m: float) -> int:
    edge_m = max(1.0, _h3_edge_length_m(int(resolution)))
    return max(1, int(math.ceil(max(0.0, float(buffer_m or 0.0)) / edge_m)))


def _append_unique_layer(layers: list[dict[str, Any]], layer: dict[str, Any] | None) -> None:
    if layer is None:
        return
    source_layer_id = str(layer.get("source_layer_id", "") or "")
    if source_layer_id and any(str(existing.get("source_layer_id", "") or "") == source_layer_id for existing in layers):
        return
    buffer_layer_id = str(layer.get("buffer_layer_id", "") or "")
    if buffer_layer_id and any(str(existing.get("buffer_layer_id", "") or "") == buffer_layer_id for existing in layers):
        return
    name = str(layer.get("name", ""))
    if name and not source_layer_id and not buffer_layer_id and any(str(existing.get("name", "")) == name for existing in layers):
        return
    layers.append(layer)


def _dedupe_layers(layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    seen_names: set[str] = set()
    for layer in layers:
        source_layer_id = str(layer.get("source_layer_id", "") or "")
        if source_layer_id:
            if source_layer_id in seen_source_ids:
                continue
            seen_source_ids.add(source_layer_id)
        buffer_layer_id = str(layer.get("buffer_layer_id", "") or "")
        if buffer_layer_id:
            if buffer_layer_id in seen_source_ids:
                continue
            seen_source_ids.add(buffer_layer_id)
        name = str(layer.get("name", "") or "")
        if name:
            if not source_layer_id and not buffer_layer_id and name in seen_names:
                continue
            seen_names.add(name)
        deduped.append(layer)
    return deduped


def _solar_population_source_layer() -> dict[str, Any] | None:
    groups, layers, registry_meta = load_acceptance_registry()
    _ = groups
    layer_spec = layers.get(WIND_POPULATION_SOURCE_LAYER_ID)
    if layer_spec is None:
        return None
    geojson = source_geojson_for_layer(registry_meta, WIND_POPULATION_SOURCE_LAYER_ID)
    if not geojson:
        return None
    source_color = _rgb_to_hex(layer_spec.source_color)
    return {
        "name": SOLAR_POPULATION_SOURCE_LABEL,
        "source_layer_id": WIND_POPULATION_SOURCE_LAYER_ID,
        "feature_collection": geojson,
        "fill_property": "fill",
        "legend_items": [],
        "legend_id": "solar_population_source",
        "legend_title": "",
        "default_visible": False,
        "stroke_color": source_color,
        "fill_color": source_color,
        "stroke_opacity": 0.85,
        "fill_opacity": 0.28,
        "weight": 1.2,
        "point_radius": int(layer_spec.point_radius),
        "use_global_opacity": False,
        "layer_kind": "vector",
    }


def _solar_population_runtime_result(buffer_m: float) -> dict[str, Any] | None:
    try:
        config = {
            "groups": {
                "settlement": {
                    "active_layer_ids": [WIND_POPULATION_SOURCE_LAYER_ID],
                    "analysis_value_m": int(round(float(buffer_m or 0.0))),
                }
            }
        }
        return run_geometry_runtime(json.dumps(config, sort_keys=True, ensure_ascii=False))
    except Exception:
        return None


def _solar_population_buffer_geojson(buffer_m: float) -> dict[str, Any] | None:
    runtime_result = _solar_population_runtime_result(float(buffer_m or 0.0))
    runtime_group = (runtime_result or {}).get("groups", {}).get("settlement") if isinstance(runtime_result, dict) else None
    if not isinstance(runtime_group, dict):
        return None
    geojson = runtime_group.get("geojson")
    return geojson if isinstance(geojson, dict) else None


def _solar_population_buffer_frame(
    region: dict[str, Any],
    target_resolution: int,
    buffer_m: float,
) -> pd.DataFrame:
    if float(buffer_m or 0.0) <= 0:
        return pd.DataFrame(columns=["hex_id", "population_buffer_m", "buffer_ring_count"])
    display_geometry_path = _h3_display_geometry_path(region, int(target_resolution))
    if not display_geometry_path:
        return pd.DataFrame(columns=["hex_id", "population_buffer_m", "buffer_ring_count"])
    buffer_geojson = _solar_population_buffer_geojson(float(buffer_m or 0.0))
    if not buffer_geojson:
        return pd.DataFrame(columns=["hex_id", "population_buffer_m", "buffer_ring_count"])
    share = runtime_combined_hex_frame(buffer_geojson, int(target_resolution), [])
    if share.empty:
        return pd.DataFrame(columns=["hex_id", "population_buffer_m", "buffer_ring_count", "buffer_share_pct"])
    share = _filter_frame_to_display_geometries(share, display_geometry_path)
    if share.empty:
        return pd.DataFrame(columns=["hex_id", "population_buffer_m", "buffer_ring_count", "buffer_share_pct"])
    score_col = "wind_score" if "wind_score" in share.columns else "potential_area_share_pct"
    share["buffer_share_pct"] = pd.to_numeric(share.get(score_col), errors="coerce").fillna(0.0)
    share = share[share["buffer_share_pct"].gt(0.0)].copy()
    share["population_buffer_m"] = float(buffer_m or 0.0)
    share["buffer_ring_count"] = 0
    return share[["hex_id", "population_buffer_m", "buffer_ring_count", "buffer_share_pct"]].copy()


def _solar_population_buffer_layer(
    region: dict[str, Any],
    target_resolution: int,
    buffer_m: float,
) -> dict[str, Any] | None:
    _ = region
    _ = target_resolution
    buffer_geojson = _solar_population_buffer_geojson(float(buffer_m or 0.0))
    if not buffer_geojson:
        return None
    features = buffer_geojson.get("features") if isinstance(buffer_geojson, dict) else None
    if not isinstance(features, list) or not features:
        return None
    for feature in features:
        props = feature.setdefault("properties", {})
        props["fill"] = "#14b8a6"
        props["popup"] = (
            f"<strong>{SOLAR_POPULATION_BUFFER_LABEL}</strong><br>"
            f"Avstånd: {float(buffer_m or 0.0):.0f} m<br>"
            "Totalt avstånd från befolkningspunkter. Källan har 100 m grundbuffert."
        )
        props["tooltip_title"] = SOLAR_POPULATION_BUFFER_LABEL
        props["tooltip_body"] = f"{float(buffer_m or 0.0):.0f} m total buffert"
    return {
        "name": SOLAR_POPULATION_BUFFER_LABEL,
        "buffer_layer_id": f"{WIND_POPULATION_SOURCE_LAYER_ID}:buffer:{int(round(float(buffer_m or 0.0)))}",
        "feature_collection": buffer_geojson,
        "fill_property": "fill",
        "legend_items": [{"label": "Polygonbuffert runt befolkningspunkter", "color": "#14b8a6"}],
        "legend_id": "solar_population_buffer",
        "legend_title": "",
        "default_visible": False,
        "stroke_color": "#0f766e",
        "fill_color": "#14b8a6",
        "stroke_opacity": 0.48,
        "fill_opacity": 0.20,
        "weight": 0.55,
        "point_radius": 4,
        "use_global_opacity": False,
        "z_index": 455,
        "layer_kind": "vector",
    }


def _solar_protected_source_layers(layer_ids: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    groups, layers, registry_meta = load_acceptance_registry()
    _ = groups
    map_layers: list[dict[str, Any]] = []
    for layer_id in _solar_available_protected_layer_ids(layer_ids):
        layer_spec = layers.get(layer_id)
        if layer_spec is None:
            continue
        geojson = source_geojson_for_layer(registry_meta, layer_id)
        if not geojson:
            continue
        source_color = _rgb_to_hex(layer_spec.source_color)
        map_layers.append(
            {
                "name": f"{SOLAR_PROTECTED_SOURCE_LABEL}: {layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label)}",
                "source_layer_id": layer_id,
                "feature_collection": geojson,
                "fill_property": "fill",
                "legend_items": [],
                "legend_id": f"solar_protected_source_{layer_id}",
                "legend_title": "",
                "default_visible": False,
                "stroke_color": source_color,
                "fill_color": source_color,
                "stroke_opacity": 0.82,
                "fill_opacity": 0.22,
                "weight": 1.4,
                "point_radius": int(layer_spec.point_radius),
                "use_global_opacity": False,
                "z_index": 456,
                "layer_kind": "vector",
            }
        )
    return map_layers


def _solar_available_protected_layer_ids(layer_ids: list[str] | tuple[str, ...] | set[str] | None = None) -> tuple[str, ...]:
    _, layers, registry_meta = load_acceptance_registry()
    requested = list(SOLAR_PROTECTED_LAYER_IDS) if layer_ids is None else [str(layer_id) for layer_id in layer_ids]
    allowed = set(SOLAR_PROTECTED_LAYER_IDS)
    available: list[str] = []
    for layer_id in requested:
        if layer_id not in allowed or layer_id in available:
            continue
        if layer_id not in layers:
            continue
        if source_geojson_for_layer(registry_meta, layer_id):
            available.append(layer_id)
    return tuple(available)


def _solar_protected_layer_options() -> list[dict[str, Any]]:
    _, layers, registry_meta = load_acceptance_registry()
    availability = _wind_layer_status_lookup(registry_meta)
    options: list[dict[str, Any]] = []
    for layer_id in SOLAR_PROTECTED_LAYER_IDS:
        layer_spec = layers.get(layer_id)
        if layer_spec is None:
            continue
        status = availability.get(layer_id, {})
        ready = (
            bool(status.get("geojson_ready"))
            and bool(status.get("source_exists"))
            and int(status.get("feature_count", 0) or 0) > 0
            and str(status.get("status", "")) == "ok"
        )
        message = str(status.get("message", "") or layer_note(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.note) or "")
        options.append(
            {
                "id": layer_id,
                "label": layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label),
                "ready": bool(ready),
                "message": message,
            }
        )
    return options


def _solar_protected_runtime_result(
    buffer_m: float,
    layer_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    selected_layer_ids = _solar_available_protected_layer_ids(layer_ids)
    if not selected_layer_ids:
        return None
    try:
        config = {
            "groups": {
                SOLAR_PROTECTED_GROUP_ID: {
                    "active_layer_ids": list(selected_layer_ids),
                    "analysis_value_m": int(round(max(0.0, float(buffer_m or 0.0)))),
                }
            }
        }
        return run_geometry_runtime(json.dumps(config, sort_keys=True, ensure_ascii=False))
    except Exception:
        return None


def _solar_protected_buffer_geojson(
    buffer_m: float,
    layer_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    runtime_result = _solar_protected_runtime_result(float(buffer_m or 0.0), layer_ids)
    runtime_group = (runtime_result or {}).get("groups", {}).get(SOLAR_PROTECTED_GROUP_ID) if isinstance(runtime_result, dict) else None
    if not isinstance(runtime_group, dict):
        return None
    geojson = runtime_group.get("geojson")
    return geojson if isinstance(geojson, dict) else None


def _solar_protected_buffer_frame(
    region: dict[str, Any],
    target_resolution: int,
    buffer_m: float,
    layer_ids: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    display_geometry_path = _h3_display_geometry_path(region, int(target_resolution))
    if not display_geometry_path:
        return pd.DataFrame(columns=["hex_id", "protected_buffer_m", "protected_buffer_share_pct"])
    buffer_geojson = _solar_protected_buffer_geojson(float(buffer_m or 0.0), layer_ids)
    if not buffer_geojson:
        return pd.DataFrame(columns=["hex_id", "protected_buffer_m", "protected_buffer_share_pct"])
    share = runtime_combined_hex_frame(buffer_geojson, int(target_resolution), [])
    if share.empty:
        return pd.DataFrame(columns=["hex_id", "protected_buffer_m", "protected_buffer_share_pct"])
    share = _filter_frame_to_display_geometries(share, display_geometry_path)
    if share.empty:
        return pd.DataFrame(columns=["hex_id", "protected_buffer_m", "protected_buffer_share_pct"])
    score_col = "wind_score" if "wind_score" in share.columns else "potential_area_share_pct"
    share["protected_buffer_share_pct"] = pd.to_numeric(share.get(score_col), errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
    share = share[share["protected_buffer_share_pct"].gt(0.0)].copy()
    share["protected_buffer_m"] = float(buffer_m or 0.0)
    return share[["hex_id", "protected_buffer_m", "protected_buffer_share_pct"]].copy()


def _solar_protected_buffer_layer(
    buffer_m: float,
    layer_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    selected_layer_ids = _solar_available_protected_layer_ids(layer_ids)
    buffer_geojson = _solar_protected_buffer_geojson(float(buffer_m or 0.0), selected_layer_ids)
    if not buffer_geojson:
        return None
    features = buffer_geojson.get("features") if isinstance(buffer_geojson, dict) else None
    if not isinstance(features, list) or not features:
        return None
    for feature in features:
        props = feature.setdefault("properties", {})
        props["fill"] = "#16a34a"
        props["popup"] = (
            f"<strong>{SOLAR_PROTECTED_BUFFER_LABEL}</strong><br>"
            f"Buffert: {float(buffer_m or 0.0):.0f} m<br>"
            "Skyddade områden används som avdrag i storskalig solpotential."
        )
        props["tooltip_title"] = SOLAR_PROTECTED_BUFFER_LABEL
        props["tooltip_body"] = f"{float(buffer_m or 0.0):.0f} m buffert"
    return {
        "name": SOLAR_PROTECTED_BUFFER_LABEL,
        "buffer_layer_id": (
            f"{SOLAR_PROTECTED_GROUP_ID}:buffer:{int(round(float(buffer_m or 0.0)))}:"
            f"{'_'.join(selected_layer_ids) if selected_layer_ids else 'none'}"
        ),
        "feature_collection": buffer_geojson,
        "fill_property": "fill",
        "legend_items": [{"label": "Buffert runt skyddade områden", "color": "#16a34a"}],
        "legend_id": "solar_protected_buffer",
        "legend_title": "",
        "default_visible": False,
        "stroke_color": "#166534",
        "fill_color": "#16a34a",
        "stroke_opacity": 0.56,
        "fill_opacity": 0.18,
        "weight": 0.75,
        "point_radius": 4,
        "use_global_opacity": False,
        "z_index": 458,
        "layer_kind": "vector",
    }


@st.cache_data(show_spinner=False)
def _solar_large_scale_h3_r10_area_frame(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    columns = ["hex_id", "potential_area_m2", "potential_area_km2", "potential_area_share_pct"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        raw = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=columns)
    if "hex_id" not in raw.columns or "potential_area_m2" not in raw.columns:
        return pd.DataFrame(columns=columns)
    work = raw.copy()
    work["hex_id"] = work["hex_id"].astype(str)
    work["potential_area_m2"] = pd.to_numeric(work["potential_area_m2"], errors="coerce").fillna(0.0).clip(lower=0.0)
    work["potential_area_km2"] = work["potential_area_m2"] / 1_000_000.0
    if "potential_area_share_pct" in work.columns:
        work["potential_area_share_pct"] = pd.to_numeric(work["potential_area_share_pct"], errors="coerce").fillna(0.0)
    else:
        hex_area_m2 = float(h3_hex_area_km2(10) * 1_000_000.0)
        work["potential_area_share_pct"] = work["potential_area_m2"] / max(hex_area_m2, 1e-9) * 100.0
    work["potential_area_share_pct"] = work["potential_area_share_pct"].clip(lower=0.0, upper=100.0)
    return work[work["potential_area_m2"].gt(0.0)].reindex(columns=columns)


def _solar_large_scale_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    resolution: int,
    population_buffer_m: float,
    protected_buffer_m: float | None = None,
    protected_layer_ids: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    target_resolution = int(resolution)
    landscape = _landscape_frame(region, landscape_manifest, target_resolution)
    columns = [
        "hex_id",
        "class_km",
        "landscape_type",
        "potential_area_m2",
        "potential_area_km2",
        "potential_area_share_pct",
        "protected_buffer_share_pct",
        "solar_score",
        "solar_class",
        "solar_class_label",
        "solar_color",
    ]
    if landscape.empty:
        return pd.DataFrame(columns=columns)

    polygon_path = _solar_large_scale_polygon_path(population_buffer_m)
    polygon_geojson = _solar_large_scale_polygon_geojson(str(polygon_path), float(population_buffer_m or 0.0))
    if not polygon_geojson:
        return pd.DataFrame(columns=columns)

    area = runtime_combined_hex_frame(polygon_geojson, target_resolution, [])
    if area.empty:
        return pd.DataFrame(columns=columns)
    area = area[["hex_id", "wind_score"]].rename(columns={"wind_score": "potential_area_share_pct"}).copy()
    area["hex_id"] = area["hex_id"].astype(str)
    area["potential_area_share_pct"] = pd.to_numeric(area["potential_area_share_pct"], errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)

    source = landscape[["hex_id", "class_km", "landscape_type"]].copy()
    work = source.merge(area, on="hex_id", how="left")
    work["potential_area_share_pct"] = pd.to_numeric(work["potential_area_share_pct"], errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
    if work.empty:
        return pd.DataFrame(columns=columns)

    work["protected_buffer_share_pct"] = 0.0
    if protected_buffer_m is not None:
        protected = _solar_protected_buffer_frame(
            region,
            target_resolution,
            float(protected_buffer_m or 0.0),
            protected_layer_ids,
        )
        if not protected.empty:
            protected = protected[["hex_id", "protected_buffer_share_pct"]].copy()
            work = work.merge(protected, on="hex_id", how="left", suffixes=("", "_protected"))
            if "protected_buffer_share_pct_protected" in work.columns:
                work["protected_buffer_share_pct"] = pd.to_numeric(
                    work["protected_buffer_share_pct_protected"],
                    errors="coerce",
                ).fillna(0.0).clip(lower=0.0, upper=100.0)
                work = work.drop(columns=["protected_buffer_share_pct_protected"])
        work["potential_area_share_pct"] = (
            work["potential_area_share_pct"] - work["protected_buffer_share_pct"]
        ).clip(lower=0.0, upper=100.0)

    hex_area_m2 = float(h3_hex_area_km2(target_resolution) * 1_000_000.0)
    work["potential_area_m2"] = (work["potential_area_share_pct"] / 100.0 * hex_area_m2).clip(lower=0.0, upper=hex_area_m2)
    work["potential_area_km2"] = work["potential_area_m2"] / 1_000_000.0
    work["solar_score"] = work["potential_area_share_pct"].round(1)
    classes = [_solar_score_class(float(value)) for value in work["solar_score"]]
    work["solar_class"] = [item["id"] for item in classes]
    work["solar_class_label"] = [item["label"] for item in classes]
    work["solar_color"] = [item["color"] for item in classes]
    return _filter_frame_to_display_geometries(work.reindex(columns=columns), _h3_display_geometry_path(region, target_resolution))


def _solar_large_scale_polygon_path(population_buffer_m: float) -> Path:
    try:
        distance = float(population_buffer_m or 0.0)
    except Exception:
        distance = 0.0
    if distance <= 0:
        rounded = 0
    else:
        rounded = int(round(distance / 25.0) * 25)
        rounded = max(100, min(500, rounded))
    return SOLAR_LARGE_SCALE_POLYGON_DIR / f"markblokke_bornholm_outside_population_{rounded:03d}m.geojson"


@st.cache_data(show_spinner=False)
def _solar_large_scale_polygon_geojson(path_str: str, population_buffer_m: float) -> dict[str, Any] | None:
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    features: list[dict[str, Any]] = []
    for feature in data.get("features") or []:
        if not isinstance(feature, dict) or not feature.get("geometry"):
            continue
        copied = json.loads(json.dumps(feature))
        props = copied.setdefault("properties", {})
        buffer_m = props.get("buffer_m", population_buffer_m)
        try:
            buffer_label = f"{float(buffer_m):.0f} m"
        except Exception:
            buffer_label = "-"
        props["fill"] = "#ca8a04"
        props["popup"] = (
            f"<strong>{SOLAR_POTENTIAL_POLYGON_LABEL}</strong><br>"
            f"Grupp: {SOLAR_LARGE_SCALE_LABEL}<br>"
            "Polygonkälla: Markblokke 2026<br>"
            f"Avstånd till befolkning: {buffer_label}"
        )
        props["tooltip_title"] = SOLAR_POTENTIAL_POLYGON_LABEL
        props["tooltip_body"] = SOLAR_LARGE_SCALE_LABEL
        features.append(copied)
    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}


def _combined_solar_hex_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    resolution: int,
    small_frame: pd.DataFrame,
    large_frame: pd.DataFrame,
) -> pd.DataFrame:
    base = _landscape_frame(region, landscape_manifest, int(resolution))[["hex_id", "class_km", "landscape_type"]].copy()
    if base.empty:
        return pd.DataFrame()
    base["small_score"] = 0.0
    base["large_score"] = 0.0
    base["small_area_m2"] = 0.0
    base["large_area_m2"] = 0.0
    if not small_frame.empty:
        small = small_frame[["hex_id", "solar_v1_score", "solar_v1_area_m2"]].rename(
            columns={"solar_v1_score": "small_score", "solar_v1_area_m2": "small_area_m2"}
        ).copy()
        base = base.drop(columns=["small_score", "small_area_m2"]).merge(small, on="hex_id", how="left")
        base["small_score"] = pd.to_numeric(base["small_score"], errors="coerce").fillna(0.0)
        base["small_area_m2"] = pd.to_numeric(base["small_area_m2"], errors="coerce").fillna(0.0).clip(lower=0.0)
    if not large_frame.empty:
        large = large_frame[["hex_id", "solar_score", "potential_area_m2"]].rename(
            columns={"solar_score": "large_score", "potential_area_m2": "large_area_m2"}
        ).copy()
        base = base.drop(columns=["large_score", "large_area_m2"]).merge(large, on="hex_id", how="left")
        base["large_score"] = pd.to_numeric(base["large_score"], errors="coerce").fillna(0.0)
        base["large_area_m2"] = pd.to_numeric(base["large_area_m2"], errors="coerce").fillna(0.0).clip(lower=0.0)
    hex_area_m2 = float(h3_hex_area_km2(int(resolution)) * 1_000_000.0)
    base["potential_area_m2"] = (base["small_area_m2"] + base["large_area_m2"]).clip(lower=0.0, upper=hex_area_m2)
    base["potential_area_km2"] = base["potential_area_m2"] / 1_000_000.0
    base["potential_area_share_pct"] = (base["potential_area_m2"] / max(hex_area_m2, 1e-9) * 100.0).clip(lower=0.0, upper=100.0)
    base["solar_score"] = base["potential_area_share_pct"].round(1)
    base["solar_group"] = "Ingen aktiv solpotential"
    base.loc[base["large_area_m2"].gt(base["small_area_m2"]) & base["large_area_m2"].gt(0), "solar_group"] = SOLAR_LARGE_SCALE_LABEL
    base.loc[base["small_area_m2"].ge(base["large_area_m2"]) & base["small_area_m2"].gt(0), "solar_group"] = SOLAR_SMALL_SCALE_LABEL
    classes = [_solar_score_class(float(value)) for value in base["solar_score"]]
    base["solar_class"] = [item["id"] for item in classes]
    base["solar_class_label"] = [item["label"] for item in classes]
    base["solar_color"] = [item["color"] for item in classes]
    return _filter_frame_to_display_geometries(base, _h3_display_geometry_path(region, int(resolution)))


def _combined_solar_hex_layer(
    name: str,
    frame: pd.DataFrame,
    display_geometry_path: str | None,
) -> dict[str, Any] | None:
    if frame.empty or not display_geometry_path:
        return None
    display_geometries = load_h3_display_geometries(display_geometry_path)
    features: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        geometry = display_geometries.get(str(row.hex_id))
        if geometry is None:
            continue
        score = float(getattr(row, "solar_score", 0.0) or 0.0)
        area_m2 = float(getattr(row, "potential_area_m2", 0.0) or 0.0)
        area_share_pct = float(getattr(row, "potential_area_share_pct", score) or 0.0)
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": str(row.hex_id),
                    "fill": str(getattr(row, "solar_color", "#991b1b")),
                    "popup": (
                        (
                            f"<strong>{name}</strong><br>"
                            f"Area share: {area_share_pct:.1f}%<br>"
                            f"Potentiell solyta: {area_m2:,.0f} m2<br>"
                            f"Dominerande grupp: {getattr(row, 'solar_group', '-') }<br>"
                            f"Landskapstyp: {getattr(row, 'landscape_type', '-') }<br>"
                            f"H3: {row.hex_id}"
                        ).replace(",", " ")
                    ),
                    "tooltip_title": f"{name}: {area_share_pct:.1f}%",
                    "tooltip_body": f"{area_m2:,.0f} m2 - {getattr(row, 'solar_group', '')}".replace(",", " "),
                },
            }
        )
    if not features:
        return None
    return {
        "name": name,
        "feature_collection": {"type": "FeatureCollection", "features": features},
        "fill_property": "fill",
        "legend_items": _solar_score_legend_items(),
        "legend_id": "solar_combined_hex",
        "legend_title": SOLAR_POTENTIAL_HEX_LABEL,
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
        "layer_kind": "hex",
        "opacity_family": name,
        "opacity_label": name,
    }


def _solar_potential_polygon_layer(
    small_buffer_geojson: dict[str, Any] | None,
    large_frame: pd.DataFrame,
    large_polygon_geojson: dict[str, Any] | None,
) -> dict[str, Any] | None:
    features: list[dict[str, Any]] = []
    if isinstance(small_buffer_geojson, dict):
        for feature in small_buffer_geojson.get("features") or []:
            if not isinstance(feature, dict) or not feature.get("geometry"):
                continue
            copied = json.loads(json.dumps(feature))
            props = copied.setdefault("properties", {})
            props["fill"] = "#facc15"
            props["popup"] = (
                f"<strong>{SOLAR_POTENTIAL_POLYGON_LABEL}</strong><br>"
                f"Grupp: {SOLAR_SMALL_SCALE_LABEL}<br>"
                "Faktisk polygonbuffert runt befolkningspunkter."
            )
            props["tooltip_title"] = SOLAR_POTENTIAL_POLYGON_LABEL
            props["tooltip_body"] = SOLAR_SMALL_SCALE_LABEL
            features.append(copied)

    if not large_frame.empty and isinstance(large_polygon_geojson, dict):
        has_large_score = pd.to_numeric(large_frame.get("solar_score"), errors="coerce").fillna(0.0).gt(0.0).any()
        if has_large_score:
            for feature in large_polygon_geojson.get("features") or []:
                if not isinstance(feature, dict) or not feature.get("geometry"):
                    continue
                copied = json.loads(json.dumps(feature))
                props = copied.setdefault("properties", {})
                props.setdefault("fill", "#ca8a04")
                props.setdefault(
                    "popup",
                    (
                        f"<strong>{SOLAR_POTENTIAL_POLYGON_LABEL}</strong><br>"
                        f"Grupp: {SOLAR_LARGE_SCALE_LABEL}<br>"
                        "Polygonkälla: Markblokke 2026"
                    ),
                )
                props["tooltip_title"] = SOLAR_POTENTIAL_POLYGON_LABEL
                props["tooltip_body"] = SOLAR_LARGE_SCALE_LABEL
                features.append(copied)

    if not features:
        return None
    legend_items = []
    if isinstance(small_buffer_geojson, dict) and small_buffer_geojson.get("features"):
        legend_items.append({"label": SOLAR_SMALL_SCALE_LABEL, "color": "#facc15"})
    if isinstance(large_polygon_geojson, dict) and large_polygon_geojson.get("features"):
        legend_items.append({"label": SOLAR_LARGE_SCALE_LABEL, "color": "#ca8a04"})
    if not legend_items:
        legend_items = [
            {"label": SOLAR_SMALL_SCALE_LABEL, "color": "#facc15"},
            {"label": SOLAR_LARGE_SCALE_LABEL, "color": "#ca8a04"},
        ]
    return {
        "name": SOLAR_POTENTIAL_POLYGON_LABEL,
        "feature_collection": {"type": "FeatureCollection", "features": features},
        "fill_property": "fill",
        "legend_items": legend_items,
        "legend_id": "solar_potential_polygon",
        "legend_title": SOLAR_POTENTIAL_POLYGON_LABEL,
        "default_visible": True,
        "stroke_color": "#854d0e",
        "fill_color": "#facc15",
        "stroke_opacity": 0.72,
        "fill_opacity": 0.18,
        "weight": 1.3,
        "point_radius": 6,
        "dash_array": "6 4",
        "use_global_opacity": False,
        "z_index": 442,
        "layer_kind": "vector",
    }


def _solar_establishment_frame(
    small_frame: pd.DataFrame,
    large_frame: pd.DataFrame,
    solar_area_need_km2: float,
    solar_twh_need: float,
    solar_km2_per_twh: float,
    hex_area_km2: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not small_frame.empty:
        small = small_frame[pd.to_numeric(small_frame.get("solar_v1_area_km2"), errors="coerce").fillna(0.0).gt(0.0)].copy()
        for row in small.itertuples(index=False):
            rows.append(
                {
                    "hex_id": str(row.hex_id),
                    "source_group": SOLAR_SMALL_SCALE_LABEL,
                    "potential_score": float(getattr(row, "solar_v1_score", 0.0) or 0.0),
                    "potential_area_km2": float(getattr(row, "solar_v1_area_km2", 0.0) or 0.0),
                    "outside_et": False,
                    "expansion_ring": 0,
                    "sort_group": 0,
                }
            )
    if not large_frame.empty:
        large = large_frame[pd.to_numeric(large_frame.get("solar_score"), errors="coerce").fillna(0.0).gt(0.0)].copy()
        for row in large.itertuples(index=False):
            potential_area_km2 = float(getattr(row, "potential_area_km2", 0.0) or 0.0)
            if potential_area_km2 <= 0:
                potential_area_km2 = float(getattr(row, "potential_area_m2", 0.0) or 0.0) / 1_000_000.0
            if potential_area_km2 <= 0:
                continue
            rows.append(
                {
                    "hex_id": str(row.hex_id),
                    "source_group": SOLAR_LARGE_SCALE_LABEL,
                    "potential_score": float(getattr(row, "solar_score", 0.0) or 0.0),
                    "potential_area_km2": min(float(hex_area_km2), potential_area_km2),
                    "outside_et": False,
                    "expansion_ring": 0,
                    "sort_group": 1,
                }
            )
    if not rows or float(solar_area_need_km2 or 0.0) <= 0:
        return pd.DataFrame(), {
            "selected_area_km2": 0.0,
            "unmet_area_km2": max(0.0, float(solar_area_need_km2 or 0.0)),
            "selected_hex_count": 0,
        }
    candidates = pd.DataFrame(rows)
    candidates = candidates.sort_values(["sort_group", "potential_score", "potential_area_km2", "hex_id"], ascending=[True, False, False, True])
    remaining = float(solar_area_need_km2 or 0.0)
    selected_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(candidates.itertuples(index=False), start=1):
        available_area = max(0.0, float(row.potential_area_km2 or 0.0))
        allocated_area = min(available_area, remaining)
        if allocated_area <= 0:
            continue
        if solar_km2_per_twh > 0 and math.isfinite(float(solar_km2_per_twh)):
            allocated_twh = allocated_area / float(solar_km2_per_twh)
        elif solar_area_need_km2 > 0:
            allocated_twh = float(solar_twh_need or 0.0) * allocated_area / float(solar_area_need_km2)
        else:
            allocated_twh = 0.0
        remaining = max(0.0, remaining - allocated_area)
        selected_rows.append(
            {
                "hex_id": str(row.hex_id),
                "selected_rank": int(rank),
                "source_group": str(row.source_group),
                "potential_score": float(row.potential_score or 0.0),
                "potential_area_km2": available_area,
                "allocated_area_km2": allocated_area,
                "allocated_twh": allocated_twh,
                "allocated_gwh": allocated_twh * 1000.0,
                "allocated_hex_share_pct": (allocated_area / max(float(hex_area_km2), 1e-9)) * 100.0,
                "remaining_area_after_km2": remaining,
                "outside_et": bool(getattr(row, "outside_et", False)),
                "expansion_ring": int(getattr(row, "expansion_ring", 0) or 0),
                "allocation_phase": "Inom LP",
            }
        )
        if remaining <= 1e-9:
            break
    selected = pd.DataFrame(selected_rows)
    stats = {
        "selected_area_km2": float(selected["allocated_area_km2"].sum()) if not selected.empty else 0.0,
        "unmet_area_km2": remaining,
        "selected_hex_count": int(len(selected)),
        "selected_twh": float(selected["allocated_twh"].sum()) if not selected.empty else 0.0,
        "available_candidate_hex": int(len(candidates)),
        "available_candidate_area_km2": float(candidates["potential_area_km2"].sum()),
    }
    return selected, stats


def _rollup_solar_establishment_frame(
    selected: pd.DataFrame,
    target_resolution: int,
    source_resolution: int,
) -> pd.DataFrame:
    if selected.empty or int(target_resolution) >= int(source_resolution):
        return selected.copy()

    work = selected.copy()

    def _numeric_column(column: str, default: float = 0.0) -> pd.Series:
        if column in work.columns:
            return pd.to_numeric(work[column], errors="coerce").fillna(default)
        return pd.Series(default, index=work.index, dtype="float64")

    work["hex_id"] = work["hex_id"].astype(str).map(lambda value: h3.cell_to_parent(value, int(target_resolution)))
    work["allocated_area_km2"] = _numeric_column("allocated_area_km2", 0.0)
    work["potential_area_km2"] = _numeric_column("potential_area_km2", 0.0)
    work["allocated_twh"] = _numeric_column("allocated_twh", 0.0)
    work["selected_rank"] = _numeric_column("selected_rank", 0.0).astype(int)
    work["potential_score"] = _numeric_column("potential_score", 0.0)
    work["expansion_ring"] = _numeric_column("expansion_ring", 0.0).astype(int)
    if "outside_et" not in work.columns:
        work["outside_et"] = False
    if "source_group" not in work.columns:
        work["source_group"] = ""
    work["outside_et"] = work["outside_et"].fillna(False).astype(bool)
    work["outside_area_km2"] = work["allocated_area_km2"].where(work["outside_et"], 0.0)
    work["inside_area_km2"] = work["allocated_area_km2"].where(~work["outside_et"], 0.0)

    def _source_group_label(values: pd.Series) -> str:
        labels = [str(value) for value in values.dropna().tolist() if str(value)]
        unique = list(dict.fromkeys(labels))
        return ", ".join(unique[:3])

    rolled = (
        work.groupby("hex_id", as_index=False)
        .agg(
            selected_rank=("selected_rank", "min"),
            source_group=("source_group", _source_group_label),
            potential_score=("potential_score", "max"),
            potential_area_km2=("potential_area_km2", "sum"),
            allocated_area_km2=("allocated_area_km2", "sum"),
            allocated_twh=("allocated_twh", "sum"),
            outside_area_km2=("outside_area_km2", "sum"),
            inside_area_km2=("inside_area_km2", "sum"),
            expansion_ring=("expansion_ring", "max"),
        )
        .sort_values(["selected_rank", "hex_id"])
        .reset_index(drop=True)
    )
    hex_area = h3_hex_area_km2(int(target_resolution))
    rolled["outside_et"] = rolled["outside_area_km2"].gt(rolled["inside_area_km2"])
    rolled["allocation_phase"] = rolled["outside_et"].map(lambda value: "Utanför LP" if value else "Inom LP")
    rolled["allocated_hex_share_pct"] = (rolled["allocated_area_km2"] / max(hex_area, 1e-9) * 100.0).clip(lower=0.0, upper=100.0)
    rolled["remaining_area_after_km2"] = 0.0
    rolled["allocated_gwh"] = rolled["allocated_twh"] * 1000.0
    return rolled


def _expand_solar_area_outside_lp(
    source_frame: pd.DataFrame,
    selected_frame: pd.DataFrame,
    proposal_stats: dict[str, Any],
    display_geometry_path: str | None,
    hex_area_km2: float,
    solar_twh_need: float,
    solar_area_need_km2: float,
    solar_km2_per_twh: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if source_frame.empty or not display_geometry_path or hex_area_km2 <= 0:
        return selected_frame, proposal_stats

    shortage = float(proposal_stats.get("unmet_area_km2", 0.0) or 0.0)
    proposal_stats["lp_selected_area_km2"] = float(proposal_stats.get("selected_area_km2", 0.0) or 0.0)
    proposal_stats["lp_unmet_area_km2"] = max(0.0, shortage)
    if shortage <= 1e-9:
        proposal_stats.setdefault("outside_selected_area_km2", 0.0)
        proposal_stats.setdefault("outside_hex_count", 0)
        proposal_stats.setdefault("max_expansion_ring", 0)
        return selected_frame, proposal_stats

    display_hexes = set(load_h3_display_geometries(display_geometry_path))
    if not display_hexes:
        return selected_frame, proposal_stats

    work = source_frame.copy()
    work["hex_id"] = work["hex_id"].astype(str)
    work["solar_score"] = pd.to_numeric(work.get("solar_score"), errors="coerce").fillna(0.0)
    lp_hexes = set(work.loc[work["solar_score"].gt(0.0), "hex_id"].astype(str)) & display_hexes
    selected_hexes = set(selected_frame.get("hex_id", pd.Series(dtype=str)).astype(str)) if not selected_frame.empty else set()
    anchor_hexes = (selected_hexes or lp_hexes) & display_hexes

    neighbor_map = _wind_runtime_hex_neighbor_map(display_geometry_path)
    distance_lookup: dict[str, int] = {}
    if anchor_hexes:
        visited = set(anchor_hexes)
        frontier: deque[tuple[str, int]] = deque((hex_id, 0) for hex_id in anchor_hexes)
        while frontier:
            current, distance = frontier.popleft()
            for neighbor in neighbor_map.get(current, []):
                neighbor = str(neighbor)
                if neighbor not in display_hexes or neighbor in visited:
                    continue
                visited.add(neighbor)
                distance_lookup[neighbor] = distance + 1
                frontier.append((neighbor, distance + 1))

    outside_hexes = sorted(display_hexes - lp_hexes)
    outside = pd.DataFrame({"hex_id": outside_hexes})
    if outside.empty:
        return selected_frame, proposal_stats
    outside["expansion_ring"] = outside["hex_id"].map(distance_lookup).fillna(999999).astype(int)
    outside = outside[outside["expansion_ring"].lt(999999)].copy()
    if outside.empty:
        return selected_frame, proposal_stats
    outside = outside.sort_values(["expansion_ring", "hex_id"], ascending=[True, True]).reset_index(drop=True)

    remaining = shortage
    start_rank = int(len(selected_frame)) + 1
    rows: list[dict[str, Any]] = []
    for offset, row in enumerate(outside.itertuples(index=False), start=0):
        allocated_area = min(float(hex_area_km2), max(0.0, remaining))
        if allocated_area <= 0:
            break
        if solar_km2_per_twh > 0 and math.isfinite(float(solar_km2_per_twh)):
            allocated_twh = allocated_area / float(solar_km2_per_twh)
        elif solar_area_need_km2 > 0:
            allocated_twh = float(solar_twh_need or 0.0) * allocated_area / float(solar_area_need_km2)
        else:
            allocated_twh = 0.0
        remaining = max(0.0, remaining - allocated_area)
        rows.append(
            {
                "hex_id": str(row.hex_id),
                "selected_rank": start_rank + offset,
                "source_group": "Utanför LP",
                "potential_score": 0.0,
                "potential_area_km2": 0.0,
                "allocated_area_km2": allocated_area,
                "allocated_twh": allocated_twh,
                "allocated_gwh": allocated_twh * 1000.0,
                "allocated_hex_share_pct": (allocated_area / max(float(hex_area_km2), 1e-9)) * 100.0,
                "remaining_area_after_km2": remaining,
                "outside_et": True,
                "expansion_ring": int(row.expansion_ring),
                "allocation_phase": "Utanför LP",
            }
        )
        if remaining <= 1e-9:
            break

    if not rows:
        return selected_frame, proposal_stats

    outside_frame = pd.DataFrame(rows)
    if "outside_et" not in selected_frame.columns and not selected_frame.empty:
        selected_frame = selected_frame.copy()
        selected_frame["outside_et"] = False
    combined = pd.concat([selected_frame, outside_frame], ignore_index=True, sort=False)
    outside_area = float(outside_frame["allocated_area_km2"].sum())
    proposal_stats.update(
        {
            "selected_area_km2": float(proposal_stats.get("lp_selected_area_km2", 0.0) or 0.0) + outside_area,
            "unmet_area_km2": max(0.0, remaining),
            "selected_hex_count": int(len(combined)),
            "outside_selected_area_km2": outside_area,
            "outside_hex_count": int(len(outside_frame)),
            "outside_candidate_hex": int(len(outside)),
            "outside_candidate_area_km2": float(len(outside) * float(hex_area_km2)),
            "max_expansion_ring": int(outside_frame["expansion_ring"].max()),
            "selected_twh": float(combined.get("allocated_twh", pd.Series(dtype=float)).sum()),
        }
    )
    return combined, proposal_stats


def _solar_v1_stats(frame: pd.DataFrame, energy_model_state: dict[str, Any]) -> dict[str, float]:
    total_area_km2 = float(pd.to_numeric(frame.get("solar_v1_area_km2", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()) if not frame.empty else 0.0
    solar_area_need = float(energy_model_state.get("solar_area_need_km2", 0.0) or 0.0) if energy_model_state.get("available") else 0.0
    solar_twh_need = float(energy_model_state.get("solar_twh", 0.0) or 0.0) if energy_model_state.get("available") else 0.0
    solar_km2_per_twh = float(energy_model_state.get("solar_km2_per_twh", math.nan) or math.nan) if energy_model_state.get("available") else math.nan
    covered_area_km2 = min(total_area_km2, solar_area_need) if solar_area_need > 0 else 0.0
    remaining_area_km2 = max(0.0, solar_area_need - total_area_km2) if solar_area_need > 0 else 0.0
    covered_share_pct = (covered_area_km2 / solar_area_need * 100.0) if solar_area_need > 0 else 0.0
    if solar_km2_per_twh > 0 and math.isfinite(solar_km2_per_twh):
        covered_twh = covered_area_km2 / solar_km2_per_twh
    elif solar_area_need > 0:
        covered_twh = solar_twh_need * covered_area_km2 / solar_area_need
    else:
        covered_twh = 0.0
    return {
        "total_area_km2": total_area_km2,
        "solar_area_need_km2": solar_area_need,
        "covered_area_km2": covered_area_km2,
        "covered_share_pct": covered_share_pct,
        "remaining_area_km2": remaining_area_km2,
        "covered_twh": min(covered_twh, solar_twh_need) if solar_twh_need > 0 else covered_twh,
        "remaining_twh": max(0.0, solar_twh_need - covered_twh) if solar_twh_need > 0 else 0.0,
        "population": float(pd.to_numeric(frame.get("population", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()) if not frame.empty else 0.0,
    }


def _combined_establishment_stats(energy_model_state: dict[str, Any]) -> dict[str, float]:
    proposal_stats = energy_model_state.get("proposal_stats") if isinstance(energy_model_state, dict) else None
    solar_v1_stats = energy_model_state.get("solar_v1_stats") if isinstance(energy_model_state, dict) else None
    solar_proposal_stats = energy_model_state.get("solar_proposal_stats") if isinstance(energy_model_state, dict) else None
    wind_area_need = float(energy_model_state.get("wind_area_need_km2", 0.0) or 0.0)
    solar_area_need = float(energy_model_state.get("solar_area_need_km2", 0.0) or 0.0)
    wind_selected_area = float((proposal_stats or {}).get("selected_area_km2", 0.0) or 0.0) if isinstance(proposal_stats, dict) else 0.0
    wind_unmet_area = float((proposal_stats or {}).get("unmet_area_km2", wind_area_need) or 0.0) if isinstance(proposal_stats, dict) else wind_area_need
    if isinstance(solar_proposal_stats, dict):
        solar_v1_area = float(solar_proposal_stats.get("selected_area_km2", 0.0) or 0.0)
        solar_unmet_area = float(solar_proposal_stats.get("unmet_area_km2", max(0.0, solar_area_need - solar_v1_area)) or 0.0)
    else:
        solar_v1_area = float((solar_v1_stats or {}).get("covered_area_km2", 0.0) or 0.0) if isinstance(solar_v1_stats, dict) else 0.0
        solar_unmet_area = max(0.0, solar_area_need - solar_v1_area)
    total_need = wind_area_need + solar_area_need
    total_covered = min(wind_selected_area, wind_area_need) + min(solar_v1_area, solar_area_need)
    return {
        "wind_selected_area_km2": wind_selected_area,
        "wind_unmet_area_km2": wind_unmet_area,
        "solar_v1_covered_area_km2": solar_v1_area,
        "solar_unmet_area_km2": solar_unmet_area,
        "total_need_area_km2": total_need,
        "total_covered_area_km2": total_covered,
        "total_covered_share_pct": (total_covered / total_need * 100.0) if total_need > 0 else 0.0,
    }


def _count_text(value: int | float) -> str:
    return f"{int(value):,}".replace(",", " ")


def _combined_outside_lp_shortage_stats(frame: pd.DataFrame, hex_area_km2: float) -> dict[str, float]:
    if frame.empty:
        return {
            "wind_hex_count": 0,
            "solar_hex_count": 0,
            "both_hex_count": 0,
            "total_shortage_hex_count": 0,
            "wind_area_km2": 0.0,
            "solar_area_km2": 0.0,
            "hex_area_km2": float(hex_area_km2 or 0.0),
        }
    wind_area = pd.to_numeric(frame.get("wind_outside_lp_area_km2", pd.Series(0.0, index=frame.index)), errors="coerce").fillna(0.0).clip(lower=0.0)
    solar_area = pd.to_numeric(frame.get("solar_outside_lp_area_km2", pd.Series(0.0, index=frame.index)), errors="coerce").fillna(0.0).clip(lower=0.0)
    wind_mask = wind_area.gt(0.0)
    solar_mask = solar_area.gt(0.0)
    total_mask = wind_mask | solar_mask
    return {
        "wind_hex_count": int(wind_mask.sum()),
        "solar_hex_count": int(solar_mask.sum()),
        "both_hex_count": int((wind_mask & solar_mask).sum()),
        "total_shortage_hex_count": int(total_mask.sum()),
        "wind_area_km2": float(wind_area.sum()),
        "solar_area_km2": float(solar_area.sum()),
        "hex_area_km2": float(hex_area_km2 or 0.0),
    }


def _render_shortage_hex_stack_card(stats: dict[str, Any]) -> None:
    total_count = int(stats.get("total_shortage_hex_count", 0) or 0)
    wind_count = int(stats.get("wind_hex_count", 0) or 0)
    solar_count = int(stats.get("solar_hex_count", 0) or 0)
    both_count = int(stats.get("both_hex_count", 0) or 0)
    wind_area = float(stats.get("wind_area_km2", 0.0) or 0.0)
    solar_area = float(stats.get("solar_area_km2", 0.0) or 0.0)
    max_count = max(total_count, wind_count, solar_count, 1)
    symbol_scale = max(1, int(math.ceil(max_count / 64)))

    def _hex_symbols(count: int) -> str:
        symbol_count = int(math.ceil(max(0, count) / symbol_scale)) if count > 0 else 0
        hexes = "".join(
            "<span style='display:inline-block;width:0.46rem;height:0.40rem;margin:0.035rem;background:#111111;"
            "clip-path:polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%);'></span>"
            for _ in range(min(symbol_count, 64))
        )
        if symbol_count > 64:
            hexes += "<span style='font-size:0.72rem;color:#6b7280;margin-left:0.2rem;'>+</span>"
        return hexes or "<span style='font-size:0.74rem;color:#6b7280;'>Inga bristhex</span>"

    def _row(label: str, count: int, area: float, accent: str) -> str:
        return (
            "<div style='border-left:4px solid "
            f"{accent};padding:0.42rem 0.5rem;margin:0.35rem 0;border-radius:6px;"
            "background:rgba(255,255,255,0.68);border-top:1px solid rgba(49,51,63,0.12);"
            "border-right:1px solid rgba(49,51,63,0.12);border-bottom:1px solid rgba(49,51,63,0.12);'>"
            "<div style='display:flex;justify-content:space-between;gap:0.5rem;font-size:0.82rem;font-weight:700;'>"
            f"<span>{label}</span><span>{_count_text(count)} hex</span></div>"
            f"<div style='font-size:0.74rem;color:#6b7280;margin:0.08rem 0 0.25rem;'>{area:.2f} km² utanför landskapets potential</div>"
            f"<div style='line-height:0.5rem;'>{_hex_symbols(count)}</div>"
            "</div>"
        )

    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:0.86rem;font-weight:750;margin-bottom:0.2rem;'>{OUTSIDE_LP_NEED_LAYER_LABEL}</div>"
            "<div style='font-size:0.75rem;color:#6b7280;margin-bottom:0.35rem;'>"
            "Samma bristhex som visas som ett separat lager i kartan.</div>"
            + _row("Vind behöver yta", wind_count, wind_area, ESTABLISHMENT_CLASS_SPECS["wind_only"]["color"])
            + _row("Sol behöver yta", solar_count, solar_area, ESTABLISHMENT_CLASS_SPECS["solar_only"]["color"])
            + (
                f"<div style='font-size:0.74rem;color:#6b7280;margin-top:0.2rem;'>"
                f"Unika ytbehovshex: {_count_text(total_count)}. "
                f"Både vind och sol i samma hex: {_count_text(both_count)}. "
                f"1 symbol ≈ {_count_text(symbol_scale)} hex.</div>"
            ),
            unsafe_allow_html=True,
        )


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


@st.cache_data(show_spinner=False)
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
        for item in _solar_class_breaks_for_display(solar_rules)
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
    colors = landscape_type_display_colors(landscape_manifest)
    return [{"label": str(labels.get(key, key)), "color": colors.get(key, "#999999")} for key in sorted(colors)]


def _factor_legend_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for idx, (_, color) in enumerate(FACTOR_STOPS):
        if idx == 0:
            label = "Blå = låg laddning"
        elif idx == len(FACTOR_STOPS) - 1:
            label = "Röd = hög laddning"
        else:
            label = " "
        items.append({"label": label, "color": color})
    return items


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
        "population_buffer_m": 250.0,
    }


def _solar_class_breaks_for_display(solar_rules: dict[str, Any]) -> list[dict[str, Any]]:
    breaks = [dict(item) for item in _class_breaks(solar_rules)]
    palette = {
        "very_low": "#991b1b",
        "low": "#f87171",
        "medium": "#fef08a",
        "high": "#facc15",
        "very_high": "#ca8a04",
    }
    for item in breaks:
        class_id = str(item.get("id", ""))
        if class_id in palette:
            item["color"] = palette[class_id]
    return breaks


def _solar_rules_with_display_palette(solar_rules: dict[str, Any]) -> dict[str, Any]:
    rules = read_manifest(str(resolve_repo_path(solar_rules.get("_manifest_path")))) if solar_rules.get("_manifest_path") else solar_rules.copy()
    rules = {
        **rules,
        "score_model": {
            **(rules.get("score_model") or {}),
            "cluster_terms": [dict(item) for item in (rules.get("score_model") or {}).get("cluster_terms") or []],
            "role_terms": [dict(item) for item in (rules.get("score_model") or {}).get("role_terms") or []],
        },
    }
    rules["score_model"]["class_breaks"] = _solar_class_breaks_for_display(rules)
    return rules


def _solar_rules_from_params(solar_rules: dict[str, Any], params: dict[str, float]) -> dict[str, Any]:
    rules = _solar_rules_with_display_palette(solar_rules)
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
    score_model["class_breaks"] = _solar_class_breaks_for_display(rules)
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


def _reference_default_wind_params() -> dict[str, float]:
    params = _default_wind_params()
    params.update(
        {
            "settlement_distance_m": 200.0,
            "road_distance_m": 200.0,
            "grid_max_distance_m": 1000.0,
            "protected_buffer_m": 0.0,
        }
    )
    return params


def _reference_default_wind_layer_selection() -> dict[str, list[str]]:
    return normalize_group_layer_map(
        {
            "settlement": ["population_points"],
            "transport": ["roads_large"],
            "electrical": ["power_substations"],
            "protected": list(WIND_GROUP_LAYER_DEFAULTS.get("protected", [])),
            "coastal": [],
            "culture": [],
            "aviation_approach": [],
            "aviation_bird": [],
            "military": [],
        }
    )


def _apply_reference_default_wind_to_controls() -> None:
    params = _reference_default_wind_params()
    selected = _reference_default_wind_layer_selection()
    st.session_state[WIND_LAYER_SELECTION_KEY] = selected
    for group_id, layer_ids in WIND_GROUP_LAYER_DEFAULTS.items():
        param_key = GROUP_PARAM_MAP.get(group_id)
        group_param_value = params.get(param_key) if param_key else None
        if group_param_value is not None:
            st.session_state[_wind_control_key("analysis", group_id)] = int(round(float(group_param_value)))
        selected_ids = set(selected.get(group_id, []))
        for layer_id in layer_ids:
            st.session_state[_wind_control_key("layer", layer_id)] = layer_id in selected_ids


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
    for group in SOLAR_CONTROL_GROUPS:
        st.session_state.setdefault(_solar_control_key("active", str(group["id"])), False)


def _solar_control_key(kind: str, item_id: str) -> str:
    return f"solar_control__{kind}__{item_id}"


def _solar_params_from_control_state(defaults: dict[str, float]) -> dict[str, float]:
    params = _state_params("solar_builder", defaults)
    for group in SOLAR_CONTROL_GROUPS:
        active = bool(st.session_state.get(_solar_control_key("active", str(group["id"])), True))
        if active:
            continue
        for param_key in group.get("params") or []:
            params[str(param_key)] = 0.0
    return params


def _solar_group_controls(defaults: dict[str, float]) -> tuple[dict[str, float], bool]:
    st.caption(
        f"Bygg {SOLAR_LANDSCAPE_POTENTIAL_LABEL} med kriteriegrupper från Sol over land-underlaget. "
        "Grupper som stängs av får ingen positiv eller negativ effekt i scoremodellen."
    )
    with st.form("solar_landscape_potential_controls", clear_on_submit=False):
        with st.expander("Bas och metod", expanded=False):
            control = SOLAR_PARAM_CONTROLS["base_score"]
            st.slider(
                str(control["label"]),
                min_value=float(control["min"]),
                max_value=float(control["max"]),
                step=float(control["step"]),
                value=float(st.session_state.get("solar_builder_base_score", defaults["base_score"])),
                key="solar_builder_base_score",
                help=str(control["help"]),
            )
            st.caption("Hög LP Sol betyder robust landskap med låg konflikt och god teknisk logik, inte bara hög solinstrålning.")
        for group in SOLAR_CONTROL_GROUPS:
            group_id = str(group["id"])
            with st.expander(str(group["label"]), expanded=False):
                st.caption(str(group.get("caption", "")))
                st.checkbox("Aktiv", key=_solar_control_key("active", group_id))
                active = bool(st.session_state.get(_solar_control_key("active", group_id), True))
                for param_key in group.get("params") or []:
                    param_key = str(param_key)
                    control = SOLAR_PARAM_CONTROLS[param_key]
                    st.slider(
                        str(control["label"]),
                        min_value=float(control["min"]),
                        max_value=float(control["max"]),
                        step=float(control["step"]),
                        value=float(st.session_state.get(f"solar_builder_{param_key}", defaults[param_key])),
                        key=f"solar_builder_{param_key}",
                        disabled=not active,
                        help=str(control["help"]),
                    )
        applied = st.form_submit_button("Använd ändringar", type="primary", width="stretch")
    return _solar_params_from_control_state(defaults), bool(applied)


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
    _builder_slider("wind_builder", "settlement_distance_m", "Minsta avstånd till boende", 100.0, 3000.0, 50.0, defaults, "Större avstånd begränsar etablering närmare bebyggelse.")
    _builder_slider("wind_builder", "road_distance_m", "Minsta avstånd till vägar", 50.0, 2000.0, 25.0, defaults, "Större avstånd begränsar etablering närmare vägar och bebyggelse.")
    _builder_slider("wind_builder", "grid_max_distance_m", "Max avstånd till elinfrastruktur", 500.0, 15000.0, 250.0, defaults, "Större tillåtet avstånd gör fler lägen tekniskt möjliga.")
    _builder_slider("wind_builder", "protected_buffer_m", "Buffert skyddade områden", 0.0, 2000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar skyddade natur- och habitatlager.")
    _builder_slider("wind_builder", "coastal_buffer_m", "Buffert kust/strand", 0.0, 1000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar kustzon och strandskydd.")
    _builder_slider("wind_builder", "landscape_sensitivity_percent", "Landskapskänslighet", 0.0, 120.0, 5.0, defaults, f"Viktar hur starkt landskapsrollerna ska bromsa {WIND_LANDSCAPE_POTENTIAL_LABEL}.")
    with st.expander("Avancerade restriktioner"):
        _builder_slider("wind_builder", "culture_buffer_m", "Buffert kulturmiljöer", 0.0, 1500.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar värdefulla kulturmiljöer.")
        _builder_slider("wind_builder", "aviation_approach_buffer_m", "Buffert inflygningszoner", 0.0, 3000.0, 100.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar flygplatsens inflygningszoner.")
        _builder_slider("wind_builder", "aviation_bird_distance_m", "Minsta avstånd fågelkollision", 0.0, 4000.0, 100.0, defaults, "0 stänger av gruppen. Högre värden ger distance-conflict mot fågelkollisionszoner.")
        _builder_slider("wind_builder", "military_buffer_m", "Buffert militära områden", 0.0, 2000.0, 50.0, defaults, "0 stänger av gruppen. Högre värden hard-excludar militära områden.")
        st.dataframe(wind_acceptance_group_summary(), width="stretch", hide_index=True, height=220)


def _save_solar_potential(params: dict[str, float], resolution: int) -> None:
    st.session_state["saved_solar_potential"] = {
        "params": dict(params),
        "preview_resolution": int(resolution),
    }


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
    note_body: str = "Aktiva lager styrs i appen och kan även slås av/på i kartkontrollen.",
) -> None:
    if not layers:
        st.info("Välj minst ett kartlager.")
        return
    adjusted_layers = _apply_layer_opacity_state(layers, opacity_key_prefix or "combined")
    map_html = build_layered_hex_map_html(
        adjusted_layers,
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
            _hex_opacity_controls(adjusted_layers, opacity_key_prefix)
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
        "layer_kind": "hex",
        "opacity_family": name,
        "opacity_label": name,
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
        f"Hex med hög/mycket hög LP Sol: {len(selected)}<br>"
        f"Andel av visad yta: {selected_share:.1f}%<br>"
        f"Medelpoäng i polygonlagret: {float(selected['solar_score'].mean()):.1f}"
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
        "layer_kind": "vector",
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
        "layer_kind": "vector",
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
        applied = st.form_submit_button(ui_text("apply_changes", language), type="primary", width="stretch")

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
            applied = st.form_submit_button("Anvand andringar", type="primary", width="stretch")
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
                    "source_layer_id": layer_id,
                    "layer_kind": "vector",
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
        if str(spec.get("id")) == "share_0":
            items.append({"label": "Mörkare röd = djupare kärnområde", "color": "#7f0000"})
        items.append({"label": str(spec["legend_label"]), "color": str(spec["base_color"])})
        if str(spec.get("id")) == "share_9":
            items.append({"label": "Mörkare blå = djupare kärnområde", "color": "#1e3a8a"})
    return items


def _wind_core_label(core_score: float, zone_size: int) -> str:
    core_value = max(0.0, min(1.0, float(core_score)))
    zone_size_value = max(0, int(zone_size))
    if zone_size_value <= 1:
        return "Enskild hex"
    if core_value >= 0.72:
        return "Djup kärna"
    if core_value >= 0.36:
        return "Mellanläge"
    return "Kantzon"


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
                    "name": f"Källa: {layer_label(layer_spec, WIND_CONTROL_LANGUAGE, layer_spec.label)} ({translated_group_label})",
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
                    "source_layer_id": layer_id,
                    "layer_kind": "vector",
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
        selected_sources = str(runtime_group.get("selected_sources", "") or "")
        analysis_value = int(round(float(runtime_group.get("analysis_value_m", 0.0) or 0.0)))
        buffer_layer_id = (
            f"{WIND_POPULATION_SOURCE_LAYER_ID}:buffer:{analysis_value}"
            if group.id == "settlement" and selected_sources.strip().lower() == "population points"
            else f"{group.id}:buffer:{analysis_value}"
        )
        map_layers.append(
            {
                "name": f"Buffert: {group_label(groups[group.id], WIND_CONTROL_LANGUAGE, groups[group.id].label)}",
                "buffer_layer_id": buffer_layer_id,
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
                "layer_kind": "vector",
            }
        )
    return map_layers


def _wind_polygon_combined_layer(runtime_result: dict[str, Any]) -> dict[str, Any] | None:
    combined = runtime_result.get("combined")
    if not isinstance(combined, dict) or combined.get("geojson") is None:
        return None
    return {
        "name": WIND_POTENTIAL_POLYGON_LABEL,
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
        "layer_kind": "vector",
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
                "Källager": ", ".join(selected_labels) if selected_labels else "-",
                "Avstånd m": int(round(threshold_value)),
                "Buffert synlig": bool(runtime_group and runtime_group.get("geojson")),
                "Landandel": "-" if land_share is None else f"{float(land_share):.1f}%",
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _wind_runtime_hex_neighbor_map(display_geometry_path: str) -> dict[str, list[str]]:
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


def _wind_runtime_hex_color(area_share_pct: float, core_score: float, zone_size: int) -> str:
    class_spec = _wind_share_class_spec(area_share_pct)
    share_value = float(area_share_pct)
    core_value = max(0.0, min(1.0, float(core_score)))
    zone_size_value = max(0, int(zone_size))
    if zone_size_value <= 1:
        return str(class_spec["base_color"])

    if share_value <= 0.0:
        core_target = _mix_hex_colors(str(class_spec["core_color"]), "#180000", min(1.0, float(zone_size_value) / 150.0))
        intensity = (core_value ** 0.82) * min(1.0, 0.48 + (float(zone_size_value) / 120.0))
        return _mix_hex_colors(str(class_spec["base_color"]), core_target, intensity)

    if share_value >= 80.0:
        core_target = _mix_hex_colors(str(class_spec["core_color"]), "#082f6f", min(1.0, max(0.0, float(zone_size_value - 4)) / 40.0))
        intensity = (core_value ** 0.86) * min(0.82, 0.36 + (float(zone_size_value) / 70.0))
        return _mix_hex_colors(str(class_spec["base_color"]), core_target, intensity)

    intensity = (core_value ** 0.9) * min(0.56, 0.16 + (float(zone_size_value) / 52.0))
    return _mix_hex_colors(str(class_spec["base_color"]), str(class_spec["core_color"]), intensity)


@st.cache_data(show_spinner=False)
def _build_wind_runtime_hex_layer_data(
    combined_geojson_json: str,
    display_geometry_path: str,
    target_resolution: int,
) -> pd.DataFrame:
    combined_geojson = json.loads(combined_geojson_json)
    base_share = runtime_combined_hex_frame(combined_geojson, WIND_RUNTIME_BASE_RESOLUTION, [])
    raw_share = pd.DataFrame(columns=["hex_id", "potential_area_share_pct"])
    if not base_share.empty and "hex_id" in base_share.columns:
        raw_share = base_share[["hex_id", "wind_score"]].rename(columns={"wind_score": "potential_area_share_pct"}).copy()
        raw_share["hex_id"] = raw_share["hex_id"].astype(str)
        raw_share["potential_area_share_pct"] = raw_share["potential_area_share_pct"].fillna(0.0).astype(float).clip(lower=0.0, upper=100.0)
        if int(target_resolution) < WIND_RUNTIME_BASE_RESOLUTION:
            raw_share["hex_id"] = raw_share["hex_id"].map(lambda value: str(h3.cell_to_parent(str(value), int(target_resolution))))
            raw_share = (
                raw_share.groupby("hex_id", as_index=False)["potential_area_share_pct"]
                .mean()
            )
    display_geometries = load_h3_display_geometries(display_geometry_path)
    frame = pd.DataFrame({"hex_id": list(display_geometries.keys())})
    if not raw_share.empty and "hex_id" in raw_share.columns:
        frame = frame.merge(
            raw_share[["hex_id", "potential_area_share_pct"]],
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

    frame = _wind_runtime_hex_core_scores(frame, _wind_runtime_hex_neighbor_map(display_geometry_path))
    frame["fill"] = [
        _wind_runtime_hex_color(share_value, core_value, zone_size)
        for share_value, core_value, zone_size in zip(
            frame["potential_area_share_pct"],
            frame["core_score"],
            frame["zone_size"],
        )
    ]
    frame["core_label"] = [
        _wind_core_label(core_value, zone_size)
        for core_value, zone_size in zip(frame["core_score"], frame["zone_size"])
    ]
    frame["stroke"] = frame["fill"].map(lambda value: _mix_hex_colors(str(value), "#3a3a3a", 0.28))
    return frame.sort_values("hex_id").reset_index(drop=True)


def _wind_runtime_hex_layer_frame(
    region: dict[str, Any],
    runtime_result: dict[str, Any],
    target_resolution: int,
) -> pd.DataFrame:
    combined = runtime_result.get("combined")
    if not isinstance(combined, dict) or combined.get("geojson") is None:
        return pd.DataFrame()
    display_geometry_path = _h3_display_geometry_path(region, int(target_resolution))
    if not display_geometry_path:
        return pd.DataFrame()
    return _build_wind_runtime_hex_layer_data(
        json.dumps(combined["geojson"], sort_keys=True, ensure_ascii=False),
        display_geometry_path,
        int(target_resolution),
    )


def _wind_runtime_hex_feature_collection(
    frame: pd.DataFrame,
    display_geometry_path: str,
    target_resolution: int,
) -> dict[str, Any]:
    display_geometries = load_h3_display_geometries(display_geometry_path)
    features: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        geometry = display_geometries.get(str(row.hex_id))
        if geometry is None:
            continue
        popup = (
            f"<strong>{WIND_LANDSCAPE_POTENTIAL_LABEL}</strong><br>"
            f"Hex: {row.hex_id}<br>"
            f"LP-andel: {float(row.potential_area_share_pct):.1f}%<br>"
            f"Klass: {row.share_class_label}<br>"
            f"Kärnläge: {row.core_label}<br>"
            f"Kärnscore: {float(row.core_score):.2f}<br>"
            f"Sammanhängande zon: {int(row.zone_size)} hex<br>"
            f"Kärnrank i zon: {int(row.center_mass_rank)} av {int(row.zone_size)}<br>"
            f"<em>Mörkare nyans betyder längre in i en sammanhängande zon av samma potentialklass.</em>"
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": str(row.hex_id),
                    "fill": str(row.fill),
                    "stroke": str(row.stroke),
                    "core_score": float(row.core_score),
                    "core_label": str(row.core_label),
                    "zone_size": int(row.zone_size),
                    "tooltip_title": f"{WIND_LANDSCAPE_POTENTIAL_LABEL} {float(row.potential_area_share_pct):.1f}%",
                    "tooltip_body": f"{row.share_class_label} · {row.core_label}",
                    "popup": popup,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _wind_runtime_hex_layer(
    region: dict[str, Any],
    runtime_result: dict[str, Any],
    target_resolution: int,
    control_name: str | None = None,
) -> dict[str, Any] | None:
    display_geometry_path = _h3_display_geometry_path(region, int(target_resolution))
    if not display_geometry_path:
        return None
    frame = _wind_runtime_hex_layer_frame(region, runtime_result, int(target_resolution))
    if frame.empty:
        return None
    return {
        "name": str(control_name or WIND_LANDSCAPE_POTENTIAL_LABEL),
        "feature_collection": _wind_runtime_hex_feature_collection(frame, display_geometry_path, int(target_resolution)),
        "fill_property": "fill",
        "stroke_property": "stroke",
        "legend_items": _wind_share_legend_items(),
        "legend_id": "wind_polygon_hex_share",
        "legend_title": WIND_POTENTIAL_HEX_LABEL,
        "default_visible": True,
        "stroke": False,
        "weight": 0.0,
        "point_radius": 4,
        "z_index": 410,
        "layer_kind": "hex",
        "opacity_family": str(control_name or WIND_LANDSCAPE_POTENTIAL_LABEL),
        "opacity_label": str(control_name or WIND_LANDSCAPE_POTENTIAL_LABEL),
    }


def _rollup_energy_area_proposal_frame(
    selected: pd.DataFrame,
    target_resolution: int,
    source_resolution: int,
) -> pd.DataFrame:
    if selected.empty or int(target_resolution) >= int(source_resolution):
        return selected.copy()

    work = selected.copy()

    def _numeric_column(column: str, default: float = 0.0) -> pd.Series:
        if column in work.columns:
            return pd.to_numeric(work[column], errors="coerce").fillna(default)
        return pd.Series(default, index=work.index, dtype="float64")

    work["hex_id"] = work["hex_id"].astype(str).map(lambda value: h3.cell_to_parent(value, int(target_resolution)))
    work["allocated_area_km2"] = _numeric_column("allocated_area_km2", 0.0)
    work["potential_area_km2"] = _numeric_column("potential_area_km2", 0.0)
    work["allocated_twh"] = _numeric_column("allocated_twh", 0.0)
    work["selected_rank"] = _numeric_column("selected_rank", 0.0).astype(int)
    work["core_score"] = _numeric_column("core_score", 0.0)
    work["zone_size"] = _numeric_column("zone_size", 0.0).astype(int)
    work["expansion_ring"] = _numeric_column("expansion_ring", 0.0).astype(int)
    if "outside_et" not in work.columns:
        work["outside_et"] = False
    work["outside_et"] = work["outside_et"].fillna(False).astype(bool)
    work["outside_area_km2"] = work["allocated_area_km2"].where(work["outside_et"], 0.0)
    work["inside_area_km2"] = work["allocated_area_km2"].where(~work["outside_et"], 0.0)

    rolled = (
        work.groupby("hex_id", as_index=False)
        .agg(
            selected_rank=("selected_rank", "min"),
            potential_area_km2=("potential_area_km2", "sum"),
            allocated_area_km2=("allocated_area_km2", "sum"),
            allocated_twh=("allocated_twh", "sum"),
            outside_area_km2=("outside_area_km2", "sum"),
            inside_area_km2=("inside_area_km2", "sum"),
            core_score=("core_score", "max"),
            zone_size=("zone_size", "sum"),
            expansion_ring=("expansion_ring", "max"),
        )
        .sort_values(["selected_rank", "hex_id"])
        .reset_index(drop=True)
    )
    hex_area = h3_hex_area_km2(int(target_resolution))
    rolled["outside_et"] = rolled["outside_area_km2"].gt(rolled["inside_area_km2"])
    rolled["allocation_phase"] = rolled["outside_et"].map(lambda value: "Utanför LP" if value else "Inom LP")
    rolled["potential_area_share_pct"] = (rolled["potential_area_km2"] / max(hex_area, 1e-9) * 100.0).clip(lower=0.0, upper=100.0)
    rolled["allocated_hex_share_pct"] = (rolled["allocated_area_km2"] / max(hex_area, 1e-9) * 100.0).clip(lower=0.0, upper=100.0)
    rolled["remaining_area_after_km2"] = 0.0
    rolled["allocated_gwh"] = rolled["allocated_twh"] * 1000.0
    return rolled


def _combined_establishment_legend_items() -> list[dict[str, str]]:
    order = ["wind_and_solar", "wind_only", "solar_only", "not_suitable"]
    return [
        {"label": ESTABLISHMENT_CLASS_SPECS[class_id]["label"], "color": ESTABLISHMENT_CLASS_SPECS[class_id]["color"]}
        for class_id in order
    ]


def _establishment_source_frame(
    selected: pd.DataFrame,
    technology: str,
    target_resolution: int,
    source_resolution: int,
) -> pd.DataFrame:
    columns = [
        "hex_id",
        f"{technology}_suitable",
        f"{technology}_rank",
        f"{technology}_potential_score",
        f"{technology}_potential_area_km2",
        f"{technology}_allocated_area_km2",
        f"{technology}_allocated_gwh",
        f"{technology}_allocated_hex_share_pct",
        f"{technology}_outside_lp",
        f"{technology}_conflict_area_km2",
        f"{technology}_conflict",
        f"{technology}_expansion_ring",
        f"{technology}_phase",
    ]
    if selected.empty:
        return pd.DataFrame(columns=columns)

    if technology == "wind":
        rolled = _rollup_energy_area_proposal_frame(selected, int(target_resolution), int(source_resolution))
        score_column = "potential_area_share_pct"
    else:
        rolled = _rollup_solar_establishment_frame(selected, int(target_resolution), int(source_resolution))
        score_column = "potential_score"
    if rolled.empty or "hex_id" not in rolled.columns:
        return pd.DataFrame(columns=columns)

    work = rolled.copy()
    work["hex_id"] = work["hex_id"].astype(str)

    def _numeric_source(column: str, default: float = 0.0) -> pd.Series:
        if column in work.columns:
            return pd.to_numeric(work[column], errors="coerce").fillna(default)
        return pd.Series(default, index=work.index, dtype="float64")

    work[f"{technology}_rank"] = _numeric_source("selected_rank", 0.0).astype(int)
    work[f"{technology}_potential_score"] = _numeric_source(score_column, 0.0).clip(lower=0.0, upper=100.0)
    work[f"{technology}_potential_area_km2"] = _numeric_source("potential_area_km2", 0.0).clip(lower=0.0)
    work[f"{technology}_allocated_area_km2"] = _numeric_source("allocated_area_km2", 0.0).clip(lower=0.0)
    if "allocated_gwh" in work.columns:
        allocated_gwh = _numeric_source("allocated_gwh", 0.0)
    else:
        allocated_gwh = _numeric_source("allocated_twh", 0.0) * 1000.0
    work[f"{technology}_allocated_gwh"] = allocated_gwh.clip(lower=0.0)
    work[f"{technology}_allocated_hex_share_pct"] = _numeric_source("allocated_hex_share_pct", 0.0).clip(lower=0.0, upper=100.0)
    if "outside_et" in work.columns:
        work[f"{technology}_outside_lp"] = work["outside_et"].fillna(False).astype(bool)
    else:
        work[f"{technology}_outside_lp"] = False
    work[f"{technology}_suitable"] = work[f"{technology}_allocated_area_km2"].gt(0.0) & ~work[f"{technology}_outside_lp"]
    work[f"{technology}_conflict_area_km2"] = work[f"{technology}_allocated_area_km2"].where(work[f"{technology}_outside_lp"], 0.0)
    work[f"{technology}_conflict"] = work[f"{technology}_conflict_area_km2"].gt(0.0)
    work[f"{technology}_expansion_ring"] = _numeric_source("expansion_ring", 0.0).astype(int)
    if "allocation_phase" in work.columns:
        work[f"{technology}_phase"] = work["allocation_phase"].fillna("").astype(str)
    else:
        work[f"{technology}_phase"] = work[f"{technology}_outside_lp"].map(lambda value: "Utanför LP" if value else "Inom LP")
    return work.reindex(columns=columns)


def _combined_establishment_class(wind_suitable: bool, solar_suitable: bool) -> str:
    if wind_suitable and solar_suitable:
        return "wind_and_solar"
    if wind_suitable:
        return "wind_only"
    if solar_suitable:
        return "solar_only"
    return "not_suitable"


def _combined_establishment_frame(
    region: dict[str, Any],
    wind_selected: pd.DataFrame,
    solar_selected: pd.DataFrame,
    target_resolution: int,
    source_resolution: int,
) -> pd.DataFrame:
    display_geometry_path = _h3_display_geometry_path(region, int(target_resolution))
    if not display_geometry_path:
        return pd.DataFrame()
    display_geometries = load_h3_display_geometries(display_geometry_path)
    base = pd.DataFrame({"hex_id": sorted(str(hex_id) for hex_id in display_geometries)})
    if base.empty:
        return base

    wind = _establishment_source_frame(wind_selected, "wind", int(target_resolution), int(source_resolution))
    solar = _establishment_source_frame(solar_selected, "solar", int(target_resolution), int(source_resolution))
    if not wind.empty:
        base = base.merge(wind, on="hex_id", how="left")
    if not solar.empty:
        base = base.merge(solar, on="hex_id", how="left")

    for technology in ["wind", "solar"]:
        bool_col = f"{technology}_suitable"
        if bool_col not in base.columns:
            base[bool_col] = False
        base[bool_col] = base[bool_col].map(lambda value: False if pd.isna(value) else bool(value))
        for column in [
            f"{technology}_rank",
            f"{technology}_potential_score",
            f"{technology}_potential_area_km2",
            f"{technology}_allocated_area_km2",
            f"{technology}_allocated_gwh",
            f"{technology}_allocated_hex_share_pct",
            f"{technology}_conflict_area_km2",
            f"{technology}_expansion_ring",
        ]:
            if column not in base.columns:
                base[column] = 0.0
            base[column] = pd.to_numeric(base[column], errors="coerce").fillna(0.0)
        outside_col = f"{technology}_outside_lp"
        if outside_col not in base.columns:
            base[outside_col] = False
        base[outside_col] = base[outside_col].map(lambda value: False if pd.isna(value) else bool(value))
        conflict_col = f"{technology}_conflict"
        if conflict_col not in base.columns:
            base[conflict_col] = False
        base[conflict_col] = base[conflict_col].map(lambda value: False if pd.isna(value) else bool(value))
        phase_col = f"{technology}_phase"
        if phase_col not in base.columns:
            base[phase_col] = ""
        base[phase_col] = base[phase_col].fillna("").astype(str)

    base["establishment_class"] = [
        _combined_establishment_class(bool(wind), bool(solar))
        for wind, solar in zip(base["wind_suitable"], base["solar_suitable"])
    ]
    base["wind_outside_lp_area_km2"] = pd.to_numeric(base.get("wind_conflict_area_km2"), errors="coerce").fillna(0.0).clip(lower=0.0)
    base["solar_outside_lp_area_km2"] = pd.to_numeric(base.get("solar_conflict_area_km2"), errors="coerce").fillna(0.0).clip(lower=0.0)
    base["outside_lp_shortage"] = base["wind_outside_lp_area_km2"].gt(0.0) | base["solar_outside_lp_area_km2"].gt(0.0)
    base["outside_lp_reason"] = [
        "vind + sol" if wind_area > 0 and solar_area > 0 else "vind" if wind_area > 0 else "sol" if solar_area > 0 else ""
        for wind_area, solar_area in zip(base["wind_outside_lp_area_km2"], base["solar_outside_lp_area_km2"])
    ]
    base["establishment_label"] = base["establishment_class"].map(
        lambda class_id: ESTABLISHMENT_CLASS_SPECS.get(str(class_id), ESTABLISHMENT_CLASS_SPECS["not_suitable"])["label"]
    )
    base["fill"] = base["establishment_class"].map(
        lambda class_id: ESTABLISHMENT_CLASS_SPECS.get(str(class_id), ESTABLISHMENT_CLASS_SPECS["not_suitable"])["color"]
    )
    base["stroke"] = base["establishment_class"].map(
        lambda class_id: ESTABLISHMENT_CLASS_SPECS.get(str(class_id), ESTABLISHMENT_CLASS_SPECS["not_suitable"])["stroke"]
    )
    base["stroke_weight"] = 0.12
    base["fill_opacity"] = 0.58
    return base


def _h3_polygon_geometry(hex_id: str) -> dict[str, Any] | None:
    try:
        boundary = h3.cell_to_boundary(str(hex_id))
    except Exception:
        return None
    ring = [[float(lng), float(lat)] for lat, lng in boundary]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    if not ring:
        return None
    return {"type": "Polygon", "coordinates": [ring]}


def _outside_lp_need_child_geometry(hex_id: str, target_resolution: int) -> tuple[str, int, dict[str, Any] | None]:
    parent_hex = str(hex_id)
    try:
        parent_resolution = int(h3.get_resolution(parent_hex))
    except Exception:
        parent_resolution = int(target_resolution)
    child_resolution = min(15, max(parent_resolution, int(target_resolution)) + OUTSIDE_LP_NEED_CHILD_RESOLUTION_OFFSET)
    try:
        child_hex = str(h3.cell_to_center_child(parent_hex, child_resolution))
    except Exception:
        child_hex = parent_hex
        child_resolution = parent_resolution
    return child_hex, int(child_resolution), _h3_polygon_geometry(child_hex)


def _outside_lp_need_feature_collection(
    frame: pd.DataFrame,
    target_resolution: int,
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    if frame.empty or "outside_lp_shortage" not in frame.columns:
        return {"type": "FeatureCollection", "features": features}

    selected = frame[frame["outside_lp_shortage"].fillna(False).astype(bool)].copy()
    for row in selected.itertuples(index=False):
        child_hex, child_resolution, geometry = _outside_lp_need_child_geometry(str(row.hex_id), int(target_resolution))
        if geometry is None:
            continue
        reason = str(getattr(row, "outside_lp_reason", "") or "")
        wind_area = float(getattr(row, "wind_outside_lp_area_km2", 0.0) or 0.0)
        solar_area = float(getattr(row, "solar_outside_lp_area_km2", 0.0) or 0.0)
        popup = (
            f"<strong>{OUTSIDE_LP_NEED_LAYER_LABEL}</strong><br>"
            f"Gäller: {reason or '-'}<br>"
            f"Vind: {wind_area:.3f} km²<br>"
            f"Sol: {solar_area:.3f} km²<br>"
            f"Underliggande hex: R{int(target_resolution)} {row.hex_id}<br>"
            f"Visningshex: R{child_resolution} {child_hex}"
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": str(row.hex_id),
                    "display_hex_id": child_hex,
                    "display_resolution": child_resolution,
                    "outside_lp_reason": reason,
                    "wind_outside_lp_area_km2": wind_area,
                    "solar_outside_lp_area_km2": solar_area,
                    "fill": "#111111",
                    "fill_opacity": 0.88,
                    "tooltip_title": OUTSIDE_LP_NEED_LAYER_LABEL,
                    "tooltip_body": f"{reason or '-'} · Vind {wind_area:.3f} km² · Sol {solar_area:.3f} km²",
                    "popup": popup,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _outside_lp_need_layer(
    frame: pd.DataFrame,
    target_resolution: int,
) -> dict[str, Any] | None:
    if frame.empty:
        return None
    feature_collection = _outside_lp_need_feature_collection(frame, int(target_resolution))
    if not feature_collection.get("features"):
        return None
    return {
        "name": OUTSIDE_LP_NEED_LAYER_LABEL,
        "feature_collection": feature_collection,
        "fill_property": "fill",
        "fill_opacity_property": "fill_opacity",
        "legend_items": [{"label": "Små svarta hexagoner visar att mer etableringsyta behövs", "color": "#111111"}],
        "legend_id": "outside_lp_need",
        "legend_title": OUTSIDE_LP_NEED_LAYER_LABEL,
        "default_visible": True,
        "stroke": False,
        "stroke_opacity": 0.0,
        "fill_opacity": 0.88,
        "weight": 0.0,
        "z_index": 486,
        "layer_kind": "hex",
        "opacity_family": OUTSIDE_LP_NEED_LAYER_LABEL,
        "opacity_label": OUTSIDE_LP_NEED_LAYER_LABEL,
    }


def _outside_lp_need_family_layers(
    region: dict[str, Any],
    wind_selected: pd.DataFrame,
    solar_selected: pd.DataFrame,
    selected_resolution: int,
    lock_resolution: bool,
) -> list[dict[str, Any]]:
    if wind_selected.empty and solar_selected.empty:
        return []
    return _hex_family_layers(
        region,
        int(selected_resolution),
        bool(lock_resolution),
        "outside_lp_need",
        OUTSIDE_LP_NEED_LAYER_LABEL,
        lambda resolution: _outside_lp_need_layer(
            _combined_establishment_frame(
                region,
                wind_selected,
                solar_selected,
                int(resolution),
                int(selected_resolution),
            ),
            int(resolution),
        ),
    )


def _combined_establishment_feature_collection(
    frame: pd.DataFrame,
    display_geometry_path: str,
    target_resolution: int,
) -> dict[str, Any]:
    display_geometries = load_h3_display_geometries(display_geometry_path)
    features: list[dict[str, Any]] = []

    def _tech_html(row: Any, technology: str, label: str, score_label: str) -> str:
        if not bool(getattr(row, f"{technology}_suitable", False)):
            conflict_area = float(getattr(row, f"{technology}_conflict_area_km2", 0.0) or 0.0)
            if bool(getattr(row, f"{technology}_conflict", False)) and conflict_area > 0:
                return (
                    f"<strong>{label}</strong>: nej (utanför LP/konflikt)<br>"
                    f"Konfliktyta: {conflict_area:.3f} km²<br>"
                    f"Expansionslager: {int(float(getattr(row, f'{technology}_expansion_ring', 0.0) or 0.0))}<br>"
                )
            return f"<strong>{label}</strong>: nej<br>"
        outside_lp = bool(getattr(row, f"{technology}_outside_lp", False))
        return (
            f"<strong>{label}</strong>: ja ({'utanför LP' if outside_lp else 'inom LP'})<br>"
            f"{score_label}: {float(getattr(row, f'{technology}_potential_score', 0.0) or 0.0):.1f}%<br>"
            f"Prioritet: {int(float(getattr(row, f'{technology}_rank', 0.0) or 0.0))}<br>"
            f"Potentiell yta: {float(getattr(row, f'{technology}_potential_area_km2', 0.0) or 0.0):.3f} km²<br>"
            f"Fördelad yta: {float(getattr(row, f'{technology}_allocated_area_km2', 0.0) or 0.0):.3f} km² "
            f"({float(getattr(row, f'{technology}_allocated_hex_share_pct', 0.0) or 0.0):.1f}% av hex)<br>"
            f"Fördelad produktion: {float(getattr(row, f'{technology}_allocated_gwh', 0.0) or 0.0):.2f} GWh<br>"
        )

    for row in frame.itertuples(index=False):
        geometry = display_geometries.get(str(row.hex_id))
        if geometry is None:
            continue
        class_id = str(getattr(row, "establishment_class", "not_suitable") or "not_suitable")
        label = str(getattr(row, "establishment_label", ESTABLISHMENT_CLASS_SPECS["not_suitable"]["label"]))
        outside_lp_shortage = bool(getattr(row, "outside_lp_shortage", False))
        outside_lp_reason = str(getattr(row, "outside_lp_reason", "") or "")
        popup = (
            f"<strong>{COMBINED_ESTABLISHMENT_LAYER_LABEL}</strong><br>"
            f"Klass: {label}<br>"
            f"Hex: {row.hex_id}<br>"
            f"{_tech_html(row, 'wind', 'Vind', 'Vindpotential')}"
            f"{_tech_html(row, 'solar', 'Sol', 'Solpotential')}"
            f"H3: R{int(target_resolution)}"
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hex_id": str(row.hex_id),
                    "establishment_class": class_id,
                    "establishment_label": label,
                    "outside_lp_shortage": outside_lp_shortage,
                    "outside_lp_reason": outside_lp_reason,
                    "wind_outside_lp_area_km2": float(getattr(row, "wind_outside_lp_area_km2", 0.0) or 0.0),
                    "solar_outside_lp_area_km2": float(getattr(row, "solar_outside_lp_area_km2", 0.0) or 0.0),
                    "wind_suitable": bool(getattr(row, "wind_suitable", False)),
                    "solar_suitable": bool(getattr(row, "solar_suitable", False)),
                    "fill": str(getattr(row, "fill", ESTABLISHMENT_CLASS_SPECS["not_suitable"]["color"])),
                    "stroke": str(getattr(row, "stroke", ESTABLISHMENT_CLASS_SPECS["not_suitable"]["stroke"])),
                    "stroke_weight": float(getattr(row, "stroke_weight", 0.38) or 0.38),
                    "fill_opacity": float(getattr(row, "fill_opacity", 0.58) or 0.58),
                    "tooltip_title": label,
                    "tooltip_body": (
                        f"Vind: {'ja' if bool(getattr(row, 'wind_suitable', False)) else 'nej'} · Sol: {'ja' if bool(getattr(row, 'solar_suitable', False)) else 'nej'}"
                    ),
                    "popup": popup,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _combined_establishment_layer(
    frame: pd.DataFrame,
    display_geometry_path: str | None,
    target_resolution: int,
) -> dict[str, Any] | None:
    if frame.empty or not display_geometry_path:
        return None
    return {
        "name": COMBINED_ESTABLISHMENT_LAYER_LABEL,
        "feature_collection": _combined_establishment_feature_collection(frame, display_geometry_path, int(target_resolution)),
        "fill_property": "fill",
        "fill_opacity_property": "fill_opacity",
        "stroke_property": "stroke",
        "stroke_weight_property": "stroke_weight",
        "legend_items": _combined_establishment_legend_items(),
        "legend_id": "combined_establishment",
        "legend_title": COMBINED_ESTABLISHMENT_LAYER_LABEL,
        "default_visible": True,
        "stroke": True,
        "stroke_opacity": 0.72,
        "fill_opacity": 0.58,
        "weight": 0.12,
        "z_index": 476,
        "layer_kind": "hex",
        "opacity_family": COMBINED_ESTABLISHMENT_LAYER_LABEL,
        "opacity_label": COMBINED_ESTABLISHMENT_LAYER_LABEL,
    }


def _combined_establishment_family_layers(
    region: dict[str, Any],
    wind_selected: pd.DataFrame,
    solar_selected: pd.DataFrame,
    selected_resolution: int,
    lock_resolution: bool,
) -> list[dict[str, Any]]:
    if wind_selected.empty and solar_selected.empty:
        return []
    return _hex_family_layers(
        region,
        int(selected_resolution),
        bool(lock_resolution),
        "combined_establishment",
        COMBINED_ESTABLISHMENT_LAYER_LABEL,
        lambda resolution: _combined_establishment_layer(
            _combined_establishment_frame(
                region,
                wind_selected,
                solar_selected,
                int(resolution),
                int(selected_resolution),
            ),
            _h3_display_geometry_path(region, int(resolution)),
            int(resolution),
        ),
    )


def _expand_wind_area_outside_et(
    source_frame: pd.DataFrame,
    selected_frame: pd.DataFrame,
    proposal_stats: dict[str, Any],
    display_geometry_path: str | None,
    hex_area_km2: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if source_frame.empty or not display_geometry_path or hex_area_km2 <= 0:
        return selected_frame, proposal_stats

    et_shortage = float(proposal_stats.get("unmet_area_km2", 0.0) or 0.0)
    proposal_stats["et_selected_area_km2"] = float(proposal_stats.get("selected_area_km2", 0.0) or 0.0)
    proposal_stats["et_unmet_area_km2"] = max(0.0, et_shortage)
    if et_shortage <= 1e-9:
        proposal_stats.setdefault("outside_selected_area_km2", 0.0)
        proposal_stats.setdefault("outside_hex_count", 0)
        proposal_stats.setdefault("max_expansion_ring", 0)
        return selected_frame, proposal_stats

    display_hexes = set(load_h3_display_geometries(display_geometry_path))
    if not display_hexes:
        return selected_frame, proposal_stats

    work = source_frame.copy()
    work["hex_id"] = work["hex_id"].astype(str)
    work["potential_area_share_pct"] = pd.to_numeric(work.get("potential_area_share_pct"), errors="coerce").fillna(0.0)
    work["core_score"] = pd.to_numeric(work.get("core_score"), errors="coerce").fillna(0.0)
    work["zone_size"] = pd.to_numeric(work.get("zone_size"), errors="coerce").fillna(0).astype(int)
    et_hexes = set(work.loc[work["potential_area_share_pct"].gt(0.0), "hex_id"].astype(str)) & display_hexes
    selected_hexes = set(selected_frame.get("hex_id", pd.Series(dtype=str)).astype(str)) if not selected_frame.empty else set()
    anchor_hexes = (selected_hexes or et_hexes) & display_hexes

    neighbor_map = _wind_runtime_hex_neighbor_map(display_geometry_path)
    distance_lookup: dict[str, int] = {}
    if anchor_hexes:
        visited = set(anchor_hexes)
        frontier: deque[tuple[str, int]] = deque((hex_id, 0) for hex_id in anchor_hexes)
        while frontier:
            current, distance = frontier.popleft()
            for neighbor in neighbor_map.get(current, []):
                neighbor = str(neighbor)
                if neighbor not in display_hexes or neighbor in visited:
                    continue
                visited.add(neighbor)
                distance_lookup[neighbor] = distance + 1
                frontier.append((neighbor, distance + 1))

    outside = work[work["hex_id"].isin(display_hexes - et_hexes)].copy()
    if outside.empty:
        return selected_frame, proposal_stats
    outside["expansion_ring"] = outside["hex_id"].map(distance_lookup).fillna(999999).astype(int)
    outside = outside[outside["expansion_ring"].lt(999999)].copy()
    if outside.empty:
        return selected_frame, proposal_stats

    outside = outside.sort_values(
        ["expansion_ring", "core_score", "zone_size", "hex_id"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)

    remaining_area = et_shortage
    start_rank = int(len(selected_frame)) + 1
    outside_rows: list[dict[str, Any]] = []
    for offset, row in enumerate(outside.itertuples(index=False), start=0):
        allocated_area = min(float(hex_area_km2), max(0.0, remaining_area))
        if allocated_area <= 0:
            break
        record = row._asdict()
        record["selected_rank"] = start_rank + offset
        record["outside_et"] = True
        record["allocation_phase"] = "Utanför LP"
        record["potential_area_km2"] = 0.0
        record["allocated_area_km2"] = allocated_area
        record["allocated_hex_share_pct"] = (allocated_area / max(float(hex_area_km2), 1e-9)) * 100.0
        remaining_area = max(0.0, remaining_area - allocated_area)
        record["remaining_area_after_km2"] = remaining_area
        outside_rows.append(record)
        if remaining_area <= 1e-9:
            break

    if not outside_rows:
        return selected_frame, proposal_stats

    outside_frame = pd.DataFrame(outside_rows)
    if "outside_et" not in selected_frame.columns and not selected_frame.empty:
        selected_frame = selected_frame.copy()
        selected_frame["outside_et"] = False
    combined = pd.concat([selected_frame, outside_frame], ignore_index=True, sort=False)
    outside_area = float(outside_frame["allocated_area_km2"].sum())
    proposal_stats.update(
        {
            "selected_area_km2": float(proposal_stats.get("et_selected_area_km2", 0.0) or 0.0) + outside_area,
            "unmet_area_km2": max(0.0, remaining_area),
            "selected_hex_count": int(len(combined)),
            "outside_selected_area_km2": outside_area,
            "outside_hex_count": int(len(outside_frame)),
            "outside_candidate_hex": int(len(outside)),
            "outside_candidate_area_km2": float(len(outside) * float(hex_area_km2)),
            "max_expansion_ring": int(outside_frame["expansion_ring"].max()),
        }
    )
    return combined, proposal_stats


def _wind_runtime_hex_layers(
    region: dict[str, Any],
    runtime_result: dict[str, Any],
    preferred_resolution: int,
    lock_resolution: bool,
    family_key: str = "wind_runtime_share",
    control_name: str = WIND_POTENTIAL_HEX_LABEL,
) -> list[dict[str, Any]]:
    preferred = min(int(preferred_resolution), WIND_RUNTIME_BASE_RESOLUTION)
    return _hex_family_layers(
        region,
        preferred,
        bool(lock_resolution),
        family_key,
        control_name,
        lambda resolution: _wind_runtime_hex_layer(region, runtime_result, int(resolution), control_name),
    )


def _wind_polygon_preview_state(
    region: dict[str, Any],
    ui_params: dict[str, float],
    layer_selection: dict[str, list[str]],
    target_resolution: int,
    lock_resolution: bool,
    family_key: str = "wind_runtime_share",
    control_name: str = WIND_POTENTIAL_HEX_LABEL,
) -> dict[str, Any]:
    runtime_error: str | None = None
    runtime_result: dict[str, Any] = {"groups": {}, "combined": None, "cache_key": None}
    try:
        runtime_result = _wind_runtime_result(ui_params, layer_selection=layer_selection)
    except Exception as exc:
        runtime_error = str(exc)

    layers: list[dict[str, Any]] = []
    hex_layers: list[dict[str, Any]] = []
    combined_layer = None if runtime_error else _wind_polygon_combined_layer(runtime_result)
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
        "hex_layer_available": bool(hex_layers),
    }


def _wind_polygon_summary_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    runtime_result: dict[str, Any],
    target_resolution: int,
) -> pd.DataFrame:
    frame = _wind_runtime_hex_layer_frame(region, runtime_result, int(target_resolution)).copy()
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
                "core_score",
                "core_label",
                "zone_size",
                "center_mass_rank",
                "class_km",
                "landscape_type",
            ]
        )

    frame["wind_score"] = frame["potential_area_share_pct"].astype(float)
    frame["wind_class"] = frame["share_class_id"].astype(str)
    frame["wind_class_label"] = frame["share_class_label"].astype(str)
    frame["wind_color"] = frame["fill"].astype(str)
    frame["core_score"] = pd.to_numeric(frame.get("core_score"), errors="coerce").fillna(0.0)
    frame["core_label"] = frame.get("core_label", "").fillna("").astype(str)
    frame["zone_size"] = pd.to_numeric(frame.get("zone_size"), errors="coerce").fillna(0).astype(int)
    frame["center_mass_rank"] = pd.to_numeric(frame.get("center_mass_rank"), errors="coerce").fillna(1).astype(int)

    landscape = _landscape_frame(region, landscape_manifest, int(target_resolution))
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
        "layer_kind": "hex",
        "opacity_family": name,
        "opacity_label": name,
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
        "layer_kind": "hex",
        "opacity_family": name,
        "opacity_label": name,
    }


def _combined_summary(map_state: dict[str, Any], scenario_state: dict[str, Any]) -> None:
    def _wind_share_summary(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["klass", "klass_label", "hexagoner", "medelandel", "djupa_karnor"])
        work = frame.copy()
        work["potential_area_share_pct"] = pd.to_numeric(work["potential_area_share_pct"], errors="coerce").fillna(0.0)
        work["share_class_index"] = pd.to_numeric(work.get("share_class_index"), errors="coerce").fillna(999).astype(int)
        work["core_score"] = pd.to_numeric(work.get("core_score"), errors="coerce").fillna(0.0)
        work["share_class_id"] = work["share_class_id"].astype(str)
        work["share_class_label"] = work["share_class_label"].astype(str)
        work["deep_core"] = work["core_score"].ge(0.72)
        return (
            work.groupby(["share_class_index", "share_class_id", "share_class_label"], as_index=False)
            .agg(
                hexagoner=("hex_id", "count"),
                medelandel=("potential_area_share_pct", "mean"),
                djupa_karnor=("deep_core", "sum"),
            )
            .sort_values(["share_class_index", "medelandel"])
            .assign(medelandel=lambda data: data["medelandel"].round(1))
            .rename(columns={"share_class_id": "klass", "share_class_label": "klass_label"})
            [["klass", "klass_label", "hexagoner", "medelandel", "djupa_karnor"]]
        )

    def _solar_area_share_summary(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["klass", "klass_label", "hexagoner", "medel_areaandel", "yta_m2"])
        work = frame.copy()
        work["potential_area_share_pct"] = pd.to_numeric(work.get("potential_area_share_pct"), errors="coerce").fillna(0.0)
        work["potential_area_m2"] = pd.to_numeric(work.get("potential_area_m2"), errors="coerce").fillna(0.0)
        work["solar_class"] = work["solar_class"].astype(str)
        work["solar_class_label"] = work["solar_class_label"].astype(str)
        return (
            work.groupby(["solar_class", "solar_class_label"], as_index=False)
            .agg(
                hexagoner=("hex_id", "count"),
                medel_areaandel=("potential_area_share_pct", "mean"),
                yta_m2=("potential_area_m2", "sum"),
            )
            .sort_values("medel_areaandel")
            .assign(
                medel_areaandel=lambda data: data["medel_areaandel"].round(1),
                yta_m2=lambda data: data["yta_m2"].round(0).astype(int),
            )
            .rename(columns={"solar_class": "klass", "solar_class_label": "klass_label"})
            [["klass", "klass_label", "hexagoner", "medel_areaandel", "yta_m2"]]
        )

    def _wind_core_summary(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty or "core_label" not in frame.columns:
            return pd.DataFrame(columns=["kärnläge", "hexagoner", "medelandel"])
        work = frame.copy()
        work["potential_area_share_pct"] = pd.to_numeric(work["potential_area_share_pct"], errors="coerce").fillna(0.0)
        work["core_score"] = pd.to_numeric(work.get("core_score"), errors="coerce").fillna(0.0)
        work["core_label"] = work["core_label"].fillna("").astype(str).replace("", "Okänt")
        order = {"Kantzon": 1, "Mellanläge": 2, "Djup kärna": 3, "Enskild hex": 4, "Okänt": 5}
        return (
            work.groupby("core_label", as_index=False)
            .agg(hexagoner=("hex_id", "count"), medelandel=("potential_area_share_pct", "mean"), kärnscore=("core_score", "mean"))
            .assign(sort=lambda data: data["core_label"].map(order).fillna(99))
            .sort_values("sort")
            .assign(medelandel=lambda data: data["medelandel"].round(1), kärnscore=lambda data: data["kärnscore"].round(2))
            .rename(columns={"core_label": "kärnläge"})
            [["kärnläge", "hexagoner", "medelandel", "kärnscore"]]
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
    resolution_info = map_state.get("resolution_info") or {}
    context_rows = [
        {"inställning": "Scenario", "värde": str(scenario_state.get("scenario") or "-")},
        {"inställning": "Vald H3", "värde": str(resolution_info.get("selected_label", f"R{map_state.get('resolution')}"))},
        {"inställning": "Hexvisning", "värde": str(resolution_info.get("display_label", f"R{map_state.get('resolution')}"))},
        {"inställning": "Läge", "värde": str(resolution_info.get("mode_label", "Fast"))},
    ]
    st.dataframe(pd.DataFrame(context_rows), width="stretch", hide_index=True, height=176)
    if resolution_info.get("caption"):
        st.caption(str(resolution_info.get("caption")))

    layer_rows = _layer_control_rows(map_state.get("layers") or [], str(map_state.get("opacity_key_prefix") or "combined"))
    with st.expander(f"Tända lager ({len(layer_rows)})", expanded=True):
        if layer_rows:
            st.dataframe(pd.DataFrame(layer_rows), width="stretch", hide_index=True, height=min(260, 72 + 36 * len(layer_rows)))
            st.caption("Samma lager kan även döljas direkt i kartans lagerkontroll.")
        else:
            st.caption("Inga lager är tända.")

    for item in map_state.get("potential_frames") or []:
        frame = item["frame"]
        technology = item["technology"]
        score_col = f"{technology}_score"
        class_col = f"{technology}_class"
        high_share = _high_share_pct(frame, class_col, item.get("high_classes"))
        mean_label = str(item.get("mean_label", "Medelpoäng"))
        mean_format = str(item.get("mean_format", "{value:.1f}"))
        high_label = str(item.get("high_label", "Hög potential"))
        with st.expander(item["label"], expanded=True):
            left, right = st.columns(2)
            left.metric(mean_label, _metric_value_text(frame, score_col, mean_format))
            right.metric(high_label, f"{high_share:.1f}%")
            item_note = item.get("resolution_note")
            item_resolution = item.get("resolution")
            if item_note:
                st.caption(str(item_note))
            elif item_resolution is not None:
                st.caption(f"H3-rollup: R{int(item_resolution)}")
            if item.get("summary_mode") == "wind_share":
                summary_frame = _wind_share_summary(frame)
            elif item.get("summary_mode") == "solar_area_share":
                summary_frame = _solar_area_share_summary(frame)
            else:
                summary_frame = potential_summary(frame, technology)
            st.dataframe(summary_frame, width="stretch", hide_index=True)
            if item.get("summary_mode") == "wind_share":
                with st.expander("Kärnområden", expanded=False):
                    st.caption("Mörkare nyans inom samma potentialklass markerar hexagoner som ligger djupare i en sammanhängande zon.")
                    st.dataframe(_wind_core_summary(frame), width="stretch", hide_index=True)

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
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.json(region)


def _render_energy_model_summary(energy_model_state: dict[str, Any]) -> None:
    if not energy_model_state.get("available"):
        return
    with st.expander("Energimodellering", expanded=True):
        st.caption(
            f"{energy_model_state.get('scenario_label', energy_model_state.get('scenario', '-'))} · "
            f"mix {float(energy_model_state.get('wind_share_pct', 0.0) or 0.0):.0f}% vind / "
            f"{float(energy_model_state.get('solar_share_pct', 0.0) or 0.0):.0f}% sol · "
            f"markintensitet {energy_model_state.get('area_scenario_label', '-')} · "
            f"källa {energy_model_state.get('source_scenario_label', '-')} "
            f"{energy_model_state.get('source_year', '-')}, skala {float(energy_model_state.get('energy_scale', 1.0) or 1.0):g}x"
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vind", f"{float(energy_model_state.get('wind_twh', 0.0) or 0.0):.2f} TWh")
        c2.metric("Sol", f"{float(energy_model_state.get('solar_twh', 0.0) or 0.0):.2f} TWh")
        c3.metric("Vindyta", f"{float(energy_model_state.get('wind_area_need_km2', 0.0) or 0.0):.2f} km²")
        c4.metric("Solyta", f"{float(energy_model_state.get('solar_area_need_km2', 0.0) or 0.0):.2f} km²")
        solar_v1_stats = energy_model_state.get("solar_v1_stats")
        if isinstance(solar_v1_stats, dict):
            s1, s2, s3 = st.columns(3)
            s1.metric(f"{SOLAR_SMALL_SCALE_LABEL}: yta", f"{float(solar_v1_stats.get('total_area_km2', 0.0) or 0.0):.2f} km²")
            s2.metric("Täcker solbehov", f"{float(solar_v1_stats.get('covered_share_pct', 0.0) or 0.0):.1f}%")
            s3.metric("Kvarvarande solbehov", f"{float(solar_v1_stats.get('remaining_area_km2', 0.0) or 0.0):.2f} km²")
            st.caption(
                f"{SOLAR_SMALL_SCALE_LABEL} är en grupp i den samlade solpotentialen och kan kompletteras av {SOLAR_LARGE_SCALE_LABEL}."
            )
        solar_proposal_stats = energy_model_state.get("solar_proposal_stats")
        if isinstance(solar_proposal_stats, dict):
            solar_need = float(energy_model_state.get("solar_area_need_km2", 0.0) or 0.0)
            solar_selected = float(solar_proposal_stats.get("selected_area_km2", 0.0) or 0.0)
            solar_unmet = max(0.0, float(solar_proposal_stats.get("unmet_area_km2", 0.0) or 0.0))
            solar_inside = float(solar_proposal_stats.get("lp_selected_area_km2", solar_selected) or 0.0)
            solar_outside = float(solar_proposal_stats.get("outside_selected_area_km2", 0.0) or 0.0)
            solar_coverage_pct = (min(solar_selected, solar_need) / solar_need * 100.0) if solar_need > 0 else 0.0
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Solbehov", f"{solar_need:.2f} km²")
            p2.metric("Sol inom landskapets potential", f"{solar_inside:.2f} km²")
            p3.metric("Sol utanför landskapets potential", f"{solar_outside:.2f} km²")
            p4.metric("Sol täckning", f"{solar_coverage_pct:.1f}%")
            if solar_need > 0 and solar_outside > 1e-6:
                st.warning(
                    "Varning: Solpotentialen räcker inte för hela energiscenariot. "
                    f"{OUTSIDE_LP_NEED_LAYER_LABEL}: sol ca {solar_outside:.1f} km²."
                )
            if solar_need > 0 and solar_unmet > 1e-6:
                st.warning(f"Varning: Solpotentialen räcker inte med detta energiscenario. Ca {solar_unmet:.1f} km² saknas.")
            elif solar_need > 0 and solar_outside <= 1e-6:
                st.success("Solpotentialen räcker för detta energiscenario.")
        combined_establishment = energy_model_state.get("combined_establishment_stats")
        if isinstance(combined_establishment, dict):
            e1, e2, e3 = st.columns(3)
            e1.metric("Samlat etableringsbehov", f"{float(combined_establishment.get('total_need_area_km2', 0.0) or 0.0):.2f} km²")
            e2.metric("Täckt av vind + sol", f"{float(combined_establishment.get('total_covered_share_pct', 0.0) or 0.0):.1f}%")
            e3.metric("Otäckt solbehov", f"{float(combined_establishment.get('solar_unmet_area_km2', 0.0) or 0.0):.2f} km²")
            st.caption(f"Samlat etableringsläge använder vindpotential och den samlade solpotentialens aktiva grupper.")
        shortage_stats = energy_model_state.get("outside_lp_shortage_stats")
        if isinstance(shortage_stats, dict):
            _render_shortage_hex_stack_card(shortage_stats)
        st.caption(
            f"{WIND_LANDSCAPE_POTENTIAL_LABEL} är den möjliga ytan i landskapsmodellen. "
            f"{COMBINED_ESTABLISHMENT_LAYER_LABEL} försöker möta vald mix och area demand för både vind och sol."
        )
        proposal_stats = energy_model_state.get("proposal_stats") or {}
        if proposal_stats:
            c3, c4 = st.columns(2)
            c3.metric("Täckt yta", f"{float(proposal_stats.get('selected_area_km2', 0.0) or 0.0):.2f} km²")
            c4.metric("Kvar", f"{float(proposal_stats.get('unmet_area_km2', 0.0) or 0.0):.2f} km²")
            selected_twh = float(proposal_stats.get("selected_twh", 0.0) or 0.0)
            if selected_twh > 0:
                st.metric("Fördelad vindproduktion", f"{selected_twh:.2f} TWh")
            et_shortage = float(proposal_stats.get("et_unmet_area_km2", 0.0) or 0.0)
            outside_area = float(proposal_stats.get("outside_selected_area_km2", 0.0) or 0.0)
            outside_hex_count = int(proposal_stats.get("outside_hex_count", 0) or 0)
            max_ring = int(proposal_stats.get("max_expansion_ring", 0) or 0)
            if et_shortage > 0:
                st.error(
                    "Varning: Landskapets potential räcker inte med detta energiscenario. "
                    f"Ca {outside_area:.0f} km2 ligger utanför den potentiella ytan och visas som en röd konfliktyta i kartan."
                )
                if outside_hex_count > 0:
                    st.caption(
                        f"Utanför LP: {outside_hex_count:,} röda hex, {outside_area:.2f} km², "
                        f"upp till expansionslager {max_ring} från blå LP.".replace(",", " ")
                    )
            needed_hex = int(proposal_stats.get("needed_hex", 0) or 0)
            selected_count = int(proposal_stats.get("selected_hex_count", 0) or 0)
            if selected_count <= 0:
                selected_count = len(energy_model_state.get("proposal_frame", pd.DataFrame()))
            hex_area = float(energy_model_state.get("hex_area_km2", 0.0) or 0.0)
            available_hex = int(proposal_stats.get("available_candidate_hex", 0) or 0)
            available_area = float(proposal_stats.get("available_candidate_area_km2", 0.0) or 0.0)
            primary_candidates = int(proposal_stats.get("primary_candidate_hex", 0) or 0)
            extension_candidates = int(proposal_stats.get("extension_candidate_hex", 0) or 0)
            selected_primary = int(proposal_stats.get("selected_primary_hex", 0) or 0)
            selected_extension = int(proposal_stats.get("selected_extension_hex", 0) or 0)
            min_share = float(proposal_stats.get("min_share_pct", energy_model_state.get("auto_min_potential_share_pct", 65.0)) or 65.0)
            mean_share = float(proposal_stats.get("mean_selected_share_pct", 0.0) or 0.0)
            available_hex_text = f"{available_hex:,}".replace(",", " ")
            h1, h2, h3_col = st.columns(3)
            h1.metric("Area per hex", f"{hex_area:.4f} km²")
            h2.metric("Hela hex behövs", f"{needed_hex:,}".replace(",", " "))
            h3_col.metric("Valda hex", f"{selected_count:,}".replace(",", " "))
            selected_potential_area = float(proposal_stats.get("selected_potential_area_km2", 0.0) or 0.0)
            selected_hex_footprint = float(proposal_stats.get("selected_hex_footprint_km2", 0.0) or 0.0)
            st.caption(
                f"{COMBINED_ESTABLISHMENT_LAYER_LABEL}: {selected_count} vindceller valda. "
                f"De innehåller {selected_potential_area:.2f} km² potentiell yta inom {selected_hex_footprint:.2f} km² hexavtryck "
                f"({needed_hex} hela hex som grov jämförelse). "
                f"Valbara LP-hex: {available_hex_text} med {available_area:.2f} km² potentiell yta; "
                f"medelandel i urvalet {mean_share:.1f}%."
            )
            st.caption(
                f"Urvalsordning: först kärn-LP med LP ≥ {min_share:.0f}% "
                f"({selected_primary:,}/{primary_candidates:,} valda), sedan kompletterande LP "
                f"({selected_extension:,}/{extension_candidates:,} valda).".replace(",", " ")
            )
            if selected_count > needed_hex:
                st.caption("Area-share gör att fler hex behövs än den teoretiska jämförelsen med helt fyllda hex.")
            if float(proposal_stats.get("unmet_area_km2", 0.0) or 0.0) > 0:
                st.warning(
                    "Lämplig blå kärnyta räcker inte. Planeringsval behövs: sänk potentialkrav, släpp in kantzoner, "
                    "ändra restriktioner, välj ett lägre framtidsscenario eller minska area demand."
                )
        elif energy_model_state.get("placement_mode") == "manual":
            st.info("Självplacering är valt. Kartklick/drag-and-drop är nästa interaktionssteg; inget manuellt urval ritas ännu.")
        warning_table = energy_model_state.get("area_warnings")
        if isinstance(warning_table, pd.DataFrame) and not warning_table.empty:
            st.caption("AreaDemand har datakvalitetsvarningar. Se Energimodellering-panelen för detaljer.")


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
    h3_resolution = int(st.session_state.get("combined_h3_resolution", _preferred_h3_resolution(region, 10)))
    lock_h3_resolution = bool(st.session_state.get("combined_lock_h3_resolution", False))
    opacity = _current_opacity("combined")
    preserve_map_view = True
    map_reset_token = _map_view_reset_token()

    st.session_state["show_default_solar"] = False
    st.session_state.setdefault("show_user_solar", False)
    st.session_state.setdefault("show_solar_v1", False)
    st.session_state.setdefault("solar_small_population_active", True)
    st.session_state.setdefault("solar_large_scale_active", False)
    st.session_state.setdefault("solar_large_markblokke_active", False)
    st.session_state.setdefault("solar_large_population_active", False)
    st.session_state.setdefault("solar_v1_area_m2_per_person", 10.0)
    st.session_state.setdefault("solar_protected_buffer_m", 0.0)
    st.session_state["show_default_wind"] = False
    st.session_state["show_user_wind"] = False
    st.session_state.setdefault("show_landscape_v10", True)
    st.session_state.setdefault("show_landscape_cluster", False)
    st.session_state.setdefault("show_landscape_factor", False)

    applied_solar_config = _solar_config_from_session()
    _prime_solar_draft_state(applied_solar_config)
    show_solar_v1 = bool(applied_solar_config.get("small_population_active", False))
    show_user_solar = bool(applied_solar_config.get("large_scale_active", False))
    solar_small_population_active = bool(applied_solar_config.get("small_population_active", False))
    solar_large_markblokke_active = bool(applied_solar_config.get("large_markblokke_active", False))
    solar_large_population_active = bool(applied_solar_config.get("large_population_active", False))
    solar_large_protected_layer_ids = list(applied_solar_config.get("large_protected_layer_ids", []))
    solar_large_protected_active = bool(solar_large_protected_layer_ids)
    show_user_wind = any(len(layer_ids) > 0 for layer_ids in normalize_group_layer_map(_selected_wind_layers()).values())
    show_v10 = bool(st.session_state.get("show_landscape_v10"))
    show_cluster = bool(st.session_state.get("show_landscape_cluster", False))
    show_factor = bool(st.session_state.get("show_landscape_factor", False))
    selected_factor = str(st.session_state.get("combined_landscape_factor", factors[0] if factors else ""))
    if selected_factor not in factors and factors:
        selected_factor = factors[0]
    active_landscape_count = _count_enabled(show_v10, show_cluster, show_factor)
    active_wind_count = _count_enabled(show_user_wind)
    active_solar_count = _count_enabled(show_user_solar, show_solar_v1)

    wind_selected_layers = _selected_wind_layers()
    wind_ui_params = _default_wind_params()
    wind_controls_applied = False
    solar_params = _solar_params_from_control_state(solar_defaults)
    solar_params["population_buffer_m"] = float(applied_solar_config.get("population_buffer_m", 250.0) or 250.0)
    solar_params["protected_buffer_m"] = float(applied_solar_config.get("protected_buffer_m", 0.0) or 0.0)
    solar_v1_area_m2_per_person = float(applied_solar_config.get("panel_area_m2_per_person", 10.0) or 0.0)
    solar_controls_applied = False
    energy_model_state: dict[str, Any] = {"available": False}

    if left_panel is not None:
        with left_panel.expander("Geografier", expanded=False):
            with st.expander("Region", expanded=False):
                region = _select_region(st)

            with st.expander(f"Landskap ({active_landscape_count})", expanded=True):
                show_v10 = st.checkbox("Landskapstyper", value=show_v10, key="show_landscape_v10")
                show_cluster = st.checkbox("Landskapstrukturer", value=show_cluster, key="show_landscape_cluster")
                show_factor = st.checkbox("Landskapsfaktorer", value=show_factor, key="show_landscape_factor")
                selected_factor = st.selectbox(
                    "Faktor",
                    options=factors,
                    index=factors.index(selected_factor) if selected_factor in factors else 0,
                    format_func=lambda factor: f"{factor} - {factor_label(landscape_manifest, factor)}",
                    disabled=not show_factor,
                    key="combined_landscape_factor",
                )

            h3_resolution, lock_h3_resolution, opacity, preserve_map_view, map_reset_token = _map_panel_controls(region, "combined", st)

            with st.expander(f"{WIND_LANDSCAPE_POTENTIAL_LABEL} ({active_wind_count})", expanded=False):
                st.caption(
                    f"Bygg {WIND_LANDSCAPE_POTENTIAL_LABEL} direkt i samma vy. Potentialandelen beräknas alltid i R{WIND_RUNTIME_BASE_RESOLUTION} "
                    "och används här för vindpolygonen och den gemensamma etableringsytan."
                )
                if lock_h3_resolution:
                    st.caption("Vald upplösning är låst. Kartan visar exakt den upplösningen även om den blir brusigare vid utzoomning.")
                else:
                    st.caption("Zoomanpassning är aktiv. Kartan kan visa grövre aggregat när du zoomar ut långt.")
                st.caption("Separat sparning behövs inte längre i den här arbetsvyn.")
                wind_selected_layers, wind_ui_params, wind_controls_applied = _wind_group_controls("wind_unified", language=WIND_CONTROL_LANGUAGE)
                show_user_wind = any(len(layer_ids) > 0 for layer_ids in normalize_group_layer_map(wind_selected_layers).values())

            with st.expander(f"{SOLAR_LANDSCAPE_POTENTIAL_LABEL} ({active_solar_count})", expanded=active_solar_count > 0):
                with st.form("solar_landscape_potential_controls_unified", clear_on_submit=False):
                    st.caption(
                        f"{SOLAR_LANDSCAPE_POTENTIAL_LABEL} är en samlad solmodell med grupper. "
                        f"Ändringar i lager och sliders appliceras först när du trycker på Använd ändringar."
                    )
                    st.markdown(
                        "[Vill du veta mer om att anlägga sol över land? Läs guiden från Byplanlab.]"
                        "(https://byplanlab.dk/sites/default/files/2025-06/Sol%20over%20land%20-%20Guide%20til%20planl%C3%A6gning%20af%20solenergi.pdf)"
                    )
                    with st.expander(SOLAR_SMALL_SCALE_LABEL, expanded=False):
                        draft_small_population_active = st.checkbox(
                            "Befolkningspunkter",
                            key="solar_draft_small_population_active",
                            help="Källan visas som aggregerade H3-centroider, inte som individpunkter.",
                        )
                        if draft_small_population_active and not SOLAR_V1_POPULATION_LAYER_PATH.exists():
                            st.warning(_solar_v1_population_source_status())
                        st.slider(
                            "Panelyta per person",
                            min_value=0.0,
                            max_value=25.0,
                            step=1.0,
                            key="solar_draft_area_m2_per_person",
                            disabled=not draft_small_population_active,
                            help="Schablon för småskalig anläggning: befolkning per hex multipliceras med m2 panelyta per person.",
                        )
                        st.caption("Kartlager: källa, aggregerad 100 m buffert, solpolygon och gemensam potentiell etableringsyta.")
                    with st.expander(SOLAR_LARGE_SCALE_LABEL, expanded=False):
                        draft_large_markblokke_active = st.checkbox(
                            "Visa jordbruksmark (Markblokke)",
                            key="solar_draft_large_markblokke_active",
                            help="Visar och beräknar storskalig sol från Markblokke över hela öns landskapsunderlag.",
                        )
                        with st.expander("Befolkning", expanded=False):
                            draft_large_population_active = st.checkbox(
                                "Befolkningspunkter",
                                key="solar_draft_large_population_active",
                            )
                            st.slider(
                                "Avstånd till befolkning",
                                min_value=100.0,
                                max_value=500.0,
                                step=25.0,
                                key="solar_draft_population_buffer_m",
                                disabled=not draft_large_population_active,
                                help="Totalt avstånd från befolkningspunkter. 250 m betyder 250 m totalt, inte 100 + 250 m.",
                            )
                            st.caption("Avståndet är totalt från befolkningspunkter. Solpolygonen och etableringsytan använder samma Markblokke-underlag.")
                        draft_selected_protected_ids: list[str] = []
                        with st.expander("Skyddade områden", expanded=False):
                            protected_options = _solar_protected_layer_options()
                            for option in protected_options:
                                layer_id = str(option["id"])
                                checked = st.checkbox(
                                    str(option["label"]),
                                    key=_solar_protected_layer_control_key(layer_id),
                                    disabled=not bool(option["ready"]),
                                    help=str(option.get("message", "") or ""),
                                )
                                if checked and bool(option["ready"]):
                                    draft_selected_protected_ids.append(layer_id)
                            if not protected_options:
                                st.caption("Inga skyddslager hittades i acceptansregistret.")
                            elif not draft_selected_protected_ids:
                                st.caption("Storskalig sol använder inget skyddsavdrag förrän minst ett skyddslager är valt.")
                            st.slider(
                                "Buffert skyddade områden",
                                min_value=0.0,
                                max_value=2000.0,
                                step=50.0,
                                key="solar_draft_protected_buffer_m",
                                disabled=not draft_selected_protected_ids,
                                help="0 m tar bort själva skyddade områdena. Högre värden lägger till buffert.",
                            )
                        draft_large_scale_active = _solar_large_scale_is_active(
                            draft_large_markblokke_active,
                            draft_large_population_active,
                            draft_selected_protected_ids,
                        )
                        if not draft_large_scale_active:
                            st.caption("Storskalig sol aktiveras när minst ett lager i gruppen är valt.")
                        st.caption("Landskapstypsfiltret är borttaget. Markblokke visas över hela öns landskapsunderlag.")
                        st.caption("Ingen bonitets- eller jordklassvariabel finns i nuvarande solunderlag; jordart/prekvartär beskriver geologi, inte jordbruksmarkens kvalitet.")
                    apply_solar = st.form_submit_button("Använd ändringar", type="primary", width="stretch")
                if apply_solar:
                    region_id = str(region.get("region_id", "region"))
                    scenario_manifest = scenario_state.get("manifest") or {}
                    scenario_levels = scenario_manifest.get("scenario_levels") or []
                    potential_scenario_key = f"potential_scenario_{region_id}"
                    energy_scenario_key = f"energy_model_planning_scenario_{region_id}"
                    current_scenario = str(
                        st.session_state.get(energy_scenario_key)
                        or st.session_state.get(potential_scenario_key)
                        or scenario_state.get("scenario")
                        or ""
                    )
                    if current_scenario in scenario_levels:
                        st.session_state[potential_scenario_key] = current_scenario
                        st.session_state[energy_scenario_key] = current_scenario
                    st.session_state[SOLAR_APPLIED_CONFIG_KEY] = _solar_draft_config_from_session()
                    solar_controls_applied = True
                    st.rerun()

        with left_panel.expander("Energimodellering", expanded=False):
            st.caption("Levereras av EML")
            st.markdown(f"[Energy Modelling Lab]({EML_PROVIDER_URL})")
            energy_model_state = _render_energy_modeling_panel(region, scenario_state, h3_resolution, st)
            if energy_model_state.get("available"):
                scenario_state = {
                    "scenario": energy_model_state.get("scenario_label") or energy_model_state.get("scenario"),
                    "manifest": scenario_state.get("manifest"),
                    "year": energy_model_state.get("source_year"),
                    "energy_model": energy_model_state,
                }

        with left_panel.expander("Social acceptans", expanded=False):
            st.caption("Levereras av IVL")
            st.caption("Kommer i augusti")
            st.markdown(f"[IVL Svenska Miljöinstitutet]({IVL_PROVIDER_URL})")

    display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
    resolution_info = _hex_display_rule(region, h3_resolution, lock_h3_resolution)
    st.session_state["solar_builder_params"] = solar_params
    st.session_state["wind_builder_params"] = wind_ui_params

    layers: list[dict[str, Any]] = []
    potential_frames: list[dict[str, Any]] = []
    unified_notes: list[str] = []
    user_solar_frame = pd.DataFrame()
    solar_v1_frame = pd.DataFrame()
    solar_small_buffer_geojson: dict[str, Any] | None = None
    solar_large_polygon_geojson: dict[str, Any] | None = None

    if show_user_solar:
        large_population_buffer_m = float(solar_params.get("population_buffer_m", 250.0) or 250.0) if solar_large_population_active else 0.0
        large_protected_buffer_m = float(solar_params.get("protected_buffer_m", 0.0) or 0.0) if solar_large_protected_layer_ids else None
        user_solar_frame = _solar_large_scale_frame(
            region,
            landscape_manifest,
            h3_resolution,
            large_population_buffer_m,
            large_protected_buffer_m,
            solar_large_protected_layer_ids,
        )
        large_polygon_path = _solar_large_scale_polygon_path(large_population_buffer_m)
        solar_large_polygon_geojson = _solar_large_scale_polygon_geojson(str(large_polygon_path), large_population_buffer_m)
        if solar_large_population_active:
            _append_unique_layer(layers, _solar_population_source_layer())
            _append_unique_layer(layers, _solar_population_buffer_layer(region, h3_resolution, large_population_buffer_m))
        if solar_large_protected_active:
            for protected_layer in _solar_protected_source_layers(solar_large_protected_layer_ids):
                _append_unique_layer(layers, protected_layer)
            _append_unique_layer(
                layers,
                _solar_protected_buffer_layer(float(large_protected_buffer_m or 0.0), solar_large_protected_layer_ids),
            )
        potential_frames.append(
            {
                "label": f"{SOLAR_LANDSCAPE_POTENTIAL_LABEL}: {SOLAR_LARGE_SCALE_LABEL}",
                "technology": "solar",
                "frame": user_solar_frame,
                "resolution": h3_resolution,
                "high_classes": ["high"],
                "mean_label": "Medel areaandel",
                "mean_format": "{value:.1f}%",
                "high_label": "Hex 75-100%",
                "summary_mode": "solar_area_share",
                "resolution_note": resolution_info["item_note"],
            }
        )
        unified_notes.append(
            f"{SOLAR_LARGE_SCALE_LABEL} använder Markblokke över hela öns landskapsunderlag och filtrerar inte längre på två landskapstyper."
        )
        if solar_large_population_active:
            unified_notes.append(
                f"Befolkningslagret tar bort potential inom {large_population_buffer_m:.0f} m från befolkningspunkter."
            )
        if solar_large_protected_active:
            unified_notes.append(
                f"Skyddade områden drar av potential med {float(large_protected_buffer_m or 0.0):.0f} m buffert."
            )
        if solar_controls_applied:
            unified_notes.append(f"{SOLAR_LANDSCAPE_POTENTIAL_LABEL}: ändringar tillämpade.")

    if show_solar_v1:
        solar_v1_frame = _solar_v1_frame(region, landscape_manifest, h3_resolution, solar_v1_area_m2_per_person)
        if solar_small_population_active:
            solar_small_buffer_geojson = _solar_population_buffer_geojson(100.0)
            _append_unique_layer(layers, _solar_population_source_layer())
            _append_unique_layer(layers, _solar_population_buffer_layer(region, h3_resolution, 100.0))
        potential_frames.append(
            {
                "label": SOLAR_SMALL_SCALE_LABEL,
                "technology": "solar_v1",
                "frame": solar_v1_frame,
                "resolution": h3_resolution,
                "high_classes": ["high", "very_high"],
                "mean_label": "Medelscore",
                "mean_format": "{value:.1f}",
                "high_label": "Hög småskalig yta",
                "resolution_note": (
                    f"Befolkningsunderlaget visas i R{h3_resolution}. Om källdata är grövre än vald upplösning "
                    "fördelas befolkningen över underhex för visualisering."
                ),
            }
        )
        energy_model_state["solar_v1_stats"] = _solar_v1_stats(solar_v1_frame, energy_model_state)
        unified_notes.append(
            f"{SOLAR_SMALL_SCALE_LABEL} bygger i första versionen på befolkning per hex och {solar_v1_area_m2_per_person:.0f} m2 panelyta per person."
        )
        unified_notes.append(_solar_v1_population_source_status())

    if show_solar_v1 or show_user_solar:
        combined_solar_frame = _combined_solar_hex_frame(
            region,
            landscape_manifest,
            h3_resolution,
            solar_v1_frame if show_solar_v1 and solar_small_population_active else pd.DataFrame(),
            user_solar_frame if show_user_solar else pd.DataFrame(),
        )
        _append_unique_layer(
            layers,
            _solar_potential_polygon_layer(
                solar_small_buffer_geojson if show_solar_v1 and solar_small_population_active else None,
                user_solar_frame if show_user_solar else pd.DataFrame(),
                solar_large_polygon_geojson,
            ),
        )
        potential_frames.append(
            {
                "label": SOLAR_LANDSCAPE_POTENTIAL_LABEL,
                "technology": "solar",
                "frame": combined_solar_frame,
                "resolution": h3_resolution,
                "high_classes": ["high"],
                "mean_label": "Medel areaandel",
                "mean_format": "{value:.1f}%",
                "high_label": "Hex 75-100%",
                "summary_mode": "solar_area_share",
                "resolution_note": resolution_info["item_note"],
            }
        )
        if energy_model_state.get("available"):
            solar_proposal_frame, solar_proposal_stats = _solar_establishment_frame(
                solar_v1_frame if show_solar_v1 and solar_small_population_active else pd.DataFrame(),
                user_solar_frame if show_user_solar else pd.DataFrame(),
                float(energy_model_state.get("solar_area_need_km2", 0.0) or 0.0),
                float(energy_model_state.get("solar_twh", 0.0) or 0.0),
                float(energy_model_state.get("solar_km2_per_twh", math.nan) or math.nan),
                float(energy_model_state.get("hex_area_km2", h3_hex_area_km2(h3_resolution)) or h3_hex_area_km2(h3_resolution)),
            )
            solar_proposal_frame, solar_proposal_stats = _expand_solar_area_outside_lp(
                combined_solar_frame,
                solar_proposal_frame,
                solar_proposal_stats,
                display_geometry_path,
                float(energy_model_state.get("hex_area_km2", h3_hex_area_km2(h3_resolution)) or h3_hex_area_km2(h3_resolution)),
                float(energy_model_state.get("solar_twh", 0.0) or 0.0),
                float(energy_model_state.get("solar_area_need_km2", 0.0) or 0.0),
                float(energy_model_state.get("solar_km2_per_twh", math.nan) or math.nan),
            )
            energy_model_state["solar_proposal_frame"] = solar_proposal_frame
            energy_model_state["solar_proposal_stats"] = solar_proposal_stats
            if not solar_proposal_frame.empty:
                unified_notes.append(
                    f"Solens etableringsyta allokeras först från {SOLAR_SMALL_SCALE_LABEL} och därefter {SOLAR_LARGE_SCALE_LABEL}; den visas i det gemensamma etableringslagret."
                )

    custom_wind_preview_state: dict[str, Any] | None = None
    if show_user_wind:
        custom_wind_preview_state = _wind_polygon_preview_state(
            region,
            wind_ui_params,
            wind_selected_layers,
            h3_resolution,
            lock_h3_resolution,
            family_key="user_wind_landscape_potential",
            control_name=WIND_POTENTIAL_POLYGON_LABEL,
        )
        layers.extend(custom_wind_preview_state["layers"])
        if custom_wind_preview_state["runtime_error"]:
            unified_notes.append(f"Vindruntime kunde inte köras: {custom_wind_preview_state['runtime_error']}")
        else:
            custom_wind_summary = _wind_polygon_summary_frame(
                region,
                landscape_manifest,
                custom_wind_preview_state["runtime_result"],
                h3_resolution,
            )
            potential_frames.append(
                {
                    "label": WIND_LANDSCAPE_POTENTIAL_LABEL,
                    "technology": "wind",
                    "frame": custom_wind_summary,
                    "resolution": h3_resolution,
                    "high_classes": ["share_8", "share_9"],
                    "mean_label": "Medelandel",
                    "mean_format": "{value:.1f}%",
                    "high_label": "Andel >65%",
                    "summary_mode": "wind_share",
                    "resolution_note": resolution_info["item_note"],
                }
            )
            if lock_h3_resolution:
                unified_notes.append(
                    f"{WIND_LANDSCAPE_POTENTIAL_LABEL} beräknas i R{WIND_RUNTIME_BASE_RESOLUTION}. Kartan visar polygonen och den gemensamma etableringsytan."
                )
            else:
                unified_notes.append(
                    f"{WIND_LANDSCAPE_POTENTIAL_LABEL} beräknas i R{WIND_RUNTIME_BASE_RESOLUTION}. Kartan visar polygonen, medan hexberäkningen används internt för statistik och etableringsyta."
                )
            unified_notes.append(
                "Vindens interna hexberäkning används för att prioritera kärnområden i den gemensamma etableringsytan."
            )
            if (
                energy_model_state.get("available")
                and energy_model_state.get("show_proposal")
                and energy_model_state.get("placement_mode") == "auto"
            ):
                wind_area_need = float(energy_model_state.get("wind_area_need_km2", 0.0) or 0.0)
                wind_twh_need = float(energy_model_state.get("wind_twh", 0.0) or 0.0)
                wind_factor = float(energy_model_state.get("wind_km2_per_twh", math.nan) or math.nan)
                proposal_frame, proposal_stats = allocate_wind_area_from_core_hexes(
                    custom_wind_summary,
                    wind_area_need,
                    float(energy_model_state.get("hex_area_km2", h3_hex_area_km2(h3_resolution)) or h3_hex_area_km2(h3_resolution)),
                    float(energy_model_state.get("auto_min_potential_share_pct", 65.0) or 65.0),
                )
                proposal_frame, proposal_stats = _expand_wind_area_outside_et(
                    custom_wind_summary,
                    proposal_frame,
                    proposal_stats,
                    display_geometry_path,
                    float(energy_model_state.get("hex_area_km2", h3_hex_area_km2(h3_resolution)) or h3_hex_area_km2(h3_resolution)),
                )
                if not proposal_frame.empty:
                    if wind_factor > 0 and math.isfinite(wind_factor):
                        proposal_frame["allocated_twh"] = proposal_frame["allocated_area_km2"].astype(float) / wind_factor
                    elif wind_area_need > 0:
                        proposal_frame["allocated_twh"] = wind_twh_need * proposal_frame["allocated_area_km2"].astype(float) / wind_area_need
                    else:
                        proposal_frame["allocated_twh"] = 0.0
                    proposal_frame["allocated_gwh"] = proposal_frame["allocated_twh"].astype(float) * 1000.0
                    proposal_frame["allocated_share_of_need_pct"] = (
                        proposal_frame["allocated_area_km2"].astype(float) / max(wind_area_need, 1e-9) * 100.0
                    )
                    proposal_stats["selected_twh"] = float(proposal_frame["allocated_twh"].sum())
                energy_model_state["proposal_frame"] = proposal_frame
                energy_model_state["proposal_stats"] = proposal_stats
                if not proposal_frame.empty:
                    unified_notes.append(
                        "Vindens etableringsyta räknar täckning med potentiell area per hex, inte hela hexytan, och visas i det gemensamma etableringslagret."
                    )
                elif wind_area_need > 0:
                    unified_notes.append("Energimodelleringen hittade inga vindceller som uppfyller minsta kärn-/potentialkrav.")

    if (
        energy_model_state.get("available")
        and energy_model_state.get("show_proposal")
        and energy_model_state.get("placement_mode") == "auto"
    ):
        selected_establishment_frame = _combined_establishment_frame(
            region,
            energy_model_state.get("proposal_frame", pd.DataFrame()),
            energy_model_state.get("solar_proposal_frame", pd.DataFrame()),
            h3_resolution,
            h3_resolution,
        )
        energy_model_state["outside_lp_shortage_stats"] = _combined_outside_lp_shortage_stats(
            selected_establishment_frame,
            float(energy_model_state.get("hex_area_km2", h3_hex_area_km2(h3_resolution)) or h3_hex_area_km2(h3_resolution)),
        )
        combined_establishment_layers = _combined_establishment_family_layers(
            region,
            energy_model_state.get("proposal_frame", pd.DataFrame()),
            energy_model_state.get("solar_proposal_frame", pd.DataFrame()),
            h3_resolution,
            lock_h3_resolution,
        )
        if combined_establishment_layers:
            layers.extend(combined_establishment_layers)
            unified_notes.append(
                f"{COMBINED_ESTABLISHMENT_LAYER_LABEL} ersätter de separata sol- och vindlagren: blå = vind, gul = sol, grön = båda, röd = inte lämplig."
            )
        outside_lp_need_layers = _outside_lp_need_family_layers(
            region,
            energy_model_state.get("proposal_frame", pd.DataFrame()),
            energy_model_state.get("solar_proposal_frame", pd.DataFrame()),
            h3_resolution,
            lock_h3_resolution,
        )
        if outside_lp_need_layers:
            layers.extend(outside_lp_need_layers)
            unified_notes.append(
                f"{OUTSIDE_LP_NEED_LAYER_LABEL} visas som centrerade child-hexagoner så att etableringsytan under fortfarande går att läsa."
            )

    if energy_model_state.get("available"):
        energy_model_state["combined_establishment_stats"] = _combined_establishment_stats(energy_model_state)

    if show_v10 or show_cluster or show_factor:
        landscape_frame = _landscape_frame(region, landscape_manifest, h3_resolution)
        if show_v10:
            layers.extend(
                _hex_family_layers(
                    region,
                    h3_resolution,
                    lock_h3_resolution,
                    "landscape_types_hex",
                    "Landskapstyper",
                    lambda resolution: _landscape_type_layer(
                        "Landskapstyper",
                        _landscape_frame(region, landscape_manifest, int(resolution)),
                        landscape_manifest,
                        _h3_display_geometry_path(region, int(resolution)),
                    ),
                )
            )
        if show_cluster:
            layers.extend(
                _hex_family_layers(
                    region,
                    h3_resolution,
                    lock_h3_resolution,
                    "landscape_structures_hex",
                    "Landskapstrukturer",
                    lambda resolution: _landscape_layer(
                        "Landskapstrukturer",
                        _landscape_frame(region, landscape_manifest, int(resolution)),
                        landscape_manifest,
                        factors[0],
                        _h3_display_geometry_path(region, int(resolution)),
                        "cluster",
                    ),
                )
            )
        if show_factor:
            layers.extend(
                _hex_family_layers(
                    region,
                    h3_resolution,
                    lock_h3_resolution,
                    f"landscape_factor_{selected_factor}",
                    "Landskapsfaktorer",
                    lambda resolution: _landscape_layer(
                        "Landskapsfaktorer",
                        _landscape_frame(region, landscape_manifest, int(resolution)),
                        landscape_manifest,
                        selected_factor,
                        _h3_display_geometry_path(region, int(resolution)),
                        "factor",
                    ),
                )
            )

    layers = _dedupe_layers(layers)
    layer_control_count = len(_layer_control_rows(layers, "combined"))
    note_body = (
        f"{layer_control_count} lagergrupper är tända. "
        f"{resolution_info.get('caption') or 'Hexvisningen följer vald H3-upplösning.'}"
    )
    proposal_stats_for_note = energy_model_state.get("proposal_stats") if isinstance(energy_model_state, dict) else None
    solar_stats_for_note = energy_model_state.get("solar_proposal_stats") if isinstance(energy_model_state, dict) else None
    warning_parts: list[str] = []
    if isinstance(proposal_stats_for_note, dict) and float(proposal_stats_for_note.get("et_unmet_area_km2", 0.0) or 0.0) > 0:
        outside_area_for_note = float(proposal_stats_for_note.get("outside_selected_area_km2", 0.0) or 0.0)
        warning_parts.append(f"vind ca {outside_area_for_note:.0f} km2")
    if isinstance(solar_stats_for_note, dict) and float(solar_stats_for_note.get("outside_selected_area_km2", 0.0) or 0.0) > 0:
        solar_outside_area = float(solar_stats_for_note.get("outside_selected_area_km2", 0.0) or 0.0)
        warning_parts.append(f"sol ca {solar_outside_area:.0f} km2")
    if warning_parts:
        note_body = (
            "<strong style='color:#be123c;'>Varning:</strong> "
            "Energiscenariot kräver mer etableringsyta än landskapets potential rymmer. "
            f"{OUTSIDE_LP_NEED_LAYER_LABEL}: " + ", ".join(warning_parts) + "."
        )
    _render_layers(
        region,
        layers,
        opacity,
        map_state_key=f"{region.get('region_id', 'region')}:workspace" if preserve_map_view else None,
        map_reset_token=map_reset_token,
        opacity_key_prefix="combined",
        note_title="Gemensam potentialvy",
        note_body=note_body,
    )

    summary_target = right_panel or st.container()
    with summary_target:
        _combined_summary(
            {
                "layers": layers,
                "potential_frames": potential_frames,
                "resolution": h3_resolution,
                "resolution_info": resolution_info,
                "landscape_active": bool(show_v10 or show_cluster or show_factor),
                "opacity_key_prefix": "combined",
            },
            scenario_state,
        )
        _render_energy_model_summary(energy_model_state)
        with st.expander("Byggstatus", expanded=False):
            if show_user_solar:
                st.metric(f"Aktiv {SOLAR_LARGE_SCALE_LABEL}", "På")
                st.caption(f"{SOLAR_LARGE_SCALE_LABEL} visas som solpolygon och kan ingå i {COMBINED_ESTABLISHMENT_LAYER_LABEL}.")
            if show_solar_v1:
                stats = energy_model_state.get("solar_v1_stats") if isinstance(energy_model_state, dict) else None
                st.metric(f"Aktiv {SOLAR_SMALL_SCALE_LABEL}", "På")
                st.caption(
                    f"Småskalig solyta beräknas som befolkning per hex × {solar_v1_area_m2_per_person:.0f} m2/person."
                )
                st.caption(_solar_v1_population_source_status())
                if isinstance(stats, dict):
                    st.caption(
                        f"Total småskalig solyta: {float(stats.get('total_area_km2', 0.0) or 0.0):.2f} km²; "
                        f"kvarvarande solbehov: {float(stats.get('remaining_area_km2', 0.0) or 0.0):.2f} km²."
                    )
            if show_user_solar:
                if solar_large_population_active:
                    st.caption(
                        f"Avstånd till befolkning är {float(solar_params.get('population_buffer_m', 250.0) or 250.0):.0f} m för storskalig sol."
                    )
                if solar_large_protected_active:
                    st.caption(
                        f"{len(solar_large_protected_layer_ids)} skyddslager är aktiva med {float(solar_params.get('protected_buffer_m', 0.0) or 0.0):.0f} m buffert."
                    )
            if show_user_wind and custom_wind_preview_state is not None:
                left_metric, right_metric = st.columns(2)
                left_metric.metric("LP Vind: aktiva källager", int(custom_wind_preview_state["active_source_count"]))
                right_metric.metric("LP Vind: buffertgrupper", int(custom_wind_preview_state["active_group_count"]))
                combined_share = custom_wind_preview_state["combined_land_share_pct"]
                st.metric("LP Vind: potentiell landandel", "-" if combined_share is None else f"{float(combined_share):.1f}%")
                if wind_controls_applied:
                    st.caption(ui_text("controls_applied", WIND_CONTROL_LANGUAGE))
            for note in unified_notes:
                st.caption(note)
        _data_method(region)


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")
    left_panel, main_panel, right_panel = _workspace_shell()
    region = _select_region(None)
    scenario_state = _scenario_state(region, None)
    context = _load_context(region)

    st.session_state.setdefault("combined_h3_resolution", _preferred_h3_resolution(region, 10))
    h3_resolution = int(st.session_state.get("combined_h3_resolution", _preferred_h3_resolution(region, 10)))
    with main_panel:
        _workspace_header(region, scenario_state, h3_resolution)
        _unified_workspace_tab(region, scenario_state, context, left_panel, right_panel)


if __name__ == "__main__":
    main()
