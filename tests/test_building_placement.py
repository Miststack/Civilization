from __future__ import annotations

import pytest

from engine.game import GameConfig, GameState
from engine.models import Action, BuildingType, TechType, TerrainType, TECH_COST


def _unlock_and_fund_farm(state: GameState) -> None:
    while state.resources["science"] < TECH_COST[TechType.AGRICULTURE]:
        state.do_turn(Action.skip())
    state.do_turn(Action.research(TechType.AGRICULTURE))
    state.resources["wood"] += 4


def test_building_requires_placement_tile() -> None:
    state = GameState(GameConfig(map_size=8, total_turns=20, seed=0))
    city = state.cities[0]
    _unlock_and_fund_farm(state)
    cells = state.legal_building_cells(city.city_id, BuildingType.FARM)
    assert cells
    x, y = cells[0]
    state.do_turn(Action.build_building(city.city_id, BuildingType.FARM, x, y))
    assert BuildingType.FARM in city.buildings
    assert city.building_tiles[BuildingType.FARM] == (x, y)


def test_auto_placement_when_coords_missing() -> None:
    state = GameState(GameConfig(map_size=8, total_turns=20, seed=1))
    city = state.cities[0]
    _unlock_and_fund_farm(state)
    state.do_turn(Action.build_building(city.city_id, BuildingType.FARM))
    assert BuildingType.FARM in city.buildings
    assert BuildingType.FARM in city.building_tiles


def test_cannot_place_on_city_center() -> None:
    state = GameState(GameConfig(map_size=8, total_turns=20, seed=0))
    city = state.cities[0]
    _unlock_and_fund_farm(state)
    ok, reason = state.can_place_building(city.city_id, BuildingType.FARM, city.x, city.y)
    assert not ok
    assert "不能" in reason or "格" in reason


def test_farm_cannot_place_on_wrong_terrain() -> None:
    state = GameState(GameConfig(map_size=8, total_turns=20, seed=0))
    city = state.cities[0]
    _unlock_and_fund_farm(state)
    for nx, ny in state._city_area_cells(city.x, city.y):
        if state.grid[ny][nx] == TerrainType.FOREST:
            ok, reason = state.can_place_building(
                city.city_id, BuildingType.FARM, nx, ny
            )
            assert not ok
            assert "地形" in reason
            return
    pytest.skip("首都周边无森林格，跳过地形校验用例")


def test_legal_cells_respect_terrain() -> None:
    state = GameState(GameConfig(map_size=8, total_turns=20, seed=0))
    city = state.cities[0]
    for x, y in state.legal_building_cells(city.city_id, BuildingType.FARM):
        assert state.grid[y][x] in {TerrainType.PLAIN, TerrainType.RIVER}
