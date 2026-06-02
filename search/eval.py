"""
搜索用状态评估：终局精确分、非终局启发式、单步扩展增益。
"""
from __future__ import annotations

from engine.game import GameState
from engine.models import Action, BuildingType, BUILDING_DEFS


def terminal_value(state: GameState) -> int:
    return state.score()

def heuristic_value(state: GameState) -> int:
    base=state.score()
    pending_bonus = len(state.pending_city_projects)*20
    building_opportunity = _count_unlocked_unbuilt_buildings(state)*4
    science_pipeline = min(state.resources["science"],10)//2
    turn_left = max(state.config.total_turns-state.turn+1,0)
    prod = state.estimate_production()
    resource_runway = (sum(prod.values())*turn_left)//4
    return base+pending_bonus+building_opportunity+science_pipeline+resource_runway

def _count_unlocked_unbuilt_buildings(state: GameState) -> int:
    count=0
    for building in BuildingType:
        need_tech = BUILDING_DEFS[building]["tech"]
        if need_tech not in state.tech_unlocked:
            continue
        for city in state.cities:
            if building not in city.buildings:
                count+=1
    return count


def action_step_delta(state: GameState, action: Action) -> int:
    before = heuristic_value(state)
    child = state.clone()
    child.do_turn(action)
    return heuristic_value(child) - before