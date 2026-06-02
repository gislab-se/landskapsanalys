from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_URL = "http://localhost:8505"
DEFAULT_REPORT_DIR = Path("artifacts/ui_ux_review")
PRIORITY_ORDER = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Finding:
    priority: str
    title: str
    evidence: str
    recommendation: str
    viewport: str


def _make_driver(headed: bool) -> webdriver.Remote:
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--window-size=1600,1000")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    if not headed:
        chrome_options.add_argument("--headless=new")
    try:
        return webdriver.Chrome(options=chrome_options)
    except WebDriverException as chrome_error:
        edge_options = EdgeOptions()
        edge_options.add_argument("--window-size=1600,1000")
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


def _snapshot_script() -> str:
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
const visibleAreaInViewport = (itemRect) => {
  if (!itemRect) return 0;
  const visibleLeft = Math.max(0, itemRect.left);
  const visibleTop = Math.max(0, itemRect.top);
  const visibleRight = Math.min(window.innerWidth, itemRect.right);
  const visibleBottom = Math.min(window.innerHeight, itemRect.bottom);
  return Math.max(0, visibleRight - visibleLeft) * Math.max(0, visibleBottom - visibleTop);
};
const visible = (node) => {
  const r = rect(node);
  const style = window.getComputedStyle(node);
  return !!r && r.width > 2 && r.height > 2 && style.visibility !== 'hidden' && style.display !== 'none';
};
const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
const sidebar = document.querySelector('section[data-testid="stSidebar"]');
const bodyText = clean(document.body.innerText || '');
const sidebarText = clean(sidebar ? sidebar.innerText || '' : '');
const headings = Array.from(document.querySelectorAll('h1,h2,h3,[data-testid="stHeading"]'))
  .filter(visible)
  .map((node) => ({ text: clean(node.innerText || node.textContent || ''), rect: rect(node) }))
  .filter((item) => item.text);
const details = Array.from(document.querySelectorAll('details'))
  .filter(visible)
  .map((node) => {
    const summary = node.querySelector('summary');
    return {
      text: clean(summary ? summary.innerText || summary.textContent || '' : node.innerText || node.textContent || ''),
      open: !!node.open,
      inSidebar: !!node.closest('section[data-testid="stSidebar"]'),
      rect: rect(node)
    };
  })
  .filter((item) => item.text);
const buttons = Array.from(document.querySelectorAll('button'))
  .filter(visible)
  .map((node) => ({ text: clean(node.innerText || node.textContent || ''), rect: rect(node) }))
  .filter((item) => item.text);
const tableNodes = Array.from(document.querySelectorAll('table,.change-table-wrap,[data-testid="stDataFrame"]'))
  .filter(visible);
const tables = tableNodes.map((node) => {
  const parent = node.parentElement;
  const itemRect = rect(node);
  const headers = Array.from(node.querySelectorAll('th,[role="columnheader"]'))
    .map((header) => clean(header.innerText || header.textContent || ''))
    .filter(Boolean);
  return {
    tag: node.tagName.toLowerCase(),
    className: node.className || '',
    text: clean((node.innerText || node.textContent || '').slice(0, 500)),
    headers,
    rect: itemRect,
    visibleArea: visibleAreaInViewport(itemRect),
    parentRect: rect(parent),
    scrollWidth: node.scrollWidth || 0,
    clientWidth: node.clientWidth || 0
  };
});
const clipped = Array.from(document.querySelectorAll('button,summary,th,td,[data-testid="stMarkdownContainer"]'))
  .filter((node) => visible(node) && node.scrollWidth > node.clientWidth + 6)
  .slice(0, 12)
  .map((node) => ({
    text: clean((node.innerText || node.textContent || '').slice(0, 140)),
    tag: node.tagName.toLowerCase(),
    rect: rect(node),
    scrollWidth: node.scrollWidth || 0,
    clientWidth: node.clientWidth || 0
  }));
const frames = Array.from(document.querySelectorAll('iframe'))
  .map((iframe) => {
    const container = iframe.closest('div[data-testid="stIFrame"]') || iframe;
    const itemRect = rect(container);
    const visibleLeft = itemRect ? Math.max(0, itemRect.left) : 0;
    const visibleTop = itemRect ? Math.max(0, itemRect.top) : 0;
    const visibleRight = itemRect ? Math.min(window.innerWidth, itemRect.right) : 0;
    const visibleBottom = itemRect ? Math.min(window.innerHeight, itemRect.bottom) : 0;
    const visibleArea = Math.max(0, visibleRight - visibleLeft) * Math.max(0, visibleBottom - visibleTop);
    return {
      rect: itemRect,
      visibleArea,
      inSidebar: !!container.closest('section[data-testid="stSidebar"]'),
      title: iframe.getAttribute('title') || '',
      src: iframe.getAttribute('src') || ''
    };
  })
  .filter((item) => item.rect && item.rect.width > 80 && item.rect.height > 80)
  .sort((a, b) => b.visibleArea - a.visibleArea);
const visibleTextBlocks = Array.from(document.querySelectorAll('p,li,span,div[data-testid="stMarkdownContainer"]'))
  .filter(visible)
  .map((node) => clean(node.innerText || node.textContent || ''))
  .filter((text) => text.length > 20)
  .slice(0, 120);
return {
  url: window.location.href,
  viewport: { width: window.innerWidth, height: window.innerHeight },
  bodyText,
  sidebarText,
  sidebarRect: rect(sidebar),
  headings,
  details,
  buttons,
  tables,
  clipped,
  frames,
  visibleTextBlocks,
  scroll: {
    x: window.scrollX,
    y: window.scrollY,
    docWidth: document.documentElement.scrollWidth,
    docHeight: document.documentElement.scrollHeight
  }
};
"""


def _wait_for_app(driver: webdriver.Remote, timeout: int) -> None:
    def ready(current: webdriver.Remote) -> bool:
        text = current.execute_script("return document.body ? document.body.innerText : ''") or ""
        has_app_title = "Sol- och vindpotential" in text or "Solar" in text
        has_result = (
            "Beräkning klar" in text
            or "Calculation complete" in text
            or "Vind/sol och landskapspåverkan" in text
            or "Wind/Solar and Landscape Impact" in text
        )
        still_calculating = "Beräknar karta" in text or "Calculating" in text
        return bool(has_app_title and has_result and not still_calculating)

    WebDriverWait(driver, timeout).until(ready)
    time.sleep(2.0)


def _snapshot(driver: webdriver.Remote, label: str) -> dict[str, Any]:
    data = driver.execute_script(_snapshot_script())
    data["label"] = label
    return data


def _open_sidebar_sections(driver: webdriver.Remote, labels: list[str]) -> None:
    driver.execute_script(
        r"""
const labels = arguments[0].map((value) => String(value).toLowerCase());
const clean = (value) => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
const sidebar = document.querySelector('section[data-testid="stSidebar"]');
if (!sidebar) return;
for (const label of labels) {
  const details = Array.from(sidebar.querySelectorAll('details')).find((node) => {
    const summary = node.querySelector('summary');
    const text = clean(summary ? summary.innerText || summary.textContent || '' : '');
    return text === label || text.includes(label);
  });
  if (details && !details.open) {
    const summary = details.querySelector('summary');
    if (summary) summary.click();
  }
}
""",
        labels,
    )
    time.sleep(0.8)


def _lower(text: str) -> str:
    return (text or "").casefold()


def _contains_any(text: str, values: list[str]) -> bool:
    lower = _lower(text)
    return any(_lower(value) in lower for value in values)


def _text_index(text: str, needle: str) -> int:
    return _lower(text).find(_lower(needle))


def _main_headings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    sidebar_rect = snapshot.get("sidebarRect") or {}
    sidebar_right = float(sidebar_rect.get("right", 0.0) or 0.0)
    headings: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in snapshot.get("headings", []):
        text = str(item.get("text", "") or "")
        rect = item.get("rect") or {}
        if not text or not rect:
            continue
        if sidebar_right > 0 and float(rect.get("right", 0.0) or 0.0) <= sidebar_right + 8:
            continue
        key = (text, int(float(rect.get("top", 0.0) or 0.0)))
        if key in seen:
            continue
        seen.add(key)
        headings.append(item)
    return sorted(headings, key=lambda value: float((value.get("rect") or {}).get("top", 0.0) or 0.0))


def _finding(priority: str, title: str, evidence: str, recommendation: str, viewport: str) -> Finding:
    return Finding(priority=priority, title=title, evidence=evidence, recommendation=recommendation, viewport=viewport)


def _audit_sidebar(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    sidebar_text = snapshot.get("sidebarText", "")
    if not sidebar_text:
        findings.append(
            _finding(
                "high",
                "Vänsterpanelen hittades inte",
                "Ingen synlig Streamlit-sidebar kunde läsas.",
                "Kontrollera att appen inte kollapsar sidopanelen eller döljer huvudkontrollerna i aktuell viewport.",
                viewport,
            )
        )
        return findings

    expected = ["Geografier", "Energimodellering", "Social acceptans"]
    missing = [label for label in expected if label not in sidebar_text]
    if missing:
        findings.append(
            _finding(
                "high",
                "Vänsterpanelen saknar huvudsektioner",
                f"Saknade sektioner: {', '.join(missing)}.",
                "Behåll en stabil vänsterstruktur med Geografier, Energimodellering och Social acceptans.",
                viewport,
            )
        )

    forbidden = ["Landskapsstrukturer", "Landskapsfaktorer", "Faktor"]
    visible_forbidden = [label for label in forbidden if label in sidebar_text]
    if visible_forbidden:
        findings.append(
            _finding(
                "medium",
                "Tekniska landskapsval syns fortfarande i vänsterpanelen",
                f"Synliga termer: {', '.join(visible_forbidden)}.",
                "Håll huvudflödet till LABLAB:s landskapstyper och flytta strukturer/faktorer till debug eller avancerat.",
                viewport,
            )
        )

    if "Landskapstyper" not in sidebar_text:
        findings.append(
            _finding(
                "medium",
                "Landskapstyper saknas som användarnära landskapsval",
                "Sidebartexten innehåller inte 'Landskapstyper'.",
                "Visa LABLAB:s landskapsanalys som 'Landskapstyper' i Geografier > Landskap.",
                viewport,
            )
        )
    return findings


def _audit_right_panel_priority(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    order = [
        "Vind/sol och landskapspåverkan",
        "Geografier",
        "Energimodellering",
        "Social acceptans",
    ]
    headings = _main_headings(snapshot)
    positions: dict[str, float] = {}
    for label in order:
        matching = [
            float((item.get("rect") or {}).get("top", 0.0) or 0.0)
            for item in headings
            if label in str(item.get("text", ""))
        ]
        if matching:
            positions[label] = min(matching)
    visible = positions
    if "Vind/sol och landskapspåverkan" not in visible:
        findings.append(
            _finding(
                "high",
                "Huvudtabellen är inte tydligt först i resultatpanelen",
                "Rubriken 'Vind/sol och landskapspåverkan' kunde inte läsas i sidans synliga text.",
                "Placera scenariotabellen som första resultatsektion och ge den en tydlig rubrik.",
                viewport,
            )
        )
    if all(label in visible for label in ["Vind/sol och landskapspåverkan", "Geografier", "Energimodellering"]):
        if not (visible["Vind/sol och landskapspåverkan"] < visible["Geografier"] < visible["Energimodellering"]):
            findings.append(
                _finding(
                    "medium",
                    "Resultatsektionerna kommer i otydlig ordning",
                    f"Rubrikpositioner: {json.dumps(visible, ensure_ascii=False)}.",
                    "Låt total-/scenarioresultatet komma först, därefter geografier och sedan energimodelleringens texttolkning.",
                    viewport,
                )
            )
    return findings


def _audit_table_layout(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    viewport_width = float(snapshot.get("viewport", {}).get("width", 0) or 0)
    for table in snapshot.get("tables", []):
        if float(table.get("visibleArea", 0.0) or 0.0) < 200:
            continue
        rect = table.get("rect") or {}
        check_rect = rect
        if "change-table" in str(table.get("className", "")) and table.get("parentRect"):
            check_rect = table.get("parentRect") or rect
        if not rect:
            continue
        overflow = max(0.0, float(check_rect.get("right", 0.0) or 0.0) - viewport_width)
        if overflow > 24:
            findings.append(
                _finding(
                    "high",
                    "Tabell går utanför viewporten",
                    f"Tabell '{table.get('className') or table.get('tag')}' sticker ut {overflow:.0f}px åt höger.",
                    "Behåll horisontell scroll i tabellens egen wrapper eller bryt om kolumner på mindre skärm.",
                    viewport,
                )
            )
        if "change-table-wrap" in str(table.get("className", "")):
            parent = table.get("parentRect") or {}
            parent_width = float(parent.get("width", 0.0) or 0.0)
            table_width = float(rect.get("width", 0.0) or 0.0)
            if parent_width > 0 and table_width < parent_width * 0.68:
                findings.append(
                    _finding(
                        "medium",
                        "Huvudtabellen lämnar mycket tom yta",
                        f"Tabellen använder {table_width:.0f}px av {parent_width:.0f}px i sin behållare.",
                        "Låt huvudtabellen fylla panelbredden med auto-layout, men behåll kompakt cellpadding.",
                        viewport,
                    )
                )
    clipped = snapshot.get("clipped", [])
    if clipped:
        examples = "; ".join(item.get("text", "")[:70] for item in clipped[:4] if item.get("text"))
        findings.append(
            _finding(
                "medium",
                "Synlig text verkar klippas",
                f"Exempel: {examples or 'okänd text'}",
                "Kontrollera knappar, summary-rader och tabellceller i aktuell viewport. Låt text radbrytas eller minska rubriklängd.",
                viewport,
            )
        )
    return findings


def _audit_language_and_copy(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    text = snapshot.get("bodyText", "")
    technical_terms = [
        "potential_km2",
        "andel_potential_pct",
        "klass_label",
        "medelpoäng",
        "class_km",
        "share_8",
        "share_9",
        "None",
        "NaN",
        "H3-rollup",
        "Hexvisning zoomanpassas",
    ]
    visible_terms = [term for term in technical_terms if term in text]
    if visible_terms:
        findings.append(
            _finding(
                "medium",
                "Tekniska modelltermer syns i huvudflödet",
                f"Synliga termer: {', '.join(visible_terms)}.",
                "Byt till mänskliga rubriker i huvudflödet och flytta råfält till Data och metod eller Debug.",
                viewport,
            )
        )
    summary_needles = ["tekniksumma", "unik fysisk markyta", "samnyttja"]
    if not _contains_any(text, summary_needles):
        findings.append(
            _finding(
                "medium",
                "Samnyttjande mellan vind och sol förklaras inte",
                "Sidan saknar synlig text om tekniksumma, unik fysisk markyta eller samnyttjande.",
                "Förklara nära totalraden att vind- och solpotential kan summera samma fysiska hex två gånger.",
                viewport,
            )
        )
    return findings


def _audit_map_balance(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    frames = [frame for frame in snapshot.get("frames", []) if not frame.get("inSidebar")]
    if not frames:
        findings.append(
            _finding(
                "high",
                "Kartan hittades inte",
                "Ingen stor iframe utanför sidopanelen kunde identifieras.",
                "Säkerställ att kartan laddas och att den inte ligger utanför viewporten.",
                viewport,
            )
        )
        return findings
    map_frame = frames[0]
    rect = map_frame.get("rect") or {}
    viewport_width = float(snapshot.get("viewport", {}).get("width", 0) or 0)
    map_width = float(rect.get("width", 0) or 0)
    if viewport_width > 900 and map_width < viewport_width * 0.22:
        findings.append(
            _finding(
                "low",
                "Kartan får mycket liten del av desktopbredden",
                f"Kartbredd: {map_width:.0f}px av viewport {viewport_width:.0f}px.",
                "Kontrollera panelbreddens default så både karta och resultatpanel får rimligt arbetsutrymme.",
                viewport,
            )
        )
    return findings


def _audit_user_questions(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    viewport = str(snapshot["label"])
    headings = [item.get("text", "") for item in _main_headings(snapshot)]
    question_map = {
        "Vind/sol och landskapspåverkan": "Hur mycket yta kräver scenariot och ryms det?",
        "Geografier": "Vilka geografiska antaganden formar potentialen?",
        "Energimodellering": "Vad betyder totalraden i energisystemet?",
        "Social acceptans": "Hur påverkar acceptans den möjliga ytan?",
    }
    missing = [heading for heading in question_map if not any(heading in value for value in headings)]
    if missing:
        findings.append(
            _finding(
                "low",
                "Alla centrala användarfrågor syns inte som tydliga sektioner",
                f"Saknade rubriker: {', '.join(missing)}.",
                "Se till att varje huvudsektion besvarar en tydlig användarfråga, och göm modellstatus i avancerat/debug.",
                viewport,
            )
        )
    return findings


def _find_button(driver: webdriver.Remote, labels: list[str]) -> Any | None:
    script = r"""
const labels = arguments[0].map((value) => String(value).toLowerCase());
const clean = (value) => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
const visible = (node) => {
  const r = node.getBoundingClientRect();
  const style = window.getComputedStyle(node);
  return r.width > 2 && r.height > 2 && style.visibility !== 'hidden' && style.display !== 'none';
};
return Array.from(document.querySelectorAll('button')).find((node) => {
  const text = clean(node.innerText || node.textContent || '');
  return visible(node) && labels.some((label) => text === label || text.includes(label));
}) || null;
"""
    return driver.execute_script(script, labels)


def _click_button(driver: webdriver.Remote, labels: list[str]) -> bool:
    element = _find_button(driver, labels)
    if element is None:
        return False
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)
    return True


def _audit_language_switch(driver: webdriver.Remote, timeout: int, skip_language: bool) -> list[Finding]:
    if skip_language:
        return []
    findings: list[Finding] = []
    if not _click_button(driver, ["EN"]):
        findings.append(
            _finding(
                "medium",
                "Språkväxlaren saknar EN-knapp",
                "Kunde inte hitta en synlig knapp med texten EN.",
                "Behåll språkväxlaren synlig och konsekvent placerad i sidopanelen.",
                "language",
            )
        )
        return findings
    try:
        WebDriverWait(driver, timeout).until(
            lambda current: "Energy Modelling" in (current.execute_script("return document.body.innerText") or "")
            or "Wind/Solar" in (current.execute_script("return document.body.innerText") or "")
        )
    except Exception:
        findings.append(
            _finding(
                "high",
                "Engelsk språkväxling slog inte igenom",
                "Efter klick på EN syntes varken 'Energy Modelling' eller 'Wind/Solar'.",
                "Säkerställ att centrala UI-texter och tutorial följer samma språkstate.",
                "language",
            )
        )
    english_text = driver.execute_script("return document.body ? document.body.innerText : ''") or ""
    if "Show guide" not in english_text and "guide" not in english_text.casefold():
        findings.append(
            _finding(
                "medium",
                "Guidens språkstatus är svår att verifiera på engelska",
                "Efter EN-växling hittades ingen tydlig engelsk guideknapp/text.",
                "Översätt guideknappen och tutorialens synliga texter med samma språkväxlare som resten av appen.",
                "language",
            )
        )
    _click_button(driver, ["SV", "Svenska"])
    return findings


def _audit_snapshot(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_audit_sidebar(snapshot))
    findings.extend(_audit_right_panel_priority(snapshot))
    findings.extend(_audit_table_layout(snapshot))
    findings.extend(_audit_language_and_copy(snapshot))
    findings.extend(_audit_map_balance(snapshot))
    findings.extend(_audit_user_questions(snapshot))
    return findings


def _write_report(report_dir: Path, url: str, snapshots: list[dict[str, Any]], findings: list[Finding]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "url": url,
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
        "snapshots": snapshots,
    }
    (report_dir / "ui_ux_review.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {priority: sum(1 for item in findings if item.priority == priority) for priority in ["high", "medium", "low"]}
    lines = [
        "# Potential App UI/UX Review",
        "",
        f"- URL: `{url}`",
        f"- Findings: {len(findings)} (high: {counts['high']}, medium: {counts['medium']}, low: {counts['low']})",
        "",
        "## Scope",
        "",
        "Automated heuristic review of the visible Streamlit UI. The test checks layout, section priority, copy clarity, technical leakage, language switching, map/result balance, and whether visible sections answer clear user questions.",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.extend(["No UI/UX findings were detected by the current heuristic checks.", ""])
    else:
        for index, finding in enumerate(sorted(findings, key=lambda item: -PRIORITY_ORDER[item.priority]), start=1):
            lines.extend(
                [
                    f"### {index}. [{finding.priority.upper()}] {finding.title}",
                    "",
                    f"- Viewport: `{finding.viewport}`",
                    f"- Evidence: {finding.evidence}",
                    f"- Recommendation: {finding.recommendation}",
                    "",
                ]
            )
    lines.extend(
        [
            "## Screenshots",
            "",
            "- `desktop.png`",
            "- `mobile.png`",
            "",
            "## Notes",
            "",
            "This is a review aid, not a replacement for human design review. Treat findings as prompts for product decisions.",
        ]
    )
    report_path = report_dir / "ui_ux_review.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _should_fail(findings: list[Finding], fail_on: str) -> bool:
    if fail_on == "none":
        return False
    threshold = PRIORITY_ORDER[fail_on]
    return any(PRIORITY_ORDER[item.priority] >= threshold for item in findings)


def run(url: str, headed: bool, timeout: int, report_dir: Path, skip_language: bool, fail_on: str) -> int:
    driver = _make_driver(headed=headed)
    findings: list[Finding] = []
    snapshots: list[dict[str, Any]] = []
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        driver.set_window_size(1600, 1000)
        driver.get(url)
        _wait_for_app(driver, timeout)
        _open_sidebar_sections(driver, ["Geografier", "Landskap"])
        desktop = _snapshot(driver, "desktop-1600x1000")
        snapshots.append(desktop)
        driver.save_screenshot(str(report_dir / "desktop.png"))
        findings.extend(_audit_snapshot(desktop))
        findings.extend(_audit_language_switch(driver, timeout, skip_language))

        driver.set_window_size(390, 900)
        driver.refresh()
        _wait_for_app(driver, timeout)
        _open_sidebar_sections(driver, ["Geografier", "Landskap"])
        mobile = _snapshot(driver, "mobile-390x900")
        snapshots.append(mobile)
        report_dir.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(report_dir / "mobile.png"))
        findings.extend(_audit_snapshot(mobile))

        report_path = _write_report(report_dir, url, snapshots, findings)
        print(f"UI/UX review wrote {report_path}")
        if findings:
            for item in sorted(findings, key=lambda value: -PRIORITY_ORDER[value.priority]):
                print(f"[{item.priority.upper()}] {item.title} ({item.viewport})")
        else:
            print("No UI/UX findings detected by heuristic review.")
        return 1 if _should_fail(findings, fail_on) else 0
    except Exception as exc:
        report_dir.mkdir(parents=True, exist_ok=True)
        try:
            driver.save_screenshot(str(report_dir / "failure.png"))
        except Exception:
            pass
        print(f"FAIL UI/UX review could not complete: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic UI/UX review for the Potential Streamlit app.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true", help="Run a visible browser instead of headless mode.")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--skip-language", action="store_true")
    parser.add_argument("--fail-on", choices=["none", "low", "medium", "high"], default="none")
    args = parser.parse_args()
    return run(args.url, args.headed, args.timeout, args.report_dir, args.skip_language, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
