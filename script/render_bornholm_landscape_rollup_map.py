from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)

from potential_model.landscape import (  # noqa: E402
    landscape_frame_for_resolution,
    landscape_type_feature_collection_for_frame,
)
from potential_model.manifests import load_region, read_manifest, resolve_repo_path  # noqa: E402


LANDSCAPE_MANIFEST = ROOT / "apps/potential_model/manifests/landscape/bornholm_landscape_v10.json"
MAP_DIR = ROOT / "docs/geocontext/model_comparisons/bornholm_v10_landscape_types/map"
SOURCE_DATA = MAP_DIR / "bornholm_v10_landscape_types_map_data.geojson"
HTML_OUTPUT = MAP_DIR / "bornholm_v10_landscape_types_rollup_map.html"
ROLLUP_OUTPUTS = {
    9: MAP_DIR / "bornholm_v10_landscape_types_rollup_r9.geojson",
    8: MAP_DIR / "bornholm_v10_landscape_types_rollup_r8.geojson",
    7: MAP_DIR / "bornholm_v10_landscape_types_rollup_r7.geojson",
    6: MAP_DIR / "bornholm_v10_landscape_types_rollup_r6.geojson",
}

V9_META = {
    "1": {
        "label": "Tätorts- och verksamhetskärnor",
        "color": "#6E7C91",
        "factor": "F4",
    },
    "2": {
        "label": "Sprickdalspåverkat övergångslandskap",
        "color": "#8B6B45",
        "factor": "F1",
    },
    "3": {
        "label": "Blandat vardagslandskap med låg faktorprofil",
        "color": "#D8C97A",
        "factor": "mixed",
    },
    "4": {
        "label": "Flygsand och sandkust - kärnzon",
        "color": "#D5B08A",
        "factor": "F2",
    },
    "5": {
        "label": "Sprickdal och brant relief - kärnzon med sand/kust",
        "color": "#8B6B45",
        "factor": "F1",
    },
    "6": {
        "label": "Öppet och låglänt blandlandskap",
        "color": "#9AA8B8",
        "factor": "F5",
    },
    "7": {
        "label": "Skog och skyddad natur - kärnzon",
        "color": "#5B7F4A",
        "factor": "F3",
    },
    "8": {
        "label": "Sand- och kustpräglat landskap",
        "color": "#D5B08A",
        "factor": "F2",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def _display_geometry_path(region: dict[str, Any], resolution: int) -> str | None:
    value = (region.get("h3_display_geometries") or {}).get(str(resolution))
    path = resolve_repo_path(value)
    if path is None or not path.exists():
        return None
    return str(path)


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return round(number, 4)


def _integer_key(value: Any) -> str | None:
    number = _numeric(value)
    if number is None:
        return None
    return str(int(number))


def _enrich_rollup_features(feature_collection: dict[str, Any], frame: Any) -> dict[str, Any]:
    rows = {str(row["hex_id"]): row for row in frame.to_dict("records") if row.get("hex_id")}
    for feature in feature_collection.get("features") or []:
        properties = feature.setdefault("properties", {})
        row = rows.get(str(properties.get("hex_id")), {})

        cluster_key = (
            _integer_key(row.get("class_k8"))
            or _integer_key(row.get("class_km"))
            or _integer_key(properties.get("v9_cluster"))
        )
        if cluster_key:
            cluster_meta = V9_META.get(cluster_key, {})
            properties["class_k8"] = int(cluster_key)
            properties["class_km"] = int(cluster_key)
            properties["v9_cluster"] = cluster_key
            properties["v9_cluster_label"] = cluster_meta.get("label", f"Kluster {cluster_key}")
            properties["v9_cluster_fill"] = cluster_meta.get("color", "#999999")

        for factor in ("F1", "F2", "F3", "F4", "F5"):
            factor_value = _numeric(row.get(factor))
            if factor_value is not None:
                properties[factor] = factor_value

        for column in ("v10_type_name_en", "v10_rule", "v10_rule_en", "v10_confidence"):
            value = row.get(column)
            if value is not None and str(value) != "nan":
                properties[column] = str(value)
    return feature_collection


def _add_resolution_metadata(feature_collection: dict[str, Any], resolution: int) -> dict[str, Any]:
    for feature in feature_collection.get("features") or []:
        properties = feature.setdefault("properties", {})
        properties["h3_resolution"] = resolution
        properties["source_h3_resolution"] = 10
    feature_collection["metadata"] = {
        "region": "Bornholm",
        "h3_resolution": resolution,
        "source_h3_resolution": 10,
        "rollup_method": "Mode for landscape type and mean factor values from R10 source cells.",
    }
    return feature_collection


def _render_rollup_geojson() -> dict[int, int]:
    manifest = read_manifest(str(LANDSCAPE_MANIFEST))
    region = load_region("bornholm")
    counts: dict[int, int] = {}

    for resolution, output_path in ROLLUP_OUTPUTS.items():
        frame = landscape_frame_for_resolution(manifest, resolution)
        feature_collection = landscape_type_feature_collection_for_frame(
            manifest,
            frame,
            _display_geometry_path(region, resolution),
        )
        feature_collection = _enrich_rollup_features(feature_collection, frame)
        feature_collection = _add_resolution_metadata(feature_collection, resolution)
        _write_json(output_path, feature_collection)
        counts[resolution] = len(feature_collection.get("features") or [])

    source_data = _read_json(SOURCE_DATA)
    counts[10] = len(source_data.get("features") or [])
    return counts


def _html_template(manifest: dict[str, Any], counts: dict[int, int]) -> str:
    type_labels = manifest.get("landscape_type_labels") or {}
    type_colors = manifest.get("landscape_type_colors") or {}
    factor_labels = manifest.get("factor_labels") or {}
    type_meta = {
        key: {"label": type_labels.get(key, key), "color": type_colors.get(key, "#999999")}
        for key in sorted(type_labels)
    }
    datasets = {
        "10": {
            "label": "R10 detalj",
            "url": "bornholm_v10_landscape_types_map_data.geojson",
            "count": counts.get(10, 0),
            "note": "Källupplösning",
        },
        "9": {
            "label": "R9 nära",
            "url": "bornholm_v10_landscape_types_rollup_r9.geojson",
            "count": counts.get(9, 0),
            "note": "Tät rollup",
        },
        "8": {
            "label": "R8 mellan",
            "url": "bornholm_v10_landscape_types_rollup_r8.geojson",
            "count": counts.get(8, 0),
            "note": "Regional läsning",
        },
        "7": {
            "label": "R7 översikt",
            "url": "bornholm_v10_landscape_types_rollup_r7.geojson",
            "count": counts.get(7, 0),
            "note": "Grov översikt",
        },
        "6": {
            "label": "R6 helhet",
            "url": "bornholm_v10_landscape_types_rollup_r6.geojson",
            "count": counts.get(6, 0),
            "note": "Mest generaliserad",
        },
    }
    return (
        """<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bornholm landskapskarta med rollup</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    :root {
      --ink: #121914;
      --muted: #5d625e;
      --paper: #f7f4ed;
      --panel: rgba(255, 253, 248, 0.94);
      --line: rgba(24, 31, 26, 0.16);
      --green: #335f49;
      --green-dark: #17241c;
      --shadow: 0 18px 45px rgba(23, 28, 23, 0.18);
    }

    * {
      box-sizing: border-box;
    }

    html,
    body,
    #map {
      width: 100%;
      height: 100%;
      margin: 0;
    }

    body {
      background: var(--paper);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }

    #map {
      background: #dce4e4;
    }

    .leaflet-container {
      font: 15px/1.45 Georgia, "Times New Roman", serif;
    }

    .leaflet-popup-content-wrapper {
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .panel {
      position: absolute;
      z-index: 600;
      left: 18px;
      top: 18px;
      width: min(380px, calc(100vw - 36px));
      max-height: calc(100vh - 36px);
      overflow: auto;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 0 10px;
      border-radius: 7px;
      background: #e8ece7;
      color: var(--green);
      font-family: Arial, sans-serif;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }

    h1 {
      margin: 12px 0 8px;
      font-size: 34px;
      line-height: 0.95;
    }

    p {
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.55;
    }

    .toolbar {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;
      margin: 16px 0 10px;
    }

    .control-block {
      display: grid;
      gap: 8px;
      margin-top: 15px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }

    .control-title {
      color: var(--green);
      font-family: Arial, sans-serif;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }

    .mode-list,
    .factor-grid {
      display: grid;
      gap: 7px;
    }

    .factor-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .option {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      color: var(--ink);
      font-family: Arial, sans-serif;
      font-size: 13px;
      font-weight: 700;
      line-height: 1.35;
    }

    .option span {
      color: var(--muted);
      display: block;
      font-weight: 600;
    }

    .option input {
      margin-top: 2px;
      accent-color: var(--green-dark);
    }

    .slider-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 48px;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-family: Arial, sans-serif;
      font-size: 13px;
      font-weight: 800;
    }

    input[type="range"] {
      width: 100%;
      accent-color: var(--green-dark);
    }

    button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fffdf8;
      color: var(--ink);
      cursor: pointer;
      font-family: Arial, sans-serif;
      font-size: 12px;
      font-weight: 800;
    }

    button:hover {
      border-color: rgba(51, 95, 73, 0.55);
    }

    button.active {
      border-color: var(--green-dark);
      background: var(--green-dark);
      color: #fffdf8;
    }

    .status {
      display: grid;
      gap: 4px;
      min-height: 48px;
      margin: 12px 0 16px;
      padding: 10px 12px;
      border-left: 4px solid #c9a65b;
      background: rgba(255, 255, 255, 0.74);
      color: var(--ink);
      font-family: Arial, sans-serif;
      font-size: 13px;
      font-weight: 700;
    }

    .status span {
      color: var(--muted);
      font-weight: 600;
    }

    .legend {
      display: grid;
      gap: 8px;
      margin-top: 16px;
    }

    .legend-title {
      font-family: Arial, sans-serif;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--green);
    }

    .legend-row {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 14px;
    }

    .swatch {
      width: 18px;
      height: 18px;
      border: 1px solid rgba(18, 25, 20, 0.18);
      border-radius: 4px;
    }

    .factor-ramp {
      height: 14px;
      border: 1px solid rgba(18, 25, 20, 0.18);
      border-radius: 4px;
      background: linear-gradient(90deg, #4f6d9a, #f7f4ec, #b65f57);
    }

    .factor-scale {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-family: Arial, sans-serif;
      font-size: 12px;
      font-weight: 700;
    }

    .zoom-control {
      position: absolute;
      z-index: 601;
      right: 18px;
      top: 18px;
      display: grid;
      gap: 8px;
    }

    .zoom-control button {
      width: 42px;
      height: 42px;
      padding: 0;
      font-size: 22px;
      line-height: 1;
      box-shadow: 0 10px 26px rgba(23, 28, 23, 0.16);
    }

    .leaflet-control-attribution {
      font-family: Arial, sans-serif;
    }

    @media (max-width: 720px) {
      .panel {
        left: 10px;
        right: 10px;
        top: 10px;
        width: auto;
        max-height: 46vh;
        padding: 14px;
      }

      h1 {
        font-size: 27px;
      }

      p {
        font-size: 14px;
      }

      .toolbar {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .zoom-control {
        right: 10px;
        bottom: 16px;
        top: auto;
      }
    }
  </style>
</head>
<body>
  <div id="map" aria-label="Bornholm landskapskarta med H3-rollup"></div>

  <section class="panel" aria-label="Kartkontroller">
    <span class="eyebrow">Bornholm</span>
    <h1>Landskapskarta med rollup</h1>
    <p>Växla mellan täta H3-steg från R10 till R6. Auto-läget byter upplösning efter zoomnivå och håller kartan läsbar från detalj till helhet.</p>

    <div class="toolbar" id="resolutionToolbar" aria-label="H3-upplösning">
      <button type="button" data-mode="auto" class="active">Auto</button>
      <button type="button" data-resolution="10">R10</button>
      <button type="button" data-resolution="9">R9</button>
      <button type="button" data-resolution="8">R8</button>
      <button type="button" data-resolution="7">R7</button>
      <button type="button" data-resolution="6">R6</button>
    </div>

    <div class="control-block" aria-label="Visningslager">
      <div class="control-title">Lager</div>
      <div class="mode-list">
        <label class="option"><input type="radio" name="viewMode" value="landscape" checked> Landskapstyper <span>Fem tolkade v10-typer.</span></label>
        <label class="option"><input type="radio" name="viewMode" value="structure"> Strukturer <span>v9 originalkluster K=8.</span></label>
        <label class="option"><input type="radio" name="viewMode" value="factor"> Faktorer <span>Kontinuerliga faktorvärden.</span></label>
      </div>
    </div>

    <div class="control-block" aria-label="Opacitet">
      <div class="control-title">Opacitet</div>
      <div class="slider-row">
        <input id="opacitySlider" type="range" min="15" max="95" value="72">
        <span id="opacityValue">72%</span>
      </div>
    </div>

    <div class="control-block" aria-label="Faktorer">
      <div class="control-title">Faktorer</div>
      <div class="factor-grid" id="factorControls">
        <label class="option"><input type="radio" name="factor" value="F1" checked> F1 <span>Sprickdal och brant relief</span></label>
        <label class="option"><input type="radio" name="factor" value="F2"> F2 <span>Flygsand och sandpräglad kust</span></label>
        <label class="option"><input type="radio" name="factor" value="F3"> F3 <span>Skog och skyddad natur</span></label>
        <label class="option"><input type="radio" name="factor" value="F4"> F4 <span>Tätort och byggd struktur</span></label>
        <label class="option"><input type="radio" name="factor" value="F5"> F5 <span>Låglänt öppet land</span></label>
      </div>
    </div>

    <div class="status" id="status">
      Laddar karta...
      <span>R10 är källnivån. Lägre resolutioner är rollups från samma Bornholm-klassning.</span>
    </div>

    <div class="legend" id="legend">
      <div class="legend-title">Landskapstyper</div>
    </div>
  </section>

  <div class="zoom-control" aria-label="Zoom">
    <button type="button" id="zoomIn" aria-label="Zooma in">+</button>
    <button type="button" id="zoomOut" aria-label="Zooma ut">−</button>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const typeMeta = __TYPE_META__;
    const v9Meta = __V9_META__;
    const factorLabels = __FACTOR_LABELS__;
    const datasets = __DATASETS__;
    const factorLimit = 4.5;
    const dataCache = new Map();
    let activeLayer = null;
    let activeResolution = null;
    let activeView = "landscape";
    let currentFactor = "F1";
    let fillOpacity = 0.72;
    let autoMode = true;
    let firstFit = true;

    const map = L.map("map", {
      preferCanvas: true,
      zoomControl: false,
      attributionControl: true
    }).setView([55.14, 14.92], 9);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    const statusEl = document.getElementById("status");
    const toolbar = document.getElementById("resolutionToolbar");
    const legend = document.getElementById("legend");
    const factorControls = document.getElementById("factorControls");
    const opacitySlider = document.getElementById("opacitySlider");
    const opacityValue = document.getElementById("opacityValue");

    document.getElementById("zoomIn").addEventListener("click", () => map.zoomIn());
    document.getElementById("zoomOut").addEventListener("click", () => map.zoomOut());

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function hexToRgb(hex) {
      const value = hex.replace("#", "");
      return [parseInt(value.slice(0, 2), 16), parseInt(value.slice(2, 4), 16), parseInt(value.slice(4, 6), 16)];
    }

    function rgbToHex(rgb) {
      return "#" + rgb.map((value) => clamp(Math.round(value), 0, 255).toString(16).padStart(2, "0")).join("");
    }

    function lerpColor(left, right, share) {
      const leftRgb = hexToRgb(left);
      const rightRgb = hexToRgb(right);
      return rgbToHex(leftRgb.map((value, index) => value + (rightRgb[index] - value) * share));
    }

    function factorColor(value) {
      const number = Number(value);
      if (!Number.isFinite(number)) {
        return "#d6d6d6";
      }
      const clamped = clamp(number, -factorLimit, factorLimit);
      if (clamped < 0) {
        return lerpColor("#4f6d9a", "#f7f4ec", (clamped + factorLimit) / factorLimit);
      }
      return lerpColor("#f7f4ec", "#b65f57", clamped / factorLimit);
    }

    function clusterKey(props) {
      return String(props.v9_cluster || props.class_km || props.class_k8 || props.cluster || "?");
    }

    function factorValueLine(props, factor) {
      const value = Number(props[factor]);
      return `${factor} ${factorLabels[factor] || factor}: ${Number.isFinite(value) ? value.toFixed(2) : "saknas"}`;
    }

    function setFactorControlsEnabled() {
      for (const input of factorControls.querySelectorAll("input")) {
        input.disabled = activeView !== "factor";
      }
    }

    function refreshLegend() {
      legend.innerHTML = "";
      const title = document.createElement("div");
      title.className = "legend-title";
      legend.appendChild(title);

      if (activeView === "factor") {
        title.textContent = `Faktor ${currentFactor}`;
        const text = document.createElement("div");
        text.className = "legend-row";
        text.style.gridTemplateColumns = "1fr";
        text.innerHTML = `<span>${escapeHtml(factorLabels[currentFactor] || currentFactor)}</span><div class="factor-ramp"></div><div class="factor-scale"><span>−${factorLimit.toFixed(1)}</span><span>0</span><span>${factorLimit.toFixed(1)}</span></div>`;
        legend.appendChild(text);
        return;
      }

      const meta = activeView === "structure" ? v9Meta : typeMeta;
      title.textContent = activeView === "structure" ? "Strukturer" : "Landskapstyper";
      for (const [id, item] of Object.entries(meta)) {
        const row = document.createElement("div");
        row.className = "legend-row";
        row.innerHTML = `<span class="swatch" style="background:${item.color}"></span><span>${escapeHtml(id)} · ${escapeHtml(item.label)}</span>`;
        legend.appendChild(row);
      }
    }

    function colorForFeature(feature) {
      const props = feature.properties || {};
      if (activeView === "factor") {
        return factorColor(props[currentFactor]);
      }
      if (activeView === "structure") {
        const meta = v9Meta[clusterKey(props)] || {};
        return props.v9_cluster_fill || meta.color || "#999999";
      }
      const typeId = props.v10_type_id || props.landscape_type || "LT?";
      const meta = typeMeta[typeId] || {};
      return props.landscape_type_fill || meta.color || "#999999";
    }

    function popupForFeature(feature) {
      const props = feature.properties || {};
      const typeId = props.v10_type_id || props.landscape_type || "LT?";
      const type = typeMeta[typeId] || {};
      const cluster = clusterKey(props);
      const structure = v9Meta[cluster] || {};
      const typeName = props.v10_type_name || type.label || typeId;
      const structureName = props.v9_cluster_label || structure.label || `Kluster ${cluster}`;
      const confidence = props.v10_confidence || props.confidence || "";
      return [
        `<strong>${escapeHtml(props.hex_id || "")}</strong>`,
        `<strong>${escapeHtml(typeId)} ${escapeHtml(typeName)}</strong>`,
        `Struktur ${escapeHtml(cluster)}: ${escapeHtml(structureName)}`,
        confidence ? `Säkerhet: ${escapeHtml(confidence)}` : "",
        factorValueLine(props, "F1"),
        factorValueLine(props, "F2"),
        factorValueLine(props, "F3"),
        factorValueLine(props, "F4"),
        factorValueLine(props, "F5")
      ].filter(Boolean).join("<br>");
    }

    async function loadDataset(resolution) {
      if (dataCache.has(resolution)) {
        return dataCache.get(resolution);
      }
      const dataset = datasets[String(resolution)];
      const response = await fetch(dataset.url);
      if (!response.ok) {
        throw new Error(`Kunde inte ladda ${dataset.url}`);
      }
      const data = await response.json();
      dataCache.set(resolution, data);
      return data;
    }

    function updateButtons(resolution) {
      for (const button of toolbar.querySelectorAll("button")) {
        const isAuto = button.dataset.mode === "auto";
        const isResolution = button.dataset.resolution === String(resolution);
        button.classList.toggle("active", (autoMode && isAuto) || (!autoMode && isResolution));
      }
    }

    function updateStatus(resolution, loading = false) {
      const dataset = datasets[String(resolution)];
      const count = new Intl.NumberFormat("sv-SE").format(dataset.count);
      const viewLabel = activeView === "factor" ? `faktor ${currentFactor}` : activeView === "structure" ? "strukturer" : "landskapstyper";
      statusEl.innerHTML = `${loading ? "Laddar" : "Visar"} ${dataset.label}<span>${dataset.note}. ${count} hexagoner. Visning: ${viewLabel}. ${autoMode ? "Auto-rollup är aktivt." : "Manuell upplösning är vald."}</span>`;
    }

    function styleFeature(feature) {
      return {
        color: "rgba(27, 36, 29, 0.10)",
        opacity: 0.65,
        weight: 0.12,
        fillColor: colorForFeature(feature),
        fillOpacity
      };
    }

    async function showResolution(resolution) {
      if (activeResolution === resolution && activeLayer) {
        updateButtons(resolution);
        updateStatus(resolution, false);
        return;
      }
      activeResolution = resolution;
      updateButtons(resolution);
      updateStatus(resolution, true);
      const data = await loadDataset(resolution);
      if (activeLayer) {
        map.removeLayer(activeLayer);
      }
      activeLayer = L.geoJSON(data, {
        style: styleFeature,
        onEachFeature: (feature, layer) => {
          layer.bindPopup(popupForFeature(feature));
          layer.on("mouseover", () => layer.setStyle({ color: "rgba(27, 36, 29, 0.26)", opacity: 0.75, weight: 0.45, fillOpacity: Math.min(fillOpacity + 0.12, 0.95) }));
          layer.on("mouseout", () => layer.setStyle(styleFeature(feature)));
        }
      }).addTo(map);
      updateStatus(resolution, false);
      refreshLegend();
      if (firstFit) {
        firstFit = false;
        map.fitBounds(activeLayer.getBounds(), { padding: [18, 18] });
      }
    }

    function resolutionForZoom(zoom) {
      if (zoom >= 12) return 10;
      if (zoom >= 11) return 9;
      if (zoom >= 9) return 8;
      if (zoom >= 7) return 7;
      return 6;
    }

    toolbar.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      if (button.dataset.mode === "auto") {
        autoMode = true;
        showResolution(resolutionForZoom(map.getZoom()));
        return;
      }
      autoMode = false;
      showResolution(Number(button.dataset.resolution));
    });

    map.on("zoomend", () => {
      if (autoMode) {
        showResolution(resolutionForZoom(map.getZoom()));
      }
    });

    document.addEventListener("change", (event) => {
      const target = event.target;
      if (!target) return;
      if (target.name === "viewMode") {
        activeView = target.value;
        setFactorControlsEnabled();
        if (activeLayer) {
          activeLayer.setStyle(styleFeature);
        }
        refreshLegend();
        updateStatus(activeResolution || resolutionForZoom(map.getZoom()), false);
      }
      if (target.name === "factor") {
        currentFactor = target.value;
        if (activeLayer) {
          activeLayer.setStyle(styleFeature);
        }
        refreshLegend();
        updateStatus(activeResolution || resolutionForZoom(map.getZoom()), false);
      }
    });

    opacitySlider.addEventListener("input", () => {
      fillOpacity = Number(opacitySlider.value) / 100;
      opacityValue.textContent = `${opacitySlider.value}%`;
      if (activeLayer) {
        activeLayer.setStyle(styleFeature);
      }
    });

    setFactorControlsEnabled();
    refreshLegend();
    showResolution(resolutionForZoom(map.getZoom())).catch((error) => {
      statusEl.innerHTML = `Kartan kunde inte laddas<span>${escapeHtml(error.message)}</span>`;
    });
  </script>
</body>
</html>
"""
        .replace("__TYPE_META__", json.dumps(type_meta, ensure_ascii=False, indent=4))
        .replace("__V9_META__", json.dumps(V9_META, ensure_ascii=False, indent=4))
        .replace("__FACTOR_LABELS__", json.dumps(factor_labels, ensure_ascii=False, indent=4))
        .replace("__DATASETS__", json.dumps(datasets, ensure_ascii=False, indent=4))
    )


def main() -> None:
    manifest = read_manifest(str(LANDSCAPE_MANIFEST))
    counts = _render_rollup_geojson()
    HTML_OUTPUT.write_text(_html_template(manifest, counts), encoding="utf-8")
    print(f"Wrote {HTML_OUTPUT.relative_to(ROOT)}")
    for resolution in sorted(ROLLUP_OUTPUTS, reverse=True):
        print(f"R{resolution}: {counts[resolution]} features -> {ROLLUP_OUTPUTS[resolution].relative_to(ROOT)}")
    print(f"R10 source: {counts[10]} features -> {SOURCE_DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
