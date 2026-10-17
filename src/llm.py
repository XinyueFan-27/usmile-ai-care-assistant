"""智谱 GLM 调用封装（OpenAI 兼容接口）。

- 配置从 .env 读取：ZHIPU_API_KEY、ZHIPU_MODEL、ZHIPU_BASE_URL。
- 关闭思考模式，默认 temperature = 0.1。
- 失败自动重试（指数退避），两次调用之间限速。
- 任何输出和报错信息都不包含 Key。
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MIN_INTERVAL = 1.0  # 两次调用最少间隔（秒）
MAX_RETRIES = 5
BACKOFF = [5, 15, 30, 60]  # 限流（429）时的等待秒数

_last_call = 0.0


def has_key() -> bool:
    return bool(os.getenv("ZHIPU_API_KEY"))


def model_name() -> str:
    name = os.getenv("ZHIPU_MODEL")
    if not name:
        raise RuntimeError("未设置 ZHIPU_MODEL，请在 .env 中填写")
    return name


def _client() -> OpenAI:
    if not has_key():
        raise RuntimeError("未设置 ZHIPU_API_KEY，请在 .env 中填写")
    return OpenAI(
        api_key=os.environ["ZHIPU_API_KEY"],
        base_url=os.getenv("ZHIPU_BASE_URL") or DEFAULT_BASE_URL,
        max_retries=0,  # 重试由下面自己控制
        timeout=60,
    )


def chat(messages: list[dict], temperature: float = 0.1, model: str | None = None, **kwargs) -> str:
    """调用一次对话，返回模型回复文本。model 不传时用 ZHIPU_MODEL。"""
    global _last_call
    client = _client()
    for attempt in range(1, MAX_RETRIES + 1):
        wait = MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            resp = client.chat.completions.create(
                model=model or model_name(),
                messages=messages,
                temperature=temperature,
                extra_body={"thinking": {"type": "disabled"}},
                **kwargs,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            # 只打印错误类型和状态码，不打印请求内容，避免泄露 Key
            status = getattr(e, "status_code", "")
            code = (getattr(e, "body", None) or {}).get("code", "") if isinstance(getattr(e, "body", None), dict) else ""
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"GLM 调用失败（{type(e).__name__} {status} {code}），已重试 {MAX_RETRIES} 次") from None
            delay = BACKOFF[min(attempt - 1, len(BACKOFF) - 1)] if status == 429 else 2 ** attempt
            print(f"  [重试 {attempt}] {status} {code}，{delay}s 后再试", flush=True)
            time.sleep(delay)
    raise AssertionError("unreachable")
