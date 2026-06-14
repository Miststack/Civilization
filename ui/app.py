"""Pygame 图形界面主应用。"""
from __future__ import annotations

import threading
from typing import List, Optional, Tuple

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
from ui.prefs import DEFAULT_AUTO_DELAY_MS, DEFAULT_IL_TOP_K
from ui.theme import DEFAULT_GUI_SCALE, Layout, theme_by_name


class CivGameApp(LoopMixin, DrawMixin, InputMixin, GameplayMixin):
    """Pygame 图形界面：人机对局或旁观自动智能体。"""

    def __init__(
        self,
        state: GameState,
        *,
        agent: Optional[object] = None,
        auto_delay_ms: int = DEFAULT_AUTO_DELAY_MS,
        title: str = "简化文明",
        light_theme: bool = False,
        gui_scale: float = DEFAULT_GUI_SCALE,
        play_mode: Optional[str] = None,
        il_top_k: int = DEFAULT_IL_TOP_K,
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
        self._history_open = False
        self._action_history: list[tuple[int, str]] = []
        self._undo_state: Optional[GameState] = None
        self._thinking = False
        self._think_thread: Optional[threading.Thread] = None
        self._think_action: Optional[Action] = None
        self._think_error: Optional[str] = None
        self._think_started_at = 0
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
        self._settings_auto_delay_ms = max(50, auto_delay_ms) if auto_delay_ms > 0 else DEFAULT_AUTO_DELAY_MS
        self._settings_il_top_k = max(1, min(16, il_top_k))

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
        self.agent = agent
        self._apply_play_mode()

