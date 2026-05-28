from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from game import GameConfig, GameState
from main import _action_label, _partition_legal
from models import Action, ActionType, BuildingType, TechType


def test_action_label_variants() -> None:
    assert _action_label(Action.skip()) == "跳过本回合"
    assert "(3, 4)" in _action_label(Action.build_city(3, 4))
    assert "farm" in _action_label(Action.build_building(2, BuildingType.FARM))
    assert "mining" in _action_label(Action.research(TechType.MINING))


def test_partition_legal_groups() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    skip_a, cities, buildings, techs = _partition_legal(s)
    assert skip_a[0].type == ActionType.SKIP
    assert all(a.type == ActionType.BUILD_CITY for a in cities)
    assert all(a.type == ActionType.BUILD_BUILDING for a in buildings)
    assert all(a.type == ActionType.RESEARCH for a in techs)


@pytest.mark.parametrize(
    "play",
    ["human", "random", "greedy", "planned"],
)
def test_main_smoke_subprocess(play: str) -> None:
    root = Path(__file__).resolve().parent.parent
    script = root / "main.py"
    inp = "0\n" if play == "human" else ""
    cmd = [
        sys.executable,
        str(script),
        "--map-size",
        "8",
        "--turns",
        "2",
        "--seed",
        "0",
        "--play",
        play,
    ]
    if play != "human":
        cmd.append("--quiet")
    proc = subprocess.run(
        cmd,
        input=inp,
        text=True,
        cwd=str(root),
        capture_output=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
