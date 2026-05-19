from __future__ import annotations

import json
import logging
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
        feature_collection = _add_resolution_metadata(feature_collection, resolution)
        _write_json(output_path, feature_collection)
        counts[resolution] = len(feature_collection.get("features") or [])

    source_data = _read_json(SOURCE_DATA)
    counts[10] = len(source_data.get("features") or [])
    return counts


def _html_template(manifest: dict[str, Any], counts: dict[int, int]) -> str:
    type_labels = manifest.get("landscape_type_labels") or {}
    type_colors = manifest.get("landscape_type_colors") or {}
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
    const datasets = __DATASETS__;
    const dataCache = new Map();
    let activeLayer = null;
    let activeResolution = null;
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

    function buildLegend() {
      for (const [typeId, meta] of Object.entries(typeMeta)) {
        const row = document.createElement("div");
        row.className = "legend-row";
        row.innerHTML = `<span class="swatch" style="background:${meta.color}"></span><span>${escapeHtml(typeId)} · ${escapeHtml(meta.label)}</span>`;
        legend.appendChild(row);
      }
    }

    function colorForFeature(feature) {
      const props = feature.properties || {};
      if (props.landscape_type_fill) {
        return props.landscape_type_fill;
      }
      const typeId = props.v10_type_id || props.landscape_type || "LT?";
      return (typeMeta[typeId] && typeMeta[typeId].color) || "#999999";
    }

    function popupForFeature(feature) {
      const props = feature.properties || {};
      if (props.popup) {
        return props.popup;
      }
      const typeId = props.v10_type_id || props.landscape_type || "LT?";
      const meta = typeMeta[typeId] || {};
      const typeName = props.v10_type_name || meta.label || typeId;
      const cluster = props.v9_cluster || props.class_km || props.class_k8 || "?";
      const confidence = props.v10_confidence || props.confidence || "";
      return [
        `<strong>${escapeHtml(props.hex_id || "")}</strong>`,
        `Landskapstyp: ${escapeHtml(typeName)}`,
        `Landskapsstruktur: ${escapeHtml(cluster)}`,
        confidence ? `Säkerhet: ${escapeHtml(confidence)}` : ""
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
      statusEl.innerHTML = `${loading ? "Laddar" : "Visar"} ${dataset.label}<span>${dataset.note}. ${count} hexagoner. ${autoMode ? "Auto-rollup är aktivt." : "Manuell upplösning är vald."}</span>`;
    }

    function styleFeature(feature) {
      return {
        color: "rgba(27, 36, 29, 0.46)",
        weight: 0.45,
        fillColor: colorForFeature(feature),
        fillOpacity: 0.72
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
          layer.on("mouseover", () => layer.setStyle({ weight: 1.8, fillOpacity: 0.88 }));
          layer.on("mouseout", () => layer.setStyle(styleFeature(feature)));
        }
      }).addTo(map);
      updateStatus(resolution, false);
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

    buildLegend();
    showResolution(resolutionForZoom(map.getZoom())).catch((error) => {
      statusEl.innerHTML = `Kartan kunde inte laddas<span>${escapeHtml(error.message)}</span>`;
    });
  </script>
</body>
</html>
"""
        .replace("__TYPE_META__", json.dumps(type_meta, ensure_ascii=False, indent=4))
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
