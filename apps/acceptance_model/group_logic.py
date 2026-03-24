from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .layers import GroupSpec, SourceLayerSpec, distance_table_for_layer


@dataclass
class GroupResult:
    group_id: str
    label: str
    analysis_kind: str
    active: bool
    selected_layer_ids: list[str] = field(default_factory=list)
    selected_layer_labels: list[str] = field(default_factory=list)
    missing_layer_ids: list[str] = field(default_factory=list)
    analysis_value_m: int = 0
    blend_value: int = 50
    source_opacity: float = 0.5
    acceptance_opacity: float = 0.5
    map_frame: pd.DataFrame | None = None
    summary: dict[str, Any] = field(default_factory=dict)


def _blend_to_opacity(blend_value: int) -> tuple[float, float]:
    blend = max(0, min(100, int(blend_value))) / 100.0
    return max(0.0, 1.0 - blend), blend


def _group_distance_frame(
    base_hex_df: pd.DataFrame,
    selected_layer_ids: list[str],
    registry_meta: dict[str, Any],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    work = base_hex_df[["hex_id"]].copy()
    distance_cols: list[str] = []
    overlap_cols: list[str] = []
    ready_layers: list[str] = []
    missing_layers: list[str] = []

    for layer_id in selected_layer_ids:
        layer_df = distance_table_for_layer(registry_meta, layer_id)
        if layer_df.empty:
            missing_layers.append(layer_id)
            continue
        distance_col = f"{layer_id}__distance_m"
        overlap_col = f"{layer_id}__intersects"
        renamed = layer_df.rename(columns={"distance_m": distance_col, "intersects": overlap_col})
        work = work.merge(renamed, on="hex_id", how="left")
        distance_cols.append(distance_col)
        overlap_cols.append(overlap_col)
        ready_layers.append(layer_id)

    if not ready_layers:
        return pd.DataFrame(columns=["hex_id", "min_distance_m", "any_intersection"]), ready_layers, missing_layers

    work["min_distance_m"] = work[distance_cols].min(axis=1, skipna=True)
    if overlap_cols:
        work["any_intersection"] = work[overlap_cols].fillna(False).astype(bool).any(axis=1)
    else:
        work["any_intersection"] = False
    work["selected_layer_count"] = len(ready_layers)
    return work, ready_layers, missing_layers


def _distance_conflict_acceptance(
    min_distance_m: pd.Series,
    threshold_m: int,
    any_intersection: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    distance = pd.to_numeric(min_distance_m, errors="coerce")
    if threshold_m <= 0:
        blocked = any_intersection.astype(bool)
        acceptance = (~blocked).astype(float)
        return acceptance, blocked

    ramp_end = max(float(threshold_m * 2), float(threshold_m + 1))
    acceptance = ((distance - threshold_m) / (ramp_end - threshold_m)).clip(lower=0.0, upper=1.0).fillna(0.0)
    acceptance.loc[any_intersection.astype(bool)] = 0.0
    blocked = any_intersection.astype(bool) | (distance <= float(threshold_m))
    return acceptance, blocked


def _proximity_acceptance(
    min_distance_m: pd.Series,
    threshold_m: int,
    any_intersection: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    capped_threshold = max(int(threshold_m), 1)
    distance = pd.to_numeric(min_distance_m, errors="coerce")
    acceptance = (1.0 - (distance / float(capped_threshold))).clip(lower=0.0, upper=1.0).fillna(0.0)
    acceptance.loc[any_intersection.astype(bool)] = 1.0
    blocked = ~any_intersection.astype(bool) & (distance > float(capped_threshold))
    return acceptance, blocked


def _hard_exclusion_acceptance(
    min_distance_m: pd.Series,
    threshold_m: int,
    any_intersection: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    distance = pd.to_numeric(min_distance_m, errors="coerce")
    if threshold_m <= 0:
        blocked = any_intersection.astype(bool)
    else:
        blocked = any_intersection.astype(bool) | (distance <= float(threshold_m))
    acceptance = (~blocked).astype(float)
    return acceptance, blocked


def create_group_acceptance_layer(
    group_spec: GroupSpec,
    base_hex_df: pd.DataFrame,
    selected_layer_ids: list[str],
    layer_specs: dict[str, SourceLayerSpec],
    registry_meta: dict[str, Any],
    analysis_value_m: int,
    blend_value: int,
) -> GroupResult:
    source_opacity, acceptance_opacity = _blend_to_opacity(blend_value)
    selected_labels = [layer_specs[layer_id].label for layer_id in selected_layer_ids if layer_id in layer_specs]
    result = GroupResult(
        group_id=group_spec.id,
        label=group_spec.label,
        analysis_kind=group_spec.analysis_kind,
        active=bool(selected_layer_ids),
        selected_layer_ids=list(selected_layer_ids),
        selected_layer_labels=selected_labels,
        analysis_value_m=int(analysis_value_m),
        blend_value=int(blend_value),
        source_opacity=source_opacity,
        acceptance_opacity=acceptance_opacity,
    )
    if not result.active:
        return result

    distance_frame, ready_layers, missing_layers = _group_distance_frame(
        base_hex_df=base_hex_df,
        selected_layer_ids=selected_layer_ids,
        registry_meta=registry_meta,
    )
    result.missing_layer_ids = missing_layers
    if distance_frame.empty or not ready_layers:
        result.summary = {
            "status": "missing_assets",
            "selected_sources": ", ".join(selected_labels) if selected_labels else "None",
        }
        return result

    if group_spec.analysis_kind == "distance_conflict":
        acceptance, blocked = _distance_conflict_acceptance(distance_frame["min_distance_m"], analysis_value_m, distance_frame["any_intersection"])
    elif group_spec.analysis_kind == "proximity_feasibility":
        acceptance, blocked = _proximity_acceptance(distance_frame["min_distance_m"], analysis_value_m, distance_frame["any_intersection"])
    else:
        acceptance, blocked = _hard_exclusion_acceptance(distance_frame["min_distance_m"], analysis_value_m, distance_frame["any_intersection"])

    map_frame = base_hex_df[["hex_id", "polygon", "lat", "lon"]].merge(
        distance_frame[["hex_id", "min_distance_m", "any_intersection"]],
        on="hex_id",
        how="left",
    )
    map_frame["group_id"] = group_spec.id
    map_frame["group_label"] = group_spec.label
    map_frame["selected_sources"] = ", ".join(result.selected_layer_labels)
    map_frame["group_acceptance"] = acceptance.fillna(0.0)
    map_frame["group_conflict"] = (1.0 - map_frame["group_acceptance"]).clip(lower=0.0, upper=1.0)
    map_frame["group_blocked"] = blocked.astype(int)
    map_frame["tooltip_title"] = f"Group layer: {group_spec.label}"
    map_frame["tooltip_body"] = (
        "Selected sources: "
        + map_frame["selected_sources"].astype(str)
        + "<br/>Analysis type: "
        + group_spec.analysis_kind
        + "<br/>Threshold: "
        + str(int(analysis_value_m))
        + " m"
        + "<br/>Nearest source: "
        + map_frame["min_distance_m"].round(1).astype(str)
        + " m"
        + "<br/>Acceptance: "
        + map_frame["group_acceptance"].round(2).astype(str)
        + "<br/>Blocked: "
        + map_frame["group_blocked"].astype(str)
    )

    result.map_frame = map_frame
    result.summary = {
        "status": "ok",
        "selected_sources": ", ".join(result.selected_layer_labels),
        "source_count": len(ready_layers),
        "missing_source_count": len(missing_layers),
        "blocked_share": float(blocked.mean()),
        "mean_acceptance": float(map_frame["group_acceptance"].mean()),
    }
    return result


def process_settlement_group(
    group_spec: GroupSpec,
    base_hex_df: pd.DataFrame,
    selected_layer_ids: list[str],
    layer_specs: dict[str, SourceLayerSpec],
    registry_meta: dict[str, Any],
    analysis_value_m: int,
    blend_value: int,
) -> GroupResult:
    return create_group_acceptance_layer(group_spec, base_hex_df, selected_layer_ids, layer_specs, registry_meta, analysis_value_m, blend_value)


def process_transport_group(
    group_spec: GroupSpec,
    base_hex_df: pd.DataFrame,
    selected_layer_ids: list[str],
    layer_specs: dict[str, SourceLayerSpec],
    registry_meta: dict[str, Any],
    analysis_value_m: int,
    blend_value: int,
) -> GroupResult:
    return create_group_acceptance_layer(group_spec, base_hex_df, selected_layer_ids, layer_specs, registry_meta, analysis_value_m, blend_value)


def process_electrical_infrastructure_group(
    group_spec: GroupSpec,
    base_hex_df: pd.DataFrame,
    selected_layer_ids: list[str],
    layer_specs: dict[str, SourceLayerSpec],
    registry_meta: dict[str, Any],
    analysis_value_m: int,
    blend_value: int,
) -> GroupResult:
    return create_group_acceptance_layer(group_spec, base_hex_df, selected_layer_ids, layer_specs, registry_meta, analysis_value_m, blend_value)


def create_combined_acceptance_layer(base_hex_df: pd.DataFrame, group_results: list[GroupResult]) -> pd.DataFrame | None:
    active_results = [result for result in group_results if result.active and result.map_frame is not None]
    if len(active_results) <= 1:
        return None

    combined = base_hex_df[["hex_id", "polygon", "lat", "lon"]].copy()
    acceptance_cols: list[str] = []
    labels: list[str] = []
    for result in active_results:
        col_name = f"{result.group_id}__acceptance"
        acceptance_cols.append(col_name)
        labels.append(result.label)
        combined = combined.merge(
            result.map_frame[["hex_id", "group_acceptance"]].rename(columns={"group_acceptance": col_name}),
            on="hex_id",
            how="left",
        )

    combined["combined_acceptance"] = combined[acceptance_cols].min(axis=1, skipna=True).fillna(0.0)
    combined["combined_conflict"] = (1.0 - combined["combined_acceptance"]).clip(lower=0.0, upper=1.0)
    combined["active_groups"] = ", ".join(labels)
    combined["tooltip_title"] = "Combined acceptance layer"
    combined["tooltip_body"] = "Active groups: " + combined["active_groups"].astype(str) + "<br/>Combined acceptance: " + combined["combined_acceptance"].round(2).astype(str)
    return combined


def aggregate_to_hexagons_placeholder(_: Any = None) -> dict[str, str]:
    return {
        "status": "placeholder",
        "message": "The prototype already consumes per-layer distance tables that were exported from source geometries onto the existing H3 hex grid. A later production version can replace this with on-demand geometry-first buffering and post-hoc area-weighted hex aggregation.",
    }
