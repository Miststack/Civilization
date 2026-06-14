from __future__ import annotations

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

class GameplayMixin:
    """对局逻辑：动作、智能体、设置、存档。"""

    def _reload_fonts(self) -> None:
        fs = lambda n: max(n, int(round(n * self.layout.scale)))
        self.font_display = load_font(fs(26), bold=True)
        self.font_title = load_font(fs(20), bold=True)
        self.font_body = load_font(fs(16))
        self.font_small = load_font(fs(14))
        self.font_tiny = load_font(fs(13))

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

    def _save_gui_prefs(self) -> None:
        try:
            save_gui_prefs(
                light_theme=self.light_theme,
                gui_scale=self.layout.scale,
                auto_delay_ms=self._settings_auto_delay_ms,
                il_top_k=self._settings_il_top_k,
            )
        except OSError:
            pass

    def _can_undo(self) -> bool:
        return self.human_mode and self._undo_state is not None and not self.game_over

    def _undo_last_turn(self) -> None:
        if not self._can_undo():
            self._show_toast("无可撤销的回合")
            return
        self.state = self._undo_state.clone()
        self._undo_state = None
        self.game_over = False
        self.final_score = None
        self.mode = InteractionMode.NORMAL
        self._selected_city_id = None
        self._scroll_offset = 0
        self._refresh_legal()
        self._show_toast(f"已撤销 · 回到第 {self.state.turn} 回合")

    def _toggle_history(self) -> None:
        self._history_open = not self._history_open
        if self._history_open:
            self._legend_open = False
            self._legend_scroll = 0

    def _is_slow_agent(self) -> bool:
        return isinstance(self.agent, PlannedSearchAgent)

    def _begin_agent_think(self) -> None:
        if self.agent is None or self.game_over or self._thinking:
            return
        self._thinking = True
        self._think_action = None
        self._think_error = None
        self._think_started_at = pygame.time.get_ticks()
        agent = self.agent
        state = self.state

        def worker() -> None:
            try:
                action = agent.choose(state)  # type: ignore[attr-defined]
                self._think_action = action
            except RuntimeError as exc:
                self._think_error = str(exc)

        self._think_thread = threading.Thread(target=worker, daemon=True)
        self._think_thread.start()

    def _poll_agent_think(self) -> None:
        if not self._thinking or self._think_thread is None:
            return
        if self._think_thread.is_alive():
            return
        self._thinking = False
        self._think_thread = None
        if self._think_error:
            self._show_toast(f"自动策略异常: {self._think_error}")
            self._push_message(f"自动策略已暂停: {self._think_error}")
            self._paused = True
            return
        if self._think_action is not None:
            self._apply_action(self._think_action, record_undo=False)

    def _begin_agent_turn(self) -> None:
        if self.agent is None or self.game_over:
            return
        if self._is_slow_agent():
            self._begin_agent_think()
        else:
            self._agent_step()

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

    def _apply_action(self, action: Action, *, record_undo: bool = True) -> None:
        if self.game_over:
            return
        if record_undo and self.human_mode:
            self._undo_state = self.state.clone()
        before_res = dict(self.state.resources)
        before_score = self.state.score()
        turn_no = self.state.turn
        self.state.do_turn(action)
        self._action_history.append((turn_no, action_label(action)))
        if len(self._action_history) > 40:
            self._action_history = self._action_history[-40:]
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
        try:
            self._apply_action(self.agent.choose(self.state), record_undo=False)  # type: ignore[attr-defined]
        except RuntimeError as exc:
            self._show_toast(f"自动策略异常: {exc}")
            self._push_message(f"自动策略已暂停: {exc}")
            self._paused = True






    def _make_agent(self, play_mode: str) -> Optional[object]:
        if play_mode == "human":
            return None
        opts = AgentOptions(
            mode=play_mode,
            map_seed=self._startup_config.seed,
            il_weights=IL_WEIGHTS_PATH,
            il_top_k=self._settings_il_top_k,
        )
        return create_agent(opts)

    def _apply_play_mode(self) -> None:
        try:
            self.agent = self._make_agent(self._settings_play_mode)
        except (ImportError, FileNotFoundError, OSError, RuntimeError) as exc:
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
            label = AUTO_MODE_TITLES.get(self._settings_play_mode, "自动")
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
            if LearnedAgent is not None and isinstance(self.agent, LearnedAgent):
                self._settings_il_top_k = getattr(self.agent, "top_k_rerank", self._settings_il_top_k)

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
        self._save_gui_prefs()

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
        self._history_open = False
        self._undo_state = None
        self._action_history.clear()
        self._thinking = False
        self._think_thread = None
        self._auto_timer = 0
        self._selected_city_id = None
        self._init_display()
        self._atlas = AssetAtlas(self.cell_size, self.theme)
        self._rebuild_theme_assets()
        self._apply_play_mode()
        self._refresh_legal()
        mode_txt = "手动" if self.human_mode else auto_mode_short_label(self._settings_play_mode)
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
            if mode_id in AUTO_MODE_LABELS:
                self._settings_play_mode = mode_id
            return
        if action == "delay_down":
            self._settings_auto_delay_ms = max(50, self._settings_auto_delay_ms - AUTO_DELAY_STEP_MS)
            self._save_gui_prefs()
            return
        if action == "delay_up":
            self._settings_auto_delay_ms = min(3000, self._settings_auto_delay_ms + AUTO_DELAY_STEP_MS)
            self._save_gui_prefs()
            return
        if action == "il_top_k_down":
            self._settings_il_top_k = max(1, self._settings_il_top_k - 1)
            self._save_gui_prefs()
            return
        if action == "il_top_k_up":
            self._settings_il_top_k = min(16, self._settings_il_top_k + 1)
            self._save_gui_prefs()
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
        self._save_gui_prefs()

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
            self._undo_state = None
            self._action_history.clear()
            self._thinking = False
            self._think_thread = None
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
            path = save_path(slot)
            meta = slot_summary(path)
            draw_rounded_rect(self.screen, rect, self.theme.card_bg, radius=12, border=self.theme.panel_border_soft)
            draw_text(self.screen, self.font_body, label, (rect.centerx, rect.y + 16), self.theme.text, center=True)
            if meta:
                draw_text(self.screen, self.font_tiny, f"回合 {meta['turn']}", (rect.centerx, rect.y + 46), self.theme.text_dim, center=True)
                draw_text(self.screen, self.font_tiny, f"地图 {meta['map_size']}×{meta['map_size']}", (rect.centerx, rect.y + 64), self.theme.text_muted, center=True)
            elif path.is_file():
                draw_text(self.screen, self.font_tiny, "损坏", (rect.centerx, rect.y + 54), self.theme.text_muted, center=True)
            else:
                draw_text(self.screen, self.font_tiny, "空", (rect.centerx, rect.y + 54), self.theme.text_muted, center=True)
            mouse = pygame.mouse.get_pos()
            if rect.collidepoint(mouse):
                draw_rounded_rect(self.screen, rect, self.theme.list_item_hover, radius=12, border=self.theme.accent)
            self._slot_rects.append((rect, slot))

