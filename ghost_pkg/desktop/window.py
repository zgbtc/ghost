"""Cross-platform window management.

Windows: pygetwindow (win32)
macOS:   AppKit / Quartz (native, no extra deps on macOS)
Linux:   xdotool (shell) or ewmh (python-ewmh)

All platforms expose the same interface:
    Windows.list()          → list of WindowInfo
    Windows.focus(title)    → bool
    Windows.get_active()    → WindowInfo | None
    Windows.move(title, x, y, w, h)
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

_SYSTEM = platform.system()


@dataclass
class WindowInfo:
    title: str
    left: int
    top: int
    width: int
    height: int
    is_active: bool = False
    handle: object = None  # platform-specific handle


class Windows:
    @staticmethod
    def list() -> list[WindowInfo]:
        if _SYSTEM == "Windows":
            return _list_windows_win()
        elif _SYSTEM == "Darwin":
            return _list_windows_mac()
        else:
            return _list_windows_linux()

    @staticmethod
    def focus(title_substring: str) -> bool:
        """Bring a window matching the title to the foreground."""
        if _SYSTEM == "Windows":
            return _focus_win(title_substring)
        elif _SYSTEM == "Darwin":
            return _focus_mac(title_substring)
        else:
            return _focus_linux(title_substring)

    @staticmethod
    def get_active() -> Optional[WindowInfo]:
        wins = Windows.list()
        for w in wins:
            if w.is_active:
                return w
        return None

    @staticmethod
    def move(title_substring: str, x: int, y: int, w: int, h: int) -> bool:
        """Move and resize a window."""
        if _SYSTEM == "Windows":
            return _move_win(title_substring, x, y, w, h)
        elif _SYSTEM == "Darwin":
            return _move_mac(title_substring, x, y, w, h)
        else:
            return _move_linux(title_substring, x, y, w, h)


# ─────────────────────────────────────────────────────────────────────
# Windows implementation
# ─────────────────────────────────────────────────────────────────────

def _list_windows_win() -> list[WindowInfo]:
    try:
        import pygetwindow as gw
        wins = []
        active = gw.getActiveWindow()
        active_title = active.title if active else ""
        for w in gw.getAllWindows():
            if not w.title:
                continue
            wins.append(WindowInfo(
                title=w.title,
                left=w.left,
                top=w.top,
                width=w.width,
                height=w.height,
                is_active=(w.title == active_title),
                handle=w._hWnd,
            ))
        return wins
    except ImportError:
        return _list_windows_win32()


def _list_windows_win32() -> list[WindowInfo]:
    """Fallback using win32gui directly."""
    try:
        import win32gui
        wins = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    rect = win32gui.GetWindowRect(hwnd)
                    wins.append(WindowInfo(
                        title=title,
                        left=rect[0],
                        top=rect[1],
                        width=rect[2] - rect[0],
                        height=rect[3] - rect[1],
                        handle=hwnd,
                    ))

        win32gui.EnumWindows(callback, None)
        return wins
    except ImportError:
        return []


def _focus_win(title_substring: str) -> bool:
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title_substring)
        if wins:
            wins[0].activate()
            return True
    except Exception:
        pass
    try:
        import win32gui
        import win32con
        def callback(hwnd, _):
            if title_substring.lower() in win32gui.GetWindowText(hwnd).lower():
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return False
        win32gui.EnumWindows(callback, None)
        return True
    except Exception:
        return False


def _move_win(title_substring: str, x: int, y: int, w: int, h: int) -> bool:
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title_substring)
        if wins:
            wins[0].moveTo(x, y)
            wins[0].resizeTo(w, h)
            return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────
# macOS implementation (Apple Silicon + Intel)
# ─────────────────────────────────────────────────────────────────────

def _list_windows_mac() -> list[WindowInfo]:
    """List windows using Quartz CGWindowListCopyWindowInfo."""
    try:
        import Quartz
        options = Quartz.kCGWindowListOptionOnScreenOnly
        window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
        wins = []
        for w in window_list:
            title = w.get("kCGWindowName", "") or w.get("kCGWindowOwnerName", "")
            if not title:
                continue
            bounds = w.get("kCGWindowBounds", {})
            wins.append(WindowInfo(
                title=title,
                left=int(bounds.get("X", 0)),
                top=int(bounds.get("Y", 0)),
                width=int(bounds.get("Width", 0)),
                height=int(bounds.get("Height", 0)),
            ))
        return wins
    except ImportError:
        return _list_windows_mac_applescript()


def _list_windows_mac_applescript() -> list[WindowInfo]:
    """Fallback: list apps via AppleScript."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every process whose background only is false'],
            capture_output=True, text=True, timeout=5,
        )
        names = result.stdout.strip().split(", ")
        return [WindowInfo(title=n, left=0, top=0, width=0, height=0) for n in names if n]
    except Exception:
        return []


def _focus_mac(title_substring: str) -> bool:
    """Focus a macOS app by name using AppleScript."""
    try:
        script = f'tell application "{title_substring}" to activate'
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)
        return True
    except Exception:
        pass
    # Try partial match
    try:
        wins = _list_windows_mac()
        for w in wins:
            if title_substring.lower() in w.title.lower():
                script = f'tell application "{w.title}" to activate'
                subprocess.run(["osascript", "-e", script], timeout=5, check=False)
                return True
    except Exception:
        pass
    return False


def _move_mac(title_substring: str, x: int, y: int, w: int, h: int) -> bool:
    """Move/resize a macOS window via AppleScript."""
    try:
        script = f'''
tell application "{title_substring}"
    set bounds of front window to {{{x}, {y}, {x+w}, {y+h}}}
end tell
'''
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────
# Linux implementation
# ─────────────────────────────────────────────────────────────────────

def _list_windows_linux() -> list[WindowInfo]:
    """List windows using xdotool."""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", ""],
            capture_output=True, text=True, timeout=5,
        )
        wids = result.stdout.strip().split("\n")
        wins = []
        for wid in wids:
            if not wid.strip():
                continue
            try:
                name_result = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=2,
                )
                title = name_result.stdout.strip()
                if title:
                    wins.append(WindowInfo(title=title, left=0, top=0, width=0, height=0, handle=wid))
            except Exception:
                continue
        return wins
    except FileNotFoundError:
        return []


def _focus_linux(title_substring: str) -> bool:
    """Focus a window using xdotool."""
    try:
        subprocess.run(
            ["xdotool", "search", "--name", title_substring, "windowactivate"],
            timeout=5, check=False,
        )
        return True
    except FileNotFoundError:
        return False


def _move_linux(title_substring: str, x: int, y: int, w: int, h: int) -> bool:
    """Move/resize a window using xdotool."""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", title_substring],
            capture_output=True, text=True, timeout=5,
        )
        wid = result.stdout.strip().split("\n")[0]
        if wid:
            subprocess.run(
                ["xdotool", "windowmove", wid, str(x), str(y)],
                timeout=5, check=False,
            )
            subprocess.run(
                ["xdotool", "windowsize", wid, str(w), str(h)],
                timeout=5, check=False,
            )
            return True
    except Exception:
        pass
    return False
