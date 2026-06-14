"""GUI 共享类型与常量。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import pygame

from agents.factory import DEFAULT_IL_WEIGHTS
from engine.models import Action

AUTO_MODE_LABELS: dict[str, str] = {
    "random": "随机",
    "greedy": "贪心",
    "planned": "搜索",
    "learned": "模仿",
}

AUTO_MODE_TITLES: dict[str, str] = {
    "random": "随机策略",
    "greedy": "贪心策略",
    "planned": "计划束搜索",
    "learned": "模仿学习",
}

IL_WEIGHTS_PATH = DEFAULT_IL_WEIGHTS
AUTO_DELAY_STEP_MS = 50


def auto_mode_short_label(play_mode: str) -> str:
    return AUTO_MODE_LABELS.get(play_mode, "自动")


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


