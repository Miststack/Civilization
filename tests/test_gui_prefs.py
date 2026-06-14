from __future__ import annotations

from pathlib import Path

from ui.prefs import load_gui_prefs, merge_gui_prefs, save_gui_prefs
from ui.theme import DEFAULT_GUI_SCALE


def test_save_and_load_prefs(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(light_theme=True, gui_scale=1.25, path=path)
    prefs = load_gui_prefs(path)
    assert prefs["light_theme"] is True
    assert prefs["gui_scale"] == 1.25


def test_merge_cli_overrides_saved(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(light_theme=True, gui_scale=1.25, path=path)
    light, scale = merge_gui_prefs(
        light_theme=False,
        gui_scale=1.0,
        cli_light=True,
        cli_scale=1.5,
        path=path,
    )
    assert light is False
    assert scale == 1.5


def test_merge_uses_saved_when_cli_default(tmp_path: Path) -> None:
    path = tmp_path / "gui_prefs.json"
    save_gui_prefs(light_theme=True, gui_scale=1.1, path=path)
    light, scale = merge_gui_prefs(
        light_theme=False,
        gui_scale=DEFAULT_GUI_SCALE,
        cli_light=False,
        cli_scale=DEFAULT_GUI_SCALE,
        path=path,
    )
    assert light is True
    assert scale == 1.1
