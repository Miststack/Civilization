# 简化文明

> **v1.0.1** · [Release 说明](https://github.com/Miststack/Civilization/releases)

在 8～12 边长的随机方格地图上发展城市、放置建筑、研究科技，支持终端交互、Pygame 图形界面、JSON 存档，以及 Random / Greedy / 计划束搜索 / 模仿学习四种自动策略。

| 模块 | 说明 |
|------|------|
| `engine/` | 地图生成、回合结算、终局评分、JSON 存档 |
| `agents/`、`search/`、`il/` | 随机与贪心基线、束搜索、可选模仿学习 |
| `ui/` | 地图渲染、深/浅色主题、四槽存档、局内设置面板、GUI 偏好持久化 |

本文件说明**环境、命令行与测试**；完整课程设计、实验数据与提交清单见 **`课程设计报告.md`**（§8 实验、§10 提交清单）。演示 GIF 与 CSV 见 **`docs/README.md`**。

---

## 环境依赖

| 项目         | 说明                                               |
|------------|--------------------------------------------------|
| **操作系统**   | Windows / macOS / Linux 均可                       |
| **Python** | **3.10 及以上**（推荐 3.12+；开发验证过 3.14）                |
| **标准库**    | 运行游戏**仅需** Python 自带标准库，**不必** `pip install` 任何包 |
| **可选**     | 单元测试需 **`pytest`**；图形界面需 **`pygame`** 或 **`pygame-ce`**；模仿学习需 **`torch`**、**`numpy`**（见下文） |

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
| 模仿学习自动对局（需先训练 `data/il_policy.pt`） | `python main.py --map-size 10 --turns 30 --seed 0 --play learned --il-top-k 8 --quiet`     |
| 批量 benchmark 写 CSV                    | `python scripts/benchmark.py --agents learned --seeds 0-99 --il-top-k 8`                   |
| 困难 seed 定向 DAgger                    | `python -m il.improve_hard`                                                                |
| **Pygame 图形界面（手动）**              | `python main.py --gui --map-size 10 --turns 30 --seed 42 --play human`                        |
| **快捷启动图形界面**（默认 10×10 / 30 回合） | `python run_gui.py`                                                                           |
| 图形界面 + 浅色主题                        | `python run_gui.py --light` 或 `python main.py --gui --light --map-size 10 --play human`      |
| 图形界面旁观自动策略                         | `python main.py --gui --map-size 10 --turns 30 --seed 0 --play greedy --gui-delay 500`        |
| 图形界面旁观计划搜索                         | `python main.py --gui --map-size 10 --turns 30 --seed 0 --play planned --gui-delay 800`       |
| 图形界面旁观模仿学习                         | `python main.py --gui --map-size 10 --turns 30 --seed 0 --play learned`（GUI 默认 top-k=8）   |
| 图形界面放大 1.25 倍                       | `python run_gui.py --gui-scale 1.25`                                                          |
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
- **仅 `learned`**：`--il-weights`（默认 `data/il_policy.pt`）、`--il-device`（`cuda` / `cpu`）、`--il-top-k`（推理重排，**推荐 8**；CLI 默认 1 即纯 argmax，**GUI 默认 8**）。
- **图形界面**：`--gui` 启用 Pygame 窗口；`--gui-delay` 旁观模式每回合间隔毫秒（默认 450，可持久化）；`--light` 浅色主题；`--gui-scale` 界面缩放（0.85～2.0，默认 1.0）。未显式传 `--gui-delay` / `--il-top-k` 时，启动会读取 `saves/gui_prefs.json`。需先 `python -m pip install pygame`（**Python 3.14 请用 `pygame-ce`**）。

不加参数时：先询问地图边长，再询问游戏方式（含「计划束搜索」），然后进入对局。

### 图形界面（Pygame）

安装依赖后可用窗口化对局，规则与终端模式一致。

```bash
python -m pip install pygame-ce   # Python 3.14；其他版本可用 pygame
python run_gui.py                # 等价于 --gui --map-size 10 --turns 30 --play human
python run_gui.py --light        # 浅色主题
```

`run_gui.py` 会在默认参数后**追加**你传入的额外参数，例如：

```bash
python run_gui.py --seed 42 --light
python run_gui.py --play greedy --gui-delay 600
python run_gui.py --play learned    # 旁观模仿学习，top-k 可在局内设置中调节
```

**界面要点**

| 区域 | 说明 |
|------|------|
| 地图 | 程序化地形贴图、城市标记、合法格/悬停 3×3 预览、河流动画 |
| 侧栏 | 得分、回合、四类资源（含每回合产出）、科技 chip、动作按钮 |
| 底栏 | 消息流、快捷键提示（手动 / 旁观模式分别显示） |
| 设置 | 局内可改地图尺寸、回合数、种子、策略模式、旁观速度、界面缩放；选「模仿」时可调 **IL top-k**（1～16） |

**快捷键（手动模式）**

| 按键 | 作用 |
|------|------|
| `1`～`4` | 跳过 / 建城 / 建造 / 研究 |
| `F5` | 快速存档（槽位 0） |
| `F9` | 快速读档（槽位 0） |
| `T` | 切换深/浅色主题 |
| `Z` | 撤销上一步 |
| `H` | 动作历史面板 |
| `L` | 图例面板 |
| `Esc` | 关闭菜单 / 取消选城；否则退出 |

**快捷键（旁观模式）**

| 按键 | 作用 |
|------|------|
| `空格` / `P` | 暂停 / 继续 |
| `N` | 暂停时单步推进一回合 |
| `[` / `]` | 调慢 / 调快（增大 / 减小每回合间隔 ms） |
| `+` / `-` | 加速 / 减速（更直观；`+` 即更快） |
| `L` | 图例面板 |
| `Esc` | 退出 |

侧栏还提供 **存档 / 读档 / 主题 / 设置** 按钮；存档菜单内按 `0`～`3` 选择槽位（`Esc` 取消）。

**GUI 偏好**（`saves/gui_prefs.json`，v2）：主题、界面缩放、旁观速度（`auto_delay_ms`）、模仿学习 top-k（`il_top_k`，默认 8）。游戏中改速度 / top-k / 主题 / 缩放或退出时会自动保存；下次启动 `--gui` 时恢复（CLI 显式传 `--light` / `--gui-scale` / `--gui-delay` / `--il-top-k` 时优先于存档）。

**存档**

- **图形界面**：`engine/save.py` 四槽 JSON 存档（F5/F9）
- **终端模式**：主菜单 **5** 快速存档、**6** 快速读档（`engine/terminal_save.py`）
- 路径：`saves/quicksave.json`（槽位 0）、`saves/slot1.json`～`slot3.json`
- `saves/` 已加入 `.gitignore`

**主题**

- 深色（默认）与浅色两套配色，定义于 `ui/theme.py` 的 `DARK_THEME` / `LIGHT_THEME`
- 地形、按钮、侧栏等资源颜色随主题切换；游戏中按 `T` 或侧栏按钮即时切换

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
| **Pygame 图形界面**                    | `--gui --map-size 10 --turns 30 --seed 42 --play human`    |
| 图形界面 + 浅色主题                        | `--gui --light --map-size 10 --play human`                 |
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

| 文件 / 目录 | 说明 |
|-------------|------|
| `main.py` | 入口、命令行与终端交互；`--gui` 桥接图形界面 |
| `run_gui.py` | 图形界面快捷入口（默认 10×10、30 回合、手动模式） |
| `pyproject.toml` | 包元数据与可选依赖分组（`gui` / `il` / `dev`） |
| `.github/workflows/ci.yml` | GitHub Actions：Python 3.12 + pytest + numpy |
| `ui/` | Pygame 图形界面（见下表） |
| `engine/` | 游戏引擎：`game.py`、`map.py`、`models.py`、`save.py`、`actions.py`、`terminal_save.py` |
| `agents/` | 基线智能体 + `factory.py` 统一构造 |
| `search/` | 计划束搜索：`agent.py`、`rules.py`、`eval.py`、`prune.py` |
| `il/` | 模仿学习：编码、训练、DAgger、`LearnedAgent`、`improve_hard` |
| `scripts/` | `benchmark.py`（批量实验）、`gen_section9.py`（报告表格生成） |
| `saves/` | 图形界面本地存档与 GUI 偏好（自动生成，不入 Git） |
| `data/` | IL 本地生成数据（见 `data/README.md`，不入 Git） |
| `docs/` | 演示 GIF（`demos/`）、实验 CSV（`experiments/`），见 `docs/README.md` |
| `课程设计报告.md` | 课程设计报告（含 §8 实验与 §10 提交清单） |
| `tests/` | `pytest` 单元测试（**AI 辅助编写**，见报告 §3.2） |

**`ui/` 模块**

| 文件 | 说明 |
|------|------|
| `app.py` | `CivGameApp` 主类（Mixin 组合） |
| `pygame_app.py` | 兼容入口，re-export `CivGameApp` / `run_pygame_game` |
| `app_gameplay.py` | 对局逻辑：动作、智能体、设置、存档 |
| `app_input.py` | 按钮、点击、滚轮 |
| `app_draw.py` | 地图、侧栏、菜单、遮罩绘制 |
| `app_loop.py` | 主循环与事件分发 |
| `gui_types.py` | 常量、`InteractionMode`、`Button` 等 |
| `gui_format.py` | 字体与动作/建筑文本格式化 |
| `prefs.py` | 主题、缩放、旁观速度、IL top-k 偏好持久化（`gui_prefs.json` v2） |
| `theme.py` | 深/浅色主题常量、中文标签、布局尺寸 |
| `draw.py` | 圆角矩形、按钮、资源行、科技 chip 等 |
| `assets.py` | 程序化地形/城市/资源图标缓存 |
| `particles.py` | 建城/建造/研究动作粒子反馈 |
| `sharp.py` | Windows 高 DPI 清晰显示 |

运行与测试时**工作目录仍为项目根**（与 `main.py` 同级），以便 `python main.py` 与 `python -m il.*` 能解析 `engine`、`agents`、`search` 包。

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
python main.py --map-size 10 --turns 30 --seed 0 --play learned --il-top-k 8 --quiet
```

**提分流程**（DAgger 与困难 seed 定向采集）：

```bash
python -m il.improve              # 通用 DAgger + 重训
python -m il.improve_hard         # 从 CSV 筛落后 seed → 定向 DAgger → 微调（推荐）
```

| 模块 | 说明 |
|------|------|
| `il/record_expert.py` | 用 `PlannedSearchAgent` 录制 `(state, action)` 专家数据 |
| `il/record_dagger.py` | DAgger 采集（支持 `--seed-list` 指定 seed） |
| `il/train.py` | 训练 `PolicyNet`；`--select-by game_score` 按对局得分选模 |
| `il/improve.py` | 一键 DAgger + 重训 |
| `il/improve_hard.py` | 困难 seed 定向 DAgger + 微调 + benchmark |
| `il/hard_seeds.py` | 从 `seed_scores.csv` 筛选 `planned − learned` 落后的 seed |
| `il/learned_agent.py` | 加载权重对局；`top_k_rerank` 推理重排 |

训练产物默认写入 `data/`，该目录已在 `.gitignore` 中排除。

---

## 实验数据 `docs/experiments/seed_scores.csv`

在 **10×10 地图、30 回合** 下，对 **seed 0～99** 记录四种自动策略的终局 `score()`：

| 列名              | 策略                                                                       |
|-----------------|--------------------------------------------------------------------------|
| `random_score`  | `RandomAgent`                                                            |
| `greedy_score`  | `GreedyAgent`                                                            |
| `planned_score` | `PlannedSearchAgent`（默认 `beam=11`, `branch=6`, `max_city_candidates=13`） |
| `learned_score` | `LearnedAgent`（需本地 `data/il_policy.pt`；推理推荐 `--il-top-k 8`）              |

**当前汇总（N=100）**：Random **467.1** · Greedy **534.6** · Planned **635.6** · Learned **634.1**（与 Planned 差 **1.5** 分）。

批量复现：

```bash
python scripts/benchmark.py --agents random,greedy,planned,learned --seeds 0-99 --il-top-k 8
```

文件编码为 **UTF-8（含 BOM）**，可用 Excel 或 pandas 直接打开。复现某一 seed 示例：

```bash
python main.py --map-size 10 --turns 30 --seed 42 --play planned --quiet
python main.py --map-size 10 --turns 30 --seed 42 --play learned --il-top-k 8 --quiet
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

当前共 **81** 项用例（**13** 个 `test_*.py`），覆盖：游戏规则、JSON 存档、终端存读档、智能体工厂、GUI 偏好（含 v1 兼容）、搜索模块、IL 编码与困难 seed 筛选、`main` 子进程冒烟（`human` / `random` / `greedy` / `planned`）等。**无 GUI 自动化测试**（需人工 `--gui` 验证）。**测试文件由 AI 辅助编写**，详见 `课程设计报告.md` §3.2。

**CI**（`.github/workflows/ci.yml`）：Ubuntu + Python 3.12，安装 `pytest` + `numpy`；无 torch 时跳过 3 项 IL 权重测试。本地完整验证：

```bash
python -m pip install pytest numpy torch
python -m pytest tests -v
```

---

## 版本与发布

| 版本 | 要点 |
|------|------|
| **v1.0.1** | GUI 偏好 v2（旁观速度、IL top-k 持久化）；设置面板 top-k 控件；旁观快捷键（`P`/`+`/`-` 等）；81 项 pytest |
| **v1.0.0** | 终端 + Pygame GUI、JSON 四槽存档、深/浅色主题、局内设置；Random / Greedy / Planned / Learned 策略；100 seed 四策略实验（`docs/experiments/seed_scores.csv`）；GitHub CI |

历史 Release 见 [GitHub Releases](https://github.com/Miststack/Civilization/releases)。

---
