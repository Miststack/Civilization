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

class InputMixin:
    """输入：按钮、点击、滚轮。"""

    def _panel_section_top(self) -> int:
        return self._tech_bottom + 14

    def _build_action_buttons(self) -> None:
        skip_a, cities, buildings, techs = self._legal_cache
        x = self.panel_rect.x + self.layout.margin
        w = self.panel_rect.width - self.layout.margin * 2
        h = self.layout.button_height
        gap = self.layout.button_gap
        y = self._panel_section_top()

        if self.mode == InteractionMode.NORMAL and not self.game_over:
            specs: List[Tuple[str, str, bool, bool]] = [
                ("skip", "跳过回合", bool(skip_a), self.mode == InteractionMode.NORMAL),
                ("build_city", f"建城 · {len(cities)}", bool(cities), self.mode == InteractionMode.BUILD_CITY),
                ("build", f"建造 · {len(buildings)}", bool(buildings), self.mode == InteractionMode.BUILDING_LIST),
                ("research", f"研究 · {len(techs)}", bool(techs), self.mode == InteractionMode.RESEARCH_LIST),
            ]
            if self._can_undo():
                specs.append(("undo", "撤销上回合", True, False))
            specs.extend([
                ("save_menu", "存档", True, False),
                ("load_menu", "读档", True, False),
                ("settings_menu", "设置", True, False),
                ("history_toggle", "历史", True, self._history_open),
                ("theme_toggle", "浅色" if not self.light_theme else "深色", True, False),
                ("legend_toggle", "图例", True, self._legend_open),
            ])
        else:
            specs = [
                ("skip", "跳过回合", bool(skip_a), self.mode == InteractionMode.NORMAL),
                ("build_city", f"建城 · {len(cities)}", bool(cities), self.mode == InteractionMode.BUILD_CITY),
                ("build", f"建造 · {len(buildings)}", bool(buildings), self.mode == InteractionMode.BUILDING_LIST),
                ("research", f"研究 · {len(techs)}", bool(techs), self.mode == InteractionMode.RESEARCH_LIST),
            ]
            if self.mode in (InteractionMode.BUILDING_LIST, InteractionMode.RESEARCH_LIST):
                specs.append(("cancel", "取消选择", True, False))

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
        if self._history_open:
            self.buttons.append(
                Button(
                    pygame.Rect(x, quit_y - gap - h, w, h),
                    "关闭历史",
                    "history_toggle",
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
            title, sub = action_list_entry(self.state, action)
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
                self._history_open = False
                self.mode = InteractionMode.NORMAL
                self._scroll_offset = 0
            return
        if action_id == "history_toggle":
            self._toggle_history()
            return
        if action_id == "undo":
            self._undo_last_turn()
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

