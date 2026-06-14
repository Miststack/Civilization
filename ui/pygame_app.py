"""Pygame GUI 入口（兼容旧 import 路径）。"""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from engine.game import GameState
from ui.app import CivGameApp
from ui.prefs import DEFAULT_AUTO_DELAY_MS, DEFAULT_IL_TOP_K
from ui.theme import DEFAULT_GUI_SCALE

__all__ = ["CivGameApp", "run_pygame_game", "main"]

def run_pygame_game(
    state: GameState,
    *,
    agent: Optional[object] = None,
    auto_delay_ms: int = DEFAULT_AUTO_DELAY_MS,
    title: str = "简化文明",
    light_theme: bool = False,
    gui_scale: float = DEFAULT_GUI_SCALE,
    play_mode: Optional[str] = None,
    il_top_k: int = DEFAULT_IL_TOP_K,
) -> int:
    app = CivGameApp(
        state,
        agent=agent,
        auto_delay_ms=auto_delay_ms,
        title=title,
        light_theme=light_theme,
        gui_scale=gui_scale,
        play_mode=play_mode,
        il_top_k=il_top_k,
    )
    return app.run()


def main(argv: Optional[Sequence[str]] = None) -> None:
    from main import main as cli_main

    if argv is None:
        argv = sys.argv[1:]
    if "--gui" not in argv and "--play" not in argv:
        argv = ["--gui", "--play", "human", *argv]
    sys.argv = [sys.argv[0], *argv]
    cli_main()


if __name__ == "__main__":
    main()
