"""对外服务层：API（src/api.py）和 Streamlit 前端（app.py）都只调这里。

每个函数的入参和返回值都是普通 dict / list，可以直接转成 JSON，
以后换成微信小程序时，小程序调用同名 HTTP 接口即可（接口说明见 docs/API.md）。
"""

from __future__ import annotations

import os
import re
from datetime import date
from functools import lru_cache

from . import care, device_sim, qa, quiz, reasons, routing
from .catalog import Catalog, load_catalog
from .kb import default_sources
from .llm_router import fallback_model
from .quota import status as quota_status
from .config import DISCLAIMER, FALLBACK_LABEL, FOOTER, KB_SUMMARY_LABEL, MOCK_LABEL, QUOTA_LABEL, SIMULATED_LABEL


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return load_catalog()


def llm_enabled() -> bool:
    from src import llm
    return llm.has_key() and os.getenv("DEMO_FORCE_MOCK", "") != "1"


def meta() -> dict:
    from .retriever import default_index
    cat = catalog()
    return {
        "footer": FOOTER,
        "disclaimer": DISCLAIMER,
        "llm_mode": "llm" if llm_enabled() else "mock",
        "llm_primary": os.getenv("ZHIPU_MODEL", ""),
        "llm_fallback": fallback_model() or "",
        "mock_label": MOCK_LABEL,
        "fallback_label": FALLBACK_LABEL,
        "kb_summary_label": KB_SUMMARY_LABEL,
        "quota": quota_status(),
        "quota_label": QUOTA_LABEL,
        "simulated_label": SIMULATED_LABEL,
        "retriever": default_index().label,
        "model_attributes": {"available": cat.available, "models": len(cat.models)},
    }


def get_quiz() -> dict:
    return {"questions": quiz.QUESTIONS, "price_note": quiz.PRICE_NOTE,
            "business_assumption": sorted(quiz.BUSINESS_ASSUMPTION)}


def buy_link(model_name: str) -> dict:
    """购买链接（D46 ⑤）：属性表价格出处里有京东官方自营详情页就用它，否则用官网购买渠道页（S12）。"""
    src = default_sources()
    m = catalog().find(model_name)
    for sid in (m.src("jd_list_price") if m else []):
        if "item.jd.com" in src.get(sid, {}).get("url", ""):
            return {"url": src[sid]["url"], "name": src[sid]["name"], "source": sid}
    s12 = src.get("S12", {})
    return {"url": s12.get("url", ""), "name": s12.get("name", "官网购买渠道"), "source": "S12"}


def recommend(answers: dict, explain: bool = True) -> dict:
    res = quiz.recommend(catalog(), answers)
    if res["status"] == "ok":
        for key in ("main", "backup"):
            if res.get(key):
                res[key]["buy"] = buy_link(res[key]["model"])
                if explain:
                    res[key]["reasons"] = reasons.explain(res[key], catalog(), use_llm=llm_enabled())
    return res


def model_options() -> dict:
    return routing.model_options(catalog())


def sources() -> dict:
    """来源清单（编号 → 名称、链接），来自 kb/sources.md。"""
    return default_sources()


def kb_note(chunk_id: str) -> dict:
    """前端需要的单条知识库要点（如 App 下载与绑定说明），带出处。"""
    from .kb import chunk_by_id, citation
    c = chunk_by_id(chunk_id)
    return {"text": c.summary, "citations": [citation(c)]} if c else {"text": "【待知识库】", "citations": []}


def route(model: str | None) -> dict:
    return routing.route(catalog(), model)


def setup(model: str | None, first_time: bool, sensitive: bool, goal: str | None = None) -> dict:
    return care.setup(catalog(), model, first_time, sensitive, goal)


def reminder(model: str | None, start_date: str, subscribe: bool = False) -> dict:
    return care.reminder(catalog(), model, date.fromisoformat(start_date), subscribe)


def profile_sync(answers: dict | None, consent: bool, already_synced: bool = False) -> dict:
    return care.profile_sync(answers, consent, already_synced)


# 只有问题和刷牙习惯相关时才参考设备数据（D46 ⑪）
DEVICE_RELEVANT = r"模式|力度|用力|按压|刷干净|清洁|刷头|刷牙|档位|习惯"


def ask(question: str, model: str | None = None, followup_done: bool = False,
        use_device_data: bool = False, profile: dict | None = None) -> dict:
    """护齿问答。

    use_device_data=True 时，智能款且问题与刷牙习惯相关才附加 V2 模拟设备数据。
    profile：测评第 2–5 题（含自己填写），不含预算；只作用户情况参考。
    """
    summary = None
    if use_device_data and model and route(model)["path"] == "smart" and re.search(DEVICE_RELEVANT, question or ""):
        summary = device_sim.summary()
    profile = {k: v for k, v in (profile or {}).items() if k != "q1" and v not in (None, "", [])} or None
    return qa.answer(question, catalog(), model=model, followup_done=followup_done,
                     device_summary=summary, use_llm=llm_enabled(), profile=profile)
