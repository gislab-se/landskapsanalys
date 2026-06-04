from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_URL = "http://localhost:8505"
TUTORIAL_STORAGE_KEY = "potential_tutorial_trondelag_v2_dismissed"
TUTORIAL_STORAGE_KEYS = [
    "potential_tutorial_trondelag_v1_dismissed",
    TUTORIAL_STORAGE_KEY,
]
SCENARIO_ALLOCATION_LAYER_LABEL = "Scenariof\u00f6rdelning i etableringshex"
OUTSIDE_LP_NEED_LAYER_LABEL = "Ytbehov utanf\u00f6r landskapets potential"


@dataclass
class StepSnapshot:
    count: str
    title: str
    highlight: dict[str, float]
    sidebar: dict[str, float] | None
    map_rect: dict[str, float] | None
    location: str


def _rect_script() -> str:
    return r"""
const rect = (node) => {
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {
    left: r.left, top: r.top, right: r.right, bottom: r.bottom,
    width: r.width, height: r.height,
    cx: r.left + r.width / 2, cy: r.top + r.height / 2
  };
};
const visible = (node) => {
  const r = rect(node);
  return !!r && r.width > 2 && r.height > 2;
};
const overlap = (a, b) => {
  if (!a || !b) return 0;
  const left = Math.max(a.left, b.left);
  const right = Math.min(a.right, b.right);
  const top = Math.max(a.top, b.top);
  const bottom = Math.min(a.bottom, b.bottom);
  return Math.max(0, right - left) * Math.max(0, bottom - top);
};
const sidebar = document.querySelector('section[data-testid="stSidebar"]');
const rightPanel = document.querySelector('div[data-testid="column"]:has(#right-panel-content-anchor)');
const frames = Array.from(document.querySelectorAll('iframe'))
  .map((iframe) => {
    const container = iframe.closest('div[data-testid="stIFrame"]') || iframe;
    const itemRect = rect(container);
    const visibleLeft = itemRect ? Math.max(0, itemRect.left) : 0;
    const visibleTop = itemRect ? Math.max(0, itemRect.top) : 0;
    const visibleRight = itemRect ? Math.min(window.innerWidth, itemRect.right) : 0;
    const visibleBottom = itemRect ? Math.min(window.innerHeight, itemRect.bottom) : 0;
    const visibleArea = Math.max(0, visibleRight - visibleLeft) * Math.max(0, visibleBottom - visibleTop);
    return { iframe, container, rect: itemRect, visibleArea, inSidebar: !!container.closest('section[data-testid="stSidebar"]') };
  })
  .filter((item) => item.rect && item.rect.height > 220 && item.rect.width > 220 && item.visibleArea > 50000 && !item.inSidebar)
  .sort((a, b) => b.visibleArea - a.visibleArea);
const mapFrame = frames.length ? frames[0].container : null;
const highlight = document.querySelector('#potential-tutorial-root .pt-highlight');
const popover = document.querySelector('#potential-tutorial-root .pt-popover');
const count = document.querySelector('#potential-tutorial-root .pt-count');
const title = document.querySelector('#potential-tutorial-root h2');
const allDetails = Array.from((sidebar || document).querySelectorAll('details')).map((node) => {
  const summary = node.querySelector('summary');
  return { text: (summary ? summary.textContent : node.textContent || '').replace(/\s+/g, ' ').trim(), open: node.open, rect: rect(node) };
});
const labels = {};
['Geografier', 'Landskapspotential Vind', 'Landskapspotential Sol', 'Befolkning och bebyggelse', 'Använd ändringar', 'Social acceptans', 'Visa guide'].forEach((label) => {
  const wanted = label.toLowerCase();
  const details = Array.from(document.querySelectorAll('details')).find((node) => {
    const summary = node.querySelector('summary');
    const text = (summary ? summary.textContent : node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return text === wanted || text.includes(wanted);
  });
  const button = Array.from(document.querySelectorAll('button')).find((node) => {
    const text = (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return visible(node) && (text === wanted || text.includes(wanted));
  });
  labels[label] = rect(details || button);
});
const findScopedLabel = (scope, label) => {
  if (!scope) return null;
  const wanted = label.toLowerCase();
  const details = Array.from(scope.querySelectorAll('details')).find((node) => {
    const summary = node.querySelector('summary');
    const text = (summary ? summary.textContent : node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return text === wanted || text.includes(wanted);
  });
  const button = Array.from(scope.querySelectorAll('button')).find((node) => {
    const text = (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return visible(node) && (text === wanted || text.includes(wanted));
  });
  const heading = Array.from(scope.querySelectorAll('h1,h2,h3,h4,h5,h6,summary,p,li')).find((node) => {
    const text = (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    return visible(node) && (text === wanted || text.includes(wanted));
  });
  return details || button || heading || null;
};
const rightLabels = {};
['Geografier', 'Landskapspotential Vind', 'Landskapspotential Sol'].forEach((label) => {
  rightLabels[label] = rect(findScopedLabel(rightPanel, label));
});
rightLabels['Geografier'] = rect(document.querySelector('[data-potential-tutorial-anchor="right-geographies"]')) || rightLabels['Geografier'];
const legendSections = {};
let legendOverall = null;
const combineRects = (rects) => {
  const visibleRects = rects.filter((item) => item && item.width > 2 && item.height > 2);
  if (!visibleRects.length) return null;
  const left = Math.min(...visibleRects.map((item) => item.left));
  const top = Math.min(...visibleRects.map((item) => item.top));
  const right = Math.max(...visibleRects.map((item) => item.right));
  const bottom = Math.max(...visibleRects.map((item) => item.bottom));
  return {
    left, top, right, bottom,
    width: right - left, height: bottom - top,
    cx: left + (right - left) / 2, cy: top + (bottom - top) / 2
  };
};
if (frames.length) {
  try {
    const iframe = frames[0].iframe;
    const frameRect = iframe.getBoundingClientRect();
    const doc = iframe.contentDocument;
    const legendRect = rect(doc.querySelector('.map-legend'));
    if (legendRect) {
      const left = frameRect.left + legendRect.left;
      const top = frameRect.top + legendRect.top;
      const right = frameRect.left + legendRect.right;
      const bottom = frameRect.top + legendRect.bottom;
      legendOverall = {
        left, top, right, bottom,
        width: right - left, height: bottom - top,
        cx: left + (right - left) / 2, cy: top + (bottom - top) / 2
      };
    }
    ['Potentiell etableringsyta', 'Scenariofördelning i etableringshex', 'Ytbehov utanför landskapets potential'].forEach((label) => {
      const wanted = label.toLowerCase();
      const heading = Array.from(doc.querySelectorAll('.map-legend-section')).find((node) => {
        const text = (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
        return text === wanted;
      });
      if (!heading) {
        legendSections[label] = null;
        return;
      }
      const nodes = [heading];
      let next = heading.nextElementSibling;
      while (next && !next.classList.contains('map-legend-section')) {
        if (next.classList.contains('map-legend-row')) {
          nodes.push(next);
        }
        next = next.nextElementSibling;
      }
      const sectionRect = combineRects(nodes.map(rect));
      if (!sectionRect) {
        legendSections[label] = null;
        return;
      }
      const left = frameRect.left + sectionRect.left;
      const top = frameRect.top + sectionRect.top;
      const right = frameRect.left + sectionRect.right;
      const bottom = frameRect.top + sectionRect.bottom;
      legendSections[label] = {
        left, top, right, bottom,
        width: right - left, height: bottom - top,
        cx: left + (right - left) / 2, cy: top + (bottom - top) / 2
      };
    });
  } catch (error) {
    legendSections.error = String(error);
  }
}
return {
  count: count ? count.textContent.trim() : '',
  title: title ? title.textContent.trim() : '',
  highlight: rect(highlight),
  popover: rect(popover),
  sidebar: rect(sidebar),
  rightPanel: rect(rightPanel),
  table: rect(document.querySelector('[data-potential-tutorial-anchor="results-table"]')),
  landscapeDistribution: rect(document.querySelector('[data-potential-tutorial-anchor="landscape-distribution"]')),
  map: rect(mapFrame),
  details: allDetails,
  labels,
  rightLabels,
  legendOverall,
  legendSections,
  frames: frames.map((item) => ({
    rect: item.rect,
    visibleArea: item.visibleArea,
    title: item.iframe.getAttribute('title') || '',
    src: item.iframe.getAttribute('src') || ''
  })),
  overlapHighlightSidebar: overlap(rect(highlight), rect(sidebar)),
  overlapHighlightMap: overlap(rect(highlight), rect(mapFrame))
};
"""


def _make_driver(headed: bool) -> webdriver.Remote:
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--window-size=2048,1200")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    if not headed:
        chrome_options.add_argument("--headless=new")
    try:
        return webdriver.Chrome(options=chrome_options)
    except WebDriverException as chrome_error:
        edge_options = EdgeOptions()
        edge_options.add_argument("--window-size=2048,1200")
        edge_options.add_argument("--disable-gpu")
        if not headed:
            edge_options.add_argument("--headless=new")
        try:
            return webdriver.Edge(options=edge_options)
        except WebDriverException as edge_error:
            raise RuntimeError(
                "Could not start Chrome or Edge through Selenium. "
                f"Chrome error: {chrome_error}; Edge error: {edge_error}"
            ) from edge_error


def _wait_for_tutorial(driver: webdriver.Remote, timeout: int) -> None:
    try:
        WebDriverWait(driver, timeout).until(
            lambda current: current.execute_script(
                r"""
const root = document.querySelector('#potential-tutorial-root');
const highlight = document.querySelector('#potential-tutorial-root .pt-highlight');
const title = document.querySelector('#potential-tutorial-root h2');
if (!root || !highlight || !title || getComputedStyle(root).display === 'none') {
  return false;
}
const rect = highlight.getBoundingClientRect();
return rect.width > 2 && rect.height > 2 && title.textContent.trim().length > 0;
"""
            )
        )
    except TimeoutException as error:
        state = driver.execute_script(
            r"""
return {
  root: !!document.querySelector('#potential-tutorial-root'),
  title: (document.querySelector('#potential-tutorial-root h2') || {}).textContent || '',
  dismissedV1: window.localStorage.getItem('potential_tutorial_trondelag_v1_dismissed'),
  dismissedV2: window.localStorage.getItem('potential_tutorial_trondelag_v2_dismissed')
};
"""
        )
        raise AssertionError(f"Tutorial did not open in time. State: {json.dumps(state, sort_keys=True)}") from error


def _snapshot(driver: webdriver.Remote) -> dict[str, Any]:
    data = driver.execute_script(_rect_script())
    if not data or not data.get("highlight"):
        raise AssertionError("Tutorial highlight was not found.")
    return data


def _overlay_state(driver: webdriver.Remote, layer_name: str) -> dict[str, Any]:
    return driver.execute_script(
        r"""
const wanted = String(arguments[0] || '');
const frames = Array.from(document.querySelectorAll("iframe"))
  .map((iframe) => {
    const container = iframe.closest('div[data-testid="stIFrame"]') || iframe;
    const rect = container.getBoundingClientRect();
    const visibleLeft = Math.max(0, rect.left);
    const visibleTop = Math.max(0, rect.top);
    const visibleRight = Math.min(window.innerWidth, rect.right);
    const visibleBottom = Math.min(window.innerHeight, rect.bottom);
    const visibleArea = Math.max(0, visibleRight - visibleLeft) * Math.max(0, visibleBottom - visibleTop);
    return { iframe, container, rect, visibleArea };
  })
  .filter((item) => item.rect.width > 220 && item.rect.height > 220 && item.visibleArea > 50000 && !item.container.closest('section[data-testid="stSidebar"]'))
  .sort((a, b) => b.visibleArea - a.visibleArea);
if (!frames.length) {
  return { available: false, visible: false, featureCount: 0, reason: "no-map-frame" };
}
const mapWindow = frames[0].iframe.contentWindow;
if (!mapWindow || typeof mapWindow.__potentialMapOverlayVisible !== "function") {
  return { available: false, visible: false, featureCount: 0, reason: "no-overlay-api" };
}
return {
  available: true,
  known: typeof mapWindow.__potentialMapOverlayKnown === "function" ? Boolean(mapWindow.__potentialMapOverlayKnown(wanted)) : true,
  visible: Boolean(mapWindow.__potentialMapOverlayVisible(wanted)),
  featureCount: Number(mapWindow.__potentialMapOverlayFeatureCount(wanted) || 0),
  reason: ""
};
""",
        layer_name,
    )


def _wait_for_overlay_layout(driver: webdriver.Remote) -> None:
    try:
        driver.execute_async_script(
            "const done = arguments[0]; requestAnimationFrame(() => requestAnimationFrame(() => done()));"
        )
    except WebDriverException:
        time.sleep(0.2)


def _click(driver: webdriver.Remote, selector: str) -> None:
    driver.execute_script(
        "const node = document.querySelector(arguments[0]); if (!node) throw new Error('Missing ' + arguments[0]); node.click();",
        selector,
    )
    _wait_for_overlay_layout(driver)


def _clear_tutorial_storage(driver: webdriver.Remote) -> None:
    driver.execute_script(
        "for (const key of arguments[0]) for (const suffix of ['', ':progress', ':paused', ':actions']) window.localStorage.removeItem(key + suffix);",
        TUTORIAL_STORAGE_KEYS,
    )


def _click_button_by_text(driver: webdriver.Remote, label: str) -> None:
    button = WebDriverWait(driver, 20).until(
        lambda current: current.execute_script(
            r"""
const wanted = String(arguments[0] || '').replace(/\s+/g, ' ').trim().toLowerCase();
const visible = (node) => {
  if (!node || !node.getBoundingClientRect) return false;
  const style = getComputedStyle(node);
  const rect = node.getBoundingClientRect();
  return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
};
const button = Array.from(document.querySelectorAll('button')).find((node) => {
  const text = (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  return visible(node) && (text === wanted || text.includes(wanted));
});
return button || null;
""",
            label,
        )
    )
    button.click()
    _wait_for_overlay_layout(driver)


def _wait_for_title(driver: webdriver.Remote, title: str, timeout: int) -> dict[str, Any]:
    def ready(current: webdriver.Remote) -> dict[str, Any] | bool:
        data = _snapshot(current)
        return data if data.get("title") == title else False

    return WebDriverWait(driver, timeout).until(ready)


def _wait_for_checked_state(
    driver: webdriver.Remote,
    title: str,
    timeout: int,
    check,
) -> dict[str, Any]:
    last_error: AssertionError | None = None

    def ready(current: webdriver.Remote) -> dict[str, Any] | bool:
        nonlocal last_error
        data = _snapshot(current)
        if data.get("title") != title:
            return False
        try:
            check(data)
        except AssertionError as error:
            last_error = error
            return False
        return data

    try:
        return WebDriverWait(driver, timeout).until(ready)
    except TimeoutException:
        if last_error:
            raise last_error
        raise


def _navigate_to_title(driver: webdriver.Remote, title: str, timeout: int, max_clicks: int = 12) -> dict[str, Any]:
    for _ in range(max_clicks):
        data = _snapshot(driver)
        if data.get("title") == title:
            return data
        _click(driver, "#potential-tutorial-root .pt-next")
        time.sleep(0.35)
    return _wait_for_title(driver, title, timeout)


def _assert_pause_resume(driver: webdriver.Remote, timeout: int) -> None:
    before = _snapshot(driver)
    _click(driver, "#potential-tutorial-root .pt-pause")
    WebDriverWait(driver, timeout).until(
        lambda current: current.execute_script(
            r"""
const root = document.querySelector('#potential-tutorial-root');
const resume = document.querySelector('#potential-tutorial-resume');
return !!root && !!resume && getComputedStyle(root).display === 'none';
"""
        )
    )
    _click(driver, "#potential-tutorial-resume")
    _wait_for_tutorial(driver, timeout)
    after = _snapshot(driver)
    if after.get("title") != before.get("title"):
        raise AssertionError(f"Tutorial resumed on {after.get('title')!r}, expected {before.get('title')!r}.")


def _assert_manual_reopen_after_auto_dismissal(driver: webdriver.Remote, timeout: int) -> None:
    _wait_for_tutorial(driver, timeout)
    _click(driver, "#potential-tutorial-root .pt-checkbox input")
    _click(driver, "#potential-tutorial-root .pt-close")
    WebDriverWait(driver, timeout).until(
        lambda current: current.execute_script(
            r"""
const root = document.querySelector('#potential-tutorial-root');
return !root || getComputedStyle(root).display === 'none';
"""
        )
    )
    dismissed = driver.execute_script("return window.localStorage.getItem(arguments[0]);", TUTORIAL_STORAGE_KEY)
    if dismissed != "1":
        raise AssertionError(f"Expected tutorial dismissed preference to be saved, got {dismissed!r}.")
    driver.refresh()
    WebDriverWait(driver, timeout).until(
        lambda current: current.execute_script(
            r"""
const root = document.querySelector('#potential-tutorial-root');
return !root || getComputedStyle(root).display === 'none';
"""
        )
    )
    _click_button_by_text(driver, "Visa guide")
    _wait_for_tutorial(driver, timeout)
    reopened = _snapshot(driver)
    if reopened.get("title") != "Hitta potential för ny vind och sol":
        raise AssertionError(f"Guide reopened on {reopened.get('title')!r}, expected first step.")


def _wait_for_action_state(driver: webdriver.Remote, state: str, timeout: int) -> str:
    def ready(current: webdriver.Remote) -> str | bool:
        value = current.execute_script(
            r"""
const node = document.querySelector('#potential-tutorial-root .pt-action-status');
if (!node || node.hidden || node.dataset.state !== arguments[0]) {
  return false;
}
return node.textContent.trim();
""",
            state,
        )
        return value or False

    return WebDriverWait(driver, timeout).until(ready)


def _close_sidebar_expanders(driver: webdriver.Remote) -> None:
    driver.execute_script(
        r"""
const sidebar = document.querySelector('section[data-testid="stSidebar"]');
Array.from((sidebar || document).querySelectorAll('details')).forEach((node) => {
  if (node.open) {
    node.open = false;
    node.dispatchEvent(new Event('toggle', { bubbles: true }));
  }
});
"""
    )


def _inside(rect: dict[str, float], container: dict[str, float]) -> bool:
    return (
        rect["cx"] >= container["left"]
        and rect["cx"] <= container["right"]
        and rect["cy"] >= container["top"]
        and rect["cy"] <= container["bottom"]
    )


def _overlap_area(a: dict[str, float], b: dict[str, float] | None) -> float:
    if not a or not b:
        return 0.0
    left = max(a["left"], b["left"])
    right = min(a["right"], b["right"])
    top = max(a["top"], b["top"])
    bottom = min(a["bottom"], b["bottom"])
    return max(0.0, right - left) * max(0.0, bottom - top)


def _assert_similar_highlight(
    actual: dict[str, float],
    expected: dict[str, float],
    label: str,
    tolerance: float = 24.0,
) -> None:
    for key in ("left", "top", "width", "height"):
        if abs(actual[key] - expected[key]) > tolerance:
            raise AssertionError(
                f"{label} did not return to the same highlight. "
                f"Expected {json.dumps(expected, sort_keys=True)}, got {json.dumps(actual, sort_keys=True)}"
            )


def _similar_map_checker(
    expected: dict[str, float],
    label: str,
    *,
    require_corner_or_full: bool = False,
    tolerance: float = 24.0,
):
    def check(data: dict[str, Any]) -> None:
        _is_map_highlight(data, require_corner_or_full=require_corner_or_full)
        _assert_similar_highlight(data["highlight"], expected, label, tolerance=tolerance)

    return check


def _classify(data: dict[str, Any]) -> str:
    highlight = data["highlight"]
    sidebar = data.get("sidebar")
    map_rect = data.get("map")
    if sidebar and _inside(highlight, sidebar):
        return "sidebar"
    if map_rect and _overlap_area(highlight, map_rect) > 0:
        return "map"
    return "other"


def _is_map_highlight(data: dict[str, Any], *, require_corner_or_full: bool = False) -> None:
    highlight = data["highlight"]
    map_rect = data.get("map")
    sidebar = data.get("sidebar")
    if not map_rect:
        raise AssertionError("Map iframe/container was not found.")
    if sidebar and _overlap_area(highlight, sidebar) > max(20.0, highlight["width"] * highlight["height"] * 0.05):
        raise AssertionError(f"Highlight overlaps the sidebar for {data['title']}: {json.dumps(highlight)}")
    map_overlap = _overlap_area(highlight, map_rect)
    if map_overlap <= max(20.0, highlight["width"] * highlight["height"] * 0.15):
        raise AssertionError(f"Highlight is not in the map for {data['title']}: {json.dumps(highlight)}")
    if require_corner_or_full:
        covers_most_map = highlight["width"] >= map_rect["width"] * 0.72 and highlight["height"] >= map_rect["height"] * 0.72
        in_lower_right = (
            highlight["cx"] >= map_rect["left"] + map_rect["width"] * 0.55
            and highlight["cy"] >= map_rect["top"] + map_rect["height"] * 0.50
        )
        if not (covers_most_map or in_lower_right):
            raise AssertionError(
                "Step 5 highlight is in the map but not near the legend/lower-right corner "
                f"and not a whole-map fallback: {json.dumps(highlight)}"
            )


def _assert_legend_step(data: dict[str, Any], title: str, section_label: str, *, allow_legend_fallback: bool = False) -> None:
    if data.get("title") != title:
        raise AssertionError(f"Expected {title!r}, got {data.get('title')!r}.")
    section = (data.get("legendSections") or {}).get(section_label)
    if not section:
        if not allow_legend_fallback:
            raise AssertionError(f"Legend section {section_label!r} was not found.")
        legend = data.get("legendOverall")
        if not legend:
            raise AssertionError(f"Legend section {section_label!r} and legend fallback were not found.")
        if _overlap_area(data["highlight"], legend) <= max(20.0, legend["width"] * legend["height"] * 0.15):
            raise AssertionError(f"{title} highlight does not cover the map legend fallback.")
        return
    highlight = data["highlight"]
    overlap_area = _overlap_area(highlight, section)
    section_area = section["width"] * section["height"]
    if overlap_area < max(20.0, section_area * 0.30):
        raise AssertionError(
            f"{title} highlight does not cover legend section {section_label!r}: "
            f"highlight={json.dumps(highlight, sort_keys=True)} section={json.dumps(section, sort_keys=True)}"
        )
    sidebar = data.get("sidebar")
    if sidebar and _overlap_area(highlight, sidebar) > 0:
        raise AssertionError(f"{title} highlight overlaps sidebar.")


def _assert_overlay_visible(driver: webdriver.Remote, layer_name: str, *, allow_missing: bool = False) -> None:
    state = _overlay_state(driver, layer_name)
    if not state.get("available"):
        raise AssertionError(f"Map overlay API is not available for {layer_name!r}: {state}")
    if allow_missing and not state.get("known"):
        print(f"SKIP optional overlay {layer_name!r}: layer is not present for the current scenario.")
        return
    if not state.get("visible"):
        raise AssertionError(f"Map overlay {layer_name!r} is not visible: {state}")
    if int(state.get("featureCount", 0) or 0) <= 0:
        raise AssertionError(f"Map overlay {layer_name!r} has no rendered features: {state}")


def _label_visible(data: dict[str, Any], label: str) -> bool:
    rect = (data.get("labels") or {}).get(label)
    return bool(rect and rect.get("width", 0) > 2 and rect.get("height", 0) > 2)


def _assert_step7(data: dict[str, Any]) -> None:
    if data.get("title") != "Vind och sol styrs under Geografier":
        raise AssertionError(f"Expected step 7 title, got {data.get('title')!r}.")
    for label in ["Geografier", "Landskapspotential Vind", "Landskapspotential Sol"]:
        if not _label_visible(data, label):
            raise AssertionError(f"{label!r} is not visible on step 7.")
    highlight = data["highlight"]
    wind = data["labels"]["Landskapspotential Vind"]
    solar = data["labels"]["Landskapspotential Sol"]
    if _overlap_area(highlight, wind) <= 0 or _overlap_area(highlight, solar) <= 0:
        raise AssertionError("Step 7 highlight does not cover both wind and solar potential controllers.")
    social = data["labels"].get("Social acceptans")
    if social and _overlap_area(highlight, social) > 0:
        raise AssertionError("Step 7 highlight overlaps Social acceptans.")


def _assert_step8(data: dict[str, Any]) -> None:
    if data.get("title") != "Ändra vindantaganden och använd dem":
        raise AssertionError(f"Expected step 8 title, got {data.get('title')!r}.")
    for label in ["Geografier", "Landskapspotential Vind", "Använd ändringar"]:
        if not _label_visible(data, label):
            raise AssertionError(f"{label!r} is not visible on step 8.")
    highlight = data["highlight"]
    apply_button = data["labels"]["Använd ändringar"]
    if _overlap_area(highlight, apply_button) <= 0:
        raise AssertionError("Step 8 highlight does not cover Använd ändringar.")


def _assert_table_step(data: dict[str, Any]) -> None:
    if data.get("title") != "Läs resultatet i tabellen":
        raise AssertionError(f"Expected table step title, got {data.get('title')!r}.")
    table = data.get("table")
    if not table:
        raise AssertionError("Result table anchor was not found.")
    overlap_area = _overlap_area(data["highlight"], table)
    if overlap_area < max(20.0, table["width"] * table["height"] * 0.30):
        raise AssertionError(
            "Table step highlight does not cover the result table: "
            f"highlight={json.dumps(data['highlight'], sort_keys=True)} table={json.dumps(table, sort_keys=True)}"
        )


def _assert_right_geographies_step(data: dict[str, Any]) -> None:
    if data.get("title") != "Geografier visar antagandena":
        raise AssertionError(f"Expected right-panel geographies step title, got {data.get('title')!r}.")
    label = (data.get("rightLabels") or {}).get("Geografier")
    if not label:
        raise AssertionError("Right-panel Geografier heading was not found.")
    if _overlap_area(data["highlight"], label) <= 0:
        raise AssertionError("Right-panel Geografier step highlight does not cover the heading.")


def _assert_landscape_distribution_step(data: dict[str, Any]) -> None:
    if data.get("title") != "Potential per landskapstyp":
        raise AssertionError(f"Expected landscape distribution step title, got {data.get('title')!r}.")
    target = data.get("landscapeDistribution")
    if not target:
        raise AssertionError("Landscape distribution anchor was not found.")
    if _overlap_area(data["highlight"], target) <= 0:
        raise AssertionError("Landscape distribution step highlight does not cover the group heading.")


def _print_snapshot(data: dict[str, Any]) -> None:
    snapshot = StepSnapshot(
        count=data.get("count", ""),
        title=data.get("title", ""),
        highlight=data["highlight"],
        sidebar=data.get("sidebar"),
        map_rect=data.get("map"),
        location=_classify(data),
    )
    print(
        f"{snapshot.count}: {snapshot.title} | highlight={snapshot.location} "
        f"box={json.dumps(snapshot.highlight, sort_keys=True)}"
    )
    if not snapshot.map_rect:
        print(f"  visible map frame candidates: {json.dumps(data.get('frames', []), sort_keys=True)}")


def run(url: str, headed: bool, timeout: int, screenshot_dir: Path | None) -> int:
    driver = _make_driver(headed=headed)
    try:
        driver.get(url)
        _clear_tutorial_storage(driver)
        driver.refresh()
        _wait_for_tutorial(driver, timeout)
        _assert_manual_reopen_after_auto_dismissal(driver, timeout)
        _assert_pause_resume(driver, timeout)

        _navigate_to_title(driver, "Potentiell etableringsyta", timeout)
        establishment = _wait_for_checked_state(
            driver,
            "Potentiell etableringsyta",
            timeout,
            lambda data: _assert_legend_step(data, "Potentiell etableringsyta", "Potentiell etableringsyta"),
        )
        _print_snapshot(establishment)

        _click(driver, "#potential-tutorial-root .pt-next")
        scenario = _wait_for_checked_state(
            driver,
            "Scenariofördelning i etableringshex",
            timeout,
            lambda data: _assert_legend_step(
                data,
                "Scenariofördelning i etableringshex",
                "Scenariofördelning i etableringshex",
                allow_legend_fallback=True,
            ),
        )
        _print_snapshot(scenario)
        _assert_overlay_visible(driver, SCENARIO_ALLOCATION_LAYER_LABEL)

        _click(driver, "#potential-tutorial-root .pt-next")
        outside_need = _wait_for_checked_state(
            driver,
            "Ytbehov utanför landskapets potential",
            timeout,
            lambda data: _assert_legend_step(
                data,
                "Ytbehov utanför landskapets potential",
                "Ytbehov utanför landskapets potential",
                allow_legend_fallback=True,
            ),
        )
        _print_snapshot(outside_need)
        _assert_overlay_visible(driver, OUTSIDE_LP_NEED_LAYER_LABEL, allow_missing=True)

        _click(driver, "#potential-tutorial-root .pt-next")
        green_start = _wait_for_checked_state(
            driver,
            "Startläget är försiktigt",
            timeout,
            _is_map_highlight,
        )
        _print_snapshot(green_start)

        _close_sidebar_expanders(driver)
        _click(driver, "#potential-tutorial-root .pt-next")
        controllers = _wait_for_checked_state(
            driver,
            "Vind och sol styrs under Geografier",
            timeout,
            _assert_step7,
        )
        _print_snapshot(controllers)
        _wait_for_action_state(driver, "todo", timeout)

        _click(driver, "#potential-tutorial-root .pt-next")
        apply_step = _wait_for_checked_state(
            driver,
            "Ändra vindantaganden och använd dem",
            timeout,
            _assert_step8,
        )
        _print_snapshot(apply_step)

        _click(driver, "#potential-tutorial-root .pt-prev")
        back_controllers = _wait_for_checked_state(
            driver,
            "Vind och sol styrs under Geografier",
            timeout,
            _assert_step7,
        )
        _print_snapshot(back_controllers)

        _click(driver, "#potential-tutorial-root .pt-prev")
        back_green = _wait_for_checked_state(
            driver,
            "Startläget är försiktigt",
            timeout,
            _is_map_highlight,
        )
        _print_snapshot(back_green)

        _click(driver, "#potential-tutorial-root .pt-prev")
        back_outside_need = _wait_for_checked_state(
            driver,
            "Ytbehov utanför landskapets potential",
            timeout,
            lambda data: _assert_legend_step(
                data,
                "Ytbehov utanför landskapets potential",
                "Ytbehov utanför landskapets potential",
                allow_legend_fallback=True,
            ),
        )
        _print_snapshot(back_outside_need)
        _assert_overlay_visible(driver, OUTSIDE_LP_NEED_LAYER_LABEL, allow_missing=True)

        _click(driver, "#potential-tutorial-root .pt-next")
        _wait_for_checked_state(
            driver,
            "Startläget är försiktigt",
            timeout,
            _is_map_highlight,
        )
        _close_sidebar_expanders(driver)
        _click(driver, "#potential-tutorial-root .pt-next")
        again7 = _wait_for_checked_state(
            driver,
            "Vind och sol styrs under Geografier",
            timeout,
            _assert_step7,
        )
        _print_snapshot(again7)

        _click(driver, "#potential-tutorial-root .pt-next")
        again8 = _wait_for_checked_state(
            driver,
            "Ändra vindantaganden och använd dem",
            timeout,
            _assert_step8,
        )
        _print_snapshot(again8)

        _click(driver, "#potential-tutorial-root .pt-next")
        table_step = _wait_for_checked_state(
            driver,
            "Läs resultatet i tabellen",
            timeout,
            _assert_table_step,
        )
        _print_snapshot(table_step)

        _click(driver, "#potential-tutorial-root .pt-next")
        right_geographies = _wait_for_checked_state(
            driver,
            "Geografier visar antagandena",
            timeout,
            _assert_right_geographies_step,
        )
        _print_snapshot(right_geographies)

        _click(driver, "#potential-tutorial-root .pt-next")
        landscape_distribution = _wait_for_checked_state(
            driver,
            "Potential per landskapstyp",
            timeout,
            _assert_landscape_distribution_step,
        )
        _print_snapshot(landscape_distribution)

        if screenshot_dir:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(screenshot_dir / "tutorial_ui_final.png"))
        print("PASS tutorial UI highlights stayed in the expected regions.")
        return 0
    except Exception as exc:
        if screenshot_dir:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            try:
                driver.save_screenshot(str(screenshot_dir / "tutorial_ui_failure.png"))
            except Exception:
                pass
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Potential App Trondelag tutorial highlight placement.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true", help="Run a visible browser instead of headless mode.")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    args = parser.parse_args()
    return run(args.url, args.headed, args.timeout, args.screenshot_dir)


if __name__ == "__main__":
    raise SystemExit(main())
