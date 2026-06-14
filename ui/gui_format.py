"""GUI 文本格式化与字体加载。"""
from __future__ import annotations

import pygame

from engine.actions import action_label
from engine.game import GameState
from engine.models import (
    Action,
    ActionType,
    BUILDING_DEFS,
    BuildingType,
    CITY_BUILD_TURNS,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
)
from ui.theme import BUILDING_LABELS, RESOURCE_ICONS, TECH_LABELS

def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in ("Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


def label_building(building: BuildingType) -> str:
    return BUILDING_LABELS.get(building.value, building.value)


def label_tech(tech: TechType) -> str:
    return TECH_LABELS.get(tech.value, tech.value)


def short_resource_cost(cost: dict[str, int]) -> str:
    parts: list[str] = []
    for key in ("food", "wood", "ore", "science"):
        val = int(cost.get(key, 0))
        if val > 0:
            parts.append(f"{RESOURCE_ICONS[key]}{val}")
    return " ".join(parts) if parts else "免费"


def building_yield_hint(building: BuildingType) -> str:
    bonus = BUILDING_DEFS[building]["yield_bonus"]
    assert isinstance(bonus, dict)
    return format_yields_static(bonus)




def terrain_yield_hint(terrain: TerrainType) -> str:
    yld = TERRAIN_YIELDS.get(terrain, {})
    if not yld:
        return "无产出"
    return format_yields_static(yld)


def building_terrain_hint(building: BuildingType) -> str:
    return building_yield_hint(building)

def format_yields_static(yields: dict[str, int]) -> str:
    parts = []
    for key in ("food", "wood", "ore", "science"):
        if int(yields.get(key, 0)) > 0:
            parts.append(f"{RESOURCE_ICONS[key]}{yields[key]}")
    return " ".join(parts) if parts else "无加成"


def action_cost_text(state: GameState, action: Action) -> str:
    if action.type == ActionType.BUILD_BUILDING and action.building is not None:
        costs = BUILDING_DEFS[action.building]["cost"]
        assert isinstance(costs, dict)
        return f"消耗 {short_resource_cost(costs)}  ·  +{building_yield_hint(action.building)}/回合"
    if action.type == ActionType.RESEARCH and action.tech is not None:
        return f"消耗 {TECH_COST[action.tech]} 科技点"
    if action.type == ActionType.BUILD_CITY:
        costs = state._next_city_build_cost()
        return f"消耗 {short_resource_cost(costs)}  ·  {CITY_BUILD_TURNS} 回合完工"
    return ""


def action_list_entry(state: GameState, action: Action) -> tuple[str, str]:
    if action.type == ActionType.BUILD_BUILDING and action.building and action.city_id is not None:
        return (
            f"城市 #{action.city_id} · {label_building(action.building)}",
            action_cost_text(state, action),
        )
    if action.type == ActionType.RESEARCH and action.tech is not None:
        return label_tech(action.tech), action_cost_text(state, action)
    return action_label(action), action_cost_text(state, action)


