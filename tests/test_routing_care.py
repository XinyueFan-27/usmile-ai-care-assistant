"""分流、首次设置、刷头提醒、画像同步测试（测试用假数据）。"""

from datetime import date

from src.core import care, routing
from src.core.config import PENDING


def test_route_smart_basic_unsure(fake_catalog):
    smart = routing.route(fake_catalog, "测试型号B")
    assert smart["path"] == "smart" and "go_app" in smart["features"]
    assert not {"setup", "reminder"} & set(smart["features"])
    basic = routing.route(fake_catalog, "测试型号A")
    assert basic["path"] == "basic" and {"setup", "reminder", "qa"} <= set(basic["features"])
    assert routing.route(fake_catalog, "我不确定")["path"] == "unsure"
    assert routing.route(fake_catalog, "测试型号C")["path"] == "unsure"  # App 支持待核实


def test_model_options_hide_unverified(fake_catalog):
    o = routing.model_options(fake_catalog)
    assert "测试型号C" in o["unverified"] and "测试型号C" not in o["smart"] + o["basic"]


def test_setup_basic_and_general(fake_catalog):
    r = care.setup(fake_catalog, "测试型号A", first_time=True, sensitive=False)
    assert r["status"] == "ok" and "测试呵护" in r["items"][0]["text"] and r["items"][0]["sources"] == ["T01"]
    assert care.setup(fake_catalog, None, True, False)["label"] == "通用建议"
    assert care.setup(fake_catalog, "测试型号B", True, False)["status"] == "not_applicable"


def test_reminder_dates(fake_catalog):
    r = care.reminder(fake_catalog, "测试型号A", date(2026, 11, 30))
    assert r["next_date"] == "2027-02-28" and r["subscribed"] is False  # 月底顺延到当月最后一天
    assert care.reminder(fake_catalog, "测试型号A", date(2026, 10, 18), subscribe=True)["subscribed"] is True
    assert care.reminder(fake_catalog, "测试型号B", date(2026, 10, 18))["status"] == "not_applicable"


def test_reminder_pending_when_cycle_missing(tmp_path):
    p = tmp_path / "测试用假数据.csv"
    p.write_text("model,category,app_support,head_replace_months\n测试型号X,成人,否,【待核实】\n", encoding="utf-8")
    from src.core.catalog import load_catalog
    r = care.reminder(load_catalog(p), "测试型号X", date(2026, 10, 18))
    assert r["status"] == "pending_kb" and r["next_date"] == PENDING


def test_profile_sync_four_fields_no_budget():
    a = {"q1": "200 元以下", "q2": ["正在正畸"], "q3": "刷不干净", "q4": ["续航长"], "q5": "是"}
    r = care.profile_sync(a, consent=True)
    assert set(r["synced"]) == {"牙齿情况", "最想解决的问题", "想要的功能", "是否第一次用电动牙刷"}
    assert "200 元以下" not in str(r["synced"])
    assert care.profile_sync(a, consent=False)["synced"] == {}
    assert care.profile_sync(a, consent=True, already_synced=True)["status"] == "already_synced"
