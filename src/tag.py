"""步骤 ③ 按 docs/tag_schema.md v1.0 给评论和商品问答打标签。

运行：
  .venv/bin/python src/tag.py --limit 10      # 试跑前 10 条
  .venv/bin/python src/tag.py                 # 全量（评论 + 问答）
  .venv/bin/python src/tag.py --mode rule     # 没有 Key 时用关键词规则版

- LLM：src/llm.py（GLM，模型名读 .env 的 ZHIPU_MODEL），一次一条，结果缓存到 jsonl，可断点续跑。
- low_info 评论不调用 LLM，直接记为 generic。
- evidence 必须是原文子串（借用 voice-of-customer-miner 的“原话不改写”规则），程序自动核对并记 evidence_ok。
输出（data/processed/，不提交）：
  reviews_tagged.csv     每条评论一行
  review_tags_long.csv   每个（评论, 标签）一行，供 SQL 分析
  qa_tagged.csv          每条问题一行
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
CLEAN = PROC / "reviews_clean.csv"
QA_RAW = ROOT / "data/raw/京东商品问答_118条.csv"
SCHEMA = ROOT / "docs/tag_schema.md"
PROMPT_VERSION = "v1.0"

F_TAGS = {
    "F1": "清洁力", "F2": "噪音/震感", "F3": "续航/充电", "F4": "刷头", "F5": "牙龈敏感/出血",
    "F6": "使用方法与操作", "F7": "智能识别准确度", "F8": "App 与连接", "F9": "外观/手感/材质",
    "F10": "质量/故障", "F11": "性价比",
}
N_TAGS = {"N1": "物流/包装", "N2": "客服/售后/退换", "N3": "价格变动/价保", "N4": "发票", "N5": "赠品/促销"}
Q_CATS = {"Q1": "选购对比", "Q2": "适用人群", "Q3": "使用方法", "Q4": "刷头与配件",
          "Q5": "售后与质量", "Q6": "产品参数", "Q7": "效果与口碑", "Q8": "其他"}
SENTIMENTS = {"正面", "负面", "中性"}
OVERALL = {"正", "负", "中"}


# ---------------- 提示词 ----------------

def schema_section(start: str, end: str) -> str:
    s = SCHEMA.read_text(encoding="utf-8")
    return s[s.index(start): s.index(end)].strip()


def review_system_prompt() -> str:
    rules = schema_section("## 一、功能标签", "## 四、")
    return f"""你是电动牙刷用户评论的标注员。严格按下面的标签定义给一条京东评论打标签。

{rules}

要求：
1. 只标评论里明确提到的内容，不推测。没提到就不标。
2. tags 只能用 F1–F11，non_product_tags 只能用 N1–N5；每个标签的 sentiment 只能是 正面 / 负面 / 中性。
3. evidence 必须是评论原文中连续的一段文字，逐字复制，不改写、不补字，尽量短（30 字以内）。
4. info_need / claim_gap / generic 为 true 或 false；overall_sentiment 只能是 正 / 负 / 中。
5. 只输出一个 JSON 对象，格式：
{{"tags":[{{"tag":"F7","sentiment":"负面","evidence":"..."}}],"non_product_tags":[{{"tag":"N2","sentiment":"负面","evidence":"..."}}],"info_need":false,"claim_gap":false,"generic":false,"overall_sentiment":"负"}}"""


def qa_system_prompt() -> str:
    rules = schema_section("## 五、商品问答分类", "## 六、")
    return f"""你是电动牙刷买家提问的分类员。按下面的类别给一条问题分类。

{rules}

要求：categories 是类别编号列表（Q1–Q8），第一个是主类别，最多 3 个；info_need 表示这个问题能否靠产品说明、科普或使用指导回答（true/false）。
只输出一个 JSON 对象，格式：{{"categories":["Q2"],"info_need":true}}"""


# ---------------- 规则版（无 Key 时） ----------------

RULE_KW = {
    "F1": ["干净", "清洁"], "F2": ["声音", "噪音", "震", "振动", "吵"], "F3": ["续航", "充电", "电池", "电量"],
    "F4": ["刷头", "刷毛", "炸毛", "呲毛"], "F5": ["牙龈", "出血", "敏感", "肿"],
    "F6": ["不会用", "看不懂", "开关", "按键", "按钮", "档位", "模式"], "F7": ["识别", "感应", "传感", "检测", "定位", "雷达"],
    "F8": ["app", "APP", "App", "连接", "蓝牙", "断联"], "F9": ["颜值", "好看", "握", "手感", "外观", "味"],
    "F10": ["坏", "故障", "失灵", "质量差", "充不进"], "F11": ["性价比", "智商税", "不值", "贵"],
    "N1": ["物流", "快递", "包装", "箱子", "盒子破", "驿站"], "N2": ["客服", "售后", "退货", "换货", "维修"],
    "N3": ["降价", "价保", "差价"], "N4": ["发票"], "N5": ["赠品"],
}
NEG_KW = ["不", "没", "差", "垃圾", "慢", "坏", "硬", "大", "贵", "麻烦", "难", "失望"]


def rule_tag_review(text: str) -> dict:
    out = {"tags": [], "non_product_tags": [], "info_need": False, "claim_gap": "宣传" in text,
           "generic": False, "overall_sentiment": "中"}
    for tag, kws in RULE_KW.items():
        hit = next((k for k in kws if k in text), None)
        if hit:
            i = text.index(hit)
            ev = text[max(0, i - 8): i + 12]
            sent = "负面" if any(n in ev for n in NEG_KW) else "中性"
            out["tags" if tag[0] == "F" else "non_product_tags"].append({"tag": tag, "sentiment": sent, "evidence": ev})
    out["info_need"] = any(k in text for k in ["不知道", "看不懂", "不会", "以为", "才知道"])
    out["generic"] = not out["tags"] and not out["non_product_tags"]
    return out


QA_RULE_KW = {
    "Q1": ["哪个", "选", "区别", "还是", "比"], "Q2": ["敏感", "正畸", "补", "孩子", "儿童", "周岁", "萎缩"],
    "Q3": ["怎么", "模式", "连接"], "Q4": ["刷头", "毛", "充电器", "充电头", "配件"],
    "Q5": ["质量", "售后", "坏", "维修", "正品", "多久"], "Q6": ["续航", "充一次", "充电", "防水", "频率", "噪音", "type"],
    "Q7": ["好用", "效果", "智商税", "好使"],
}


def rule_tag_qa(text: str) -> dict:
    cats = [c for c, kws in QA_RULE_KW.items() if any(k in text for k in kws)][:3] or ["Q8"]
    return {"categories": cats, "info_need": cats[0] in {"Q2", "Q3", "Q4", "Q6"}}


# ---------------- 调用与校验 ----------------

def parse_json(s: str) -> dict:
    s = s.strip()
    s = re.sub(r"^```(json)?|```$", "", s, flags=re.M).strip()
    m = re.search(r"\{.*\}", s, flags=re.S)
    return json.loads(m.group(0) if m else s)


def llm_json(system: str, user: str) -> dict:
    from llm import chat
    last_err = None
    for _ in range(2):  # JSON 解析失败再试一次
        reply = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                     temperature=0.1, response_format={"type": "json_object"})
        try:
            return parse_json(reply)
        except (json.JSONDecodeError, AttributeError) as e:
            last_err = e
    raise RuntimeError(f"JSON 解析失败：{last_err}")


def normalize_review(raw: dict, text: str) -> dict:
    def clean_list(items, allowed):
        out, seen = [], set()
        for it in items or []:
            tag = str(it.get("tag", "")).strip()
            if tag not in allowed or tag in seen:
                continue
            seen.add(tag)
            sent = it.get("sentiment") if it.get("sentiment") in SENTIMENTS else "中性"
            ev = str(it.get("evidence", "")).strip()
            out.append({"tag": tag, "sentiment": sent, "evidence": ev, "evidence_ok": bool(ev) and ev in text})
        return out

    return {
        "tags": clean_list(raw.get("tags"), F_TAGS),
        "non_product_tags": clean_list(raw.get("non_product_tags"), N_TAGS),
        "info_need": bool(raw.get("info_need")),
        "claim_gap": bool(raw.get("claim_gap")),
        "generic": bool(raw.get("generic")),
        "overall_sentiment": raw.get("overall_sentiment") if raw.get("overall_sentiment") in OVERALL else "中",
    }


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {r["id"]: r for r in rows}


def run_items(items: list[tuple[str, str]], cache_path: Path, fn) -> dict:
    cache = load_cache(cache_path)
    todo = [(i, t) for i, t in items if i not in cache]
    print(f"  缓存 {len(items) - len(todo)} 条，待处理 {len(todo)} 条")
    with cache_path.open("a", encoding="utf-8") as f:
        for n, (i, t) in enumerate(todo, 1):
            try:
                res = fn(t)
            except Exception as e:  # noqa: BLE001
                print(f"  {i} 失败：{e}", flush=True)
                continue
            rec = {"id": i, **res}
            cache[i] = rec
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if n % 20 == 0:
                print(f"  已完成 {n}/{len(todo)}", flush=True)
    return cache


# ---------------- 主流程 ----------------

def tag_reviews(mode: str, limit: int | None) -> None:
    df = pd.read_csv(CLEAN, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if limit:
        df = df.head(limit)
    texts = dict(zip(df["review_id"], df["full_text"]))
    low_info = set(df.loc[df["low_info"] == "True", "review_id"])
    system = review_system_prompt()

    def fn_review(text):
        raw = rule_tag_review(text) if mode == "rule" else llm_json(system, f"评论原文：\n{text}")
        return normalize_review(raw, text)

    items = [(i, t) for i, t in texts.items() if i not in low_info]
    cache = run_items(items, PROC / f"tag_cache_reviews_{mode}.jsonl", fn_review)
    for i in low_info:
        cache[i] = {"id": i, "tags": [], "non_product_tags": [], "info_need": False, "claim_gap": False,
                    "generic": True, "overall_sentiment": "正"}

    wide, long = [], []
    for rid in df["review_id"]:
        r = cache.get(rid)
        if r is None:
            continue
        row = {"review_id": rid, "info_need": r["info_need"], "claim_gap": r["claim_gap"],
               "generic": r["generic"], "overall_sentiment": r["overall_sentiment"]}
        for t in r["tags"] + r["non_product_tags"]:
            row[t["tag"]] = t["sentiment"]
            long.append({"review_id": rid, "tag": t["tag"],
                         "tag_name": F_TAGS.get(t["tag"]) or N_TAGS[t["tag"]],
                         "tag_type": "产品" if t["tag"][0] == "F" else "非产品",
                         "sentiment": t["sentiment"], "evidence": t["evidence"], "evidence_ok": t["evidence_ok"]})
        row["tags_json"] = json.dumps(r["tags"] + r["non_product_tags"], ensure_ascii=False)
        wide.append(row)

    tag_cols = list(F_TAGS) + list(N_TAGS)
    out = df.merge(pd.DataFrame(wide), on="review_id", how="left")
    for c in tag_cols:
        if c not in out:
            out[c] = ""
    out[tag_cols] = out[tag_cols].fillna("")
    out["tag_mode"] = mode
    out["prompt_version"] = PROMPT_VERSION
    out.to_csv(PROC / "reviews_tagged.csv", index=False, encoding="utf-8-sig")
    long_df = pd.DataFrame(long, columns=["review_id", "tag", "tag_name", "tag_type", "sentiment", "evidence", "evidence_ok"])
    long_df.to_csv(PROC / "review_tags_long.csv", index=False, encoding="utf-8-sig")

    n_missing = len(df) - len(wide)
    print(f"评论：完成 {len(wide)}/{len(df)} 条（失败 {n_missing}）；标签 {len(long_df)} 个；"
          f"evidence 原文核对通过 {long_df['evidence_ok'].sum()}/{len(long_df)}")


def tag_qa(mode: str, limit: int | None) -> None:
    q = pd.read_csv(QA_RAW, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    q.insert(0, "qa_id", [f"Q{i:03d}" for i in range(1, len(q) + 1)])
    if limit:
        q = q.head(limit)
    system = qa_system_prompt()

    def fn_qa(text):
        raw = rule_tag_qa(text) if mode == "rule" else llm_json(system, f"买家提问：\n{text}")
        cats = [c for c in raw.get("categories", []) if c in Q_CATS][:3] or ["Q8"]
        return {"categories": cats, "info_need": bool(raw.get("info_need"))}

    cache = run_items(list(zip(q["qa_id"], q["question"])), PROC / f"tag_cache_qa_{mode}.jsonl", fn_qa)
    q["categories"] = q["qa_id"].map(lambda i: "|".join(cache[i]["categories"]) if i in cache else "")
    q["main_category"] = q["categories"].str.split("|").str[0]
    q["main_category_name"] = q["main_category"].map(Q_CATS)
    q["info_need"] = q["qa_id"].map(lambda i: cache[i]["info_need"] if i in cache else None)
    q["tag_mode"] = mode
    q.to_csv(PROC / "qa_tagged.csv", index=False, encoding="utf-8-sig")
    print(f"问答：完成 {(q['categories'] != '').sum()}/{len(q)} 条")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["llm", "rule"], default=None, help="默认：有 Key 用 llm，否则 rule")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", choices=["reviews", "qa"], default=None)
    args = ap.parse_args()
    if args.mode is None:
        from llm import has_key
        args.mode = "llm" if has_key() else "rule"
    print(f"模式：{args.mode}")
    if args.only != "qa":
        tag_reviews(args.mode, args.limit)
    if args.only != "reviews":
        tag_qa(args.mode, args.limit)


if __name__ == "__main__":
    main()
