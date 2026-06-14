"""
DAgger：LearnedAgent 跑局，Planned 专家对每步状态打标签，合并进训练集。
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np

from engine.game import GameConfig, GameState
from il.encoding import action_to_index, encode_state, legal_action_mask
from il.learned_agent import LearnedAgent
from search import PlannedSearchAgent, SearchConfig


def collect_dagger_game(seed, *, map_size, turns, learner, expert):
    state = GameState(GameConfig(map_size=map_size, total_turns=turns, seed=seed))
    states, actions, masks = [], [], []
    corrections = 0
    while not state.is_terminal():
        learner_action = learner.choose(state)
        expert_action = expert.choose(state)
        if action_to_index(learner_action) != action_to_index(expert_action):
            corrections += 1
        states.append(encode_state(state))
        actions.append(action_to_index(expert_action))
        masks.append(legal_action_mask(state))
        state.do_turn(learner_action)
    return states, actions, masks, state.score(), corrections


def merge_npz(paths, out):
    chunks_s, chunks_a, chunks_m = [], [], []
    map_size, turns = 10, 30
    for path in paths:
        raw = np.load(path)
        chunks_s.append(raw["states"])
        chunks_a.append(raw["actions"])
        chunks_m.append(raw["masks"])
        map_size = int(raw.get("map_size", map_size))
        turns = int(raw.get("turns", turns))
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        states=np.concatenate(chunks_s).astype(np.float32),
        actions=np.concatenate(chunks_a).astype(np.int64),
        masks=np.concatenate(chunks_m).astype(np.float32),
        map_size=np.int32(map_size),
        turns=np.int32(turns),
    )
    return len(chunks_s[0]) if len(chunks_s) == 1 else sum(len(c) for c in chunks_s)


def parse_seed_list(text: str) -> list[int]:
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def main():
    p = argparse.ArgumentParser(description="DAgger 数据采集")
    p.add_argument("--base-data", default="data/il_expert.npz")
    p.add_argument("--weights", default="data/il_policy.pt")
    p.add_argument("--out", default="data/il_expert_dagger.npz")
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--seed-start", type=int, default=100)
    p.add_argument(
        "--seed-list",
        type=str,
        default=None,
        help="指定 seed 列表（逗号分隔），提供时忽略 --seeds / --seed-start",
    )
    p.add_argument("--map-size", type=int, default=10)
    p.add_argument("--turns", type=int, default=30)
    p.add_argument("--top-k", type=int, default=8)
    args = p.parse_args()

    learner = LearnedAgent(weights_path=args.weights, top_k_rerank=args.top_k)
    expert = PlannedSearchAgent(SearchConfig(), None)

    dagger_only = Path(str(args.out).replace(".npz", ".dagger_only.npz"))
    all_s, all_a, all_m = [], [], []
    total_corr = 0
    if args.seed_list:
        seeds = parse_seed_list(args.seed_list)
    else:
        seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    random.shuffle(seeds)

    for i, seed in enumerate(seeds):
        s, a, m, score, corr = collect_dagger_game(
            seed, map_size=args.map_size, turns=args.turns, learner=learner, expert=expert
        )
        all_s.extend(s); all_a.extend(a); all_m.extend(m)
        total_corr += corr
        if (i + 1) % 5 == 0 or i + 1 == len(seeds):
            print(f"[{i+1}/{len(seeds)}] seed={seed} score={score} corr={corr}", flush=True)

    np.savez_compressed(
        dagger_only,
        states=np.stack(all_s).astype(np.float32),
        actions=np.array(all_a, dtype=np.int64),
        masks=np.stack(all_m).astype(np.float32),
        map_size=np.int32(args.map_size),
        turns=np.int32(args.turns),
    )
    print(f"DAgger {len(all_s)} 条, 纠错 {total_corr} -> {dagger_only}", flush=True)

    paths = [Path(args.base_data), dagger_only] if Path(args.base_data).is_file() else [dagger_only]
    merge_npz(paths, Path(args.out))
    n = len(np.load(args.out)["states"])
    print(f"合并 -> {args.out} ({n} 条)", flush=True)


if __name__ == "__main__":
    main()
