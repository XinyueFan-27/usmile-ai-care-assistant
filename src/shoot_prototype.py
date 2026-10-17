"""给 prototype/index.html 逐屏截图，并检查手机宽度下有没有横向溢出。

用法：.venv/bin/python src/shoot_prototype.py
依赖：playwright（用本机已装的 Google Chrome，不另下浏览器）。
输出：prototype/screenshots/*.png（390×844 视口，2 倍图，整页）。
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
    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow === 'hidden' && el.className !== 'title')
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

        def shot(name):
            page.wait_for_timeout(300)
            problems[name] = page.evaluate(CHECK)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

        # 按真实流程点击：首页 → 测评 5 题 → 推荐卡 → 首次设置
        page.goto(PAGE + "#home")
        shot("01_home")
        page.click("text=还没买，帮我选")
        shot("02a_quiz_q1_required")
        page.click("#qOpts .opt >> nth=0")
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=0")  # 牙龈敏感或容易出血
        shot("02b_quiz_q2_multi")
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=3")  # 护理牙龈
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=1")  # 续航长
        page.click("#qNext")
        page.click("#qOpts .opt >> nth=0")  # 第一次用
        shot("02c_quiz_q5")
        page.click("#qNext")
        shot("03a_rec")
        page.click("#emptyToggle")
        shot("03b_rec_empty_budget")
        page.click("#emptyToggle")
        page.click("text=已经买了 → 去首次设置")
        page.click("#s-setup [data-key=goal] button >> nth=2")
        page.click("#genBtn")
        shot("04a_setup_result")
        page.click("#remindBtn")
        page.evaluate("window.scrollTo(0,0)")
        shot("04b_setup_subscribe")
        page.click("#subYes")

        page.goto(PAGE + "#setup/unsure")
        page.reload()
        shot("04c_setup_unsure_general")

        # 问答：追问一次 → 选型号 → 带出处的回答
        page.goto(PAGE + "#chat")
        page.reload()
        page.click("#exampleChips [data-kind=followup]")
        shot("05a_chat_followup")
        page.click("#chatBox [data-model=a]")
        page.click("#chatBox .feedback button >> nth=0")
        shot("05b_chat_answer_cited")
        page.click("#exampleChips [data-kind=nodata]")
        shot("05c_chat_nodata")

        # 边界页：从问答页点真实输入跳转
        page.click("#exampleChips [data-kind=b-medical]")
        page.wait_for_timeout(900)
        shot("06a_boundary_medical")
        page.click("#urgentToggle")
        shot("06b_boundary_urgent")
        page.goto(PAGE + "#chat")
        page.click("#exampleChips [data-kind=b-service]")
        page.wait_for_timeout(900)
        shot("06c_boundary_service")
        page.goto(PAGE + "#chat")
        page.click("#exampleChips [data-kind=b-fake]")
        page.wait_for_timeout(900)
        shot("06d_boundary_fake")
        page.goto(PAGE + "#rec")
        page.click("#s-rec [data-boundary=competitor]")
        shot("06e_boundary_competitor")

        page.goto(PAGE + "#weekly")
        shot("07_weekly_v2")

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
