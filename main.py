from __future__ import annotations

import argparse
import random
import sys
from typing import List

from game import GameConfig, GameState
from greedy_agent import GreedyAgent
from models import Action, ActionType, BuildingType, TechType
from planned_search_agent import PlannedSearchAgent, SearchConfig
from random_agent import RandomAgent


def _pause_before_exit() -> None:
    """
    交互终端下在程序结束前等待一次回车，避免窗口立即关闭。
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return
    try:
        input("\n按回车键退出...")
    except (EOFError, KeyboardInterrupt):
        pass


def _action_label(a: Action) -> str:
    if a.type == ActionType.SKIP:
        return "跳过本回合"
    if a.type == ActionType.BUILD_CITY and a.x is not None and a.y is not None:
        return f"在 ({a.x}, {a.y}) 开始建城"
    if a.type == ActionType.BUILD_BUILDING and a.city_id is not None and a.building is not None:
        return f"城市 #{a.city_id} 建造 {a.building.value}"
    if a.type == ActionType.RESEARCH and a.tech is not None:
        return f"研究科技 {a.tech.value}"
    return str(a)


def _partition_legal(state: GameState) -> tuple[List[Action], List[Action], List[Action], List[Action]]:
    legal = state.legal_actions()
    skip_a: List[Action] = []
    build_city: List[Action] = []
    build_b: List[Action] = []
    research: List[Action] = []
    for a in legal:
        if a.type == ActionType.SKIP:
            skip_a.append(a)
        elif a.type == ActionType.BUILD_CITY:
            build_city.append(a)
        elif a.type == ActionType.BUILD_BUILDING:
            build_b.append(a)
        elif a.type == ActionType.RESEARCH:
            research.append(a)
    return skip_a, build_city, build_b, research


def _pick_from_list(items: List[Action], title: str) -> Action | None:
    if not items:
        print("当前没有可选项。")
        return None
    while True:
        print(title)
        for i, a in enumerate(items):
            print(f"  [{i}] {_action_label(a)}")
        raw = input("输入序号（直接回车取消）: ").strip()
        if raw == "":
            return None
        try:
            idx = int(raw)
        except ValueError:
            print("请输入整数序号，或回车取消。")
            continue
        if not (0 <= idx < len(items)):
            print("序号超出范围，请重试。")
            continue
        return items[idx]


def play(state: GameState) -> None:
    while not state.is_terminal():
        print("\n" + "=" * 56)
        print(state.render_map())
        print(state.summary())
        print(f"当前得分: {state.score()}")

        skips, cities, buildings, techs = _partition_legal(state)
        action: Action | None = None
        while True:
            print("\n主菜单（输入数字后回车）:")
            print("  1 — 跳过回合")
            if cities:
                print(f"  2 — 建城（当前 {len(cities)} 个合法坐标）")
            if buildings:
                print(f"  3 — 建造建筑（当前 {len(buildings)} 个合法组合）")
            if techs:
                print(f"  4 — 研究科技（当前 {len(techs)} 项可研究）")
            print("  0 — 结束游戏并退出")
            print("  h — 建筑/科技名称对照（farm / lumber_mill / mine / library …）")

            choice = input("\n请选择: ").strip().lower()

            if choice == "0":
                print("游戏已结束。")
                return
            if choice == "h":
                print(
                    "建筑: "
                    + ", ".join(f"{b.name}={b.value}" for b in BuildingType)
                    + "\n科技: "
                    + ", ".join(f"{t.name}={t.value}" for t in TechType)
                )
                continue
            if choice == "1":
                if not skips:
                    print("无法跳过（不应发生）。")
                    continue
                action = skips[0]
                break
            if choice == "2":
                if not cities:
                    print("当前没有可建城的位置。")
                    continue
                action = _pick_from_list(cities, "可选建城位置:")
                if action is None:
                    continue
                break
            if choice == "3":
                if not buildings:
                    print("当前没有可建造的建筑。")
                    continue
                action = _pick_from_list(buildings, "可选建造:")
                if action is None:
                    continue
                break
            if choice == "4":
                if not techs:
                    print("当前没有可研究的科技。")
                    continue
                action = _pick_from_list(techs, "可选研究:")
                if action is None:
                    continue
                break

            print("无效选择，请重新输入（1/2/3/4/0/h，视当前菜单项而定）。")
            continue

        assert action is not None  # 仅在选择 1～4 且子菜单未取消时 break 至此
        msg = state.do_turn(action)
        print(f"\n>>> {msg}")

    print("\n已达最大回合数，游戏自然结束。")
    print(state.render_map())
    print(state.summary())
    print(f"最终得分: {state.score()}")


def prompt_map_size() -> int:
    """启动时第一步：询问地图边长。直接回车为 10；否则须为 8~12 的整数。"""
    print("\n—— 第一步：地图尺寸 ——")
    print("  地图为正方形，边长须在 8 ~ 12 之间（例如 10 表示 10×10）。")
    while True:
        raw = input("请输入地图边长（不输入默认 10）: ").strip()
        if raw == "":
            return 10
        try:
            n = int(raw)
        except ValueError:
            print("请输入整数，或直接回车使用默认 10。")
            continue
        if 8 <= n <= 12:
            return n
        print("边长必须在 8 到 12 之间，请重试。")
    raise RuntimeError("unreachable")


def prompt_play_mode() -> str:
    """启动时询问游戏方式。"""
    while True:
        print("\n—— 游戏方式 ——")
        print("  1 — 手动操作（每回合自己选动作）")
        print("  2 — 随机策略（自动下棋）")
        print("  3 — 贪心策略（自动，启发式规则）")
        print("  4 — 计划束搜索（PlannedSearchAgent，多步前瞻）")
        raw = input("请选择 [1/2/3/4]: ").strip()
        if raw == "1":
            return "human"
        if raw == "2":
            return "random"
        if raw == "3":
            return "greedy"
        if raw == "4":
            return "planned"
        print("请输入 1～4 之间的数字。")


def play_agent(state: GameState, agent: object, *, quiet: bool = False) -> None:
    while not state.is_terminal():
        if not quiet:
            print("\n" + "=" * 56)
            print(state.render_map())
            print(state.summary())
            print(f"当前得分: {state.score()}")
        action = agent.choose(state)  # type: ignore[attr-defined]
        msg = state.do_turn(action)
        if not quiet:
            print(f"\n>>> [{_action_label(action)}] {msg}")
    if not quiet:
        print("\n已达最大回合数，游戏自然结束。")
        print(state.render_map())
        print(state.summary())
    print(f"最终得分: {state.score()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="文明简化版 — 手动 / 随机 / 贪心 / 计划搜索")
    parser.add_argument(
        "--map-size",
        type=int,
        default=None,
        help="地图边长 8~12；省略则在启动时第一步询问",
    )
    parser.add_argument("--turns", type=int, default=30, help="总回合数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（可复现地图）")
    parser.add_argument(
        "--play",
        choices=("human", "random", "greedy", "planned"),
        default=None,
        help="human / random / greedy / planned",
    )
    parser.add_argument(
        "--agent-seed",
        type=int,
        default=None,
        help="策略随机数种子（默认：地图 seed+1；地图无 seed 则系统随机）",
    )
    parser.add_argument("--quiet", action="store_true", help="自动模式少打印，只看最终得分等")
    parser.add_argument(
        "--beam",
        type=int,
        default=None,
        help="仅 planned：束宽（每层保留轨迹数，默认 11）",
    )
    parser.add_argument(
        "--branch",
        type=int,
        default=None,
        help="仅 planned：每结点展开动作数上限（默认 6）",
    )
    parser.add_argument(
        "--max-city-candidates",
        type=int,
        default=None,
        help="仅 planned：建城动作 top-K 剪枝（默认 13）",
    )
    parser.add_argument(
        "--max-horizon",
        type=int,
        default=None,
        help="仅 planned：模拟深度硬顶（默认用剩余回合数）",
    )
    args = parser.parse_args()

    if args.map_size is not None:
        if not (8 <= args.map_size <= 12):
            parser.error("--map-size 必须在 8~12 之间")
        map_size = args.map_size
    else:
        print("欢迎来到简化文明。")
        map_size = prompt_map_size()

    mode = args.play if args.play is not None else prompt_play_mode()
    cfg = GameConfig(map_size=map_size, total_turns=args.turns, seed=args.seed)
    state = GameState(cfg)

    if mode == "human":
        print("\n每回合先选动作，结算后进入下一回合。")
        try:
            play(state)
            _pause_before_exit()
        except (KeyboardInterrupt, EOFError):
            print("\n已中断退出。")
            sys.exit(0)
        return

    if args.agent_seed is not None:
        agent_rng = random.Random(args.agent_seed)
    elif args.seed is not None:
        agent_rng = random.Random(args.seed + 1)
    else:
        agent_rng = random.Random()

    agent: object
    if mode == "random":
        agent = RandomAgent(agent_rng)
    elif mode == "greedy":
        agent = GreedyAgent(agent_rng)
    elif mode == "planned":
        search_defaults = SearchConfig()
        search_cfg = SearchConfig(
            beam=args.beam if args.beam is not None else search_defaults.beam,
            branch=args.branch if args.branch is not None else search_defaults.branch,
            max_city_candidates=(
                args.max_city_candidates
                if args.max_city_candidates is not None
                else search_defaults.max_city_candidates
            ),
            max_horizon=args.max_horizon,
        )
        if search_cfg.beam < 1 or search_cfg.branch < 1 or search_cfg.max_city_candidates < 1:
            parser.error("--beam / --branch / --max-city-candidates 必须为正整数")
        if args.max_horizon is not None and args.max_horizon < 1:
            parser.error("--max-horizon 必须为正整数")
        agent = PlannedSearchAgent(config=search_cfg, rng=agent_rng)
    else:
        raise AssertionError(f"未知自动模式: {mode}")

    label = {
        "random": "随机",
        "greedy": "贪心",
        "planned": "计划束搜索",
    }[mode]
    extra = ""
    if mode == "planned" and isinstance(agent, PlannedSearchAgent):
        c = agent.config
        extra = (
            f" | beam={c.beam} branch={c.branch}"
            f" max_city={c.max_city_candidates} horizon={c.max_horizon!r}"
        )
    print(f"\n当前为自动模式：{label} | 地图 seed={args.seed!r}{extra}")
    if mode == "planned" and not args.quiet:
        print("提示：计划搜索较慢，可加 --quiet 减少输出。")
    try:
        play_agent(state, agent, quiet=args.quiet)
        _pause_before_exit()
    except (KeyboardInterrupt, EOFError):
        print("\n已中断退出。")
        sys.exit(0)

if __name__ == "__main__":
    main()