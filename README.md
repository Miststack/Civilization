# 简化文明

> 本文件为项目说明（`README.md`），用于说明运行源代码所需命令、环境依赖、智能体与测试方法。完整课程设计说明见 **`课程设计报告.md`**（含实验数据、对照分析与提交清单 §10）。

## 环境依赖

| 项目         | 说明                                               |
|------------|--------------------------------------------------|
| **操作系统**   | Windows / macOS / Linux 均可                       |
| **Python** | **3.10 及以上**（推荐 3.12+；开发验证过 3.14）                |
| **标准库**    | 运行游戏**仅需** Python 自带标准库，**不必** `pip install` 任何包 |
| **可选**     | 单元测试需 **`pytest`**；模仿学习需 **`torch`**、**`numpy`**（见下文） |

检查 Python 是否可用：

```bash
python --version
```

或（Windows 上若 `python` 不可用）：

```bash
py --version
```

---

## 运行源代码（命令）

**第一步**：进入与本 `README.md` 同级的项目根目录（内含 `main.py`）。

```bash
cd Civilization
```

（将 `Civilization` 换为你本地的文件夹名；路径可为相对路径，无需写盘符。）

**第二步**：启动程序。

```bash
python main.py
```

若系统只注册了 `py` 启动器：

```bash
py main.py
```

### 常用命令示例

| 需求                                | 命令                                                                                            |
|-----------------------------------|-----------------------------------------------------------------------------------------------|
| 查看全部参数说明                          | `python main.py -h`                                                                           |
| 固定 10×10、30 回合、可复现地图，手动模式（跳过启动询问） | `python main.py --map-size 10 --turns 30 --seed 42 --play human`                              |
| 随机策略自动对局                          | `python main.py --map-size 10 --turns 30 --seed 0 --play random --quiet`                      |
| Greedy 规则 baseline 自动对局           | `python main.py --map-size 10 --turns 30 --seed 0 --play greedy --quiet`                      |
| 计划束搜索自动对局（推荐加 `--quiet`）          | `python main.py --map-size 10 --turns 30 --seed 0 --play planned --quiet`                     |
| 模仿学习自动对局（需先训练 `data/il_policy.pt`） | `python main.py --map-size 10 --turns 30 --seed 0 --play learned --quiet`                     |
| 自定义束搜索参数                          | `python main.py --map-size 10 --turns 30 --seed 0 --play planned --beam 8 --branch 5 --quiet` |
| 指定策略随机源（与地图 `--seed` 独立）          | `python main.py --map-size 10 --play random --seed 1 --agent-seed 999`                        |

**参数摘要**：

- `--map-size`：地图边长，**8～12**；省略则启动时在终端询问。  
- `--turns`：总回合数，默认 **30**。  
- `--seed`：地图随机种子，`整数`；省略则每次地图不同。  
- `--play`：`human` / `random` / `greedy` / `planned` / `learned`；省略则启动时询问（1～5）。  
- `--quiet`：自动模式下减少打印。  
- `--agent-seed`：随机体 / 贪心平局随机源；计划搜索为确定性排序，此参数仅保留接口兼容。  
- **仅 `planned`**：`--beam`（束宽，默认 11）、`--branch`（分支上限，默认 6）、`--max-city-candidates`（建城 top-K，默认 13）、`--max-horizon`（模拟深度上限，默认用剩余回合数）。  
- **仅 `learned`**：`--il-weights`（权重路径，默认 `data/il_policy.pt`）、`--il-device`（`cuda` / `cpu`）、`--il-top-k`（top-k 启发式重排，默认 1）。

不加参数时：先询问地图边长，再询问游戏方式（含「计划束搜索」），然后进入对局。

### 在 PyCharm 中运行

1. **打开项目**：用 PyCharm 打开包含 `main.py` 的文件夹作为工程根目录。  
2. **运行配置**：**脚本** 选 `main.py`；**工作目录** 选项目根（与 `main.py` 同级），否则可能 `ModuleNotFoundError`。  
3. **解释器**：选择已安装 Python 3.10+ 的解释器。

#### 如何调整「形参」（种子、运行方式等）

「形参」对应命令行里 **`main.py` 后面的参数**，不要写 `python` 或 `main.py`。

1. 菜单 **运行** → **编辑配置…**（或右上角运行配置下拉 → **Edit Configurations…**）。  
2. 选中 **main**（或新建 **Python**，脚本指向 `main.py`）。 
3. 在 **「形参」**（英文：**Parameters**）输入框中填写，**多个参数用空格分隔**，例如：

| 目的                               | 形参栏填写示例                                                    |
|----------------------------------|------------------------------------------------------------|
| 指定地图种子 + 手动                      | `--map-size 10 --turns 30 --seed 42 --play human`          |
| 指定种子 + 随机体                       | `--map-size 10 --turns 30 --seed 0 --play random --quiet`  |
| 指定种子 + Greedy                    | `--map-size 10 --turns 30 --seed 0 --play greedy --quiet`  |
| 指定种子 + 计划束搜索                     | `--map-size 10 --turns 30 --seed 0 --play planned --quiet` |
| 指定种子 + 模仿学习                       | `--map-size 10 --turns 30 --seed 0 --play learned --quiet` |
| 只改种子和模式（仍会问地图边长若未写 `--map-size`） | `--seed 42 --play human`                                   |

- **选种子**：`--seed` 后跟整数。  
- **选运行方式**：`--play human` / `random` / `greedy` / `planned` / `learned`。  
- 想启动后**不再询问地图尺寸**：务必加上 `--map-size 8`～`12` 之一。  
- 自动模式想**少打印**：加 `--quiet`。  
- 计划搜索较慢，建议始终加 `--quiet` 只看终局得分。
4. 点 **应用 / 确定**，再点绿色 **运行**。

与终端等价关系：**形参** = `python main.py` 后面的整段，例如：

```bash
python main.py --seed 0 --play planned --map-size 10 --turns 30 --quiet
```

---

## 项目结构（简要）

| 文件 / 目录                                                  | 说明                                  |
|----------------------------------------------------------|-------------------------------------|
| `main.py`                                                | 入口、命令行与交互                           |
| `game.py`                                                | 对局规则、`GameState`、`score()`          |
| `map.py` / `models.py`                                   | 地图生成与数据定义                           |
| `random_agent.py` / `greedy_agent.py`                    | 随机 / 规则贪心基线                         |
| `planned_search_agent.py`                                | 计划束搜索智能体                            |
| `search_rules.py` / `search_eval.py` / `search_prune.py` | 搜索用合法动作、估值、剪枝                       |
| `il/`                                                    | 模仿学习：编码、录数据、训练、`LearnedAgent`        |
| `data/`                                                  | IL 本地生成数据（见 `data/README.md`，不入 Git）  |
| `课程设计报告.md`                                              | 课程设计报告（含 §8 实验与 §10 提交清单）           |
| `seed_scores.csv`                                        | 基线实验数据（见下）                          |
| `tests/`                                                 | `pytest` 单元测试（**AI 辅助编写**，见报告 §3.2） |

---

## 模仿学习（可选）

需安装依赖：

```bash
python -m pip install torch numpy
```

**一键流程**（录制专家轨迹 → 训练 → 提示对局命令）：

```bash
python -m il.run_pipeline --seeds 100 --epochs 50
```

分步执行：

```bash
python -m il.record_expert --seeds 100 --out data/il_expert.npz
python -m il.train --data data/il_expert.npz --out data/il_policy.pt
python main.py --map-size 10 --turns 30 --seed 0 --play learned --quiet
```

| 模块 | 说明 |
|------|------|
| `il/record_expert.py` | 用 `PlannedSearchAgent` 录制 `(state, action)` 专家数据 |
| `il/record_dagger.py` | DAgger 迭代采集（进阶） |
| `il/train.py` | 训练 `PolicyNet` 并保存权重 |
| `il/improve.py` | 评估与迭代改进脚本 |
| `il/learned_agent.py` | 加载权重对局的 `LearnedAgent` |

训练产物默认写入 `data/`，该目录已在 `.gitignore` 中排除。

---

## 实验数据 `seed_scores.csv`

在 **10×10 地图、30 回合** 下，对 **seed 0～99** 记录三种自动策略的终局 `score()`：

| 列名              | 策略                                                                       |
|-----------------|--------------------------------------------------------------------------|
| `random_score`  | `RandomAgent`                                                            |
| `greedy_score`  | `GreedyAgent`                                                            |
| `planned_score` | `PlannedSearchAgent`（默认 `beam=11`, `branch=6`, `max_city_candidates=13`） |

文件编码为 **UTF-8（含 BOM）**，可用 Excel 或 pandas 直接打开。复现某一 seed 的 planned 得分示例：

```bash
python main.py --map-size 10 --turns 30 --seed 42 --play planned --quiet
```

---

## 测试（可选）

需先安装 `pytest`（二选一）：

```bash
pip install pytest
```

```bash
python -m pip install pytest
```

在项目根目录执行：

```bash
python -m pytest tests -v
```

当前共 **57** 项用例，覆盖：游戏规则、`main` 冒烟（含 `planned` / `learned`）、搜索模块、计划智能体与 IL 编码等。**测试文件由 AI 辅助编写**，本人负责核对断言与实现是否一致；详见 `课程设计报告.md` §3.2。

---
