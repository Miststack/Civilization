"""图形界面（Pygame）。"""

from __future__ import annotations

__all__ = ["run_pygame_game"]


def run_pygame_game(*args, **kwargs):
    from ui.pygame_app import run_pygame_game as _run

    return _run(*args, **kwargs)
