from __future__ import annotations

import random

import pytest

from map import MapGenConfig, MapGenerator, generate_map, format_map
from models import TerrainType


def test_map_gen_config_invalid_size() -> None:
    with pytest.raises(ValueError):
        MapGenConfig(size=7).validate()


def test_map_gen_config_max_retries_non_positive() -> None:
    with pytest.raises(ValueError):
        MapGenConfig(size=10, max_retries=0).validate()


def test_map_generator_produces_square_grid() -> None:
    cfg = MapGenConfig(size=10, seed=12345, max_retries=300)
    grid = MapGenerator(cfg).generate()
    assert len(grid) == 10 and all(len(row) == 10 for row in grid)
    assert all(isinstance(c, TerrainType) for row in grid for c in row)


def test_generate_map_shape() -> None:
    grid = generate_map(8, random.Random(99))
    assert len(grid) == 8 and len(grid[0]) == 8


def test_format_map_contains_legend() -> None:
    cfg = MapGenConfig(size=8, seed=0, max_retries=200)
    grid = MapGenerator(cfg).generate()
    text = format_map(grid, [(1, 2)])
    assert "图例" in text and "00" in text
