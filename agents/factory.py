"""构造对局智能体，供 main 与 GUI 共用。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from agents import GreedyAgent, RandomAgent
from search import PlannedSearchAgent, SearchConfig

try:
    from il.learned_agent import LearnedAgent
except ImportError:
    LearnedAgent = None  # type: ignore[misc, assignment]

MODE_LABELS: dict[str, str] = {
    "random": "随机",
    "greedy": "贪心",
    "planned": "计划束搜索",
    "learned": "模仿学习",
}

GUI_TITLES: dict[str, str] = {
    "random": "简化文明 — 随机策略",
    "greedy": "简化文明 — 贪心策略",
    "planned": "简化文明 — 计划束搜索",
    "learned": "简化文明 — 模仿学习",
}

DEFAULT_IL_WEIGHTS = "data/il_policy.pt"


@dataclass(frozen=True)
class AgentOptions:
    mode: str
    agent_seed: Optional[int] = None
    map_seed: Optional[int] = None
    beam: Optional[int] = None
    branch: Optional[int] = None
    max_city_candidates: Optional[int] = None
    max_horizon: Optional[int] = None
    il_weights: str = DEFAULT_IL_WEIGHTS
    il_device: Optional[str] = None
    il_top_k: int = 1


def resolve_agent_rng(agent_seed: Optional[int], map_seed: Optional[int]) -> random.Random:
    if agent_seed is not None:
        return random.Random(agent_seed)
    if map_seed is not None:
        return random.Random(map_seed + 1)
    return random.Random()


def build_search_config(opts: AgentOptions) -> SearchConfig:
    defaults = SearchConfig()
    return SearchConfig(
        beam=opts.beam if opts.beam is not None else defaults.beam,
        branch=opts.branch if opts.branch is not None else defaults.branch,
        max_city_candidates=(
            opts.max_city_candidates
            if opts.max_city_candidates is not None
            else defaults.max_city_candidates
        ),
        max_horizon=opts.max_horizon,
    )


def validate_planned_options(opts: AgentOptions) -> None:
    cfg = build_search_config(opts)
    if cfg.beam < 1 or cfg.branch < 1 or cfg.max_city_candidates < 1:
        raise ValueError("--beam / --branch / --max-city-candidates 必须为正整数")
    if opts.max_horizon is not None and opts.max_horizon < 1:
        raise ValueError("--max-horizon 必须为正整数")


def create_agent(opts: AgentOptions) -> object:
    rng = resolve_agent_rng(opts.agent_seed, opts.map_seed)
    if opts.mode == "random":
        return RandomAgent(rng)
    if opts.mode == "greedy":
        return GreedyAgent(rng)
    if opts.mode == "planned":
        validate_planned_options(opts)
        return PlannedSearchAgent(config=build_search_config(opts), rng=rng)
    if opts.mode == "learned":
        if LearnedAgent is None:
            raise RuntimeError("learned 模式需要 PyTorch，请先: python -m pip install torch")
        return LearnedAgent(
            weights_path=opts.il_weights,
            device=opts.il_device,
            top_k_rerank=opts.il_top_k,
        )
    raise ValueError(f"未知策略模式: {opts.mode}")
