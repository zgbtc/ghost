"""Demonstration learning — record a human doing a task, distill into a skill.

Inspired by ShowUI-Aloha: instead of prompting Ghost to figure it out, you
*show* it how. Ghost watches your mouse/keyboard + periodic screenshots,
then turns the trace into a markdown SOP it can replay later.
"""

from ghost.demo.recorder import DemoRecorder, DemoEvent

__all__ = ["DemoRecorder", "DemoEvent"]
