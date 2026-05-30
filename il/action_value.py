from __future__ import annotations

from game import GameState
from models import Action
from search_eval import heuristic_value


def heuristic_step_delta(state: GameState, action: Action) -> int:
    before = heuristic_value(state)
    child = state.clone()
    child.do_turn(action)
    return heuristic_value(child) - before


def pick_best_by_heuristic(state: GameState, candidates: list[Action]) -> Action:
    if not candidates:
        raise ValueError('empty candidates')
    if len(candidates) == 1:
        return candidates[0]
    best = candidates[0]
    best_delta = heuristic_step_delta(state, best)
    for action in candidates[1:]:
        delta = heuristic_step_delta(state, action)
        if delta > best_delta:
            best_delta = delta
            best = action
    return best
