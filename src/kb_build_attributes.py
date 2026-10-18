"""步骤 ⑩：生成 kb/model_attributes.csv（型号属性表，给推荐规则用）。

值全部来自 kb/ 里已核对的官方资料；每个字段后面紧跟一列 *_src，写来源编号（见 kb/sources.md）。
找不到官方依据的写【待核实】；官方页面没提到的功能写“未提及”（不等于“没有”）。
价格是 2026-10-18 京东官方自营店标价快照，价格段的切分由产品决定，这里不预设。
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TBD, NA = "【待核实】", "未提及"
REPLACE = ("3", "S15;S16;S17")  # 官网成人刷头页：牙医建议每3个月更换一次刷头
COMPAT_ADULT = ("官网成人刷头（灵动3.0 / 类关节缓震 / 缓震亮白）均写适配全系列成人电刷", "S15;S16;S17")
COMPAT_KIDS = ("官网儿童防蛀刷头系列，适配全系列儿童电刷", "S18")

FIELDS = [
    "model", "category", "jd_list_price", "jd_list_price_src",
    "modes", "modes_src", "intensity_levels", "intensity_levels_src", "bristle", "bristle_src",
    "battery_days", "battery_days_src", "battery_condition", "charging", "charging_src",
    "waterproof", "waterproof_src", "app_support", "app_support_src",
    "suitable_people", "suitable_people_src", "standard_heads", "standard_heads_src",
    "compatible_heads", "compatible_heads_src", "head_replace_months", "head_replace_months_src",
    "head_reminder", "head_reminder_src", "first_use_mode", "first_use_mode_src",
    "sensitive_advice", "sensitive_advice_src", "screen", "screen_src",
    "voice_reminder", "voice_reminder_src", "zone_or_miss_reminder", "zone_or_miss_reminder_src",
    "smart_recognition", "smart_recognition_src", "noise", "noise_src",
    "travel_case", "travel_case_src", "notes",
]


def row(model, category, **kw):
    r = {f: "" for f in FIELDS}
    r.update(model=model, category=category)
    for k, v in kw.items():
        if isinstance(v, tuple):
            r[k], r[f"{k}_src"] = v
        else:
            r[k] = v
    # 未填的字段统一为待核实
    for f in FIELDS:
        if not f.endswith("_src") and f not in ("notes",) and r[f] == "":
            r[f] = TBD
    return r


ROWS = [
    row("Y30", "成人",
        jd_list_price=("299", "S01;S04"),
        modes=("早晚双效/强效净齿/柔感呵护", "S01;S20"),
        intensity_levels=("三档（按键调节）", "S01"),
        bristle=("软毛", "S01"),
        battery_days=("120", "S01;S20"), battery_condition="柔感呵护模式，每天2次每次2分钟",
        charging=("Type-C，4–5小时", "S01;S20"),
        waterproof=("IP68（只防常温水）", "S01;S20"),
        app_support=("是", "S20;S01"),
        suitable_people=("成人", "S01;S20"),
        standard_heads=("新一代缓震亮白刷头×1、新一代缓震呵护刷头×1", "S01"),
        compatible_heads=COMPAT_ADULT, head_replace_months=("3", "S01;S15;S16;S17"),
        head_reminder=("手柄内置刷头天数提醒，85–90天亮红灯，换新后需手动重置", "S01"),
        first_use_mode=("早晚双效", "S01"),
        sensitive_advice=("轻度敏感：柔感呵护模式+新一代缓震呵护刷头；严重敏感先咨询医生", "S01"),
        screen=("是（智能小圆屏）", "S01"), voice_reminder=("是（骨传导语音）", "S01"),
        zone_or_miss_reminder=("是（漏刷提醒、补刷提醒）", "S01"),
        smart_recognition=("是（智能感应齿面识别）", "S20"),
        noise=("45dB及以下", "S01"), travel_case=("否", "S01"),
        notes="官网型号写Y30/Y30 S；京东Y30其他颜色标价279；Y30S标价299–314"),
    row("P10", "成人",
        jd_list_price=("159", "S02;S04"),
        modes=("清洁/亮白/呵护", "S02"),
        intensity_levels=("三档（按键调节）", "S02"),
        bristle=("软毛", "S02"),
        battery_days=("365", "S02"), battery_condition="呵护（soft）模式，每天2次每次2分钟；京东规格表写180天以上（区间分类）",
        charging=("Type-C，4–5小时", "S02"),
        waterproof=("IPX8（只防常温水）", "S02"),
        app_support=("否", "S10;S02"),
        suitable_people=("成人", "S02"),
        standard_heads=("缓震清洁刷头×2", "S02"),
        compatible_heads=COMPAT_ADULT, head_replace_months=("3", "S02;S15;S16;S17"),
        head_reminder=("无手柄提醒；刷毛褪色变白提示更换", "S02"),
        first_use_mode=("呵护", "S02"),
        sensitive_advice=("轻度敏感：呵护模式；严重敏感先咨询医生", "S02"),
        screen=(NA, "S02"), voice_reminder=(NA, "S02"),
        zone_or_miss_reminder=("是（30秒换区提醒）", "S02"),
        smart_recognition=(NA, "S02"),
        noise=("46-65dB", "S02"), travel_case=("否", "S02"),
        notes="官网电动牙刷列表无P10（有P10 PRO），P10在京东官方自营店在售；本项目归为基础款"),
    row("P10S", "成人",
        jd_list_price=("149", "S04"),
        modes=("呵护/清洁/亮白", "S02"),
        battery_days=("180", "S02"), battery_condition="P10详情页对比图（P10S 180天续航）",
        charging=("Type-C", "S02"), waterproof=("IPX8", "S02"),
        app_support=(TBD, ""),
        standard_heads=("缓震清洁刷头", "S02"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        zone_or_miss_reminder=("是（30秒换区提醒）", "S02"),
        notes="资料只来自P10详情页的对比图，其余参数待核实"),
    row("U7 Pro", "成人",
        jd_list_price=("719", "S03;S04"),
        modes=("智能/亮白/呵护", "S24;S03"),
        intensity_levels=("三档", "S03"),
        bristle=("软毛", "S03"),
        battery_days=("60", "S24;S03"), battery_condition="呵护模式，每天2次每次2分钟（官网脚注“22分钟”为笔误，以京东详情图为准）",
        charging=("Type-C，4–5小时", "S24;S03"),
        waterproof=("IPX8（只防常温水）", "S24"),
        app_support=("是（笑容加App/华为智慧生活App）", "S10;S24;S03"),
        suitable_people=("成人", "S24"),
        standard_heads=("新一代缓震亮白刷头、新一代缓震呵护刷头", "S03"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        screen=("是", "S03"), voice_reminder=("是（骨传导语音）", "S24;S03"),
        zone_or_miss_reminder=("是（实时提示未刷到位区域）", "S03"),
        smart_recognition=("是（6区16面，准确率非100%）", "S24"),
        noise=("46-65dB", "S03"), travel_case=("否", "S03"),
        notes="京东由华为京东自营旗舰店销售，品牌栏显示鸿蒙智选；操控方式触控式"),
    row("Y30 Pro", "成人",
        jd_list_price=("399", "S04"),
        modes=("早晚双效/强效净齿/柔感呵护", "S21"),
        battery_days=("120", "S21"), battery_condition="柔感呵护模式，每天2次每次2分钟",
        charging=("4–5小时", "S21"), waterproof=("IP68", "S21"),
        app_support=("是", "S21"), suitable_people=("成人", "S21"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        smart_recognition=("是（智能感应齿面识别）", "S21")),
    row("Y50", "成人",
        jd_list_price=("329", "S04"),
        modes=("日常清洁/早晚双效PRO/专属", "S22"),
        battery_days=("180", "S22"), battery_condition="参数栏180天；脚注写基础清洁一档模式120天以上，不一致待核实",
        charging=("4–5小时", "S22"), waterproof=("IP68", "S22"),
        app_support=("是", "S22"), suitable_people=("成人", "S22"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        notes="连接App和WiFi后有AI刷牙搭子，部分付费"),
    row("Y20", "成人",
        modes=("智能/清洁/亮白/呵护", "S23"),
        battery_days=("90", "S23"), battery_condition="clean模式，每天2次每次2分钟",
        charging=("4–5小时", "S23"), waterproof=("IPX8", "S23"),
        app_support=("是", "S10;S23"), suitable_people=("成人", "S23"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        voice_reminder=("是（骨传导）", "S23")),
    row("F20", "成人",
        jd_list_price=("999", "S04"),
        modes=("智能/亮白/呵护；另有隐形正畸、牙周炎、种植牙、龋齿专护模式", "S25"),
        battery_days=("110", "S25"), battery_condition="呵护模式，每天2次每次2分钟",
        charging=("4–5小时", "S25"), waterproof=("IPX8", "S25"),
        app_support=(TBD, "S10;S25"), suitable_people=("成人", "S25"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        notes="专护模式不能替代医疗治疗（官网说明）"),
    row("F10 PRO", "成人",
        modes=("智能/清洁/亮白/呵护/专属清洁", "S26"),
        battery_days=("180", "S26"), battery_condition="呵护模式",
        charging=("4–5小时", "S26"), waterproof=("IPX8", "S26"),
        app_support=("是", "S10;S26"), suitable_people=("成人", "S26"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        screen=("是（双面屏）", "S26")),
    row("L30", "成人",
        jd_list_price=("999", "S04"),
        modes=("呵护/日常/强效", "S27"),
        battery_days=("100", "S27"), battery_condition="呵护模式发光续航，每天2次每次2分钟",
        charging=("4–5小时", "S27"), waterproof=("IPX7", "S27"),
        app_support=(TBD, ""), suitable_people=("成人", "S27"),
        compatible_heads=(TBD, ""), head_replace_months=REPLACE,
        notes="蓝光电动牙刷"),
    row("P70", "成人",
        jd_list_price=("349", "S04"),
        modes=("呵护/日常/强效/超级动力", "S28"),
        battery_days=("180", "S28"), battery_condition="官网未写测试条件",
        charging=("4–5小时", "S28"), waterproof=("IPX8", "S28"),
        app_support=(TBD, ""), suitable_people=("成人", "S28"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE),
    row("P20", "成人",
        modes=("清洁/亮白/呵护", "S29"),
        battery_days=("210", "S29"), battery_condition="呵护模式，每天2次每次2分钟",
        charging=("4–5小时", "S29"), waterproof=("IPX8", "S29"),
        app_support=(TBD, ""), suitable_people=("成人", "S29"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE),
    row("P20 PRO", "成人",
        modes=("呵护清洁/日常清洁/强效清洁", "S30"),
        battery_days=("90", "S30"), battery_condition="官网未写测试条件",
        charging=("4–5小时", "S30"), waterproof=("IPX8", "S30"),
        app_support=("是", "S10;S30"), suitable_people=("成人", "S30"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        smart_recognition=("是（智能感应齿面识别）", "S30"),
        notes="含P20 PROX；京东在售P20 PRO S（标价259）不是同一型号"),
    row("P10 PRO", "成人",
        modes=("清洁/亮白/呵护", "S31"),
        battery_days=("180", "S31"), battery_condition="clean模式，每天2次每次2分钟",
        charging=("4–5小时", "S31"),
        app_support=(TBD, ""), suitable_people=("成人", "S31"),
        compatible_heads=COMPAT_ADULT, head_replace_months=REPLACE,
        screen=("是（四区小圆屏）", "S31"),
        zone_or_miss_reminder=("是（30秒换区、漏刷区域反馈、4分钟自动关机）", "S31")),
    row("Q30", "儿童",
        jd_list_price=("299", "S04"),
        modes=("智能防蛀/分龄护理", "S32"),
        battery_days=("90", "S32"), charging=("4–5小时", "S32"),
        app_support=("是", "S32;S33"), suitable_people=("3–12岁", "S32"),
        compatible_heads=COMPAT_KIDS, head_replace_months=("3", "S18"),
        voice_reminder=("是（骨传导）", "S32"), zone_or_miss_reminder=("是（六个齿区提醒）", "S32")),
    row("Q20Pro", "儿童",
        modes=("专属/新手/音乐", "S33"),
        battery_days=("90", "S33"), battery_condition="每天2次每次2分钟",
        charging=("4–5小时", "S33"), waterproof=("IPX8", "S33"),
        app_support=("是", "S33"), suitable_people=("3–12岁", "S33"),
        compatible_heads=COMPAT_KIDS, head_replace_months=("3", "S18")),
    row("Q20", "儿童",
        modes=("智能防蛀/日常清洁/新手适应", "S34"),
        battery_days=("90", "S34"), battery_condition="每天2次每次2分钟",
        charging=("4–5小时", "S34"), waterproof=("IPX8", "S34"),
        app_support=("是", "S10;S34"), suitable_people=("3–15岁", "S34"),
        compatible_heads=COMPAT_KIDS, head_replace_months=("3", "S18")),
]


def main() -> None:
    out = ROOT / "kb" / "model_attributes.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ROWS)
    print(f"{len(ROWS)} 个型号 × {len(FIELDS)} 列 → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
