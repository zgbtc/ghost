"""Clipboard read/write."""

from __future__ import annotations

import pyperclip


class Clipboard:
    @staticmethod
    def get() -> str | None:
        try:
            return pyperclip.paste()
        except Exception:
            return None

    @staticmethod
    def set(text: str) -> None:
        pyperclip.copy(text)
