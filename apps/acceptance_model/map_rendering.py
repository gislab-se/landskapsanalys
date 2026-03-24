from __future__ import annotations

from typing import Any

import pandas as pd
import pydeck as pdk

from .group_logic import GroupResult
from .layers import SourceLayerSpec


MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
COMBINED_COLOR = (35, 77, 112)


def _hex_outline_layer(hex_df: pd.DataFrame) -> pdk.Layer:
    return pdk.Layer(
        "PolygonLayer",
        data=hex_df,
        get_polygon="polygon",
        get_fill_color=[255, 255, 255, 0],
        get_line_color=[110, 110, 110, 40],
        line_width_min_pixels=0.35,
        stroked=True,
        filled=True,
        pickable=False,
    )


def _source_geojson_layer(
    geojson: dict[str, Any],
    layer_spec: SourceLayerSpec,
    geometry_family: str,
    opacity: float,
) -> pdk.Layer | None:
    if not geojson or opacity <= 0:
        return None

    color = list(layer_spec.source_color)
    fill_color = color + [55]
    line_color = color + [215]
    filled = geometry_family != "line"
    stroked = geometry_family != "point"
    return pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        opacity=float(opacity),
        filled=filled,
        stroked=stroked,
        pickable=True,
        auto_highlight=True,
        get_fill_color=fill_color,
        get_line_color=line_color,
        line_width_min_pixels=1.6,
        point_radius_min_pixels=3,
        point_radius_scale=1,
        get_point_radius=int(layer_spec.point_radius),
    )


def _group_hex_layer(group_result: GroupResult, group_color: tuple[int, int, int]) -> pdk.Layer | None:
    if group_result.map_frame is None or group_result.acceptance_opacity <= 0:
        return None

    df = group_result.map_frame.copy()
    alpha_scale = max(0.0, min(1.0, group_result.acceptance_opacity))
    fill_colors: list[list[int]] = []
    line_colors: list[list[int]] = []
    for conflict in df["group_conflict"].fillna(0.0):
        alpha = int(round(float(conflict) * 210 * alpha_scale))
        fill_colors.append([group_color[0], group_color[1], group_color[2], alpha])
        line_colors.append([group_color[0], group_color[1], group_color[2], min(alpha + 25, 230)])
    df["fill_color"] = fill_colors
    df["line_color"] = line_colors
    return pdk.Layer(
        "PolygonLayer",
        data=df,
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color="line_color",
        line_width_min_pixels=0.55,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )


def _combined_hex_layer(combined_df: pd.DataFrame | None) -> pdk.Layer | None:
    if combined_df is None or combined_df.empty:
        return None

    df = combined_df.copy()
    fill_colors: list[list[int]] = []
    for conflict in df["combined_conflict"].fillna(0.0):
        alpha = int(round(float(conflict) * 28))
        fill_colors.append([COMBINED_COLOR[0], COMBINED_COLOR[1], COMBINED_COLOR[2], alpha])
    df["fill_color"] = fill_colors
    return pdk.Layer(
        "PolygonLayer",
        data=df,
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color=[COMBINED_COLOR[0], COMBINED_COLOR[1], COMBINED_COLOR[2], 40],
        line_width_min_pixels=0.4,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )


def build_deck(
    hex_df: pd.DataFrame,
    source_layers: list[tuple[dict[str, Any], SourceLayerSpec, str, float]],
    group_layers: list[tuple[GroupResult, tuple[int, int, int]]],
    combined_df: pd.DataFrame | None,
) -> pdk.Deck:
    layers: list[pdk.Layer] = [_hex_outline_layer(hex_df)]

    for geojson, layer_spec, geometry_family, opacity in source_layers:
        source_layer = _source_geojson_layer(geojson, layer_spec, geometry_family, opacity)
        if source_layer is not None:
            layers.append(source_layer)

    for group_result, group_color in group_layers:
        group_layer = _group_hex_layer(group_result, group_color)
        if group_layer is not None:
            layers.append(group_layer)

    combined_layer = _combined_hex_layer(combined_df)
    if combined_layer is not None:
        layers.append(combined_layer)

    center_lat = float(hex_df["lat"].median())
    center_lon = float(hex_df["lon"].median())
    tooltip = {
        "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
        "style": {"backgroundColor": "white", "color": "black"},
    }
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=9.1, pitch=0),
        tooltip=tooltip,
        map_style=MAP_STYLE,
    )
