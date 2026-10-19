"""安全边界（PRD 2.3.6）：先于大模型判断，规则拦截 + Prompt 双保险。

判断顺序：急症 > 医疗（诊断、用药、出血肿胀等症状，D46 ⑩）> 售后 > 真伪 > 竞品 > 主观口碑。
命中前 5 类时不调用大模型，直接返回边界页文案；官方入口从知识库读（KB-SVC-01 / 02）。
"""

from __future__ import annotations

import re

from .config import DISCLAIMER, PENDING
from .kb import chunk_by_id, citation

RULES = [
    ("urgent", r"止不住|不止|大量(出血|流血)|血流不止|外伤|磕断|撞断|摔断|发烧|发热|脸肿|半边脸"),
    ("medical", r"出血|流血|药|消炎|抗生素|诊断|牙周炎|牙龈炎|是不是.{0,6}(炎|病)|什么病|治疗|治好|化脓|溃疡|肿胀|肿了|发炎|疼得|剧痛|很疼"),
    ("service", r"退货|退款|换货|退换|维修|保修|质保|价保|保价|物流|快递|发货|发票|充不进|冲不起|充不上|充不了电|坏了|故障|不开机|开不了机|客服|售后|使用期限"),
    ("authenticity", r"正品|真假|假货|真伪|防伪|山寨|是真的吗"),
    ("competitor", r"飞利浦|philips|欧乐|oral-?b|博朗|米家|小米|松下|舒客|素士|徕芬|罗曼|扉乐|其他品牌|别的牌子|别的品牌"),
    ("subjective", r"好用吗|好不好用|值得买|值不值|值得入手|推荐吗|耐用吗|效果好吗|效果怎么样|质量怎么样|质量好吗"),
]

BOUNDARY = {"urgent", "medical", "service", "authenticity", "competitor"}


def classify(question: str) -> str | None:
    q = question.lower()
    for cat, pattern in RULES:
        if re.search(pattern, q, re.I):
            return cat
    return None


def _kb_entry(chunk_id: str) -> dict:
    c = chunk_by_id(chunk_id)
    if c is None:
        return {"text": PENDING, "citations": []}
    return {"text": c.summary, "citations": [citation(c)]}


def respond(category: str) -> dict:
    """返回边界页内容：title、answer、citations、actions。"""
    if category == "urgent":
        return {"title": "请尽快就医",
                "answer": "请尽快就医。如出血不止、外伤或肿胀发热，请立即前往医院口腔科或急诊。",
                "citations": [], "actions": [], "disclaimer": DISCLAIMER}
    if category == "medical":
        return {"title": "建议看牙医",
                "answer": "助手不能诊断，也不推荐任何药物。你描述的情况建议尽快看牙医，由医生检查后处理。",
                "citations": [], "actions": [], "disclaimer": DISCLAIMER}
    if category == "service":
        e = _kb_entry("KB-SVC-01")
        return {"title": "售后请找官方客服",
                "answer": "助手不处理售后、退换、价保和物流，也不承诺任何保修或退换结果。请联系官方客服：\n" + e["text"],
                "citations": e["citations"], "actions": ["contact_service"], "disclaimer": DISCLAIMER}
    if category == "authenticity":
        e = _kb_entry("KB-SVC-02")
        return {"title": "真伪请走官方查询",
                "answer": "助手不判断真伪。可以通过官方防伪查询：\n" + e["text"],
                "citations": e["citations"], "actions": ["check_authenticity"], "disclaimer": DISCLAIMER}
    if category == "competitor":
        return {"title": "不评价其他品牌",
                "answer": "助手只介绍 usmile 的产品，不评价其他品牌。可以告诉我你最在意什么（清洁、噪音、续航、价格），或者做 5 题选购测评，我按你的需求推荐。",
                "citations": [], "actions": ["start_quiz"], "disclaimer": DISCLAIMER}
    if category == "subjective":
        return {"title": "体验因人而异",
                "answer": "刷牙体验因人而异，助手不下“好用 / 不好用”的结论。可以问我具体参数（模式、续航、刷头），或者做 5 题选购测评。",
                "citations": [], "actions": ["start_quiz"], "disclaimer": DISCLAIMER}
    raise ValueError(category)
