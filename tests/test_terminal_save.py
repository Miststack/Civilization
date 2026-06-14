from __future__ import annotations

from pathlib import Path

from engine.game import GameConfig, GameState
from engine.models import Action, TechType
from engine.save import save_game, save_path
from engine.terminal_save import format_slot_line, terminal_load, terminal_save


def test_format_slot_line_empty(tmp_path: Path) -> None:
    assert "（空）" in format_slot_line(0, tmp_path)


def test_format_slot_line_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "quicksave.json"
    path.write_text("{}", encoding="utf-8")
    line = format_slot_line(0, tmp_path)
    assert "损坏" in line or "无法读取" in line


def test_terminal_save_and_load(tmp_path: Path, monkeypatch) -> None:
    state = GameState(GameConfig(map_size=8, total_turns=10, seed=3))
    state.do_turn(Action.research(TechType.AGRICULTURE))

    slots: list[str] = ["0"]

    def fake_input(_: str = "") -> str:
        return slots.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    assert terminal_save(state, tmp_path) is True
    assert save_path(0, tmp_path).is_file()

    slots = ["0"]
    loaded = terminal_load(tmp_path)
    assert loaded is not None
    assert loaded.turn == state.turn
    assert loaded.tech_unlocked == state.tech_unlocked
