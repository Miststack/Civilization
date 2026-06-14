"""从 seed_scores.csv 筛选 learned 落后 planned 的困难 seed。"""
from __future__ import annotations

import csv
from pathlib import Path


def load_seed_gaps(csv_path: Path | str) -> list[tuple[int, int, int, int]]:
    """
    返回 [(seed, planned, learned, gap), ...]，gap = planned - learned。
    仅含 planned/learned 均有值且 learned < planned 的行。
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"未找到 CSV: {path}")

    rows: list[tuple[int, int, int, int]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            planned_raw = (row.get("planned_score") or "").strip()
            learned_raw = (row.get("learned_score") or "").strip()
            if not planned_raw or not learned_raw:
                continue
            planned = int(planned_raw)
            learned = int(learned_raw)
            if learned >= planned:
                continue
            seed = int(row["seed"])
            rows.append((seed, planned, learned, planned - learned))
    return rows


def select_hard_seeds(
    csv_path: Path | str,
    *,
    min_gap: int = 15,
    top_n: int = 50,
) -> list[int]:
    """
    按 gap 降序取困难 seed，至少落后 min_gap 分，最多 top_n 个。
    """
    if min_gap < 0:
        raise ValueError("min_gap 须 >= 0")
    if top_n < 1:
        raise ValueError("top_n 须 >= 1")

    gaps = load_seed_gaps(csv_path)
    gaps.sort(key=lambda item: item[3], reverse=True)

    selected: list[int] = []
    for seed, _planned, _learned, gap in gaps:
        if gap < min_gap:
            break
        selected.append(seed)
        if len(selected) >= top_n:
            break
    return selected


def format_seed_summary(csv_path: Path | str, seeds: list[int]) -> str:
    by_seed = {item[0]: item for item in load_seed_gaps(csv_path)}
    lines = []
    for seed in seeds:
        if seed not in by_seed:
            continue
        _seed, planned, learned, gap = by_seed[seed]
        lines.append(f"  seed={seed} planned={planned} learned={learned} gap={gap}")
    return "\n".join(lines)
