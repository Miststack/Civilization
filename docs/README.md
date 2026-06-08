# 文档与演示素材

| 路径 | 说明 |
|------|------|
| `demos/` | 课程演示 GIF（手动 / Random / Greedy / Planned，同 `--seed` 对照） |
| `experiments/seed_scores.csv` | seed 0～99 基线终局分（Random / Greedy / Planned） |

**复现单点**（10×10、30 回合）：

```bash
python main.py --map-size 10 --turns 30 --seed 0 --play planned --quiet   # 示例 645
```

课程设计正文与统计见 **`课程设计报告.md`** §8～§9；运行说明见 **`README.md`**。
