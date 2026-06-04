from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import test_potential_tutorial_ui as tutorial_ui  # noqa: E402


DEFAULT_URL = "http://localhost:8505"


def _body_text(driver: Any) -> str:
    return str(driver.execute_script("return document.body ? document.body.innerText : '';") or "")


def _wait_for(driver: Any, predicate: Callable[[Any], bool], label: str, timeout: int) -> None:
    try:
        WebDriverWait(driver, timeout).until(lambda current: bool(predicate(current)))
    except Exception as error:
        state = {
            "body_head": _body_text(driver)[:1000],
            "visible_controls": _visible_control_summary(driver),
        }
        raise AssertionError(f"Timeout waiting for {label}: {json.dumps(state, ensure_ascii=False)}") from error


def _wait_app_ready(driver: Any, timeout: int) -> None:
    _wait_for(
        driver,
        lambda current: (
            "Sol- och vindpotential" in _body_text(current)
            and "Vind/sol och landskapspåverkan" in _body_text(current)
            and "Beräkning klar" in _body_text(current)
        ),
        "app ready",
        timeout,
    )


def _dismiss_tutorial(driver: Any) -> None:
    driver.execute_script(
        """
const close = document.querySelector('#potential-tutorial-root .pt-close');
if (close) close.click();
"""
    )
    time.sleep(0.35)


def _visible_control_summary(driver: Any) -> dict[str, Any]:
    return dict(
        driver.execute_script(
            r"""
const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
const visible = (node) => {
  if (!node || !node.getBoundingClientRect) return false;
  const style = getComputedStyle(node);
  const rect = node.getBoundingClientRect();
  return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
};
return {
  buttons: Array.from(document.querySelectorAll('button')).filter(visible).map((node) => clean(node.textContent)).filter(Boolean).slice(0, 40),
  details: Array.from(document.querySelectorAll('details')).map((node) => {
    const summary = node.querySelector('summary');
    return { text: clean(summary ? summary.textContent : node.textContent), open: !!node.open };
  }).slice(0, 40),
  checkboxes: Array.from(document.querySelectorAll('input[type="checkbox"]')).map((node) => {
    const label = node.closest('label');
    return { text: clean(label ? label.textContent : node.getAttribute('aria-label')), checked: !!node.checked };
  }).slice(0, 40),
  radios: Array.from(document.querySelectorAll('input[type="radio"]')).map((node) => {
    const label = node.closest('label');
    return { text: clean(label ? label.textContent : node.getAttribute('aria-label')), checked: !!node.checked };
  }).slice(0, 40),
  sliderCount: document.querySelectorAll('[role="slider"]').length
};
"""
        )
        or {}
    )


def _click_expander(driver: Any, label: str, timeout: int, open_state: bool | None = True) -> None:
    clicked = driver.execute_script(
        r"""
const wanted = String(arguments[0] || '').replace(/\s+/g, ' ').trim().toLowerCase();
const details = Array.from(document.querySelectorAll('details')).find((node) => {
  const summary = node.querySelector('summary');
  const text = String(summary ? summary.textContent : node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  return text === wanted || text.includes(wanted);
});
if (!details) return false;
const summary = details.querySelector('summary') || details;
summary.click();
return true;
""",
        label,
    )
    if not clicked:
        raise AssertionError(f"Could not find expander {label!r}. Controls: {_visible_control_summary(driver)}")
    time.sleep(0.45)
    if open_state is not None:
        _wait_for(
            driver,
            lambda current: bool(
                current.execute_script(
                    r"""
const wanted = String(arguments[0] || '').replace(/\s+/g, ' ').trim().toLowerCase();
const details = Array.from(document.querySelectorAll('details')).find((node) => {
  const summary = node.querySelector('summary');
  const text = String(summary ? summary.textContent : node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  return text === wanted || text.includes(wanted);
});
return details ? details.open === arguments[1] : false;
""",
                    label,
                    open_state,
                )
            ),
            f"expander {label!r} open={open_state}",
            timeout,
        )


def _click_labeled_input(driver: Any, label: str) -> None:
    clicked = driver.execute_script(
        r"""
const wanted = String(arguments[0] || '').replace(/\s+/g, ' ').trim().toLowerCase();
const visible = (node) => {
  if (!node || !node.getBoundingClientRect) return false;
  const style = getComputedStyle(node);
  const rect = node.getBoundingClientRect();
  return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
};
const labels = Array.from(document.querySelectorAll('label')).filter((node) => {
  const text = String(node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  return visible(node) && (text === wanted || text.includes(wanted));
});
const node = labels[0];
if (!node) return false;
node.click();
return true;
""",
        label,
    )
    if not clicked:
        raise AssertionError(f"Could not find labeled input {label!r}. Controls: {_visible_control_summary(driver)}")
    time.sleep(0.8)


def _click_button(driver: Any, label: str) -> None:
    tutorial_ui._click_button_by_text(driver, label)
    time.sleep(0.8)


def _move_first_slider(driver: Any, offset_px: int) -> None:
    sliders = driver.find_elements("css selector", '[role="slider"]')
    visible = [slider for slider in sliders if slider.is_displayed()]
    if not visible:
        raise AssertionError(f"No visible sliders found. Controls: {_visible_control_summary(driver)}")
    ActionChains(driver).move_to_element(visible[0]).drag_and_drop_by_offset(visible[0], offset_px, 0).perform()
    time.sleep(0.9)


def _assert_no_severe_console_errors(driver: Any) -> None:
    try:
        logs = driver.get_log("browser")
    except (WebDriverException, Exception):
        return
    severe = [
        entry
        for entry in logs
        if str(entry.get("level", "")).upper() == "SEVERE"
        and "favicon" not in str(entry.get("message", "")).lower()
    ]
    if severe:
        raise AssertionError(f"Browser console has severe errors: {json.dumps(severe[:5], ensure_ascii=False)}")


def run(url: str, headed: bool, timeout: int) -> int:
    driver = tutorial_ui._make_driver(headed=headed)
    checks: list[str] = []
    try:
        driver.get(url)
        tutorial_ui._clear_tutorial_storage(driver)
        driver.refresh()
        _wait_app_ready(driver, timeout)
        _dismiss_tutorial(driver)
        checks.append("app opens and tutorial can be closed")

        _click_expander(driver, "Geografier", timeout, True)
        _click_expander(driver, "Landskap", timeout, True)
        _click_expander(driver, "Avancerade inställningar", timeout, True)
        _click_expander(driver, "Avancerade inställningar", timeout, False)
        checks.append("geography expanders open and close")

        _click_expander(driver, "Landskapspotential Vind", timeout, True)
        _click_expander(driver, "Befolkning och bebyggelse", timeout, None)
        _click_button(driver, "Använd ändringar")
        _wait_app_ready(driver, timeout)
        checks.append("wind potential group opens and apply remains stable")

        _click_expander(driver, "Energimodellering", timeout, True)
        _move_first_slider(driver, 80)
        _wait_app_ready(driver, timeout)
        _move_first_slider(driver, -80)
        _wait_app_ready(driver, timeout)
        checks.append("energy/visible slider can move both directions")

        _click_expander(driver, "Social acceptans", timeout, True)
        _click_labeled_input(driver, "Visa social acceptanslager")
        _wait_app_ready(driver, timeout)
        _move_first_slider(driver, -60)
        _wait_app_ready(driver, timeout)
        _click_labeled_input(driver, "Hög acceptans")
        _wait_app_ready(driver, timeout)
        _click_labeled_input(driver, "Mellanacceptans")
        _wait_app_ready(driver, timeout)
        _click_labeled_input(driver, "Visa social acceptanslager")
        _wait_app_ready(driver, timeout)
        checks.append("social acceptance checkbox, slider and radio stay stable")

        _click_button(driver, "Visa guide")
        _wait_for(
            driver,
            lambda current: bool(
                current.execute_script(
                    "const title=document.querySelector('#potential-tutorial-root h2'); return title && title.textContent.includes('Hitta potential');"
                )
            ),
            "manual guide opens after interactions",
            timeout,
        )
        _dismiss_tutorial(driver)
        checks.append("guide opens after mixed interactions")

        _assert_no_severe_console_errors(driver)
        print(json.dumps({"status": "PASS", "checks": checks}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Broad interaction smoke test for the Potential App.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout", type=int, default=100)
    args = parser.parse_args()
    return run(args.url, args.headed, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
