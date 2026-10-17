"""步骤 ④ 人工抽检。

  .venv/bin/python src/spotcheck.py sample   # 按型号分层随机抽 50 条，生成抽检表
  .venv/bin/python src/spotcheck.py score    # Melody 填完后计算准确率
  .venv/bin/python src/spotcheck.py sample2  # D18：新字段补充抽检 20 条（不与第一批重复）
  .venv/bin/python src/spotcheck.py score2

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
    for c in CHECK_COLS:  # 也接受 T/F、TRUE/FALSE、对/错
        s[c] = s[c].str.strip().str.upper().replace({"T": "Y", "TRUE": "Y", "对": "Y", "F": "N", "FALSE": "N", "错": "N"})
    filled = s[s[CHECK_COLS].isin(["Y", "N"]).all(axis=1)]
    if len(filled) < len(s):
        print(f"注意：{len(s) - len(filled)} 条没填完整，只统计已填的 {len(filled)} 条")
    for c in CHECK_COLS:
        print(f"{c}：{(filled[c] == 'Y').mean():.0%}")
    ok = (filled[CHECK_COLS] == "Y").all(axis=1)
    print(f"完全正确率：{ok.mean():.0%}（{ok.sum()}/{len(filled)}），验收线 85% → {'通过' if ok.mean() >= 0.85 else '未通过'}")
    print("\n错误条目：")
    print(filled.loc[~ok, ["review_id"] + CHECK_COLS + ["备注"]].to_string(index=False))


SHEET2 = PROC / "spotcheck2_20.csv"
N2 = 20
CHECK2 = ["info_need对吗", "claim_gap对吗", "ai_can_help对吗"]


def sample2() -> None:
    """D18 补充抽检：只看 info_need / claim_gap / ai_can_help。候选：非 generic、不在第一批 50 条里。10 条从标为 true 的抽，10 条从其余抽。"""
    df = pd.read_csv(TAGGED, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    first = set(pd.read_csv(SHEET, dtype=str, encoding="utf-8-sig")["review_id"]) if SHEET.exists() else set()
    pool = df[(df["generic"] != "True") & ~df["review_id"].isin(first | EXCLUDE)]
    # 一半从“标为 true”的评论里抽（查 true 标得对不对），一半从其余评论里抽（查有没有漏标）
    pos = pool[(pool["ai_can_help"] == "True") | (pool["claim_gap"] == "True")]
    pos_s = pos.sample(min(N2 // 2, len(pos)), random_state=SEED)
    neg_s = pool[~pool["review_id"].isin(pos["review_id"])].sample(N2 - len(pos_s), random_state=SEED)
    s = pd.concat([pos_s, neg_s]).sort_values("review_id")
    sheet = pd.DataFrame({
        "review_id": s["review_id"], "型号": s["model"], "评论全文": s["full_text"],
        "模型打的标签（情感）：证据": s["tags_json"].map(fmt_tags),
        "info_need": s["info_need"], "claim_gap": s["claim_gap"], "ai_can_help": s["ai_can_help"],
        **{c: "" for c in CHECK2}, "备注": "",
    })
    if SHEET2.exists():
        sys.exit(f"{SHEET2.name} 已存在，为免覆盖已填内容，请先手动改名或删除")
    sheet.to_csv(SHEET2, index=False, encoding="utf-8-sig")
    print(f"已生成 {SHEET2.relative_to(ROOT)}：{len(sheet)} 条（候选池 {len(pool)} 条）")
    print(f"其中 info_need=True {(s['info_need'] == 'True').sum()}，claim_gap=True {(s['claim_gap'] == 'True').sum()}，"
          f"ai_can_help=True {(s['ai_can_help'] == 'True').sum()}")


def score2() -> None:
    s = pd.read_csv(SHEET2, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for c in CHECK2:
        s[c] = s[c].str.strip().str.upper().replace({"T": "Y", "TRUE": "Y", "对": "Y", "F": "N", "FALSE": "N", "错": "N"})
    filled = s[s[CHECK2].isin(["Y", "N"]).all(axis=1)]
    if len(filled) < len(s):
        print(f"注意：{len(s) - len(filled)} 条没填完整，只统计已填的 {len(filled)} 条")
    for c in CHECK2:
        print(f"{c}：{(filled[c] == 'Y').mean():.0%}")
    ok = (filled[CHECK2] == "Y").all(axis=1)
    print(f"完全正确率：{ok.mean():.0%}（{ok.sum()}/{len(filled)}），验收线 85% → {'通过' if ok.mean() >= 0.85 else '未通过'}")
    print(filled.loc[~ok, ["review_id"] + CHECK2 + ["备注"]].to_string(index=False))


if __name__ == "__main__":
    {"sample": sample, "score": score, "sample2": sample2, "score2": score2}[sys.argv[1] if len(sys.argv) > 1 else "sample"]()
