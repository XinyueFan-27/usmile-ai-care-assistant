"""安全边界与问答测试。问题文本用京东买家提问原文（见 src/core/examples.py）；
型号、知识块是测试用假数据（conftest.py）。"""

from src.core import qa, reasons, safety
from src.core.config import MOCK_LABEL, SIMULATED_LABEL
from src.core.examples import EXAMPLES

Q = dict(EXAMPLES)


def test_boundary_categories():
    assert safety.classify(Q["Q040"]) == "competitor"
    assert safety.classify(Q["Q060"]) == "service"
    assert safety.classify(Q["Q100"]) == "authenticity"
    assert safety.classify(Q["Q002"]) == "subjective"
    assert safety.classify(Q["R081"]) == "medical"
    assert safety.classify("刷牙后大量出血止不住") == "urgent"  # 构造
    assert safety.classify(Q["Q020"]) is None


def test_urgent_only_says_see_doctor():
    r = safety.respond("urgent")
    assert "请尽快就医" in r["answer"] and "模式" not in r["answer"] and "刷头" not in r["answer"]


def test_boundary_runs_before_llm(fake_catalog, fake_index):
    r = qa.answer(Q["Q100"], fake_catalog, use_llm=True, index=fake_index)
    assert r["type"] == "boundary" and r["mode"] == "rule"


def test_followup_once(fake_catalog, fake_index):
    r = qa.answer(Q["Q052"], fake_catalog, use_llm=False, index=fake_index)
    assert r["type"] == "followup" and "测试型号A" in r["followup_options"] and "我不确定" in r["followup_options"]
    r2 = qa.answer(Q["Q052"], fake_catalog, model="测试型号A", followup_done=True, use_llm=False, index=fake_index)
    assert r2["type"] != "followup"


def test_mock_answer_has_citation_and_label(fake_catalog, fake_index):
    r = qa.answer("测试型号A 续航", fake_catalog, use_llm=False, index=fake_index)
    assert r["type"] == "answer" and r["mode"] == "mock" and MOCK_LABEL in r["answer"]
    assert r["citations"] and r["citations"][0]["chunk_id"].startswith("T-KB")
    assert r["disclaimer"]


def test_no_evidence(fake_catalog, fake_index):
    r = qa.answer("帮我写首诗", fake_catalog, use_llm=False, index=fake_index)
    assert r["type"] == "no_evidence" and "没有找到可靠的官方资料" in r["answer"]


def test_device_data_labelled(fake_catalog, fake_index):
    r = qa.answer("测试型号B 刷头更换", fake_catalog, model="测试型号B",
                  device_summary={"force_overuse": "较多（模拟）", "updated_at": "模拟"}, use_llm=False, index=fake_index)
    assert r["simulated"] and SIMULATED_LABEL in r["notices"][0] and "参考了你的牙刷数据" in r["notices"][0]


def test_reason_check_rejects_invented_numbers(fake_catalog):
    m = fake_catalog.find("测试型号A")
    good = [{"reason": "续航 365 天"}, {"reason": "有呵护模式"}]
    assert reasons.check_reasons(good, m, fake_catalog)
    assert not reasons.check_reasons([{"reason": "续航 999 天"}, {"reason": "有呵护模式"}], m, fake_catalog)
    assert not reasons.check_reasons([{"reason": "比测试型号B 更好"}, {"reason": "有呵护模式"}], m, fake_catalog)
    assert not reasons.check_reasons([{"reason": "只有一条"}], m, fake_catalog)


def test_citation_formats_and_punctuation_only(fake_catalog, fake_index, monkeypatch):
    """模型回复的几种写法（测试用假数据）：[1, 2] 合并出处能识别；只剩标点算没有依据。"""
    monkeypatch.setattr(qa, "_generate", lambda *a: ("测试回答 [1, 2]。", "llm:测试模型"))
    r = qa.answer("测试型号A 续航", fake_catalog, index=fake_index)
    assert r["type"] == "answer" and len(r["citations"]) == 2 and r["llm_model"] == "测试模型"


def test_battery_number_must_match_battery_days(fake_catalog):
    """测试用假数据：测试型号A 的 battery_days 是 365。"""
    m = fake_catalog.find("测试型号A")
    assert reasons.check_reasons([{"reason": "续航 365 天"}, {"reason": "有呵护模式"}], m, fake_catalog)
    # 3 出现在参数里（更换周期），但不是续航天数
    assert not reasons.check_reasons([{"reason": "续航 3 天"}, {"reason": "有呵护模式"}], m, fake_catalog)


def test_device_hint_and_brush_head_notice(fake_catalog, fake_index):
    r = qa.answer("测试型号B 刷头更换", fake_catalog, model="测试型号B",
                  device_summary={"force_overuse": "较多（模拟）", "updated_at": "模拟"}, use_llm=False, index=fake_index)
    assert any("按压力度" in n and SIMULATED_LABEL in n for n in r["notices"])
    assert any("笑容加 App" in n for n in r["notices"])  # 测试型号B 是智能款


def test_unsupported_claim_dropped(fake_catalog, fake_index, monkeypatch):
    """测试用假数据：模型说“能刷干净”，但引用的假知识块里没有 → 不采用该回答。"""
    monkeypatch.setattr(qa, "_generate", lambda *a: ("测试型号A 能刷干净 [1]。", "llm:测试模型"))
    r = qa.answer("测试型号A 续航", fake_catalog, index=fake_index)
    assert r.get("dropped") == "claim" and "能刷干净" not in r["answer"]


def test_high_score_no_evidence_shows_kb_summary(fake_catalog, fake_index, monkeypatch):
    monkeypatch.setattr(qa, "_generate", lambda *a: ("NO_EVIDENCE", "llm:测试模型"))
    monkeypatch.setitem(qa.HIGH_SCORE, "tfidf", 0.0)
    r = qa.answer("测试型号A 续航", fake_catalog, index=fake_index)
    assert r["mode"] == "kb_summary" and r["citations"]


def test_default_claim_needs_source(fake_catalog, fake_index, monkeypatch):
    """测试用假数据：假知识块里没写“默认”，模型说“默认模式为测试呵护”→ 不采用。"""
    monkeypatch.setattr(qa, "_generate", lambda *a: ("测试型号A 默认模式为测试呵护 [1]。", "llm:测试模型"))
    assert qa.answer("测试型号A 续航", fake_catalog, index=fake_index).get("dropped") == "claim"
