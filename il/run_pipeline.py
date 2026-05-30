"""
一键流程：录制专家数据 -> 训练 -> 可选评估。
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(">>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="模仿学习一键：录数据 + 训练")
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--map-size", type=int, default=10)
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--data", type=str, default="data/il_expert.npz")
    parser.add_argument("--out", type=str, default="data/il_policy.pt")
    args = parser.parse_args()

    record_cmd = [
        sys.executable,
        "-u",
        "-m",
        "il.record_expert",
        "--seeds",
        str(args.seeds),
        "--map-size",
        str(args.map_size),
        "--turns",
        str(args.turns),
        "--out",
        args.data,
    ]
    if args.fast:
        record_cmd.append("--fast")

    train_cmd = [
        sys.executable,
        "-u",
        "-m",
        "il.train",
        "--data",
        args.data,
        "--out",
        args.out,
        "--epochs",
        str(args.epochs),
        "--eval-seeds",
        "20",
    ]

    run(record_cmd)
    run(train_cmd)
    print("完成。运行对局:", flush=True)
    print(
        f"  python main.py --map-size {args.map_size} --turns {args.turns} "
        f"--seed 0 --play learned --il-weights {args.out} --quiet",
        flush=True,
    )


if __name__ == "__main__":
    main()
