from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import pygame

Color = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def lerp_color(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def vertical_gradient(surf: pygame.Surface, top: Color, bottom: Color) -> None:
    h = surf.get_height()
    for y in range(h):
        c = lerp_color(top, bottom, y / max(1, h - 1))
        pygame.draw.line(surf, c, (0, y), (surf.get_width(), y))


def draw_rounded_rect(
    surf: pygame.Surface,
    rect: pygame.Rect,
    color: Color,
    *,
    radius: int = 8,
    border: Color | None = None,
    border_width: int = 1,
) -> None:
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surf, border, rect, width=border_width, border_radius=radius)


def draw_card(
    surf: pygame.Surface,
    rect: pygame.Rect,
    fill: Color,
    border: Color,
    *,
    radius: int = 10,
    shadow: bool = True,
) -> None:
    if shadow:
        sh = rect.move(0, 2)
        draw_rounded_rect(surf, sh, (0, 0, 0), radius=radius)
    draw_rounded_rect(surf, rect, fill, radius=radius, border=border)


def draw_text(
    surf: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[int, int],
    color: Color,
    *,
    center: bool = False,
) -> pygame.Rect:
    img = font.render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    rect.x = int(rect.x)
    rect.y = int(rect.y)
    surf.blit(img, rect)
    return rect


def draw_progress_bar(
    surf: pygame.Surface,
    rect: pygame.Rect,
    ratio: float,
    *,
    bg: Color,
    fill: Color,
    border: Color,
    radius: int = 6,
) -> None:
    ratio = max(0.0, min(1.0, ratio))
    draw_rounded_rect(surf, rect, bg, radius=radius, border=border)
    if ratio <= 0:
        return
    inner = rect.inflate(-4, -4)
    fill_w = max(4, int(inner.width * ratio))
    fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
    draw_rounded_rect(surf, fill_rect, fill, radius=max(3, radius - 2))


def draw_resource_row(
    surf: pygame.Surface,
    rect: pygame.Rect,
    *,
    icon: str,
    label: str,
    value: int,
    per_turn: int,
    color: Color,
    font_label: pygame.font.Font,
    font_value: pygame.font.Font,
    bg: Color,
    border: Color,
    icon_surface: pygame.Surface | None = None,
    value_color: Color | None = None,
    per_turn_note: str = "",
) -> None:
    draw_rounded_rect(surf, rect, bg, radius=8, border=border)
    if icon_surface is not None:
        ir = icon_surface.get_rect(center=(rect.x + 18, rect.centery))
        surf.blit(icon_surface, ir)
    else:
        icon_surf = font_value.render(icon, True, color)
        surf.blit(icon_surf, (rect.x + 10, rect.centery - icon_surf.get_height() // 2))
    label_img = font_label.render(label, True, color)
    surf.blit(label_img, (rect.x + 38, rect.centery - label_img.get_height() // 2))
    right_text = f"{value}   +{per_turn}/回合"
    if per_turn_note:
        right_text += f"  {per_turn_note}"
    right_img = font_value.render(right_text, True, value_color or color)
    surf.blit(right_img, right_img.get_rect(midright=(rect.right - 10, rect.centery)))


def draw_button(
    surf: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    *,
    font: pygame.font.Font,
    icon: str = "",
    enabled: bool = True,
    active: bool = False,
    hover: bool = False,
    palette: dict[str, Color],
) -> None:
    if not enabled:
        bg = palette["btn_disabled"]
        fg = palette["text_dim"]
        accent = palette["border"]
    elif active:
        bg = palette["btn_active"]
        fg = palette["text"]
        accent = palette["accent"]
    elif hover:
        bg = palette["btn_hover"]
        fg = palette["text"]
        accent = palette["accent_soft"]
    else:
        bg = palette["btn"]
        fg = palette["text"]
        accent = palette["border"]

    draw_rounded_rect(surf, rect, bg, radius=8, border=accent)
    if active:
        stripe = pygame.Rect(rect.x + 2, rect.y + 6, 4, rect.height - 12)
        draw_rounded_rect(surf, stripe, palette["accent"], radius=2)

    tx = rect.x + 14
    if icon:
        icon_img = font.render(icon, True, fg)
        surf.blit(icon_img, (tx, rect.centery - icon_img.get_height() // 2))
        tx += icon_img.get_width() + 8
    text_img = font.render(label, True, fg)
    surf.blit(text_img, (tx, rect.centery - text_img.get_height() // 2))


def draw_terrain_tile(
    surf: pygame.Surface,
    rect: pygame.Rect,
    terrain_key: str,
    base: Color,
    light: Color,
    dark: Color,
    detail: Color,
) -> None:
    draw_rounded_rect(surf, rect, base, radius=6, border=dark)
    inner = rect.inflate(-6, -6)
    highlight = pygame.Rect(inner.x, inner.y, inner.width, max(3, inner.height // 3))
    draw_rounded_rect(surf, highlight, light, radius=4)

    cx, cy = rect.center
    if terrain_key == "forest":
        for ox, oy in ((-5, 2), (0, -2), (5, 2)):
            pygame.draw.circle(surf, detail, (cx + ox, cy + oy), 3)
            pygame.draw.rect(surf, dark, (cx + ox - 1, cy + oy, 2, 5))
    elif terrain_key == "mountain":
        pts = [(cx, cy - 7), (cx - 8, cy + 6), (cx + 8, cy + 6)]
        pygame.draw.polygon(surf, detail, pts)
        pygame.draw.polygon(surf, light, [(cx, cy - 7), (cx - 3, cy - 1), (cx + 2, cy - 4)])
    elif terrain_key == "river":
        for i in range(-2, 3):
            pygame.draw.arc(surf, detail, rect.inflate(-8 + i, -10), 0, 3.14, 2)
    elif terrain_key == "plain":
        for ox, oy in ((-4, 3), (4, -2)):
            pygame.draw.line(surf, detail, (cx + ox, cy + oy), (cx + ox, cy + oy - 5), 2)
    elif terrain_key == "wasteland":
        for ox in range(-6, 8, 4):
            pygame.draw.line(surf, detail, (cx + ox, cy + 4), (cx + ox + 2, cy - 3), 1)


def draw_city_marker(
    surf: pygame.Surface,
    rect: pygame.Rect,
    city_id: int,
    building_count: int,
    *,
    font_id: pygame.font.Font,
    font_tiny: pygame.font.Font,
) -> None:
    cx, cy = rect.center
    r = max(10, rect.width // 4 + 2)
    glow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 200, 80, 28), (r * 3 // 2, r * 3 // 2), r + 2)
    surf.blit(glow, (int(cx - r * 1.5), int(cy - r * 1.5)))
    pygame.draw.circle(surf, (255, 220, 120), (cx, cy), r)
    pygame.draw.circle(surf, (160, 100, 30), (cx, cy), r, width=2)
    pygame.draw.circle(surf, (255, 255, 255), (cx - 3, cy - 3), max(2, r // 4))
    id_img = font_id.render(str(city_id), True, (55, 35, 10))
    surf.blit(id_img, id_img.get_rect(center=(cx, cy)))
    if building_count > 0:
        badge = font_tiny.render(str(building_count), True, (255, 255, 255))
        badge_rect = badge.get_rect(center=(cx + r - 2, cy - r + 2))
        pygame.draw.circle(surf, (92, 120, 220), badge_rect.center, 8)
        surf.blit(badge, badge_rect)


def draw_tech_chips(
    surf: pygame.Surface,
    origin: Tuple[int, int],
    width: int,
    techs: Iterable[str],
    *,
    font: pygame.font.Font,
    unlocked: set[str],
    chip_bg: Color,
    chip_on: Color,
    text: Color,
    text_dim: Color,
    border: Color,
) -> int:
    x, y = origin
    gap = 6
    chip_h = 24
    for tech in techs:
        on = tech in unlocked
        label = font.render(tech, True, text if on else text_dim)
        chip_w = label.get_width() + 16
        if x + chip_w > origin[0] + width:
            x = origin[0]
            y += chip_h + gap
        rect = pygame.Rect(x, y, chip_w, chip_h)
        draw_rounded_rect(surf, rect, chip_on if on else chip_bg, radius=12, border=border)
        surf.blit(label, label.get_rect(center=rect.center))
        x += chip_w + gap
    return y + chip_h
