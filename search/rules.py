"""
搜索用合法动作与回合视界工具。
供 PlannedSearchAgent 在展开结点前过滤动作、计算模拟深度。
"""
from __future__ import annotations

from typing import List, Sequence

from engine.game import GameState
from engine.models import Action, ActionType


def effective_legal(state: GameState) -> List[Action]:
    raw = state.legal_actions()
    last_turn = state.turn == state.config.total_turns
    out: List[Action] = []
    for a in raw:
        if last_turn and a.type == ActionType.BUILD_CITY:
            continue
        out.append(a)
    return out if out else [Action.skip()]


def has_non_skip_choice(legal: Sequence[Action]) -> bool:
    return any(a.type != ActionType.SKIP for a in legal)


def remaining_decision_steps(state: GameState) -> int:
    return max(0, state.config.total_turns - state.turn + 1)