"""
用 PlannedSearchAgent 录制 (state, action, mask) 专家轨迹，保存为 data/il_expert.npz。
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np

from game import GameConfig, GameState
from il.encoding import action_to_index, encode_state, legal_action_mask
from planned_search_agent import PlannedSearchAgent, SearchConfig


def collect_game(
    seed: int,
    *,
    map_size: int,
    turns: int,
    expert: PlannedSearchAgent,
) -> tuple[list[np.ndarray], list[int], list[np.ndarray], int]:
    state = GameState(GameConfig(map_size=map_size, total_turns=turns, seed=seed))
    states: list[np.ndarray] = []
    actions: list[int] = []
    masks: list[np.ndarray] = []

    while not state.is_terminal():
        action = expert.choose(state)
        states.append(encode_state(state))
        actions.append(action_to_index(action))
        masks.append(legal_action_mask(state))
        state.do_turn(action)

    return states, actions, masks, state.score()


def main() -> None:
    parser = argparse.ArgumentParser(description="录制 Planned 专家轨迹用于模仿学习")
    parser.add_argument("--map-size", type=int, default=10)
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument("--seeds", type=int, default=50, help="录制局数（seed 0..seeds-1）")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--out", type=str, default="data/il_expert.npz")
    parser.add_argument("--fast", action="store_true", help="缩小束搜索以加快录数据")
    parser.add_argument("--beam", type=int, default=None)
    parser.add_argument("--branch", type=int, default=None)
    parser.add_argument("--max-city-candidates", type=int, default=None)
    parser.add_argument("--max-horizon", type=int, default=None)
    args = parser.parse_args()

    if not (8 <= args.map_size <= 12):
        parser.error("--map-size 必须在 8~12")

    defaults = SearchConfig()
    if args.fast:
        cfg = SearchConfig(beam=8, branch=5, max_city_candidates=10, max_horizon=12)
    else:
        cfg = SearchConfig(
            beam=args.beam if args.beam is not None else defaults.beam,
            branch=args.branch if args.branch is not None else defaults.branch,
            max_city_candidates=(
                args.max_city_candidates
                if args.max_city_candidates is not None
                else defaults.max_city_candidates
            ),
            max_horizon=args.max_horizon,
        )

    expert = PlannedSearchAgent(config=cfg, rng=None)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_states: list[np.ndarray] = []
    all_actions: list[int] = []
    all_masks: list[np.ndarray] = []
    game_scores: list[int] = []

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    random.shuffle(seeds)

    for i, seed in enumerate(seeds):
        states, actions, masks, score = collect_game(
            seed, map_size=args.map_size, turns=args.turns, expert=expert
        )
        all_states.extend(states)
        all_actions.extend(actions)
        all_masks.extend(masks)
        game_scores.append(score)
        if (i + 1) % 5 == 0 or i + 1 == len(seeds):
            print(
                f"[{i + 1}/{len(seeds)}] seed={seed} score={score} "
                f"samples={len(all_states)} avg_score={sum(game_scores)/len(game_scores):.1f}",
                flush=True,
            )

    np.savez_compressed(
        out_path,
        states=np.stack(all_states).astype(np.float32),
        actions=np.array(all_actions, dtype=np.int64),
        masks=np.stack(all_masks).astype(np.float32),
        game_scores=np.array(game_scores, dtype=np.int32),
        map_size=np.int32(args.map_size),
        turns=np.int32(args.turns),
    )
    print(f"已保存 {len(all_states)} 条样本 -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
