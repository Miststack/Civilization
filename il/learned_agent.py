from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import torch
import torch.nn.functional as F

from game import GameState
from il.action_value import pick_best_by_heuristic
from il.encoding import action_to_index, encode_state, index_to_action, legal_action_mask
from il.model import PolicyNet
from models import Action


class LearnedAgent:
    """
    模仿学习策略：
    - top_k_rerank：在模型 top-k 候选中用 score() 单步增量重排（提分关键）
    - fallback_agent：模型置信度过低时委托 Greedy
    """

    def __init__(
        self,
        weights_path: str | Path = "data/il_policy.pt",
        device: Optional[str] = None,
        *,
        top_k_rerank: int = 1,
        min_confidence: Optional[float] = None,
    ) -> None:
        path = Path(weights_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"未找到模型权重: {path}\n"
                "请先运行: python -m il.record_expert && python -m il.train"
            )

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.top_k_rerank = max(1, top_k_rerank)
        self.min_confidence = min_confidence
        self._fallback = None

        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        state_dim = int(ckpt["state_dim"])
        action_dim = int(ckpt["action_dim"])
        hidden = int(ckpt.get("hidden", 256))

        self.model = PolicyNet(state_dim=state_dim, hidden=hidden, action_dim=action_dim).to(self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

    def _fallback_agent(self):
        if self._fallback is None:
            from greedy_agent import GreedyAgent

            self._fallback = GreedyAgent(None)
        return self._fallback

    def _top_k_action_indices(self, logits: torch.Tensor, mask: torch.Tensor, k: int) -> list[int]:
        masked = logits.masked_fill(mask < 0.5, -1e9)
        k = min(k, int((mask > 0.5).sum().item()))
        if k <= 0:
            return [int(masked.argmax(dim=1).item())]
        top = torch.topk(masked, k=k, dim=1)
        return [int(i) for i in top.indices[0].tolist()]

    def _indices_to_actions(self, indices: Sequence[int], legal: list[Action]) -> list[Action]:
        seen: set[int] = set()
        out: list[Action] = []
        for idx in indices:
            if idx in seen:
                continue
            seen.add(idx)
            out.append(index_to_action(idx, legal))
        return out

    def choose(self, state: GameState) -> Action:
        legal = state.legal_actions()
        x = torch.tensor(encode_state(state), dtype=torch.float32, device=self.device).unsqueeze(0)
        mask = torch.tensor(legal_action_mask(state), dtype=torch.float32, device=self.device).unsqueeze(0)

        with torch.no_grad():
            logits = self.model(x)
            masked_logits = logits.masked_fill(mask < 0.5, -1e9)
            probs = F.softmax(masked_logits, dim=1)
            max_prob = float(probs.max().item())

            if self.min_confidence is not None and max_prob < self.min_confidence:
                return self._fallback_agent().choose(state)

            if self.top_k_rerank <= 1:
                idx = int(masked_logits.argmax(dim=1).item())
                return index_to_action(idx, legal)

            top_indices = self._top_k_action_indices(logits, mask, self.top_k_rerank)
            candidates = self._indices_to_actions(top_indices, legal)
            return pick_best_by_heuristic(state, candidates)
