"""Desktop control — Ghost's hands and eyes.

  perception/  — screen, windows, clipboard, files
  control/     — mouse, keyboard, app launching, shell
"""

from ghost.desktop.screen import Screen
from ghost.desktop.input import Mouse, Keyboard
from ghost.desktop.window import Windows
from ghost.desktop.clipboard import Clipboard
from ghost.desktop.shell import Shell

__all__ = ["Screen", "Mouse", "Keyboard", "Windows", "Clipboard", "Shell"]
