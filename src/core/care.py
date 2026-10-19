"""购后功能：首次设置（基础款，PRD 2.3.4）、刷头更换提醒（基础款，2.3.7）、画像同步（2.3.10）。"""

from __future__ import annotations

import calendar
from datetime import date

from .catalog import Catalog
from .config import PENDING
from .kb import chunk_by_id, citation
from .quiz import pick_brush_head, start_advice
from .routing import route

GOAL_OPTIONS = ["刷不干净", "刷牙习惯不好", "牙黄", "护理牙龈"]


def _kb_note(chunk_id: str) -> dict:
    c = chunk_by_id(chunk_id)
    return {"text": c.summary, "citations": [citation(c)]} if c else {"text": PENDING, "citations": []}


def setup(catalog: Catalog, model_name: str | None, first_time: bool, sensitive: bool, goal: str | None = None) -> dict:
    """首次设置建议。只对基础款和“我不确定”开放；智能款请去 App。"""
    r = route(catalog, model_name)
    if r["path"] == "smart":
        return {"status": "not_applicable", "message": "这款是智能款，设备设置请在笑容加 App 里完成。", "route": r}
    flags = {"first_time": first_time, "sensitive": sensitive}
    if r["path"] == "unsure":
        return {
            "status": "general",
            "label": "通用建议",
            "route": r,
            "how_to_find_model": PENDING,  # 官方“怎么看型号”的方法没找到（kb_backfill）
            "items": [
                {"name": "起始模式", **(start_advice(None, flags) or {"text": "按官方说明选择模式。", "sources": []})},
                {"name": "第一次用电动牙刷", **_kb_note("KB-USE-01")},
                {"name": "刷头更换", **_kb_note("KB-HEAD-01")},
            ],
            "notes": ["第一周如有出血或不适，换回更温和的模式；持续出血请先看牙医。"],
        }
    m = catalog.find(r["model"])
    head_answers = {"q2": ["牙龈敏感或容易出血"] if sensitive else [], "q3": goal}
    adv = start_advice(m, flags)
    return {
        "status": "ok",
        "label": m.name,
        "route": r,
        "items": [
            {"name": "起始模式和档位", **(adv or {"text": f"可选模式：{m.get('modes')}，档位：{m.get('intensity_levels')}。",
                                           "sources": m.src("modes")})},
            {"name": "刷头建议", **pick_brush_head(m, head_answers)},
            {"name": "刷头更换提示", "text": m.get("head_reminder"), "sources": m.src("head_reminder")},
            {"name": "防水", "text": m.get("waterproof"), "sources": m.src("waterproof")},
        ],
        "notes": ["第一周如有出血或不适，换回更温和的模式；持续出血请先看牙医。"],
    }


def add_months(d: date, months: int) -> date:
    y, mo = divmod(d.month - 1 + months, 12)
    y, mo = d.year + y, mo + 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def reminder(catalog: Catalog, model_name: str | None, start: date, subscribe: bool = False) -> dict:
    """刷头更换提醒（模拟）：下次更换日期 = 开始使用日期 + 官方更换周期。

    订阅是模拟的（不真的发微信订阅消息）；不订阅也能看到日期；默认关闭。
    """
    r = route(catalog, model_name)
    if r["path"] == "smart":
        return {"status": "not_applicable", "message": "智能款的刷头提醒由笑容加 App 发送，小程序不重复提醒。"}
    m = catalog.find(r["model"]) if r["model"] else None
    months = m.replace_months if m else None
    sources = m.src("head_replace_months") if m else []
    if months is None and m is None:
        # 型号不确定时用知识库里的通用周期（KB-HEAD-01 写明适用全系列）
        c = chunk_by_id("KB-HEAD-01")
        if c and "3 个月" in c.title:
            months, sources = 3, c.source_ids
    if months is None:
        return {"status": "pending_kb", "cycle": PENDING, "next_date": PENDING, "subscribed": False}
    return {
        "status": "ok",
        "cycle": f"{months} 个月",
        "cycle_sources": sources,
        "start_date": start.isoformat(),
        "next_date": add_months(start, months).isoformat(),
        "subscribed": bool(subscribe),
        "message": "已模拟订阅：到期时会发一条提醒（含商城入口）。" if subscribe else "未订阅也能看到这个日期；需要时点“提醒我”。",
        "simulated": True,
    }


# 画像同步只同步测评第 2–5 题，不同步预算（D36 ②）
SYNC_FIELDS = {"q2": "牙齿情况", "q3": "最想解决的问题", "q4": "想要的功能", "q5": "是否第一次用电动牙刷"}


def profile_sync(answers: dict | None, consent: bool, already_synced: bool = False) -> dict:
    """模拟“小程序 → App”的一次性画像同步。不真的连接 App。"""
    if not answers:
        return {"status": "no_profile", "synced": {}, "message": "没有做过测评，直接去 App 绑定即可。"}
    if not consent:
        return {"status": "declined", "synced": {}, "message": "已选择不同步，不影响绑定。"}
    if already_synced:
        return {"status": "already_synced", "synced": {}, "message": "画像只在绑定时同步一次，已经同步过了。"}
    synced = {label: answers.get(q) for q, label in SYNC_FIELDS.items() if answers.get(q) not in (None, "", [])}
    return {"status": "synced", "synced": synced, "message": "已同步（模拟），预算不同步。", "simulated": True}
