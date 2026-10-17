"""步骤 ⑤-2 执行 sql/analysis.sql，结果写到 results/*.csv。

运行：.venv/bin/python src/analyze.py           # 全部
      .venv/bin/python src/analyze.py 03 06     # 只跑名字以 03、06 开头的段
results/ 里只有统计数字，不含评论全文，可以提交。
"""

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/usmile.db"
SQL = ROOT / "sql/analysis.sql"
OUT = ROOT / "results"


def load_queries() -> list[tuple[str, str]]:
    text = SQL.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (\S+)\s*$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def main() -> None:
    only = sys.argv[1:]
    OUT.mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    with sqlite3.connect(DB) as con:
        for name, q in load_queries():
            if only and not any(name.startswith(o) for o in only):
                continue
            df = pd.read_sql_query(q, con)
            df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
            print(f"\n=== {name}（{len(df)} 行）===")
            print(df.to_string(index=False))


if __name__ == "__main__":
    main()
