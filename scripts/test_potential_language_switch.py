from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from selenium.webdriver.support.ui import WebDriverWait

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import test_potential_tutorial_ui as tutorial_ui  # noqa: E402


DEFAULT_URL = "http://localhost:8505"


def _body_text(driver: Any) -> str:
    return str(driver.execute_script("return document.body ? document.body.innerText : '';") or "")


def _tutorial_state(driver: Any) -> dict[str, Any]:
    return dict(
        driver.execute_script(
            r"""
const root = document.querySelector('#potential-tutorial-root');
const title = document.querySelector('#potential-tutorial-root h2');
const body = document.querySelector('#potential-tutorial-root p');
const count = document.querySelector('#potential-tutorial-root .pt-count');
const action = document.querySelector('#potential-tutorial-root .pt-action-status');
const buttons = Array.from(document.querySelectorAll('#potential-tutorial-root button'))
  .map((button) => (button.textContent || button.getAttribute('aria-label') || '').trim())
  .filter(Boolean);
const checkbox = document.querySelector('#potential-tutorial-root .pt-checkbox');
return {
  visible: !!root && getComputedStyle(root).display !== 'none',
  title: title ? title.textContent.trim() : '',
  body: body ? body.textContent.trim() : '',
  count: count ? count.textContent.trim() : '',
  action: action && !action.hidden ? action.textContent.trim() : '',
  buttons,
  checkbox: checkbox ? checkbox.textContent.trim() : ''
};
"""
        )
        or {}
    )


def _wait_for(driver: Any, predicate: Callable[[Any], bool], label: str, timeout: int) -> None:
    try:
        WebDriverWait(driver, timeout).until(lambda current: bool(predicate(current)))
    except Exception as error:
        state = {
            "body_head": _body_text(driver)[:800],
            "tutorial": _tutorial_state(driver),
        }
        raise AssertionError(f"Timeout waiting for {label}: {json.dumps(state, ensure_ascii=False)}") from error


def _wait_title(driver: Any, title: str, timeout: int) -> None:
    _wait_for(
        driver,
        lambda current: _tutorial_state(current).get("visible") and _tutorial_state(current).get("title") == title,
        f"tutorial title {title!r}",
        timeout,
    )


def _click_tutorial(driver: Any, selector: str) -> None:
    tutorial_ui._click(driver, selector)
    time.sleep(0.25)


def _assert_contains(value: str, expected: str, label: str) -> None:
    if expected not in value:
        raise AssertionError(f"{label} missing {expected!r}. Got {value!r}.")


def run(url: str, headed: bool, timeout: int) -> int:
    driver = tutorial_ui._make_driver(headed=headed)
    checks: list[str] = []
    try:
        driver.get(url)
        tutorial_ui._clear_tutorial_storage(driver)
        driver.refresh()

        _wait_title(driver, "Hitta potential för ny vind och sol", timeout)
        sv_start = _tutorial_state(driver)
        _assert_contains(str(sv_start["count"]), "Steg 1 av 15", "Swedish tutorial count")
        if "Nästa" not in sv_start["buttons"]:
            raise AssertionError(f"Swedish tutorial buttons missing Nästa: {sv_start}")
        _assert_contains(str(sv_start["checkbox"]), "Öppna inte automatiskt igen", "Swedish tutorial checkbox")
        checks.append("SV autostart and tutorial controls")

        _click_tutorial(driver, "#potential-tutorial-root .pt-checkbox input")
        _click_tutorial(driver, "#potential-tutorial-root .pt-close")

        tutorial_ui._click_button_by_text(driver, "EN")
        _wait_for(
            driver,
            lambda current: (
                "Energy Modelling" in _body_text(current)
                and "Show guide" in _body_text(current)
                and "Wind/Solar and Landscape Impact" in _body_text(current)
            ),
            "English app shell labels",
            timeout,
        )
        checks.append("EN app shell labels")

        tutorial_ui._click_button_by_text(driver, "Show guide")
        _wait_title(driver, "Find potential for new wind and solar", timeout)
        en_start = _tutorial_state(driver)
        _assert_contains(str(en_start["count"]), "Step 1 of 15", "English tutorial count")
        if "Next" not in en_start["buttons"]:
            raise AssertionError(f"English tutorial buttons missing Next: {en_start}")
        _assert_contains(str(en_start["checkbox"]), "Do not open automatically again", "English tutorial checkbox")
        checks.append("EN tutorial step 1")

        for _ in range(4):
            _click_tutorial(driver, "#potential-tutorial-root .pt-next")
        _wait_title(driver, "Add social acceptance", timeout)
        en_acceptance = _tutorial_state(driver)
        _assert_contains(str(en_acceptance["action"]), "Acceptance impact slider", "English step 5 suggestion")
        checks.append("EN tutorial step 5 suggestion")

        for _ in range(5):
            _click_tutorial(driver, "#potential-tutorial-root .pt-next")
        _wait_title(driver, "Wind and solar are controlled under Geographies", timeout)
        en_geographies = _tutorial_state(driver)
        _assert_contains(str(en_geographies["action"]), "Try this", "English step 10 action card")
        checks.append("EN tutorial step 10 action card")

        for _ in range(2):
            _click_tutorial(driver, "#potential-tutorial-root .pt-next")
        _wait_title(driver, "Read the result table", timeout)
        checks.append("EN tutorial step 12 table")

        _click_tutorial(driver, "#potential-tutorial-root .pt-close")
        tutorial_ui._click_button_by_text(driver, "SV")
        _wait_for(
            driver,
            lambda current: (
                "Energimodellering" in _body_text(current)
                and "Visa guide" in _body_text(current)
                and "Vind/sol och landskapspåverkan" in _body_text(current)
            ),
            "Swedish app shell labels after return",
            timeout,
        )
        checks.append("SV app shell labels after return")

        tutorial_ui._click_button_by_text(driver, "Visa guide")
        _wait_title(driver, "Hitta potential för ny vind och sol", timeout)
        sv_return = _tutorial_state(driver)
        _assert_contains(str(sv_return["count"]), "Steg 1 av 15", "Swedish tutorial count after return")
        if "Nästa" not in sv_return["buttons"]:
            raise AssertionError(f"Swedish tutorial buttons missing after return: {sv_return}")
        checks.append("SV tutorial after return")

        print(json.dumps({"status": "PASS", "checks": checks}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Potential App language switching, especially tutorial copy.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout", type=int, default=80)
    args = parser.parse_args()
    return run(args.url, args.headed, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
