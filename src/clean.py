"""步骤 ① 清洗京东评论。

输入：data/raw/京东商品评论_中差评50pct_178条.csv
输出：data/processed/reviews_clean.csv

规则（见 CLAUDE.md 第 5 节、第 10 节）：
1. 重复评论：按 型号 + 正文 + 追评 合并。source_filter 用 "|" 记录所有来源。
   只要任一来源是中评/差评，sample_bucket 记为“中差评”（内容本身就是中差评）。
2. 占位正文（“此用户未（及时）填写评价内容”）：正文置空，标 text_is_placeholder，用追评文字。
3. is_recent_12m：review_date 在采集日前 12 个月内（>= 2025-10-17）。
4. maybe_truncated：正文 >= 245 字（采集时约在 250 字处截断）。
5. full_text = 正文 + 追评。
6. low_info：full_text 少于 8 字，且去掉泛泛好评词后什么都不剩。只标记，不删除。
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/京东商品评论_中差评50pct_178条.csv"
OUT = ROOT / "data/processed/reviews_clean.csv"

RECENT_SINCE = "2025-10-17"  # 采集日 2026-10-16 往前 12 个月
TRUNC_LEN = 245
LOW_INFO_LEN = 8
PLACEHOLDER = re.compile(r"^此用户未(及时)?填写评价内容$")
GENERIC_PRAISE = ["太好用", "很好用", "好用", "很不错", "不错", "挺好", "很好", "满意", "推荐", "啦", "了", "的"]
NEG_FILTERS = {"中评", "差评"}
BUCKET_ORDER = ["中差评", "追评", "普通好评"]


def is_low_info(full_text: str) -> bool:
    if len(full_text) >= LOW_INFO_LEN:
        return False
    rest = re.sub(r"[\W_]+", "", full_text)  # 去掉标点、空格、emoji
    for w in GENERIC_PRAISE:
        rest = rest.replace(w, "")
    return rest == ""


def merge_group(g: pd.DataFrame) -> pd.Series:
    row = g.iloc[0].copy()
    filters = list(dict.fromkeys(g["source_filter"]))
    buckets = list(dict.fromkeys(g["sample_bucket"]))
    row["source_filter"] = "|".join(filters)
    row["sample_bucket_all"] = "|".join(buckets)
    if NEG_FILTERS & set(filters):
        row["sample_bucket"] = "中差评"
    else:
        row["sample_bucket"] = min(buckets, key=BUCKET_ORDER.index)
    row["rating"] = str(g["rating"].astype(int).min())  # 档位映射，不是真实星级
    votes = pd.to_numeric(g["useful_votes"], errors="coerce")
    row["useful_votes"] = "" if votes.isna().all() else str(int(votes.max()))
    row["has_image"] = str((g["has_image"] == "true").any()).lower()
    row["dup_count"] = len(g)
    return row


def main() -> None:
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    n_raw = len(df)
    df["_order"] = range(n_raw)

    keys = ["model", "text", "append_text"]
    merged = (
        df.groupby(keys, sort=False, group_keys=False)
        .apply(merge_group, include_groups=False)
        .reset_index()
        .sort_values("_order")
        .drop(columns="_order")
        .reset_index(drop=True)
    )
    merged = merged[[c for c in df.columns if c != "_order"] + ["sample_bucket_all", "dup_count"]]

    merged["text_is_placeholder"] = merged["text"].str.strip().str.match(PLACEHOLDER)
    merged["text_clean"] = merged["text"].where(~merged["text_is_placeholder"], "").str.strip()
    merged["append_text"] = merged["append_text"].str.strip()
    merged["full_text"] = (merged["text_clean"] + " " + merged["append_text"]).str.strip()

    merged["is_recent_12m"] = merged["review_date"] >= RECENT_SINCE
    merged["maybe_truncated"] = merged["text"].str.len() >= TRUNC_LEN
    merged["low_info"] = merged["full_text"].map(is_low_info)
    merged["full_text_len"] = merged["full_text"].str.len()

    merged.insert(0, "review_id", [f"R{i:03d}" for i in range(1, len(merged) + 1)])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False, encoding="utf-8-sig")

    # ---- 汇总 ----
    print(f"原始 {n_raw} 条 → 合并重复 {(merged['dup_count'] > 1).sum()} 组 → 清洗后 {len(merged)} 条")
    print(f"占位正文（用追评）：{merged['text_is_placeholder'].sum()} 条，其中追评为空：{(merged['text_is_placeholder'] & (merged['append_text'] == '')).sum()} 条")
    print(f"maybe_truncated：{merged['maybe_truncated'].sum()} 条")
    print(f"low_info：{merged['low_info'].sum()} 条 → {merged.loc[merged['low_info'], 'full_text'].tolist()}")
    print(f"is_recent_12m：{merged['is_recent_12m'].sum()} / {len(merged)} 条")
    print("\n各型号 × sample_bucket：")
    tab = pd.crosstab(merged["model"], merged["sample_bucket"], margins=True, margins_name="合计")
    print(tab.to_string())
    print("\n各型号 近 12 个月占比：")
    print(merged.groupby("model")["is_recent_12m"].agg(["sum", "count"]).assign(
        pct=lambda x: (x["sum"] / x["count"]).round(2)).to_string())
    print(f"\n已写出 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
