"""选购测评 5 题 + 规则推荐（PRD 2.3.2、2.3.3）。

规则负责选型号，大模型只负责解释：
1. 筛选：只看成人款（儿童款不进测评，kb_backfill 第 3 项建议 A）；只保留京东官方自营店标价在所选预算内的型号；
   价格【待核实】的型号不参与（无法确认在预算内）。
2. 打分：按 MATCH_RULES 把第 2–4 题的选项对到属性表字段，字段有官方依据且满足条件就加 1 分；
   字段【待核实】/“未提及”不加分（D38）。
3. 排序：得分高者优先；同分价格低者优先；再同分按型号名排序（D27 ①）。第一为主推，第二为备选。
4. 选刷头：只从该型号官方标配刷头里挑（敏感 → 呵护 / 护龈款；牙渍、牙黄 → 亮白款）。
"""

from __future__ import annotations

import re

from .catalog import Catalog, ModelInfo, is_yes
from .config import PENDING

# 价位段：按 2026-10-18 京东官方自营店标价自己切（usmile 没有公开的官方价位段），kb_backfill 第 2 项建议 A
BUDGETS = [
    {"label": "200 元以下", "min": 0, "max": 200},
    {"label": "200–400 元", "min": 200, "max": 400},
    {"label": "400–800 元", "min": 400, "max": 800},
    {"label": "800 元以上", "min": 800, "max": None},
]
PRICE_NOTE = "价位按 2026-10-18 京东官方自营店标价划分，以购买页面为准"

SENSITIVE = "牙龈敏感或容易出血"
NONE_TEETH = "没有特别问题"
BUSINESS_ASSUMPTION = {"有牙渍或烟渍", "牙黄"}  # 无评论数据支持，标为业务假设（PRD 2.3.2）

QUESTIONS = [
    {"id": "q1", "text": "你的预算是多少？", "type": "single", "required": True,
     "options": [b["label"] for b in BUDGETS], "note": PRICE_NOTE},
    {"id": "q2", "text": "你的牙齿情况？（可多选）", "type": "multi", "required": False,
     "options": [SENSITIVE, "正在正畸", "有补牙或牙龈萎缩", "有牙渍或烟渍", NONE_TEETH], "exclusive": NONE_TEETH},
    {"id": "q3", "text": "最想解决的问题？", "type": "single", "required": False,
     "options": ["刷不干净", "刷牙习惯不好", "牙黄", "护理牙龈"]},
    {"id": "q4", "text": "想要的功能？（可多选）", "type": "multi", "required": False,
     "options": ["App 或智能识别", "续航长", "安静或震感小", "方便出差携带"]},
    {"id": "q5", "text": "是第一次用电动牙刷吗？", "type": "single", "required": False, "options": ["是", "否"]},
]


def _db(v: str) -> float | None:
    """噪音字段取最大分贝，如“45dB及以下”→45，“46-65dB”→65。"""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", v)]
    return max(nums) if nums else None


def _int(v: str) -> int | None:
    m = re.search(r"\d+", v)
    return int(m.group()) if m else None


# 测评选项 → (属性表字段, 判断条件, 理由模板，{v} 换成字段原值)。条件只在字段有官方依据时才判断。
# 【待 Melody 确认】这张对照表决定推荐结果；“有补牙或牙龈萎缩”属性表里没有对应字段，暂不加分。
MATCH_RULES = {
    SENSITIVE: ("sensitive_advice", lambda v: True, "官方给敏感用户的建议是：{v}"),
    "正在正畸": ("modes", lambda v: "正畸" in v, "的模式包括：{v}"),
    "有牙渍或烟渍": ("modes", lambda v: "亮白" in v, "有亮白模式（{v}）"),
    "刷不干净": ("zone_or_miss_reminder", is_yes, "有提醒：{v}"),
    "刷牙习惯不好": ("smart_recognition", is_yes, "有智能识别：{v}"),
    "牙黄": ("modes", lambda v: "亮白" in v, "有亮白模式（{v}）"),
    "护理牙龈": ("modes", lambda v: "呵护" in v or "护龈" in v, "有呵护类模式（{v}）"),
    "App 或智能识别": ("app_support", is_yes, "支持笑容加 App"),
    "续航长": ("battery_days", lambda v: (_int(v) or 0) >= 180, "官方续航 {v} 天"),
    "安静或震感小": ("noise", lambda v: (_db(v) or 999) <= 45, "官方噪音 {v}"),
    "方便出差携带": ("travel_case", is_yes, "带旅行收纳"),
}


def _as_list(v) -> list[str]:
    if v is None or v == "":
        return []
    return [v] if isinstance(v, str) else list(v)


def validate(answers: dict) -> list[str]:
    """返回错误列表；空列表表示可以提交。"""
    errors = []
    if answers.get("q1") not in [b["label"] for b in BUDGETS]:
        errors.append("请先选择预算（必答）")
    q2 = _as_list(answers.get("q2"))
    if NONE_TEETH in q2 and len(q2) > 1:
        errors.append("“没有特别问题”不能和其他牙齿情况同时选")
    for q in QUESTIONS[1:]:
        for v in _as_list(answers.get(q["id"])):
            if v not in q["options"]:
                errors.append(f"{q['id']} 的选项不在题目中：{v}")
    return errors


def user_options(answers: dict) -> list[str]:
    opts = []
    for qid in ("q2", "q3", "q4"):
        opts += [o for o in _as_list(answers.get(qid)) if o != NONE_TEETH]
    return opts


def in_budget(price: float | None, budget_label: str) -> bool:
    b = next(b for b in BUDGETS if b["label"] == budget_label)
    if price is None:
        return False
    return price >= b["min"] and (b["max"] is None or price < b["max"])


def match(model: ModelInfo, options: list[str]) -> list[dict]:
    """返回命中的选项及依据（字段、字段值、出处）。"""
    hits = []
    for opt in options:
        rule = MATCH_RULES.get(opt)
        if not rule:
            continue
        field, cond, says = rule
        value = model.get(field)
        if value != PENDING and cond(value):
            hits.append({"option": opt, "field": field, "value": value, "says": says.format(v=value), "sources": model.src(field)})
    return hits


def rank(catalog: Catalog, answers: dict) -> list[dict]:
    opts = user_options(answers)
    cands = [m for m in catalog.models
             if m.category != "儿童" and in_budget(m.price, answers["q1"])]
    scored = [{"model": m, "hits": match(m, opts)} for m in cands]
    scored.sort(key=lambda x: (-len(x["hits"]), x["model"].price, x["model"].name))
    return scored


def pick_brush_head(model: ModelInfo, answers: dict) -> dict:
    """只从官方标配刷头里挑；挑不出就返回标配刷头原文。"""
    heads = model.get("standard_heads")
    src = model.src("standard_heads")
    if heads == PENDING:
        return {"text": PENDING, "sources": []}
    items = [h.strip() for h in re.split(r"[、，,；;]", heads) if h.strip()]
    q2, q3 = _as_list(answers.get("q2")), answers.get("q3")
    want = None
    if SENSITIVE in q2 or q3 == "护理牙龈":
        want = r"呵护|护龈"
    elif "有牙渍或烟渍" in q2 or q3 == "牙黄":
        want = r"亮白"
    if want:
        hit = next((h for h in items if re.search(want, h)), None)
        if hit:
            return {"text": re.sub(r"\s*[×x]\s*\d+$", "", hit), "sources": src}
    return {"text": heads, "sources": src}


def start_advice(model: ModelInfo | None, answers_or_flags: dict) -> dict | None:
    """新手或敏感：从官方建议的起始模式开始（D39 ④，官方没有“最低档”的说法）。

    P10 首次和轻度敏感 → 呵护；Y30 首次 → 早晚双效，轻度敏感 → 柔感呵护 + 缓震呵护刷头（以属性表为准）。
    """
    sensitive = SENSITIVE in _as_list(answers_or_flags.get("q2")) or answers_or_flags.get("sensitive")
    first = answers_or_flags.get("q5") == "是" or answers_or_flags.get("first_time")
    if not (sensitive or first):
        return None
    if model is None:
        return {"text": "从官方建议的起始模式开始，适应后再换；不同型号的起始模式不同，确认型号后再看。", "sources": []}
    field = "sensitive_advice" if sensitive else "first_use_mode"
    v = model.get(field)
    if v == PENDING:
        return {"text": f"从官方建议的起始模式开始，适应后再换。{model.name} 的官方起始模式{PENDING}。", "sources": []}
    if sensitive:
        return {"text": f"从官方建议的起始模式开始，适应后再换。官方建议：{v}。", "sources": model.src(field)}
    return {"text": f"从官方建议的起始模式开始：第一次用选“{v}”模式，适应后再换。", "sources": model.src(field)}


def notes(answers: dict, model: ModelInfo | None = None) -> list[dict]:
    """使用注意事项：只用规则，不经过大模型（PRD 2.3.3 验收场景）。"""
    out = []
    adv = start_advice(model, answers)
    if adv:
        out.append(adv)
    if "正在正畸" in _as_list(answers.get("q2")):
        out.append({"text": "正畸期间的清洁方法请先咨询你的正畸医生。", "sources": []})
    if SENSITIVE in _as_list(answers.get("q2")):
        out.append({"text": "持续出血请先看牙医。", "sources": []})
    return out


def recommend(catalog: Catalog, answers: dict) -> dict:
    """规则推荐，不调用大模型；同输入同输出。"""
    errors = validate(answers)
    if errors:
        return {"status": "invalid", "errors": errors}
    if not catalog.available:
        return {"status": "pending_kb", "message": f"型号属性表还没有整理好，推荐结果{PENDING}", "notes": notes(answers)}
    ranked = rank(catalog, answers)
    if not ranked:
        return {"status": "empty", "message": "这个预算内暂时没有合适的型号", "notes": notes(answers),
                "actions": ["change_budget"]}
    main, backup = ranked[0], (ranked[1] if len(ranked) > 1 else None)
    return {
        "status": "ok",
        "main": _card(main, answers),
        "backup": _card(backup, answers) if backup else None,
        "notes": notes(answers, main["model"]),
        "price_note": PRICE_NOTE,
    }


def _card(item: dict, answers: dict) -> dict:
    m: ModelInfo = item["model"]
    return {
        "model": m.name,
        "price": m.get("jd_list_price"),
        "price_sources": m.src("jd_list_price"),
        "app_support": m.get("app_support"),
        "battery_days": m.get("battery_days"),
        "brush_head": pick_brush_head(m, answers),
        "score": len(item["hits"]),
        "matched": item["hits"],
    }
