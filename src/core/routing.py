"""按型号分流（PRD 2.3.8）：规则判断，不交给大模型。

- 属性表里 app_support = 支持 → 智能款：显示“去 App 设置”和问答，不显示首次设置和刷头提醒。
- app_support = 不支持 → 基础款：显示首次设置、刷头更换提醒和问答。
- 选“我不确定”、型号不在表中、或 app_support 待核实 → 走基础款路径，只给“通用建议”（D36 ③）。
"""

from __future__ import annotations

from .catalog import Catalog
from .config import PENDING

UNSURE = "我不确定"

FEATURES = {
    "smart": ["go_app", "qa"],
    "basic": ["setup", "reminder", "qa"],
    "unsure": ["setup_general", "qa"],
}


def route(catalog: Catalog, model_name: str | None) -> dict:
    if not model_name or model_name == UNSURE:
        return {"path": "unsure", "model": None, "features": FEATURES["unsure"],
                "message": "型号确认前，只给出“通用建议”。"}
    m = catalog.find(model_name)
    if m is None:
        return {"path": "unsure", "model": model_name, "features": FEATURES["unsure"],
                "message": f"型号属性表里没有这个型号{PENDING}，先按“通用建议”处理。"}
    status = m.app_status
    if status == "unknown":
        return {"path": "unsure", "model": m.name, "features": FEATURES["unsure"],
                "message": f"这个型号是否支持笑容加 App {PENDING}，先按“通用建议”处理。"}
    return {"path": status, "model": m.name, "features": FEATURES[status], "message": ""}


def model_options(catalog: Catalog) -> dict:
    """购后选型号页的选项：按智能款 / 基础款分组。"""
    groups = {"smart": [], "basic": [], "unknown": []}
    for m in catalog.models:
        if m.name != PENDING:
            groups[m.app_status].append(m.name)
    # App 支持情况【待核实】的型号不放进智能款或基础款名单（kb_backfill 第二节）
    return {"available": catalog.available, "smart": groups["smart"], "basic": groups["basic"],
            "unverified": groups["unknown"], "unsure": UNSURE}
