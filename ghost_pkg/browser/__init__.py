"""Browser automation via Playwright (lazy import — only loaded if used)."""

from ghost.browser.session import BrowserSession, get_browser_tools

__all__ = ["BrowserSession", "get_browser_tools"]
