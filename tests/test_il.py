from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from engine.game import GameConfig, GameState
from agents.greedy import GreedyAgent
from il.encoding import (
    ACTION_DIM,
    STATE_DIM,
    action_to_index,
    encode_state,
    index_to_action,
    legal_action_mask,
)
from engine.models import Action


def test_encode_state_dim() -> None:
    state = GameState(GameConfig(10, 30, seed=0))
    vec = encode_state(state)
    assert vec.shape == (STATE_DIM,)
    assert vec.dtype == np.float32


def test_action_roundtrip_on_legal() -> None:
    state = GameState(GameConfig(8, 15, seed=1))
    legal = state.legal_actions()
    for action in legal:
        idx = action_to_index(action)
        assert 0 <= idx < ACTION_DIM
        assert index_to_action(idx, legal) == action


def test_legal_mask_matches_actions() -> None:
    state = GameState(GameConfig(10, 20, seed=2))
    mask = legal_action_mask(state)
    assert mask.shape == (ACTION_DIM,)
    for action in state.legal_actions():
        assert mask[action_to_index(action)] == 1.0


def test_greedy_trajectory_encodable() -> None:
    state = GameState(GameConfig(8, 8, seed=0))
    agent = GreedyAgent(None)
    steps = 0
    while not state.is_terminal():
        action = agent.choose(state)
        encode_state(state)
        legal_action_mask(state)
        action_to_index(action)
        state.do_turn(action)
        steps += 1
    assert steps == 8


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="需要 PyTorch",
)
def test_heuristic_rerank_picks_legal_action(tmp_path) -> None:
    import torch

    from il.action_value import pick_best_by_heuristic
    from il.learned_agent import LearnedAgent
    from il.model import PolicyNet

    state = GameState(GameConfig(8, 10, seed=0))
    legal = state.legal_actions()
    picked = pick_best_by_heuristic(state, legal[: min(5, len(legal))])
    assert picked in legal

    weights = tmp_path / "w.pt"
    model = PolicyNet()
    torch.save(
        {"state_dict": model.state_dict(), "state_dim": STATE_DIM, "action_dim": ACTION_DIM, "hidden": 256},
        weights,
    )
    agent = LearnedAgent(weights_path=weights, device="cpu", top_k_rerank=3)
    assert agent.choose(state) in legal


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="需要 PyTorch",
)
def test_expand_rerank_includes_heuristic_branch() -> None:
    from il.action_value import build_rerank_candidates, pick_best_rerank, rerank_value
    from search.prune import rank_actions_for_expansion

    state = GameState(GameConfig(10, 30, seed=5))
    legal = state.legal_actions()
    heuristic_top = rank_actions_for_expansion(state, legal, branch_limit=3, max_city_candidates=13)
    model_indices = [0]
    pool = build_rerank_candidates(state, legal, model_indices, pool_size=3)
    pool_indices = {action_to_index(a) for a in pool}
    assert action_to_index(heuristic_top[0]) in pool_indices
    picked = pick_best_rerank(state, pool)
    assert picked in legal
    assert rerank_value(state, picked) >= rerank_value(state, pool[0])


def test_high_confidence_tie_rerank_keeps_model_argmax_when_clear() -> None:
    import torch

    from il.action_value import choose_reranked_action

    state = GameState(GameConfig(8, 10, seed=0))
    legal = state.legal_actions()
    action_dim = max(action_to_index(a) for a in legal) + 1
    logits = torch.full((action_dim,), -10.0)
    mask = torch.zeros(action_dim)
    for action in legal:
        idx = action_to_index(action)
        mask[idx] = 1.0
        logits[idx] = 0.0
    best_action = legal[0]
    best_idx = action_to_index(best_action)
    logits[best_idx] = 5.0
    picked = choose_reranked_action(
        state, legal, logits, mask, top_k=5, max_prob=0.9, tie_margin=0.05
    )
    assert action_to_index(picked) == best_idx
