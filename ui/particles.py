from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

import pygame

Color = Tuple[int, int, int]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: Color
    size: int


class ParticleSystem:
    def __init__(self) -> None:
        self._particles: List[Particle] = []
        self._rng = random.Random()

    def emit(self, x: float, y: float, color: Color, *, count: int = 10, spread: float = 2.2) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, 6.283)
            speed = self._rng.uniform(0.4, spread)
            life = self._rng.randint(18, 36)
            self._particles.append(
                Particle(
                    x=x + self._rng.uniform(-4, 4),
                    y=y + self._rng.uniform(-4, 4),
                    vx=speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x,
                    vy=speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y - 0.6,
                    life=life,
                    max_life=life,
                    color=color,
                    size=self._rng.randint(2, 4),
                )
            )

    def update(self, dt_ms: int) -> None:
        step = max(1, dt_ms / 16)
        alive: List[Particle] = []
        for p in self._particles:
            p.life -= int(step)
            if p.life <= 0:
                continue
            p.x += p.vx * step
            p.y += p.vy * step
            p.vy += 0.04 * step
            alive.append(p)
        self._particles = alive

    def draw(self, surf: pygame.Surface) -> None:
        for p in self._particles:
            alpha = max(30, int(255 * p.life / p.max_life))
            r = max(1, int(p.size * p.life / p.max_life))
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*p.color, alpha), (r * 2, r * 2), r)
            surf.blit(glow, (int(p.x - r * 2), int(p.y - r * 2)))
