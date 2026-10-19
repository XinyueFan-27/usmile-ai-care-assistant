"""主模型失败时换备用模型（D41）。不真的调用大模型：用假的 chat 函数（测试用假数据）。"""

from src import llm
from src.core import llm_router


def test_fallback_when_primary_fails(monkeypatch):
    monkeypatch.setenv("ZHIPU_MODEL", "测试主模型")
    monkeypatch.setenv("ZHIPU_FALLBACK_MODEL", "测试备用模型")
    calls = []

    def fake_chat(messages, model=None, **kw):
        calls.append(model)
        if model == "测试主模型":
            raise RuntimeError("429")
        return "测试回复"

    monkeypatch.setattr(llm, "chat", fake_chat)
    assert llm_router.generate([{"role": "user", "content": "x"}]) == ("测试回复", "测试备用模型")
    assert calls == ["测试主模型", "测试备用模型"]


def test_primary_used_when_ok(monkeypatch):
    monkeypatch.setenv("ZHIPU_MODEL", "测试主模型")
    monkeypatch.setattr(llm, "chat", lambda messages, model=None, **kw: "测试回复")
    assert llm_router.generate([{"role": "user", "content": "x"}])[1] == "测试主模型"
