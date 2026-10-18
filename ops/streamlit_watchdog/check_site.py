"""Read public UI; click the documented sleep button once, never redeploy.

No API keys, application imports, Git commands, or private project paths.
The CLI permits only the fixed production URL. Tests use Config with loopback.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import Error as BrowserError, sync_playwright

SITE_URL = "https://gokpop-hwna3kwp26qx8h9zs4b7g5.streamlit.app/"
SITE_HOST = urlsplit(SITE_URL).hostname
WAKE_BUTTON = "Yes, get this app back up!"
MENUS = ("점수 보기", "직접 계산", "감상 노트")
SLEEP = re.compile(r"gone to sleep|sleeping|\bZzzz\b|절전", re.I)
APP_NAME = re.compile(r"GOKPOP\s*2\.0")
SCORE = re.compile(r"69\.44\s*/\s*100\s*점")
ERROR = re.compile(
    r"Oh no[.!]|Error running (?:your )?app|This app has encountered an error|"
    r"Application error|ModuleNotFoundError|ImportError|"
    r"Traceback \(most recent call last\)|gone over its resource limits", re.I
)


class Config:
    def __init__(self, url=SITE_URL, initial_timeout=90.0, wake_timeout=240.0,
                 poll=5.0, navigation_timeout=45.0, network_retry_delay=15.0):
        parsed = urlsplit(url)
        production = url == SITE_URL
        loopback = parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
        if not (production or loopback) or parsed.username or parsed.password:
            raise ValueError("Only the fixed public app or a loopback test server is permitted")
        self.url = url
        self.initial_timeout = initial_timeout
        self.wake_timeout = wake_timeout
        self.poll = poll
        self.navigation_timeout = navigation_timeout
        self.network_retry_delay = network_retry_delay
        self.production = production

    def allows(self, url):
        parsed = urlsplit(url)
        if self.production:
            return parsed.scheme == "https" and parsed.hostname in (SITE_HOST, "share.streamlit.io")
        target = urlsplit(self.url)
        return parsed.scheme == "http" and parsed.netloc == target.netloc


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_text(text):
    # Diagnostics contain visible public text, never headers, cookies or storage.
    text = re.sub(r"https?://[^\s<>]+", "[URL]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", text)
    text = re.sub(r"(?i)(api[_ -]?key|token|password|secret)\s*[:=]\s*\S+", r"\1=[redacted]", text)
    return text[:8000]


def inspect(page, config):
    """Use same-origin rendered frames, excluding YouTube and status widgets."""
    if not config.allows(page.url):
        return {"state": "error", "reason": "unexpected_redirect", "text": ""}, None
    observations = []
    wake = None
    for frame in page.frames:
        if not config.allows(frame.url):
            continue
        try:
            # Streamlit uses fixed-position content: its body can have height 0
            # while stMain and all controls are visibly rendered. Check the
            # iframe, not the body's own box, before reading rendered text.
            if frame != page.main_frame and not frame.frame_element().is_visible():
                continue
            body = frame.locator("body")
            text = body.inner_text(timeout=1000)
            exception = frame.locator('[data-testid="stException"]')
            if any(exception.nth(i).is_visible() for i in range(exception.count())) or ERROR.search(text):
                return {"state": "error", "reason": "application_error", "text": text}, None
            buttons = frame.get_by_role("button", name=WAKE_BUTTON, exact=True)
            visible = [buttons.nth(i) for i in range(buttons.count()) if buttons.nth(i).is_visible()]
            if SLEEP.search(text) and len(visible) == 1:
                wake = visible[0]
                observations.append({"state": "sleeping", "text": text})
            elif APP_NAME.search(text) and SCORE.search(text) and all(
                frame.get_by_role("radio", name=name, exact=True).is_visible() for name in MENUS
            ):
                observations.append({"state": "healthy", "text": text})
            else:
                observations.append({"state": "loading", "sleep_text": bool(SLEEP.search(text)), "text": text})
        except BrowserError:
            # Frames can be replaced while Cloud starts the app; observe again.
            continue
    # Never let a stale app iframe override an active sleep page.
    for state in ("sleeping", "healthy"):
        match = next((o for o in observations if o["state"] == state), None)
        if match:
            return match, wake if state == "sleeping" else None
    return {"state": "loading", "sleep_text": any(o.get("sleep_text") for o in observations),
            "text": "\n".join(o["text"] for o in observations)}, None


def monitor(page, config, output):
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = {"target": config.url, "started_at_utc": utc_now(), "status": "failed",
              "wake_clicked": False, "wake_confirmed": False, "navigation_attempts": 0,
              "initial_state": None, "final_state": None, "error_code": None}
    events = []

    def event(name, **details):
        item = {"at_utc": utc_now(), "elapsed_seconds": round(time.monotonic() - start, 3),
                "event": name, **details}
        events.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
        (output / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")

    observed = {"state": "loading", "text": ""}
    try:
        for attempt in (1, 2):
            result["navigation_attempts"] = attempt
            try:
                response = page.goto(config.url, wait_until="domcontentloaded",
                                     timeout=config.navigation_timeout * 1000)
                if response and response.status >= 400:
                    result["error_code"] = "http_error"
                    event("http_error", status=response.status)
                break
            except BrowserError as exc:
                # One retry for transport/navigation failure only. No HTTP-error retry.
                event("navigation_error", attempt=attempt, message=safe_text(str(exc))[:500])
                if attempt == 2:
                    result["error_code"] = "network_error"
                    break
                page.wait_for_timeout(config.network_retry_delay * 1000)
        deadline = time.monotonic() + config.initial_timeout
        previous = None
        while not result["error_code"]:
            observed, button = inspect(page, config)
            state = observed["state"]
            result["initial_state"] = result["initial_state"] or state
            result["final_state"] = state
            if state != previous:
                event("state", state=state)
                previous = state
            if state == "error":
                result["error_code"] = observed["reason"]
                break
            if state == "healthy":
                result["status"] = "healthy"
                result["wake_confirmed"] = result["wake_clicked"]
                event("healthy", wake_confirmed=result["wake_confirmed"])
                break
            if state == "sleeping" and not result["wake_clicked"]:
                page.screenshot(path=str(output / "sleep-before.png"), full_page=False, timeout=10000)
                # Only the documented, visible button in an allowed Cloud frame.
                button.click(timeout=10000)
                result["wake_clicked"] = True
                event("wake_button_clicked")
                deadline = time.monotonic() + config.wake_timeout
            if time.monotonic() >= deadline:
                result["error_code"] = ("wake_timeout" if result["wake_clicked"] else
                                        "sleep_button_missing" if observed.get("sleep_text") else "loading_timeout")
                break
            # DOM observation only; no repeated refresh or health HTTP requests.
            page.wait_for_timeout(config.poll * 1000)
    except BrowserError as exc:
        result["error_code"] = "browser_error"
        event("browser_error", message=safe_text(str(exc))[:500])
    finally:
        result["finished_at_utc"] = utc_now()
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        if result["status"] != "healthy":
            event("failed", error_code=result["error_code"])
        (output / "visible-text.txt").write_text(safe_text(observed.get("text", "")), encoding="utf-8")
        try:
            page.screenshot(path=str(output / "final.png"), full_page=False, timeout=10000)
        except BrowserError:
            event("screenshot_unavailable")
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def block_unneeded(route):
    host = urlsplit(route.request.url).hostname or ""
    if route.request.resource_type == "media" or any(
        host == domain or host.endswith("." + domain)
        for domain in ("youtube.com", "youtube-nocookie.com", "googlevideo.com", "ytimg.com")
    ):
        route.abort()
    else:
        route.continue_()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New diagnostics directory; existing records are never overwritten")
    args = parser.parse_args()
    config = Config()
    if args.output_dir.exists():
        parser.error("Output directory already exists; choose a new run directory")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US")
            context.route("**/*", block_unneeded)
            page = context.new_page()
            result = monitor(page, config, args.output_dir)
            browser.close()
    except BrowserError as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        result = {"status": "failed", "error_code": "browser_startup_error", "wake_clicked": False,
                  "wake_confirmed": False, "message": safe_text(str(exc))[:500], "finished_at_utc": utc_now()}
        (args.output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## GOKPOP public site check\n\n")
            handle.write(f"- Status: **{result['status']}**\n- Wake clicked: {result['wake_clicked']}\n")
            handle.write(f"- Wake confirmed: {result['wake_confirmed']}\n- Error: {result.get('error_code')}\n")
            handle.write("- See the diagnostics artifact for timing and screenshots.\n")
    return 0 if result["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
