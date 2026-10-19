"""给 prototype/index.html 逐屏截图，并检查手机宽度下有没有横向溢出。

用法：.venv/bin/python src/shoot_prototype.py
依赖：playwright（用本机已装的 Google Chrome，不另下浏览器）。
输出：prototype/screenshots/*.png（390×844 视口，2 倍图；页面截整页，弹窗截当前屏幕）。
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "prototype" / "index.html").as_uri()
OUT = ROOT / "prototype" / "screenshots"
OUT.mkdir(exist_ok=True)

# 溢出检查：页面横向滚动，或可见元素右边超出视口
CHECK = """() => {
  const w = document.documentElement.clientWidth, bad = [];
  if (document.documentElement.scrollWidth > w) bad.push('页面横向滚动 ' + document.documentElement.scrollWidth + '>' + w);
  document.querySelectorAll('.screen.on *, .nav *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > w + 0.5) bad.push((el.className || el.tagName) + ' 右侧超出 ' + Math.round(r.right - w) + 'px');
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow === 'hidden' && !['title','fx-hero','darkcard','phone'].includes(el.className))
      bad.push((el.className || el.tagName) + ' 内容被裁切');
  });
  return bad.slice(0, 10);
}"""


def main():
    problems = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()

        def shot(name, full=True):
            page.wait_for_timeout(300)
            problems[name] = page.evaluate(CHECK)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)

        def fresh(route):
            page.goto(PAGE + "#" + route)
            page.reload()
            page.wait_for_timeout(300)

        # 首页（顶部按 Figma 原设计，人物图在线加载）
        fresh("home")
        page.wait_for_timeout(1500)
        shot("01_home")

        # 智能选购：5 题测评（前 4 题可自己填写）→ 推荐卡
        page.click("#s-home .tile.blue")
        shot("02a_quiz_q1_required")
        page.click("#qOpts .opt >> nth=0")
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=0")  # 牙龈敏感或容易出血
        page.click("#qOpts .opt >> nth=5")  # 其他，自己填写（输入框留空，不编造用户输入）
        shot("02b_quiz_q2_custom_input")
        page.click("#qOpts .opt >> nth=5")  # 取消自填，继续流程
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=3")  # 护理牙龈
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=1")  # 续航长
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=0")  # 第一次用
        shot("02c_quiz_q5_no_custom")
        page.click("#qNext")
        shot("03a_rec")
        page.click("#emptyToggle")
        shot("03b_rec_empty_budget")
        page.click("#emptyToggle")

        # 推荐卡 → 问 AI 助手：自动带上推荐型号，助手先问想了解什么
        page.click("#askAiBtn")
        shot("03c_rec_ask_ai")
        # 在问答里问竞品 → 弹出“不评价竞品”
        page.click("#exampleChips [data-kind=b-competitor]")
        shot("08e_popup_competitor", full=False)
        page.click("#bClose")

        # 买好了 → 我的牙刷：选型号（界面不显示智能款 / 基础款）
        page.goto(PAGE + "#rec")
        page.click("text=买好了")
        shot("04_my_toothbrush_pick_model")
        page.click("[data-model-pick=a]")  # 演示约定：型号 A 在 App 适配列表中
        shot("05_bind_app")
        page.click("#s-bind [data-go=sync]")
        shot("06a_sync_consent")
        page.click("#syncYes")
        page.wait_for_timeout(1900)
        shot("06b_sync_done")

        # 型号 A 的用户在问答里问设备设置 → 简要说明 + 去 App 设置；V2 结合模拟设备数据
        page.click("#s-sync [data-go=chat]")
        page.click("#exampleChips [data-kind=setting]")
        shot("07d_chat_setting_go_app")
        page.click("#exampleChips [data-kind=gentle]")
        shot("07e_chat_devicedata_v2_simulated")

        # 型号 B（不在 App 适配列表中）：首次设置 + 刷头提醒
        page.goto(PAGE + "#route")
        page.click("[data-model-pick=b]")
        page.click("#s-setup [data-key=first] button >> nth=0")
        page.click("#s-setup [data-key=sens] button >> nth=0")
        page.click("#s-setup [data-key=goal] button >> nth=2")
        page.click("#genBtn")
        shot("06c_setup_result")
        page.click("#remindBtn")
        page.evaluate("window.scrollTo(0,0)")
        shot("06d_setup_subscribe", full=False)
        page.click("#subYes")
        # 我不确定型号 → 通用建议
        page.goto(PAGE + "#route")
        page.click("[data-model-pick=unsure]")
        page.click("#s-setup [data-key=first] button >> nth=0")
        page.click("#s-setup [data-key=sens] button >> nth=1")
        page.click("#s-setup [data-key=goal] button >> nth=0")
        page.click("#genBtn")
        shot("06e_setup_unsure_general")

        # AI 问答（未选型号）：追问一次 → 带出处回答 → 没有依据
        fresh("chat")
        page.click("#exampleChips [data-kind=followup]")
        shot("07a_chat_followup")
        page.click("#chatBox [data-model=a]")
        page.click("#chatBox .feedback button >> nth=0")
        shot("07b_chat_answer_cited")
        page.click("#exampleChips [data-kind=nodata]")
        shot("07c_chat_nodata")

        # 安全边界：问答中触发后弹出
        page.click("#exampleChips [data-kind=b-medical] >> nth=0")
        shot("08a_popup_medical", full=False)
        page.click("#urgentToggle")
        shot("08b_popup_urgent", full=False)
        page.click("#bClose")
        page.click("#exampleChips [data-kind=b-service]")
        shot("08c_popup_service", full=False)
        page.click("#bClose")
        page.click("#exampleChips [data-kind=b-fake]")
        shot("08d_popup_fake", full=False)
        page.click("#bClose")

        # 桌面宽度总览（带左侧屏幕导航）
        desk = browser.new_page(viewport={"width": 1200, "height": 920})
        desk.goto(PAGE + "#home")
        desk.wait_for_timeout(300)
        desk.screenshot(path=str(OUT / "00_desktop_overview.png"))
        browser.close()

    bad = {k: v for k, v in problems.items() if v}
    print(f"截图 {len(problems) + 1} 张，存于 {OUT.relative_to(ROOT)}")
    print("溢出检查：" + ("全部通过" if not bad else ""))
    for k, v in bad.items():
        print(" ", k, v)


if __name__ == "__main__":
    main()
