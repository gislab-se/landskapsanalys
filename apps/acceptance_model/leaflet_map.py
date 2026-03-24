from __future__ import annotations

import json
from typing import Any


DEFAULT_CENTER = [55.14, 14.92]
V4_CLASS_LEGEND = [
    ("Exkluderad", "#d7dde2"),
    ("Lag", "#f1e8a6"),
    ("Medel", "#f0b35b"),
    ("Hog", "#7dbb7d"),
    ("Mycket hog", "#2c7a4b"),
]
V4_SCORE_LEGEND = [
    ("0", "#efe8d8"),
    ("20", "#e0c782"),
    ("40", "#d99048"),
    ("60", "#9bb86c"),
    ("80", "#2c7a4b"),
]
V4_CLUSTER_LEGEND = [
    ("1", "#355C7D", "Tatorts- och verksamhetskarnor"),
    ("2", "#C06C84", "Vardagslandskap med blandad bakgrundskaraktar"),
    ("3", "#F67280", "Flygsands- och laglanta kuststrak"),
    ("4", "#99B898", "Brant relief och dalpraglat inland"),
    ("5", "#E5D97B", "Skogligt skyddsinland och habitatkarnor"),
]


def _overlay_spec(
    name: str,
    geojson: dict[str, Any],
    stroke_color: str,
    fill_color: str,
    stroke_opacity: float,
    fill_opacity: float,
    weight: float,
    point_radius: int,
    default_visible: bool = True,
    fill_pattern: str | None = None,
    stroke: bool = True,
    fill_color_property: str | None = None,
    fill_opacity_property: str | None = None,
    popup_title: str | None = None,
    popup_title_property: str | None = None,
    popup_body_property: str | None = None,
    overlay_family: str = "standard",
) -> dict[str, Any]:
    return {
        "name": name,
        "data": geojson,
        "stroke": stroke,
        "strokeColor": stroke_color,
        "fillColor": fill_color,
        "fillColorProperty": fill_color_property,
        "fillOpacityProperty": fill_opacity_property,
        "strokeOpacity": stroke_opacity,
        "fillOpacity": fill_opacity,
        "weight": weight,
        "pointRadius": point_radius,
        "defaultVisible": default_visible,
        "fillPattern": fill_pattern,
        "popupTitle": popup_title,
        "popupTitleProperty": popup_title_property,
        "popupBodyProperty": popup_body_property,
        "overlayFamily": overlay_family,
    }


def build_leaflet_html(
    source_overlays: list[dict[str, Any]],
    group_overlays: list[dict[str, Any]],
    combined_overlay: dict[str, Any] | None,
    reference_payload: dict[str, Any] | None = None,
) -> str:
    overlay_specs = []
    overlay_specs.extend(source_overlays)
    overlay_specs.extend(group_overlays)
    if combined_overlay is not None:
        overlay_specs.append(combined_overlay)

    payload = json.dumps(overlay_specs)
    reference = json.dumps(reference_payload)
    center = json.dumps(DEFAULT_CENTER)
    class_legend = json.dumps(V4_CLASS_LEGEND)
    score_legend = json.dumps(V4_SCORE_LEGEND)
    cluster_legend = json.dumps(V4_CLUSTER_LEGEND)
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    #map {{ min-height: 720px; border-radius: 12px; overflow: hidden; }}
    .leaflet-control-layers {{ font-family: sans-serif; font-size: 12px; max-height: 80vh; overflow-y: auto; }}
    .leaflet-popup-content {{ font-family: sans-serif; font-size: 12px; line-height: 1.35; }}
    .v4-control {{ background: rgba(255,255,255,0.95); padding: 8px 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); border-radius: 4px; font-family: sans-serif; }}
    .v4-control-title {{ font-weight: 600; margin-bottom: 4px; font-size: 12px; }}
    .v4-legend-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 3px; font-size: 12px; }}
    .v4-swatch {{ width: 12px; height: 12px; border-radius: 2px; flex: 0 0 12px; }}
    .v4-score-row {{ display: flex; align-items: center; gap: 4px; margin-top: 4px; font-size: 11px; }}
    .v4-score-box {{ width: 16px; height: 10px; border-radius: 2px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const overlaySpecs = {payload};
    const referencePayload = {reference};
    const defaultCenter = {center};
    const v4ClassLegend = {class_legend};
    const v4ScoreLegend = {score_legend};
    const v4ClusterLegend = {cluster_legend};
    const map = L.map('map', {{ preferCanvas: true }}).setView(defaultCenter, 9);
    const svgRenderer = L.svg();
    svgRenderer.addTo(map);

    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors'
    }});

    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
    }});

    osm.addTo(map);

    const baseLayers = {{
      'OSM': osm,
      'Satellite': satellite
    }};

    const overlayLayers = {{}};
    let overallBounds = null;
    let referenceOpacity = 0.95;

    function ensurePatternDefs() {{
      const svgRoot = svgRenderer._container;
      if (!svgRoot) return;
      const svgNs = 'http://www.w3.org/2000/svg';
      let defs = svgRoot.querySelector('defs');
      if (!defs) {{
        defs = document.createElementNS(svgNs, 'defs');
        svgRoot.insertBefore(defs, svgRoot.firstChild);
      }}

      if (!svgRoot.querySelector('#combined-acceptance-thin-red-hatch')) {{
        const pattern = document.createElementNS(svgNs, 'pattern');
        pattern.setAttribute('id', 'combined-acceptance-thin-red-hatch');
        pattern.setAttribute('patternUnits', 'userSpaceOnUse');
        pattern.setAttribute('width', '8');
        pattern.setAttribute('height', '8');
        pattern.setAttribute('patternTransform', 'rotate(32)');

        const background = document.createElementNS(svgNs, 'rect');
        background.setAttribute('width', '8');
        background.setAttribute('height', '8');
        background.setAttribute('fill', '#c4322b');
        background.setAttribute('fill-opacity', '0.06');
        pattern.appendChild(background);

        const line = document.createElementNS(svgNs, 'line');
        line.setAttribute('x1', '0');
        line.setAttribute('y1', '0');
        line.setAttribute('x2', '0');
        line.setAttribute('y2', '8');
        line.setAttribute('stroke', '#c4322b');
        line.setAttribute('stroke-width', '0.9');
        line.setAttribute('stroke-opacity', '0.45');
        pattern.appendChild(line);

        defs.appendChild(pattern);
      }}
    }}

    function applyPatternToLayer(geoLayer, meta) {{
      if (!meta.fillPattern) return;
      ensurePatternDefs();
      geoLayer.eachLayer((featureLayer) => {{
        if (!featureLayer._path) return;
        featureLayer._path.setAttribute('fill', `url(#${{meta.fillPattern}})`);
        featureLayer._path.setAttribute('fill-opacity', '1');
      }});
    }}

    function mergeBounds(layer) {{
      if (!layer || !layer.getBounds) return;
      const layerBounds = layer.getBounds();
      if (!layerBounds || !layerBounds.isValid()) return;
      overallBounds = overallBounds ? overallBounds.extend(layerBounds) : layerBounds;
    }}

    function featureFillColor(meta, feature) {{
      const props = (feature && feature.properties) || {{}};
      if (meta.fillColorProperty && props[meta.fillColorProperty]) {{
        return props[meta.fillColorProperty];
      }}
      return meta.fillColor;
    }}

    function baseFeatureFillOpacity(meta, feature) {{
      const props = (feature && feature.properties) || {{}};
      if (meta.fillOpacityProperty && props[meta.fillOpacityProperty] != null) {{
        return parseFloat(props[meta.fillOpacityProperty]);
      }}
      return meta.fillOpacity;
    }}

    function effectiveFeatureFillOpacity(meta, feature) {{
      const baseOpacity = baseFeatureFillOpacity(meta, feature);
      if (meta.overlayFamily === 'reference') {{
        return baseOpacity * referenceOpacity;
      }}
      return baseOpacity;
    }}

    function featurePopupTitle(meta, props) {{
      if (meta.popupTitleProperty && props[meta.popupTitleProperty]) {{
        return props[meta.popupTitleProperty];
      }}
      if (meta.popupTitle) {{
        return meta.popupTitle;
      }}
      return props.tooltip_title || meta.name;
    }}

    function featurePopupBody(meta, props) {{
      if (meta.popupBodyProperty && props[meta.popupBodyProperty]) {{
        return props[meta.popupBodyProperty];
      }}
      return props.tooltip_body || '';
    }}

    function registerOverlay(meta, data) {{
      if (!data) return;
      const geoLayer = L.geoJSON(data, {{
        renderer: meta.fillPattern ? svgRenderer : undefined,
        style: function(feature) {{
          return {{
            stroke: meta.stroke !== false,
            color: meta.strokeColor,
            weight: meta.weight,
            opacity: meta.strokeOpacity,
            fillColor: featureFillColor(meta, feature),
            fillOpacity: effectiveFeatureFillOpacity(meta, feature)
          }};
        }},
        pointToLayer: function(feature, latlng) {{
          const fillColor = featureFillColor(meta, feature);
          const fillOpacity = effectiveFeatureFillOpacity(meta, feature);
          return L.circleMarker(latlng, {{
            radius: meta.pointRadius,
            color: meta.strokeColor,
            weight: Math.max(meta.weight, 1),
            opacity: meta.strokeOpacity,
            fillColor: fillColor,
            fillOpacity: Math.max(fillOpacity, meta.overlayFamily === 'reference' ? 0.0 : 0.2)
          }});
        }},
        onEachFeature: function(feature, layer) {{
          const props = feature.properties || {{}};
          const title = featurePopupTitle(meta, props);
          const body = featurePopupBody(meta, props);
          const html = `<strong>${{title}}</strong>${{body ? '<br>' + body : ''}}`;
          layer.bindPopup(html);
        }}
      }});

      geoLayer._overlayMeta = meta;
      geoLayer.on('add', function() {{
        window.requestAnimationFrame(() => applyPatternToLayer(geoLayer, meta));
        if (meta.overlayFamily === 'reference' && geoLayer.bringToFront) {{
          geoLayer.bringToFront();
        }}
      }});

      overlayLayers[meta.name] = geoLayer;
      if (meta.defaultVisible) {{
        geoLayer.addTo(map);
      }}
      mergeBounds(geoLayer);
    }}

    function applyReferenceOpacity(value) {{
      referenceOpacity = value;
      Object.values(overlayLayers).forEach((layer) => {{
        if (!layer || !layer._overlayMeta || layer._overlayMeta.overlayFamily !== 'reference') return;
        const meta = layer._overlayMeta;
        layer.eachLayer((featureLayer) => {{
          const feature = featureLayer.feature || null;
          const nextStyle = {{
            fillOpacity: effectiveFeatureFillOpacity(meta, feature),
            fillColor: featureFillColor(meta, feature),
            stroke: meta.stroke !== false,
            opacity: meta.strokeOpacity,
            color: meta.strokeColor,
            weight: meta.weight,
          }};
          if (featureLayer.setStyle) {{
            featureLayer.setStyle(nextStyle);
          }}
        }});
      }});
    }}

    function addReferenceOpacityControl() {{
      if (!referencePayload || !referencePayload.layers || !referencePayload.layers.length) return;
      const OpacityControl = L.Control.extend({{
        options: {{ position: 'topleft' }},
        onAdd: function() {{
          const container = L.DomUtil.create('div', 'v4-control');
          container.style.width = '185px';
          const title = L.DomUtil.create('div', 'v4-control-title', container);
          title.innerHTML = 'V4 opacity';
          const slider = L.DomUtil.create('input', '', container);
          slider.type = 'range';
          slider.min = '5';
          slider.max = '100';
          slider.step = '5';
          slider.value = String(Math.round(referenceOpacity * 100));
          slider.style.width = '100%';
          const valueLabel = L.DomUtil.create('div', '', container);
          valueLabel.style.fontSize = '12px';
          valueLabel.style.marginTop = '4px';
          valueLabel.innerHTML = slider.value + '%';
          L.DomEvent.disableClickPropagation(container);
          L.DomEvent.disableScrollPropagation(container);
          slider.addEventListener('input', function(e) {{
            valueLabel.innerHTML = e.target.value + '%';
            applyReferenceOpacity(parseFloat(e.target.value) / 100.0);
          }});
          return container;
        }}
      }});
      map.addControl(new OpacityControl());
    }}

    function addReferenceLegendControl() {{
      if (!referencePayload || !referencePayload.layers || !referencePayload.layers.length) return null;
      const LegendControl = L.Control.extend({{
        options: {{ position: 'bottomright' }},
        onAdd: function() {{
          const container = L.DomUtil.create('div', 'v4-control');
          container.style.maxWidth = '210px';
          const title = L.DomUtil.create('div', 'v4-control-title', container);
          title.innerHTML = 'V4 legend';

          const classTitle = L.DomUtil.create('div', '', container);
          classTitle.style.fontSize = '12px';
          classTitle.style.marginBottom = '4px';
          classTitle.innerHTML = 'Scenarioklass';
          v4ClassLegend.forEach((item) => {{
            const row = L.DomUtil.create('div', 'v4-legend-row', container);
            const swatch = L.DomUtil.create('span', 'v4-swatch', row);
            swatch.style.background = item[1];
            if (item[0] === 'Exkluderad') {{
              swatch.style.opacity = '0.18';
            }}
            const label = L.DomUtil.create('span', '', row);
            label.innerHTML = item[0];
          }});

          const scoreTitle = L.DomUtil.create('div', '', container);
          scoreTitle.style.fontSize = '12px';
          scoreTitle.style.marginTop = '6px';
          scoreTitle.style.marginBottom = '4px';
          scoreTitle.innerHTML = 'Mellan scenarioscore';
          const scoreRow = L.DomUtil.create('div', 'v4-score-row', container);
          v4ScoreLegend.forEach((item) => {{
            const wrap = L.DomUtil.create('div', '', scoreRow);
            wrap.style.display = 'flex';
            wrap.style.flexDirection = 'column';
            wrap.style.alignItems = 'center';
            const box = L.DomUtil.create('span', 'v4-score-box', wrap);
            box.style.background = item[1];
            const label = L.DomUtil.create('span', '', wrap);
            label.innerHTML = item[0];
          }});

          L.DomEvent.disableClickPropagation(container);
          L.DomEvent.disableScrollPropagation(container);
          return container;
        }}
      }});
      const control = new LegendControl();
      map.addControl(control);
      return control;
    }}

    function addClusterLegendControl() {{
      if (!referencePayload || !referencePayload.layers || !referencePayload.layers.length) return null;
      const ClusterLegendControl = L.Control.extend({{
        options: {{ position: 'bottomleft' }},
        onAdd: function() {{
          const container = L.DomUtil.create('div', 'v4-control');
          container.style.maxWidth = '240px';
          container.style.display = 'none';
          const title = L.DomUtil.create('div', 'v4-control-title', container);
          title.innerHTML = 'V4 klusterlegend';
          v4ClusterLegend.forEach((item) => {{
            const row = L.DomUtil.create('div', 'v4-legend-row', container);
            const swatch = L.DomUtil.create('span', 'v4-swatch', row);
            swatch.style.background = item[1];
            const label = L.DomUtil.create('span', '', row);
            label.innerHTML = item[0] + ' - ' + item[2];
          }});
          L.DomEvent.disableClickPropagation(container);
          L.DomEvent.disableScrollPropagation(container);
          return container;
        }}
      }});
      const control = new ClusterLegendControl();
      map.addControl(control);
      return control;
    }}

    overlaySpecs.forEach((meta) => registerOverlay(meta, meta.data));

    if (referencePayload && referencePayload.featureCollection && Array.isArray(referencePayload.layers)) {{
      referencePayload.layers.forEach((meta) => registerOverlay(meta, referencePayload.featureCollection));
    }}

    addReferenceOpacityControl();
    const v4LegendControl = addReferenceLegendControl();
    const clusterLegendControl = addClusterLegendControl();

    L.control.layers(baseLayers, overlayLayers, {{ collapsed: false }}).addTo(map);

    function toggleClusterLegend() {{
      if (!clusterLegendControl || !clusterLegendControl.getContainer) return;
      const container = clusterLegendControl.getContainer();
      if (!container) return;
      const clusterLayer = overlayLayers['V4: Landskapskluster'];
      const isActive = clusterLayer ? map.hasLayer(clusterLayer) : false;
      container.style.display = isActive ? 'block' : 'none';
    }}

    map.on('overlayadd', function(e) {{
      if (e.layer && e.layer.bringToFront) {{
        e.layer.bringToFront();
      }}
      toggleClusterLegend();
    }});
    map.on('overlayremove', function() {{
      toggleClusterLegend();
    }});

    applyReferenceOpacity(referenceOpacity);
    toggleClusterLegend();
    if (overallBounds && overallBounds.isValid()) {{
      map.fitBounds(overallBounds.pad(0.05));
    }}
  </script>
</body>
</html>
"""


def source_overlay(
    name: str,
    geojson: dict[str, Any],
    color_hex: str,
    opacity: float,
    point_radius: int,
) -> dict[str, Any]:
    return _overlay_spec(
        name=name,
        geojson=geojson,
        stroke_color=color_hex,
        fill_color=color_hex,
        stroke_opacity=max(min(opacity, 1.0), 0.0),
        fill_opacity=max(min(opacity * 0.28, 1.0), 0.0),
        weight=2.0,
        point_radius=point_radius,
        default_visible=False,
    )


def group_overlay(
    name: str,
    geojson: dict[str, Any],
    color_hex: str,
    opacity: float,
) -> dict[str, Any]:
    return _overlay_spec(
        name=name,
        geojson=geojson,
        stroke_color=color_hex,
        fill_color=color_hex,
        stroke_opacity=max(min(opacity * 0.95, 1.0), 0.0),
        fill_opacity=max(min(opacity * 0.32, 1.0), 0.0),
        weight=2.2,
        point_radius=6,
        default_visible=False,
    )


def combined_overlay(name: str, geojson: dict[str, Any], semantics: str | None) -> dict[str, Any]:
    if semantics == "combined_conflict":
        return _overlay_spec(
            name=name,
            geojson=geojson,
            stroke_color="#c4322b",
            fill_color="#c4322b",
            stroke_opacity=0.62,
            fill_opacity=0.20,
            weight=1.9,
            point_radius=6,
            default_visible=True,
        )

    return _overlay_spec(
        name=name,
        geojson=geojson,
        stroke_color="#c4322b",
        fill_color="#c4322b",
        stroke_opacity=0.72,
        fill_opacity=0.08,
        weight=1.5,
        point_radius=6,
        default_visible=True,
        fill_pattern="combined-acceptance-thin-red-hatch",
    )
