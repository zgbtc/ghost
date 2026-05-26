"""Atomic tools — Ghost's only system interface.

Inspired by GenericAgent's "9 atomic tools" philosophy: keep the toolset narrow
and let `code_run` create new capabilities at runtime.

Categories:
  - Perception:  screen_capture, list_windows, read_clipboard
  - Control:     mouse_*, keyboard_*, focus_window, launch_app
  - Compute:     code_run, shell_run
  - Files:       file_read, file_write, file_patch
  - Web:         web_fetch, web_search (optional)
  - Memory:      remember, recall, write_skill, log_failure
  - Meta:        ask_user
"""

from ghost.tools.registry import ToolRegistry, Tool, ToolResult
from ghost.tools.builtin import register_all_builtins

__all__ = ["ToolRegistry", "Tool", "ToolResult", "register_all_builtins"]
