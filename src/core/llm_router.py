"""大模型调用路由：主模型被限流或失败时，自动换备用模型（D41，PRD 5.3）。

- 主模型：.env 的 ZHIPU_MODEL（glm-4.7-flash）。
- 备用模型：.env 的 ZHIPU_FALLBACK_MODEL；没填时用 ZHIPU_TAG_MODEL（同为 GLM-4-Flash 系列）。
- 返回实际用的模型名，界面和评测记录里注明。
- 界面上少重试、短超时（不能让用户干等）；评测时设 DEMO_LLM_PATIENT=1，按 src/llm.py 默认的长重试跑。
"""

from __future__ import annotations

import os


def fallback_model() -> str | None:
    return os.getenv("ZHIPU_FALLBACK_MODEL") or os.getenv("ZHIPU_TAG_MODEL") or None


def generate(messages: list[dict], timeout: float = 20) -> tuple[str, str]:
    """返回 (回复文本, 实际使用的模型名)。主备都失败时抛出 RuntimeError。"""
    from src import llm

    patient = os.getenv("DEMO_LLM_PATIENT") == "1"
    opts = {} if patient else {"retries": 1, "timeout": timeout}
    primary = llm.model_name()
    try:
        return llm.chat(messages, model=primary, **opts) or "", primary
    except Exception:  # noqa: BLE001
        backup = fallback_model()
        if not backup or backup == primary:
            raise
        return llm.chat(messages, model=backup, **opts) or "", backup
