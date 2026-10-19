"""给新前端（web/index.html，D46）按真实点击流程逐屏截图，并检查手机宽度下有没有横向溢出。

用法：先启动服务（.venv/bin/uvicorn src.api:app --port 8000），再运行
      .venv/bin/python src/shoot_web.py [--url http://localhost:8000]
依赖：playwright（用本机已装的 Google Chrome）。
输出：docs/screenshots_web/*.png（390×844 视口，2 倍图；页面整页截，弹窗只截一屏）。
截图里的提问全部是京东买家提问 / 评论原文；回答是截图当时后端的真实输出，卡片底部注明生成的模型。
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots_web"
OUT.mkdir(parents=True, exist_ok=True)

CHECK = """() => {
  const w = document.documentElement.clientWidth, bad = [];
  if (document.documentElement.scrollWidth > w) bad.push('页面横向滚动 ' + document.documentElement.scrollWidth + '>' + w);
  document.querySelectorAll('.screen.on *, .mask.on *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > w + 0.5) bad.push((el.className || el.tagName) + ' 右侧超出 ' + Math.round(r.right - w) + 'px');
  });
  return bad.slice(0, 5);
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    url = ap.parse_args().url
    problems = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()

        def idle(timeout=240_000):
            """等页面上的加载提示消失（推荐生成中 / 正在查找官方资料）。"""
            page.wait_for_timeout(400)
            page.wait_for_function("""() => {
                const l = document.querySelector('#recLoading');
                const busy = (l && l.offsetParent && l.style.display !== 'none') ||
                  [...document.querySelectorAll('.msg.bot')].some(m => m.textContent.includes('正在查找官方资料'));
                return !busy; }""", timeout=timeout)
            page.wait_for_timeout(500)

        def shot(name, full=True):
            idle()
            problems[name] = page.evaluate(CHECK)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            print("✓", name, problems[name] or "")

        def css(sel):
            page.locator(sel).first.click()
            page.wait_for_timeout(250)

        def opt(i):
            css(f"#qOpts .opt[data-i='{i}']")

        def chip(text):
            page.locator("#exampleChips .chip", has_text=text).first.click()
            idle()

        # 1 首页 → 测评 → 推荐卡 → 问 AI 助手
        page.goto(url + "/#home")
        page.wait_for_timeout(1500)
        shot("01_home")
        page.goto(url + "/#quiz")
        page.wait_for_timeout(500)
        opt(1)
        shot("02_quiz_q1_budget")
        css("#qNext")
        opt(0)
        opt(5)
        page.fill("#qCustomInput", "牙齿怕冷")
        shot("03_quiz_q2_multi_custom")
        css("#qNext"); opt(3)
        css("#qNext"); opt(0)
        css("#qNext"); opt(0)
        css("#qNext")
        page.wait_for_selector("#recFull", state="visible", timeout=240_000)
        shot("04_rec")
        css("#askAiBtn")
        page.locator("[data-recq]").first.click()
        shot("05_chat_from_rec")

        # 2 我的牙刷 → 智能款绑定 + 画像同步
        page.goto(url + "/#route")
        page.wait_for_selector("#modelList .entry")
        shot("06_route_models")
        page.locator("[data-model-pick='U7 Pro']").click()
        page.wait_for_timeout(800)
        shot("07_bind_app")
        page.locator("#s-bind [data-go='sync']").click()
        page.wait_for_timeout(400)
        shot("08a_sync_consent")
        css("#syncYes")
        page.wait_for_timeout(800)
        shot("08b_sync_done")

        # 3 基础款首次设置 + 刷头提醒
        page.goto(url + "/#route")
        page.wait_for_selector("#modelList .entry")
        page.locator("[data-model-pick='P10']").click()
        page.wait_for_timeout(800)
        css("[data-key=first] [data-v=yes]"); css("[data-key=sens] [data-v=no]"); css("[data-key=goal] [data-v=clean]")
        css("#genBtn")
        page.wait_for_selector("#setupResult", state="visible")
        page.wait_for_timeout(1200)
        shot("09a_setup_basic")
        css("#remindBtn")
        shot("09b_subscribe_sheet", full=False)
        css("#subYes")

        # 4 问答（未选型号的新会话）
        page.goto("about:blank")
        page.goto(url + "/#chat")
        page.wait_for_timeout(1200)
        chip("刷头用多久会炸毛")
        shot("10_chat_answer_cited")
        css("#humanBtn")
        page.wait_for_function("() => !document.querySelector('#humanText').textContent.includes('正在读取')")
        shot("10b_human_service_sheet", full=False)
        css("#humanClose")
        chip("续航多久呀")
        shot("11a_chat_followup")
        page.locator("#chatBox [data-model='P10']").last.click()
        shot("11b_chat_followup_answer")
        chip("好用吗")
        shot("11c_chat_subjective")
        for name, text in [("12a_boundary_medical", "用了几次都牙龈出血了"), ("12b_boundary_fake", "请问这个是正品吗"),
                           ("12c_boundary_competitor", "飞利浦跟这个怎么选"), ("12d_boundary_service", "冲不起电了")]:
            chip(text)
            page.wait_for_selector("#bMask.on")
            shot(name, full=False)
            css("#bClose")

        # 5 智能款 + V2 模拟设备数据（重新打开页面，对话从头开始）
        page.goto("about:blank")
        page.goto(url + "/#route")
        page.wait_for_selector("#modelList .entry")
        page.locator("[data-model-pick='U7 Pro']").click()
        page.wait_for_timeout(800)
        page.evaluate("location.hash = 'chat'")   # 只换页面，不刷新，保留已选的型号
        page.wait_for_timeout(800)
        chip("轻柔模式能刷干净吗")
        shot("13_chat_smart_v2_simulated")
        browser.close()

    bad = {k: v for k, v in problems.items() if v}
    print(f"共 {len(problems)} 张，横向溢出问题 {len(bad)} 张", bad or "")


if __name__ == "__main__":
    main()
