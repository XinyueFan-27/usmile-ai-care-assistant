"""步骤 ④ 人工抽检。

  .venv/bin/python src/spotcheck.py sample   # 按型号分层随机抽 50 条，生成抽检表
  .venv/bin/python src/spotcheck.py score    # Melody 填完后计算准确率

抽检表：data/processed/spotcheck_50.csv（含评论全文，不提交）。用 Excel / Numbers 打开填写。
每条填 3 列（Y = 对，N = 错），错的在“备注”写正确答案：
  标签对吗：该打的标签都打了、没打错（含中文名对应的方面）
  情感对吗：每个标签的 正面/负面/中性 都对
  标记对吗：info_need / claim_gap / generic / 整体情感 都对
一条评论 3 列全是 Y 才算“完全正确”。验收：完全正确率 ≥ 85%。
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
TAGGED = PROC / "reviews_tagged.csv"
SHEET = PROC / "spotcheck_50.csv"
N = 50
SEED = 20261016
EXCLUDE = {"R001"}  # 用作提示词示例，不参与抽检
CHECK_COLS = ["标签对吗", "情感对吗", "标记对吗"]

F_N_NAMES = {
    "F1": "清洁力", "F2": "噪音/震感", "F3": "续航/充电", "F4": "刷头", "F5": "牙龈敏感/出血",
    "F6": "使用方法与操作", "F7": "智能识别准确度", "F8": "App 与连接", "F9": "外观/手感/材质",
    "F10": "质量/故障", "F11": "性价比", "N1": "物流/包装", "N2": "客服/售后/退换",
    "N3": "价格变动/价保", "N4": "发票", "N5": "赠品/促销",
}


def fmt_tags(js: str) -> str:
    items = json.loads(js) if js else []
    if not items:
        return "（无）"
    return "\n".join(f"{F_N_NAMES[t['tag']]}（{t['sentiment']}）：{t['evidence']}" for t in items)


def sample() -> None:
    df = pd.read_csv(TAGGED, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    pool = df[~df["review_id"].isin(EXCLUDE)]
    # 按型号等比例分层：每个型号先抽 floor(50/6)=8 条，剩下的名额从其余评论里随机补
    per = N // pool["model"].nunique()
    picked = pool.groupby("model").sample(n=per, random_state=SEED)
    rest = pool[~pool["review_id"].isin(picked["review_id"])].sample(N - len(picked), random_state=SEED)
    s = pd.concat([picked, rest]).sort_values("review_id")

    sheet = pd.DataFrame({
        "review_id": s["review_id"],
        "型号": s["model"],
        "来源筛选": s["source_filter"],
        "评论全文": s["full_text"],
        "模型打的标签（情感）：证据": s["tags_json"].map(fmt_tags),
        "info_need": s["info_need"],
        "claim_gap": s["claim_gap"],
        "generic": s["generic"],
        "整体情感": s["overall_sentiment"],
        **{c: "" for c in CHECK_COLS},
        "备注": "",
    })
    if SHEET.exists():
        sys.exit(f"{SHEET.name} 已存在，为免覆盖已填内容，请先手动改名或删除")
    sheet.to_csv(SHEET, index=False, encoding="utf-8-sig")
    print(f"已生成 {SHEET.relative_to(ROOT)}：{len(sheet)} 条")
    print(sheet["型号"].value_counts().to_string())


def score() -> None:
    s = pd.read_csv(SHEET, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for c in CHECK_COLS:
        s[c] = s[c].str.strip().str.upper()
    filled = s[s[CHECK_COLS].isin(["Y", "N"]).all(axis=1)]
    if len(filled) < len(s):
        print(f"注意：{len(s) - len(filled)} 条没填完整，只统计已填的 {len(filled)} 条")
    for c in CHECK_COLS:
        print(f"{c}：{(filled[c] == 'Y').mean():.0%}")
    ok = (filled[CHECK_COLS] == "Y").all(axis=1)
    print(f"完全正确率：{ok.mean():.0%}（{ok.sum()}/{len(filled)}），验收线 85% → {'通过' if ok.mean() >= 0.85 else '未通过'}")
    print("\n错误条目：")
    print(filled.loc[~ok, ["review_id"] + CHECK_COLS + ["备注"]].to_string(index=False))


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "sample"]()
