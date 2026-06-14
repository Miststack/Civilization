"""GUI 用户偏好持久化（主题、缩放、旁观速度、IL top-k）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui.theme import DEFAULT_GUI_SCALE

PREFS_VERSION = 2
DEFAULT_PREFS_PATH = Path("saves/gui_prefs.json")
DEFAULT_AUTO_DELAY_MS = 450
DEFAULT_IL_TOP_K = 8
IL_TOP_K_MIN = 1
IL_TOP_K_MAX = 16


def _clamp_auto_delay(ms: int) -> int:
    return max(50, min(3000, int(ms)))


def _clamp_il_top_k(k: int) -> int:
    return max(IL_TOP_K_MIN, min(IL_TOP_K_MAX, int(k)))


def load_gui_prefs(path: Path | str = DEFAULT_PREFS_PATH) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    version = int(data.get("version", 0))
    if version not in (1, PREFS_VERSION):
        return {}
    return data


def save_gui_prefs(
    *,
    light_theme: bool,
    gui_scale: float,
    auto_delay_ms: int = DEFAULT_AUTO_DELAY_MS,
    il_top_k: int = DEFAULT_IL_TOP_K,
    path: Path | str = DEFAULT_PREFS_PATH,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": PREFS_VERSION,
        "light_theme": bool(light_theme),
        "gui_scale": round(max(0.85, min(2.0, float(gui_scale))), 2),
        "auto_delay_ms": _clamp_auto_delay(auto_delay_ms),
        "il_top_k": _clamp_il_top_k(il_top_k),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def merge_gui_prefs(
    *,
    light_theme: bool,
    gui_scale: float,
    cli_light: bool,
    cli_scale: float,
    auto_delay_ms: int = DEFAULT_AUTO_DELAY_MS,
    il_top_k: int = DEFAULT_IL_TOP_K,
    cli_auto_delay: int | None = None,
    cli_il_top_k: int | None = None,
    path: Path | str = DEFAULT_PREFS_PATH,
) -> tuple[bool, float, int, int]:
    """CLI 显式指定 `--light` / `--gui-scale` / `--gui-delay` / `--il-top-k` 时优先于本地存档。"""
    prefs = load_gui_prefs(path)
    out_light = light_theme
    out_scale = gui_scale
    out_auto = auto_delay_ms
    out_il = il_top_k
    if prefs:
        if not cli_light:
            out_light = bool(prefs.get("light_theme", light_theme))
        if abs(cli_scale - DEFAULT_GUI_SCALE) < 1e-6:
            saved = prefs.get("gui_scale")
            if saved is not None:
                out_scale = float(saved)
        else:
            out_scale = float(cli_scale)
        if cli_auto_delay is None:
            saved = prefs.get("auto_delay_ms")
            if saved is not None:
                out_auto = int(saved)
        else:
            out_auto = cli_auto_delay
        if cli_il_top_k is None:
            saved = prefs.get("il_top_k")
            if saved is not None:
                out_il = int(saved)
        else:
            out_il = cli_il_top_k
    else:
        if abs(cli_scale - DEFAULT_GUI_SCALE) >= 1e-6:
            out_scale = float(cli_scale)
        if cli_auto_delay is not None:
            out_auto = cli_auto_delay
        if cli_il_top_k is not None:
            out_il = cli_il_top_k
    return (
        out_light,
        max(0.85, min(2.0, out_scale)),
        _clamp_auto_delay(out_auto),
        _clamp_il_top_k(out_il),
    )
