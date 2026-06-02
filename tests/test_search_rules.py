from __future__ import annotations

from engine.game import GameConfig, GameState
from engine.models import Action, ActionType
from search.rules import effective_legal, has_non_skip_choice, remaining_decision_steps


def test_last_turn_excludes_build_city() -> None:
    s = GameState(GameConfig(map_size=8, total_turns=5, seed=0))
    while s.turn < s.config.total_turns:
        s.do_turn(Action.skip())
    assert s.turn == s.config.total_turns
    leg = effective_legal(s)
    assert not any(a.type == ActionType.BUILD_CITY for a in leg)
    assert any(a.type == ActionType.SKIP for a in leg)


def test_only_skip_detected() -> None:
    assert not has_non_skip_choice([Action.skip()])


def test_has_non_skip_when_research_available() -> None:
    s = GameState(GameConfig(8, 30, seed=0))
    leg = effective_legal(s)
    if any(a.type == ActionType.RESEARCH for a in leg):
        assert has_non_skip_choice(leg)


def test_effective_legal_never_empty() -> None:
    s = GameState(GameConfig(8, 10, seed=1))
    assert effective_legal(s)


def test_remaining_decision_steps_at_start() -> None:
    s = GameState(GameConfig(8, total_turns=30, seed=0))
    assert remaining_decision_steps(s) == 30


def test_remaining_decision_steps_after_terminal() -> None:
    s = GameState(GameConfig(8, total_turns=2, seed=0))
    s.do_turn(Action.skip())
    s.do_turn(Action.skip())
    assert s.is_terminal()
    assert remaining_decision_steps(s) == 0
