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
    cluster_summary,
    factor_columns,
    factor_label,
    feature_collection_for_frame,
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
    wind_potential_frame,
)


PAGE_TITLE = "Sol- och vindpotential"
VIEW_OPTIONS = ["Samlad potential", "Bygg solpotential", "Bygg vindpotential"]


def _region_choice_label(region: dict[str, Any]) -> str:
    status = str(region.get("status", "planned"))
    suffix = "" if status == "active" else " (planerad)"
    return f"{region.get('display_name', region.get('region_id'))}{suffix}"


def _select_region() -> dict[str, Any]:
    regions = list_regions()
    if not regions:
        st.error("Inga regionmanifest hittades.")
        st.stop()

    options = {str(region["region_id"]): region for region in regions}
    default_index = list(options).index("bornholm") if "bornholm" in options else 0
    selected_id = st.sidebar.selectbox(
        "Region",
        options=list(options),
        index=default_index,
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


def _map_controls(region: dict[str, Any], key_prefix: str) -> tuple[int, float]:
    left, right = st.columns([0.58, 0.42], gap="large")
    with left:
        h3_resolution = st.radio(
            "H3-rollup",
            options=_available_h3_resolutions(region),
            index=0,
            format_func=lambda value: _h3_option_label(region, value),
            horizontal=True,
            key=f"{key_prefix}_h3_resolution",
        )
    with right:
        opacity = st.slider(
            "Opacitet hexlager",
            min_value=0.15,
            max_value=1.0,
            value=0.78,
            step=0.05,
            key=f"{key_prefix}_hex_opacity",
        )
    return int(h3_resolution), float(opacity)


def _display_mode_control(key_prefix: str) -> str:
    return str(
        st.radio(
            "Visningsläge potential",
            options=["Hexagon", "Vektor", "Båda"],
            index=0,
            horizontal=True,
            key=f"{key_prefix}_display_mode",
            help="Vektorlager kopplas in via manifest i nästa datasteg. Hexagon är fullt fungerande nu.",
        )
    )


def _wants_hex(display_mode: str) -> bool:
    return display_mode in {"Hexagon", "Båda"}


def _wants_vector(display_mode: str) -> bool:
    return display_mode in {"Vektor", "Båda"}


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
    entry = _solar_rollup_entry(potential_manifest, resolution)
    if entry is not None:
        frame = rollup_frame_for_entry(entry)
    else:
        frame = rollup_potential_frame(
            solar_capacity_frame(landscape_manifest, solar_rules),
            resolution,
            _class_breaks(solar_rules),
            "solar",
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
    frame = rollup_potential_frame(base, resolution, _class_breaks(rules), "solar")
    return _filter_frame_to_display_geometries(frame, _h3_display_geometry_path(region, resolution))


def _wind_frame(
    region: dict[str, Any],
    landscape_manifest: dict[str, Any],
    solar_rules: dict[str, Any],
    resolution: int,
    params: dict[str, float],
) -> pd.DataFrame:
    base = wind_potential_frame(landscape_manifest, _class_breaks(solar_rules), params)
    frame = rollup_potential_frame(base, resolution, _class_breaks(solar_rules), "wind")
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
        "everyday_matrix_bonus": cluster_terms.get("class_km:2", 15.0),
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
        if term.get("cluster_ref") == "class_km:2":
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
        "settlement_distance_m": 700.0,
        "road_distance_m": 150.0,
        "grid_max_distance_m": 4000.0,
        "protected_buffer_m": 0.0,
        "coastal_buffer_m": 0.0,
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


def _save_solar_potential(params: dict[str, float], resolution: int) -> None:
    st.session_state["saved_solar_potential"] = {
        "params": dict(params),
        "preview_resolution": int(resolution),
    }
    st.session_state["show_user_solar"] = True


def _save_wind_potential(ui_params: dict[str, float], resolution: int) -> None:
    st.session_state["saved_wind_potential"] = {
        "ui_params": dict(ui_params),
        "preview_resolution": int(resolution),
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


def _set_active_view(view: str) -> None:
    st.session_state["active_view"] = view


def _render_layers(region: dict[str, Any], layers: list[dict[str, Any]], opacity: float) -> None:
    if not layers:
        st.info("Välj minst ett kartlager.")
        return
    map_html = build_layered_hex_map_html(
        layers,
        center=list(region.get("default_map_center", [55.14, 14.92])),
        zoom=int(region.get("default_zoom", 9)),
        bounds=region.get("default_map_bounds"),
        fill_opacity=opacity,
    )
    components.html(map_html, height=780)


def _potential_layer(
    name: str,
    frame: pd.DataFrame,
    technology: str,
    display_geometry_path: str | None,
    legend_items: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "name": name,
        "feature_collection": potential_feature_collection(frame, technology, display_geometry_path),
        "fill_property": "fill",
        "legend_items": legend_items,
        "legend_id": "potential_classes",
        "legend_title": "Potentialklasser",
        "default_visible": True,
    }


def _landscape_layer(
    name: str,
    frame: pd.DataFrame,
    manifest: dict[str, Any],
    factor: str,
    display_geometry_path: str | None,
    mode: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "feature_collection": feature_collection_for_frame(manifest, frame, factor, display_geometry_path),
        "fill_property": "factor_fill" if mode == "factor" else "cluster_fill",
        "legend_items": _factor_legend_items() if mode == "factor" else _cluster_legend_items(manifest),
        "legend_id": f"landscape_{mode}_{factor}",
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
            st.write("Landskapslager visas med samma H3-rollup som potentiallagren.")


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


def _combined_tab(region: dict[str, Any], scenario_state: dict[str, Any], context: dict[str, Any]) -> None:
    landscape_manifest = context["landscape_manifest"]
    potential_manifest = context["potential_manifest"]
    solar_rules = context["solar_rules"]
    factors = factor_columns(landscape_manifest, load_factor_scores(landscape_manifest))

    h3_resolution, opacity = _map_controls(region, "combined")
    display_mode = _display_mode_control("combined")
    display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
    saved_solar_params = _saved_solar_params()
    saved_wind_ui_params = _saved_wind_params()

    with st.expander("Kartlager", expanded=True):
        c1, c2, c3 = st.columns(3)
        show_default_solar = c1.checkbox("Default solpotential", value=True, key="show_default_solar")
        show_user_solar = c1.checkbox("Egen solpotential", value=False, key="show_user_solar")
        c1.caption("Egen sol: sparad" if saved_solar_params is not None else "Egen sol: ej sparad")
        show_default_wind = c2.checkbox("Default vindpotential", value=False, key="show_default_wind")
        show_user_wind = c2.checkbox("Egen vindpotential", value=False, key="show_user_wind")
        c2.caption("Egen vind: sparad" if saved_wind_ui_params is not None else "Egen vind: ej sparad")
        show_cluster = c3.checkbox("Landskapskluster", value=False, key="show_landscape_cluster")
        show_factor = c3.checkbox("Landskapsfaktor", value=False, key="show_landscape_factor")
        selected_factor = st.selectbox(
            "Faktor för landskapsfaktor",
            options=factors,
            index=0,
            format_func=lambda factor: f"{factor} - {factor_label(landscape_manifest, factor)}",
            disabled=not show_factor,
            key="combined_landscape_factor",
        )

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
        if _wants_hex(display_mode):
            frame = _default_solar_frame(region, landscape_manifest, potential_manifest, solar_rules, h3_resolution)
            layers.append(_potential_layer(f"Default solpotential R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Default solpotential", "technology": "solar", "frame": frame})
        if _wants_vector(display_mode):
            vector_placeholders.append("default solpotential")

    if show_user_solar and saved_solar_params is not None:
        if _wants_hex(display_mode):
            frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, saved_solar_params)
            layers.append(_potential_layer(f"Egen solpotential R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Egen solpotential", "technology": "solar", "frame": frame})
        if _wants_vector(display_mode):
            vector_placeholders.append("sparad egen solpotential")

    if show_default_wind:
        if _wants_hex(display_mode):
            params = _wind_score_params_from_ui(_default_wind_params())
            frame = _wind_frame(region, landscape_manifest, solar_rules, h3_resolution, params)
            layers.append(_potential_layer(f"Default vindpotential R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Default vindpotential", "technology": "wind", "frame": frame})
        if _wants_vector(display_mode):
            vector_placeholders.append("default vindpotential")

    if show_user_wind and saved_wind_ui_params is not None:
        if _wants_hex(display_mode):
            params = _wind_score_params_from_ui(saved_wind_ui_params)
            frame = _wind_frame(region, landscape_manifest, solar_rules, h3_resolution, params)
            layers.append(_potential_layer(f"Egen vindpotential R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
            potential_frames.append({"label": "Egen vindpotential", "technology": "wind", "frame": frame})
        if _wants_vector(display_mode):
            vector_placeholders.append("sparad egen vindpotential")

    if show_cluster or show_factor:
        landscape_frame = _landscape_frame(region, landscape_manifest, h3_resolution)
        if show_cluster:
            layers.append(_landscape_layer(f"Landskapskluster R{h3_resolution}", landscape_frame, landscape_manifest, factors[0], display_geometry_path, "cluster"))
        if show_factor:
            layers.append(_landscape_layer(f"{selected_factor}: {factor_label(landscape_manifest, selected_factor)} R{h3_resolution}", landscape_frame, landscape_manifest, selected_factor, display_geometry_path, "factor"))

    map_column, info_column = st.columns([0.72, 0.28], gap="large")
    with map_column:
        _vector_placeholder(vector_placeholders)
        _render_layers(region, layers, opacity)
    with info_column:
        with st.container(border=True):
            _combined_summary(
                {
                    "layers": layers,
                    "potential_frames": potential_frames,
                    "resolution": h3_resolution,
                    "landscape_active": bool(show_cluster or show_factor),
                },
                scenario_state,
            )
            _data_method(region)


def _solar_builder_tab(region: dict[str, Any], context: dict[str, Any]) -> None:
    landscape_manifest = context["landscape_manifest"]
    solar_rules = context["solar_rules"]
    defaults = _default_solar_params(solar_rules)
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
        h3_resolution, opacity = _map_controls(region, "solar_builder_preview")
        display_mode = _display_mode_control("solar_builder_preview")
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        frame = _custom_solar_frame(region, landscape_manifest, solar_rules, h3_resolution, params)
        if _wants_vector(display_mode):
            _vector_placeholder(["egen solpotential"])
        layers = []
        if _wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad solförhandsvisning R{h3_resolution}", frame, "solar", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(region, layers, opacity)
    with info_col:
        with st.container(border=True):
            _potential_detail_panel("Osparad solförhandsvisning", frame, "solar", h3_resolution)
            with st.expander("Aktiva solparametrar"):
                st.json(params)

    st.divider()
    action_left, action_right = st.columns(2)
    if action_left.button("Spara solpotential", type="primary", use_container_width=True):
        _save_solar_potential(params, h3_resolution)
        st.success("Solpotential sparad. Den kan nu togglas på i Samlad potential.")
    action_right.button(
        "Gå tillbaka till huvudkartan",
        use_container_width=True,
        on_click=_set_active_view,
        args=("Samlad potential",),
    )


def _wind_builder_tab(region: dict[str, Any], context: dict[str, Any]) -> None:
    landscape_manifest = context["landscape_manifest"]
    solar_rules = context["solar_rules"]
    defaults = _default_wind_params()
    st.subheader("Bygg vindpotential")
    st.caption("Vindbyggaren följer vindacceptansappens reglagelogik, men översätter den till en H3-baserad potentialscore i denna första version.")

    if st.button("Återställ vind-default", key="reset_wind_builder"):
        _reset_builder("wind_builder", defaults)

    control_col, map_col, info_col = st.columns([0.24, 0.50, 0.26], gap="large")
    with control_col:
        _builder_slider("wind_builder", "settlement_distance_m", "Minsta avstånd till boende", 100.0, 3000.0, 50.0, defaults, "Större avstånd ger hårdare bebyggelsestraff.")
        _builder_slider("wind_builder", "road_distance_m", "Minsta avstånd till vägar", 50.0, 2000.0, 25.0, defaults, "Större avstånd ger hårdare transport-/bebyggelsestraff.")
        _builder_slider("wind_builder", "grid_max_distance_m", "Max avstånd till elinfrastruktur", 500.0, 15000.0, 250.0, defaults, "Större tillåtet avstånd gör fler lägen tekniskt möjliga i denna proxy.")
        _builder_slider("wind_builder", "protected_buffer_m", "Buffert skyddade områden", 0.0, 2000.0, 50.0, defaults, "Större buffert sänker potential nära skyddade skogs- och habitatmiljöer.")
        _builder_slider("wind_builder", "coastal_buffer_m", "Buffert kust/strand", 0.0, 1000.0, 50.0, defaults, "Större buffert sänker potential i kust- och låglandsmiljöer.")
        _builder_slider("wind_builder", "landscape_sensitivity_percent", "Landskapskänslighet", 0.0, 120.0, 5.0, defaults, "Viktar hur starkt landskapsrollerna ska bromsa vindpotentialen.")
        st.caption("Geometriska källager från vindacceptansappen kopplas in stegvis. Här används landskapsanalysens roller som snabb score-proxy.")

    ui_params = _state_params("wind_builder", defaults)
    st.session_state["wind_builder_params"] = ui_params
    score_params = _wind_score_params_from_ui(ui_params)
    with map_col:
        h3_resolution, opacity = _map_controls(region, "wind_builder_preview")
        display_mode = _display_mode_control("wind_builder_preview")
        display_geometry_path = _h3_display_geometry_path(region, h3_resolution)
        frame = _wind_frame(region, landscape_manifest, solar_rules, h3_resolution, score_params)
        if _wants_vector(display_mode):
            _vector_placeholder(["egen vindpotential"])
        layers = []
        if _wants_hex(display_mode):
            layers.append(_potential_layer(f"Osparad vindförhandsvisning R{h3_resolution}", frame, "wind", display_geometry_path, _solar_legend_items(solar_rules)))
        _render_layers(region, layers, opacity)
    with info_col:
        with st.container(border=True):
            _potential_detail_panel("Osparad vindförhandsvisning", frame, "wind", h3_resolution)
            with st.expander("Aktiva vindparametrar"):
                st.json(ui_params)

    st.divider()
    action_left, action_right = st.columns(2)
    if action_left.button("Spara vindpotential", type="primary", use_container_width=True):
        _save_wind_potential(ui_params, h3_resolution)
        st.success("Vindpotential sparad. Den kan nu togglas på i Samlad potential.")
    action_right.button(
        "Gå tillbaka till huvudkartan",
        use_container_width=True,
        on_click=_set_active_view,
        args=("Samlad potential",),
    )


def _view_selector() -> str:
    st.session_state.setdefault("active_view", VIEW_OPTIONS[0])
    if hasattr(st, "segmented_control"):
        selected = st.segmented_control("Vy", VIEW_OPTIONS, key="active_view", label_visibility="collapsed")
        return str(selected or st.session_state.get("active_view", VIEW_OPTIONS[0]))
    return str(st.radio("Vy", VIEW_OPTIONS, horizontal=True, key="active_view", label_visibility="collapsed"))


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    region = _select_region()
    scenario_state = _scenario_sidebar(region)
    context = _load_context(region)

    view = _view_selector()
    h3_resolution = int(st.session_state.get("combined_h3_resolution", region.get("default_h3_resolution", 9)))
    _metric_header(region, scenario_state, h3_resolution)

    if view == "Bygg solpotential":
        _solar_builder_tab(region, context)
    elif view == "Bygg vindpotential":
        _wind_builder_tab(region, context)
    else:
        _combined_tab(region, scenario_state, context)


if __name__ == "__main__":
    main()
