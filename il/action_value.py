from __future__ import annotations

from typing import Sequence

from engine.game import GameState
from engine.models import Action
from il.encoding import action_to_index, index_to_action
from search.eval import heuristic_value, terminal_value
from search.prune import action_sort_key, rank_actions_for_expansion

# 与 PlannedSearchAgent 默认建城剪枝一致
_DEFAULT_MAX_CITY_CANDIDATES = 13
# logits 与 top-1 相差在该范围内视为「接近」，才用前瞻值打破平局
DEFAULT_LOGIT_TIE_MARGIN = 0.05
# 低置信时扩大候选池的 softmax 阈值
DEFAULT_LOW_CONFIDENCE = 0.25


def rerank_value(state: GameState, action: Action) -> float:
    """单步前瞻值：终局或临近终局用 score，否则用搜索启发式。"""
    child = state.clone()
    child.do_turn(action)
    if child.is_terminal():
        return float(terminal_value(child))
    turns_left = max(0, state.config.total_turns - state.turn)
    if turns_left <= 2:
        return float(child.score())
    return float(heuristic_value(child))


def pick_best_rerank(state: GameState, candidates: list[Action]) -> Action:
    if not candidates:
        raise ValueError("empty candidates")
    if len(candidates) == 1:
        return candidates[0]
    scored = [(rerank_value(state, action), action_sort_key(action), action) for action in candidates]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]


def model_top_k_indices(
    logits_row,
    mask_row,
    k: int,
) -> list[int]:
    """合法动作中 logits 最高的 top-k 动作索引。"""
    masked = logits_row.masked_fill(mask_row < 0.5, -1e9)
    k = min(max(1, k), int((mask_row > 0.5).sum().item()))
    if k <= 0:
        return [int(masked.argmax().item())]
    top = masked.topk(k=k)
    return [int(i) for i in top.indices.tolist()]


def narrow_logit_ties(
    logits_row,
    top_indices: Sequence[int],
    *,
    tie_margin: float = DEFAULT_LOGIT_TIE_MARGIN,
) -> list[int]:
    """在 top-k 中保留与 top-1 logits 足够接近的动作（避免覆盖模型高置信选择）。"""
    if not top_indices:
        return []
    if len(top_indices) == 1:
        return list(top_indices)
    best_logit = float(logits_row[top_indices[0]].item())
    tied = [idx for idx in top_indices if float(logits_row[idx].item()) >= best_logit - tie_margin]
    return tied if tied else [top_indices[0]]


def build_rerank_candidates(
    state: GameState,
    legal: Sequence[Action],
    model_indices: Sequence[int],
    pool_size: int,
    *,
    max_city_candidates: int = _DEFAULT_MAX_CITY_CANDIDATES,
) -> list[Action]:
    """模型 top-k 并上启发式 top-k，供低置信度时的宽候选池。"""
    k = max(1, pool_size)
    legal_list = list(legal)

    seen: set[int] = set()
    pool: list[Action] = []
    for idx in model_indices:
        if idx in seen:
            continue
        seen.add(idx)
        pool.append(index_to_action(idx, legal_list))

    for action in rank_actions_for_expansion(
        state, legal_list, branch_limit=k, max_city_candidates=max_city_candidates
    ):
        idx = action_to_index(action)
        if idx in seen:
            continue
        seen.add(idx)
        pool.append(action)

    return pool if pool else [index_to_action(model_indices[0], legal_list)]


def choose_reranked_action(
    state: GameState,
    legal: Sequence[Action],
    logits_row,
    mask_row,
    *,
    top_k: int,
    max_prob: float,
    low_confidence: float = DEFAULT_LOW_CONFIDENCE,
    tie_margin: float = DEFAULT_LOGIT_TIE_MARGIN,
) -> Action:
    """
    top_k=1：直接 argmax。
    top_k>1 且高置信：仅当 logits 几乎相同时，在模型 top-k 内用 rerank_value 打破平局。
    top_k>1 且低置信：扩大候选（模型 top-k ∪ 启发式 top-k）再 rerank。
    """
    legal_list = list(legal)
    masked_logits = logits_row.masked_fill(mask_row < 0.5, -1e9)
    best_idx = int(masked_logits.argmax().item())
    best_action = index_to_action(best_idx, legal_list)

    if top_k <= 1:
        return best_action

    top_indices = model_top_k_indices(logits_row, mask_row, top_k)

    if max_prob >= low_confidence:
        tied_indices = narrow_logit_ties(logits_row, top_indices, tie_margin=tie_margin)
        if len(tied_indices) <= 1:
            return best_action
        candidates = [index_to_action(idx, legal_list) for idx in tied_indices]
        return pick_best_rerank(state, candidates)

    candidates = build_rerank_candidates(state, legal_list, top_indices, top_k)
    return pick_best_rerank(state, candidates)


# 兼容旧名
def expand_rerank_candidates(
    state: GameState,
    legal: Sequence[Action],
    model_indices: Sequence[int],
    pool_size: int,
    *,
    max_city_candidates: int = _DEFAULT_MAX_CITY_CANDIDATES,
) -> list[Action]:
    return build_rerank_candidates(
        state, legal, model_indices, pool_size, max_city_candidates=max_city_candidates
    )


def heuristic_step_delta(state: GameState, action: Action) -> int:
    before = heuristic_value(state)
    child = state.clone()
    child.do_turn(action)
    return heuristic_value(child) - before


def pick_best_by_heuristic(state: GameState, candidates: list[Action]) -> Action:
    return pick_best_rerank(state, candidates)
