# 本地数据目录

本目录存放模仿学习（IL）流水线**本地生成**的文件，默认不提交到 Git。

| 文件 | 说明 |
|------|------|
| `il_expert.npz` | 专家轨迹（`python -m il.record_expert`） |
| `il_expert_dagger.npz` | 合并 DAgger 后的训练集 |
| `il_expert_dagger_hard.npz` | 含困难 seed 定向 DAgger 的合并训练集 |
| `il_policy.pt` | 训练后的策略权重（`python -m il.train`） |
| `*.log` | 训练 / 录制日志 |

**一键训练**：

```bash
python -m il.run_pipeline --seeds 100 --epochs 50
```

**提分（推荐）**：

```bash
python -m il.improve --dagger-seeds 50 --seed-start 100
python -m il.improve_hard --min-gap 15    # 从 CSV 筛困难 seed，微调训练
```

生成权重后对局：

```bash
python main.py --map-size 10 --turns 30 --seed 0 --play learned --il-top-k 8 --quiet
python main.py --gui --play learned --seed 0    # 图形界面旁观，默认 top-k=8，可在设置中调节
```

完整流程见项目根目录 `README.md`「模仿学习」一节。
