"""推荐规则测试（测试用假数据，见 conftest.py）。"""

from src.core import quiz
from src.core.catalog import load_catalog
from src.core.config import PENDING

BASE = {"q1": "200 元以下", "q2": ["没有特别问题"], "q3": None, "q4": [], "q5": "否"}


def test_budget_required_and_exclusive():
    assert quiz.validate({}) == ["请先选择预算（必答）"]
    errs = quiz.validate({"q1": "200 元以下", "q2": ["没有特别问题", "正在正畸"]})
    assert any("没有特别问题" in e for e in errs)


def test_missing_attribute_table_returns_pending(tmp_path):
    res = quiz.recommend(load_catalog(tmp_path / "none.csv"), BASE)
    assert res["status"] == "pending_kb" and PENDING in res["message"]


def test_budget_is_hard_filter_and_kids_excluded(fake_catalog):
    res = quiz.recommend(fake_catalog, BASE)
    models = [res["main"]["model"], res["backup"]["model"]]
    assert set(models) == {"测试型号A", "测试型号B"}  # 测试儿童E ¥120 不进测评
    for b in quiz.BUDGETS:
        r = quiz.recommend(fake_catalog, {**BASE, "q1": b["label"]})
        for k in ("main", "backup"):
            if r.get(k):
                assert quiz.in_budget(float(r[k]["price"]), b["label"])


def test_empty_budget_shows_no_model(fake_catalog):
    res = quiz.recommend(fake_catalog, {**BASE, "q1": "800 元以上"})  # 测试型号D 价格待核实，不算
    assert res["status"] == "empty" and "main" not in res and "暂时没有" in res["message"]


def test_tie_break_price_then_name(fake_catalog):
    # A、B 同价 150，都不命中任何选项 → 按型号名排序
    res = quiz.recommend(fake_catalog, BASE)
    assert res["main"]["model"] == "测试型号A"


def test_score_uses_only_verified_fields(fake_catalog):
    a = {**BASE, "q4": ["App 或智能识别", "安静或震感小"]}
    res = quiz.recommend(fake_catalog, a)
    assert res["main"]["model"] == "测试型号B" and res["main"]["score"] == 2
    # A 的 smart_recognition 是“未提及”，不加分
    hits = quiz.match(fake_catalog.find("测试型号A"), ["刷牙习惯不好"])
    assert hits == []


def test_same_answers_same_result(fake_catalog):
    a = {**BASE, "q2": ["牙龈敏感或容易出血"], "q4": ["续航长"]}
    outs = {str(quiz.recommend(fake_catalog, a)) for _ in range(10)}
    assert len(outs) == 1


def test_brush_head_only_from_standard_heads(fake_catalog):
    b = fake_catalog.find("测试型号B")
    assert quiz.pick_brush_head(b, {"q2": ["牙龈敏感或容易出血"]})["text"] == "测试呵护刷头"
    assert quiz.pick_brush_head(b, {"q2": ["有牙渍或烟渍"]})["text"] == "测试亮白刷头"
    c = fake_catalog.find("测试型号C")
    assert quiz.pick_brush_head(c, {})["text"] == PENDING


def test_sensitive_notes(fake_catalog):
    res = quiz.recommend(fake_catalog, {**BASE, "q2": ["牙龈敏感或容易出血"]})
    text = " ".join(n["text"] for n in res["notes"])
    assert "起始模式" in text and "持续出血请先看牙医" in text
