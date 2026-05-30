from __future__ import annotations

from typing import List, Sequence

import numpy as np

from game import GameState
from models import Action, ActionType, BuildingType, RESOURCE_KEYS, TechType, TerrainType

MAX_MAP = 12
NUM_BUILDINGS = len(BuildingType)
NUM_TECHS = len(TechType)
# 12×12 地图在距离约束下城数可超过 12，需留足建筑动作槽位
MAX_CITIES = 30
TERRAIN_LIST = list(TerrainType)
BUILDING_LIST = list(BuildingType)
TECH_LIST = list(TechType)

ACTION_SKIP = 0
ACTION_CITY_BASE = 1
ACTION_BUILDING_BASE = 1 + MAX_MAP * MAX_MAP
ACTION_RESEARCH_BASE = ACTION_BUILDING_BASE + MAX_CITIES * NUM_BUILDINGS
ACTION_DIM = ACTION_RESEARCH_BASE + NUM_TECHS

STATE_DIM = (
    len(TERRAIN_LIST) * MAX_MAP * MAX_MAP
    + MAX_MAP * MAX_MAP
    + MAX_MAP * MAX_MAP
    + 12
    + NUM_TECHS
    + MAX_CITIES * NUM_BUILDINGS
)


def action_to_index(action: Action) -> int:
    if action.type == ActionType.SKIP:
        return ACTION_SKIP
    if action.type == ActionType.BUILD_CITY:
        if action.x is None or action.y is None:
            raise ValueError("建城动作缺少坐标")
        return ACTION_CITY_BASE + action.y * MAX_MAP + action.x
    if action.type == ActionType.BUILD_BUILDING:
        if action.city_id is None or action.building is None:
            raise ValueError("建造动作缺少 city_id 或 building")
        bi = BUILDING_LIST.index(action.building)
        return ACTION_BUILDING_BASE + (action.city_id - 1) * NUM_BUILDINGS + bi
    if action.type == ActionType.RESEARCH:
        if action.tech is None:
            raise ValueError("研究动作缺少 tech")
        ti = TECH_LIST.index(action.tech)
        return ACTION_RESEARCH_BASE + ti
    raise ValueError(f"未知动作: {action}")


def index_to_action(idx: int, legal: Sequence[Action]) -> Action:
    for action in legal:
        if action_to_index(action) == idx:
            return action
    for action in legal:
        if action.type == ActionType.SKIP:
            return action
    return legal[0]


def legal_action_mask(state: GameState) -> np.ndarray:
    mask = np.zeros(ACTION_DIM, dtype=np.float32)
    for action in state.legal_actions():
        mask[action_to_index(action)] = 1.0
    return mask


def encode_state(state: GameState) -> np.ndarray:
    n = state.size
    feats: List[np.ndarray] = []

    terrain = np.zeros((len(TERRAIN_LIST), MAX_MAP, MAX_MAP), dtype=np.float32)
    for y in range(n):
        for x in range(n):
            ti = TERRAIN_LIST.index(state.grid[y][x])
            terrain[ti, y, x] = 1.0
    feats.append(terrain.ravel())

    city_map = np.zeros((MAX_MAP, MAX_MAP), dtype=np.float32)
    pending_map = np.zeros((MAX_MAP, MAX_MAP), dtype=np.float32)
    for city in state.cities:
        city_map[city.y, city.x] = 1.0
    for x, y, _ in state.pending_city_projects:
        pending_map[y, x] = 1.0
    feats.append(city_map.ravel())
    feats.append(pending_map.ravel())

    prod = state.estimate_production()
    total_turns = max(1, state.config.total_turns)
    scalars = np.array(
        [
            state.turn / total_turns,
            len(state.cities) / 20.0,
            len(state.pending_city_projects) / 5.0,
            state.score() / 800.0,
            *[state.resources[k] / 100.0 for k in RESOURCE_KEYS],
            *[prod[k] / 20.0 for k in RESOURCE_KEYS],
        ],
        dtype=np.float32,
    )
    feats.append(scalars)

    tech_vec = np.zeros(NUM_TECHS, dtype=np.float32)
    for tech in state.tech_unlocked:
        tech_vec[TECH_LIST.index(tech)] = 1.0
    feats.append(tech_vec)

    bld = np.zeros((MAX_CITIES, NUM_BUILDINGS), dtype=np.float32)
    for city in state.cities:
        if 1 <= city.city_id <= MAX_CITIES:
            for building in city.buildings:
                bld[city.city_id - 1, BUILDING_LIST.index(building)] = 1.0
    feats.append(bld.ravel())

    out = np.concatenate(feats)
    if out.shape[0] != STATE_DIM:
        raise RuntimeError(f"状态维度不一致: {out.shape[0]} != {STATE_DIM}")
    return out
