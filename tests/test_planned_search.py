from __future__ import annotations

import random

import pytest

from engine.game import GameConfig, GameState
from agents.greedy import GreedyAgent
from engine.models import Action
from search import PlannedSearchAgent, SearchConfig, expand_trace, pick_best_first_move
from search.rules import effective_legal


def test_planned_agent_choose_returns_action() -> None:
    s = GameState(GameConfig(8, 10, seed=0))
    agent = PlannedSearchAgent(config=SearchConfig(beam=4, branch=3, max_city_candidates=5))
    action = agent.choose(s)
    assert action in effective_legal(s)


def test_planned_agent_terminal_raises() -> None:
    s = GameState(GameConfig(8, 2, seed=0))
    s.do_turn(Action.skip())
    s.do_turn(Action.skip())
    agent = PlannedSearchAgent()
    with pytest.raises(RuntimeError):
        agent.choose(s)


def test_expand_trace_sets_first_move() -> None:
    from search.agent import SearchTrace

    s = GameState(GameConfig(8, 10, seed=0))
    root = SearchTrace(state=s, first=None)
    tr = expand_trace(root, Action.skip())
    assert tr.first == Action.skip()
    assert tr.state.turn == 2


def test_pick_best_first_move_from_terminal_traces() -> None:
    from search.agent import SearchTrace

    s = GameState(GameConfig(8, 2, seed=0))
    s.do_turn(Action.skip())
    s.do_turn(Action.skip())
    tr = SearchTrace(state=s, first=Action.skip())
    assert pick_best_first_move([tr]) == Action.skip()


def test_planned_not_worse_than_greedy_short_game() -> None:
    """短局抽样：计划搜索终局分应不低于贪心。"""
    for seed in (0, 3):
        cfg = GameConfig(map_size=8, total_turns=10, seed=seed)
        rng = random.Random(seed + 1)

        g = GameState(cfg)
        ga = GreedyAgent(rng)
        while not g.is_terminal():
            g.do_turn(ga.choose(g))

        p = GameState(cfg)
        pa = PlannedSearchAgent(
            config=SearchConfig(beam=6, branch=4, max_city_candidates=8, max_horizon=8),
        )
        while not p.is_terminal():
            p.do_turn(pa.choose(p))

        assert p.score() >= g.score(), f"seed={seed} planned={p.score()} greedy={g.score()}"
