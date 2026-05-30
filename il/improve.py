"""一键提分：DAgger 扩数据 + 从头训练 + 评估。"""
from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print('>>>', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(description='模仿学习提分流程')
    p.add_argument('--dagger-seeds', type=int, default=30)
    p.add_argument('--seed-start', type=int, default=100)
    p.add_argument('--epochs', type=int, default=50)
    p.add_argument('--data', default='data/il_expert_dagger.npz')
    p.add_argument('--out', default='data/il_policy.pt')
    p.add_argument('--skip-dagger', action='store_true')
    args = p.parse_args()
    py = sys.executable
    if not args.skip_dagger:
        run([py, '-u', '-m', 'il.record_dagger',
             '--seeds', str(args.dagger_seeds),
             '--seed-start', str(args.seed_start),
             '--out', args.data])
    run([py, '-u', '-m', 'il.train',
         '--data', args.data,
         '--out', args.out,
         '--epochs', str(args.epochs),
         '--patience', '12',
         '--select-by', 'game_score',
         '--eval-every', '3',
         '--eval-seeds', '100'])
    print('完成。', flush=True)


if __name__ == '__main__':
    main()
