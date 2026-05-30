from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from il.encoding import ACTION_DIM, STATE_DIM


class PolicyNet(nn.Module):
    def __init__(self, state_dim: int = STATE_DIM, hidden: int = 256, action_dim: int = ACTION_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def masked_cross_entropy(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    masked_logits = logits.masked_fill(mask < 0.5, -1e9)
    return F.cross_entropy(masked_logits, target)
