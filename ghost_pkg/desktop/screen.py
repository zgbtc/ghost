"""Cross-platform screenshot capture.

Uses mss (much faster than PIL/pyautogui screenshot) on all platforms.
Falls back to pyautogui if mss is not installed.

Platform support:
- Windows: mss (native GDI)
- macOS Apple Silicon: mss (CoreGraphics)
- macOS Intel: mss (CoreGraphics)
- Linux X11: mss
- Linux Wayland: scrot/gnome-screenshot fallback
"""

from __future__ import annotations

import base64
import io
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_SYSTEM = platform.system()


@dataclass
class Screenshot:
    width: int
    height: int
    _data: bytes  # raw PNG bytes

    def to_base64(self) -> str:
        return base64.b64encode(self._data).decode("ascii")

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self._data)

    @property
    def png_bytes(self) -> bytes:
        return self._data


class Screen:
    """Cross-platform screenshot capture."""

    def capture(self, monitor: int = 0) -> Screenshot:
        """Capture a monitor. monitor=0 means primary/all."""
        try:
            return self._capture_mss(monitor)
        except Exception:
            return self._capture_pyautogui()

    def primary(self) -> Screenshot:
        return self.capture(monitor=0)

    def _capture_mss(self, monitor: int) -> Screenshot:
        try:
            import mss
            import mss.tools
        except ImportError:
            raise RuntimeError("mss not installed. Run: pip install mss")

        with mss.mss() as sct:
            monitors = sct.monitors
            # monitors[0] = all monitors combined, monitors[1] = primary
            idx = min(monitor + 1, len(monitors) - 1)
            mon = monitors[idx]
            img = sct.grab(mon)

            # Convert to PNG bytes
            png_bytes = mss.tools.to_png(img.rgb, img.size)
            return Screenshot(
                width=img.width,
                height=img.height,
                _data=png_bytes,
            )

    def _capture_pyautogui(self) -> Screenshot:
        try:
            import pyautogui
            from PIL import Image
        except ImportError:
            raise RuntimeError(
                "Neither mss nor pyautogui+Pillow available. "
                "Run: pip install mss  OR  pip install pyautogui pillow"
            )

        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        return Screenshot(width=img.width, height=img.height, _data=data)

    def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> Screenshot:
        """Capture a specific region of the screen."""
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                region = {"left": left, "top": top, "width": width, "height": height}
                img = sct.grab(region)
                png_bytes = mss.tools.to_png(img.rgb, img.size)
                return Screenshot(width=img.width, height=img.height, _data=png_bytes)
        except ImportError:
            pass

        try:
            import pyautogui
            img = pyautogui.screenshot(region=(left, top, width, height))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()
            return Screenshot(width=img.width, height=img.height, _data=data)
        except Exception as e:
            raise RuntimeError(f"Screenshot failed: {e}")

    def monitor_count(self) -> int:
        """Return the number of monitors."""
        try:
            import mss
            with mss.mss() as sct:
                return len(sct.monitors) - 1  # subtract the "all" entry
        except ImportError:
            return 1
