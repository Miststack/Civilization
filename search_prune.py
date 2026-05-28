"""
搜索用动作剪枝与排序：控制建城分支、确定性平局、每结点 top-branch 展开。
"""
from __future__ import annotations

from typing import List, Sequence, Tuple
from game import GameState
from models import Action, ActionType
from search_eval import heuristic_value


def action_sort_key(action: Action) -> Tuple:
    return(
        action.type.value,
        action.x if action.x is not None else -1,
        action.y if action.y is not None else -1,
        action.city_id if action.city_id is not None else -1,
        action.building.value if action.building else "",
        action.tech.value if action.tech else "",
    )

def prune_build_city_actions(
    state: GameState,
    legal: Sequence[Action],
    max_city_candidates: int,
) -> List[Action]:
    keep,cities= [],[]
    for a in legal:
        if a.type == ActionType.BUILD_CITY and a.x is not None and a.y is not None:
            cities.append(a)
        else:
            keep.append(a)
    cities.sort(key=lambda a:state._location_resource_potential(a.x, a.y),reverse=True)
    if len(cities) > max_city_candidates:
        cities = cities[:max_city_candidates]
    return keep + cities

def rank_actions_for_expansion(
    state: GameState,
    legal: Sequence[Action],
    branch_limit: int,
    max_city_candidates: int,
) -> List[Action]:
    branch_limit =max(1,branch_limit)
    candidates = prune_build_city_actions(state, legal, max_city_candidates)
    scored = []
    for a in candidates:
        child =state.clone()
        child.do_turn(a)
        v=heuristic_value(child)
        scored.append((v,a))
    scored.sort(key=lambda t:(t[0],action_sort_key(t[1])),reverse=True)
    if branch_limit >= len(scored):
        return [a for _,a in scored]
    threshold = scored[branch_limit-1][0]
    ties = [(v, a) for v, a in scored if v >= threshold]
    ties.sort(key=lambda t:(t[0],action_sort_key(t[1])),reverse=True)
    return [a for _,a in ties[:branch_limit]]