from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Sequence, Tuple

import pygame

try:
    from il.learned_agent import LearnedAgent
except ImportError:
    LearnedAgent = None  # type: ignore[misc, assignment]

from agents import GreedyAgent, RandomAgent
from search import PlannedSearchAgent, SearchConfig
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
from ui.theme import (
    BUILDING_LABELS,
    BUTTON_ICONS,
    DEFAULT_GUI_SCALE,
    Layout,
    RESOURCE_ICONS,
    RESOURCE_LABELS,
    TECH_LABELS,
    TERRAIN_LABELS,
    theme_by_name,
)



_AUTO_MODE_LABELS: dict[str, str] = {
    "random": "随机",
    "greedy": "贪心",
    "planned": "搜索",
    "learned": "模仿",
}

_AUTO_MODE_TITLES: dict[str, str] = {
    "random": "随机策略",
    "greedy": "贪心策略",
    "planned": "计划束搜索",
    "learned": "模仿学习",
}

IL_WEIGHTS_PATH = "data/il_policy.pt"


def _auto_mode_short_label(play_mode: str) -> str:
    return _AUTO_MODE_LABELS.get(play_mode, "自动")


class InteractionMode(Enum):
    NORMAL = auto()
    BUILD_CITY = auto()
    BUILDING_LIST = auto()
    RESEARCH_LIST = auto()
    SAVE_MENU = auto()
    LOAD_MENU = auto()
    SETTINGS = auto()


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action_id: str
    enabled: bool = True
    active: bool = False


@dataclass
class ListItem:
    rect: pygame.Rect
    label: str
    sublabel: str
    action: Action


def action_label(a: Action) -> str:
    if a.type == ActionType.SKIP:
        return "跳过本回合"
    if a.type == ActionType.BUILD_CITY and a.x is not None and a.y is not None:
        return f"在 ({a.x}, {a.y}) 开始建城"
    if a.type == ActionType.BUILD_BUILDING and a.city_id is not None and a.building is not None:
        return f"城市 #{a.city_id} 建造 {a.building.value}"
    if a.type == ActionType.RESEARCH and a.tech is not None:
        return f"研究科技 {a.tech.value}"
    return str(a)


def partition_legal(
    state: GameState,
) -> tuple[List[Action], List[Action], List[Action], List[Action]]:
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


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in ("Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


def _label_building(building: BuildingType) -> str:
    return BUILDING_LABELS.get(building.value, building.value)


def _label_tech(tech: TechType) -> str:
    return TECH_LABELS.get(tech.value, tech.value)


def _short_resource_cost(cost: dict[str, int]) -> str:
    parts: list[str] = []
    for key in ("food", "wood", "ore", "science"):
        val = int(cost.get(key, 0))
        if val > 0:
            parts.append(f"{RESOURCE_ICONS[key]}{val}")
    return " ".join(parts) if parts else "免费"


def _building_yield_hint(building: BuildingType) -> str:
    bonus = BUILDING_DEFS[building]["yield_bonus"]
    assert isinstance(bonus, dict)
    return _format_yields_static(bonus)




def _terrain_yield_hint(terrain: TerrainType) -> str:
    yld = TERRAIN_YIELDS.get(terrain, {})
    if not yld:
        return "无产出"
    return _format_yields_static(yld)


def _building_terrain_hint(building: BuildingType) -> str:
    return _building_yield_hint(building)

def _format_yields_static(yields: dict[str, int]) -> str:
    parts = []
    for key in ("food", "wood", "ore", "science"):
        if int(yields.get(key, 0)) > 0:
            parts.append(f"{RESOURCE_ICONS[key]}{yields[key]}")
    return " ".join(parts) if parts else "无加成"


def _action_cost_text(state: GameState, action: Action) -> str:
    if action.type == ActionType.BUILD_BUILDING and action.building is not None:
        costs = BUILDING_DEFS[action.building]["cost"]
        assert isinstance(costs, dict)
        return f"消耗 {_short_resource_cost(costs)}  ·  +{_building_yield_hint(action.building)}/回合"
    if action.type == ActionType.RESEARCH and action.tech is not None:
        return f"消耗 {TECH_COST[action.tech]} 科技点"
    if action.type == ActionType.BUILD_CITY:
        costs = state._next_city_build_cost()
        return f"消耗 {_short_resource_cost(costs)}  ·  {CITY_BUILD_TURNS} 回合完工"
    return ""


def _action_list_entry(state: GameState, action: Action) -> tuple[str, str]:
    if action.type == ActionType.BUILD_BUILDING and action.building and action.city_id is not None:
        return (
            f"城市 #{action.city_id} · {_label_building(action.building)}",
            _action_cost_text(state, action),
        )
    if action.type == ActionType.RESEARCH and action.tech is not None:
        return _label_tech(action.tech), _action_cost_text(state, action)
    return action_label(action), _action_cost_text(state, action)


class CivGameApp:
    """Pygame 图形界面：人机对局或旁观自动智能体。"""

    def __init__(
        self,
        state: GameState,
        *,
        agent: Optional[object] = None,
        auto_delay_ms: int = 450,
        title: str = "简化文明",
        light_theme: bool = False,
        gui_scale: float = DEFAULT_GUI_SCALE,
        play_mode: Optional[str] = None,
    ) -> None:
        self.state = state
        self.auto_delay_ms = max(0, auto_delay_ms)
        self.title = title
        if play_mode is not None:
            self._settings_play_mode = play_mode
        elif agent is None:
            self._settings_play_mode = "human"
        elif isinstance(agent, RandomAgent):
            self._settings_play_mode = "random"
        elif isinstance(agent, PlannedSearchAgent):
            self._settings_play_mode = "planned"
        elif LearnedAgent is not None and isinstance(agent, LearnedAgent):
            self._settings_play_mode = "learned"
        else:
            self._settings_play_mode = "greedy"
        if auto_delay_ms > 0:
            self._settings_auto_delay_ms = max(50, auto_delay_ms)
        self.agent: Optional[object] = None
        self.human_mode = True
        self.light_theme = light_theme
        self.theme = theme_by_name(light_theme)
        self.layout = Layout(max(0.85, min(2.0, gui_scale)))

        self.mode = InteractionMode.NORMAL
        self.hover_cell: Optional[Tuple[int, int]] = None
        self.messages: List[str] = []
        self.game_over = False
        self.final_score: Optional[int] = None
        self._auto_timer = 0
        self._scroll_offset = 0
        self._toast_text = ""
        self._toast_until = 0
        self._overlay_close_rect: Optional[pygame.Rect] = None
        self._tech_bottom = 0
        self._resource_flash: dict[str, tuple[int, int]] = {}
        self._score_flash: tuple[int, int] | None = None
        self._turn_banner_until = 0
        self._turn_banner_text = ""
        self._slot_rects: list[tuple[pygame.Rect, int]] = []
        self._overlay_replay_rect: Optional[pygame.Rect] = None
        self._paused = False
        self._legend_open = False
        self._legend_scroll = 0
        self._startup_config = GameConfig(
            map_size=state.config.map_size,
            total_turns=state.config.total_turns,
            seed=state.config.seed,
        )
        self._selected_city_id: Optional[int] = None
        self._settings_map_size = state.config.map_size
        self._settings_turns = state.config.total_turns
        self._settings_seed = state.config.seed if state.config.seed is not None else 0
        self._settings_random_seed = state.config.seed is None
        self._settings_rects: list[tuple[pygame.Rect, str]] = []
        self._city_detail_close_rect: Optional[pygame.Rect] = None
        self._settings_auto_delay_ms = max(50, auto_delay_ms) if auto_delay_ms > 0 else 450

        self.buttons: List[Button] = []
        self.list_items: List[ListItem] = []
        self._legal_cache: tuple[List[Action], List[Action], List[Action], List[Action]] = (
            [],
            [],
            [],
            [],
        )

        pygame.init()
        self._reload_fonts()

        self._bg_surface: Optional[pygame.Surface] = None
        self._init_display()
        self._atlas = AssetAtlas(self.cell_size, self.theme)
        self._particles = ParticleSystem()
        self._apply_play_mode()

    def _reload_fonts(self) -> None:
        fs = lambda n: max(n, int(round(n * self.layout.scale)))
        self.font_display = _load_font(fs(26), bold=True)
        self.font_title = _load_font(fs(20), bold=True)
        self.font_body = _load_font(fs(16))
        self.font_small = _load_font(fs(14))
        self.font_tiny = _load_font(fs(13))

    def _init_display(self) -> None:
        pygame.display.init()
        pygame.display.set_caption(self.title)
        size = self.state.size
        map_px = size * self.cell_size + (size + 1) * self.layout.cell_gap + self.layout.margin * 2 + 24
        self.map_rect = pygame.Rect(
            self.layout.margin + 12,
            self.layout.header_height + self.layout.margin,
            map_px - self.layout.margin * 2 - 24,
            map_px - self.layout.margin * 2 - 24,
        )
        win_w = map_px + self.layout.panel_width
        win_h = max(map_px + 16, self.layout.header_height + self.layout.footer_height + self.layout.panel_min_height)
        self.screen = pygame.display.set_mode((win_w, win_h))
        self.panel_rect = pygame.Rect(map_px, 0, self.layout.panel_width, win_h)
        self.footer_rect = pygame.Rect(0, win_h - self.layout.footer_height, map_px, self.layout.footer_height)
        self.header_rect = pygame.Rect(0, 0, win_w, self.layout.header_height)
        self.clock = pygame.time.Clock()
        self._bg_surface = pygame.Surface((win_w, win_h))
        vertical_gradient(self._bg_surface, self.theme.bg_top, self.theme.bg_bottom)

    @property
    def cell_size(self) -> int:
        return self.layout.cell_size_for(self.state.size)

    def _refresh_legal(self) -> None:
        self._legal_cache = partition_legal(self.state)

    def _show_toast(self, text: str, ms: int = 1800) -> None:
        self._toast_text = text
        self._toast_until = pygame.time.get_ticks() + ms

    def _push_message(self, text: str) -> None:
        self.messages.append(text)
        if len(self.messages) > 5:
            self.messages = self.messages[-5:]
        self._show_toast(text)

    def _map_origin(self) -> Tuple[int, int]:
        return self.map_rect.x + self.layout.cell_gap + 12, self.map_rect.y + self.layout.cell_gap + 12

    def _cell_at_pos(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        ox, oy = self._map_origin()
        cs = self.cell_size
        gx, gy = pos[0] - ox, pos[1] - oy
        if gx < 0 or gy < 0:
            return None
        x, y = gx // (cs + self.layout.cell_gap), gy // (cs + self.layout.cell_gap)
        if x >= self.state.size or y >= self.state.size:
            return None
        return x, y

    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        ox, oy = self._map_origin()
        cs = self.cell_size
        return pygame.Rect(ox + x * (cs + self.layout.cell_gap), oy + y * (cs + self.layout.cell_gap), cs, cs)


    def _emit_action_particles(self, action: Action) -> None:
        cx, cy = self.map_rect.center
        if action.type == ActionType.BUILD_CITY and action.x is not None and action.y is not None:
            r = self._cell_rect(action.x, action.y)
            cx, cy = r.center
            self._particles.emit(cx, cy, self.theme.success, count=14, spread=2.8)
        elif action.type == ActionType.BUILD_BUILDING:
            for c in self.state.cities:
                if c.city_id == action.city_id:
                    r = self._cell_rect(c.x, c.y)
                    cx, cy = r.center
                    break
            self._particles.emit(cx, cy, self.theme.accent, count=12, spread=2.4)
        elif action.type == ActionType.RESEARCH:
            cx = self.panel_rect.centerx
            cy = self.panel_rect.centery
            self._particles.emit(cx, cy, self.theme.accent_blue, count=16, spread=3.0)
        else:
            self._particles.emit(cx, cy, self.theme.text_dim, count=6, spread=1.2)

    def _apply_action(self, action: Action) -> None:
        if self.game_over:
            return
        before_res = dict(self.state.resources)
        before_score = self.state.score()
        self.state.do_turn(action)
        self._flash_resource_deltas(before_res, self.state.resources)
        score_delta = self.state.score() - before_score
        if score_delta != 0:
            self._score_flash = (score_delta, pygame.time.get_ticks() + 1500)
        if not self.state.is_terminal():
            self._turn_banner_text = f"第 {self.state.turn} 回合"
            self._turn_banner_until = pygame.time.get_ticks() + 1100
        self._emit_action_particles(action)
        self._push_message(f"{action_label(action)}")
        self.mode = InteractionMode.NORMAL
        self._scroll_offset = 0
        self._selected_city_id = None
        if self.state.is_terminal():
            self.game_over = True
            self.final_score = self.state.score()
            self._push_message(f"游戏结束 · 得分 {self.final_score}")
        self._refresh_legal()

    def _agent_step(self) -> None:
        if self.agent is None or self.game_over:
            return
        self._apply_action(self.agent.choose(self.state))  # type: ignore[attr-defined]






    def _make_agent(self, play_mode: str) -> Optional[object]:
        if play_mode == "human":
            return None
        seed = self._startup_config.seed
        rng = random.Random(seed + 1) if seed is not None else random.Random()
        if play_mode == "random":
            return RandomAgent(rng)
        if play_mode == "planned":
            return PlannedSearchAgent(config=SearchConfig(), rng=rng)
        if play_mode == "learned":
            if LearnedAgent is None:
                raise ImportError("模仿学习需要 PyTorch，请先: python -m pip install torch")
            return LearnedAgent(weights_path=IL_WEIGHTS_PATH)
        return GreedyAgent(rng)

    def _apply_play_mode(self) -> None:
        try:
            self.agent = self._make_agent(self._settings_play_mode)
        except (ImportError, FileNotFoundError, OSError) as exc:
            if self._settings_play_mode == "learned":
                self._show_toast(str(exc))
                self._settings_play_mode = "greedy"
                self.agent = self._make_agent("greedy")
            else:
                raise
        self.human_mode = self._settings_play_mode == "human"
        if self.human_mode:
            self.title = "简化文明"
            self.auto_delay_ms = 0
            self._paused = False
        else:
            label = _AUTO_MODE_TITLES.get(self._settings_play_mode, "自动")
            self.title = f"简化文明 — {label}"
            self.auto_delay_ms = max(50, self._settings_auto_delay_ms)
        if getattr(self, "screen", None) is not None:
            pygame.display.set_caption(self.title)

    def _sync_settings_from_config(self) -> None:
        self._settings_map_size = self._startup_config.map_size
        self._settings_turns = self._startup_config.total_turns
        self._settings_random_seed = self._startup_config.seed is None
        self._settings_seed = 0 if self._settings_random_seed else int(self._startup_config.seed or 0)
        if self.human_mode:
            self._settings_play_mode = "human"
        elif isinstance(self.agent, RandomAgent):
            self._settings_play_mode = "random"
        elif isinstance(self.agent, PlannedSearchAgent):
            self._settings_play_mode = "planned"
        elif LearnedAgent is not None and isinstance(self.agent, LearnedAgent):
            self._settings_play_mode = "learned"
        else:
            self._settings_play_mode = "greedy"
        if not self.human_mode:
            self._settings_auto_delay_ms = self.auto_delay_ms

    def _open_settings(self) -> None:
        self._sync_settings_from_config()
        self._legend_open = False
        self._legend_scroll = 0
        self.mode = InteractionMode.SETTINGS
        self._selected_city_id = None

    def _set_gui_scale(self, scale: float) -> None:
        self.layout = Layout(max(0.85, min(2.0, round(scale, 2))))
        self._reload_fonts()
        self._init_display()
        self._atlas = AssetAtlas(self.cell_size, self.theme)
        self._rebuild_theme_assets()
        self._show_toast(f"界面缩放 {int(self.layout.scale * 100)}%")

    def _city_by_id(self, city_id: int) -> Optional[City]:
        for city in self.state.cities:
            if city.city_id == city_id:
                return city
        return None

    def _city_raw_yields(self, city: City) -> dict[str, int]:
        totals = empty_resources()
        for nx, ny in self.state._city_area_cells(city.x, city.y):
            for key, val in TERRAIN_YIELDS[self.state.grid[ny][nx]].items():
                totals[key] += int(val)
        for key, val in CITY_FIXED_YIELD.items():
            totals[key] += int(val)
        for building in city.buildings:
            bonus = BUILDING_DEFS[building]["yield_bonus"]
            assert isinstance(bonus, dict)
            for key, val in bonus.items():
                totals[key] += int(val)
        return totals

    def _city_overlap_cells(self, city: City) -> set[tuple[int, int]]:
        own = set(self.state._city_area_cells(city.x, city.y))
        overlap: set[tuple[int, int]] = set()
        for other in self.state.cities:
            if other.city_id == city.city_id:
                continue
            other_cells = set(self.state._city_area_cells(other.x, other.y))
            overlap |= own & other_cells
        return overlap

    def _start_new_game_from_settings(self) -> None:
        seed = None if self._settings_random_seed else int(self._settings_seed)
        cfg = GameConfig(
            map_size=int(self._settings_map_size),
            total_turns=int(self._settings_turns),
            seed=seed,
        )
        cfg.validate()
        self._startup_config = cfg
        self.state = GameState(cfg)
        self.game_over = False
        self.final_score = None
        self.mode = InteractionMode.NORMAL
        self.messages = []
        self._scroll_offset = 0
        self._resource_flash.clear()
        self._score_flash = None
        self._paused = False
        self._legend_open = False
        self._legend_scroll = 0
        self._auto_timer = 0
        self._selected_city_id = None
        self._init_display()
        self._atlas = AssetAtlas(self.cell_size, self.theme)
        self._rebuild_theme_assets()
        self._apply_play_mode()
        self._refresh_legal()
        mode_txt = "手动" if self.human_mode else _auto_mode_short_label(self._settings_play_mode)
        seed_txt = "随机" if seed is None else str(seed)
        self._show_toast(
            f"新局 {cfg.map_size}×{cfg.map_size} · {cfg.total_turns}回合 · {mode_txt} · 种子{seed_txt}"
        )

    def _handle_settings_click(self, action: str) -> None:
        if action == "settings_cancel":
            self.mode = InteractionMode.NORMAL
            return
        if action == "scale_down":
            self._set_gui_scale(self.layout.scale - 0.1)
            return
        if action == "scale_up":
            self._set_gui_scale(self.layout.scale + 0.1)
            return
        if action.startswith("map_"):
            self._settings_map_size = int(action.split("_", 1)[1])
            return
        if action == "turns_down":
            self._settings_turns = max(10, self._settings_turns - 5)
            return
        if action == "turns_up":
            self._settings_turns = min(60, self._settings_turns + 5)
            return
        if action == "seed_mode_random":
            self._settings_random_seed = True
            return
        if action == "seed_mode_fixed":
            self._settings_random_seed = False
            return
        if action == "seed_down":
            self._settings_random_seed = False
            self._settings_seed = max(0, self._settings_seed - 1)
            return
        if action == "seed_up":
            self._settings_random_seed = False
            self._settings_seed = min(9999, self._settings_seed + 1)
            return
        if action == "play_human":
            self._settings_play_mode = "human"
            return
        if action == "play_auto":
            self._settings_play_mode = "greedy" if self._settings_play_mode == "human" else self._settings_play_mode
            return
        if action.startswith("agent_"):
            mode_id = action.split("_", 1)[1]
            if mode_id == "learned" and LearnedAgent is None:
                self._show_toast("模仿学习需要 PyTorch，请先: python -m pip install torch")
                return
            if mode_id in _AUTO_MODE_LABELS:
                self._settings_play_mode = mode_id
            return
        if action == "delay_down":
            self._settings_auto_delay_ms = min(3000, self._settings_auto_delay_ms + 100)
            return
        if action == "delay_up":
            self._settings_auto_delay_ms = max(50, self._settings_auto_delay_ms - 100)
            return
        if action == "new_game_start":
            try:
                self._start_new_game_from_settings()
            except ValueError as exc:
                self._show_toast(str(exc))

    def _restart_game(self) -> None:
        self._open_settings()

    def _rebuild_theme_assets(self) -> None:
        w, h = self.screen.get_size()
        self._bg_surface = pygame.Surface((w, h))
        vertical_gradient(self._bg_surface, self.theme.bg_top, self.theme.bg_bottom)
        self._atlas = AssetAtlas(self.cell_size, self.theme)

    def _toggle_theme(self) -> None:
        self.light_theme = not self.light_theme
        self.theme = theme_by_name(self.light_theme)
        self._rebuild_theme_assets()
        name = "浅色" if self.light_theme else "深色"
        self._show_toast(f"已切换为{name}主题")

    def _area_yields(self, x: int, y: int) -> dict[str, int]:
        totals = {"food": 0, "wood": 0, "ore": 0, "science": 0}
        for nx, ny in self.state._city_area_cells(x, y):
            for key, val in TERRAIN_YIELDS[self.state.grid[ny][nx]].items():
                totals[key] = totals.get(key, 0) + int(val)
        return totals

    def _format_yields(self, yields: dict[str, int]) -> str:
        parts = []
        for key in ("food", "wood", "ore", "science"):
            if yields.get(key, 0) > 0:
                parts.append(f"{RESOURCE_ICONS[key]}{yields[key]}")
        return " ".join(parts) if parts else "无产出"

    def _flash_resource_deltas(self, before: dict[str, int], after: dict[str, int]) -> None:
        now = pygame.time.get_ticks()
        for key in before:
            delta = int(after.get(key, 0)) - int(before.get(key, 0))
            if delta != 0:
                self._resource_flash[key] = (delta, now + 1600)

    def _draw_city_range_preview(self, cx: int, cy: int) -> None:
        for nx, ny in self.state._city_area_cells(cx, cy):
            rect = self._cell_rect(nx, ny)
            color = self.theme.accent_soft if (nx, ny) == (cx, cy) else (100, 140, 200)
            pygame.draw.rect(self.screen, color, rect, width=1, border_radius=5)


    def _save_to_slot(self, slot: int) -> None:
        if self.game_over:
            return
        try:
            path = save_game(self.state, save_path(slot))
            self._show_toast(f"已存档 · 槽位 {slot if slot else '快速'}")
            self._push_message(f"存档成功: {path.name}")
        except OSError as exc:
            self._show_toast(f"存档失败: {exc}")

    def _load_from_slot(self, slot: int) -> None:
        path = save_path(slot)
        if not path.is_file():
            self._show_toast("该槽位暂无存档")
            return
        try:
            self.state = load_game(path)
            self.game_over = False
            self.final_score = None
            self.mode = InteractionMode.NORMAL
            self._scroll_offset = 0
            self._resource_flash.clear()
            self._score_flash = None
            self._refresh_legal()
            self._show_toast(f"读档成功 · 回合 {self.state.turn}")
            self._push_message(f"读档: {path.name}")
        except (OSError, ValueError, KeyError) as exc:
            self._show_toast(f"读档失败: {exc}")

    def _draw_save_load_menu(self, mode: str) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self.theme.overlay, 190))
        self.screen.blit(overlay, (0, 0))
        title = "选择存档位置" if mode == "save" else "选择读档位置"
        draw_text(self.screen, self.font_title, title, (self.screen.get_width() // 2, 120), self.theme.accent, center=True)
        draw_text(self.screen, self.font_tiny, "Esc 取消  ·  0=快速  1~3=槽位", (self.screen.get_width() // 2, 150), self.theme.text_dim, center=True)
        self._slot_rects = []
        cx = self.screen.get_width() // 2
        specs = [(0, "快速"), (1, "槽位 1"), (2, "槽位 2"), (3, "槽位 3")]
        start_x = cx - (4 * 118) // 2 + 8
        for i, (slot, label) in enumerate(specs):
            rect = pygame.Rect(start_x + i * 118, 190, 108, 120)
            meta = slot_summary(save_path(slot))
            draw_rounded_rect(self.screen, rect, self.theme.card_bg, radius=12, border=self.theme.panel_border_soft)
            draw_text(self.screen, self.font_body, label, (rect.centerx, rect.y + 16), self.theme.text, center=True)
            if meta:
                draw_text(self.screen, self.font_tiny, f"回合 {meta['turn']}", (rect.centerx, rect.y + 46), self.theme.text_dim, center=True)
                draw_text(self.screen, self.font_tiny, f"地图 {meta['map_size']}×{meta['map_size']}", (rect.centerx, rect.y + 64), self.theme.text_muted, center=True)
            else:
                draw_text(self.screen, self.font_tiny, "空", (rect.centerx, rect.y + 54), self.theme.text_muted, center=True)
            mouse = pygame.mouse.get_pos()
            if rect.collidepoint(mouse):
                draw_rounded_rect(self.screen, rect, self.theme.list_item_hover, radius=12, border=self.theme.accent)
            self._slot_rects.append((rect, slot))

    def _panel_section_top(self) -> int:
        return self._tech_bottom + 14

    def _build_action_buttons(self) -> None:
        skip_a, cities, buildings, techs = self._legal_cache
        x = self.panel_rect.x + self.layout.margin
        w = self.panel_rect.width - self.layout.margin * 2
        h = self.layout.button_height
        gap = self.layout.button_gap
        y = self._panel_section_top()

        specs: List[Tuple[str, str, bool, bool]] = [
            ("skip", "跳过回合", bool(skip_a), self.mode == InteractionMode.NORMAL),
            ("build_city", f"建城 · {len(cities)}", bool(cities), self.mode == InteractionMode.BUILD_CITY),
            ("build", f"建造 · {len(buildings)}", bool(buildings), self.mode == InteractionMode.BUILDING_LIST),
            ("research", f"研究 · {len(techs)}", bool(techs), self.mode == InteractionMode.RESEARCH_LIST),
        ]
        if self.mode in (InteractionMode.BUILDING_LIST, InteractionMode.RESEARCH_LIST):
            specs.append(("cancel", "取消选择", True, False))
        if self.mode == InteractionMode.NORMAL and not self.game_over:
            specs.extend([
                ("save_menu", "存档", True, False),
                ("load_menu", "读档", True, False),
                ("settings_menu", "设置", True, False),
                ("theme_toggle", "浅色" if not self.light_theme else "深色", True, False),
                ("legend_toggle", "图例", True, self._legend_open),
            ])

        quit_y = self.panel_rect.bottom - self.layout.margin - h
        self.buttons = []
        self.buttons.append(
            Button(pygame.Rect(x, quit_y, w, h), "退出游戏", "quit", enabled=True)
        )
        if self._legend_open:
            self.buttons.append(
                Button(
                    pygame.Rect(x, quit_y - gap - h, w, h),
                    "关闭图例",
                    "legend_toggle",
                    enabled=True,
                    active=True,
                )
            )
            return

        row_y = quit_y - gap - h
        for action_id, label, enabled, active in reversed(specs):
            self.buttons.append(
                Button(pygame.Rect(x, row_y, w, h), label, action_id, enabled=enabled, active=active)
            )
            row_y -= h + gap

    def _build_list_items(self) -> None:
        self.list_items = []
        _, _, buildings, techs = self._legal_cache
        if self.mode == InteractionMode.BUILDING_LIST:
            actions: Sequence[Action] = buildings
        elif self.mode == InteractionMode.RESEARCH_LIST:
            actions = techs
        else:
            return

        x = self.panel_rect.x + self.layout.margin + 6
        w = self.panel_rect.width - self.layout.margin * 2 - 12
        list_top = self._panel_section_top() + self.layout.list_panel_offset
        list_bottom = self.panel_rect.bottom - self.layout.margin - 52
        h = self.layout.list_item_height
        gap = self.layout.list_item_gap
        for i, action in enumerate(actions):
            y = list_top + i * (h + gap) - self._scroll_offset
            if y + h < list_top or y > list_bottom:
                continue
            title, sub = _action_list_entry(self.state, action)
            self.list_items.append(
                ListItem(pygame.Rect(x, y, w, h), title, sub, action)
            )

    def _handle_button(self, action_id: str) -> None:
        if action_id == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        if action_id == "skip":
            skip_a, _, _, _ = self._legal_cache
            if skip_a:
                self._apply_action(skip_a[0])
            return
        if action_id == "build_city":
            self._selected_city_id = None
            self.mode = InteractionMode.BUILD_CITY
            return
        if action_id == "build":
            self.mode = InteractionMode.BUILDING_LIST
            self._scroll_offset = 0
            return
        if action_id == "research":
            self.mode = InteractionMode.RESEARCH_LIST
            self._scroll_offset = 0
            return
        if action_id == "cancel":
            self.mode = InteractionMode.NORMAL
            self._scroll_offset = 0
            return
        if action_id == "save_menu":
            self.mode = InteractionMode.SAVE_MENU
            return
        if action_id == "load_menu":
            self.mode = InteractionMode.LOAD_MENU
            return
        if action_id == "settings_menu":
            self._open_settings()
            return
        if action_id == "legend_toggle":
            self._legend_open = not self._legend_open
            self._legend_scroll = 0
            if self._legend_open:
                self.mode = InteractionMode.NORMAL
                self._scroll_offset = 0
            return
        if action_id == "theme_toggle":
            self._toggle_theme()
            return

    def _handle_map_click(self, cell: Tuple[int, int]) -> None:
        x, y = cell
        city_by_pos = {(c.x, c.y): c for c in self.state.cities}
        if self.mode == InteractionMode.BUILD_CITY:
            for action in self._legal_cache[1]:
                if action.x == x and action.y == y:
                    self._apply_action(action)
                    return
            return
        if self.mode == InteractionMode.NORMAL and not self.game_over:
            if (x, y) in city_by_pos:
                city = city_by_pos[(x, y)]
                self._selected_city_id = (
                    None if self._selected_city_id == city.city_id else city.city_id
                )
            else:
                self._selected_city_id = None

    def _on_click(self, pos: Tuple[int, int]) -> None:
        if self.mode == InteractionMode.SETTINGS:
            for rect, action in self._settings_rects:
                if rect.collidepoint(pos):
                    self._handle_settings_click(action)
                    return
            self.mode = InteractionMode.NORMAL
            return
        if self.mode in (InteractionMode.SAVE_MENU, InteractionMode.LOAD_MENU):
            for rect, slot in self._slot_rects:
                if rect.collidepoint(pos):
                    if self.mode == InteractionMode.SAVE_MENU:
                        self._save_to_slot(slot)
                    else:
                        self._load_from_slot(slot)
                    self.mode = InteractionMode.NORMAL
                    return
            self.mode = InteractionMode.NORMAL
            return
        if self.game_over:
            if self._overlay_replay_rect and self._overlay_replay_rect.collidepoint(pos):
                self.game_over = False
                self._open_settings()
                return
            if self._overlay_close_rect and self._overlay_close_rect.collidepoint(pos):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        if (
            self._selected_city_id is not None
            and self._city_detail_close_rect is not None
            and self._city_detail_close_rect.collidepoint(pos)
        ):
            self._selected_city_id = None
            return
        if self.mode in (InteractionMode.BUILDING_LIST, InteractionMode.RESEARCH_LIST):
            for item in self.list_items:
                if item.rect.collidepoint(pos):
                    self._apply_action(item.action)
                    return
        for btn in self.buttons:
            if btn.rect.collidepoint(pos) and btn.enabled:
                self._handle_button(btn.action_id)
                return
        cell = self._cell_at_pos(pos)
        if cell is not None:
            self._handle_map_click(cell)

    def _on_wheel(self, delta: int) -> None:
        if self._legend_open:
            view_h = max(
                1,
                self.panel_rect.bottom
                - self._panel_section_top()
                - self.layout.margin
                - self.layout.button_height * 2
                - self.layout.button_gap,
            )
            self._legend_scroll = max(
                0, min(self._max_legend_scroll(view_h), self._legend_scroll - delta * 28)
            )
            return
        if self.mode in (InteractionMode.BUILDING_LIST, InteractionMode.RESEARCH_LIST):
            self._scroll_offset = max(0, self._scroll_offset - delta * 28)

    def _draw_header(self) -> None:
        draw_rounded_rect(self.screen, self.header_rect, (0, 0, 0, 0))
        header_bg = pygame.Surface((self.header_rect.width, self.header_rect.height), pygame.SRCALPHA)
        header_bg.fill((*self.theme.header_bg, 230))
        self.screen.blit(header_bg, self.header_rect.topleft)
        pygame.draw.line(
            self.screen,
            self.theme.panel_border_soft,
            (0, self.header_rect.bottom - 1),
            (self.header_rect.width, self.header_rect.bottom - 1),
        )
        draw_text(self.screen, self.font_title, self.title, (self.layout.margin + 4, 14), self.theme.accent)
        sub = "手动模式" if self.human_mode else "旁观模式"
        draw_text(self.screen, self.font_tiny, sub, (self.layout.margin + 4, 36), self.theme.text_dim)

        total = max(1, self.state.config.total_turns)
        ratio = min(1.0, (self.state.turn - 1) / total)
        bar = pygame.Rect(self.panel_rect.x + self.layout.margin, 18, self.panel_rect.width - self.layout.margin * 2, 8)
        draw_progress_bar(
            self.screen,
            bar,
            ratio,
            bg=self.theme.panel_bg_alt,
            fill=self.theme.accent_blue,
            border=self.theme.panel_border_soft,
            radius=4,
        )
        turn_txt = f"{self.state.turn} / {total}"
        draw_text(self.screen, self.font_tiny, turn_txt, (bar.right - 2, bar.y - 2), self.theme.text_muted)

    def _draw_map(self) -> None:
        frame = self.map_rect.inflate(24, 24)
        draw_card(self.screen, frame, self.theme.map_frame, self.theme.panel_border, radius=14, shadow=True)
        inner = self.map_rect.inflate(-4, -4)
        draw_rounded_rect(self.screen, inner, self.theme.map_inner, radius=10, border=self.theme.map_grid)

        _, cities, _, _ = self._legal_cache
        legal_cells = {(a.x, a.y) for a in cities if a.x is not None and a.y is not None}
        pending = {(x, y): remain for x, y, remain in self.state.pending_city_projects}
        city_by_pos = {(c.x, c.y): c for c in self.state.cities}
        size = self.state.size
        ox, oy = self._map_origin()

        for i in range(size):
            lx = ox - 18 + i * (self.cell_size + self.layout.cell_gap) + self.cell_size // 2
            draw_text(self.screen, self.font_tiny, str(i), (lx - 4, oy - 20), self.theme.text_muted)
            ly = oy - 18 + i * (self.cell_size + self.layout.cell_gap) + self.cell_size // 2
            draw_text(self.screen, self.font_tiny, str(i), (ox - 22, ly - 6), self.theme.text_muted)

        selected_city = self._city_by_id(self._selected_city_id) if self._selected_city_id else None
        influence: set[Tuple[int, int]] = set()
        if selected_city and self.mode == InteractionMode.NORMAL:
            for nx, ny in self.state._city_area_cells(selected_city.x, selected_city.y):
                influence.add((nx, ny))
        if self.hover_cell and self.mode == InteractionMode.BUILD_CITY:
            hx, hy = self.hover_cell
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = hx + dx, hy + dy
                    if 0 <= nx < size and 0 <= ny < size:
                        influence.add((nx, ny))

        for y in range(size):
            for x in range(size):
                rect = self._cell_rect(x, y)
                terrain = self.state.grid[y][x]
                shimmer = (pygame.time.get_ticks() % 3000) / 3000.0 if terrain == TerrainType.RIVER else 0.0
                self._atlas.blit_terrain(self.screen, rect, terrain, shimmer=shimmer)

                if (x, y) in influence:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    if self.mode == InteractionMode.BUILD_CITY and (x, y) not in legal_cells:
                        overlay.fill((120, 160, 220, 24))
                    elif selected_city and self.mode == InteractionMode.NORMAL:
                        overlay.fill((*self.theme.accent_blue, 32))
                    if overlay.get_at((0, 0))[3] > 0:
                        self.screen.blit(overlay, rect.topleft)

                if self.mode == InteractionMode.BUILD_CITY and (x, y) in legal_cells:
                    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
                    glow.fill((*self.theme.success, 70))
                    self.screen.blit(glow, rect.topleft)
                    draw_rounded_rect(self.screen, rect, self.theme.success, radius=6, border=self.theme.accent_soft, border_width=2)

                if self.hover_cell == (x, y):
                    draw_rounded_rect(self.screen, rect, (255, 255, 255), radius=6, border=self.theme.accent_soft, border_width=2)

                if (x, y) in pending:
                    self._atlas.blit_pending(self.screen, rect)
                    draw_rounded_rect(self.screen, rect, self.theme.warning, radius=6, border=self.theme.accent_soft, border_width=1)
                    remain = pending[(x, y)]
                    tag = self.font_tiny.render(f"{remain}回合", True, self.theme.text)
                    tag_bg = pygame.Rect(rect.x + 2, rect.y + 2, tag.get_width() + 6, 13)
                    draw_rounded_rect(self.screen, tag_bg, (*self.theme.overlay, 200), radius=4)
                    self.screen.blit(tag, (rect.x + 5, rect.y + 3))

                if (x, y) in city_by_pos:
                    city = city_by_pos[(x, y)]
                    self._atlas.blit_city(
                        self.screen, rect, city.city_id, self.font_tiny, len(city.buildings)
                    )


        # 地图暗角
        vig = pygame.Surface(self.map_rect.size, pygame.SRCALPHA)
        w, h = vig.get_size()
        for i in range(18):
            a = int(28 * i / 18)
            pygame.draw.rect(vig, (0, 0, 0, a), pygame.Rect(i, i, w - 2 * i, h - 2 * i), width=1, border_radius=8)
        self.screen.blit(vig, self.map_rect.topleft)
        if (
            self.hover_cell is not None
            and self.mode == InteractionMode.BUILD_CITY
            and self.hover_cell in legal_cells
        ):
            hx, hy = self.hover_cell
            pot = int(self.state._location_resource_potential(hx, hy))
            pot_rect = self._cell_rect(hx, hy)
            tag = self.font_tiny.render(f"潜力 {pot}", True, (240, 255, 240))
            bg = pygame.Rect(pot_rect.x, pot_rect.bottom - 14, tag.get_width() + 6, 13)
            draw_rounded_rect(self.screen, bg, (20, 60, 40), radius=4)
            self.screen.blit(tag, (pot_rect.x + 3, pot_rect.bottom - 13))


    def _legend_total_height(self) -> int:
        row_h = self.layout.px(42)
        gap = self.layout.px(6)
        sec = self.layout.px(20)
        pad = self.layout.px(16)
        counts = (len(TERRAIN_LABELS), len(BuildingType), 2)
        return pad + len(counts) * sec + sum(c * (row_h + gap) for c in counts) + pad

    def _max_legend_scroll(self, view_h: int) -> int:
        return max(0, self._legend_total_height() - view_h)

    def _draw_sidebar_legend(self, box: pygame.Rect) -> None:
        pad = self.layout.px(10)
        icon_sz = self.layout.px(22)
        row_h = self.layout.px(42)
        gap = self.layout.px(6)
        sec_h = self.layout.px(20)
        text_gap = self.layout.px(8)
        clip = self.screen.get_clip()
        self.screen.set_clip(box)

        sections: list[tuple[str, str, list[tuple[str, str, str]]]] = [
            (
                "地形",
                "terrain",
                [(tt.value, label, _terrain_yield_hint(tt)) for tt, label in TERRAIN_LABELS.items()],
            ),
            (
                "建筑",
                "building",
                [(b.value, _label_building(b), _building_terrain_hint(b)) for b in BuildingType],
            ),
            (
                "标记",
                "marker",
                [("city", "城市", "城心格"), ("pending", "施工中", f"需 {CITY_BUILD_TURNS} 回合")],
            ),
        ]

        y = box.y + pad - self._legend_scroll
        text_x_base = box.x + pad + icon_sz + text_gap

        for sec_name, kind, items in sections:
            draw_text(self.screen, self.font_small, sec_name, (box.x + pad, y), self.theme.accent)
            y += sec_h
            for key, title, sub in items:
                if y + row_h < box.y or y > box.bottom:
                    y += row_h + gap
                    continue
                row_rect = pygame.Rect(box.x + pad, y, box.width - pad * 2, row_h)
                draw_rounded_rect(
                    self.screen,
                    row_rect,
                    self.theme.list_item,
                    radius=8,
                    border=self.theme.panel_border_soft,
                )
                ir = pygame.Rect(row_rect.x + self.layout.px(6), y + (row_h - icon_sz) // 2, icon_sz, icon_sz)
                if kind == "terrain":
                    self._atlas.blit_terrain(self.screen, ir, TerrainType(key))
                    sub_col = self.theme.warning if key == TerrainType.WASTELAND.value else self.theme.text_dim
                elif kind == "building":
                    self._atlas.blit_building(self.screen, ir, BuildingType(key))
                    sub_col = self.theme.text_dim
                elif key == "city":
                    self._atlas.blit_city(self.screen, ir, 1, self.font_tiny, 0)
                    sub_col = self.theme.text_dim
                else:
                    self._atlas.blit_pending(self.screen, ir)
                    sub_col = self.theme.text_dim
                draw_text(self.screen, self.font_small, title, (text_x_base, y + 6), self.theme.text)
                if sub:
                    draw_text(self.screen, self.font_tiny, sub, (text_x_base, y + 24), sub_col)
                y += row_h + gap
            y += gap

        self.screen.set_clip(clip)
        if self._max_legend_scroll(box.height) > 0:
            draw_text(
                self.screen,
                self.font_tiny,
                "滚轮查看更多",
                (box.centerx, box.bottom - self.layout.px(14)),
                self.theme.text_muted,
                center=True,
            )

    def _draw_status_card(self) -> None:
        x = self.panel_rect.x + self.layout.margin
        card = pygame.Rect(x, self.layout.status_card_top, self.panel_rect.width - self.layout.margin * 2, self.layout.status_card_height)
        draw_card(self.screen, card, self.theme.card_bg, self.theme.card_border, radius=12)
        score = self.state.score()
        draw_text(self.screen, self.font_tiny, "得分", (card.x + 14, card.y + 10), self.theme.text_dim)
        draw_text(self.screen, self.font_display, f"{score}", (card.x + 14, card.y + 26), self.theme.accent)
        if self._score_flash is not None:
            delta, until = self._score_flash
            if pygame.time.get_ticks() <= until:
                sign = "+" if delta > 0 else ""
                flash_col = (120, 220, 150) if delta > 0 else (220, 120, 120)
                draw_text(self.screen, self.font_tiny, f"{sign}{delta}", (card.x + 80, card.y + 32), flash_col)
            else:
                self._score_flash = None
        stats = (
            f"城 {len(self.state.cities)}  "
            f"筑 {sum(len(c.buildings) for c in self.state.cities)}  "
            f"科 {len(self.state.tech_unlocked)}"
        )
        draw_text(self.screen, self.font_tiny, stats, (card.x + 14, card.y + 56), self.theme.text_muted)

        badge = pygame.Rect(card.right - 72, card.y + 12, 58, 52)
        draw_rounded_rect(self.screen, badge, self.theme.panel_bg_alt, radius=10, border=self.theme.panel_border_soft)
        draw_text(self.screen, self.font_tiny, "回合", (badge.centerx, badge.y + 8), self.theme.text_dim, center=True)
        draw_text(self.screen, self.font_title, f"{self.state.turn}", (badge.centerx, badge.y + 30), self.theme.text, center=True)

    def _draw_resources(self) -> None:
        x = self.panel_rect.x + self.layout.margin
        y = self.layout.resources_top
        w = self.panel_rect.width - self.layout.margin * 2
        h = self.layout.resource_row_height
        gap = self.layout.resource_row_gap
        prod = self.state.estimate_production()
        upkeep = len(self.state.cities) * CITY_MAINTENANCE_FOOD
        for key in ("food", "wood", "ore", "science"):
            rect = pygame.Rect(x, y, w, h)
            per_turn = prod[key]
            note = ""
            if key == "food" and upkeep > 0:
                per_turn = prod["food"] - upkeep
                note = f"(-{upkeep}维护)"
            draw_resource_row(
                self.screen,
                rect,
                icon=RESOURCE_ICONS[key],
                label=RESOURCE_LABELS[key],
                value=self.state.resources[key],
                per_turn=per_turn,
                color=self.theme.resource_colors[key],
                font_label=self.font_tiny,
                font_value=self.font_small,
                bg=self.theme.panel_bg_alt,
                border=self.theme.panel_border_soft,
                icon_surface=self._atlas.resource_icons.get(key),
            )
            flash = self._resource_flash.get(key)
            if flash is not None:
                delta, until = flash
                if pygame.time.get_ticks() <= until:
                    sign = "+" if delta > 0 else ""
                    col = (130, 220, 160) if delta > 0 else (230, 130, 130)
                    draw_text(self.screen, self.font_tiny, f"{sign}{delta}", (rect.right - 8, rect.y - 2), col)
                else:
                    del self._resource_flash[key]
            y += h + gap

    def _draw_tech_row(self) -> None:
        x = self.panel_rect.x + self.layout.margin
        box_top = self.layout.resources_top + 4 * (self.layout.resource_row_height + self.layout.resource_row_gap) + self.layout.px(8)
        box = pygame.Rect(x, box_top, self.panel_rect.width - self.layout.margin * 2, self.layout.tech_box_height)
        draw_rounded_rect(self.screen, box, self.theme.panel_bg_alt, radius=10, border=self.theme.panel_border_soft)
        draw_text(self.screen, self.font_tiny, "科技", (box.x + 10, box.y + 8), self.theme.text_dim)
        unlocked = {_label_tech(t) for t in self.state.tech_unlocked}
        bottom = draw_tech_chips(
            self.screen,
            (box.x + 8, box.y + 26),
            box.width - 16,
            list(TECH_LABELS.values()),
            font=self.font_tiny,
            unlocked=unlocked,
            chip_bg=self.theme.card_bg,
            chip_on=self.theme.tech_chip_on,
            text=self.theme.text,
            text_dim=self.theme.text_muted,
            border=self.theme.panel_border_soft,
        )
        self._tech_bottom = max(box.bottom, bottom + 6)

    def _draw_panel(self) -> None:
        panel_surf = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        vertical_gradient(panel_surf, self.theme.panel_bg, self.theme.panel_bg)
        self.screen.blit(panel_surf, self.panel_rect.topleft)
        pygame.draw.line(
            self.screen,
            self.theme.panel_border,
            (self.panel_rect.x, 0),
            (self.panel_rect.x, self.panel_rect.height),
            2,
        )

        self._tech_bottom = 300
        self._draw_status_card()
        self._draw_resources()
        self._draw_tech_row()

        if self.human_mode and not self.game_over:
            self._build_action_buttons()
            action_card = pygame.Rect(
                self.panel_rect.x + self.layout.margin,
                self._panel_section_top() - 10,
                self.panel_rect.width - self.layout.margin * 2,
                self.panel_rect.bottom - self._panel_section_top() - 20,
            )
            draw_rounded_rect(
                self.screen,
                action_card,
                self.theme.action_card,
                radius=12,
                border=self.theme.panel_border_soft,
            )
            draw_text(
                self.screen,
                self.font_tiny,
                "行动  ·  F5存 F9读  1~4  ·  点城市查看",
                (action_card.x + 12, action_card.y + 8),
                self.theme.text_dim,
            )

            if (
                self._selected_city_id is not None
                and self.mode == InteractionMode.NORMAL
                and not self._legend_open
            ):
                self._draw_city_detail(action_card)
            mouse = pygame.mouse.get_pos()
            for btn in self.buttons:
                draw_button(
                    self.screen,
                    btn.rect,
                    btn.label,
                    font=self.font_body,
                    icon=BUTTON_ICONS.get(btn.action_id, ""),
                    enabled=btn.enabled,
                    active=btn.active,
                    hover=btn.rect.collidepoint(mouse),
                    palette=self.theme.ui_palette,
                )

            if self._legend_open:
                legend_box = pygame.Rect(
                    action_card.x + 8,
                    action_card.y + self.layout.px(28),
                    action_card.width - 16,
                    action_card.bottom - action_card.y - self.layout.px(36),
                )
                draw_rounded_rect(
                    self.screen,
                    legend_box,
                    self.theme.list_box,
                    radius=8,
                    border=self.theme.panel_border_soft,
                )
                draw_text(
                    self.screen,
                    self.font_tiny,
                    "地图图例  ·  L 或 Esc 关闭",
                    (legend_box.x + 10, legend_box.y + 6),
                    self.theme.text_muted,
                )
                inner = legend_box.inflate(-4, -self.layout.px(18))
                inner.y += self.layout.px(14)
                inner.height -= self.layout.px(10)
                self._draw_sidebar_legend(inner)
            elif self.mode in (InteractionMode.BUILDING_LIST, InteractionMode.RESEARCH_LIST):
                list_box = pygame.Rect(
                    action_card.x + 8,
                    self._panel_section_top() + self.layout.list_panel_inner_offset,
                    action_card.width - 16,
                    action_card.bottom - self._panel_section_top() - self.layout.px(228),
                )
                draw_rounded_rect(self.screen, list_box, self.theme.list_box, radius=8, border=self.theme.panel_border_soft)
                title = "选择建造项目" if self.mode == InteractionMode.BUILDING_LIST else "选择研究项目"
                draw_text(self.screen, self.font_tiny, title, (list_box.x + 10, list_box.y + 6), self.theme.text_muted)
                self._build_list_items()
                for item in self.list_items:
                    hover = item.rect.collidepoint(mouse)
                    draw_rounded_rect(
                        self.screen,
                        item.rect,
                        self.theme.list_item_hover if hover else self.theme.list_item,
                        radius=8,
                        border=self.theme.accent if hover else self.theme.panel_border_soft,
                    )
                    draw_text(
                        self.screen,
                        self.font_small,
                        item.label,
                        (item.rect.x + 10, item.rect.y + 6),
                        self.theme.text,
                    )
                    if item.sublabel:
                        draw_text(
                            self.screen,
                            self.font_tiny,
                            item.sublabel,
                            (item.rect.x + 10, item.rect.y + 22),
                            self.theme.text_muted,
                        )
            elif self.mode == InteractionMode.BUILD_CITY:
                _, city_actions, _, _ = self._legal_cache
                legal_cells = {(a.x, a.y) for a in city_actions if a.x is not None and a.y is not None}
                costs = self.state._next_city_build_cost()
                tip_rect = pygame.Rect(
                    action_card.x + 10,
                    action_card.bottom - 44,
                    action_card.width - 20,
                    34,
                )
                draw_rounded_rect(
                    self.screen,
                    tip_rect,
                    self.theme.panel_bg_alt,
                    radius=8,
                    border=self.theme.success,
                )
                draw_text(
                    self.screen,
                    self.font_tiny,
                    f"点击高亮格建城  ·  {_short_resource_cost(costs)}  ·  {CITY_BUILD_TURNS}回合",
                    (tip_rect.x + 10, tip_rect.y + 6),
                    self.theme.text,
                )
                draw_text(
                    self.screen,
                    self.font_tiny,
                    f"合法地块 {len(legal_cells)} 处",
                    (tip_rect.x + 10, tip_rect.y + 20),
                    self.theme.text_muted,
                )
        elif not self.human_mode and not self.game_over:
            if self._legend_open:
                lx = self.panel_rect.x + self.layout.margin
                legend_box = pygame.Rect(
                    lx,
                    self._panel_section_top(),
                    self.panel_rect.width - self.layout.margin * 2,
                    self.panel_rect.bottom - self._panel_section_top() - self.layout.margin,
                )
                draw_rounded_rect(
                    self.screen,
                    legend_box,
                    self.theme.list_box,
                    radius=8,
                    border=self.theme.panel_border_soft,
                )
                draw_text(
                    self.screen,
                    self.font_tiny,
                    "地图图例  ·  L 关闭",
                    (legend_box.x + 10, legend_box.y + 6),
                    self.theme.text_muted,
                )
                inner = legend_box.inflate(-4, -self.layout.px(18))
                inner.y += self.layout.px(14)
                self._draw_sidebar_legend(inner)
            else:
                status = "已暂停" if self._paused else f"自动推进中…  {self.auto_delay_ms}ms/回合"
                draw_text(
                    self.screen,
                    self.font_small,
                    status,
                    (self.panel_rect.x + self.layout.margin, self._panel_section_top()),
                    self.theme.text_dim,
                )
                draw_text(
                    self.screen,
                    self.font_tiny,
                    "空格暂停  [ 减速  ] 加速  ·  L 图例",
                    (self.panel_rect.x + self.layout.margin, self._panel_section_top() + 22),
                    self.theme.text_muted,
                )


    def _draw_turn_banner(self) -> None:
        if pygame.time.get_ticks() > self._turn_banner_until or not self._turn_banner_text:
            return
        elapsed = self._turn_banner_until - pygame.time.get_ticks()
        alpha = min(255, max(40, int(255 * elapsed / 1100)))
        text = self.font_title.render(self._turn_banner_text, True, self.theme.accent)
        box = text.get_rect()
        box.width += 40
        box.height += 16
        box.center = self.map_rect.center
        surf = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*self.theme.header_bg, alpha), surf.get_rect(), border_radius=12)
        pygame.draw.rect(surf, (*self.theme.accent, alpha), surf.get_rect(), width=2, border_radius=12)
        ts = text.copy()
        ts.set_alpha(alpha)
        surf.blit(ts, ts.get_rect(center=surf.get_rect().center))
        self.screen.blit(surf, box.topleft)

    def _draw_hover_tooltip(self) -> None:
        if self.hover_cell is None or self.game_over:
            return
        hx, hy = self.hover_cell
        rect = self._cell_rect(hx, hy)
        terrain = self.state.grid[hy][hx]
        lines = [TERRAIN_LABELS[terrain], f"3×3: {self._format_yields(self._area_yields(hx, hy))}"]
        if self.mode == InteractionMode.BUILD_CITY:
            ok, reason = self.state.can_build_city(hx, hy)
            if ok:
                costs = self.state._next_city_build_cost()
                lines.append(
                    f"可建城 · 潜力 {int(self.state._location_resource_potential(hx, hy))}"
                    f"  ·  {_short_resource_cost(costs)}"
                )
            else:
                lines.append(reason)
        tw = max(self.font_tiny.size(line)[0] for line in lines) + 20
        th = 10 + len(lines) * 16
        tip_x = min(rect.right + 8, self.map_rect.right - tw)
        tip_y = max(self.map_rect.y, rect.y - 4)
        box = pygame.Rect(tip_x, tip_y, tw, th)
        draw_rounded_rect(self.screen, box, (22, 30, 44), radius=8, border=self.theme.accent_soft)
        for i, line in enumerate(lines):
            draw_text(self.screen, self.font_tiny, line, (box.x + 10, box.y + 6 + i * 16), self.theme.text)

    def _draw_footer(self) -> None:
        foot = pygame.Surface(self.footer_rect.size, pygame.SRCALPHA)
        foot.fill((*self.theme.footer_bg, 240))
        self.screen.blit(foot, self.footer_rect.topleft)
        pygame.draw.line(
            self.screen,
            self.theme.panel_border_soft,
            (0, self.footer_rect.y),
            (self.footer_rect.width, self.footer_rect.y),
        )

        x, y = self.layout.margin + 4, self.footer_rect.y + 12
        if self.hover_cell is not None:
            hx, hy = self.hover_cell
            terrain = self.state.grid[hy][hx]
            cell_y = TERRAIN_YIELDS[terrain]
            area = self._area_yields(hx, hy)
            line1 = f"({hx},{hy}) {TERRAIN_LABELS[terrain]}  格产出: {self._format_yields(cell_y)}"
            line2 = f"3×3 范围: {self._format_yields(area)}"
            pill = pygame.Rect(x, y, self.footer_rect.width - self.layout.margin * 2, 46)
            draw_rounded_rect(self.screen, pill, self.theme.panel_bg_alt, radius=10, border=self.theme.panel_border_soft)
            draw_text(self.screen, self.font_small, line1, (pill.x + 12, pill.y + 6), self.theme.text)
            draw_text(self.screen, self.font_tiny, line2, (pill.x + 12, pill.y + 26), self.theme.text_dim)
            y += 52

        for msg in self.messages[-2:]:
            draw_text(self.screen, self.font_tiny, f"› {msg}", (x, y), self.theme.text_dim)
            y += 18

    def _draw_toast(self) -> None:
        if not self._toast_text or pygame.time.get_ticks() > self._toast_until:
            return
        remain = self._toast_until - pygame.time.get_ticks()
        alpha = min(255, max(60, int(255 * remain / 1800)))
        text = self.font_small.render(self._toast_text, True, self.theme.text)
        pad_x, pad_y = 16, 8
        box = text.get_rect()
        box.width += pad_x * 2
        box.height += pad_y * 2
        box.centerx = self.map_rect.centerx
        box.y = self.map_rect.y + 4
        surf = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*self.theme.toast_bg, alpha), surf.get_rect(), border_radius=10)
        pygame.draw.rect(surf, (*self.theme.accent, alpha), surf.get_rect(), width=1, border_radius=10)
        ts = text.copy()
        ts.set_alpha(alpha)
        surf.blit(ts, (pad_x, pad_y))
        self.screen.blit(surf, box.topleft)


    def _draw_city_detail(self, action_card: pygame.Rect) -> None:
        city = self._city_by_id(self._selected_city_id) if self._selected_city_id else None
        if city is None:
            return
        box = pygame.Rect(
            action_card.x + 8,
            action_card.y + 28,
            action_card.width - 16,
            min(self.layout.px(150), action_card.height - 36),
        )
        draw_rounded_rect(self.screen, box, self.theme.list_box, radius=10, border=self.theme.accent)
        yields = self._city_raw_yields(city)
        overlap = self._city_overlap_cells(city)
        draw_text(
            self.screen,
            self.font_small,
            f"城市 #{city.city_id}  ({city.x},{city.y})",
            (box.x + 10, box.y + 8),
            self.theme.accent,
        )
        if city.buildings:
            bnames = "、".join(_label_building(b) for b in sorted(city.buildings, key=lambda x: x.value))
        else:
            bnames = "无建筑"
        draw_text(self.screen, self.font_tiny, f"建筑: {bnames}", (box.x + 10, box.y + 28), self.theme.text)
        draw_text(
            self.screen,
            self.font_tiny,
            f"3×3产出: {_format_yields_static(yields)}  ·  维护 -{CITY_MAINTENANCE_FOOD}粮",
            (box.x + 10, box.y + 46),
            self.theme.text_dim,
        )
        note = f"与{city.city_id}城范围重叠 {len(overlap)} 格（全局去重）" if overlap else "范围无与其他城重叠"
        draw_text(self.screen, self.font_tiny, note, (box.x + 10, box.y + 62), self.theme.text_muted)
        close_rect = pygame.Rect(box.right - self.layout.px(52), box.y + 6, self.layout.px(44), self.layout.px(20))
        draw_button(
            self.screen,
            close_rect,
            "关闭",
            font=self.font_tiny,
            enabled=True,
            hover=close_rect.collidepoint(pygame.mouse.get_pos()),
            palette=self.theme.ui_palette,
        )
        self._city_detail_close_rect = close_rect

    def _draw_settings_menu(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self.theme.overlay, 210))
        self.screen.blit(overlay, (0, 0))
        self._settings_rects = []
        box_w, box_h = self.layout.px(400), self.layout.px(580)
        box = pygame.Rect(
            (self.screen.get_width() - box_w) // 2,
            (self.screen.get_height() - box_h) // 2,
            box_w,
            box_h,
        )
        draw_card(self.screen, box, self.theme.card_bg, self.theme.accent, radius=16, shadow=True)
        draw_text(self.screen, self.font_title, "游戏设置", (box.centerx, box.y + 16), self.theme.accent, center=True)
        y = box.y + 52
        row_h = self.layout.px(34)
        gap = self.layout.px(10)

        draw_text(self.screen, self.font_tiny, "界面大小", (box.x + 20, y + 8), self.theme.text_dim)
        minus = pygame.Rect(box.x + 120, y, self.layout.px(36), row_h)
        plus = pygame.Rect(box.right - 20 - self.layout.px(36), y, self.layout.px(36), row_h)
        mid = pygame.Rect(minus.right + 8, y, plus.x - minus.right - 16, row_h)
        draw_button(self.screen, minus, "-", font=self.font_body, hover=minus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        draw_button(self.screen, plus, "+", font=self.font_body, hover=plus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        draw_rounded_rect(self.screen, mid, self.theme.panel_bg_alt, radius=8, border=self.theme.panel_border_soft)
        draw_text(self.screen, self.font_body, f"{int(self.layout.scale * 100)}%", (mid.centerx, mid.centery - 8), self.theme.text, center=True)
        self._settings_rects.extend([(minus, "scale_down"), (plus, "scale_up")])
        y += row_h + gap

        draw_text(self.screen, self.font_tiny, "操作方式", (box.x + 20, y + 8), self.theme.text_dim)
        human_r = pygame.Rect(box.x + 120, y, self.layout.px(72), row_h)
        auto_r = pygame.Rect(human_r.right + 8, y, self.layout.px(72), row_h)
        draw_button(
            self.screen,
            human_r,
            "手动",
            font=self.font_tiny,
            active=self._settings_play_mode == "human",
            hover=human_r.collidepoint(pygame.mouse.get_pos()),
            palette=self.theme.ui_palette,
        )
        draw_button(
            self.screen,
            auto_r,
            "自动",
            font=self.font_tiny,
            active=self._settings_play_mode != "human",
            hover=auto_r.collidepoint(pygame.mouse.get_pos()),
            palette=self.theme.ui_palette,
        )
        self._settings_rects.extend([(human_r, "play_human"), (auto_r, "play_auto")])
        y += row_h + gap

        if self._settings_play_mode != "human":
            draw_text(self.screen, self.font_tiny, "AI 策略", (box.x + 20, y + 8), self.theme.text_dim)
            chip_w = self.layout.px(64)
            chip_gap = 6
            for mode_id, label in (("random", "随机"), ("greedy", "贪心")):
                ax = box.x + 120 + (chip_w + chip_gap) * (0 if mode_id == "random" else 1)
                r = pygame.Rect(ax, y, chip_w, row_h)
                draw_button(
                    self.screen,
                    r,
                    label,
                    font=self.font_tiny,
                    active=self._settings_play_mode == mode_id,
                    hover=r.collidepoint(pygame.mouse.get_pos()),
                    palette=self.theme.ui_palette,
                )
                self._settings_rects.append((r, f"agent_{mode_id}"))
            y += row_h + self.layout.px(4)
            for mode_id, label in (("planned", "搜索"), ("learned", "模仿")):
                ax = box.x + 120 + (chip_w + chip_gap) * (0 if mode_id == "planned" else 1)
                r = pygame.Rect(ax, y, chip_w, row_h)
                il_ok = LearnedAgent is not None or mode_id != "learned"
                draw_button(
                    self.screen,
                    r,
                    label,
                    font=self.font_tiny,
                    active=self._settings_play_mode == mode_id,
                    enabled=il_ok,
                    hover=r.collidepoint(pygame.mouse.get_pos()),
                    palette=self.theme.ui_palette,
                )
                self._settings_rects.append((r, f"agent_{mode_id}"))
            y += row_h + gap

            draw_text(self.screen, self.font_tiny, "旁观速度", (box.x + 20, y + 8), self.theme.text_dim)
            dminus = pygame.Rect(box.x + 120, y, self.layout.px(36), row_h)
            dplus = pygame.Rect(box.x + 120 + self.layout.px(100), y, self.layout.px(36), row_h)
            dmid = pygame.Rect(dminus.right + 8, y, dplus.x - dminus.right - 16, row_h)
            draw_button(self.screen, dminus, "-", font=self.font_body, hover=dminus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
            draw_button(self.screen, dplus, "+", font=self.font_body, hover=dplus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
            draw_rounded_rect(self.screen, dmid, self.theme.panel_bg_alt, radius=8, border=self.theme.panel_border_soft)
            draw_text(
                self.screen,
                self.font_body,
                f"{self._settings_auto_delay_ms}ms",
                (dmid.centerx, dmid.centery - 8),
                self.theme.text,
                center=True,
            )
            self._settings_rects.extend([(dminus, "delay_down"), (dplus, "delay_up")])
            y += row_h + gap

        draw_text(self.screen, self.font_tiny, "地图边长", (box.x + 20, y + 8), self.theme.text_dim)
        x = box.x + 120
        for size in range(8, 13):
            r = pygame.Rect(x, y, self.layout.px(40), row_h)
            active = size == self._settings_map_size
            draw_rounded_rect(
                self.screen,
                r,
                self.theme.tech_chip_on if active else self.theme.panel_bg_alt,
                radius=8,
                border=self.theme.accent if active else self.theme.panel_border_soft,
            )
            draw_text(self.screen, self.font_small, str(size), (r.centerx, r.centery - 7), self.theme.text if active else self.theme.text_dim, center=True)
            self._settings_rects.append((r, f"map_{size}"))
            x += r.width + 6
        y += row_h + gap

        draw_text(self.screen, self.font_tiny, "总回合数", (box.x + 20, y + 8), self.theme.text_dim)
        tminus = pygame.Rect(box.x + 120, y, self.layout.px(36), row_h)
        tplus = pygame.Rect(box.x + 120 + self.layout.px(100), y, self.layout.px(36), row_h)
        tmid = pygame.Rect(tminus.right + 8, y, tplus.x - tminus.right - 16, row_h)
        draw_button(self.screen, tminus, "-", font=self.font_body, hover=tminus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        draw_button(self.screen, tplus, "+", font=self.font_body, hover=tplus.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        draw_rounded_rect(self.screen, tmid, self.theme.panel_bg_alt, radius=8, border=self.theme.panel_border_soft)
        draw_text(self.screen, self.font_body, str(self._settings_turns), (tmid.centerx, tmid.centery - 8), self.theme.text, center=True)
        self._settings_rects.extend([(tminus, "turns_down"), (tplus, "turns_up")])
        y += row_h + gap

        draw_text(self.screen, self.font_tiny, "地图种子", (box.x + 20, y + 8), self.theme.text_dim)
        rand_r = pygame.Rect(box.x + 120, y, self.layout.px(72), row_h)
        fix_r = pygame.Rect(rand_r.right + 8, y, self.layout.px(72), row_h)
        draw_button(self.screen, rand_r, "随机", font=self.font_tiny, active=self._settings_random_seed, hover=rand_r.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        draw_button(self.screen, fix_r, "固定", font=self.font_tiny, active=not self._settings_random_seed, hover=fix_r.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
        self._settings_rects.extend([(rand_r, "seed_mode_random"), (fix_r, "seed_mode_fixed")])
        if not self._settings_random_seed:
            sm = pygame.Rect(fix_r.right + 12, y, self.layout.px(32), row_h)
            sp = pygame.Rect(sm.right + 6, y, self.layout.px(32), row_h)
            sv = pygame.Rect(sp.right + 6, y, self.layout.px(72), row_h)
            draw_button(self.screen, sm, "-", font=self.font_body, hover=sm.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
            draw_button(self.screen, sp, "+", font=self.font_body, hover=sp.collidepoint(pygame.mouse.get_pos()), palette=self.theme.ui_palette)
            draw_rounded_rect(self.screen, sv, self.theme.panel_bg_alt, radius=8, border=self.theme.panel_border_soft)
            draw_text(self.screen, self.font_small, str(self._settings_seed), (sv.centerx, sv.centery - 7), self.theme.text, center=True)
            self._settings_rects.extend([(sm, "seed_down"), (sp, "seed_up")])
        y += row_h + gap + 8

        start_r = pygame.Rect(0, 0, self.layout.px(140), self.layout.px(38))
        start_r.midright = (box.centerx - 8, box.bottom - 28)
        cancel_r = pygame.Rect(0, 0, self.layout.px(140), self.layout.px(38))
        cancel_r.midleft = (box.centerx + 8, box.bottom - 28)
        mouse = pygame.mouse.get_pos()
        draw_button(self.screen, start_r, "开始新局", font=self.font_body, hover=start_r.collidepoint(mouse), palette=self.theme.ui_palette)
        draw_button(self.screen, cancel_r, "取消", font=self.font_body, hover=cancel_r.collidepoint(mouse), palette=self.theme.ui_palette)
        self._settings_rects.extend([(start_r, "new_game_start"), (cancel_r, "settings_cancel")])

    def _draw_overlay(self) -> None:
        if not self.game_over:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self.theme.overlay, 200))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 420, 320
        box = pygame.Rect(
            (self.screen.get_width() - box_w) // 2,
            (self.screen.get_height() - box_h) // 2,
            box_w,
            box_h,
        )
        draw_card(self.screen, box, self.theme.card_bg, self.theme.accent, radius=16, shadow=True)

        parts = self.state.score_breakdown()
        cities = len(self.state.cities)
        buildings = sum(len(c.buildings) for c in self.state.cities)
        techs = len(self.state.tech_unlocked)
        lines = [
            ("文明征程结束", self.font_display, self.theme.accent),
            (f"最终得分  {self.final_score}", self.font_title, self.theme.text),
            (
                f"城市×20  {parts['cities']}  ·  建筑×5  {parts['buildings']}"
                f"  ·  科技×8  {parts['techs']}  ·  资源  {parts['resources']}",
                self.font_tiny,
                self.theme.text_dim,
            ),
            (f"城市 {cities}  ·  建筑 {buildings}  ·  科技 {techs}", self.font_small, self.theme.text_muted),
        ]
        cy = box.y + 24
        for text, font, color in lines:
            surf = font.render(text, True, color)
            self.screen.blit(surf, surf.get_rect(centerx=box.centerx, top=cy))
            cy += surf.get_height() + 12

        mouse = pygame.mouse.get_pos()
        self._overlay_replay_rect = pygame.Rect(0, 0, 140, 38)
        self._overlay_replay_rect.midright = (box.centerx - 8, box.bottom - 36)
        self._overlay_close_rect = pygame.Rect(0, 0, 140, 38)
        self._overlay_close_rect.midleft = (box.centerx + 8, box.bottom - 36)
        draw_button(
            self.screen,
            self._overlay_replay_rect,
            "新局设置",
            font=self.font_body,
            enabled=True,
            hover=self._overlay_replay_rect.collidepoint(mouse),
            palette=self.theme.ui_palette,
        )
        draw_button(
            self.screen,
            self._overlay_close_rect,
            "关闭",
            font=self.font_body,
            enabled=True,
            hover=self._overlay_close_rect.collidepoint(mouse),
            palette=self.theme.ui_palette,
        )

    def run(self) -> int:
        self._refresh_legal()
        running = True
        while running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and self.human_mode and not self.game_over:
                        if self._legend_open:
                            self._legend_open = False
                            self._legend_scroll = 0
                        elif self.mode in (
                            InteractionMode.SAVE_MENU,
                            InteractionMode.LOAD_MENU,
                            InteractionMode.SETTINGS,
                        ):
                            self.mode = InteractionMode.NORMAL
                        elif self._selected_city_id is not None:
                            self._selected_city_id = None
                        else:
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif not self.human_mode and not self.game_over:
                        if event.key == pygame.K_l:
                            self._legend_open = not self._legend_open
                            self._legend_scroll = 0
                        elif event.key == pygame.K_SPACE:
                            self._paused = not self._paused
                            self._show_toast("已暂停" if self._paused else "继续旁观")
                        elif event.key == pygame.K_LEFTBRACKET:
                            self.auto_delay_ms = min(3000, self.auto_delay_ms + 100)
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                        elif event.key == pygame.K_RIGHTBRACKET:
                            self.auto_delay_ms = max(50, self.auto_delay_ms - 100)
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                    elif self.human_mode and not self.game_over:
                        if event.key == pygame.K_l:
                            self._legend_open = not self._legend_open
                            self._legend_scroll = 0
                            if self._legend_open:
                                self.mode = InteractionMode.NORMAL
                                self._scroll_offset = 0
                        elif event.key == pygame.K_t:
                            self._toggle_theme()
                        elif event.key == pygame.K_F5:
                            self._save_to_slot(0)
                        elif event.key == pygame.K_F9:
                            self._load_from_slot(0)
                        elif self.mode == InteractionMode.SAVE_MENU and event.key in (
                            pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3,
                        ):
                            slot = {pygame.K_0: 0, pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[event.key]
                            self._save_to_slot(slot)
                            self.mode = InteractionMode.NORMAL
                        elif self.mode == InteractionMode.LOAD_MENU and event.key in (
                            pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3,
                        ):
                            slot = {pygame.K_0: 0, pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[event.key]
                            self._load_from_slot(slot)
                            self.mode = InteractionMode.NORMAL
                        elif self.mode == InteractionMode.NORMAL:
                            key_map = {
                                pygame.K_1: "skip",
                                pygame.K_2: "build_city",
                                pygame.K_3: "build",
                                pygame.K_4: "research",
                            }
                            if event.key in key_map:
                                self._handle_button(key_map[event.key])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self._on_click(event.pos)
                    elif event.button == 4:
                        self._on_wheel(1)
                    elif event.button == 5:
                        self._on_wheel(-1)
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_cell = self._cell_at_pos(event.pos)

            if not self.human_mode and not self.game_over and not self._paused:
                self._auto_timer += dt
                if self._auto_timer >= self.auto_delay_ms:
                    self._auto_timer = 0
                    self._agent_step()

            if self._bg_surface is not None:
                self.screen.blit(self._bg_surface, (0, 0))
            else:
                self.screen.fill(self.theme.bg)
            self._particles.update(dt)
            self._draw_header()
            self._draw_map()
            self._particles.draw(self.screen)
            self._draw_hover_tooltip()
            self._draw_turn_banner()
            self._draw_panel()
            self._draw_footer()
            self._draw_toast()
            self._draw_overlay()
            if self.mode == InteractionMode.SETTINGS:
                self._draw_settings_menu()
            elif self.mode in (InteractionMode.SAVE_MENU, InteractionMode.LOAD_MENU):
                self._draw_save_load_menu("save" if self.mode == InteractionMode.SAVE_MENU else "load")
            pygame.display.flip()

        pygame.quit()
        return self.final_score if self.final_score is not None else self.state.score()


def run_pygame_game(
    state: GameState,
    *,
    agent: Optional[object] = None,
    auto_delay_ms: int = 450,
    title: str = "简化文明",
    light_theme: bool = False,
    gui_scale: float = DEFAULT_GUI_SCALE,
    play_mode: Optional[str] = None,
) -> int:
    app = CivGameApp(
        state,
        agent=agent,
        auto_delay_ms=auto_delay_ms,
        title=title,
        light_theme=light_theme,
        gui_scale=gui_scale,
        play_mode=play_mode,
    )
    return app.run()


def main(argv: Optional[Sequence[str]] = None) -> None:
    from main import main as cli_main

    if argv is None:
        argv = sys.argv[1:]
    if "--gui" not in argv and "--play" not in argv:
        argv = ["--gui", "--play", "human", *argv]
    sys.argv = [sys.argv[0], *argv]
    cli_main()


if __name__ == "__main__":
    main()
