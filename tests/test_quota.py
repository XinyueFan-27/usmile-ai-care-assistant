"""公开部署限流（src/core/quota.py）的测试。不涉及任何用户数据。"""

import pytest

from src.core import quota


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    quota._recent.clear()
    quota._day.update(date=None, count=0)
    monkeypatch.delenv("DEMO_RATE_PER_MIN", raising=False)
    monkeypatch.delenv("DEMO_DAILY_CAP", raising=False)
    yield
    quota._recent.clear()


def test_off_by_default():
    for _ in range(100):
        quota.check_and_count()


def test_per_minute_limit_is_per_visitor(monkeypatch):
    monkeypatch.setenv("DEMO_RATE_PER_MIN", "2")
    token = quota.client_ip.set("1.1.1.1")
    quota.check_and_count()
    quota.check_and_count()
    with pytest.raises(quota.QuotaExceeded):
        quota.check_and_count()
    quota.client_ip.reset(token)
    token = quota.client_ip.set("2.2.2.2")  # 另一个访问者不受影响
    quota.check_and_count()
    quota.client_ip.reset(token)


def test_daily_cap(monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "3")
    for ip in ["a", "b", "c"]:
        token = quota.client_ip.set(ip)
        quota.check_and_count()
        quota.client_ip.reset(token)
    with pytest.raises(quota.QuotaExceeded):
        quota.check_and_count()


def test_quota_falls_back_to_kb_summary(monkeypatch):
    """额度用完时，问答走资料要点兜底，并标明“演示额度”，不报错。"""
    from src.core import qa
    from src.core.config import QUOTA_LABEL
    from src.core.retriever import default_index

    monkeypatch.setenv("DEMO_DAILY_CAP", "1")
    quota._day.update(date=quota.datetime.now(quota._BEIJING).date(), count=1)
    monkeypatch.setattr("src.llm.has_key", lambda: True)
    hits = default_index().search("刷头多久换一次", k=2)
    text, mode = qa._generate("刷头多久换一次", hits, None, None, use_llm=True)
    assert mode == "quota"
    assert text.startswith(QUOTA_LABEL)
