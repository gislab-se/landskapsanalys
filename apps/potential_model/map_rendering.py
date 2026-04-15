from __future__ import annotations

import json
from typing import Any


def build_landscape_map_html(
    feature_collection: dict[str, Any],
    center: list[float],
    zoom: int,
    mode: str,
    title: str,
    bounds: list[list[float]] | None = None,
    fill_opacity: float = 0.72,
    legend_items: list[dict[str, str]] | None = None,
) -> str:
    payload = json.dumps(feature_collection, ensure_ascii=False)
    center_payload = json.dumps(center)
    bounds_payload = json.dumps(bounds)
    mode_payload = json.dumps(mode)
    title_payload = json.dumps(title, ensure_ascii=False)
    opacity_payload = json.dumps(max(0.0, min(1.0, float(fill_opacity))))
    legend_payload = json.dumps(legend_items or [], ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    #map {{ min-height: 720px; border-radius: 8px; overflow: hidden; }}
    .leaflet-control-layers, .map-note, .map-legend {{ font-family: sans-serif; font-size: 12px; }}
    .map-note {{ background: rgba(255,255,255,0.94); padding: 8px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); max-width: 240px; }}
    .map-legend {{ background: rgba(255,255,255,0.94); padding: 9px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); line-height: 1.25; max-width: 260px; }}
    .map-legend-title {{ font-weight: 700; margin-bottom: 6px; }}
    .map-legend-row {{ display: flex; align-items: center; gap: 6px; margin: 4px 0; }}
    .map-legend-swatch {{ width: 14px; height: 14px; border: 1px solid rgba(0,0,0,0.22); flex: 0 0 auto; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const data = {payload};
    const defaultCenter = {center_payload};
    const defaultBounds = {bounds_payload};
    const mode = {mode_payload};
    const mapTitle = {title_payload};
    const hexFillOpacity = {opacity_payload};
    const legendItems = {legend_payload};
    const map = L.map('map', {{ preferCanvas: true }}).setView(defaultCenter, {int(zoom)});

    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
    }});

    function styleFeature(feature) {{
      const props = feature.properties || {{}};
      const fill = mode === 'factor' ? props.factor_fill : props.cluster_fill;
      return {{
        color: mode === 'factor' ? '#666666' : '#444444',
        weight: mode === 'factor' ? 0.25 : 0.35,
        opacity: Math.min(0.85, hexFillOpacity + 0.1),
        fillColor: fill || '#999999',
        fillOpacity: hexFillOpacity
      }};
    }}

    const landscape = L.geoJSON(data, {{
      style: styleFeature,
      onEachFeature: function(feature, layer) {{
        const props = feature.properties || {{}};
        layer.bindPopup(props.popup || props.hex_id || mapTitle);
      }}
    }}).addTo(map);

    const overlays = {{}};
    overlays[mapTitle] = landscape;
    L.control.layers({{ 'OSM': osm, 'Satellite': satellite }}, overlays, {{ collapsed: false }}).addTo(map);

    const note = L.control({{ position: 'topright' }});
    note.onAdd = function() {{
      const div = L.DomUtil.create('div', 'map-note');
      div.innerHTML = '<strong>' + mapTitle + '</strong><br>' + (mode === 'factor' ? 'Faktorscore från manifest.' : 'Kluster från manifest.');
      L.DomEvent.disableClickPropagation(div);
      return div;
    }};
    note.addTo(map);

    if (legendItems.length > 0) {{
      const legend = L.control({{ position: 'bottomright' }});
      legend.onAdd = function() {{
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = '<div class="map-legend-title">' + mapTitle + '</div>' +
          legendItems.map(function(item) {{
            return '<div class="map-legend-row"><span class="map-legend-swatch" style="background:' + item.color + '"></span><span>' + item.label + '</span></div>';
          }}).join('');
        L.DomEvent.disableClickPropagation(div);
        return div;
      }};
      legend.addTo(map);
    }}

    function fitInitialBounds() {{
      map.invalidateSize();
      if (defaultBounds && defaultBounds.length === 2) {{
        map.fitBounds(defaultBounds, {{ padding: [18, 18] }});
        return;
      }}
      const dataBounds = landscape.getBounds();
      if (dataBounds && dataBounds.isValid()) {{
        map.fitBounds(dataBounds.pad(0.04));
      }}
    }}
    setTimeout(fitInitialBounds, 80);
  </script>
</body>
</html>
"""


def build_layered_hex_map_html(
    layers: list[dict[str, Any]],
    center: list[float],
    zoom: int,
    bounds: list[list[float]] | None = None,
    fill_opacity: float = 0.78,
) -> str:
    layers_payload = json.dumps(layers, ensure_ascii=False)
    center_payload = json.dumps(center)
    bounds_payload = json.dumps(bounds)
    opacity_payload = json.dumps(max(0.0, min(1.0, float(fill_opacity))))
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    #map {{ min-height: 720px; border-radius: 8px; overflow: hidden; }}
    .leaflet-control-layers, .map-note, .map-legend {{ font-family: sans-serif; font-size: 12px; }}
    .map-note, .map-legend {{ background: rgba(255,255,255,0.94); padding: 9px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); max-width: 280px; }}
    .map-legend {{ line-height: 1.25; max-height: 420px; overflow-y: auto; }}
    .map-legend-title {{ font-weight: 700; margin-bottom: 7px; }}
    .map-legend-section {{ font-weight: 700; margin: 7px 0 4px; }}
    .map-legend-row {{ display: flex; align-items: center; gap: 6px; margin: 4px 0; }}
    .map-legend-swatch {{ width: 14px; height: 14px; border: 1px solid rgba(0,0,0,0.22); flex: 0 0 auto; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const layerSpecs = {layers_payload};
    const defaultCenter = {center_payload};
    const defaultBounds = {bounds_payload};
    const hexFillOpacity = {opacity_payload};
    const map = L.map('map', {{ preferCanvas: true }}).setView(defaultCenter, {int(zoom)});

    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
    }});

    function styleFor(fillProperty) {{
      return function(feature) {{
        const props = feature.properties || {{}};
        const fill = props[fillProperty] || props.fill || props.cluster_fill || props.factor_fill || '#999999';
        return {{
          color: '#555555',
          weight: 0.25,
          opacity: Math.min(0.85, hexFillOpacity + 0.1),
          fillColor: fill,
          fillOpacity: hexFillOpacity
        }};
      }};
    }}

    const overlays = {{}};
    const renderedLayers = [];
    layerSpecs.forEach(function(spec) {{
      const layer = L.geoJSON(spec.feature_collection, {{
        style: styleFor(spec.fill_property || 'fill'),
        onEachFeature: function(feature, itemLayer) {{
          const props = feature.properties || {{}};
          itemLayer.bindPopup(props.popup || props.hex_id || spec.name);
        }}
      }});
      overlays[spec.name] = layer;
      renderedLayers.push(layer);
      if (spec.default_visible !== false) {{
        layer.addTo(map);
      }}
    }});

    L.control.layers({{ 'OSM': osm, 'Satellite': satellite }}, overlays, {{ collapsed: false }}).addTo(map);

    const note = L.control({{ position: 'topright' }});
    note.onAdd = function() {{
      const div = L.DomUtil.create('div', 'map-note');
      div.innerHTML = '<strong>Samlad potential</strong><br>Aktiva lager styrs i appen och kan även slås av/på i kartkontrollen.';
      L.DomEvent.disableClickPropagation(div);
      return div;
    }};
    note.addTo(map);

    const legendById = {{}};
    layerSpecs.forEach(function(spec) {{
      if (!(spec.legend_items && spec.legend_items.length > 0)) {{
        return;
      }}
      const legendId = spec.legend_id || spec.name;
      if (!legendById[legendId]) {{
        legendById[legendId] = {{
          title: spec.legend_title || spec.name,
          items: spec.legend_items
        }};
      }}
    }});
    const legendSections = Object.values(legendById);
    if (legendSections.length > 0) {{
      const legend = L.control({{ position: 'bottomright' }});
      legend.onAdd = function() {{
        const div = L.DomUtil.create('div', 'map-legend');
        let html = '<div class="map-legend-title">Teckenförklaring</div>';
        legendSections.forEach(function(section) {{
          html += '<div class="map-legend-section">' + section.title + '</div>';
          html += section.items.map(function(item) {{
            return '<div class="map-legend-row"><span class="map-legend-swatch" style="background:' + item.color + '"></span><span>' + item.label + '</span></div>';
          }}).join('');
        }});
        div.innerHTML = html;
        L.DomEvent.disableClickPropagation(div);
        return div;
      }};
      legend.addTo(map);
    }}

    function fitInitialBounds() {{
      map.invalidateSize();
      if (defaultBounds && defaultBounds.length === 2) {{
        map.fitBounds(defaultBounds, {{ padding: [18, 18] }});
        return;
      }}
      const group = L.featureGroup(renderedLayers);
      const dataBounds = group.getBounds();
      if (dataBounds && dataBounds.isValid()) {{
        map.fitBounds(dataBounds.pad(0.04));
      }}
    }}
    setTimeout(fitInitialBounds, 80);
  </script>
</body>
</html>
"""


def build_potential_map_html(
    feature_collection: dict[str, Any],
    center: list[float],
    zoom: int,
    title: str,
    bounds: list[list[float]] | None = None,
    fill_opacity: float = 0.78,
    legend_items: list[dict[str, str]] | None = None,
) -> str:
    payload = json.dumps(feature_collection, ensure_ascii=False)
    center_payload = json.dumps(center)
    bounds_payload = json.dumps(bounds)
    title_payload = json.dumps(title, ensure_ascii=False)
    opacity_payload = json.dumps(max(0.0, min(1.0, float(fill_opacity))))
    legend_payload = json.dumps(legend_items or [], ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    #map {{ min-height: 720px; border-radius: 8px; overflow: hidden; }}
    .leaflet-control-layers, .map-note, .map-legend {{ font-family: sans-serif; font-size: 12px; }}
    .map-note {{ background: rgba(255,255,255,0.94); padding: 8px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); max-width: 260px; }}
    .map-legend {{ background: rgba(255,255,255,0.94); padding: 9px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.2); line-height: 1.25; max-width: 260px; }}
    .map-legend-title {{ font-weight: 700; margin-bottom: 6px; }}
    .map-legend-row {{ display: flex; align-items: center; gap: 6px; margin: 4px 0; }}
    .map-legend-swatch {{ width: 14px; height: 14px; border: 1px solid rgba(0,0,0,0.22); flex: 0 0 auto; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const data = {payload};
    const defaultCenter = {center_payload};
    const defaultBounds = {bounds_payload};
    const mapTitle = {title_payload};
    const hexFillOpacity = {opacity_payload};
    const legendItems = {legend_payload};
    const map = L.map('map', {{ preferCanvas: true }}).setView(defaultCenter, {int(zoom)});

    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
    }});

    function styleFeature(feature) {{
      const props = feature.properties || {{}};
      return {{
        color: '#555555',
        weight: 0.25,
        opacity: Math.min(0.85, hexFillOpacity + 0.1),
        fillColor: props.fill || '#999999',
        fillOpacity: hexFillOpacity
      }};
    }}

    const potential = L.geoJSON(data, {{
      style: styleFeature,
      onEachFeature: function(feature, layer) {{
        const props = feature.properties || {{}};
        layer.bindPopup(props.popup || props.hex_id || mapTitle);
      }}
    }}).addTo(map);

    const overlays = {{}};
    overlays[mapTitle] = potential;
    L.control.layers({{ 'OSM': osm, 'Satellite': satellite }}, overlays, {{ collapsed: false }}).addTo(map);

    const note = L.control({{ position: 'topright' }});
    note.onAdd = function() {{
      const div = L.DomUtil.create('div', 'map-note');
      div.innerHTML = '<strong>' + mapTitle + '</strong><br>Manifestdriven H3-kapacitetsmodell. Detaljerade vektorer kopplas in senare.';
      L.DomEvent.disableClickPropagation(div);
      return div;
    }};
    note.addTo(map);

    if (legendItems.length > 0) {{
      const legend = L.control({{ position: 'bottomright' }});
      legend.onAdd = function() {{
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = '<div class="map-legend-title">' + mapTitle + '</div>' +
          legendItems.map(function(item) {{
            return '<div class="map-legend-row"><span class="map-legend-swatch" style="background:' + item.color + '"></span><span>' + item.label + '</span></div>';
          }}).join('');
        L.DomEvent.disableClickPropagation(div);
        return div;
      }};
      legend.addTo(map);
    }}

    function fitInitialBounds() {{
      map.invalidateSize();
      if (defaultBounds && defaultBounds.length === 2) {{
        map.fitBounds(defaultBounds, {{ padding: [18, 18] }});
        return;
      }}
      const dataBounds = potential.getBounds();
      if (dataBounds && dataBounds.isValid()) {{
        map.fitBounds(dataBounds.pad(0.04));
      }}
    }}
    setTimeout(fitInitialBounds, 80);
  </script>
</body>
</html>
"""
