"""Persistent browser session for Ghost — stealth + human-like behavior.

Playwright is an optional dependency: install with `pip install playwright`
plus `playwright install chromium`. Tools are only registered if available.

Key upgrades over v1:
- Anti-detection: removes navigator.webdriver, randomizes fingerprint
- Human-like delays, mouse movement curves, natural typing speed
- Multi-tab management
- Persistent profile (cookies survive restarts)
- Screenshot → base64 inline for vision analysis
- Connect to real Chrome via CDP (no bot detection)
"""

from __future__ import annotations

import base64
import math
import os
import platform
import random
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from ghost.tools.registry import Tool, ToolResult


_session_lock = threading.Lock()
_singleton: "BrowserSession | None" = None


def _get() -> "BrowserSession":
    global _singleton
    with _session_lock:
        if _singleton is None:
            _singleton = BrowserSession()
            _singleton.start()
        return _singleton


def _get_cdp() -> "BrowserSession":
    """Get a session connected to real Chrome via CDP."""
    global _singleton
    with _session_lock:
        if _singleton is None or not _singleton._cdp_mode:
            if _singleton:
                _singleton.stop()
            _singleton = BrowserSession(cdp_mode=True)
            _singleton.start()
        return _singleton


# ─────────────────────────────────────────────────────────────────────
# Human behavior helpers
# ─────────────────────────────────────────────────────────────────────

def _human_delay(min_s: float = 0.5, max_s: float = 2.0) -> None:
    """Random sleep that mimics human reaction time."""
    time.sleep(random.uniform(min_s, max_s))


def _bezier_curve(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int = 20,
) -> list[tuple[float, float]]:
    """Generate a bezier curve path between two points for natural mouse movement."""
    # Two random control points for a cubic bezier
    cp1 = (
        start[0] + random.uniform(-100, 100),
        start[1] + random.uniform(-80, 80),
    )
    cp2 = (
        end[0] + random.uniform(-100, 100),
        end[1] + random.uniform(-80, 80),
    )
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Cubic bezier formula
        x = (
            (1 - t) ** 3 * start[0]
            + 3 * (1 - t) ** 2 * t * cp1[0]
            + 3 * (1 - t) * t ** 2 * cp2[0]
            + t ** 3 * end[0]
        )
        y = (
            (1 - t) ** 3 * start[1]
            + 3 * (1 - t) ** 2 * t * cp1[1]
            + 3 * (1 - t) * t ** 2 * cp2[1]
            + t ** 3 * end[1]
        )
        points.append((x, y))
    return points


def _human_type(page, text: str, wpm: int = 60) -> None:
    """Type text at human speed with occasional typos and corrections."""
    # Average chars per minute based on WPM (1 word ≈ 5 chars)
    chars_per_second = (wpm * 5) / 60
    base_delay = 1.0 / chars_per_second

    for i, char in enumerate(text):
        # Occasional burst typing (faster) or pause (thinking)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.3, 0.8))  # brief pause
        elif random.random() < 0.03:
            time.sleep(random.uniform(0.8, 1.5))  # longer pause

        # Vary typing speed naturally
        delay = base_delay * random.uniform(0.5, 2.0)

        # Very rare typo + correction (1% chance)
        if random.random() < 0.01 and char.isalpha():
            wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
            page.keyboard.type(wrong)
            time.sleep(random.uniform(0.1, 0.3))
            page.keyboard.press("Backspace")
            time.sleep(random.uniform(0.05, 0.15))

        page.keyboard.type(char)
        time.sleep(delay)


# ─────────────────────────────────────────────────────────────────────
# Anti-detection JS patches
# ─────────────────────────────────────────────────────────────────────

_STEALTH_SCRIPT = """
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Fake plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'zh-CN'],
});

// Override chrome object
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
};

// Permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

# Random user agents pool (real Chrome versions)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ─────────────────────────────────────────────────────────────────────
# BrowserSession
# ─────────────────────────────────────────────────────────────────────

class BrowserSession:
    """A single shared Chromium session with stealth + human-behavior support.
    
    Two modes:
    - Normal mode: launches Ghost's own Chromium with anti-detection
    - CDP mode: connects to your real Chrome browser (no bot detection)
    """

    def __init__(
        self,
        headless: bool = False,
        profile_dir: str | None = None,
        cdp_mode: bool = False,
        cdp_port: int = 9222,
    ) -> None:
        self.headless = headless
        self.profile_dir = profile_dir or str(Path.home() / ".ghost" / "browser_profile")
        self.cdp_mode = cdp_mode
        self._cdp_mode = cdp_mode
        self.cdp_port = cdp_port
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._user_agent = random.choice(_USER_AGENTS)

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()

        if self._cdp_mode:
            # Connect to real Chrome via CDP — uses your actual browser
            # Chrome must be started with: --remote-debugging-port=9222
            try:
                self._browser = self._pw.chromium.connect_over_cdp(
                    f"http://localhost:{self.cdp_port}"
                )
                contexts = self._browser.contexts
                if contexts:
                    self._context = contexts[0]
                    pages = self._context.pages
                    self._page = pages[0] if pages else self._context.new_page()
                else:
                    self._context = self._browser.new_context()
                    self._page = self._context.new_page()
                self._page.set_default_timeout(20000)
                return
            except Exception as e:
                # CDP connection failed — fall back to normal mode
                self._cdp_mode = False
                if self._pw:
                    try:
                        self._pw.stop()
                    except Exception:
                        pass
                self._pw = sync_playwright().start()

        # Normal mode: launch Ghost's own Chromium with anti-detection
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions-except=",
                "--disable-plugins-discovery",
            ],
            user_agent=self._user_agent,
            viewport={"width": 1280 + random.randint(-20, 20), "height": 800 + random.randint(-10, 10)},
            locale="en-US",
            timezone_id="America/New_York",
            screen={"width": 1920, "height": 1080},
            color_scheme="light",
            device_scale_factor=1.0,
            is_mobile=False,
            has_touch=False,
        )
        self._context.add_init_script(_STEALTH_SCRIPT)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.set_default_timeout(20000)

    def page(self):
        if self._page is None or not self._is_alive():
            self.stop()
            self.start()
        return self._page

    def new_tab(self, url: str | None = None):
        """Open a new tab, optionally navigate to url."""
        ctx = self._context
        if ctx is None:
            self.start()
            ctx = self._context
        page = ctx.new_page()
        page.set_default_timeout(20000)
        if url:
            page.goto(url, wait_until="domcontentloaded")
        self._page = page
        return page

    def all_tabs(self) -> list:
        if self._context is None:
            return []
        return list(self._context.pages)

    def switch_tab(self, index: int) -> bool:
        tabs = self.all_tabs()
        if 0 <= index < len(tabs):
            self._page = tabs[index]
            self._page.bring_to_front()
            return True
        return False

    def _is_alive(self) -> bool:
        try:
            if self._page and self._context:
                _ = self._page.url  # will throw if closed
                return True
        except Exception:
            pass
        return False

    def stop(self) -> None:
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page = self._context = self._pw = None

    # ── Human-like actions ────────────────────────────────────────────

    def human_goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate with a brief pre-navigation pause."""
        _human_delay(0.3, 1.0)
        self.page().goto(url, wait_until=wait_until, timeout=30000)
        _human_delay(1.0, 2.5)

    def human_click(self, selector: str, timeout: int = 15000) -> None:
        """Move mouse naturally to element, then click."""
        page = self.page()
        el = page.locator(selector).first
        el.wait_for(state="visible", timeout=timeout)
        box = el.bounding_box()
        if box:
            # Move to element with bezier curve
            cur_x, cur_y = page.evaluate("() => [window.mouseX || 640, window.mouseY || 400]")
            target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            path = _bezier_curve((cur_x, cur_y), (target_x, target_y), steps=random.randint(15, 25))
            for px, py in path:
                page.mouse.move(px, py)
                time.sleep(random.uniform(0.005, 0.015))
            _human_delay(0.1, 0.3)
        el.click()
        _human_delay(0.3, 0.8)

    def human_type(self, selector: str, text: str, clear_first: bool = True) -> None:
        """Click field and type with human-like speed."""
        page = self.page()
        el = page.locator(selector).first
        el.wait_for(state="visible", timeout=10000)
        el.click()
        _human_delay(0.2, 0.5)
        if clear_first:
            el.select_all()
            page.keyboard.press("Delete")
            _human_delay(0.1, 0.3)
        _human_type(page, text)

    def human_scroll(self, direction: str = "down", amount: int | None = None) -> None:
        """Scroll naturally with variable speed."""
        page = self.page()
        if amount is None:
            amount = random.randint(200, 600)
        delta = amount if direction == "down" else -amount
        # Scroll in small increments
        steps = random.randint(3, 8)
        per_step = delta // steps
        for _ in range(steps):
            page.mouse.wheel(0, per_step)
            time.sleep(random.uniform(0.05, 0.15))
        _human_delay(0.3, 0.8)


# ─────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────

def _goto(url: str, wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> ToolResult:
    sess = _get()
    sess.human_goto(url, wait_until=wait_until)
    page = sess.page()
    return ToolResult(ok=True, content=f"loaded: {page.url} | title: {page.title()}")


def _click(selector: str, human: bool = True) -> ToolResult:
    sess = _get()
    try:
        if human:
            sess.human_click(selector)
        else:
            sess.page().click(selector, timeout=15000)
        return ToolResult(ok=True, content=f"clicked: {selector}")
    except Exception as e:
        return ToolResult(ok=False, content=f"click failed on '{selector}': {e}")


def _fill(selector: str, value: str, human: bool = True) -> ToolResult:
    sess = _get()
    try:
        if human:
            sess.human_type(selector, value)
        else:
            sess.page().fill(selector, value, timeout=15000)
        return ToolResult(ok=True, content=f"filled '{selector}' with {len(value)} chars")
    except Exception as e:
        return ToolResult(ok=False, content=f"fill failed on '{selector}': {e}")


def _scroll(direction: str = "down", amount: int = 400) -> ToolResult:
    _get().human_scroll(direction=direction, amount=amount)
    return ToolResult(ok=True, content=f"scrolled {direction} {amount}px")


def _wait(seconds: float = 1.5) -> ToolResult:
    """Explicit wait — useful between actions to appear more human."""
    actual = min(max(seconds, 0.1), 30.0)
    time.sleep(actual)
    return ToolResult(ok=True, content=f"waited {actual:.1f}s")


def _snapshot(max_chars: int = 6000) -> ToolResult:
    page = _get().page()
    try:
        text = page.evaluate("document.body.innerText")
    except Exception:
        text = ""
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…[truncated]"
    return ToolResult(
        ok=True,
        content=text,
        data={"url": page.url, "title": page.title()},
    )


def _get_html(selector: str = "body", max_chars: int = 8000) -> ToolResult:
    """Get inner HTML of a selector — useful for scraping structured data."""
    page = _get().page()
    try:
        html = page.inner_html(selector, timeout=10000)
        if len(html) > max_chars:
            html = html[:max_chars] + "\n…[truncated]"
        return ToolResult(ok=True, content=html)
    except Exception as e:
        return ToolResult(ok=False, content=f"get_html failed: {e}")


def _eval_js(script: str) -> ToolResult:
    page = _get().page()
    try:
        out: Any = page.evaluate(script)
        return ToolResult(ok=True, content=repr(out)[:8000])
    except Exception as e:
        return ToolResult(ok=False, content=f"eval failed: {e}")


def _screenshot(path: str | None = None, full_page: bool = False) -> ToolResult:
    page = _get().page()
    try:
        img = page.screenshot(full_page=full_page)
        if path:
            Path(path).write_bytes(img)
            return ToolResult(ok=True, content=f"saved → {path} ({len(img)} bytes)")
        b64 = base64.b64encode(img).decode("ascii")
        return ToolResult(
            ok=True,
            content=f"screenshot captured ({len(img)} bytes)",
            data={"png_b64": b64},
        )
    except Exception as e:
        return ToolResult(ok=False, content=f"screenshot failed: {e}")


def _new_tab(url: str | None = None) -> ToolResult:
    sess = _get()
    page = sess.new_tab(url)
    tabs = sess.all_tabs()
    return ToolResult(
        ok=True,
        content=f"new tab opened (index {len(tabs)-1})" + (f", navigated to {url}" if url else ""),
        data={"tab_count": len(tabs)},
    )


def _switch_tab(index: int) -> ToolResult:
    ok = _get().switch_tab(index)
    if ok:
        page = _get().page()
        return ToolResult(ok=True, content=f"switched to tab {index}: {page.url}")
    return ToolResult(ok=False, content=f"no tab at index {index}")


def _list_tabs() -> ToolResult:
    tabs = _get().all_tabs()
    lines = [f"[{i}] {t.url} — {t.title()}" for i, t in enumerate(tabs)]
    return ToolResult(ok=True, content="\n".join(lines) or "(no tabs)", data={"count": len(tabs)})


def _close_tab(index: int | None = None) -> ToolResult:
    sess = _get()
    tabs = sess.all_tabs()
    if index is None:
        index = len(tabs) - 1
    if 0 <= index < len(tabs):
        tabs[index].close()
        remaining = sess.all_tabs()
        if remaining:
            sess._page = remaining[-1]
        return ToolResult(ok=True, content=f"closed tab {index}")
    return ToolResult(ok=False, content=f"no tab at index {index}")


def _hover(selector: str) -> ToolResult:
    """Hover over an element (triggers tooltips, dropdowns, etc.)."""
    sess = _get()
    try:
        sess.human_click(selector)  # move mouse there
        sess.page().hover(selector, timeout=10000)
        _human_delay(0.3, 0.8)
        return ToolResult(ok=True, content=f"hovered: {selector}")
    except Exception as e:
        return ToolResult(ok=False, content=f"hover failed: {e}")


def _press_key(key: str) -> ToolResult:
    """Press a keyboard key (Enter, Escape, Tab, ArrowDown, etc.)."""
    _get().page().keyboard.press(key)
    _human_delay(0.1, 0.3)
    return ToolResult(ok=True, content=f"pressed: {key}")


def _select_option(selector: str, value: str) -> ToolResult:
    """Select an option from a <select> dropdown."""
    try:
        _get().page().select_option(selector, value=value, timeout=10000)
        return ToolResult(ok=True, content=f"selected '{value}' in {selector}")
    except Exception as e:
        return ToolResult(ok=False, content=f"select failed: {e}")


def _wait_for(selector: str, state: str = "visible", timeout_ms: int = 15000) -> ToolResult:
    """Wait for an element to reach a state: visible | hidden | attached | detached."""
    try:
        _get().page().wait_for_selector(selector, state=state, timeout=timeout_ms)
        return ToolResult(ok=True, content=f"'{selector}' is now {state}")
    except Exception as e:
        return ToolResult(ok=False, content=f"wait_for failed: {e}")


def _close_browser() -> ToolResult:
    global _singleton
    with _session_lock:
        if _singleton is not None:
            _singleton.stop()
            _singleton = None
    return ToolResult(ok=True, content="browser closed")


def _connect_real_chrome(port: int = 9222) -> ToolResult:
    """Connect Ghost to your real Chrome browser via CDP.
    
    This lets Ghost control your actual Chrome with all your cookies,
    logins, and extensions — no bot detection.
    
    Chrome must be running with remote debugging enabled.
    Ghost will launch Chrome with debugging if it's not already running.
    """
    import sys

    # First try to connect to already-running Chrome
    global _singleton
    with _session_lock:
        if _singleton is not None:
            _singleton.stop()
            _singleton = None

    # Check if Chrome is already running with CDP
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/json", timeout=2)
        # Chrome already running with CDP
    except Exception:
        # Launch Chrome with CDP enabled
        _system = platform.system()
        chrome_paths = []

        if _system == "Windows":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
        elif _system == "Darwin":
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        else:
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]

        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
        if not chrome_exe:
            return ToolResult(
                ok=False,
                content=(
                    f"Chrome not found. Please:\n"
                    f"1. Open Chrome manually\n"
                    f"2. Close it completely\n"
                    f"3. Relaunch with: chrome.exe --remote-debugging-port={port}\n"
                    f"   (Windows: right-click Chrome shortcut → Properties → add to Target)"
                )
            )

        # Launch Chrome with CDP
        try:
            if _system == "Windows":
                subprocess.Popen(
                    [chrome_exe, f"--remote-debugging-port={port}", "--no-first-run"],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                subprocess.Popen(
                    [chrome_exe, f"--remote-debugging-port={port}", "--no-first-run"],
                    start_new_session=True,
                )
            time.sleep(2)  # Wait for Chrome to start
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to launch Chrome: {e}")

    # Now connect via CDP
    try:
        with _session_lock:
            sess = BrowserSession(cdp_mode=True, cdp_port=port)
            sess.start()
            if sess._cdp_mode:
                _singleton = sess
                page = sess.page()
                return ToolResult(
                    ok=True,
                    content=f"✅ Connected to your real Chrome! Current page: {page.url}\n"
                            f"Ghost now controls your actual browser with all your cookies and logins.\n"
                            f"No bot detection — this is your real Chrome.",
                )
            else:
                return ToolResult(
                    ok=False,
                    content=(
                        f"CDP connection failed. Make sure Chrome is running with:\n"
                        f"  --remote-debugging-port={port}\n\n"
                        f"Windows: Run this in PowerShell:\n"
                        f'  & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port={port}'
                    )
                )
    except Exception as e:
        return ToolResult(ok=False, content=f"CDP connection error: {e}")


def _get_cookies(domain: str | None = None) -> ToolResult:
    """Get cookies from the current browser context."""
    ctx = _get()._context
    if ctx is None:
        return ToolResult(ok=False, content="no browser context")
    cookies = ctx.cookies()
    if domain:
        cookies = [c for c in cookies if domain in c.get("domain", "")]
    summary = [f"{c['name']}={c['value'][:20]}... (domain={c['domain']})" for c in cookies[:20]]
    return ToolResult(
        ok=True,
        content=f"{len(cookies)} cookies" + ("\n" + "\n".join(summary) if summary else ""),
        data={"count": len(cookies)},
    )


def _find_elements(selector: str, attribute: str | None = None, max_results: int = 20) -> ToolResult:
    """Find elements by selector and optionally extract an attribute."""
    page = _get().page()
    try:
        els = page.locator(selector).all()[:max_results]
        results = []
        for el in els:
            if attribute:
                val = el.get_attribute(attribute) or ""
                results.append(val)
            else:
                results.append(el.inner_text()[:200])
        return ToolResult(
            ok=True,
            content=f"found {len(els)} elements\n" + "\n".join(f"  [{i}] {r}" for i, r in enumerate(results)),
            data={"count": len(els)},
        )
    except Exception as e:
        return ToolResult(ok=False, content=f"find_elements failed: {e}")


# ─────────────────────────────────────────────────────────────────────
# Tool registry builder
# ─────────────────────────────────────────────────────────────────────

def get_browser_tools() -> list[Tool]:
    """Return browser tools, or empty list if Playwright is missing."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return []

    return [
        Tool(
            name="browser_goto",
            description=(
                "Navigate to a URL in Ghost's persistent stealth browser. "
                "Uses human-like delays. Cookies persist across sessions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "wait_until": {
                        "type": "string",
                        "enum": ["load", "domcontentloaded", "networkidle"],
                        "default": "domcontentloaded",
                    },
                    "timeout_ms": {"type": "integer", "default": 30000},
                },
                "required": ["url"],
            },
            handler=_goto,
        ),
        Tool(
            name="browser_click",
            description=(
                "Click an element by CSS selector or text. "
                "human=true (default) moves the mouse naturally along a bezier curve."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "human": {"type": "boolean", "default": True},
                },
                "required": ["selector"],
            },
            handler=_click,
        ),
        Tool(
            name="browser_fill",
            description=(
                "Type text into an input field. "
                "human=true (default) types at realistic WPM with natural variance."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                    "human": {"type": "boolean", "default": True},
                },
                "required": ["selector", "value"],
            },
            handler=_fill,
        ),
        Tool(
            name="browser_scroll",
            description="Scroll the page up or down with natural speed variation.",
            input_schema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                    "amount": {"type": "integer", "default": 400, "description": "Pixels to scroll"},
                },
            },
            handler=_scroll,
        ),
        Tool(
            name="browser_wait",
            description="Wait for N seconds — use between actions to appear more human.",
            input_schema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "default": 1.5},
                },
            },
            handler=_wait,
        ),
        Tool(
            name="browser_snapshot",
            description="Read visible text of the current page. Use to understand page state before acting.",
            input_schema={
                "type": "object",
                "properties": {
                    "max_chars": {"type": "integer", "default": 6000},
                },
            },
            handler=_snapshot,
        ),
        Tool(
            name="browser_get_html",
            description="Get inner HTML of a CSS selector. Useful for scraping structured data.",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "default": "body"},
                    "max_chars": {"type": "integer", "default": 8000},
                },
            },
            handler=_get_html,
        ),
        Tool(
            name="browser_find_elements",
            description=(
                "Find all elements matching a CSS selector and return their text or an attribute. "
                "Great for scraping lists, tweets, comments, etc."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "attribute": {
                        "type": "string",
                        "description": "Optional HTML attribute to extract (e.g. 'href', 'data-id'). Omit for inner text.",
                    },
                    "max_results": {"type": "integer", "default": 20},
                },
                "required": ["selector"],
            },
            handler=_find_elements,
        ),
        Tool(
            name="browser_screenshot",
            description=(
                "Screenshot the current browser page. "
                "Returns base64 PNG inline for vision analysis if no path given."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional file path to save PNG."},
                    "full_page": {"type": "boolean", "default": False},
                },
            },
            handler=_screenshot,
        ),
        Tool(
            name="browser_eval",
            description=(
                "Run JavaScript in the page context. Powerful escape hatch for anything "
                "not covered by other browser tools."
            ),
            input_schema={
                "type": "object",
                "properties": {"script": {"type": "string"}},
                "required": ["script"],
            },
            handler=_eval_js,
            dangerous=True,
        ),
        Tool(
            name="browser_press_key",
            description="Press a keyboard key: Enter, Escape, Tab, ArrowDown, Backspace, etc.",
            input_schema={
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
            handler=_press_key,
        ),
        Tool(
            name="browser_hover",
            description="Hover over an element to trigger tooltips, dropdowns, or hover states.",
            input_schema={
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
            handler=_hover,
        ),
        Tool(
            name="browser_select",
            description="Select an option from a <select> dropdown by value.",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["selector", "value"],
            },
            handler=_select_option,
        ),
        Tool(
            name="browser_wait_for",
            description="Wait for an element to become visible, hidden, attached, or detached.",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "state": {
                        "type": "string",
                        "enum": ["visible", "hidden", "attached", "detached"],
                        "default": "visible",
                    },
                    "timeout_ms": {"type": "integer", "default": 15000},
                },
                "required": ["selector"],
            },
            handler=_wait_for,
        ),
        Tool(
            name="browser_new_tab",
            description="Open a new browser tab, optionally navigating to a URL.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
            },
            handler=_new_tab,
        ),
        Tool(
            name="browser_list_tabs",
            description="List all open browser tabs with their URLs and titles.",
            input_schema={"type": "object", "properties": {}},
            handler=_list_tabs,
        ),
        Tool(
            name="browser_switch_tab",
            description="Switch to a browser tab by index (from browser_list_tabs).",
            input_schema={
                "type": "object",
                "properties": {"index": {"type": "integer"}},
                "required": ["index"],
            },
            handler=_switch_tab,
        ),
        Tool(
            name="browser_close_tab",
            description="Close a browser tab by index. Omit index to close the current tab.",
            input_schema={
                "type": "object",
                "properties": {"index": {"type": "integer"}},
            },
            handler=_close_tab,
        ),
        Tool(
            name="browser_get_cookies",
            description="Get cookies from the browser context. Optionally filter by domain.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Filter by domain substring, e.g. 'twitter.com'"},
                },
            },
            handler=_get_cookies,
        ),
        Tool(
            name="browser_close",
            description="Close Ghost's browser session and free resources.",
            input_schema={"type": "object", "properties": {}},
            handler=_close_browser,
        ),
        Tool(
            name="browser_connect_chrome",
            description=(
                "Connect Ghost to YOUR REAL Chrome browser — uses your actual logins, "
                "cookies, and extensions. No bot detection, no captchas. "
                "This is the recommended way to control websites where you're already logged in. "
                "Ghost will launch Chrome with remote debugging if needed."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 9222,
                        "description": "CDP debug port (default 9222)",
                    },
                },
            },
            handler=_connect_real_chrome,
        ),
    ]
