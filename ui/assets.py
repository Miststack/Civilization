from __future__ import annotations

import math
import random
from typing import Dict, Tuple

import pygame

from engine.models import BuildingType, TechType, TerrainType
from ui.theme import DARK_THEME, Theme

Color = Tuple[int, int, int]


def _lerp(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


class AssetAtlas:
    """程序化贴图缓存：地形、城市、资源图标。"""

    def __init__(self, cell_size: int, theme: Theme = DARK_THEME) -> None:
        self.cell_size = max(28, cell_size)
        self.theme = theme
        self._rng = random.Random(7)
        self.terrain: Dict[TerrainType, pygame.Surface] = {}
        self.city: pygame.Surface | None = None
        self.city_small: pygame.Surface | None = None
        self.resource_icons: Dict[str, pygame.Surface] = {}
        self.building_icons: Dict[BuildingType, pygame.Surface] = {}
        self.tech_icons: Dict[TechType, pygame.Surface] = {}
        self.pending: pygame.Surface | None = None
        self._build_all()

    def _tile_surface(self) -> pygame.Surface:
        s = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        return s

    def _paint_base(self, surf: pygame.Surface, base: Color, light: Color, dark: Color) -> None:
        w, h = surf.get_size()
        for y in range(h):
            t = y / max(1, h - 1)
            row = _lerp(light, base, t * 0.65)
            pygame.draw.line(surf, row, (0, y), (w, y))
        pygame.draw.rect(surf, dark, surf.get_rect(), width=1, border_radius=6)
        gloss = pygame.Rect(2, 2, w - 4, max(3, h // 4))
        pygame.draw.rect(surf, (*light, 90), gloss, border_radius=4)

    def _speckle(self, surf: pygame.Surface, color: Color, n: int = 8) -> None:
        w, h = surf.get_size()
        for _ in range(n):
            x, y = self._rng.randint(3, w - 4), self._rng.randint(3, h - 4)
            pygame.draw.circle(surf, color, (x, y), 1)

    def _build_terrain(self, terrain: TerrainType) -> pygame.Surface:
        surf = self._tile_surface()
        base = self.theme.terrain_colors[terrain]
        light = self.theme.terrain_light[terrain]
        dark = self.theme.terrain_dark[terrain]
        detail = self.theme.terrain_detail[terrain]
        self._paint_base(surf, base, light, dark)
        cx, cy = self.cell_size // 2, self.cell_size // 2

        if terrain == TerrainType.FOREST:
            for ox, scale in ((-9, 1.0), (0, 1.15), (9, 0.9)):
                x = cx + ox
                trunk_h = self.cell_size // 4
                pygame.draw.rect(surf, dark, (x - 2, cy, 4, trunk_h + 4))
                pts = [(x, cy - self.cell_size // 4), (x - 7, cy + 4), (x + 7, cy + 4)]
                pygame.draw.polygon(surf, detail, pts)
                pygame.draw.polygon(surf, light, [(x, cy - self.cell_size // 4), (x - 3, cy - 2), (x + 2, cy - 6)])
            self._speckle(surf, dark, 6)
        elif terrain == TerrainType.MOUNTAIN:
            for ox, hscale in ((-8, 0.8), (0, 1.0), (8, 0.7)):
                bh = int(self.cell_size * 0.35 * hscale)
                pts = [(cx + ox, cy - bh), (cx + ox - 9, cy + 8), (cx + ox + 9, cy + 8)]
                pygame.draw.polygon(surf, detail, pts)
                pygame.draw.polygon(surf, light, [(cx + ox, cy - bh), (cx + ox - 3, cy - bh // 2), (cx + ox + 2, cy - bh // 2)])
            self._speckle(surf, (200, 210, 220), 5)
        elif terrain == TerrainType.RIVER:
            for i in range(3):
                off = i * 3
                pygame.draw.arc(
                    surf,
                    detail,
                    pygame.Rect(4 + off, 6, self.cell_size - 8 - off, self.cell_size - 10),
                    0.2,
                    math.pi - 0.2,
                    2,
                )
            pygame.draw.arc(surf, light, pygame.Rect(8, 10, self.cell_size - 16, self.cell_size - 18), 0.5, math.pi - 0.5, 1)
        elif terrain == TerrainType.PLAIN:
            for ox, oy in ((-8, 4), (0, -2), (8, 3)):
                pygame.draw.line(surf, detail, (cx + ox, cy + oy + 4), (cx + ox, cy + oy - 6), 2)
                pygame.draw.line(surf, light, (cx + ox - 2, cy + oy - 4), (cx + ox + 2, cy + oy - 6), 1)
            self._speckle(surf, light, 10)
        elif terrain == TerrainType.WASTELAND:
            for ox in range(-10, 12, 5):
                pygame.draw.line(surf, detail, (cx + ox, cy + 6), (cx + ox + 3, cy - 5), 1)
            pygame.draw.ellipse(surf, dark, pygame.Rect(cx - 10, cy + 2, 20, 6))

        return surf.convert_alpha()

    def _build_city(self) -> pygame.Surface:
        s = self._tile_surface()
        cx, cy = self.cell_size // 2, self.cell_size // 2
        # 城墙底座
        pygame.draw.ellipse(s, (40, 28, 12, 80), pygame.Rect(cx - 14, cy + 8, 28, 10))
        body = pygame.Rect(cx - 12, cy - 4, 24, 18)
        pygame.draw.rect(s, (210, 175, 95), body, border_radius=4)
        pygame.draw.rect(s, (120, 80, 35), body, width=2, border_radius=4)
        # 塔楼
        tower = pygame.Rect(cx - 6, cy - 14, 12, 14)
        pygame.draw.rect(s, (230, 195, 110), tower, border_radius=3)
        pygame.draw.rect(s, (120, 80, 35), tower, width=1, border_radius=3)
        pygame.draw.polygon(s, (180, 60, 50), [(cx, cy - 20), (cx - 8, cy - 14), (cx + 8, cy - 14)])
        pygame.draw.circle(s, (255, 255, 255), (cx - 4, cy - 2), 2)
        return s.convert_alpha()

    def _build_pending(self) -> pygame.Surface:
        s = self._tile_surface()
        cx, cy = self.cell_size // 2, self.cell_size // 2
        pygame.draw.rect(s, (90, 70, 40), pygame.Rect(cx - 10, cy - 2, 20, 12), border_radius=2)
        for i in range(3):
            pygame.draw.line(s, (200, 160, 80), (cx - 8 + i * 8, cy - 10), (cx - 8 + i * 8, cy + 2), 2)
        return s.convert_alpha()

    def _build_building_icon(self, building: BuildingType) -> pygame.Surface:
        s = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        cx, cy = self.cell_size // 2, self.cell_size // 2
        pad = max(4, self.cell_size // 8)
        base = pygame.Rect(pad, pad + 2, self.cell_size - pad * 2, self.cell_size - pad * 2 - 4)
        pygame.draw.rect(s, (30, 30, 30, 70), base.inflate(4, 4), border_radius=6)
        if building == BuildingType.FARM:
            pygame.draw.rect(s, (96, 168, 72), base, border_radius=5)
            pygame.draw.rect(s, (58, 110, 42), base, width=1, border_radius=5)
            for ox in (-8, 0, 8):
                pygame.draw.line(s, (210, 230, 120), (cx + ox, cy + 6), (cx + ox, cy - 8), 2)
                pygame.draw.circle(s, (240, 220, 80), (cx + ox, cy - 9), 3)
        elif building == BuildingType.LUMBER_MILL:
            pygame.draw.rect(s, (150, 95, 45), base, border_radius=4)
            pygame.draw.rect(s, (95, 55, 25), base, width=1, border_radius=4)
            pygame.draw.rect(s, (110, 70, 35), pygame.Rect(cx - 10, cy - 2, 20, 8), border_radius=2)
            for i in range(3):
                pygame.draw.circle(s, (180, 120, 60), (cx - 8 + i * 8, cy + 8), 3)
        elif building == BuildingType.MINE:
            pygame.draw.polygon(
                s,
                (120, 125, 135),
                [(cx, cy - 12), (cx - 14, cy + 10), (cx + 14, cy + 10)],
            )
            pygame.draw.polygon(
                s,
                (170, 175, 185),
                [(cx, cy - 12), (cx - 6, cy - 2), (cx + 2, cy - 8)],
            )
            pygame.draw.rect(s, (70, 72, 78), pygame.Rect(cx - 3, cy + 2, 6, 8))
        elif building == BuildingType.LIBRARY:
            pygame.draw.rect(s, (120, 150, 210), base, border_radius=4)
            pygame.draw.rect(s, (60, 90, 150), base, width=1, border_radius=4)
            for i, col in enumerate(((220, 80, 80), (230, 200, 80), (90, 170, 230))):
                pygame.draw.rect(
                    s,
                    col,
                    pygame.Rect(cx - 10 + i * 7, cy - 8, 5, 14),
                    border_radius=1,
                )
        return s.convert_alpha()


    def _build_tech_icon(self, tech: TechType) -> pygame.Surface:
        s = pygame.Surface((28, 28), pygame.SRCALPHA)
        cx, cy = 14, 14
        pygame.draw.circle(s, (40, 40, 40, 60), (cx, cy), 13)
        if tech == TechType.AGRICULTURE:
            pygame.draw.circle(s, (90, 170, 70), (cx, cy + 4), 5)
            pygame.draw.line(s, (120, 200, 90), (cx, cy - 6), (cx, cy + 2), 2)
        elif tech == TechType.LOGGING:
            pygame.draw.rect(s, (120, 75, 35), pygame.Rect(cx - 3, cy - 2, 6, 10), border_radius=1)
            pygame.draw.polygon(s, (60, 140, 70), [(cx, cy - 8), (cx - 7, cy + 2), (cx + 7, cy + 2)])
        elif tech == TechType.MINING:
            pygame.draw.polygon(s, (150, 155, 165), [(cx, cy - 7), (cx - 8, cy + 6), (cx + 8, cy + 6)])
            pygame.draw.rect(s, (90, 92, 100), pygame.Rect(cx - 2, cy + 2, 4, 5))
        elif tech == TechType.EDUCATION:
            pygame.draw.rect(s, (100, 140, 220), pygame.Rect(cx - 6, cy - 7, 12, 14), border_radius=2)
            pygame.draw.line(s, (240, 240, 255), (cx - 3, cy - 3), (cx + 3, cy + 4), 1)
        return s.convert_alpha()

    def _build_resource_icon(self, key: str, color: Color) -> pygame.Surface:
        s = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, 40), (11, 11), 10)
        pygame.draw.circle(s, color, (11, 11), 9, width=1)
        cx, cy = 11, 11
        if key == "food":
            pygame.draw.circle(s, color, (cx, cy + 3), 4)
            pygame.draw.line(s, color, (cx, cy - 5), (cx, cy + 1), 2)
        elif key == "wood":
            pygame.draw.rect(s, color, pygame.Rect(cx - 5, cy - 2, 10, 4), border_radius=2)
            pygame.draw.circle(s, color, (cx - 4, cy - 3), 2)
            pygame.draw.circle(s, color, (cx + 4, cy - 3), 2)
        elif key == "ore":
            pygame.draw.polygon(s, color, [(cx, cy - 5), (cx - 5, cy + 4), (cx + 5, cy + 4)])
        elif key == "science":
            pygame.draw.rect(s, color, pygame.Rect(cx - 4, cy - 5, 8, 10), border_radius=1)
            pygame.draw.line(s, (255, 255, 255), (cx - 2, cy - 2), (cx + 2, cy + 3), 1)
        return s.convert_alpha()

    def _build_all(self) -> None:
        for terrain in TerrainType:
            self.terrain[terrain] = self._build_terrain(terrain)
        self.city = self._build_city()
        self.pending = self._build_pending()
        for key, color in self.theme.resource_colors.items():
            self.resource_icons[key] = self._build_resource_icon(key, color)
        for building in BuildingType:
            self.building_icons[building] = self._build_building_icon(building)
        for tech in TechType:
            self.tech_icons[tech] = self._build_tech_icon(tech)

    def blit_terrain(self, target: pygame.Surface, rect: pygame.Rect, terrain: TerrainType, *, shimmer: float = 0.0) -> None:
        tile = self.terrain[terrain]
        scaled = tile
        if rect.width != self.cell_size:
            scaled = pygame.transform.smoothscale(tile, (rect.width, rect.height))
        target.blit(scaled, rect.topleft)
        if terrain == TerrainType.RIVER and shimmer > 0:
            gloss = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            y = int((shimmer % 1.0) * rect.height)
            pygame.draw.line(gloss, (220, 245, 255, 70), (4, y), (rect.width - 4, y + 3), 2)
            target.blit(gloss, rect.topleft)

    def blit_city(self, target: pygame.Surface, rect: pygame.Rect, city_id: int, font: pygame.font.Font, buildings: int) -> None:
        if self.city is None:
            return
        cx, cy = rect.center
        img = self.city
        if rect.width != self.cell_size:
            img = pygame.transform.smoothscale(self.city, (rect.width, rect.height))
        ir = img.get_rect(center=(cx, cy))
        target.blit(img, ir)
        id_img = font.render(str(city_id), True, (40, 25, 8))
        badge = pygame.Rect(cx - 8, cy + 2, 16, 14)
        pygame.draw.rect(target, (255, 240, 200), badge, border_radius=3)
        target.blit(id_img, id_img.get_rect(center=badge.center))
        if buildings > 0:
            dot_x = cx + rect.width // 4
            pygame.draw.circle(target, (100, 180, 255), (dot_x, cy - rect.height // 4), 5)
            cnt = font.render(str(buildings), True, (255, 255, 255))
            target.blit(cnt, cnt.get_rect(center=(dot_x, cy - rect.height // 4)))


    def blit_tech(self, target: pygame.Surface, rect: pygame.Rect, tech: TechType) -> None:
        icon = self.tech_icons.get(tech)
        if icon is None:
            return
        size = max(16, min(rect.width, rect.height))
        img = icon if size == 28 else pygame.transform.smoothscale(icon, (size, size))
        target.blit(img, img.get_rect(center=rect.center))

    def blit_building(
        self, target: pygame.Surface, rect: pygame.Rect, building: BuildingType
    ) -> None:
        icon = self.building_icons.get(building)
        if icon is None:
            return
        size = max(16, int(rect.width * 0.72))
        img = icon
        if size != self.cell_size:
            img = pygame.transform.smoothscale(icon, (size, size))
        ir = img.get_rect(center=rect.center)
        target.blit(img, ir)

    def blit_pending(self, target: pygame.Surface, rect: pygame.Rect) -> None:
        if self.pending is None:
            return
        img = self.pending
        if rect.width != self.cell_size:
            img = pygame.transform.smoothscale(self.pending, (rect.width, rect.height))
        target.blit(img, rect.topleft)
