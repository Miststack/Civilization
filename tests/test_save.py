from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.game import GameConfig, GameState
from engine.models import Action, BuildingType, TechType
from engine.save import load_game, save_game, save_path, slot_summary, state_from_dict, state_to_dict


def test_roundtrip_save_load(tmp_path: Path) -> None:
    state = GameState(GameConfig(map_size=8, total_turns=10, seed=7))
    state.do_turn(Action.research(TechType.AGRICULTURE))
    path = tmp_path / "test.json"
    save_game(state, path)
    loaded = load_game(path)
    assert loaded.turn == state.turn
    assert loaded.resources == state.resources
    assert loaded.tech_unlocked == state.tech_unlocked
    assert len(loaded.cities) == len(state.cities)
    assert loaded.config.seed == 7


def test_slot_summary_missing(tmp_path: Path) -> None:
    assert slot_summary(tmp_path / "missing.json") is None


def test_slot_summary_exists(tmp_path: Path) -> None:
    state = GameState(GameConfig(8, 10, seed=1))
    path = tmp_path / "slot1.json"
    save_game(state, path)
    meta = slot_summary(path)
    assert meta is not None
    assert meta["turn"] == 1
    assert meta["map_size"] == 8


def test_state_from_dict_rejects_bad_version() -> None:
    with pytest.raises(ValueError, match="版本"):
        state_from_dict({"version": 99, "config": {"map_size": 8, "total_turns": 10, "seed": 0}})


def test_save_path_slots() -> None:
    assert save_path(0).name == "quicksave.json"
    assert save_path(2).name == "slot2.json"
