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

class LoopMixin:
    """主循环与事件分发。"""

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
                        elif event.key == pygame.K_SPACE or event.key == pygame.K_p:
                            self._paused = not self._paused
                            self._show_toast("已暂停" if self._paused else "继续旁观")
                        elif event.key == pygame.K_n and (self._paused or self._thinking):
                            if not self._thinking:
                                self._begin_agent_turn()
                        elif event.key in (pygame.K_LEFTBRACKET,):
                            self.auto_delay_ms = min(3000, self.auto_delay_ms + AUTO_DELAY_STEP_MS)
                            self._settings_auto_delay_ms = self.auto_delay_ms
                            self._save_gui_prefs()
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                        elif event.key in (pygame.K_RIGHTBRACKET,):
                            self.auto_delay_ms = max(50, self.auto_delay_ms - AUTO_DELAY_STEP_MS)
                            self._settings_auto_delay_ms = self.auto_delay_ms
                            self._save_gui_prefs()
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                            self.auto_delay_ms = max(50, self.auto_delay_ms - AUTO_DELAY_STEP_MS)
                            self._settings_auto_delay_ms = self.auto_delay_ms
                            self._save_gui_prefs()
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                            self.auto_delay_ms = min(3000, self.auto_delay_ms + AUTO_DELAY_STEP_MS)
                            self._settings_auto_delay_ms = self.auto_delay_ms
                            self._save_gui_prefs()
                            self._show_toast(f"速度 {self.auto_delay_ms}ms/回合")
                    elif self.human_mode and not self.game_over:
                        if event.key == pygame.K_l:
                            self._legend_open = not self._legend_open
                            self._legend_scroll = 0
                            if self._legend_open:
                                self._history_open = False
                                self.mode = InteractionMode.NORMAL
                                self._scroll_offset = 0
                        elif event.key == pygame.K_h:
                            self._toggle_history()
                            self.mode = InteractionMode.NORMAL
                            self._scroll_offset = 0
                        elif event.key == pygame.K_z:
                            self._undo_last_turn()
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

            if not self.human_mode and not self.game_over:
                if self._thinking:
                    self._poll_agent_think()
                elif not self._paused:
                    self._auto_timer += dt
                    if self._auto_timer >= self.auto_delay_ms:
                        self._auto_timer = 0
                        self._begin_agent_turn()

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
            if self._thinking:
                self._draw_thinking_overlay()
            self._draw_overlay()
            if self.mode == InteractionMode.SETTINGS:
                self._draw_settings_menu()
            elif self.mode in (InteractionMode.SAVE_MENU, InteractionMode.LOAD_MENU):
                self._draw_save_load_menu("save" if self.mode == InteractionMode.SAVE_MENU else "load")
            pygame.display.flip()

        self._save_gui_prefs()
        pygame.quit()
        return self.final_score if self.final_score is not None else self.state.score()


