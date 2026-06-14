"""终端模式存档/读档交互（与 GUI 共用 engine.save 格式）。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from engine.game import GameState
from engine.save import DEFAULT_SAVE_DIR, load_game, save_game, save_path, slot_summary

_SLOT_NAMES = {
    0: "快速存档 (F5)",
    1: "槽位 1",
    2: "槽位 2",
    3: "槽位 3",
}


def format_slot_line(slot: int, save_dir: Path | str = DEFAULT_SAVE_DIR) -> str:
    path = save_path(slot, save_dir)
    label = _SLOT_NAMES.get(slot, f"槽位 {slot}")
    if not path.is_file():
        return f"  [{slot}] {label} — （空）"
    meta = slot_summary(path)
    if meta is None:
        return f"  [{slot}] {label} — （损坏或无法读取）"
    return (
        f"  [{slot}] {label} — "
        f"回合 {meta['turn']} | 得分 {meta['score']} | "
        f"城市 {meta['cities']} | 建筑 {meta['buildings']} | "
        f"地图 {meta['map_size']}×{meta['map_size']}"
    )


def print_slot_menu(*, action: str, save_dir: Path | str = DEFAULT_SAVE_DIR) -> None:
    print(f"\n—— {action} ——")
    for slot in range(4):
        print(format_slot_line(slot, save_dir))
    print("  直接回车取消")


def prompt_save_slot(save_dir: Path | str = DEFAULT_SAVE_DIR) -> Optional[int]:
    print_slot_menu(action="选择存档槽位", save_dir=save_dir)
    raw = input("输入槽位序号 0～3: ").strip()
    if raw == "":
        return None
    try:
        slot = int(raw)
    except ValueError:
        print("请输入 0～3 的整数。")
        return None
    if not (0 <= slot <= 3):
        print("槽位须在 0～3 之间。")
        return None
    return slot


def prompt_load_slot(save_dir: Path | str = DEFAULT_SAVE_DIR) -> Optional[int]:
    print_slot_menu(action="选择读档槽位", save_dir=save_dir)
    raw = input("输入槽位序号 0～3: ").strip()
    if raw == "":
        return None
    try:
        slot = int(raw)
    except ValueError:
        print("请输入 0～3 的整数。")
        return None
    if not (0 <= slot <= 3):
        print("槽位须在 0～3 之间。")
        return None
    path = save_path(slot, save_dir)
    if not path.is_file():
        print(f"槽位 {slot} 为空，无法读档。")
        return None
    return slot


def terminal_save(state: GameState, save_dir: Path | str = DEFAULT_SAVE_DIR) -> bool:
    slot = prompt_save_slot(save_dir)
    if slot is None:
        print("已取消存档。")
        return False
    try:
        path = save_game(state, save_path(slot, save_dir))
    except OSError as exc:
        print(f"存档失败: {exc}")
        return False
    print(f"已存档至 {path}（回合 {state.turn}，当前得分 {state.score()}）")
    return True


def terminal_load(save_dir: Path | str = DEFAULT_SAVE_DIR) -> Optional[GameState]:
    slot = prompt_load_slot(save_dir)
    if slot is None:
        return None
    try:
        loaded = load_game(save_path(slot, save_dir))
    except (ValueError, KeyError, FileNotFoundError, OSError) as exc:
        print(f"读档失败: {exc}")
        return None
    if loaded.is_terminal():
        print(
            f"警告: 该存档已终局（回合 {loaded.turn}/{loaded.config.total_turns}），"
            "读档后将直接结束。"
        )
    print(
        f"已读档（槽位 {slot}）：回合 {loaded.turn}/{loaded.config.total_turns}，"
        f"当前得分 {loaded.score()}"
    )
    return loaded
