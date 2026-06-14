# 文档与演示素材

| 路径 | 说明 |
|------|------|
| `demos/` | 课程演示 GIF（手动 / Random / Greedy / Planned，同 `--seed` 对照） |
| `experiments/seed_scores.csv` | seed 0～99 四策略终局分（Random / Greedy / Planned / Learned） |

**复现单点**（10×10、30 回合）：

```bash
python main.py --map-size 10 --turns 30 --seed 0 --play planned --quiet    # 示例 645
python main.py --map-size 10 --turns 30 --seed 0 --play learned --il-top-k 8 --quiet  # 需 data/il_policy.pt
python main.py --gui --play learned --seed 0    # 图形界面旁观模仿学习（GUI 默认 top-k=8）
python scripts/benchmark.py --agents learned --seeds 0-99 --il-top-k 8
```

**当前汇总（N=100）**：Random 467.1 · Greedy 534.6 · Planned 635.6 · Learned 634.1。

课程设计正文与统计见 **`课程设计报告.md`** §8～§9；运行说明见 **`README.md`**。

更新 §9 全表可运行：`python scripts/gen_section9.py`（输出片段供粘贴至报告）。
