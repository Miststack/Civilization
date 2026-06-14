from __future__ import annotations

import pytest

from engine.game import GameConfig, GameState
from engine.models import (
    Action,
    CITY_FIXED_YIELD,
    TECH_COST,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
    empty_resources,
)


def test_game_config_validation() -> None:
    with pytest.raises(ValueError):
        GameConfig(map_size=7, total_turns=10).validate()
    with pytest.raises(ValueError):
        GameConfig(map_size=10, total_turns=0).validate()


def test_game_starts_with_one_city() -> None:
    s = GameState(GameConfig(map_size=8, total_turns=5, seed=0))
    assert len(s.cities) == 1 and s.turn == 1


def test_capital_area_has_forest() -> None:
    for seed in range(15):
        s = GameState(GameConfig(10, 5, seed=seed))
        c = s.cities[0]
        cells = s._city_area_cells(c.x, c.y)
        assert any(s.grid[ny][nx] == TerrainType.FOREST for nx, ny in cells), seed


def test_legal_actions_includes_skip() -> None:
    s = GameState(GameConfig(8, 10, seed=1))
    assert any(a.type.name == "SKIP" for a in s.legal_actions())


def test_do_turn_skip_advances_turn() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    s.do_turn(Action.skip())
    assert s.turn == 2


def test_terminal_after_enough_turns() -> None:
    s = GameState(GameConfig(8, total_turns=2, seed=0))
    s.do_turn(Action.skip())
    s.do_turn(Action.skip())
    assert s.is_terminal()


def test_clone_is_independent() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    c = s.clone()
    c.do_turn(Action.skip())
    assert s.turn == 1 and c.turn == 2


def test_clone_copies_mutable_state() -> None:
    s = GameState(GameConfig(8, 30, seed=2))
    for _ in range(5):
        s.do_turn(Action.skip())
    c = s.clone()
    assert c.turn == s.turn
    assert c.resources == s.resources
    assert c.tech_unlocked == s.tech_unlocked
    assert len(c.cities) == len(s.cities)
    assert c.score() == s.score()

    c.resources["food"] += 99
    assert c.resources != s.resources
    assert c.cities is not s.cities
    assert c.cities[0] is not s.cities[0]
    assert c.cities[0].buildings is not s.cities[0].buildings


def test_clone_shares_static_grid() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    c = s.clone()
    assert c.grid is s.grid


def test_research_science_cost_and_production_stack() -> None:
    s = GameState(GameConfig(8, 60, seed=1))
    while s.resources["science"] < TECH_COST[TechType.AGRICULTURE]:
        s.do_turn(Action.skip())
    before = s.resources["science"]
    cost = TECH_COST[TechType.AGRICULTURE]
    prod_sci = s.estimate_production()["science"]
    s.do_turn(Action.research(TechType.AGRICULTURE))
    assert s.resources["science"] == before - cost + prod_sci
    assert TechType.AGRICULTURE in s.tech_unlocked


def test_single_city_estimate_matches_manual() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    c = s.cities[0]
    manual = empty_resources()
    for nx, ny in s._city_area_cells(c.x, c.y):
        terr = s.grid[ny][nx]
        for k, v in TERRAIN_YIELDS[terr].items():
            manual[k] += v
    for k, v in CITY_FIXED_YIELD.items():
        manual[k] += int(v)
    assert s.estimate_production() == manual


def test_render_map_non_empty() -> None:
    s = GameState(GameConfig(8, 5, seed=0))
    assert len(s.render_map()) > 50 and "图例" in s.render_map()


def test_score_increases_with_four_food() -> None:
    s = GameState(GameConfig(8, 5, seed=0))
    s0 = s.score()
    s.resources["food"] += 4
    assert s.score() == s0 + 1
