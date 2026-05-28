"""
planned_search_agent.py — 计划型束搜索智能体

【模块依赖】
    search_rules  — 合法动作与视界
    search_eval   — 终局分与启发式
    search_prune  — 动作剪枝与排序
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from game import GameState
from models import Action

from search_eval import heuristic_value, terminal_value
from search_prune import rank_actions_for_expansion
from search_rules import effective_legal, has_non_skip_choice, remaining_decision_steps


@dataclass(frozen=True)
class SearchConfig:
    """
    束搜索超参数与剪枝上限。
    【用法】
        cfg = SearchConfig(beam=12, branch=7, max_city_candidates=10)
        agent = PlannedSearchAgent(config=cfg)
    【字段】
        beam: 每层保留轨迹数
        branch: 每个结点展开的动作数上限
        max_city_candidates: 建城动作 top-K 剪枝
        root_branch_mult: 第 0 层 branch 乘数
        max_horizon: 模拟深度硬顶（None 则用剩余回合数）
    """
    beam: int = 11
    branch: int = 6
    max_city_candidates: int = 13
    root_branch_mult: int = 1
    max_horizon: Optional[int] = None


@dataclass(frozen=True)
class SearchTrace:
    """
    一条模拟轨迹。
    【字段】
        state: 模拟到的局面
        first: 从真实根局面出发的第一步；根轨迹为 None
    """

    state: GameState
    first: Optional[Action]


def expand_trace(trace: SearchTrace, action: Action) -> SearchTrace:
    child_state = trace.state.clone()
    child_state.do_turn(action)
    first_move = action if trace.first is None else trace.first
    return SearchTrace(state=child_state, first=first_move)


def trace_sort_key(trace: SearchTrace) -> Tuple[int, int]:
    if trace.state.is_terminal():
        return 1, terminal_value(trace.state)
    return 0, heuristic_value(trace.state)


def select_beam(traces: Sequence[SearchTrace], beam_width: int) -> List[SearchTrace]:
    beam_width = max(1, beam_width)
    sorted_traces = sorted(traces, key=trace_sort_key, reverse=True)
    return sorted_traces[:beam_width]


def pick_best_first_move(traces: Sequence[SearchTrace]) -> Optional[Action]:
    if not traces:
        return None
    finals = [t for t in traces if t.state.is_terminal()]
    if finals:
        best = max(finals, key=lambda t: t.state.score())
        return best.first
    best = max(traces, key=trace_sort_key)
    return best.first


class PlannedSearchAgent:
    """
    计划型束搜索智能体（对外入口）。
    【用法】
        agent = PlannedSearchAgent(config=SearchConfig(), rng=None)
        while not state.is_terminal():
            action = agent.choose(state)
            state.do_turn(action)
    """

    def __init__(
        self,
        config: Optional[SearchConfig] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        【参数】
            config: 搜索超参；None 则用 SearchConfig() 默认。
            rng: 兼容 main.py 传入；本策略不应依赖随机打破平局。
        """
        self._config = config if config is not None else SearchConfig()
        self._rng = rng

    def choose(self, state: GameState) -> Action:
        if state.is_terminal():
            raise RuntimeError("终局状态不应再决策")

        legal = effective_legal(state)
        if not legal:
            raise RuntimeError("无合法动作")
        if not has_non_skip_choice(legal):
            return Action.skip()

        cfg = self._config
        horizon = remaining_decision_steps(state)
        if cfg.max_horizon is not None:
            horizon = min(horizon, cfg.max_horizon)
        if horizon <= 0:
            return legal[0]

        beam: List[SearchTrace] = [SearchTrace(state=state, first=None)]

        for step_i in range(horizon):
            expanded: List[SearchTrace] = []
            branch_limit = (
                cfg.branch * cfg.root_branch_mult if step_i == 0 else cfg.branch
            )
            branch_limit = max(1, branch_limit)

            for tr in beam:
                if tr.state.is_terminal():
                    expanded.append(tr)
                    continue
                leg = effective_legal(tr.state)
                if not leg:
                    continue
                ranked = rank_actions_for_expansion(
                    tr.state,
                    leg,
                    branch_limit,
                    cfg.max_city_candidates,
                )
                for action in ranked:
                    expanded.append(expand_trace(tr, action))

            if not expanded:
                break
            beam = select_beam(expanded, cfg.beam)

        best = pick_best_first_move(beam)
        if best is not None:
            return best

        ranked = rank_actions_for_expansion(
            state, legal, 1, cfg.max_city_candidates
        )
        return ranked[0]

    @property
    def config(self):
        return self._config


def fallback_greedy_action(state: GameState, rng: Optional[random.Random] = None) -> Action:
    """
    兜底：委托 GreedyAgent.choose（测试或异常时用）。
    """
    from greedy_agent import GreedyAgent

    return GreedyAgent(rng).choose(state)