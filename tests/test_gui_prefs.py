from __future__ import annotations

from pathlib import Path

from ui.prefs import (
    DEFAULT_AUTO_DELAY_MS,
    DEFAULT_IL_TOP_K,
    load_gui_prefs,
    merge_gui_prefs,
    save_gui_prefs,
)
from ui.theme import DEFAULT_GUI_SCALE


def test_save_and_load_prefs(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(
        light_theme=True,
        gui_scale=1.25,
        auto_delay_ms=600,
        il_top_k=8,
        path=path,
    )
    prefs = load_gui_prefs(path)
    assert prefs["version"] == 2
    assert prefs["light_theme"] is True
    assert prefs["gui_scale"] == 1.25
    assert prefs["auto_delay_ms"] == 600
    assert prefs["il_top_k"] == 8


def test_merge_cli_overrides_saved(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(light_theme=True, gui_scale=1.25, auto_delay_ms=800, il_top_k=4, path=path)
    light, scale, delay, top_k = merge_gui_prefs(
        light_theme=False,
        gui_scale=1.0,
        cli_light=True,
        cli_scale=1.5,
        cli_auto_delay=300,
        cli_il_top_k=12,
        path=path,
    )
    assert light is False
    assert scale == 1.5
    assert delay == 300
    assert top_k == 12


def test_merge_uses_saved_when_cli_default(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(light_theme=True, gui_scale=1.1, auto_delay_ms=500, il_top_k=8, path=path)
    light, scale, delay, top_k = merge_gui_prefs(
        light_theme=False,
        gui_scale=DEFAULT_GUI_SCALE,
        cli_light=False,
        cli_scale=DEFAULT_GUI_SCALE,
        path=path,
    )
    assert light is True
    assert scale == 1.1
    assert delay == 500
    assert top_k == 8


def test_load_v1_prefs_still_works(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    path.write_text(
        '{"version": 1, "light_theme": false, "gui_scale": 1.15}',
        encoding="utf-8",
    )
    prefs = load_gui_prefs(path)
    assert prefs["gui_scale"] == 1.15
    light, scale, delay, top_k = merge_gui_prefs(
        light_theme=False,
        gui_scale=DEFAULT_GUI_SCALE,
        cli_light=False,
        cli_scale=DEFAULT_GUI_SCALE,
        path=path,
    )
    assert light is False
    assert scale == 1.15
    assert delay == DEFAULT_AUTO_DELAY_MS
    assert top_k == DEFAULT_IL_TOP_K
