from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from acceptance_model.layers import (
    acceptance_reference_payload,
    layer_status_table,
    load_registry,
    ordered_groups,
    ordered_layers,
    source_geojson_for_layer,
)
from acceptance_model.leaflet_map import (
    build_leaflet_html,
    combined_overlay as combined_overlay_spec,
    group_overlay,
    source_overlay,
)
from acceptance_model.runtime_geometry import run_geometry_runtime


APP_TITLE = "Bornholm Wind-Acceptance Prototype"

CRITICAL_REVIEW = [
    "This stage should stay geometry-first. Settlement, roads, substations, and protected areas mean something as real source geometries, so the live map should show and buffer those geometries directly instead of collapsing them to hexes too early.",
    "Settlement proxies still overlap heavily, so group logic should use dissolved unions and shared buffers rather than additive scoring. That avoids counting the same built structure multiple times.",
    "Electrical infrastructure still needs different semantics: buffering selected grid assets by a maximum connection distance is a feasibility rule, not a classic no-go buffer.",
    "Population points are visually noisy as raw points at this scale, so the prototype now displays them as a dissolved 100 m buffer polygon. That keeps the layer legible while still making the source logic explicit.",
    "All source, group, and combined geometries are clipped to a Bornholm landmask derived from the full-coverage prekvart_bornholm polygon, so buffers do not spill into the sea.",
    "Combined acceptance should always be shown as the land that remains available inside a polygon. Without a feasibility group, that means Bornholm landmass minus the active conflict layers. With a feasibility group, it means feasible land minus active conflicts.",
]

HEXAGON_NOTE = [
    "Hexagons are no longer used in the live map stage of this prototype.",
    "They can still be useful later for reporting, ranking, comparison with the landscape-analysis clusters, or summarising how much land remains after geometry-first filtering.",
    "If you later want a hex view again, it should come after the geometry-based buffers and intersections, not before them.",
]


def _state_key(prefix: str, item_id: str) -> str:
    return f"{prefix}__{item_id}"


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _source_opacity(blend_value: int) -> float:
    return max(0.0, 1.0 - (int(blend_value) / 100.0))


def _group_opacity(blend_value: int) -> float:
    return max(0.0, min(1.0, int(blend_value) / 100.0))


def _init_state() -> None:
    groups, layers, _ = load_registry()
    for group in groups.values():
        st.session_state.setdefault(_state_key("analysis", group.id), group.analysis_default_m)
        st.session_state.setdefault(_state_key("blend", group.id), group.blend_default)
    for layer in layers.values():
        st.session_state.setdefault(_state_key("layer", layer.id), False)


def _layer_status_lookup(registry_meta: dict[str, object]) -> dict[str, dict[str, object]]:
    status_df = layer_status_table(registry_meta)
    return {row["layer_id"]: row.to_dict() for _, row in status_df.iterrows()}


def _build_group_controls(registry_meta: dict[str, object]) -> tuple[dict[str, list[str]], bool]:
    availability = _layer_status_lookup(registry_meta)
    selected: dict[str, list[str]] = {group.id: [] for group in ordered_groups()}

    with st.sidebar:
        st.header("Groups")
        st.caption("Select source layers per group. Group polygons are dissolved real-geometry buffers, not hex cells.")
        with st.form("group_controls", clear_on_submit=False):
            st.caption("Map updates when you click Apply changes. This avoids rerunning the geometry engine on every slider move.")

            for group in ordered_groups():
                with st.expander(group.label, expanded=group.id in {"settlement", "transport", "electrical"}):
                    st.caption(group.interpretation)
                    st.slider(
                        group.analysis_label,
                        min_value=group.analysis_min_m,
                        max_value=group.analysis_max_m,
                        step=group.analysis_step_m,
                        key=_state_key("analysis", group.id),
                        help="Analysis only. This value changes the real buffer / feasibility geometry.",
                    )
                    st.slider(
                        "Display / blend",
                        min_value=0,
                        max_value=100,
                        step=5,
                        key=_state_key("blend", group.id),
                        help="Display only. 0 = source layers, 100 = group layer.",
                    )

                    for layer in [item for item in ordered_layers() if item.group_id == group.id]:
                        status = availability.get(layer.id, {})
                        ready = (
                            bool(status.get("geojson_ready"))
                            and bool(status.get("source_exists"))
                            and int(status.get("feature_count", 0) or 0) > 0
                            and str(status.get("status", "")) == "ok"
                        )
                        message = str(status.get("message", "") or layer.note or "Layer is not available for the current prototype.")
                        checked = st.checkbox(layer.label, key=_state_key("layer", layer.id), disabled=not ready, help=message)
                        if checked and ready:
                            selected[group.id].append(layer.id)

                    if not selected[group.id]:
                        st.caption("Group inactive. Select one or more source layers above.")

            applied = st.form_submit_button("Apply changes", type="primary", use_container_width=True)

    return selected, applied


def _runtime_payload(selected_by_group: dict[str, list[str]]) -> str:
    payload = {"groups": {}}
    for group in ordered_groups():
        active_layer_ids = selected_by_group.get(group.id, [])
        if not active_layer_ids:
            continue
        payload["groups"][group.id] = {
            "active_layer_ids": active_layer_ids,
            "analysis_value_m": int(st.session_state[_state_key("analysis", group.id)]),
        }
    return json.dumps(payload, sort_keys=True)


def _source_overlay_specs(selected_by_group: dict[str, list[str]], registry_meta: dict[str, object]) -> list[dict[str, object]]:
    _, layers, _ = load_registry()
    specs = []
    for group in ordered_groups():
        blend_value = int(st.session_state[_state_key("blend", group.id)])
        opacity = _source_opacity(blend_value)
        for layer_id in selected_by_group.get(group.id, []):
            geojson = source_geojson_for_layer(registry_meta, layer_id)
            if geojson is None:
                continue
            layer = layers[layer_id]
            specs.append(
                source_overlay(
                    name=f"Source: {layer.label}",
                    geojson=geojson,
                    color_hex=_rgb_to_hex(layer.source_color),
                    opacity=opacity,
                    point_radius=layer.point_radius,
                )
            )
    return specs


def _group_overlay_specs(runtime_result: dict[str, object]) -> list[dict[str, object]]:
    groups, _, _ = load_registry()
    specs = []
    for group in ordered_groups():
        runtime_group = runtime_result["groups"].get(group.id)
        if runtime_group is None or runtime_group.get("geojson") is None:
            continue
        opacity = _group_opacity(int(st.session_state[_state_key("blend", group.id)]))
        specs.append(
            group_overlay(
                name=f"Group: {groups[group.id].label}",
                geojson=runtime_group["geojson"],
                color_hex=_rgb_to_hex(groups[group.id].group_color),
                opacity=opacity,
            )
        )
    return specs


def _combined_overlay_spec(runtime_result: dict[str, object]) -> dict[str, object] | None:
    combined = runtime_result.get("combined")
    if combined is None or combined.get("geojson") is None:
        return None
    return combined_overlay_spec("Combined: acceptance", combined["geojson"], combined.get("semantics"))


def _group_summary_frame(selected_by_group: dict[str, list[str]], runtime_result: dict[str, object]) -> pd.DataFrame:
    _, layers, _ = load_registry()
    rows = []
    for group in ordered_groups():
        selected_layer_ids = selected_by_group.get(group.id, [])
        selected_labels = [layers[layer_id].label for layer_id in selected_layer_ids]
        runtime_group = runtime_result["groups"].get(group.id)
        land_share = None
        if runtime_group and runtime_group.get("land_share_pct") is not None:
            land_share = f"{float(runtime_group['land_share_pct']):.1f}%"
        rows.append(
            {
                "Group": group.label,
                "Type": group.analysis_kind,
                "Active": bool(selected_layer_ids),
                "Sources": ", ".join(selected_labels) if selected_labels else "None",
                "Analysis (m)": int(st.session_state[_state_key("analysis", group.id)]),
                "Blend": f"{int(st.session_state[_state_key('blend', group.id)])}%",
                "Land share": land_share,
                "Role": runtime_group.get("role") if runtime_group else None,
            }
        )
    return pd.DataFrame(rows)


def _map_legend() -> None:
    groups, _, _ = load_registry()
    st.caption("Map reading guide")
    st.caption("Source layers are real source geometries. Population points are shown as a dissolved 100 m display buffer.")
    st.caption("Group layers are dissolved analysis buffers or feasibility polygons built from the selected source layers. Electrical shows the land area that stays within the chosen maximum connection distance.")
    st.caption("The combined layer always shows accepted land that remains inside Bornholm after the active group rules are applied.")
    st.caption("The combined acceptance layer is turned on by default. Source and group layers are still available in the map control, but start hidden.")
    st.caption("Five optional V4 hex reference layers are also available in the map control: Hog, Mellan, Lag, Mellan score, and Landskapskluster. The map now includes a separate V4 opacity slider and legend.")
    st.caption("The basemap toggle is inside the map control: OSM or Satellite.")
    for group in ordered_groups():
        color = groups[group.id].group_color
        swatch = f"<span style='display:inline-block;width:12px;height:12px;border-radius:2px;background:rgb({color[0]},{color[1]},{color[2]});margin-right:6px;'></span>{group.label}"
        st.markdown(swatch, unsafe_allow_html=True)


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("Geometry-first prototype. The live map now uses real buffered and dissolved source geometries instead of hexagons.")

groups, layers, registry_meta = load_registry()
_init_state()

status_df = layer_status_table(registry_meta)
selected_by_group, controls_applied = _build_group_controls(registry_meta)
runtime_config_json = _runtime_payload(selected_by_group)

try:
    with st.spinner("Updating geometry..."):
        runtime_result = run_geometry_runtime(runtime_config_json)
except Exception as exc:
    st.error(f"Geometry runtime failed: {exc}")
    st.stop()

source_specs = _source_overlay_specs(selected_by_group, registry_meta)
group_specs = _group_overlay_specs(runtime_result)
combined_spec = _combined_overlay_spec(runtime_result)
reference_payload = acceptance_reference_payload(registry_meta)
map_html = build_leaflet_html(source_specs, group_specs, combined_spec, reference_payload)

active_source_count = sum(len(v) for v in selected_by_group.values())
active_group_count = len(runtime_result["groups"])
combined_share = None
if runtime_result.get("combined") and runtime_result["combined"].get("land_share_pct") is not None:
    combined_share = f"{float(runtime_result['combined']['land_share_pct']):.1f}%"
source_ready_count = int(
    (
        status_df["geojson_ready"].astype(bool)
        & status_df["source_exists"].astype(bool)
        & status_df["status"].astype(str).eq("ok")
        & (status_df["feature_count"].fillna(0) > 0)
    ).sum()
)

tab_map, tab_review, tab_data = st.tabs(["Prototype", "Model review", "Data status"])

with tab_map:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Selectable source layers", f"{source_ready_count}")
    m2.metric("Active source layers", f"{active_source_count}")
    m3.metric("Active groups", f"{active_group_count}")
    m4.metric("Combined acceptance", combined_share or "Off")

    if controls_applied:
        st.caption("Updated with the latest selected layers and slider values.")

    left, right = st.columns([2.3, 1.0], gap="large")
    with left:
        components.html(map_html, height=760)
        st.caption("Group polygons are real dissolved buffers or feasibility areas derived from the selected source layers. The combined layer always shows accepted land that remains available after the active rules are applied, and it is the only overlay shown by default.")
    with right:
        st.subheader("Group summary")
        st.dataframe(_group_summary_frame(selected_by_group, runtime_result), use_container_width=True, hide_index=True, height=360)
        _map_legend()
        st.caption(f"Runtime cache key: {runtime_result['cache_key']}")

with tab_review:
    st.subheader("Critical review")
    for item in CRITICAL_REVIEW:
        st.write(f"- {item}")

    st.subheader("Hexagon note")
    for item in HEXAGON_NOTE:
        st.write(f"- {item}")

with tab_data:
    st.subheader("Layer asset status")
    st.dataframe(status_df, use_container_width=True, hide_index=True, height=420)
    st.caption("Static source GeoJSON and readiness are exported by `script/acceptance/export_wind_acceptance_prototype_assets.R`. Dynamic group polygons are rendered by `script/acceptance/render_wind_acceptance_geometry_runtime.R`.")
    if not status_df.empty and (status_df["status"] != "ok").any():
        st.warning("Some source assets are not ready. Disabled checkboxes in the sidebar come from this table.")
    else:
        st.success("All source assets required by the current prototype are available.")
