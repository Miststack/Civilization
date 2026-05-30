# 本地数据目录

本目录存放模仿学习（IL）流水线**本地生成**的文件，默认不提交到 Git。

| 文件 | 说明 |
|------|------|
| il_expert.npz | 专家轨迹（python -m il.record_expert） |
| il_policy.pt | 训练后的策略权重（python -m il.train） |
| *.log | 训练 / 录制日志 |

生成权重后，可用以下命令对局：

```bash
python main.py --map-size 10 --turns 30 --seed 0 --play learned --quiet
```

完整流程见项目根目录 README.md 中的「模仿学习」一节。
