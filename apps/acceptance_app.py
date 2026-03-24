from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from acceptance_model.i18n import (
    analysis_kind_label,
    critical_review_items,
    group_analysis_label,
    group_interpretation,
    group_label,
    hexagon_note_items,
    language_option_label,
    layer_label,
    layer_note,
    role_label,
    ui_text,
)
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


PAGE_TITLE = "Bornholm Wind-Acceptance Prototype"


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
    st.session_state.setdefault("ui_language", "sv")
    for group in groups.values():
        st.session_state.setdefault(_state_key("analysis", group.id), group.analysis_default_m)
        st.session_state.setdefault(_state_key("blend", group.id), group.blend_default)
    for layer in layers.values():
        st.session_state.setdefault(_state_key("layer", layer.id), False)


def _language_toggle() -> str:
    st.radio(
        ui_text("language_toggle", st.session_state.get("ui_language", "sv")),
        options=["sv", "en"],
        format_func=language_option_label,
        horizontal=True,
        key="ui_language",
    )
    return str(st.session_state.get("ui_language", "sv"))


def _layer_status_lookup(registry_meta: dict[str, object]) -> dict[str, dict[str, object]]:
    status_df = layer_status_table(registry_meta)
    return {row["layer_id"]: row.to_dict() for _, row in status_df.iterrows()}


def _build_group_controls(registry_meta: dict[str, object], language: str) -> tuple[dict[str, list[str]], bool]:
    availability = _layer_status_lookup(registry_meta)
    selected: dict[str, list[str]] = {group.id: [] for group in ordered_groups()}

    with st.sidebar:
        st.header(ui_text("groups_header", language))
        st.caption(ui_text("groups_caption", language))
        with st.form("group_controls", clear_on_submit=False):
            st.caption(ui_text("apply_hint", language))

            for group in ordered_groups():
                with st.expander(group_label(group, language, group.label), expanded=group.id in {"settlement", "transport", "electrical"}):
                    st.caption(group_interpretation(group, language, group.interpretation))
                    st.slider(
                        group_analysis_label(group, language, group.analysis_label),
                        min_value=group.analysis_min_m,
                        max_value=group.analysis_max_m,
                        step=group.analysis_step_m,
                        key=_state_key("analysis", group.id),
                        help=ui_text("analysis_slider_help", language),
                    )
                    st.slider(
                        ui_text("display_blend", language),
                        min_value=0,
                        max_value=100,
                        step=5,
                        key=_state_key("blend", group.id),
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
                            key=_state_key("layer", layer.id),
                            disabled=not ready,
                            help=message,
                        )
                        if checked and ready:
                            selected[group.id].append(layer.id)

                    if not selected[group.id]:
                        st.caption(ui_text("group_inactive", language))

            applied = st.form_submit_button(ui_text("apply_changes", language), type="primary", use_container_width=True)

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


def _source_overlay_specs(selected_by_group: dict[str, list[str]], registry_meta: dict[str, object], language: str) -> list[dict[str, object]]:
    _, layers, _ = load_registry()
    specs: list[dict[str, object]] = []
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
                    name=f"{ui_text('source_prefix', language)}: {layer_label(layer, language, layer.label)}",
                    geojson=geojson,
                    color_hex=_rgb_to_hex(layer.source_color),
                    opacity=opacity,
                    point_radius=layer.point_radius,
                )
            )
    return specs


def _group_overlay_specs(runtime_result: dict[str, object], language: str) -> list[dict[str, object]]:
    groups, _, _ = load_registry()
    specs: list[dict[str, object]] = []
    for group in ordered_groups():
        runtime_group = runtime_result["groups"].get(group.id)
        if runtime_group is None or runtime_group.get("geojson") is None:
            continue
        opacity = _group_opacity(int(st.session_state[_state_key("blend", group.id)]))
        specs.append(
            group_overlay(
                name=f"{ui_text('group_prefix', language)}: {group_label(groups[group.id], language, groups[group.id].label)}",
                geojson=runtime_group["geojson"],
                color_hex=_rgb_to_hex(groups[group.id].group_color),
                opacity=opacity,
            )
        )
    return specs


def _combined_overlay_spec(runtime_result: dict[str, object], language: str) -> dict[str, object] | None:
    combined = runtime_result.get("combined")
    if combined is None or combined.get("geojson") is None:
        return None
    return combined_overlay_spec(ui_text("combined_overlay_name", language), combined["geojson"], combined.get("semantics"))


def _group_summary_frame(selected_by_group: dict[str, list[str]], runtime_result: dict[str, object], language: str) -> pd.DataFrame:
    _, layers, _ = load_registry()
    rows: list[dict[str, object]] = []
    for group in ordered_groups():
        selected_layer_ids = selected_by_group.get(group.id, [])
        selected_labels = [layer_label(layers[layer_id], language, layers[layer_id].label) for layer_id in selected_layer_ids]
        runtime_group = runtime_result["groups"].get(group.id)
        land_share = None
        if runtime_group and runtime_group.get("land_share_pct") is not None:
            land_share = f"{float(runtime_group['land_share_pct']):.1f}%"
        rows.append(
            {
                ui_text("summary_group", language): group_label(group, language, group.label),
                ui_text("summary_type", language): analysis_kind_label(group.analysis_kind, language),
                ui_text("summary_active", language): bool(selected_layer_ids),
                ui_text("summary_sources", language): ", ".join(selected_labels) if selected_labels else ui_text("none", language),
                ui_text("summary_analysis_m", language): int(st.session_state[_state_key("analysis", group.id)]),
                ui_text("summary_blend", language): f"{int(st.session_state[_state_key('blend', group.id)])}%",
                ui_text("summary_land_share", language): land_share,
                ui_text("summary_role", language): role_label(runtime_group.get("role") if runtime_group else None, language),
            }
        )
    return pd.DataFrame(rows)


def _map_legend(language: str) -> None:
    groups, _, _ = load_registry()
    st.caption(ui_text("map_reading_guide", language))
    st.caption(ui_text("map_guide_source", language))
    st.caption(ui_text("map_guide_group", language))
    st.caption(ui_text("map_guide_combined", language))
    st.caption(ui_text("map_guide_default", language))
    st.caption(ui_text("map_guide_v4", language))
    st.caption(ui_text("map_guide_basemap", language))
    for group in ordered_groups():
        color = groups[group.id].group_color
        swatch = (
            f"<span style='display:inline-block;width:12px;height:12px;border-radius:2px;"
            f"background:rgb({color[0]},{color[1]},{color[2]});margin-right:6px;'></span>"
            f"{group_label(group, language, group.label)}"
        )
        st.markdown(swatch, unsafe_allow_html=True)


st.set_page_config(page_title=PAGE_TITLE, layout="wide")
_init_state()
language = _language_toggle()

st.title(ui_text("app_title", language))
st.caption(ui_text("app_caption", language))

groups, layers, registry_meta = load_registry()
status_df = layer_status_table(registry_meta)
selected_by_group, controls_applied = _build_group_controls(registry_meta, language)
runtime_config_json = _runtime_payload(selected_by_group)

try:
    with st.spinner(ui_text("updating_geometry", language)):
        runtime_result = run_geometry_runtime(runtime_config_json)
except Exception as exc:
    st.error(f"{ui_text('geometry_runtime_failed', language)}: {exc}")
    st.stop()

source_specs = _source_overlay_specs(selected_by_group, registry_meta, language)
group_specs = _group_overlay_specs(runtime_result, language)
combined_spec = _combined_overlay_spec(runtime_result, language)
reference_payload = acceptance_reference_payload(registry_meta, language)
map_html = build_leaflet_html(source_specs, group_specs, combined_spec, reference_payload, language)

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

tab_map, tab_review, tab_data = st.tabs([
    ui_text("tab_prototype", language),
    ui_text("tab_review", language),
    ui_text("tab_data", language),
])

with tab_map:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(ui_text("metric_selectable_source_layers", language), f"{source_ready_count}")
    m2.metric(ui_text("metric_active_source_layers", language), f"{active_source_count}")
    m3.metric(ui_text("metric_active_groups", language), f"{active_group_count}")
    m4.metric(ui_text("metric_combined_acceptance", language), combined_share or ui_text("off", language))

    if controls_applied:
        st.caption(ui_text("controls_applied", language))

    left, right = st.columns([2.3, 1.0], gap="large")
    with left:
        components.html(map_html, height=760)
        st.caption(ui_text("map_panel_caption", language))
    with right:
        st.subheader(ui_text("group_summary", language))
        st.dataframe(_group_summary_frame(selected_by_group, runtime_result, language), use_container_width=True, hide_index=True, height=360)
        _map_legend(language)
        st.caption(f"{ui_text('runtime_cache_key', language)}: {runtime_result['cache_key']}")

with tab_review:
    st.subheader(ui_text("critical_review", language))
    for item in critical_review_items(language):
        st.write(f"- {item}")

    st.subheader(ui_text("hexagon_note", language))
    for item in hexagon_note_items(language):
        st.write(f"- {item}")

with tab_data:
    st.subheader(ui_text("layer_asset_status", language))
    st.dataframe(status_df, use_container_width=True, hide_index=True, height=420)
    st.caption(ui_text("data_status_caption", language))
    if not status_df.empty and (status_df["status"] != "ok").any():
        st.warning(ui_text("data_status_warning", language))
    else:
        st.success(ui_text("data_status_success", language))
