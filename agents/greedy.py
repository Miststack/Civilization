"""
Baseline 规则智能体
决策顺序：
1. 资源补短板 — 科技：发展明显受某类资源制约且对应科技可研究时，按
   农业→教育→伐木→采矿 的优先序尝试研究。
2. 资源补短板 — 建筑：预估产出显示某类资源偏低且已解锁对应科技时，
   优先建农场 / 伐木场 / 图书馆 / 矿场。
3. 高收益建城：在合法建城格中选 `_location_resource_potential` 最高者
  （与首都选址启发式一致：周围格粮食/木材/矿石/科技加权和）。
4. 关键科技：其余可研究科技，按枚举顺序择一。
5. 其他建筑：任意合法建造动作（枚举顺序中第一个）。
6. 跳过：以上皆不可行则 `SKIP`（合法动作中必含跳过）。
"""
from __future__ import annotations
import random
from typing import Iterable, List, Optional
from engine.game import GameState
from engine.models import Action, ActionType, BuildingType, TechType


def _legal_list(state: GameState) -> List[Action]:
    return state.legal_actions()


def _first_skip(legal: Iterable[Action]) -> Optional[Action]:
    for a in legal:
        if a.type == ActionType.SKIP:
            return a
    return None


def _pick_research(legal: Iterable[Action], tech: TechType) -> Optional[Action]:
    for a in legal:
        if a.type == ActionType.RESEARCH and a.tech == tech:
            return a
    return None


def _pick_first_building(legal: Iterable[Action], building: BuildingType) -> Optional[Action]:
    for a in legal:
        if a.type == ActionType.BUILD_BUILDING and a.building == building:
            return a
    return None


def _pick_first_building_any(legal: Iterable[Action]) -> Optional[Action]:
    for a in legal:
        if a.type == ActionType.BUILD_BUILDING:
            return a
    return None


def _pick_best_build_city(legal: Iterable[Action], state: GameState, rng: Optional[random.Random]) -> Optional[Action]:
    best_score = float("-inf")
    best: List[Action] = []
    for a in legal:
        if a.type != ActionType.BUILD_CITY or a.x is None or a.y is None:
            continue
        sc = state._location_resource_potential(a.x, a.y)
        if sc > best_score:
            best_score = sc
            best = [a]
        elif sc == best_score:
            best.append(a)
    if not best:
        return None
    if rng is not None and len(best) > 1:
        return rng.choice(best)
    return best[0]


def _production(state: GameState) -> dict[str, int]:
    return state.estimate_production()


def _stress_flags(state: GameState, prod: dict[str, int]) -> tuple[bool, bool, bool, bool]:
    """粮食 / 木材 / 矿石 / 科技 是否「明显偏低」（启发式阈值，可调）。"""
    n = max(1, len(state.cities))
    r = state.resources
    food_low = prod["food"] < n * 5 or r["food"] < 12 + n * 2
    wood_low = prod["wood"] < n * 2 or r["wood"] < 10 + n
    ore_low = prod["ore"] < n * 2 or r["ore"] < 6 + n
    sci_low = prod["science"] < n * 3 or r["science"] < 8 + n * 2
    return food_low, wood_low, ore_low, sci_low


class GreedyAgent:
    """基于规则的 baseline 智能体"""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng

    def choose(self, state: GameState) -> Action:
        legal = _legal_list(state)
        skip = _first_skip(legal)
        if skip is None:
            raise RuntimeError("无合法动作：缺少 SKIP（环境实现异常）")

        prod = _production(state)
        food_s, wood_s, ore_s, sci_s = _stress_flags(state, prod)

        #1) 短板：优先研究对应科技（农业 / 教育 / 伐木 / 采矿）---
        stress_tech_pairs: list[tuple[TechType, bool]] = [
            (TechType.AGRICULTURE, food_s),
            (TechType.EDUCATION, sci_s),
            (TechType.LOGGING, wood_s),
            (TechType.MINING, ore_s),
        ]
        for tech, stressed in stress_tech_pairs:
            if not stressed:
                continue
            a = _pick_research(legal, tech)
            if a is not None:
                return a

        #2) 短板：增产建筑（需已解锁科技，由 legal 隐含保证）---
        if food_s:
            a = _pick_first_building(legal, BuildingType.FARM)
            if a is not None:
                return a
        if wood_s:
            a = _pick_first_building(legal, BuildingType.LUMBER_MILL)
            if a is not None:
                return a
        if sci_s:
            a = _pick_first_building(legal, BuildingType.LIBRARY)
            if a is not None:
                return a
        if ore_s:
            a = _pick_first_building(legal, BuildingType.MINE)
            if a is not None:
                return a

        #3) 高收益建城 ---
        a = _pick_best_build_city(legal, state, self._rng)
        if a is not None:
            return a

        #4) 关键科技：其余可研究项（固定顺序）---
        for tech in (TechType.AGRICULTURE, TechType.LOGGING, TechType.MINING, TechType.EDUCATION):
            a = _pick_research(legal, tech)
            if a is not None:
                return a

        #5) 其他建筑 ---
        a = _pick_first_building_any(legal)
        if a is not None:
            return a

        return skip