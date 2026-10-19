"""对外服务层：API（src/api.py）和 Streamlit 前端（app.py）都只调这里。

每个函数的入参和返回值都是普通 dict / list，可以直接转成 JSON，
以后换成微信小程序时，小程序调用同名 HTTP 接口即可（接口说明见 docs/API.md）。
"""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache

from . import care, device_sim, qa, quiz, reasons, routing
from .catalog import Catalog, load_catalog
from .llm_router import fallback_model
from .config import DISCLAIMER, FOOTER, MOCK_LABEL, SIMULATED_LABEL


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
        "simulated_label": SIMULATED_LABEL,
        "retriever": default_index().label,
        "model_attributes": {"available": cat.available, "models": len(cat.models)},
    }


def get_quiz() -> dict:
    return {"questions": quiz.QUESTIONS, "price_note": quiz.PRICE_NOTE,
            "business_assumption": sorted(quiz.BUSINESS_ASSUMPTION)}


def recommend(answers: dict, explain: bool = True) -> dict:
    res = quiz.recommend(catalog(), answers)
    if res["status"] == "ok" and explain:
        for key in ("main", "backup"):
            if res.get(key):
                res[key]["reasons"] = reasons.explain(res[key], catalog(), use_llm=llm_enabled())
    return res


def model_options() -> dict:
    return routing.model_options(catalog())


def route(model: str | None) -> dict:
    return routing.route(catalog(), model)


def setup(model: str | None, first_time: bool, sensitive: bool, goal: str | None = None) -> dict:
    return care.setup(catalog(), model, first_time, sensitive, goal)


def reminder(model: str | None, start_date: str, subscribe: bool = False) -> dict:
    return care.reminder(catalog(), model, date.fromisoformat(start_date), subscribe)


def profile_sync(answers: dict | None, consent: bool, already_synced: bool = False) -> dict:
    return care.profile_sync(answers, consent, already_synced)


def ask(question: str, model: str | None = None, followup_done: bool = False,
        use_device_data: bool = False) -> dict:
    """护齿问答。use_device_data=True 时附加 V2 模拟设备数据（只对智能款有效）。"""
    summary = None
    if use_device_data and model and route(model)["path"] == "smart":
        summary = device_sim.summary()
    return qa.answer(question, catalog(), model=model, followup_done=followup_done,
                     device_summary=summary, use_llm=llm_enabled())
