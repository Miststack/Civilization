"""GUI 用户偏好持久化（主题、缩放）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui.theme import DEFAULT_GUI_SCALE

PREFS_VERSION = 1
DEFAULT_PREFS_PATH = Path("saves/gui_prefs.json")


def load_gui_prefs(path: Path | str = DEFAULT_PREFS_PATH) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    if int(data.get("version", 0)) != PREFS_VERSION:
        return {}
    return data


def save_gui_prefs(
    *,
    light_theme: bool,
    gui_scale: float,
    path: Path | str = DEFAULT_PREFS_PATH,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": PREFS_VERSION,
        "light_theme": bool(light_theme),
        "gui_scale": round(max(0.85, min(2.0, float(gui_scale))), 2),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def merge_gui_prefs(
    *,
    light_theme: bool,
    gui_scale: float,
    cli_light: bool,
    cli_scale: float,
    path: Path | str = DEFAULT_PREFS_PATH,
) -> tuple[bool, float]:
    """CLI 显式指定 `--light` / `--gui-scale` 时优先于本地存档。"""
    prefs = load_gui_prefs(path)
    out_light = light_theme
    out_scale = gui_scale
    if prefs:
        if not cli_light:
            out_light = bool(prefs.get("light_theme", light_theme))
        if abs(cli_scale - DEFAULT_GUI_SCALE) < 1e-6:
            saved = prefs.get("gui_scale")
            if saved is not None:
                out_scale = float(saved)
        else:
            out_scale = float(cli_scale)
    elif abs(cli_scale - DEFAULT_GUI_SCALE) >= 1e-6:
        out_scale = float(cli_scale)
    return out_light, max(0.85, min(2.0, out_scale))
