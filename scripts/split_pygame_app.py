"""一次性脚本：将 pygame_app.py 拆分为多个模块。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
SRC = (UI / "pygame_app.py").read_text(encoding="utf-8")
lines = SRC.splitlines(keepends=True)


def find_prefix(prefix: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise ValueError(f"not found: {prefix!r}")


def slice_lines(a: int, b: int) -> str:
    return "".join(lines[a:b])


# --- gui_types.py ---
types_start = find_prefix("_AUTO_MODE_LABELS")
format_start = find_prefix("def _load_font")
class_start = find_prefix("class CivGameApp:")
draw_start = find_prefix("    def _draw_header")
run_start = find_prefix("    def run(")
run_game_start = find_prefix("def run_pygame_game")

(UI / "gui_types.py").write_text(
    '''"""GUI 共享类型与常量。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import pygame

from agents.factory import DEFAULT_IL_WEIGHTS
from engine.models import Action

'''
    + slice_lines(types_start, format_start)
    .replace("_AUTO_MODE_LABELS", "AUTO_MODE_LABELS")
    .replace("_AUTO_MODE_TITLES", "AUTO_MODE_TITLES")
    .replace("def _auto_mode_short_label", "def auto_mode_short_label"),
    encoding="utf-8",
)

format_src = (
    slice_lines(format_start, class_start)
    .replace("def _load_font", "def load_font")
    .replace("def _label_building", "def label_building")
    .replace("def _label_tech", "def label_tech")
    .replace("def _short_resource_cost", "def short_resource_cost")
    .replace("def _building_yield_hint", "def building_yield_hint")
    .replace("def _terrain_yield_hint", "def terrain_yield_hint")
    .replace("def _building_terrain_hint", "def building_terrain_hint")
    .replace("def _format_yields_static", "def format_yields_static")
    .replace("def _action_cost_text", "def action_cost_text")
    .replace("def _action_list_entry", "def action_list_entry")
    .replace("_format_yields_static", "format_yields_static")
    .replace("_building_yield_hint", "building_yield_hint")
    .replace("_label_building", "label_building")
    .replace("_label_tech", "label_tech")
    .replace("_short_resource_cost", "short_resource_cost")
    .replace("_action_cost_text", "action_cost_text")
)

(UI / "gui_format.py").write_text(
    '''"""GUI 文本格式化与字体加载。"""
from __future__ import annotations

import pygame

from engine.actions import action_label
from engine.game import GameState
from engine.models import (
    Action,
    ActionType,
    BUILDING_DEFS,
    BuildingType,
    CITY_BUILD_TURNS,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
)
from ui.theme import BUILDING_LABELS, RESOURCE_ICONS, TECH_LABELS

'''
    + format_src,
    encoding="utf-8",
)

gameplay_body = (
    slice_lines(find_prefix("    def _reload_fonts"), find_prefix("    def _panel_section_top"))
    .replace("_AUTO_MODE_TITLES", "AUTO_MODE_TITLES")
    .replace("_AUTO_MODE_LABELS", "AUTO_MODE_LABELS")
    .replace("_auto_mode_short_label", "auto_mode_short_label")
    .replace("_load_font", "load_font")
)
input_body = (
    slice_lines(find_prefix("    def _panel_section_top"), draw_start)
    .replace("_action_list_entry", "action_list_entry")
)
draw_body = slice_lines(draw_start, run_start)
loop_body = slice_lines(run_start, run_game_start)
tail = slice_lines(run_game_start, len(lines))

init_body = slice_lines(class_start + 1, find_prefix("    def _reload_fonts"))
# init_body 含 class 内 docstring，写入 app.py 时不再重复
if init_body.lstrip().startswith('"""'):
    end = init_body.find('"""', 3)
    if end != -1:
        init_body = init_body[end + 3 :].lstrip("\n")

COMMON_IMPORTS = '''from __future__ import annotations

import random
import sys
import threading
from typing import List, Optional, Sequence, Tuple

import pygame

from agents import GreedyAgent, RandomAgent
from agents.factory import AgentOptions, create_agent
from search import PlannedSearchAgent

try:
    from il.learned_agent import LearnedAgent
except ImportError:
    LearnedAgent = None  # type: ignore[misc, assignment]

from engine.actions import action_label, partition_legal
from engine.game import GameConfig, GameState
from engine.save import load_game, save_game, save_path, slot_summary
from engine.models import (
    Action,
    ActionType,
    BUILDING_DEFS,
    BuildingType,
    CITY_BUILD_TURNS,
    CITY_FIXED_YIELD,
    CITY_MAINTENANCE_FOOD,
    City,
    empty_resources,
    TECH_COST,
    TechType,
    TerrainType,
    TERRAIN_YIELDS,
)
from ui.assets import AssetAtlas
from ui.particles import ParticleSystem
from ui.draw import (
    draw_button,
    draw_card,
    draw_progress_bar,
    draw_resource_row,
    draw_rounded_rect,
    draw_tech_chips,
    draw_text,
    vertical_gradient,
)
from ui.prefs import save_gui_prefs
from ui.theme import (
    BUTTON_ICONS,
    DEFAULT_GUI_SCALE,
    Layout,
    RESOURCE_ICONS,
    RESOURCE_LABELS,
    TECH_LABELS,
    TERRAIN_LABELS,
    theme_by_name,
)
from ui.gui_types import (
    AUTO_DELAY_STEP_MS,
    AUTO_MODE_LABELS,
    AUTO_MODE_TITLES,
    Button,
    IL_WEIGHTS_PATH,
    InteractionMode,
    ListItem,
    auto_mode_short_label,
)
from ui.gui_format import (
    action_list_entry,
    building_terrain_hint,
    format_yields_static,
    label_building,
    label_tech,
    load_font,
    short_resource_cost,
    terrain_yield_hint,
)

'''

(UI / "app_gameplay.py").write_text(
    COMMON_IMPORTS
    + '''class GameplayMixin:
    """对局逻辑：动作、智能体、设置、存档。"""

'''
    + gameplay_body,
    encoding="utf-8",
)

(UI / "app_input.py").write_text(
    COMMON_IMPORTS
    + '''class InputMixin:
    """输入：按钮、点击、滚轮。"""

'''
    + input_body,
    encoding="utf-8",
)

# Fix references in draw body
draw_fixed = draw_body
replacements = {
    "_AUTO_MODE_LABELS": "AUTO_MODE_LABELS",
    "_short_resource_cost": "short_resource_cost",
    "_label_building": "label_building",
    "_label_tech": "label_tech",
    "_terrain_yield_hint": "terrain_yield_hint",
    "_building_terrain_hint": "building_terrain_hint",
    "_format_yields_static": "format_yields_static",
}
for old, new in replacements.items():
    draw_fixed = draw_fixed.replace(old, new)

(UI / "app_draw.py").write_text(
    COMMON_IMPORTS
    + '''class DrawMixin:
    """绘制：地图、侧栏、菜单、遮罩。"""

'''
    + draw_fixed,
    encoding="utf-8",
)

(UI / "app_loop.py").write_text(
    COMMON_IMPORTS
    + '''class LoopMixin:
    """主循环与事件分发。"""

'''
    + loop_body,
    encoding="utf-8",
)

(UI / "app.py").write_text(
    '''"""Pygame 图形界面主应用。"""
from __future__ import annotations

from typing import List, Optional

import pygame

from agents import GreedyAgent, RandomAgent
from search import PlannedSearchAgent

try:
    from il.learned_agent import LearnedAgent
except ImportError:
    LearnedAgent = None  # type: ignore[misc, assignment]

from engine.game import GameConfig, GameState
from engine.models import Action
from ui.app_draw import DrawMixin
from ui.app_gameplay import GameplayMixin
from ui.app_input import InputMixin
from ui.app_loop import LoopMixin
from ui.assets import AssetAtlas
from ui.gui_types import Button, InteractionMode, ListItem
from ui.particles import ParticleSystem
from ui.theme import DEFAULT_GUI_SCALE, Layout, theme_by_name


class CivGameApp(LoopMixin, DrawMixin, InputMixin, GameplayMixin):
    """Pygame 图形界面：人机对局或旁观自动智能体。"""

'''
    + init_body.replace("_apply_play_mode", "_apply_play_mode"),
    encoding="utf-8",
)

# Fix init: agent assignment at end
app_content = (UI / "app.py").read_text(encoding="utf-8")
if "self.agent = agent" not in app_content:
    app_content = app_content.replace(
        "        self._apply_play_mode()\n",
        "        self.agent = agent\n        self._apply_play_mode()\n",
    )
    (UI / "app.py").write_text(app_content, encoding="utf-8")

(UI / "pygame_app.py").write_text(
    '''"""Pygame GUI 入口（兼容旧 import 路径）。"""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from engine.game import GameState
from ui.app import CivGameApp
from ui.theme import DEFAULT_GUI_SCALE

__all__ = ["CivGameApp", "run_pygame_game", "main"]

'''
    + tail,
    encoding="utf-8",
)

print("split complete")
