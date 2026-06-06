from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from engine.models import TerrainType

Color = Tuple[int, int, int]

# 布局（与主题无关）
DEFAULT_GUI_SCALE = 1.0

PANEL_WIDTH = 336
HEADER_HEIGHT = 52
FOOTER_HEIGHT = 108
MARGIN = 14
CELL_GAP = 2


@dataclass(frozen=True)
class Layout:
    """界面缩放：地图格、侧栏、字号等按同一比例放大。"""

    scale: float = DEFAULT_GUI_SCALE

    def px(self, value: float) -> int:
        return max(1, int(round(value * self.scale)))

    @property
    def panel_width(self) -> int:
        return self.px(PANEL_WIDTH)

    @property
    def header_height(self) -> int:
        return self.px(HEADER_HEIGHT)

    @property
    def footer_height(self) -> int:
        return self.px(FOOTER_HEIGHT)

    @property
    def margin(self) -> int:
        return self.px(MARGIN)

    @property
    def cell_gap(self) -> int:
        return max(2, self.px(CELL_GAP))

    @property
    def panel_min_height(self) -> int:
        return self.px(720)

    @property
    def status_card_top(self) -> int:
        return self.px(56)

    @property
    def status_card_height(self) -> int:
        return self.px(76)

    @property
    def resources_top(self) -> int:
        return self.px(142)

    @property
    def resource_row_height(self) -> int:
        return self.px(34)

    @property
    def resource_row_gap(self) -> int:
        return self.px(5)

    @property
    def tech_box_height(self) -> int:
        return self.px(56)

    @property
    def button_height(self) -> int:
        return self.px(38)

    @property
    def button_gap(self) -> int:
        return self.px(8)

    @property
    def list_item_height(self) -> int:
        return self.px(40)

    @property
    def list_item_gap(self) -> int:
        return self.px(4)

    @property
    def list_panel_offset(self) -> int:
        return self.px(220)

    @property
    def list_panel_inner_offset(self) -> int:
        return self.px(208)

    def cell_size_for(self, map_size: int) -> int:
        budget = self.px(720)
        return max(self.px(34), min(self.px(68), budget // max(1, map_size)))


@dataclass(frozen=True)
class Theme:
    name: str
    bg_top: Color
    bg_bottom: Color
    bg: Color
    panel_bg: Color
    panel_bg_alt: Color
    panel_border: Color
    panel_border_soft: Color
    text: Color
    text_dim: Color
    text_muted: Color
    accent: Color
    accent_soft: Color
    accent_blue: Color
    success: Color
    warning: Color
    danger: Color
    button_bg: Color
    button_hover: Color
    button_active: Color
    button_disabled: Color
    card_bg: Color
    card_border: Color
    map_frame: Color
    map_grid: Color
    map_inner: Color
    action_card: Color
    list_box: Color
    list_item: Color
    list_item_hover: Color
    tech_chip_on: Color
    footer_bg: Color
    toast_bg: Color
    overlay: Color
    header_bg: Color
    terrain_colors: Dict[TerrainType, Color] = field(repr=False)
    terrain_light: Dict[TerrainType, Color] = field(repr=False)
    terrain_dark: Dict[TerrainType, Color] = field(repr=False)
    terrain_detail: Dict[TerrainType, Color] = field(repr=False)
    resource_colors: Dict[str, Color] = field(repr=False)

    @property
    def ui_palette(self) -> dict[str, Color]:
        return {
            "btn": self.button_bg,
            "btn_hover": self.button_hover,
            "btn_active": self.button_active,
            "btn_disabled": self.button_disabled,
            "text": self.text,
            "text_dim": self.text_dim,
            "border": self.panel_border_soft,
            "accent": self.accent,
            "accent_soft": self.accent_soft,
        }


DARK_THEME = Theme(
    name="dark",
    bg_top=(16, 22, 34),
    bg_bottom=(10, 14, 24),
    bg=(14, 18, 28),
    panel_bg=(24, 30, 44),
    panel_bg_alt=(20, 26, 38),
    panel_border=(56, 68, 92),
    panel_border_soft=(42, 52, 72),
    text=(244, 247, 252),
    text_dim=(148, 158, 178),
    text_muted=(108, 118, 138),
    accent=(218, 175, 72),
    accent_soft=(255, 214, 120),
    accent_blue=(92, 156, 230),
    success=(72, 196, 138),
    warning=(245, 180, 70),
    danger=(232, 98, 98),
    button_bg=(36, 44, 60),
    button_hover=(48, 58, 78),
    button_active=(54, 74, 108),
    button_disabled=(30, 34, 44),
    card_bg=(28, 34, 48),
    card_border=(50, 60, 82),
    map_frame=(18, 24, 36),
    map_grid=(34, 42, 58),
    map_inner=(12, 16, 24),
    action_card=(22, 28, 40),
    list_box=(16, 20, 30),
    list_item=(28, 34, 48),
    list_item_hover=(40, 52, 72),
    tech_chip_on=(54, 88, 130),
    footer_bg=(14, 18, 28),
    toast_bg=(28, 36, 52),
    overlay=(6, 10, 18),
    header_bg=(18, 24, 36),
    terrain_colors={
        TerrainType.PLAIN: (98, 168, 88),
        TerrainType.FOREST: (38, 118, 72),
        TerrainType.MOUNTAIN: (130, 138, 150),
        TerrainType.RIVER: (58, 142, 210),
        TerrainType.WASTELAND: (168, 138, 98),
    },
    terrain_light={
        TerrainType.PLAIN: (140, 210, 120),
        TerrainType.FOREST: (72, 160, 100),
        TerrainType.MOUNTAIN: (180, 188, 198),
        TerrainType.RIVER: (110, 188, 240),
        TerrainType.WASTELAND: (200, 172, 128),
    },
    terrain_dark={
        TerrainType.PLAIN: (62, 110, 58),
        TerrainType.FOREST: (22, 72, 48),
        TerrainType.MOUNTAIN: (82, 88, 98),
        TerrainType.RIVER: (32, 88, 140),
        TerrainType.WASTELAND: (110, 88, 62),
    },
    terrain_detail={
        TerrainType.PLAIN: (220, 240, 170),
        TerrainType.FOREST: (180, 230, 150),
        TerrainType.MOUNTAIN: (230, 235, 245),
        TerrainType.RIVER: (200, 235, 255),
        TerrainType.WASTELAND: (220, 200, 160),
    },
    resource_colors={
        "food": (255, 188, 84),
        "wood": (130, 188, 78),
        "ore": (170, 178, 188),
        "science": (110, 178, 245),
    },
)

LIGHT_THEME = Theme(
    name="light",
    bg_top=(248, 246, 242),
    bg_bottom=(232, 228, 220),
    bg=(240, 237, 230),
    panel_bg=(255, 253, 248),
    panel_bg_alt=(245, 241, 234),
    panel_border=(190, 180, 168),
    panel_border_soft=(210, 202, 192),
    text=(38, 44, 54),
    text_dim=(98, 106, 118),
    text_muted=(130, 138, 150),
    accent=(168, 118, 32),
    accent_soft=(210, 165, 60),
    accent_blue=(52, 118, 198),
    success=(42, 150, 98),
    warning=(210, 140, 40),
    danger=(200, 72, 72),
    button_bg=(235, 230, 222),
    button_hover=(220, 214, 204),
    button_active=(200, 220, 245),
    button_disabled=(225, 222, 216),
    card_bg=(252, 250, 245),
    card_border=(200, 192, 180),
    map_frame=(220, 214, 204),
    map_grid=(190, 184, 174),
    map_inner=(228, 224, 216),
    action_card=(245, 241, 234),
    list_box=(238, 234, 226),
    list_item=(250, 247, 240),
    list_item_hover=(230, 238, 252),
    tech_chip_on=(140, 185, 235),
    footer_bg=(245, 242, 236),
    toast_bg=(255, 252, 245),
    overlay=(240, 237, 230),
    header_bg=(252, 250, 245),
    terrain_colors={
        TerrainType.PLAIN: (152, 205, 130),
        TerrainType.FOREST: (72, 145, 95),
        TerrainType.MOUNTAIN: (175, 180, 188),
        TerrainType.RIVER: (100, 165, 225),
        TerrainType.WASTELAND: (195, 168, 128),
    },
    terrain_light={
        TerrainType.PLAIN: (195, 230, 170),
        TerrainType.FOREST: (120, 190, 140),
        TerrainType.MOUNTAIN: (215, 220, 228),
        TerrainType.RIVER: (150, 205, 245),
        TerrainType.WASTELAND: (225, 200, 165),
    },
    terrain_dark={
        TerrainType.PLAIN: (100, 150, 85),
        TerrainType.FOREST: (45, 100, 65),
        TerrainType.MOUNTAIN: (130, 135, 145),
        TerrainType.RIVER: (60, 115, 175),
        TerrainType.WASTELAND: (150, 125, 90),
    },
    terrain_detail={
        TerrainType.PLAIN: (240, 255, 210),
        TerrainType.FOREST: (200, 240, 175),
        TerrainType.MOUNTAIN: (245, 248, 252),
        TerrainType.RIVER: (220, 245, 255),
        TerrainType.WASTELAND: (235, 215, 180),
    },
    resource_colors={
        "food": (220, 140, 40),
        "wood": (90, 150, 55),
        "ore": (120, 128, 138),
        "science": (50, 120, 200),
    },
)


def theme_by_name(light: bool) -> Theme:
    return LIGHT_THEME if light else DARK_THEME


# 兼容旧引用（默认深色）
_active = DARK_THEME
BG_TOP = _active.bg_top
BG_BOTTOM = _active.bg_bottom
BG = _active.bg
PANEL_BG = _active.panel_bg
PANEL_BG_ALT = _active.panel_bg_alt
PANEL_BORDER = _active.panel_border
PANEL_BORDER_SOFT = _active.panel_border_soft
TEXT = _active.text
TEXT_DIM = _active.text_dim
TEXT_MUTED = _active.text_muted
ACCENT = _active.accent
ACCENT_SOFT = _active.accent_soft
ACCENT_BLUE = _active.accent_blue
SUCCESS = _active.success
WARNING = _active.warning
DANGER = _active.danger
BUTTON_BG = _active.button_bg
BUTTON_HOVER = _active.button_hover
BUTTON_ACTIVE = _active.button_active
BUTTON_DISABLED = _active.button_disabled
CARD_BG = _active.card_bg
CARD_BORDER = _active.card_border
MAP_FRAME = _active.map_frame
MAP_GRID = _active.map_grid
UI_PALETTE = _active.ui_palette
TERRAIN_COLORS = _active.terrain_colors
TERRAIN_LIGHT = _active.terrain_light
TERRAIN_DARK = _active.terrain_dark
TERRAIN_DETAIL = _active.terrain_detail
RESOURCE_COLORS = _active.resource_colors

TERRAIN_LABELS: dict[TerrainType, str] = {
    TerrainType.PLAIN: "平原",
    TerrainType.FOREST: "森林",
    TerrainType.MOUNTAIN: "山地",
    TerrainType.RIVER: "河流",
    TerrainType.WASTELAND: "荒地",
}

RESOURCE_ICONS: dict[str, str] = {
    "food": "粮",
    "wood": "木",
    "ore": "矿",
    "science": "科",
}

RESOURCE_LABELS: dict[str, str] = {
    "food": "粮食",
    "wood": "木材",
    "ore": "矿石",
    "science": "科技",
}

BUILDING_LABELS: dict[str, str] = {
    "farm": "农场",
    "lumber_mill": "伐木场",
    "mine": "矿场",
    "library": "图书馆",
}

TECH_LABELS: dict[str, str] = {
    "agriculture": "农业",
    "logging": "伐木",
    "mining": "采矿",
    "education": "教育",
}

BUTTON_ICONS: dict[str, str] = {
    "skip": "⏭",
    "build_city": "🏙",
    "build": "🔨",
    "research": "📜",
    "cancel": "↩",
    "quit": "✕",
    "save_menu": "💾",
    "load_menu": "📂",
    "theme": "☀",
    "theme_toggle": "☀",
    "settings_menu": "⚙",
    "help_menu": "?",
    "confirm_place": "✓",
}
