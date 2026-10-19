"""给 Streamlit Demo（app.py）按真实点击流程逐屏截图，并检查手机宽度下有没有横向溢出。

用法：先启动 Demo（.venv/bin/streamlit run app.py，默认 8501 端口），再运行
      .venv/bin/python src/shoot_demo.py [--url http://localhost:8501]
依赖：playwright（用本机已装的 Google Chrome）。
输出：docs/screenshots_demo/*.png（390×844 视口，2 倍图，整页）。
截图里的提问全部是京东买家提问 / 评论原文（src/core/examples.py）；回答是 Demo 当时的真实输出（GLM 或备用模型）。
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots_demo"
OUT.mkdir(parents=True, exist_ok=True)

CHECK = """() => {
  const w = document.documentElement.clientWidth, bad = [];
  if (document.documentElement.scrollWidth > w) bad.push('页面横向滚动 ' + document.documentElement.scrollWidth + '>' + w);
  document.querySelectorAll('.block-container *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > w + 0.5) bad.push((el.className || el.tagName) + ' 右侧超出 ' + Math.round(r.right - w) + 'px');
  });
  return bad.slice(0, 5);
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    url = ap.parse_args().url
    problems = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()

        def settle(timeout=120_000):
            """等 Streamlit 跑完（没有 spinner、状态不是 running）。"""
            page.wait_for_timeout(600)
            page.wait_for_function(
                "() => !document.querySelector('[data-testid=\"stSpinner\"]') && "
                "!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=timeout)
            page.wait_for_timeout(400)

        def shot(name):
            settle()
            # Streamlit 在内部容器里滚动：按内容实际高度临时拉长窗口再截，保证整屏内容都在图里
            h = page.evaluate("""() => { const el = document.querySelector('[data-testid="stMainBlockContainer"]')
                || document.querySelector('.block-container'); return el ? el.scrollHeight : 844; }""")
            page.set_viewport_size({"width": 390, "height": max(844, int(h) + 180)})
            page.wait_for_timeout(500)
            problems[name] = page.evaluate(CHECK)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            print("✓", name, problems[name] or "")

        def click(text, exact=True):
            page.get_by_role("button", name=text, exact=exact).first.click()
            settle()

        def pick(text):
            page.get_by_text(text, exact=True).first.click()
            settle()

        def tick(text):
            page.get_by_role("checkbox", name=text).first.check(force=True)
            settle()

        def examples():
            """展开示例问题（已展开就不再点）。"""
            if not page.get_by_role("button", name="好用吗", exact=True).count():
                page.get_by_text("示例问题（京东买家提问 / 评论原文）").click()
                settle()

        def fresh():
            page.goto(url)
            page.wait_for_selector("text=还没买，帮我选", timeout=120_000)
            settle()

        # 1 首页 → 测评 → 推荐卡 → 智能款分流 → 画像同步
        fresh()
        shot("01_home")
        click("还没买，帮我选")
        pick("200–400 元")
        shot("02_quiz_budget")
        click("下一题")
        tick("牙龈敏感或容易出血")
        shot("03_quiz_teeth")
        click("下一题")
        pick("护理牙龈")
        click("下一题")
        tick("App 或智能识别")
        click("下一题")
        pick("是")
        click("看推荐")
        page.wait_for_selector("text=推荐理由", timeout=180_000)
        shot("04a_rec")
        page.locator("details.srcs summary").first.click()
        shot("04b_rec_sources_open")
        click("买好了 → 按型号继续")
        shot("05_route")
        click("确认型号")
        shot("06_smart_bind_app")
        click("去 App 绑定")
        shot("07a_sync_consent")
        click("同意并去绑定")
        shot("07b_sync_done")

        # 2 已买基础款 → 首次设置 + 刷头提醒
        fresh()
        click("已经买了，教我用")
        pick("基础款｜P10")
        click("确认型号")
        click("生成我的设置")
        shot("08a_basic_setup")
        click("提醒我")
        click("允许")
        shot("08b_basic_reminder_subscribed")

        # 3 问答
        fresh()
        click("直接提问 ›")
        examples()
        click("刷头用多久会炸毛？")
        shot("09_chat_answer_cited")
        click("清空对话")
        examples()
        click("续航多久呀")
        shot("10a_chat_followup")
        click("P10")
        shot("10b_chat_followup_answer")
        for name, q in [("11a_boundary_fake", "请问这个是正品吗？"), ("11b_boundary_medical", "我用了两个月后牙龈肿胀"),
                        ("11c_boundary_competitor", "飞利浦跟这个怎么选"), ("11d_boundary_service", "冲不起电了，是更换还是维修，使用期限是多久？")]:
            click("清空对话") if page.get_by_role("button", name="清空对话").count() else None
            examples()
            click(q)
            shot(name)
            click("返回问答")

        # 4 智能款 + V2 模拟设备数据
        click("清空对话") if page.get_by_role("button", name="清空对话").count() else None
        pick("智能款")
        page.get_by_text("V2：结合我的牙刷数据").click()
        settle()
        examples()
        click("轻柔模式能刷干净吗")
        shot("12_chat_smart_v2_simulated")
        browser.close()

    bad = {k: v for k, v in problems.items() if v}
    print(f"共 {len(problems)} 张，横向溢出问题 {len(bad)} 张", bad or "")


if __name__ == "__main__":
    main()
