from __future__ import annotations

from models import (
    Action,
    ActionType,
    BUILD_TERRAINS,
    BUILDING_DEFS,
    BuildingType,
    RESOURCE_KEYS,
    TECH_COST,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
    empty_resources,
)


def test_empty_resources_keys() -> None:
    z = empty_resources()
    assert set(z.keys()) == set(RESOURCE_KEYS)
    assert all(v == 0 for v in z.values())


def test_build_terrains_subset_of_enum() -> None:
    assert BUILD_TERRAINS <= set(TerrainType)


def test_terrain_yields_keys_match_resource_keys() -> None:
    for yld in TERRAIN_YIELDS.values():
        for k in yld:
            assert k in RESOURCE_KEYS


def test_building_defs_have_cost_yield_tech() -> None:
    for d in BUILDING_DEFS.values():
        assert "cost" in d and "yield_bonus" in d and "tech" in d
        assert isinstance(d["tech"], TechType)


def test_action_factories() -> None:
    assert Action.skip().type == ActionType.SKIP
    a = Action.build_city(3, 4)
    assert a.type == ActionType.BUILD_CITY and a.x == 3 and a.y == 4
    assert Action.build_building(1, BuildingType.FARM).building == BuildingType.FARM
    assert Action.research(TechType.MINING).tech == TechType.MINING


def test_tech_costs_positive() -> None:
    for c in TECH_COST.values():
        assert c > 0


def test_mine_yield_bonus_has_ore() -> None:
    bonus = BUILDING_DEFS[BuildingType.MINE]["yield_bonus"]
    assert isinstance(bonus, dict) and "ore" in bonus


def test_course_spec_farm_lumber_mine_costs_and_yields() -> None:
    """课程给定：农场 / 伐木场 / 矿场的建造成本与周产出（其余建筑不在此断言）。"""
    farm = BUILDING_DEFS[BuildingType.FARM]
    assert farm["cost"] == {"wood": 2}
    assert farm["yield_bonus"] == {"food": 1}
    assert farm["tech"] is TechType.AGRICULTURE

    lm = BUILDING_DEFS[BuildingType.LUMBER_MILL]
    assert lm["cost"] == {"wood": 2}
    assert lm["yield_bonus"] == {"wood": 1}
    assert lm["tech"] is TechType.LOGGING

    mine = BUILDING_DEFS[BuildingType.MINE]
    assert mine["cost"] == {"wood": 3}
    assert mine["yield_bonus"] == {"ore": 2}
    assert mine["tech"] is TechType.MINING
