"""步骤 ⑤-1 把清洗、打标签结果存入 SQLite。

输入：data/processed/reviews_tagged.csv、review_tags_long.csv、qa_tagged.csv
输出：data/processed/usmile.db（含评论全文，不提交）

表：
  reviews       每条评论一行（含 full_text、标记字段）
  review_tags   每个（评论, 标签）一行
  questions     每条买家提问一行
  question_cats 每个（提问, 类别）一行
布尔字段统一存 0/1。
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
DB = PROC / "usmile.db"

BOOL_COLS = ["text_is_placeholder", "is_recent_12m", "maybe_truncated", "low_info",
             "info_need", "claim_gap", "ai_can_help", "generic"]
Q_NAMES = {"Q1": "选购对比", "Q2": "适用人群", "Q3": "使用方法", "Q4": "刷头与配件",
           "Q5": "售后与质量", "Q6": "产品参数", "Q7": "效果与口碑", "Q8": "其他"}


def to01(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().map({"true": 1, "false": 0}).fillna(0).astype(int)


def main() -> None:
    r = pd.read_csv(PROC / "reviews_tagged.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for c in BOOL_COLS:
        r[c] = to01(r[c])
    r["is_usmile"] = (r["brand"] == "usmile").astype(int)
    # 主来源：合并过的评论按 D13，含“差评”记差评、含“中评”记中评，否则取第一个
    def main_source(f: str) -> str:
        parts = f.split("|")
        return "差评" if "差评" in parts else "中评" if "中评" in parts else parts[0]
    r["source_main"] = r["source_filter"].map(main_source)
    reviews = r[["review_id", "brand", "model", "is_usmile", "review_date", "is_recent_12m", "sample_bucket",
                 "source_filter", "source_main", "dup_count", "full_text", "full_text_len", "text_is_placeholder",
                 "maybe_truncated", "low_info", "generic", "info_need", "ai_can_help", "claim_gap",
                 "overall_sentiment", "tag_model", "prompt_version"]]

    t = pd.read_csv(PROC / "review_tags_long.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    t["evidence_ok"] = to01(t["evidence_ok"])

    q = pd.read_csv(PROC / "qa_tagged.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    q["info_need"] = to01(q["info_need"])
    questions = q[["qa_id", "brand", "model", "question", "answer_count", "question_date",
                   "main_category", "main_category_name", "categories", "info_need", "tag_model", "prompt_version"]]
    qc = (q[["qa_id", "categories"]].assign(category=q["categories"].str.split("|")).explode("category")
          .assign(category_name=lambda x: x["category"].map(Q_NAMES))[["qa_id", "category", "category_name"]])

    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        reviews.to_sql("reviews", con, index=False)
        t.to_sql("review_tags", con, index=False)
        questions.to_sql("questions", con, index=False)
        qc.to_sql("question_cats", con, index=False)
        con.execute("CREATE INDEX idx_tags_review ON review_tags(review_id)")
        for name in ["reviews", "review_tags", "questions", "question_cats"]:
            n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"{name}: {n} 行")
    print(f"已写出 {DB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
