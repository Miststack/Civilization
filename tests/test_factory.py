from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agents.factory import AgentOptions, create_agent, resolve_agent_rng, validate_planned_options
from agents import GreedyAgent, RandomAgent
from search import PlannedSearchAgent


def test_resolve_agent_rng_deterministic() -> None:
    a = resolve_agent_rng(None, 42)
    b = resolve_agent_rng(None, 42)
    assert a.randint(0, 1000) == b.randint(0, 1000)
    assert resolve_agent_rng(7, 42).randint(0, 1000) != a.randint(0, 1000)


def test_create_agent_modes() -> None:
    opts = AgentOptions(mode="random", agent_seed=0)
    assert isinstance(create_agent(opts), RandomAgent)
    assert isinstance(create_agent(AgentOptions(mode="greedy", agent_seed=0)), GreedyAgent)
    assert isinstance(create_agent(AgentOptions(mode="planned", agent_seed=0)), PlannedSearchAgent)


def test_validate_planned_options_rejects_bad_beam() -> None:
    with pytest.raises(ValueError, match="beam"):
        validate_planned_options(AgentOptions(mode="planned", beam=0))


def test_main_learned_missing_weights_exits_cleanly() -> None:
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "main.py"),
            "--map-size",
            "8",
            "--turns",
            "2",
            "--seed",
            "0",
            "--play",
            "learned",
            "--il-weights",
            "data/nonexistent_policy.pt",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "未找到模型权重" in proc.stderr + proc.stdout or "nonexistent" in proc.stderr + proc.stdout
