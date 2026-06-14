"""从 seed_scores.csv 筛选困难 seed，定向 DAgger + 重训 + benchmark。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from il.hard_seeds import format_seed_summary, select_hard_seeds


def run(cmd: list[str]) -> None:
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="困难 seed 定向 DAgger 提分")
    p.add_argument(
        "--csv",
        default="docs/experiments/seed_scores.csv",
        help="含 planned_score / learned_score 的 CSV",
    )
    p.add_argument("--min-gap", type=int, default=15, help="至少落后 planned 多少分才纳入")
    p.add_argument("--top-n", type=int, default=50, help="最多取多少个困难 seed")
    p.add_argument("--base-data", default="data/il_expert_dagger.npz", help="合并的基础训练集")
    p.add_argument("--data", default="data/il_expert_dagger_hard.npz", help="合并后输出 npz")
    p.add_argument("--weights", default="data/il_policy.pt")
    p.add_argument("--out", default="data/il_policy.pt", help="训练后权重路径")
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--fine-tune", action=argparse.BooleanOptionalAction, default=True,
                   help="从 --weights 微调（默认开，减轻遗忘）")
    p.add_argument("--lr", type=float, default=5e-4, help="微调学习率（--fine-tune 时）")
    p.add_argument("--top-k", type=int, default=8, help="DAgger 时 LearnedAgent 的 top-k")
    p.add_argument("--skip-dagger", action="store_true")
    p.add_argument("--skip-train", action="store_true")
    p.add_argument("--skip-benchmark", action="store_true")
    p.add_argument("--seed-list", type=str, default=None, help="手动指定 seed，逗号分隔（覆盖 CSV 筛选）")
    args = p.parse_args()

    py = sys.executable
    csv_path = Path(args.csv)

    if args.seed_list:
        seeds = [int(s.strip()) for s in args.seed_list.split(",") if s.strip()]
    else:
        seeds = select_hard_seeds(csv_path, min_gap=args.min_gap, top_n=args.top_n)

    if not seeds:
        print(
            f"无符合条件的困难 seed（min_gap={args.min_gap}）。"
            " 请先运行 benchmark 填充 learned_score，或降低 --min-gap。",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"困难 seed {len(seeds)} 个（min_gap={args.min_gap}, top_n={args.top_n}）:", flush=True)
    if not args.seed_list and csv_path.is_file():
        print(format_seed_summary(csv_path, seeds), flush=True)
    else:
        print(" ", ", ".join(str(s) for s in seeds), flush=True)

    if not args.skip_dagger:
        cmd = [
            py,
            "-u",
            "-m",
            "il.record_dagger",
            "--seed-list",
            ",".join(str(s) for s in seeds),
            "--base-data",
            args.base_data,
            "--weights",
            args.weights,
            "--out",
            args.data,
            "--top-k",
            str(args.top_k),
        ]
        run(cmd)

    if not args.skip_train:
        train_cmd = [
            py,
            "-u",
            "-m",
            "il.train",
            "--data",
            args.data,
            "--out",
            args.out,
            "--epochs",
            str(args.epochs),
            "--patience",
            "12",
            "--select-by",
            "game_score",
            "--eval-every",
            "3",
            "--eval-seeds",
            "100",
        ]
        if args.fine_tune and Path(args.weights).is_file():
            train_cmd.extend(["--resume", args.weights, "--lr", str(args.lr)])
        run(train_cmd)

    if not args.skip_benchmark:
        run(
            [
                py,
                "scripts/benchmark.py",
                "--agents",
                "learned",
                "--seeds",
                "0-99",
                "--il-top-k",
                str(args.top_k),
            ]
        )

    print("完成。", flush=True)


if __name__ == "__main__":
    main()
