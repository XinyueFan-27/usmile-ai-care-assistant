"""推荐理由（PRD 6.1 LLM 3）：大模型只解释已选定的型号，不能换型号。

- 输入：选中型号的官方参数（属性表那一行，去掉【待核实】字段）+ 用户命中的选项。
- 校验：理由里出现的每个数字都必须能在该型号的官方参数里找到；出现其他型号名、条数不是 2–3 条、
  或解析失败 → 整组换成模板文案。
- 没有 Key：直接用模板文案（规则生成，不是 mock，界面注明“模板文案”）。
"""

from __future__ import annotations

import json
import re

from .catalog import Catalog, ModelInfo, is_unverified

SYSTEM = """你是 usmile 电动牙刷推荐卡的文案助手。型号已经由规则选好，你只负责解释为什么适合这位用户。
要求：
1. 只使用“官方参数”里出现的信息，不补充参数，不改换或新增型号，不比较价格高低，不评价其他品牌，不承诺功效。
2. 每个“命中的用户选项”写一条理由（共 2–3 条），一句话，简单中文。
3. 只输出 JSON 数组，例如：[{"option": "续航长", "reason": "……"}]"""


def template_reasons(card: dict) -> list[dict]:
    out = [{"option": h["option"], "reason": f"你选了“{h['option']}”：{card['model']} {h['says']}。",
            "sources": h["sources"]} for h in card.get("matched", [])[:3]]
    if len(out) < 2:
        out.append({"option": "预算", "reason": f"价格在你选的预算内（京东官方自营店标价 ¥{card['price']}）。",
                    "sources": card.get("price_sources", [])})
    return out


def check_reasons(reasons: list, model: ModelInfo, catalog: Catalog) -> bool:
    if not isinstance(reasons, list) or not 2 <= len(reasons) <= 3:
        return False
    facts = model.facts_text()
    for r in reasons:
        text = str(r.get("reason", "")) if isinstance(r, dict) else ""
        if not text:
            return False
        if any(num not in facts for num in re.findall(r"\d+(?:\.\d+)?", text)):
            return False
        for other in catalog.names():
            if other != model.name and other in text.replace(model.name, ""):
                return False
    return True


def explain(card: dict, catalog: Catalog, use_llm: bool = True) -> dict:
    """返回 {"reasons": [...], "by": "llm" | "template"}。"""
    fallback = {"reasons": template_reasons(card), "by": "template"}
    model = catalog.find(card["model"])
    if not use_llm or model is None or len(card.get("matched", [])) < 2:
        return fallback  # 命中少于 2 项时，大模型写不出 2 条有依据的理由
    from src import llm  # 延迟导入：测试和无 Key 时不需要
    if not llm.has_key():
        return fallback
    params = {k: v for k, v in model.raw.items() if not k.endswith("_src") and not is_unverified(v)}
    hits = [h["option"] for h in card["matched"][:3]]  # 最多 3 条理由
    try:
        reply = llm.chat([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"官方参数：{json.dumps(params, ensure_ascii=False)}\n"
                                        f"命中的用户选项：{json.dumps(hits, ensure_ascii=False)}"},
        ])
        m = re.search(r"\[.*\]", reply or "", re.S)
        reasons = json.loads(m.group()) if m else []
    except Exception:  # noqa: BLE001  调用或解析失败都退回模板
        return fallback
    if not check_reasons(reasons, model, catalog):
        return fallback
    src = {h["option"]: h["sources"] for h in card["matched"]}
    for r in reasons:
        r["sources"] = src.get(r.get("option"), model.src("model"))
    return {"reasons": reasons, "by": "llm"}
