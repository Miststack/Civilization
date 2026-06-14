from __future__ import annotations

import csv
from pathlib import Path

import pytest

from il.hard_seeds import load_seed_gaps, select_hard_seeds


def test_select_hard_seeds_by_gap(tmp_path: Path) -> None:
    csv_path = tmp_path / "scores.csv"
    csv_path.write_text(
        "seed,random_score,greedy_score,planned_score,learned_score\n"
        "0,1,1,700,680\n"
        "1,1,1,600,590\n"
        "2,1,1,650,640\n"
        "3,1,1,720,710\n"
        "4,1,1,500,500\n"
        "5,1,1,600,550\n",
        encoding="utf-8",
    )
    gaps = load_seed_gaps(csv_path)
    assert len(gaps) == 5  # seed 4 excluded（持平）
    hard = select_hard_seeds(csv_path, min_gap=15, top_n=10)
    assert hard == [5, 0]


def test_select_hard_seeds_respects_top_n(tmp_path: Path) -> None:
    csv_path = tmp_path / "scores.csv"
    rows = ["seed,random_score,greedy_score,planned_score,learned_score\n"]
    for seed in range(10):
        rows.append(f"{seed},1,1,{700},{650 - seed}\n")
    csv_path.write_text("".join(rows), encoding="utf-8")
    hard = select_hard_seeds(csv_path, min_gap=1, top_n=3)
    assert len(hard) == 3
    assert hard[0] == 9  # gap=59


def test_select_hard_seeds_missing_csv() -> None:
    with pytest.raises(FileNotFoundError):
        select_hard_seeds("nonexistent.csv")
