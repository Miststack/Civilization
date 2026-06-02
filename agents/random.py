"""随机策略：在 `legal_actions()` 中均匀随机选一个动作。"""
from __future__ import annotations

import random
from typing import Optional

from engine.game import GameState
from engine.models import Action

class RandomAgent:
    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng if rng is not None else random.Random()
    def choose(self, state: GameState) -> Action:
        legal = state.legal_actions()
        if not legal:
            raise RuntimeError("无合法动作（终局或未实现）")
        return self._rng.choice(legal)