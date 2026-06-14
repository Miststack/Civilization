from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.game import GameConfig, GameState
from engine.models import BuildingType, City, TechType, TerrainType, empty_resources

SAVE_VERSION = 1
DEFAULT_SAVE_DIR = Path("saves")


def _enum_list(items) -> List[str]:
    return sorted(item.value for item in items)


def state_to_dict(state: GameState) -> Dict[str, Any]:
    return {
        "version": SAVE_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "map_size": state.config.map_size,
            "total_turns": state.config.total_turns,
            "seed": state.config.seed,
        },
        "turn": state.turn,
        "score": state.score(),
        "resources": dict(state.resources),
        "tech_unlocked": _enum_list(state.tech_unlocked),
        "grid": [[cell.value for cell in row] for row in state.grid],
        "cities": [
            {
                "city_id": city.city_id,
                "x": city.x,
                "y": city.y,
                "buildings": _enum_list(city.buildings),
            }
            for city in state.cities
        ],
        "pending_city_projects": [list(item) for item in state.pending_city_projects],
        "next_city_id": state._next_city_id,
    }


def state_from_dict(data: Dict[str, Any]) -> GameState:
    version = int(data.get("version", 0))
    if version != SAVE_VERSION:
        raise ValueError(f"不支持的存档版本: {version}")

    cfg_raw = data["config"]
    config = GameConfig(
        map_size=int(cfg_raw["map_size"]),
        total_turns=int(cfg_raw["total_turns"]),
        seed=cfg_raw.get("seed"),
    )
    config.validate()

    state = GameState.__new__(GameState)
    state.config = config
    state.rng = __import__("random").Random(config.seed)
    state.turn = int(data["turn"])
    state.resources = empty_resources()
    state.resources.update({k: int(v) for k, v in data["resources"].items()})
    state.tech_unlocked = {TechType(v) for v in data.get("tech_unlocked", [])}
    state.grid = [
        [TerrainType(cell) for cell in row]
        for row in data["grid"]
    ]
    state.cities = []
    for raw_city in data.get("cities", []):
        buildings = {BuildingType(b) for b in raw_city.get("buildings", [])}
        state.cities.append(
            City(
                city_id=int(raw_city["city_id"]),
                x=int(raw_city["x"]),
                y=int(raw_city["y"]),
                buildings=buildings,
            )
        )
    state.pending_city_projects = [
        (int(x), int(y), int(remain))
        for x, y, remain in data.get("pending_city_projects", [])
    ]
    state._next_city_id = int(data.get("next_city_id", len(state.cities) + 1))
    return state


def save_path(slot: int = 0, save_dir: Path | str = DEFAULT_SAVE_DIR) -> Path:
    root = Path(save_dir)
    root.mkdir(parents=True, exist_ok=True)
    if slot == 0:
        return root / "quicksave.json"
    if 1 <= slot <= 3:
        return root / f"slot{slot}.json"
    raise ValueError("slot 须为 0(快速) 或 1~3")


def save_game(state: GameState, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = state_to_dict(state)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_game(path: Path | str) -> GameState:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"存档不存在: {target}")
    data = json.loads(target.read_text(encoding="utf-8"))
    return state_from_dict(data)


def slot_summary(path: Path | str) -> Optional[Dict[str, Any]]:
    target = Path(path)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    try:
        cities = data.get("cities", [])
        resources = data.get("resources", {})
        techs = data.get("tech_unlocked", [])
        buildings = sum(len(c.get("buildings", [])) for c in cities)
        if "score" in data:
            score = int(data["score"])
        else:
            res_sum = sum(int(resources.get(k, 0)) for k in ("food", "wood", "ore", "science"))
            score = 20 * len(cities) + 5 * buildings + 8 * len(techs) + res_sum // 4
        return {
            "turn": int(data.get("turn", 1)),
            "score": score,
            "cities": len(cities),
            "buildings": buildings,
            "map_size": int(data["config"]["map_size"]),
            "saved_at": data.get("saved_at", ""),
        }
    except (KeyError, TypeError, ValueError):
        return None
