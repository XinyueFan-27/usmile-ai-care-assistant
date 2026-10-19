"""公开部署时的大模型调用限流（保护免费额度）。

- 只在设置了环境变量时生效，本地开发和评测默认不限：
  DEMO_RATE_PER_MIN：每个访问者（按 IP）每分钟最多调用大模型几次，0 = 不限。
  DEMO_DAILY_CAP：全站每天最多调用大模型几次（按北京时间自然日），0 = 不限。
- 超出时抛出 QuotaExceeded（RuntimeError 的子类），调用方沿用原来的兜底：
  问答展示官方资料要点并标明“演示额度”，推荐理由用模板文案。页面照常可用。
- 访问者 IP 由 src/api.py 的中间件写入 client_ip；拿不到时按同一个访问者处理。
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

client_ip: ContextVar[str] = ContextVar("client_ip", default="unknown")

_lock = threading.Lock()
_recent: dict[str, deque] = defaultdict(deque)
_day = {"date": None, "count": 0}
_BEIJING = timezone(timedelta(hours=8))


class QuotaExceeded(RuntimeError):
    pass


def _limits() -> tuple[int, int]:
    return int(os.getenv("DEMO_RATE_PER_MIN", "0") or 0), int(os.getenv("DEMO_DAILY_CAP", "0") or 0)


def check_and_count() -> None:
    """调用大模型前调用一次：没超限就记一次数，超限就抛 QuotaExceeded。"""
    per_min, daily = _limits()
    if not per_min and not daily:
        return
    now = time.time()
    today = datetime.now(_BEIJING).date()
    ip = client_ip.get()
    with _lock:
        if _day["date"] != today:
            _day.update(date=today, count=0)
        if daily and _day["count"] >= daily:
            raise QuotaExceeded("今日演示额度已用完")
        q = _recent[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if per_min and len(q) >= per_min:
            raise QuotaExceeded("提问太频繁")
        q.append(now)
        _day["count"] += 1


def status() -> dict:
    per_min, daily = _limits()
    return {"rate_per_min": per_min, "daily_cap": daily, "used_today": _day["count"] if _day["date"] else 0}
