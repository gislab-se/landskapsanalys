from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

try:
    import h3
except Exception:  # pragma: no cover
    h3 = None


CLUSTER_COLORS = {
    0: [166, 219, 210, 90],
    1: [253, 174, 97, 90],
    2: [255, 255, 191, 90],
    3: [231, 212, 232, 90],
    4: [215, 25, 28, 90],
    5: [255, 237, 111, 90],
    6: [171, 217, 233, 90],
    7: [197, 176, 213, 90],
}


@st.cache_data(show_spinner=False)
def load_gc4(repo_root: Path) -> pd.DataFrame:
    pts = pd.read_csv(repo_root / "data" / "gc4" / "bornholm_points_with_context_gc4.csv")
    scores = pd.read_csv(repo_root / "data" / "gc4" / "bornholm_r8_factor_scores_gc4.csv")
    cols = ["hex_id", "class_km", "F1", "F2", "F3", "F4", "F5"]
    merged = pts.merge(scores[cols], on="hex_id", how="left")
    merged["class_km"] = pd.to_numeric(merged["class_km"], errors="coerce").fillna(-1).astype(int)
    return merged


@st.cache_data(show_spinner=False)
def load_layer_dictionary(repo_root: Path) -> pd.DataFrame | None:
    path = repo_root / "docs" / "geocontext" / "bornholm_37_lager_svenska.csv"
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_validation_assets(repo_root: Path) -> tuple[pd.DataFrame, int]:
    pdf_dir = repo_root / "data" / "raw" / "lablab" / "SpeedLocal" / "Bornholm" / "PDF GIS"
    img_dir = repo_root / "data" / "raw" / "lablab" / "SpeedLocal" / "Bornholm" / "Bilder G-maps"

    rows: list[dict[str, object]] = []
    if pdf_dir.exists():
        for p in sorted(pdf_dir.glob("*.pdf")):
            rows.append(
                {
                    "source_group": "PDF GIS",
                    "file_name": p.name,
                    "size_mb": round(float(p.stat().st_size) / (1024 * 1024), 2),
                    "modified": p.stat().st_mtime,
                }
            )
    image_count = len(list(img_dir.glob("*"))) if img_dir.exists() else 0
    return pd.DataFrame(rows), image_count


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
    out = df[["hex_id", "class_km", "F1", "F2", "F3", "F4", "F5"]].copy()
    if h3 is None:
        out["lat"] = np.nan
        out["lon"] = np.nan
        out["polygon"] = None
        out["hex_area_km2"] = np.nan
        return out

    lat = []
    lon = []
    polygon = []
    area = []
    for hex_id in out["hex_id"].astype(str):
        try:
            y, x = h3.cell_to_latlng(hex_id)
            lat.append(y)
            lon.append(x)
            polygon.append(_hex_polygon(hex_id))
            area.append(float(h3.cell_area(hex_id, unit="km^2")))
        except Exception:
            lat.append(np.nan)
            lon.append(np.nan)
            polygon.append(None)
            area.append(np.nan)

    out["lat"] = lat
    out["lon"] = lon
    out["polygon"] = polygon
    out["hex_area_km2"] = area
    return out


def _norm(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    lo = series.min()
    hi = series.max()
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - lo) / (hi - lo)


def composite_score(df: pd.DataFrame, w: dict[str, float]) -> pd.Series:
    score = np.zeros(len(df), dtype=float)
    total_weight = float(sum(max(0.0, float(v)) for v in w.values()))
    if total_weight <= 0:
        total_weight = 1.0
    for key in ["F1", "F2", "F3", "F4", "F5"]:
        score += _norm(df[key]).to_numpy() * (max(0.0, float(w[key])) / total_weight)
    return pd.Series(score, index=df.index)


st.set_page_config(page_title="Landskapsanalys Geocontext", layout="wide")
st.title("Landskapsanalys + Geocontext (Bornholm)")
st.caption("Fristaende app for kluster, geocontext-score och urval av hexagoner.")

repo_root = Path(__file__).resolve().parent

if h3 is None:
    st.error("Python-paketet `h3` saknas. Installera dependencies och starta om appen.")
    st.stop()

try:
    gc4 = load_gc4(repo_root)
except Exception as exc:
    st.error(f"Kunde inte lasa GC4-data: {exc}")
    st.stop()

map_df = build_map_frame(gc4).dropna(subset=["lat", "lon", "polygon"]).copy()
if map_df.empty:
    st.error("GC4-data laddades, men inga kartbara hexagoner hittades.")
    st.stop()

all_clusters = sorted([int(v) for v in map_df["class_km"].dropna().unique().tolist() if int(v) >= 0])
default_clusters = [0] if 0 in all_clusters else all_clusters

st.sidebar.header("Urval")
cluster_filter = st.sidebar.multiselect(
    "Kluster (class_km)",
    options=all_clusters,
    default=default_clusters,
)
if not cluster_filter:
    st.warning("Valj minst ett kluster i sidpanelen.")
    st.stop()

top_n = int(st.sidebar.number_input("Antal hex att markera", min_value=1, max_value=len(map_df), value=120))

st.sidebar.header("Viktning F1-F5")
w = {}
for factor, default in [("F1", 30), ("F2", 20), ("F3", 20), ("F4", 20), ("F5", 10)]:
    w[factor] = float(st.sidebar.slider(f"{factor} vikt", min_value=0, max_value=100, value=default, step=1))

work = map_df[map_df["class_km"].isin(cluster_filter)].copy()
if work.empty:
    st.error("Inga hexagoner finns i valt klusterurval.")
    st.stop()

work["score_composite"] = composite_score(work, w)
work = work.sort_values("score_composite", ascending=False)
work["selected"] = 0
work.iloc[: min(top_n, len(work)), work.columns.get_loc("selected")] = 1

view = map_df.merge(
    work[["hex_id", "score_composite", "selected"]],
    on="hex_id",
    how="left",
)
view["score_composite"] = pd.to_numeric(view["score_composite"], errors="coerce").fillna(0.0)
view["selected"] = pd.to_numeric(view["selected"], errors="coerce").fillna(0).astype(int)
view["cluster_color"] = view["class_km"].map(CLUSTER_COLORS).apply(
    lambda x: x if isinstance(x, list) else [180, 180, 180, 70]
)
view["fill_color"] = view["cluster_color"]
selected_mask = view["selected"] == 1
if selected_mask.any():
    view.loc[selected_mask, "fill_color"] = view.loc[selected_mask, "fill_color"].apply(lambda _: [220, 20, 60, 180])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Hex total", f"{len(map_df)}")
c2.metric("Hex i urval", f"{len(work)}")
c3.metric("Markerade hex", f"{int(work['selected'].sum())}")
c4.metric("Median score", f"{float(work['score_composite'].median()):.3f}")
st.caption(
    f"Valda kluster: {sorted(cluster_filter)} | Top N: {top_n} | "
    f"Vikter: F1={w['F1']:.0f}, F2={w['F2']:.0f}, F3={w['F3']:.0f}, F4={w['F4']:.0f}, F5={w['F5']:.0f}"
)

validation_df, validation_image_count = load_validation_assets(repo_root)
with st.expander("Valideringsunderlag (referens)", expanded=False):
    st.caption(
        "Kallor i data/raw/lablab/SpeedLocal/Bornholm används som visuell referens for validering av landskapsanalysen."
    )
    if not validation_df.empty:
        show = validation_df.copy()
        show["modified"] = pd.to_datetime(show["modified"], unit="s").dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(show, use_container_width=True, height=220, hide_index=True)
    else:
        st.caption("Inga PDF-referenser hittades i mappen PDF GIS.")
    st.caption(f"Antal bilder i 'Bilder G-maps': {validation_image_count}")

left, right = st.columns([1.1, 2.2], gap="large")
with left:
    st.subheader("Kluster")
    cc = (
        map_df["class_km"]
        .value_counts()
        .sort_index()
        .rename_axis("class_km")
        .reset_index(name="n_hex")
    )
    st.bar_chart(cc, x="class_km", y="n_hex", use_container_width=True)

    st.subheader("Topprankade hex")
    st.dataframe(
        work[["hex_id", "class_km", "F1", "F2", "F3", "F4", "F5", "score_composite"]].head(top_n).round(4),
        use_container_width=True,
        height=420,
    )
    layer_dict = load_layer_dictionary(repo_root)
    if layer_dict is not None and not layer_dict.empty:
        st.subheader("Lagerordlista")
        show_cols = [c for c in ["svensk_namn", "kategori", "source_column", "short_column"] if c in layer_dict.columns]
        st.dataframe(layer_dict[show_cols], use_container_width=True, height=220)

with right:
    st.subheader("Karta: geocontext-kluster och urval")
    tooltip = {
        "html": (
            "<b>hex_id:</b> {hex_id}<br/>"
            "<b>class_km:</b> {class_km}<br/>"
            "<b>selected:</b> {selected}<br/>"
            "<b>score:</b> {score_composite}"
        ),
        "style": {"backgroundColor": "white", "color": "black"},
    }
    layer = pdk.Layer(
        "PolygonLayer",
        data=view,
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color=[90, 90, 90, 90],
        line_width_min_pixels=0.5,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )
    center_lat = float(view["lat"].median())
    center_lon = float(view["lon"].median())
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=9, pitch=0),
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    )
    st.pydeck_chart(deck, use_container_width=True)
