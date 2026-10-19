"""知识库解析（读真实 kb/，只检查格式）和 API 冒烟测试。"""

import pytest

from src.core.kb import default_sources, load_chunks


def test_real_kb_chunks_have_metadata():
    chunks = load_chunks()
    assert chunks, "kb/ 下应有知识块"
    for c in chunks:
        assert c.chunk_id.startswith("KB-"), c.chunk_id
        assert "来源" in c.meta and "抓取日期" in c.meta, c.chunk_id


def test_sources_resolve():
    src = default_sources()
    assert "S01" in src and src["S01"]["url"].startswith("http")


def test_api_smoke():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from src.api import app

    c = TestClient(app)
    assert c.get("/api/health").json()["footer"].startswith("个人作品集项目")
    assert len(c.get("/api/quiz").json()["questions"]) == 5
    r = c.post("/api/ask", json={"question": "请问这个是正品吗？"}).json()
    assert r["type"] == "boundary"
    assert c.post("/api/reminder", json={"start_date": "bad"}).status_code == 422


def test_web_page_and_buy_link():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from src.api import app
    from src.core import service

    c = TestClient(app)
    page = c.get("/")
    assert page.status_code == 200 and "AI 护齿助手 Demo" in page.text  # web/index.html
    assert "S01" in c.get("/api/sources").json()
    # D46 ⑤：有京东官方自营详情页的用详情页，其余用官网购买渠道页
    assert "item.jd.com" in service.buy_link("Y30")["url"]
    assert service.buy_link("Y50")["source"] == "S12"
