from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

try:
    import h3
except Exception:  # pragma: no cover
    h3 = None


APP_TITLE = "Bornholm Vindacceptans Explorer"
DATA_RELATIVE_PATH = (
    "docs/geocontext/acceptance_framework/data/"
    "bornholm_vindacceptans_stage1_v3_2_res9/"
    "bornholm_vindacceptans_stage1_v3_2_res9_hex.gpkg"
)
DATA_LAYER = "bornholm_vindacceptans_stage1_v3_2_res9"

CLASS_COLORS = {
    "Exkluderad": [140, 140, 140, 180],
    "Lag": [241, 232, 166, 180],
    "Medel": [240, 179, 91, 185],
    "Hog": [125, 187, 125, 190],
    "Mycket hog": [44, 122, 75, 210],
}

BASELINE_CLASS_COLS = {
    "balanced": "acceptance_class_balanced",
    "strict": "acceptance_class_strict",
    "tech_prioritized": "acceptance_class_tech_prioritized",
}

LAYER_META = {
    "score_hv_line": {"label": "Hogspanningsledning", "group": "El och teknik"},
    "score_substation": {"label": "Elstation", "group": "El och teknik"},
    "score_cable": {"label": "Kabel", "group": "El och teknik"},
    "score_existing_wind": {"label": "Befintlig vindkraft", "group": "El och teknik"},
    "score_settlement_clearance": {"label": "Avstand till bosattning", "group": "Bosattning och kultur"},
    "score_culture_clearance": {"label": "Avstand till kulturmiljo", "group": "Bosattning och kultur"},
    "score_protected_edge_clearance": {"label": "Avstand till skyddad natur", "group": "Skydd och natur"},
    "score_aviation_bird_clearance": {"label": "Avstand till fagelkollisionszon", "group": "Skydd och natur"},
    "score_landscape_cluster": {"label": "Landskapskluster", "group": "Landskap"},
    "score_landscape_plateau": {"label": "Hog jordbruksplata", "group": "Landskap"},
    "score_landscape_open_terrain": {"label": "Oppet terrain", "group": "Landskap"},
}

LAYER_GROUPS = [
    "El och teknik",
    "Bosattning och kultur",
    "Skydd och natur",
    "Landskap",
]

PRESETS = {
    "balanced": {
        "label": "Balanserad",
        "hard": {
            "settlement_mode": "Hard stop",
            "settlement_threshold_m": 800,
            "culture_mode": "Hard stop",
            "protected_mode": "Hard stop",
            "military_mode": "Hard stop",
            "aviation_approach_mode": "Hard stop",
            "aviation_bird_mode": "Soft",
            "aviation_bird_threshold_m": 0,
            "strand_mode": "Hard stop",
        },
        "weights": {
            "score_hv_line": 18,
            "score_substation": 12,
            "score_cable": 8,
            "score_existing_wind": 12,
            "score_settlement_clearance": 18,
            "score_culture_clearance": 8,
            "score_protected_edge_clearance": 12,
            "score_aviation_bird_clearance": 8,
            "score_landscape_cluster": 14,
            "score_landscape_plateau": 6,
            "score_landscape_open_terrain": 4,
        },
    },
    "strict": {
        "label": "Strikt",
        "hard": {
            "settlement_mode": "Hard stop",
            "settlement_threshold_m": 1000,
            "culture_mode": "Hard stop",
            "protected_mode": "Hard stop",
            "military_mode": "Hard stop",
            "aviation_approach_mode": "Hard stop",
            "aviation_bird_mode": "Hard stop",
            "aviation_bird_threshold_m": 0,
            "strand_mode": "Hard stop",
        },
        "weights": {
            "score_hv_line": 12,
            "score_substation": 10,
            "score_cable": 6,
            "score_existing_wind": 8,
            "score_settlement_clearance": 22,
            "score_culture_clearance": 12,
            "score_protected_edge_clearance": 14,
            "score_aviation_bird_clearance": 10,
            "score_landscape_cluster": 4,
            "score_landscape_plateau": 1,
            "score_landscape_open_terrain": 1,
        },
    },
    "tech_prioritized": {
        "label": "Teknikprioriterad",
        "hard": {
            "settlement_mode": "Hard stop",
            "settlement_threshold_m": 800,
            "culture_mode": "Ignore",
            "protected_mode": "Hard stop",
            "military_mode": "Hard stop",
            "aviation_approach_mode": "Hard stop",
            "aviation_bird_mode": "Ignore",
            "aviation_bird_threshold_m": 0,
            "strand_mode": "Hard stop",
        },
        "weights": {
            "score_hv_line": 24,
            "score_substation": 18,
            "score_cable": 10,
            "score_existing_wind": 8,
            "score_settlement_clearance": 12,
            "score_culture_clearance": 4,
            "score_protected_edge_clearance": 8,
            "score_aviation_bird_clearance": 4,
            "score_landscape_cluster": 8,
            "score_landscape_plateau": 2,
            "score_landscape_open_terrain": 2,
        },
    },
}


@st.cache_data(show_spinner=False)
def load_acceptance_table(gpkg_path: str, layer_name: str) -> pd.DataFrame:
    con = sqlite3.connect(gpkg_path)
    try:
        query = f'SELECT * FROM "{layer_name}"'
        df = pd.read_sql_query(query, con)
    finally:
        con.close()
    if "geom" in df.columns:
        df = df.drop(columns=["geom"])
    return df


def _hex_polygon(hex_id: str):
    if h3 is None:
        return None
    try:
        boundary = h3.cell_to_boundary(hex_id)
        return [[lng, lat] for lat, lng in boundary]
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def build_map_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    lat = []
    lon = []
    polygon = []
    for hex_id in out["hex_id"].astype(str):
        try:
            y, x = h3.cell_to_latlng(hex_id)
            lat.append(y)
            lon.append(x)
            polygon.append(_hex_polygon(hex_id))
        except Exception:
            lat.append(np.nan)
            lon.append(np.nan)
            polygon.append(None)
    out["lat"] = lat
    out["lon"] = lon
    out["polygon"] = polygon
    return out.dropna(subset=["lat", "lon", "polygon"]).copy()


def _init_state_from_preset(preset_key: str) -> None:
    preset = PRESETS[preset_key]
    st.session_state["preset_key"] = preset_key
    for key, value in preset["hard"].items():
        st.session_state[key] = value
    for key, value in preset["weights"].items():
        st.session_state[key] = value


def ensure_state() -> None:
    if "preset_key" not in st.session_state:
        _init_state_from_preset("balanced")
    if "active_layers" not in st.session_state:
        st.session_state["active_layers"] = list(LAYER_META.keys())


def apply_preset(preset_key: str) -> None:
    _init_state_from_preset(preset_key)


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = float(sum(max(0.0, float(v)) for v in weights.values()))
    if total <= 0:
        total = 1.0
    return {k: max(0.0, float(v)) / total for k, v in weights.items()}


def export_current_config(active_layers: list[str]) -> str:
    payload = {
        "preset_key": st.session_state["preset_key"],
        "hard": {
            "settlement_mode": st.session_state["settlement_mode"],
            "settlement_threshold_m": st.session_state["settlement_threshold_m"],
            "culture_mode": st.session_state["culture_mode"],
            "protected_mode": st.session_state["protected_mode"],
            "military_mode": st.session_state["military_mode"],
            "aviation_approach_mode": st.session_state["aviation_approach_mode"],
            "aviation_bird_mode": st.session_state["aviation_bird_mode"],
            "aviation_bird_threshold_m": st.session_state["aviation_bird_threshold_m"],
            "strand_mode": st.session_state["strand_mode"],
        },
        "active_layers": active_layers,
        "weights": {key: st.session_state[key] for key in LAYER_META},
    }
    return json.dumps(payload, indent=2)


def load_config_from_upload(uploaded_file) -> None:
    payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
    if "preset_key" in payload and payload["preset_key"] in PRESETS:
        st.session_state["preset_key"] = payload["preset_key"]
    for key, value in payload.get("hard", {}).items():
        st.session_state[key] = value
    for key, value in payload.get("weights", {}).items():
        if key in LAYER_META:
            st.session_state[key] = value
    if "active_layers" in payload:
        st.session_state["active_layers"] = [x for x in payload["active_layers"] if x in LAYER_META]


def compute_hard_exclusions(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    reasons = []

    settlement_threshold = float(st.session_state["settlement_threshold_m"])
    settlement_hard = (
        st.session_state["settlement_mode"] == "Hard stop"
    ) & (pd.to_numeric(df["dist_to_settlement_hard_m"], errors="coerce") <= settlement_threshold)
    culture_hard = (st.session_state["culture_mode"] == "Hard stop") & df["hard_exclusion_culture"].astype(bool)
    protected_hard = (st.session_state["protected_mode"] == "Hard stop") & df["hard_exclusion_protected"].astype(bool)
    military_hard = (st.session_state["military_mode"] == "Hard stop") & df["hard_exclusion_military"].astype(bool)
    aviation_approach_hard = (
        (st.session_state["aviation_approach_mode"] == "Hard stop")
        & df["hard_exclusion_aviation_approach"].astype(bool)
    )
    strand_hard = (st.session_state["strand_mode"] == "Hard stop") & df["hard_exclusion_strand"].astype(bool)

    bird_mode = st.session_state["aviation_bird_mode"]
    if bird_mode == "Hard stop":
        bird_threshold = float(st.session_state["aviation_bird_threshold_m"])
        if bird_threshold > 0:
            bird_hard = pd.to_numeric(df["dist_to_aviation_bird_m"], errors="coerce") <= bird_threshold
        else:
            bird_hard = df["hard_exclusion_aviation_bird"].astype(bool)
    else:
        bird_hard = pd.Series(False, index=df.index)

    exclusion_frame = pd.DataFrame(
        {
            "Bosattning": settlement_hard,
            "Kulturmiljo": culture_hard,
            "Skyddad natur": protected_hard,
            "Militar": military_hard,
            "Inflygning": aviation_approach_hard,
            "Fagelkollision": bird_hard,
            "Strandskydd": strand_hard,
        }
    )

    for _, row in exclusion_frame.iterrows():
        active = [name for name, flag in row.items() if bool(flag)]
        reasons.append("; ".join(active) if active else "Ingen hard exkludering")

    hard_count = exclusion_frame.sum(axis=1).astype(int)
    return hard_count, pd.Series(reasons, index=df.index)


def compute_compound_score(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    normalized = normalize_weights(weights)
    score = np.zeros(len(df), dtype=float)
    for col, weight in normalized.items():
        score += pd.to_numeric(df[col], errors="coerce").fillna(0).to_numpy() * weight
    return pd.Series(score * 100, index=df.index)


def classify_score(score: pd.Series, allowed: pd.Series) -> pd.Series:
    labels = pd.Series("Exkluderad", index=score.index)
    labels.loc[allowed & (score < 30)] = "Lag"
    labels.loc[allowed & (score >= 30) & (score < 50)] = "Medel"
    labels.loc[allowed & (score >= 50) & (score < 70)] = "Hog"
    labels.loc[allowed & (score >= 70)] = "Mycket hog"
    return labels


def class_to_color(class_series: pd.Series) -> list[list[int]]:
    return [
        CLASS_COLORS.get(label, [180, 180, 180, 140])
        for label in class_series.fillna("Exkluderad").astype(str)
    ]


def numeric_gradient(series: pd.Series) -> list[list[int]]:
    x = pd.to_numeric(series, errors="coerce").fillna(0)
    lo = float(x.min())
    hi = float(x.max())
    if hi <= lo:
        hi = lo + 1
    scaled = (x - lo) / (hi - lo)
    colors = []
    for value in scaled:
        r = int(239 - 194 * value)
        g = int(232 - 110 * value)
        b = int(216 - 141 * value)
        colors.append([r, g, b, 195])
    return colors


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption(
    "Interaktiv acceptansapp ovanpa landskapsanalysen. Valj vilka lager som ar hard stop, "
    "vilka som bara ska paverka score, och bygg en egen sammansatt acceptansyta."
)

repo_root = Path(__file__).resolve().parent.parent
data_path = repo_root / DATA_RELATIVE_PATH

if h3 is None:
    st.error("Python-paketet `h3` saknas. Installera dependencies och starta om appen.")
    st.stop()

ensure_state()

try:
    base_df = load_acceptance_table(str(data_path), DATA_LAYER)
except Exception as exc:
    st.error(f"Kunde inte lasa acceptance-data: {exc}")
    st.stop()

map_df = build_map_frame(base_df)
if map_df.empty:
    st.error("Acceptance-data laddades men inga kartbara hexagoner hittades.")
    st.stop()

st.sidebar.header("Scenario")
preset_choice = st.sidebar.selectbox(
    "Startlogik",
    options=list(PRESETS.keys()),
    format_func=lambda x: PRESETS[x]["label"],
    index=list(PRESETS.keys()).index(st.session_state["preset_key"]),
)
if preset_choice != st.session_state["preset_key"]:
    apply_preset(preset_choice)

uploaded_config = st.sidebar.file_uploader("Ladda scenario JSON", type=["json"])
if uploaded_config is not None:
    load_config_from_upload(uploaded_config)

st.sidebar.download_button(
    "Spara current scenario som JSON",
    data=export_current_config(st.session_state.get("active_layers", list(LAYER_META.keys()))),
    file_name="bornholm_acceptance_scenario.json",
    mime="application/json",
)

st.sidebar.header("Hard stop")
st.sidebar.select_slider("Bosattning", options=["Ignore", "Soft", "Hard stop"], key="settlement_mode")
st.sidebar.slider("Bosattningsgrans (m)", 0, 2000, step=50, key="settlement_threshold_m")
st.sidebar.select_slider("Kulturmiljo", options=["Ignore", "Soft", "Hard stop"], key="culture_mode")
st.sidebar.select_slider("Skyddad natur", options=["Ignore", "Hard stop"], key="protected_mode")
st.sidebar.select_slider("Militar", options=["Ignore", "Hard stop"], key="military_mode")
st.sidebar.select_slider("Inflygningszon", options=["Ignore", "Hard stop"], key="aviation_approach_mode")
st.sidebar.select_slider("Fagelkollisionszon", options=["Ignore", "Soft", "Hard stop"], key="aviation_bird_mode")
st.sidebar.slider("Fagelkollisionsgrans (m, 0 = overlap)", 0, 4000, step=100, key="aviation_bird_threshold_m")
st.sidebar.select_slider("Strandskydd", options=["Ignore", "Hard stop"], key="strand_mode")

st.sidebar.header("Compound layer")
active_layers = st.sidebar.multiselect(
    "Aktiva lager i score",
    options=list(LAYER_META.keys()),
    default=st.session_state.get("active_layers", list(LAYER_META.keys())),
    format_func=lambda x: f"{LAYER_META[x]['group']} | {LAYER_META[x]['label']}",
    key="active_layers",
)

weights: dict[str, float] = {}
for group_name in LAYER_GROUPS:
    group_layers = [key for key, meta in LAYER_META.items() if meta["group"] == group_name and key in active_layers]
    if not group_layers:
        continue
    with st.sidebar.expander(group_name, expanded=(group_name == "El och teknik")):
        for layer_key in group_layers:
            weights[layer_key] = float(
                st.slider(
                    f"{LAYER_META[layer_key]['label']} vikt",
                    min_value=0,
                    max_value=100,
                    step=1,
                    key=layer_key,
                )
            )

if not active_layers:
    st.warning("Valj minst ett lager i compound score.")
    st.stop()

work = map_df.copy()
hard_count, hard_reason = compute_hard_exclusions(work)
allowed = hard_count == 0
compound_score = compute_compound_score(work, weights)
acceptance_class = classify_score(compound_score, allowed)

work["user_hard_exclusion_count"] = hard_count
work["user_exclusion_reason"] = hard_reason
work["user_allowed"] = allowed
work["user_acceptance_score"] = compound_score.round(1)
work["user_acceptance_class"] = acceptance_class

map_mode = st.sidebar.radio(
    "Kartlager",
    options=["User class", "User score", "Balanced baseline", "Strict baseline", "Tech baseline"],
    index=0,
)
show_only_allowed = st.sidebar.checkbox("Visa bara tillatna hex", value=False)

if map_mode == "User class":
    work["fill_color"] = class_to_color(work["user_acceptance_class"])
elif map_mode == "User score":
    work["fill_color"] = numeric_gradient(work["user_acceptance_score"])
elif map_mode == "Balanced baseline":
    work["fill_color"] = class_to_color(work[BASELINE_CLASS_COLS["balanced"]])
elif map_mode == "Strict baseline":
    work["fill_color"] = class_to_color(work[BASELINE_CLASS_COLS["strict"]])
else:
    work["fill_color"] = class_to_color(work[BASELINE_CLASS_COLS["tech_prioritized"]])

if show_only_allowed:
    display_df = work[work["user_allowed"]].copy()
else:
    display_df = work.copy()

if display_df.empty:
    st.warning("Inga hexagoner aterstar med nuvarande urval.")
    st.stop()

normalized_weights = normalize_weights(weights)
weights_table = pd.DataFrame(
    {
        "Grupp": [LAYER_META[k]["group"] for k in normalized_weights.keys()],
        "Lager": [LAYER_META[k]["label"] for k in normalized_weights.keys()],
        "Relativ vikt": [round(v * 100, 1) for v in normalized_weights.values()],
    }
).sort_values(["Grupp", "Relativ vikt"], ascending=[True, False])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Hex totalt", f"{len(work)}")
c2.metric("Tillatna hex", f"{int(work['user_allowed'].sum())}")
c3.metric("Tillaten andel", f"{(100 * float(work['user_allowed'].mean())):.1f}%")
c4.metric(
    "Median score",
    f"{float(work.loc[work['user_allowed'], 'user_acceptance_score'].median()):.1f}"
    if work["user_allowed"].any()
    else "n/a",
)

left, right = st.columns([1.15, 2.15], gap="large")

with left:
    st.subheader("Scenario mot baseline")
    baseline_compare = pd.DataFrame(
        {
            "Scenario": ["Strikt", "Balanserad", "Teknikprioriterad", "User"],
            "Allowed hex": [
                int(pd.to_numeric(work["allowed_for_wind_strict"], errors="coerce").fillna(0).astype(bool).sum()),
                int(pd.to_numeric(work["allowed_for_wind_balanced"], errors="coerce").fillna(0).astype(bool).sum()),
                int(pd.to_numeric(work["allowed_for_wind_tech_prioritized"], errors="coerce").fillna(0).astype(bool).sum()),
                int(work["user_allowed"].sum()),
            ],
            "Median score": [
                round(float(pd.to_numeric(work["acceptance_score_strict"], errors="coerce")[work["allowed_for_wind_strict"]].median()), 1),
                round(float(pd.to_numeric(work["acceptance_score_balanced"], errors="coerce")[work["allowed_for_wind_balanced"]].median()), 1),
                round(float(pd.to_numeric(work["acceptance_score_tech_prioritized"], errors="coerce")[work["allowed_for_wind_tech_prioritized"]].median()), 1),
                round(float(work.loc[work["user_allowed"], "user_acceptance_score"].median()), 1) if work["user_allowed"].any() else np.nan,
            ],
        }
    )
    st.dataframe(baseline_compare, use_container_width=True, hide_index=True)

    st.subheader("Aktiva vikter")
    st.dataframe(weights_table, use_container_width=True, hide_index=True, height=280)

    st.subheader("Hard stop profil")
    hard_profile = pd.DataFrame(
        {
            "Kriterium": [
                "Bosattning",
                "Kulturmiljo",
                "Skyddad natur",
                "Militar",
                "Inflygningszon",
                "Fagelkollisionszon",
                "Strandskydd",
            ],
            "Val": [
                st.session_state["settlement_mode"],
                st.session_state["culture_mode"],
                st.session_state["protected_mode"],
                st.session_state["military_mode"],
                st.session_state["aviation_approach_mode"],
                st.session_state["aviation_bird_mode"],
                st.session_state["strand_mode"],
            ],
        }
    )
    st.dataframe(hard_profile, use_container_width=True, hide_index=True)

    st.subheader("Topprankade tillatna hex")
    top_table = (
        work[work["user_allowed"]]
        .sort_values("user_acceptance_score", ascending=False)
        .loc[
            :,
            [
                "hex_id",
                "class_km",
                "user_acceptance_score",
                "score_grid_proximity",
                "score_clearance",
                "score_landscape",
                "user_exclusion_reason",
            ],
        ]
        .head(150)
        .rename(
            columns={
                "class_km": "Kluster",
                "user_acceptance_score": "Score",
                "score_grid_proximity": "Grid",
                "score_clearance": "Clearance",
                "score_landscape": "Landskap",
                "user_exclusion_reason": "Hard stop",
            }
        )
    )
    st.dataframe(top_table.round(3), use_container_width=True, height=350)

with right:
    st.subheader("Karta")
    st.caption(f"Aktiv visning: {map_mode}")
    tooltip = {
        "html": (
            "<b>hex_id:</b> {hex_id}<br/>"
            "<b>Kluster:</b> {class_km}<br/>"
            "<b>User class:</b> {user_acceptance_class}<br/>"
            "<b>User score:</b> {user_acceptance_score}<br/>"
            "<b>Hard stop:</b> {user_exclusion_reason}<br/>"
            "<b>Balanced:</b> {acceptance_score_balanced}<br/>"
            "<b>Strict:</b> {acceptance_score_strict}<br/>"
            "<b>Tech:</b> {acceptance_score_tech_prioritized}"
        ),
        "style": {"backgroundColor": "white", "color": "black"},
    }
    layer = pdk.Layer(
        "PolygonLayer",
        data=display_df,
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color=[80, 80, 80, 90],
        line_width_min_pixels=0.5,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )
    center_lat = float(display_df["lat"].median())
    center_lon = float(display_df["lon"].median())
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=9, pitch=0),
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    )
    st.pydeck_chart(deck, use_container_width=True)

st.subheader("Download")
download_cols = [
    "hex_id",
    "class_km",
    "user_allowed",
    "user_acceptance_score",
    "user_acceptance_class",
    "user_exclusion_reason",
    "score_grid_proximity",
    "score_clearance",
    "score_landscape",
] + active_layers
download_df = work[download_cols].sort_values("user_acceptance_score", ascending=False)
st.download_button(
    "Ladda ner current user scenario som CSV",
    data=download_df.to_csv(index=False).encode("utf-8"),
    file_name="bornholm_acceptance_user_scenario.csv",
    mime="text/csv",
)
