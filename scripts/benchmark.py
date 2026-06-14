"""
批量运行多策略对局并写入 CSV。

示例：
  python scripts/benchmark.py
  python scripts/benchmark.py --agents learned --seeds 0-9
  python scripts/benchmark.py --out docs/experiments/seed_scores.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.factory import AgentOptions, create_agent, DEFAULT_IL_WEIGHTS
from engine.game import GameConfig, GameState

ALL_AGENTS = ("random", "greedy", "planned", "learned")
SCORE_COLUMNS = {
    "random": "random_score",
    "greedy": "greedy_score",
    "planned": "planned_score",
    "learned": "learned_score",
}
STANDARD_COLUMNS = [SCORE_COLUMNS[a] for a in ALL_AGENTS]


def parse_seed_range(text: str) -> list[int]:
    text = text.strip()
    if "-" in text:
        start_s, end_s = text.split("-", 1)
        start, end = int(start_s), int(end_s)
        if end < start:
            raise ValueError(f"无效 seed 范围: {text}")
        return list(range(start, end + 1))
    if "," in text:
        return [int(part.strip()) for part in text.split(",") if part.strip()]
    return [int(text)]


def run_single_score(
    mode: str,
    *,
    map_size: int,
    turns: int,
    seed: int,
    agent_opts: AgentOptions,
) -> int:
    state = GameState(GameConfig(map_size=map_size, total_turns=turns, seed=seed))
    agent = create_agent(agent_opts)
    while not state.is_terminal():
        state.do_turn(agent.choose(state))  # type: ignore[attr-defined]
    return state.score()


def read_existing_csv(path: Path) -> dict[int, dict[str, str]]:
    if not path.is_file():
        return {}
    rows: dict[int, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            seed = int(row["seed"])
            rows[seed] = {k: v for k, v in row.items() if k != "seed" and v != ""}
    return rows


def write_csv(path: Path, rows: dict[int, dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["seed", *columns]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for seed in sorted(rows):
            out = {"seed": seed}
            for col in columns:
                out[col] = rows[seed].get(col, "")
            writer.writerow(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="批量策略对局并输出 seed_scores.csv")
    parser.add_argument("--seeds", type=str, default="0-99", help="如 0-99 或 0,1,42")
    parser.add_argument("--map-size", type=int, default=10)
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument(
        "--agents",
        type=str,
        default="random,greedy,planned,learned",
        help="逗号分隔：random,greedy,planned,learned",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="docs/experiments/seed_scores.csv",
    )
    parser.add_argument("--il-weights", type=str, default=DEFAULT_IL_WEIGHTS)
    parser.add_argument("--il-device", type=str, default=None)
    parser.add_argument("--il-top-k", type=int, default=1)
    parser.add_argument("--beam", type=int, default=None)
    parser.add_argument("--branch", type=int, default=None)
    parser.add_argument("--max-city-candidates", type=int, default=None)
    parser.add_argument("--max-horizon", type=int, default=None)
    args = parser.parse_args()

    if not (8 <= args.map_size <= 12):
        parser.error("--map-size 须在 8~12")

    seeds = parse_seed_range(args.seeds)
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    for agent in agents:
        if agent not in ALL_AGENTS:
            parser.error(f"未知策略: {agent}")

    if "learned" in agents and not Path(args.il_weights).is_file():
        print(
            f"警告: 未找到 {args.il_weights}，跳过 learned。"
            " 请先训练: python -m il.run_pipeline",
            file=sys.stderr,
        )
        agents = [a for a in agents if a != "learned"]

    out_path = Path(args.out)
    rows = read_existing_csv(out_path)
    for seed in seeds:
        rows.setdefault(seed, {})

    base_opts = AgentOptions(
        mode="random",
        map_seed=None,
        beam=args.beam,
        branch=args.branch,
        max_city_candidates=args.max_city_candidates,
        max_horizon=args.max_horizon,
        il_weights=args.il_weights,
        il_device=args.il_device,
        il_top_k=args.il_top_k,
    )

    total = len(seeds) * len(agents)
    step = 0
    for seed in seeds:
        for mode in agents:
            step += 1
            col = SCORE_COLUMNS[mode]
            print(f"[{step}/{total}] seed={seed} {mode} …", flush=True)
            opts = AgentOptions(
                mode=mode,
                map_seed=seed,
                beam=base_opts.beam,
                branch=base_opts.branch,
                max_city_candidates=base_opts.max_city_candidates,
                max_horizon=base_opts.max_horizon,
                il_weights=base_opts.il_weights,
                il_device=base_opts.il_device,
                il_top_k=base_opts.il_top_k,
            )
            score = run_single_score(
                mode,
                map_size=args.map_size,
                turns=args.turns,
                seed=seed,
                agent_opts=opts,
            )
            rows[seed][col] = str(score)
            print(f"  -> {score}", flush=True)

    write_csv(out_path, rows, STANDARD_COLUMNS)
    print(f"\n已写入 {out_path}（{len(seeds)} 个 seed，列: {', '.join(STANDARD_COLUMNS)}）")


if __name__ == "__main__":
    main()
