"""V2 个性化问答用的“模拟设备数据”（D35，PRD 2.3.11）。

模拟设备数据，仅作演示，非真实用户。只写定性摘要，不编造任何具体数字；
只用于个性化问答，不展示完整报告，不根据数据推断疾病。
"""

from .config import SIMULATED_LABEL

SIMULATED_SUMMARY = {
    "label": SIMULATED_LABEL,
    "head_days": "模拟",
    "force_overuse": "较多（模拟）",
    "common_mode": "模拟",
    "score_trend": "模拟",
    "updated_at": "模拟",
}


def summary() -> dict:
    return dict(SIMULATED_SUMMARY)
