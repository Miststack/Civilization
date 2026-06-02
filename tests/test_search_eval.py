from __future__ import annotations

from engine.game import GameConfig, GameState
from engine.models import Action, TechType
from search.eval import (
    action_step_delta,
    heuristic_value,
    terminal_value,
    _count_unlocked_unbuilt_buildings,
)


def test_terminal_value_equals_score() -> None:
    s = GameState(GameConfig(8, 2, seed=0))
    s.do_turn(Action.skip())
    s.do_turn(Action.skip())
    assert terminal_value(s) == s.score()


def test_heuristic_at_least_score() -> None:
    s = GameState(GameConfig(10, 30, seed=1))
    assert heuristic_value(s) >= s.score()


def test_pending_city_increases_heuristic() -> None:
    s = GameState(GameConfig(8, 30, seed=0))
    base_h = heuristic_value(s)
    s.pending_city_projects.append((0, 0, 2))
    assert heuristic_value(s) >= base_h + 20


def test_count_unlocked_unbuilt_zero_without_tech() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    assert _count_unlocked_unbuilt_buildings(s) == 0


def test_count_unlocked_unbuilt_after_agriculture() -> None:
    s = GameState(GameConfig(8, 30, seed=1))
    while s.resources["science"] < 6:
        s.do_turn(Action.skip())
    s.do_turn(Action.research(TechType.AGRICULTURE))
    assert _count_unlocked_unbuilt_buildings(s) >= len(s.cities)


def test_action_step_delta_skip() -> None:
    s = GameState(GameConfig(8, 15, seed=2))
    delta = action_step_delta(s, Action.skip())
    child = s.clone()
    child.do_turn(Action.skip())
    assert delta == heuristic_value(child) - heuristic_value(s)
