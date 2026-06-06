from __future__ import annotations

import os
import sys


def enable_sharp_display() -> None:
    if sys.platform == "win32":
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def ui_scale() -> float:
    try:
        import pygame
        dpi = float(pygame.display.get_window_dpi())
        if dpi > 0:
            return max(1.0, min(2.0, dpi / 96.0))
    except Exception:
        pass
    return 1.0