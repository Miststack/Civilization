from __future__ import annotations

from engine.game import GameConfig, GameState
from engine.models import Action, ActionType
from search.prune import (
    action_sort_key,
    prune_build_city_actions,
    rank_actions_for_expansion,
)


def test_action_sort_key_deterministic() -> None:
    a = Action.build_city(3, 4)
    b = Action.build_city(3, 4)
    assert action_sort_key(a) == action_sort_key(b)


def test_prune_build_city_limits_count() -> None:
    s = GameState(GameConfig(10, 20, seed=0))
    legal = [a for a in s.legal_actions() if a.type == ActionType.BUILD_CITY]
    if len(legal) <= 3:
        return
    pruned = prune_build_city_actions(s, s.legal_actions(), max_city_candidates=3)
    city_count = sum(1 for a in pruned if a.type == ActionType.BUILD_CITY)
    assert city_count <= 3
    assert any(a.type == ActionType.SKIP for a in pruned)


def test_prune_keeps_non_city_actions() -> None:
    s = GameState(GameConfig(8, 20, seed=1))
    raw = s.legal_actions()
    pruned = prune_build_city_actions(s, raw, max_city_candidates=1)
    raw_skip = sum(1 for a in raw if a.type == ActionType.SKIP)
    pruned_skip = sum(1 for a in pruned if a.type == ActionType.SKIP)
    assert pruned_skip == raw_skip


def test_rank_actions_respects_branch_limit() -> None:
    s = GameState(GameConfig(8, 15, seed=0))
    leg = s.legal_actions()
    ranked = rank_actions_for_expansion(s, leg, branch_limit=2, max_city_candidates=5)
    assert 1 <= len(ranked) <= 2


def test_rank_actions_nonempty() -> None:
    s = GameState(GameConfig(8, 10, seed=2))
    ranked = rank_actions_for_expansion(s, s.legal_actions(), 3, 5)
    assert ranked
