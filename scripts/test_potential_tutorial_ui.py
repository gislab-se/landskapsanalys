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
TUTORIAL_STORAGE_KEY = "potential_tutorial_trondelag_v1_dismissed"


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
['Geografier', 'Landskapspotential Vind', 'Landskapspotential Sol', 'Befolkning och bebyggelse', 'Använd ändringar', 'Visa guide'].forEach((label) => {
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
return {
  count: count ? count.textContent.trim() : '',
  title: title ? title.textContent.trim() : '',
  highlight: rect(highlight),
  popover: rect(popover),
  sidebar: rect(sidebar),
  map: rect(mapFrame),
  details: allDetails,
  labels,
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
    WebDriverWait(driver, timeout).until(
        lambda current: current.execute_script("return !!document.querySelector('#potential-tutorial-root .pt-highlight')")
    )


def _snapshot(driver: webdriver.Remote) -> dict[str, Any]:
    data = driver.execute_script(_rect_script())
    if not data or not data.get("highlight"):
        raise AssertionError("Tutorial highlight was not found.")
    return data


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
):
    def check(data: dict[str, Any]) -> None:
        _is_map_highlight(data, require_corner_or_full=require_corner_or_full)
        _assert_similar_highlight(data["highlight"], expected, label)

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
        driver.execute_script(f"window.localStorage.removeItem({TUTORIAL_STORAGE_KEY!r});")
        driver.refresh()
        _wait_for_tutorial(driver, timeout)

        _navigate_to_title(driver, "Läs resultatet i kartan", timeout)
        step5 = _wait_for_checked_state(
            driver,
            "Läs resultatet i kartan",
            timeout,
            lambda data: _is_map_highlight(data, require_corner_or_full=True),
        )
        _print_snapshot(step5)

        _click(driver, "#potential-tutorial-root .pt-next")
        step6 = _wait_for_checked_state(
            driver,
            "Grönt är ett öppet startläge",
            timeout,
            _is_map_highlight,
        )
        _print_snapshot(step6)

        _close_sidebar_expanders(driver)
        _click(driver, "#potential-tutorial-root .pt-next")
        step7 = _wait_for_checked_state(
            driver,
            "Vind och sol styrs under Geografier",
            timeout,
            _assert_step7,
        )
        _print_snapshot(step7)

        _click(driver, "#potential-tutorial-root .pt-prev")
        back6 = _wait_for_checked_state(
            driver,
            "Grönt är ett öppet startläge",
            timeout,
            _similar_map_checker(step6["highlight"], "Step 6 previous-navigation"),
        )
        _print_snapshot(back6)

        _click(driver, "#potential-tutorial-root .pt-prev")
        back5 = _wait_for_checked_state(
            driver,
            "Läs resultatet i kartan",
            timeout,
            _similar_map_checker(
                step5["highlight"],
                "Step 5 previous-navigation",
                require_corner_or_full=True,
            ),
        )
        _print_snapshot(back5)

        _click(driver, "#potential-tutorial-root .pt-next")
        _wait_for_checked_state(
            driver,
            "Grönt är ett öppet startläge",
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
