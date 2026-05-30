from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from game import GameConfig, GameState
from greedy_agent import GreedyAgent
from il.encoding import (
    ACTION_DIM,
    STATE_DIM,
    action_to_index,
    encode_state,
    index_to_action,
    legal_action_mask,
)
from models import Action


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
