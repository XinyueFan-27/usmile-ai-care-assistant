"""Streamlit 主流程冒烟测试：用 streamlit.testing 模拟点击，走完 首页→测评→推荐卡、
已买→选型号→基础款设置+提醒 / 智能款→绑定→画像同步、问答→边界页。
读真实 kb/（只检查页面能走通，不检查内容）；mock 模式 + 备用检索，不联网。"""

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402


def click(at, label):
    [b for b in at.button if b.label == label][0].click().run()
    assert not at.exception, at.exception


def page_text(at):
    return " ".join(m.value for m in at.markdown)


@pytest.fixture
def at():
    a = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not a.exception
    return a


def test_quiz_to_recommendation(at):
    click(at, "还没买，帮我选")
    at.radio[0].set_value("200–400 元").run()
    click(at, "下一题")
    at.checkbox[0].check().run()  # 牙龈敏感或容易出血
    click(at, "下一题")
    at.radio[0].set_value("护理牙龈").run()
    click(at, "下一题")
    at.checkbox[0].check().run()  # App 或智能识别
    click(at, "下一题")
    at.radio[0].set_value("是").run()
    click(at, "看推荐")
    text = page_text(at)
    assert "主推" in text and "推荐理由" in text and "持续出血请先看牙医" in text
    assert "个人作品集项目，非 usmile 官方，未上线" in text


def test_basic_model_setup_and_reminder(at):
    click(at, "已经买了，教我用")
    at.radio[0].set_value("基础款｜P10").run()
    click(at, "确认型号")
    click(at, "生成我的设置")
    text = page_text(at)
    assert "起始模式" in text and "下次更换日期" in text
    click(at, "提醒我")
    click(at, "允许")
    assert "已模拟订阅" in page_text(at)


def test_smart_model_bind_and_sync(at):
    at.session_state["answers"] = {"q1": "200–400 元", "q2": ["正在正畸"], "q3": "刷不干净", "q4": [], "q5": "是"}
    click(at, "已经买了，教我用")
    at.radio[0].set_value("智能款｜U7 Pro").run()
    click(at, "确认型号")
    assert "支持笑容加 App" in page_text(at)
    click(at, "去 App 绑定")
    assert "不同步预算" in page_text(at)
    click(at, "同意并去绑定")
    assert "预算不同步" in page_text(at)


def test_chat_answer_and_boundary(at):
    click(at, "直接提问 ›")
    click(at, "刷头用多久会炸毛？")
    text = page_text(at)
    assert "出处" in text and "mock 模式" in text
    click(at, "请问这个是正品吗？")
    assert "真伪请走官方查询" in page_text(at)
