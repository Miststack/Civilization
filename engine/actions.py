"""合法动作分组与可读标签（终端与 GUI 共用）。"""

from __future__ import annotations

from typing import List

from engine.game import GameState
from engine.models import Action, ActionType


def action_label(a: Action) -> str:
    if a.type == ActionType.SKIP:
        return "跳过本回合"
    if a.type == ActionType.BUILD_CITY and a.x is not None and a.y is not None:
        return f"在 ({a.x}, {a.y}) 开始建城"
    if a.type == ActionType.BUILD_BUILDING and a.city_id is not None and a.building is not None:
        return f"城市 #{a.city_id} 建造 {a.building.value}"
    if a.type == ActionType.RESEARCH and a.tech is not None:
        return f"研究科技 {a.tech.value}"
    return str(a)


def partition_legal(
    state: GameState,
) -> tuple[List[Action], List[Action], List[Action], List[Action]]:
    legal = state.legal_actions()
    skip_a: List[Action] = []
    build_city: List[Action] = []
    build_b: List[Action] = []
    research: List[Action] = []
    for a in legal:
        if a.type == ActionType.SKIP:
            skip_a.append(a)
        elif a.type == ActionType.BUILD_CITY:
            build_city.append(a)
        elif a.type == ActionType.BUILD_BUILDING:
            build_b.append(a)
        elif a.type == ActionType.RESEARCH:
            research.append(a)
    return skip_a, build_city, build_b, research
