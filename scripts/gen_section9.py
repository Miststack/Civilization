"""从 seed_scores.csv 生成课程设计报告 §9 表格。"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "docs" / "experiments" / "seed_scores.csv"
OUT = ROOT / "scripts" / "_section9_fragment.md"


def fmt_delta(d: int) -> str:
    return f"+{d}" if d >= 0 else str(d)


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    lines = [
        "## 9. 附录：`docs/experiments/seed_scores.csv` 逐 seed 得分全表",
        "",
        "下列表格与项目根目录 **`docs/experiments/seed_scores.csv`** 一致（`utf-8-sig`）。"
        "**P-R** = Planned−Random，**P-G** = Planned−Greedy，**L-P** = Learned−Planned（正表示 Learned 更高）。",
        "",
        "| seed | Random | Greedy | Planned | Learned | P-R | P-G | L-P |",
        "|-----:|-------:|-------:|--------:|--------:|----:|----:|----:|",
    ]
    for row in rows:
        seed = int(row["seed"])
        rn = int(row["random_score"])
        g = int(row["greedy_score"])
        p = int(row["planned_score"])
        l = int(row["learned_score"])
        pr, pg, lp = p - rn, p - g, l - p
        lines.append(
            f"| {seed:4d} | {rn:6d} | {g:6d} | {p:7d} | {l:7d} | "
            f"{fmt_delta(pr):>4s} | {fmt_delta(pg):>4s} | {fmt_delta(lp):>4s} |"
        )
    lines.extend(["", "---", ""])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
